CONTROL_NOOP=False
"""Developer-authored imported-asset adapter. Not a model result or baseline."""
import bpy,math
from mathutils import Matrix,Vector,Euler

scene=bpy.context.scene
scene.frame_start=0;scene.frame_end=48;scene.render.fps=24
poses={'UprightRide':(0,0,0),'DuckRide':(-.95,0,0),'LeftRide':(0,0,math.radians(70))}
if globals().get('CONTROL_NOOP',False):poses={name:(0,0,0) for name in poses}

# Imported active actions and NLA often reference the same action. Normalize
# the imported timeline once per action, then retain it in each adapter clip.
animated=[];seen=set()
for obj in list(scene.objects):
    if not obj.animation_data:continue
    data=obj.animation_data
    action=data.action or next((s.action for t in data.nla_tracks for s in t.strips),None)
    if not action:continue
    if action.as_pointer() not in seen:
        offset=action.frame_range[0]
        for curve in action.fcurves:
            for point in curve.keyframe_points:
                point.co.x-=offset;point.handle_left.x-=offset;point.handle_right.x-=offset
        seen.add(action.as_pointer())
    data.action=action
    for track in list(data.nla_tracks):data.nla_tracks.remove(track)
    animated.append((obj,action))
scene.frame_set(0);bpy.context.view_layer.update()

rig=bpy.data.objects.new('HeadAdapter',None);scene.collection.objects.link(rig)
rig.location=(0,-.190265864133835,1.63638150691986)
bpy.context.view_layer.update()
for name in ['Neck','PelicanHead','EyeLeft','EyeRight','Beak','Pouch']:
    obj=bpy.data.objects[name];world=obj.matrix_world.copy();obj.parent=rig;obj.matrix_world=world

for obj,action in animated:
    data=obj.animation_data;data.action=None
    for name in poses:
        track=data.nla_tracks.new();track.name=name
        strip=track.strips.new(name,0,action)
        strip.action_frame_start=0;strip.action_frame_end=48;strip.frame_start=0;strip.frame_end=48

rig.rotation_mode='QUATERNION';rig.animation_data_create()
for name,angles in poses.items():
    action=bpy.data.actions.new('Head_'+name);rig.animation_data.action=action
    for frame in [0,48]:
        rig.rotation_quaternion=Euler(angles,'XYZ').to_quaternion();rig.keyframe_insert('rotation_quaternion',frame=frame)
    track=rig.animation_data.nla_tracks.new();track.name=name
    strip=track.strips.new(name,0,action);strip.action_frame_start=0;strip.action_frame_end=48;strip.frame_start=0;strip.frame_end=48
    rig.animation_data.action=None
scene.frame_set(0);bpy.context.view_layer.update()
bpy.ops.export_scene.gltf(filepath='/output/asset.glb',export_format='GLB',export_yup=True,
    export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,
    export_frame_range=True,export_force_sampling=True,export_optimize_animation_size=False,
    export_optimize_animation_keep_anim_object=True,export_cameras=False,export_lights=False)
