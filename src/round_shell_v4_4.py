"""Continuous radial shell, textured from the accepted Rodin surface per texel.
Per-texel barycentric sampling avoids drawing across source UV atlas islands.
"""
import bpy,math,numpy as np,hashlib,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

def make_shell(source,source_image,materials,out):
 source.calc_loop_triangles();tris=[(tuple(t.vertices),tuple(t.loops)) for t in source.loop_triangles]
 points=[v.co.copy() for v in source.vertices];tree=BVHTree.FromPolygons(points,[t[0] for t in tris],all_triangles=True)
 source_uv=[Vector((*x.uv,0)) for x in source.uv_layers.active.data];center=Vector((0,0,1.22));radius=.99
 theta=np.r_[np.linspace(0,.65,26),np.linspace(.65,math.pi,39)[1:]];N=80
 def shape(t,p):
  x=radius*math.sin(t)*math.cos(p);z=1.22+radius*math.sin(t)*math.sin(p);y=-radius*math.cos(t)
  if t<.85:
   hit,_,_,_=tree.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
   if hit:
    w=max(0,min(1,(.85-t)/.20));w=w*w*(3-2*w);y=y*(1-w)+hit.y*w
  return (x,y,z)
 verts=[shape(t,i*math.tau/N) for t in theta for i in range(N+1)];faces=[]
 # Smooth depth-only sampling noise around the recessed face. The source fur
 # geometry contains fine spikes; they must not become large lip-edge teeth.
 grid=np.array(verts).reshape(len(theta),N+1,3)
 for iteration in range(8):
  old=grid[:,:,1].copy()
  for row in range(1,len(theta)-1):
   if theta[row]>.70:continue
   weight=.55*max(0,min(1,(.70-theta[row])/.10))
   for col in range(N):
    average=(old[row-1,col]+old[row+1,col]+old[row,(col-1)%N]+old[row,(col+1)%N])/4
    grid[row,col,1]=old[row,col]*(1-weight)+average*weight
  grid[:,-1]=grid[:,0]
 # Broad continuous groom variation, below 1% of the radius: rounded silhouette.
 for row,t in enumerate(theta):
  w=max(0,min(1,(t-.70)/.50))
  for col in range(N+1):
   p=col*math.tau/N;d=grid[row,col]-np.array([0,0,1.22]);d*=1+w*(.006*math.cos(8*p+.3)+.003*math.cos(13*p))*math.sin(t)**4;grid[row,col]=np.array([0,0,1.22])+d
 verts=grid.reshape(-1,3).tolist()
 for row in range(len(theta)-1):
  for col in range(N):
   a=row*(N+1)+col
   if row>0:faces.append((a,a+1,a+N+1))
   if row<len(theta)-2:faces.append((a+1,a+N+2,a+N+1))
 mesh=bpy.data.meshes.new('hanhan_continuous_round_shell');mesh.from_pydata(verts,[],faces);mesh.update();uv=mesh.uv_layers.new(name='UVMap')
 for p in mesh.polygons:
  p.use_smooth=True;p.material_index=3
  for j in p.loop_indices:
   index=mesh.loops[j].vertex_index;row,col=divmod(index,N+1);uv.data[j].uv=(col/N,row/(len(theta)-1))
 for m in materials:mesh.materials.append(m)
 material=bpy.data.materials.new('radial_fur_shell');material.use_nodes=True;nt=material.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.82
 w,h=1024,512;image_path=out/'hanhan_rodin_v4_4_shell_color.png';cache=out/'hanhan_rodin_v4_4_shell_cache.json'
 sw,sh=source_image.size;pixels=np.array(source_image.pixels[:],dtype=np.float32).reshape(sh,sw,4);digest=hashlib.sha256(pixels.tobytes()+b'round_shell_clean_arm_3').hexdigest()
 if image_path.exists() and cache.exists() and json.loads(cache.read_text()).get('source')==digest:
  image=bpy.data.images.load(str(image_path),check_existing=False)
 else:
  def color_at(t,p):
   if t<.85:
    pos=shape(t,p);origin=Vector((pos[0],-3,pos[2]));direction=Vector((0,1,0))
   else:
    direction=Vector((math.sin(t)*math.cos(p),-math.cos(t),math.sin(t)*math.sin(p)))
    # Sample intact upper fur for the small T-pose arm/boot zones; blend below.
    origin=center+direction*3;direction=-direction
   hit,normal,index,distance=tree.ray_cast(origin,direction)
   if hit is None:return np.array([.018,.04,.34,1])
   ids,loops=tris[index];coord=barycentric_transform(hit,*(points[j] for j in ids),*(source_uv[j] for j in loops));x=min(sw-1,max(0,coord.x*(sw-1)));y=min(sh-1,max(0,coord.y*(sh-1)));ix,iy=int(x),int(y);dx,dy=x-ix,y-iy
   return pixels[iy,ix]*(1-dx)*(1-dy)+pixels[iy,min(ix+1,sw-1)]*dx*(1-dy)+pixels[min(iy+1,sh-1),ix]*(1-dx)*dy+pixels[min(iy+1,sh-1),min(ix+1,sw-1)]*dx*dy
  result=np.empty((h,w,4),dtype=np.float32)
  for row in range(h):
   t=float(np.interp(row/(h-1),np.linspace(0,1,len(theta)),theta))
   for col in range(w):
    p=col/(w-1)*math.tau;x,y,z=shape(t,p);c=color_at(t,p)
    # Feather material reconstruction around removed arms and boots.
    side=max(0,min(1,(.53-abs(y))/.18))*max(0,min(1,(.62-abs(z-1.19))/.22))*max(0,min(1,(abs(x)-.65)/.20))
    bottom=max(0,min(1,(.43-z)/.14))
    blend=max(side,bottom);blend=blend*blend*(3-2*blend)
    if blend>0:
     # Same azimuthal flow, no pink limb pixels or yellow boots on the body.
     replacement=color_at(t,(.70+(z-1.22)*.5) if x>=0 else math.pi-(.70+(z-1.22)*.5)) if side>=bottom else color_at(1.15,.65+x*.18);c=c*(1-blend)+replacement*blend
    if t<.60 and abs(x)<.33 and z<1.10 and c[0]>.15 and c[2]<c[0]*.85:
     pink_weight=max(0,min(1,(z-1.076)/.014));pink_weight=pink_weight*pink_weight*(3-2*pink_weight);c=c*pink_weight+np.array([.014,.025,.24,1])*(1-pink_weight)
    result[row,col]=c;result[row,col,3]=1
   if row%64==0:print('SHELL_TEXTURE_ROW',row,flush=True)
  image=bpy.data.images.new('hanhan_v4_4_radial_fur',width=w,height=h,alpha=False);image.pixels.foreach_set(result.ravel());image.filepath_raw=str(image_path);image.file_format='PNG';image.save();cache.write_text(json.dumps({'source':digest}))
 image.pack();tex=nt.nodes.new('ShaderNodeTexImage');tex.image=image;nt.links.new(tex.outputs['Color'],bs.inputs['Base Color']);mesh.materials.append(material)
 # Weld only duplicate pole/seam positions. Loop UVs remain independent.
 import bmesh
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 return mesh,material
