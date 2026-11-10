"""Conservative cylinder recovery to avoid using a QEM skinny-feature artifact as difficulty."""
import math
import numpy as np
import trimesh

def cylinder_fit(mesh,tolerance):
 v=np.unique(np.asarray(mesh.vertices),axis=0);center=v.mean(0);_,_,axes=np.linalg.svd(v-center,full_matrices=False)
 for axis in axes:
  axial=(v-center)@axis;levels=np.unique(np.round(axial,8))
  if len(levels)!=2:continue
  radial=v-center-axial[:,None]*axis;r=np.linalg.norm(radial,axis=1);radius=float(r.max());ring=r>radius*.5
  if radius<=0 or np.count_nonzero(ring)<24 or np.std(r[ring])>max(1e-8,radius*1e-6):continue
  if np.any((r>radius*1e-5)&(~ring)):continue
  height=float(np.ptp(axial));helper=np.eye(3)[np.argmin(abs(axis))];u=np.cross(axis,helper);u/=np.linalg.norm(u);w=np.cross(axis,u)
  directions=np.arctan2(radial[ring]@w,radial[ring]@u);segments=len(np.unique(np.round(directions,7)))
  if segments<12:continue
  error=max(1e-8,tolerance*.3);angle=math.acos(max(-1.,min(1.,1-error/radius)));n=max(8,min(segments,math.ceil(math.pi/max(angle,1e-6))))
  transform=np.eye(4);transform[:3,:3]=np.column_stack([u,w,axis]);transform[:3,3]=center
  return trimesh.creation.cylinder(radius,height,sections=n,transform=transform)
 return None
