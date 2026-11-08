"""Real-asset mechanism screening. Geometry-derived inputs; hidden URDF labels."""
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'.tools/real-assets-screen/ArtVIP'
ASSETS=['cabinet_1','microscope001','medical_cart001']


def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
def vec(text,default='0 0 0'):return np.array([float(v) for v in (text or default).split()])
def rotation(rpy):
    r,p,y=rpy;cx,sx=math.cos(r),math.sin(r);cy,sy=math.cos(p),math.sin(p);cz,sz=math.cos(y),math.sin(y)
    return np.array([[cz,-sz,0],[sz,cz,0],[0,0,1.]])@np.array([[cy,0,sy],[0,1.,0],[-sy,0,cy]])@np.array([[1.,0,0],[0,cx,-sx],[0,sx,cx]])
def origin(element):
    t=np.eye(4)
    if element is not None:t[:3,3]=vec(element.get('xyz'));t[:3,:3]=rotation(vec(element.get('rpy')))
    return t


def load_asset(name):
    folder=DATA/name;urdf=next((folder/'urdf').glob('*.urdf'));xml=ET.parse(urdf).getroot()
    links={n.get('name'):n for n in xml.findall('link')};joints=[]
    for j in xml.findall('joint'):
        joints.append(dict(name=j.get('name'),type=j.get('type'),parent=j.find('parent').get('link'),
            child=j.find('child').get('link'),origin=origin(j.find('origin')),axis=vec(j.find('axis').get('xyz')) if j.find('axis') is not None else np.array([1.,0,0])))
    world={name:np.eye(4) for name in links if not any(j['child']==name for j in joints)}
    for _ in range(len(joints)+1):
        for j in joints:
            if j['parent'] in world:world[j['child']]=world[j['parent']]@j['origin']
    if set(links)-set(world):raise ValueError('Unresolved reference hierarchy')
    points={};faces={}
    for link,node in links.items():
        vertices=[];triangles=[];offset=0
        for collision in node.findall('collision'):
            mesh=collision.find('geometry/mesh')
            if mesh is None:continue
            path=(urdf.parent/mesh.get('filename')).resolve()
            if not path.is_relative_to(folder.resolve()):raise ValueError('Mesh path outside delivered asset')
            obj=trimesh.load(path,force='mesh',process=False)
            v=np.asarray(obj.vertices,dtype=float)*vec(mesh.get('scale'),'1 1 1')
            transform=world[link]@origin(collision.find('origin'))
            v=v@transform[:3,:3].T+transform[:3,3]
            vertices.append(v);triangles.append(np.asarray(obj.faces)+offset);offset+=len(v)
        if vertices:points[link]=np.concatenate(vertices);faces[link]=np.concatenate(triangles)
    # Reject unobservable/unsupported source structures before any model call.
    moving=[j for j in joints if j['type']!='fixed']
    if any(j['type'] not in ['revolute','continuous','prismatic'] or j['child'] not in points or j['parent'] not in points for j in moving):
        raise ValueError('Unsupported or non-geometric movable source link')
    names=sorted(points);np.random.default_rng(20261108).shuffle(names);ids={n:'p'+str(i).zfill(2) for i,n in enumerate(names)}
    all_points=np.concatenate(list(points.values()));diagonal=float(np.linalg.norm(np.ptp(all_points,axis=0)))
    descriptors=[]
    for link in names:
        v=points[link];sample=v[np.linspace(0,len(v)-1,min(10000,len(v)),dtype=int)]
        _,axes=np.linalg.eigh(np.cov(sample.T));axes=axes[:,::-1]
        descriptors.append(dict(id=ids[link],center=np.mean(v,axis=0).round(6).tolist(),bbox_min=v.min(axis=0).round(6).tolist(),bbox_max=v.max(axis=0).round(6).tolist(),principal_axes=axes.T.round(6).tolist(),triangle_count=len(faces[link])))
    reference=[]
    for j in moving:
        transform=world[j['parent']]@j['origin'];axis=transform[:3,:3]@j['axis'];axis/=np.linalg.norm(axis)
        reference.append(dict(child=ids[j['child']],parent=ids[j['parent']],type='revolute' if j['type']=='continuous' else j['type'],axis=axis.tolist(),pivot=transform[:3,3].tolist()))
    root_links=[n for n in points if not any(j['child']==n and j['type']!='fixed' for j in joints)]
    if len(root_links)!=1:raise ValueError('Probe currently requires one visible fixed base')
    return dict(name=name,folder=folder,ids=ids,points=points,faces=faces,input=dict(asset=name,coordinate_frame='world +Z up, metres',asset_diagonal=diagonal,parts=descriptors),reference=dict(root_id=ids[root_links[0]],joints=reference),diagonal=diagonal)


