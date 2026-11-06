import bpy, math, os
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
scene.frame_start=0
scene.frame_end=48
scene.render.fps=24

def mat(name,color,metallic=0):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metallic
    p.inputs['Roughness'].default_value=.72
    return m
white=mat('Ivory feathers',(.84,.88,.83))
wing=mat('Charcoal folded feathers',(.055,.085,.095))
orange=mat('Orange bill and legs',(.95,.43,.025))
pouchmat=mat('Golden throat pouch',(.91,.64,.16))
turquoise=mat('Turquoise enamel',(.025,.46,.48),.25)
rubber=mat('Dark tyres',(.045,.063,.069))
silver=mat('Silver spokes',(.49,.59,.61),.65)
black=mat('Eyes',(.008,.012,.013))

def empty(name,loc,parent=None):
    o=bpy.data.objects.new(name,None)
    scene.collection.objects.link(o)
    o.parent=parent
    o.location=loc
    return o

def mesh(name,verts,faces,material,parent=None):
    me=bpy.data.meshes.new(name+'Geometry')
    me.from_pydata(verts,[],faces)
    me.update()
    o=bpy.data.objects.new(name,me)
    scene.collection.objects.link(o)
    o.data.materials.append(material)
    o.parent=parent
    return o

def ellipsoid(name,loc,scale,material,parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8,ring_count=6,radius=1)
    o=bpy.context.object
    o.name=name
    for v in o.data.vertices:
        v.co.x*=scale[0]
        v.co.y*=scale[1]
        v.co.z*=scale[2]
    o.data.materials.append(material)
    o.parent=parent
    o.location=loc
    return o

def rod(name,a,b,r,material,parent=None,vertices=6):
    a,b=Vector(a),Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=(b-a).length)
    o=bpy.context.object
    o.name=name
    o.data.materials.append(material)
    o.parent=parent
    o.location=(a+b)*.5
    o.rotation_mode='QUATERNION'
    o.rotation_quaternion=(b-a).to_track_quat('Z','Y')
    return o

