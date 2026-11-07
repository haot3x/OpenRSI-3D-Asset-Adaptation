"""Read GLB triangle geometry; enforce unchanged mesh-local surface and colors."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct


def load(path):
    raw = Path(path).read_bytes()
    assert raw[:4] == b'glTF' and struct.unpack_from('<I',raw,4)[0] == 2
    n = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20+n])
    length, kind = struct.unpack_from('<II', raw, 20+n)
    assert kind == 0x004e4942
    return doc, raw[28+n:28+n+length]


def accessor(doc, binary, index):
    a = doc['accessors'][index]
    assert 'sparse' not in a
    view = doc['bufferViews'][a['bufferView']]
    width = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    code = {5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]
    fmt = '<'+code*width
    stride = view.get('byteStride',struct.calcsize(fmt))
    offset = view.get('byteOffset',0)+a.get('byteOffset',0)
    return [struct.unpack_from(fmt,binary,offset+i*stride) for i in range(a['count'])]


def meshes(path):
    doc,binary = load(path)
    result = {}
    for node in doc['nodes']:
        if 'mesh' not in node:
            continue
        name = node['name']
        assert name not in result, 'duplicate mesh role '+name
        triangles = []
        colors = []
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            assert primitive.get('mode',4) == 4
            vertices = accessor(doc,binary,primitive['attributes']['POSITION'])
            indices = [v[0] for v in accessor(doc,binary,primitive['indices'])] if 'indices' in primitive else list(range(len(vertices)))
            triangles += [tuple(vertices[j] for j in indices[i:i+3]) for i in range(0,len(indices),3)]
            material = doc.get('materials',[])[primitive['material']] if 'material' in primitive else {}
            colors.append(material.get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1]))
        result[name] = dict(triangles=triangles,colors=colors)
    return result


def compare(canonical, candidate, tolerance=0.00001):
    a,b = meshes(canonical),meshes(candidate)
    issues = []
    if set(a) != set(b):
        issues.append(dict(kind='mesh_roles_changed',missing=sorted(set(a)-set(b)),extra=sorted(set(b)-set(a))))
    for name in sorted(set(a)&set(b)):
        original,new = a[name],b[name]
        if len(original['triangles']) != len(new['triangles']):
            issues.append(dict(mesh=name,kind='triangle_count_changed'));continue
        # Resolve candidate coordinates to exact canonical position IDs using
        # tolerance buckets. This tolerates export reordering and floating noise,
        # while rejecting geometry edits or baked scaling/translations.
        positions = sorted({v for t in original['triangles'] for v in t})
        buckets = {}
        cell = lambda v: tuple(math.floor(x/tolerance) for x in v)
        for i,v in enumerate(positions):buckets.setdefault(cell(v),[]).append(i)
        def resolve(v):
            base = cell(v)
            for offset in itertools.product([-1,0,1],repeat=3):
                for index in buckets.get(tuple(base[i]+offset[i] for i in range(3)),[]):
                    if max(abs(v[i]-positions[index][i]) for i in range(3)) <= tolerance:
                        return index
            raise ValueError('vertex coordinates changed')
        try:
            before = sorted(tuple(sorted(resolve(v) for v in t)) for t in original['triangles'])
            after = sorted(tuple(sorted(resolve(v) for v in t)) for t in new['triangles'])
        except ValueError:
            issues.append(dict(mesh=name,kind='local_surface_changed'))
        else:
            if before != after:issues.append(dict(mesh=name,kind='surface_connectivity_changed'))
        if len(original['colors']) != len(new['colors']) or any(max(abs(x-y) for x,y in zip(c,d))>0.0001 for c,d in zip(original['colors'],new['colors'])):
            issues.append(dict(mesh=name,kind='base_color_changed'))
    return dict(passed=not issues,issues=issues,canonical_sha256=hashlib.sha256(Path(canonical).read_bytes()).hexdigest(),
                candidate_sha256=hashlib.sha256(Path(candidate).read_bytes()).hexdigest(),mesh_count=len(a),
                scope='mesh-local surface/connectivity and base-color preservation; node transforms and rig may change')