def render_parts(asset,out):
    out.mkdir(parents=True,exist_ok=False)
    colors=[(230,50,60),(20,120,230),(20,175,100),(225,145,10),(155,70,200),(0,180,180),(220,70,155),(90,115,40),(70,75,180),(155,100,55),(70,160,155),(190,100,100),(100,100,100)]
    cloud=[];ids=[]
    for index,(name,pid) in enumerate(asset['ids'].items()):
        mesh=trimesh.Trimesh(vertices=asset['points'][name],faces=asset['faces'][name],process=False)
        p,_=trimesh.sample.sample_surface(mesh,16000,seed=20261108+index)
        cloud.append(p);ids.extend([index]*len(p))
    cloud=np.concatenate(cloud);ids=np.array(ids);center=(cloud.min(axis=0)+cloud.max(axis=0))/2
    definitions={'front':(np.array([1.,0,0]),np.array([0.,0,1]),np.array([0.,-1,0])),
        'side':(np.array([0.,1,0]),np.array([0.,0,1]),np.array([1.,0,0])),
        'iso':(np.array([1.,1,0])/2**.5,np.array([-1.,1,2])/6**.5,np.array([1.,-1,1])/3**.5)}
    for name,(u,v,w) in definitions.items():
        q=cloud-center;xy=np.stack([q@u,q@v],axis=1);extent=max(np.ptp(xy[:,0]),np.ptp(xy[:,1]));scale=430/max(extent,1e-9)
        pixels=xy*scale;pixels[:,0]+=270;pixels[:,1]=250-pixels[:,1];depth=q@w
        im=Image.new('RGB',(720,520),(245,245,245));draw=ImageDraw.Draw(im)
        for i in np.argsort(depth):
            x,y=pixels[i];draw.ellipse((x-1,y-1,x+1,y+1),fill=colors[ids[i]%len(colors)])
        for i,(link,pid) in enumerate(asset['ids'].items()):
            c=(np.mean(asset['points'][link],axis=0)-center);x,y=c@u*scale+270,250-c@v*scale
            draw.text((x,y),pid,fill=(0,0,0),stroke_width=1,stroke_fill='white')
            draw.rectangle((555,30+i*25,573,45+i*25),fill=colors[i%len(colors)]);draw.text((582,30+i*25),pid,fill='black')
        draw.text((12,10),asset['name']+' / '+name+' / neutral collision-surface point cloud',fill='black')
        im.save(out/(name+'.png'))


def score(reference,prediction,diagonal):
    expected={j['child']:j for j in reference['joints']};pred={j['child']:j for j in prediction['joints']}
    rows=[];pivot_tolerance=max(.005,.02*diagonal)
    for child,gt in expected.items():
        actual=pred.get(child);row=dict(child=child,parent_correct=False,type_correct=False,axis_correct=False,pivot_correct=None)
        if actual:
            kind='revolute' if actual['type']=='continuous' else actual['type'];row['parent_correct']=actual['parent']==gt['parent'];row['type_correct']=kind==gt['type']
            if kind!='fixed':
                axis=np.array(actual['axis_world'],dtype=float);n=float(np.linalg.norm(axis))
                if n<=1e-9:raise ValueError('Zero predicted movable axis')
                axis/=n;angle=math.degrees(math.acos(min(1.,abs(float(axis@np.array(gt['axis']))))))
                row['axis_error_degrees']=angle;row['axis_correct']=angle<=15
                if gt['type']=='revolute':
                    delta=np.array(actual['pivot_world'])-np.array(gt['pivot']);err=float(np.linalg.norm(delta-np.array(gt['axis'])*(delta@np.array(gt['axis']))))
                    row['pivot_perpendicular_error_metres']=err;row['pivot_correct']=err<=pivot_tolerance
        row['passed']=row['parent_correct'] and row['type_correct'] and row['axis_correct'] and (gt['type']=='prismatic' or row['pivot_correct'] is True)
        rows.append(row)
    return dict(kind='URDF ground-truth agreement diagnostic, not physical functionality or official reward',joint_count=len(rows),correct=sum(r['passed'] for r in rows),fraction=sum(r['passed'] for r in rows)/len(rows),root_correct=prediction['root_id']==reference['root_id'],pivot_tolerance_metres=pivot_tolerance,rows=rows)


def validate_prediction(prediction,parts):
    ids={p['id'] for p in parts};root=prediction['root_id'];joints=prediction['joints']
    if root not in ids:raise ValueError('Unknown root')
    children=[j['child'] for j in joints]
    if len(children)!=len(set(children)) or set(children)!=ids-{root}:raise ValueError('Each non-root part requires exactly one joint')
    parents={j['child']:j['parent'] for j in joints}
    for j in joints:
        if j['parent'] not in ids or j['child']==j['parent']:raise ValueError('Invalid parent')
        for field in ['axis_world','pivot_world']:
            value=np.asarray(j[field],dtype=float)
            if value.shape!=(3,) or not np.isfinite(value).all():raise ValueError('Invalid vector')
        if j['type'] not in ['fixed','revolute','continuous','prismatic']:raise ValueError('Invalid type')
        if j['type']!='fixed' and np.linalg.norm(j['axis_world'])<1e-9:raise ValueError('Zero movable axis')
        seen=set();node=j['child']
        while node!=root:
            if node in seen or node not in parents:raise ValueError('Disconnected or cyclic hierarchy')
            seen.add(node);node=parents[node]