def box(name,loc,size,material,parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object
    o.name=name
    for v in o.data.vertices:
        v.co.x*=size[0]
        v.co.y*=size[1]
        v.co.z*=size[2]
    o.data.materials.append(material)
    o.parent=parent
    o.location=loc
    return o

front=empty('WheelFront',(0,.85,.5))
rear=empty('WheelRear',(0,-.85,.5))
crank=empty('Crank',(0,-.1,.52))
for suffix,pivot in [('Front',front),('Rear',rear)]:
    verts=[]
    faces=[]
    n=24
    k=6
    for i in range(n):
        a=2*math.pi*i/n
        for j in range(k):
            b=2*math.pi*j/k
            radius=.465+.035*math.cos(b)
            verts.append((.04*math.sin(b),radius*math.cos(a),radius*math.sin(a)))
    for i in range(n):
        for j in range(k):
            faces.append((i*k+j,((i+1)%n)*k+j,((i+1)%n)*k+(j+1)%k,i*k+(j+1)%k))
    mesh('Tyre'+suffix,verts,faces,rubber,pivot)
    rod('Hub'+suffix,(-.07,0,0),(.07,0,0),.065,silver,pivot)
    for i in range(8):
        a=2*math.pi*i/8
        endpoint=(0,.4*math.cos(a),.4*math.sin(a))
        rod('Spoke'+suffix+str(i),(0,0,0),endpoint,.008,silver,pivot,4)
        rod('RimLink'+suffix+str(i),endpoint,(0,.438*math.cos(a),.438*math.sin(a)),.008,silver,pivot,4)
    empty('SpokeMark'+suffix,(0,.4,0),pivot)

rearhub=(0,-.85,.5)
seat=(0,-.32,1.04)
bottom=(0,-.1,.52)
head=(0,.53,1.04)
for i,(a,b) in enumerate([(rearhub,seat),(seat,bottom),(bottom,rearhub),(seat,head),(bottom,head)]):
    rod('FrameTube'+str(i),a,b,.029,turquoise)
for x in [-.065,.065]:
    rod('Fork'+str(x),(x,.53,1.04),(x,.85,.5),.023,turquoise)
rod('SeatPost',(0,-.32,1.02),(0,-.40,1.20),.023,silver)
box('Saddle',(0,-.42,1.215),(.27,.27,.055),wing)
rod('HandleStem',(0,.53,1.04),(0,.64,1.36),.026,turquoise)
rod('Handlebar',(-.235,.64,1.36),(.235,.64,1.36),.026,turquoise)
rod('CrankAxle',(-.22,0,0),(.22,0,0),.035,silver,crank)
for side,x,y in [('Left',-.2,.2),('Right',.2,-.2)]:
    rod('CrankArm'+side,(x,0,0),(x,y,0),.021,orange,crank)
    box('Pedal'+side,(x,y,0),(.10,.13,.035),silver,crank)

ellipsoid('PelicanBody',(0,-.34,1.55),(.25,.405,.315),white)
ellipsoid('Breast',(0,-.09,1.53),(.22,.22,.25),white)
ellipsoid('Tail',(0,-.77,1.53),(.14,.235,.095),white)
for x in [-.225,.225]:
    ellipsoid('FoldedWing'+('Left' if x<0 else 'Right'),(x,-.34,1.57),(.035,.335,.20),wing)
neck=ellipsoid('Neck',(0,-.035,1.695),(.115,.13,.215),white)
neck.rotation_euler.x=-.55
ellipsoid('PelicanHead',(0,.075,1.79),(.17,.19,.17),white)
for x in [-.153,.153]:
    ellipsoid('Eye'+('Left' if x<0 else 'Right'),(x,.145,1.835),(.023,.023,.028),black)

def bill_part(name,sections,material):
    verts=[]
    faces=[]
    for y,z,w,h in sections:
        verts.extend([(-w,y,z),(0,y,z+h),(w,y,z),(0,y,z-h)])
    faces.append((3,2,1,0))
    for i in range(len(sections)-1):
        for j in range(4):
            faces.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
    s=4*(len(sections)-1)
    faces.append((s,s+1,s+2,s+3))
    return mesh(name,verts,faces,material)
bill_part('Beak',[(.20,1.775,.105,.035),(.51,1.78,.105,.036),(.82,1.765,.065,.021),(1.02,1.75,.003,.004)],orange)
bill_part('Pouch',[(.20,1.715,.087,.055),(.43,1.685,.09,.09),(.68,1.70,.065,.055),(.94,1.74,.003,.005)],pouchmat)

# A horizontal carrier deck connected to the bicycle by rails and axle stays.
box('DockPlate',(0,-1.2,1.10),(.36,.34,.04),turquoise)
empty('DockSocket',(0,-1.2,1.12))
for x in [-.15,.15]:
    rod('RackRail'+str(x),(x,-1.35,1.065),(x,-.42,1.065),.018,turquoise)
    rod('RackSeatTie'+str(x),(x,-.42,1.065),(0,-.32,1.04),.018,turquoise)
    rod('RackStay'+str(x),(x,-1.32,1.08),(x,-.85,.5),.018,silver)
    rod('RackAxleTie'+str(x),(x,-.85,.5),(0,-.85,.5),.018,silver)

legs=[]
for side,x in [('Left',-.15),('Right',.15)]:
    hip=empty('Hip'+side,(x,-.28,1.45))
    knee=empty('Knee'+side,(0,0,0))
    foot=ellipsoid('Foot'+side,(0,0,0),(.06,.145,.033),orange)
    thigh=rod('Thigh'+side,(0,0,0),(0,0,.65),.033,orange)
    shin=rod('Shin'+side,(0,0,0),(0,0,.65),.026,orange)
    legs.append((side,hip,knee,foot,thigh,shin))

animated=set()
def key(o,prop,frame):
    o.keyframe_insert(data_path=prop,frame=frame)
    animated.add(o)

def pose_rod(o,a,b,frame):
    o.location=(a+b)*.5
    q=(b-a).to_track_quat('Z','Y')
    if o.rotation_quaternion.dot(q)<0:
        q.negate()
    o.rotation_quaternion=q
    key(o,'location',frame)
    key(o,'rotation_quaternion',frame)

for frame in range(49):
    theta=2*math.pi*frame/48
    for wheel in [front,rear]:
        wheel.rotation_euler=(2*theta,0,0)
        key(wheel,'rotation_euler',frame)
    crank.rotation_euler=(theta,0,0)
    key(crank,'rotation_euler',frame)
    for side,hip,knee,foot,thigh,shin in legs:
        left=side=='Left'
        pedal=bpy.data.objects['Pedal'+side]
        pedal.rotation_euler=(-theta,0,0)
        key(pedal,'rotation_euler',frame)
        x=-.2 if left else .2
        r=.2 if left else -.2
        f=Vector((x,-.1+r*math.cos(theta),.52+r*math.sin(theta)+.035))
        h=hip.location.copy()
        delta=f-h
        distance=delta.length
        axis=delta.normalized()
        bend=Vector((0,1,0))
        bend=(bend-axis*bend.dot(axis)).normalized()
        k=(h+f)*.5+bend*math.sqrt(max(0,.65**2-distance**2/4))
        knee.location=k
        foot.location=f
        key(knee,'location',frame)
        key(foot,'location',frame)
        pose_rod(thigh,h,k,frame)
        pose_rod(shin,k,f,frame)

for o in animated:
    action=o.animation_data.action
    action.name=o.name+'_Ride'
    for fc in action.fcurves:
        for point in fc.keyframe_points:
            point.interpolation='LINEAR'
    track=o.animation_data.nla_tracks.new()
    track.name='Ride'
    strip=track.strips.new('Ride',0,action)
    strip.action_frame_start=0
    strip.action_frame_end=48
    strip.frame_start=0
    strip.frame_end=48
    o.animation_data.action=None

for o in scene.objects:
    if o.type=='MESH':
        for polygon in o.data.polygons:
            polygon.use_smooth=False
triangles=sum(len(p.vertices)-2 for o in scene.objects if o.type=='MESH' for p in o.data.polygons)
assert triangles<=2800,triangles
for frame in range(49):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    for o in scene.objects:
        if o.type=='MESH':
            for v in o.data.vertices:
                p=o.matrix_world@v.co
                assert abs(p.x)<=.265001,(o.name,frame,p.x)
                assert p.z<=1.970001,(o.name,frame,p.z)
for name,minimum in [('PelicanHead',.02),('Beak',.008),('PelicanBody',.15)]:
    o=bpy.data.objects[name]
    assert o.dimensions.x*o.dimensions.y*o.dimensions.z>minimum,name
scene.frame_set(0)
bpy.context.view_layer.update()
os.makedirs('/output',exist_ok=True)
bpy.ops.export_scene.gltf(filepath='/output/asset.glb',export_format='GLB',export_yup=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_nla_strips=True,export_frame_range=True,export_force_sampling=True,export_cameras=False,export_lights=False)
