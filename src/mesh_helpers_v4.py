import bpy, math
from mathutils import Vector
class Mesh:
 def __init__(self,name,materials):self.name=name;self.materials=materials;self.v=[];self.f=[];self.mi=[];self.uv=[];self.colors=[];self.weights=[]
 def add(self,vs,fs,mat,bone,color=(1,1,1,1),uv=None):
  start=len(self.v);self.v.extend([tuple(p) for p in vs]);self.f.extend([tuple(start+i for i in f) for f in fs]);self.mi.extend([mat]*len(fs));self.uv.extend(uv or [(0,0)]*len(vs));self.colors.extend([color]*len(vs));self.weights.extend([bone]*len(vs));return list(range(start,len(self.v)))
 def sphere(self,c,s,mat,bone,color=(1,1,1,1),seg=20,rings=12,transform=None):
  vs=[];uv=[];fs=[]
  for j in range(rings+1):
   th=math.pi*j/rings
   for i in range(seg+1):
    ph=2*math.pi*i/seg;p=Vector((s[0]*math.sin(th)*math.cos(ph),s[1]*math.sin(th)*math.sin(ph),s[2]*math.cos(th)))
    if transform:p=transform@p
    vs.append(Vector(c)+p);uv.append((i/seg,1-j/rings))
  for j in range(rings):
   for i in range(seg):
    a=j*(seg+1)+i
    if j>0:fs.append((a,a+seg+1,a+1))
    if j<rings-1:fs.append((a+1,a+seg+1,a+seg+2))
  return self.add(vs,fs,mat,bone,color,uv)
 def capsule(self,a,b,r,mat,bone,color=(1,1,1,1),seg=12,rings=8):
  a=Vector(a);b=Vector(b);rot=Vector((0,0,1)).rotation_difference(b-a).to_matrix()
  return self.sphere((a+b)/2,(r,r,(b-a).length/2),mat,bone,color,seg,rings,rot)
 def tube(self,pts,r,mat,bone,color=(1,1,1,1),sides=6):
  vs=[];fs=[]
  for j,p in enumerate(pts):
   p=Vector(p);t=Vector(pts[min(j+1,len(pts)-1)])-Vector(pts[max(j-1,0)]);t.normalize();a=t.cross(Vector((0,1,0)));a.normalize();b=t.cross(a)
   for k in range(sides):vs.append(p+r*(a*math.cos(k*math.tau/sides)+b*math.sin(k*math.tau/sides)))
  for j in range(len(pts)-1):
   for k in range(sides):a=j*sides+k;b=j*sides+(k+1)%sides;fs.append((a,b,b+sides,a+sides))
  return self.add(vs,fs,mat,bone,color)
 def finish(self):
  me=bpy.data.meshes.new(self.name);me.from_pydata(self.v,[],self.f);me.update();ob=bpy.data.objects.new(self.name,me);COL.objects.link(ob)
  for m in self.materials:me.materials.append(m)
  uv=me.uv_layers.new(name='UVMap');color=me.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='POINT')
  for i,c in enumerate(self.colors):color.data[i].color=c
  for p in me.polygons:
   p.material_index=self.mi[p.index];p.use_smooth=True
   for loop in p.loop_indices:uv.data[loop].uv=self.uv[me.loops[loop].vertex_index]
  for bone in set(self.weights):g=ob.vertex_groups.new(name=bone);g.add([i for i,n in enumerate(self.weights) if n==bone],1,'REPLACE')
  mod=ob.modifiers.new('deform','ARMATURE');mod.object=rig;ob.parent=rig
  return ob

