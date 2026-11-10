"""Exact convex partition of a simple 2D reference polygon; no subject labels."""
import numpy as np
from scipy.spatial import ConvexHull

def area(points):return abs(float(np.dot(points[:,0],np.roll(points[:,1],-1))-np.dot(points[:,1],np.roll(points[:,0],-1))))/2

def partition(points,max_vertices=32):
 points=np.asarray(points,dtype=float);remaining=list(range(len(points)));polygons=[]
 def cross(a,b):return a[0]*b[1]-a[1]*b[0]
 while len(remaining)>3:
  for k,b in enumerate(remaining):
   a=remaining[k-1];c=remaining[(k+1)%len(remaining)];A,B,C=points[[a,b,c]]
   if cross(B-A,C-B)<=1e-12:continue
   others=[p for p in remaining if p not in [a,b,c]];q=points[others]
   inside=((B[0]-A[0])*(q[:,1]-A[1])-(B[1]-A[1])*(q[:,0]-A[0])>=-1e-12)&((C[0]-B[0])*(q[:,1]-B[1])-(C[1]-B[1])*(q[:,0]-B[0])>=-1e-12)&((A[0]-C[0])*(q[:,1]-C[1])-(A[1]-C[1])*(q[:,0]-C[0])>=-1e-12)
   if np.any(inside):continue
   polygons.append([a,b,c]);remaining.pop(k);break
  else:raise ValueError('Reference polygon could not be triangulated')
 polygons.append(remaining)
 while True:
  edges={};choices=[]
  for i,poly in enumerate(polygons):
   for a,b in zip(poly,poly[1:]+poly[:1]):edges.setdefault(tuple(sorted([a,b])),[]).append(i)
  for edge,owners in edges.items():
   if len(owners)!=2:continue
   i,j=owners;merged=sorted(set(polygons[i]+polygons[j]))
   if len(merged)>max_vertices:continue
   h=ConvexHull(points[merged]);poly=[merged[k] for k in h.vertices]
   if abs(h.volume-area(points[polygons[i]])-area(points[polygons[j]]))>1e-10:continue
   choices.append((float(np.linalg.norm(points[edge[1]]-points[edge[0]])),i,j,poly))
  if not choices:break
  _,i,j,poly=max(choices,key=lambda x:x[0]);polygons[i]=poly;polygons.pop(j)
 return [points[p] for p in polygons]
