import bpy
import math
from mathutils import Vector, Matrix

scene = bpy.context.scene
upper_names = ('Neck', 'PelicanHead', 'EyeLeft', 'EyeRight', 'Beak', 'Pouch')
upper = {name: bpy.data.objects[name] for name in upper_names}
objects = list(scene.objects)
scene.render.fps = 24
scene.render.fps_base = 1.0

def godot(v):
    return Vector((v[0], -v[2], v[1]))

def around(point, rotation):
    return Matrix.Translation(point) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-point)

# Read each shared imported action once. Sample the original playback before
# replacing any animation, so active-action/NLA sharing is never retimed twice.
actions = {}
animated = []
strip_ranges = []
for obj in objects:
    ad = obj.animation_data
    if ad is None:
        continue
    participating = False
    if ad.action:
        actions[ad.action.as_pointer()] = ad.action
        participating = True
    for track in ad.nla_tracks:
        for strip in track.strips:
            if strip.action:
                actions[strip.action.as_pointer()] = strip.action
                participating = True
                if not track.mute and not strip.mute:
                    strip_ranges.append((float(strip.frame_start), float(strip.frame_end)))
    if participating:
        animated.append(obj)
if not actions:
    raise RuntimeError('The imported canonical Ride animation is missing.')
if strip_ranges:
    source_start = min(x[0] for x in strip_ranges)
    source_end = max(x[1] for x in strip_ranges)
else:
    source_start = min(float(a.frame_range[0]) for a in actions.values())
    source_end = max(float(a.frame_range[1]) for a in actions.values())
if source_end <= source_start:
    raise RuntimeError('Ride has no playback interval.')

participants = list(dict.fromkeys(animated + list(upper.values())))
world_samples = []
basis_samples = []
for frame in range(49):
    time = source_start + (source_end - source_start) * frame / 48.0
    integer = math.floor(time)
    scene.frame_set(integer, subframe=time-integer)
    bpy.context.view_layer.update()
    world_samples.append({o: o.matrix_world.copy() for o in objects})
    basis_samples.append({o: o.matrix_basis.copy() for o in participants})

reference = world_samples[0]
anchor = godot((0.0, 1.63638150691986, 0.190265864133835))
head_obj = upper['PelicanHead']
head_vertices = [reference[head_obj] @ v.co for v in head_obj.data.vertices]
head = Vector(tuple((min(v[i] for v in head_vertices) + max(v[i] for v in head_vertices)) * 0.5 for i in range(3)))
beak_obj = upper['Beak']
beak_vertices = [reference[beak_obj] @ v.co for v in beak_obj.data.vertices]
forward = max(v.y for v in beak_vertices)
end_vertices = [v for v in beak_vertices if abs(v.y-forward) < 0.00001]
tip = sum(end_vertices, Vector()) / len(end_vertices)

# Orient the original beak endpoint about the unchanged head center.
upright_target = godot((0.0, 2.08, -0.99))
upright_rotation = (tip-head).rotation_difference(upright_target-head)
upright_head_matrix = around(head, upright_rotation)
identity = Matrix.Identity(4)
upright = {o: (identity.copy() if name == 'Neck' else upright_head_matrix.copy()) for name, o in upper.items()}

# A rigid rotation about the real neck attachment keeps the neck/head
# relationship intact while reaching the side window.
side_target = godot((-1.109, 2.08, -0.214))
upright_tip = upright_head_matrix @ tip
side_rotation = (upright_tip-anchor).rotation_difference(side_target-anchor)
side_matrix = around(anchor, side_rotation)
left = {o: side_matrix @ upright[o] for o in upper.values()}

# Fold the neck forward at its attachment while counter-rotating the head.
# Test actual mesh vertices at every original Ride phase for tunnel clearance.
local_vertices = {o: [v.co.copy() for v in o.data.vertices] for o in upper.values()}
duck = None
for step in range(901):
    angle = -math.radians(step * 0.1)
    neck_rotation = Matrix.Rotation(angle, 4, 'X')
    neck_matrix = Matrix.Translation(anchor) @ neck_rotation @ Matrix.Translation(-anchor)
    displaced_head = neck_matrix @ head
    head_matrix = Matrix.Translation(displaced_head-head) @ upright_head_matrix
    candidate = {o: (neck_matrix if name == 'Neck' else head_matrix) for name, o in upper.items()}
    maximum = max((candidate[o] @ worlds[o] @ vertex).z
                  for worlds in world_samples
                  for o in upper.values()
                  for vertex in local_vertices[o])
    if maximum <= 1.997:
        duck = candidate
        break
if duck is None:
    raise RuntimeError('Could not obtain tunnel clearance with rigid upper transforms.')

# Remove only the source animation bindings after sampling. Mesh datablocks,
# materials, parenting, and all unanimated lower components remain untouched.
for obj in participants:
    obj.animation_data_clear()
scene.frame_start = 0
scene.frame_end = 48
scene.frame_set(0)

for clip_name, transforms in (('UprightRide', upright), ('DuckRide', duck), ('LeftRide', left)):
    for obj in participants:
        ad = obj.animation_data_create()
        action = bpy.data.actions.new(clip_name + '__' + obj.name)
        ad.action = action
        obj.rotation_mode = 'QUATERNION'
        previous = None
        for frame in range(49):
            worlds = world_samples[frame]
            if obj in transforms:
                desired_world = transforms[obj] @ worlds[obj]
                if obj.parent:
                    parent_world = worlds[obj.parent]
                    if obj.parent in transforms:
                        parent_world = transforms[obj.parent] @ parent_world
                    basis = obj.matrix_parent_inverse.inverted() @ parent_world.inverted() @ desired_world
                else:
                    basis = desired_world
            else:
                basis = basis_samples[frame][obj]
            location, rotation, scale = basis.decompose()
            if previous is not None:
                rotation.make_compatible(previous)
            previous = rotation.copy()
            obj.location = location
            obj.rotation_quaternion = rotation
            obj.scale = scale
            obj.keyframe_insert(data_path='location', frame=frame, group='Transform')
            obj.keyframe_insert(data_path='rotation_quaternion', frame=frame, group='Transform')
            obj.keyframe_insert(data_path='scale', frame=frame, group='Transform')
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        ad.action = None
        track = ad.nla_tracks.new()
        track.name = clip_name
        strip = track.strips.new(clip_name, 0, action)
        strip.name = clip_name
        strip.action_frame_start = 0.0
        strip.action_frame_end = 48.0
        strip.frame_start = 0.0
        strip.frame_end = 48.0
        strip.scale = 1.0
        strip.repeat = 1.0
        strip.blend_type = 'REPLACE'
        strip.extrapolation = 'NOTHING'
        strip.use_auto_blend = False

scene.frame_set(0)
bpy.context.view_layer.update()
bpy.ops.export_scene.gltf(
    filepath='/output/asset.glb',
    export_format='GLB',
    export_yup=True,
    export_animations=True,
    export_animation_mode='NLA_TRACKS',
    export_nla_strips=True,
    export_frame_range=True,
    export_force_sampling=True,
    export_frame_step=1,
    export_optimize_animation_size=False,
    export_optimize_animation_keep_anim_object=True,
    export_current_frame=False
)
