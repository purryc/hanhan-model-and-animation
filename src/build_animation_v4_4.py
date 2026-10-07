"""Rodin-based v4: editable rig, independent face, authored state actions."""
import bpy, math, json, sys, shutil, os
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Euler
B=Path(__file__).resolve().parents[1];O=B/'output';Q=B/'qa/v4_4';Q.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(B/'src'))
bpy.ops.wm.open_mainfile(filepath=str(O/'hanhan_rodin_v4_t_pose.blend'));scene=bpy.context.scene;scene.render.fps=30
body=bpy.data.objects['hanhan_rodin_v4_t_pose'];body.name='hanhan_rodin_body'
COL=bpy.data.collections.new('HANHAN_RODIN_V4');scene.collection.children.link(COL)
for c in list(body.users_collection):c.objects.unlink(body)
COL.objects.link(body)
def material(name,color,vertex=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.65
 if vertex:
  a=m.node_tree.nodes.new('ShaderNodeVertexColor');a.layer_name='Color';m.node_tree.links.new(a.outputs['Color'],p.inputs['Base Color'])
 return m
pink=material('face_skin',(.92,.32,.48));ink=material('expression_palette',(.008,.01,.025),True)
body.data.materials.append(pink)
cap_material=material('cut_surface_palette',(.02,.04,.4),True);body.data.materials.append(cap_material)
# Reuse the original recessed face surface, removing baked static eyes/mouth.
# Smooth vertex mask replaces the baked expression without a polygonal face border.
mask=body.data.color_attributes.new(name='face_paint',type='FLOAT_COLOR',domain='POINT')
def ss(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for v in body.data.vertices:
 x,y,z=v.co;w=ss(-.64,-.585,y)*(1-ss(-.46,-.40,y))*(1-ss(.245,.305,abs(x)))*ss(1.035,1.085,z)*(1-ss(1.435,1.49,z));mask.data[v.index].color=(w,w,w,1)
nt=body.data.materials[0].node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');old=bs.inputs['Base Color'].links[0].from_socket
vc=nt.nodes.new('ShaderNodeVertexColor');vc.layer_name='face_paint';mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[2].default_value=(.92,.32,.48,1);nt.links.new(old,mix.inputs[1]);nt.links.new(vc.outputs['Color'],mix.inputs[0]);nt.links.new(mix.outputs[0],bs.inputs['Base Color'])
arm_mask=body.data.color_attributes.new(name='arm_cleanup',type='FLOAT_COLOR',domain='POINT')
for v in body.data.vertices:
 x,y,z=v.co;w=ss(.76,.82,abs(x))*(1-ss(1.07,1.105,abs(x)))*(1-ss(.30,.36,abs(y)))*ss(.84,.90,z)*(1-ss(1.45,1.52,z));arm_mask.data[v.index].color=(w,w,w,1)
av=nt.nodes.new('ShaderNodeVertexColor');av.layer_name='arm_cleanup';arm_mix=nt.nodes.new('ShaderNodeMixRGB');arm_mix.inputs[2].default_value=(.014,.024,.24,1);nt.links.new(mix.outputs[0],arm_mix.inputs[1]);nt.links.new(av.outputs['Color'],arm_mix.inputs[0]);mix=arm_mix
# Replace only pink wrist pixels; preserve the original blue fur around the seam.
sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(old,sep.inputs[0]);diff=nt.nodes.new('ShaderNodeMath');diff.operation='DIVIDE';nt.links.new(sep.outputs[0],diff.inputs[0]);nt.links.new(sep.outputs[2],diff.inputs[1]);pink_test=nt.nodes.new('ShaderNodeMapRange');pink_test.inputs['From Min'].default_value=.16;pink_test.inputs['From Max'].default_value=.32;nt.links.new(diff.outputs[0],pink_test.inputs['Value']);mask_mul=nt.nodes.new('ShaderNodeMath');mask_mul.operation='MULTIPLY';nt.links.new(av.outputs['Color'],mask_mul.inputs[0]);nt.links.new(pink_test.outputs[0],mask_mul.inputs[1]);nt.links.new(mask_mul.outputs[0],arm_mix.inputs[0])
# Bake this local face cleanup into a new export texture. Keep the provider original intact.
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
baked=bpy.data.images.new('hanhan_v4_color',width=1024,height=1024,alpha=False);target=nt.nodes.new('ShaderNodeTexImage');target.image=baked;nt.nodes.active=target
output=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL');em=nt.nodes.new('ShaderNodeEmission');nt.links.new(mix.outputs[0],em.inputs['Color']);nt.links.new(em.outputs[0],output.inputs['Surface'])
scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=8;bpy.ops.object.bake(type='EMIT')
nt.links.new(bs.outputs[0],output.inputs['Surface']);nt.links.new(target.outputs['Color'],bs.inputs['Base Color']);baked.filepath_raw=str(O/'hanhan_rodin_v4_4_color.png');baked.file_format='PNG';baked.save();baked.pack()
for im in bpy.data.images:
 if 'normal' in im.name and im.size[0]>512:im.scale(512,512);im.pack()
for attr in list(body.data.color_attributes):body.data.color_attributes.remove(attr)
# Separate the generated wrist bridge; preserve Rodin hands, close the body shell.
import bmesh
original_mesh=body.data.copy();hand_parts=[]
def fur_uv(point):
 # Use one continuous, inspected fur-only atlas island. Ray-projecting each corner
 # independently crossed UV islands and sampled black atlas padding inside caps.
 return Vector((.49+point.y*.15,.60+(point.z-1.2)*.20))
def cut_mesh(mesh,plane,normal,outer,color=(.014,.024,.24,1)):
 bm=bmesh.new();bm.from_mesh(mesh);result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=Vector(plane),plane_no=Vector(normal),clear_outer=outer,clear_inner=not outer)
 boundary=[e for e in result['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
 if boundary:
  layer=bm.loops.layers.float_color.get('Color')
  if layer is None:
   layer=bm.loops.layers.float_color.new('Color')
   for f in bm.faces:
    for loop in f.loops:loop[layer]=(1,1,1,1)
  caps=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces']
  if abs(normal[0])>0 and color[0]<.1:
   poked=bmesh.ops.poke(bm,faces=caps);caps=poked['faces']
   for v in poked['verts']:
    x,y,z=v.co;v.co.x=math.copysign(.995*math.sqrt(max(.1,1-(y/.98)**2-((z-1.22)/1.08)**2)),x)
  for f in caps:
   f.material_index=2
   for loop in f.loops:loop[layer]=color
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
for side,sign in [('l',1),('r',-1)]:
 mesh=original_mesh.copy();cut_mesh(mesh,(sign*1.105,0,0),(sign,0,0),False,(.95,.46,.58,1));
 for v in mesh.vertices:
  taper=ss(1.105,1.235,abs(v.co.x));v.co.y*=.52+.48*taper;v.co.z=1.17+(v.co.z-1.17)*(.43+.57*taper)
 ob=bpy.data.objects.new('rodin_hand_'+side,mesh);COL.objects.link(ob);g=ob.vertex_groups.new(name='part_hand_'+side);g.add(list(range(len(mesh.vertices))),1,'REPLACE');hand_parts.append(ob)
from round_shell_v4_4 import make_shell
body.data,shell_material=make_shell(original_mesh,baked,list(body.data.materials),O)
# Extract only the yellow boots, never the blue body bridge above them.
for side,sign in [('l',1),('r',-1)]:
 mesh=original_mesh.copy();cut_mesh(mesh,(0,0,.218),(0,0,1),True,(1,.58,.025,1));cut_mesh(mesh,(0,0,0),(sign,0,0),False,(1,.58,.025,1))
 
 for v in mesh.vertices:
  if v.co.z>.12:v.co.z=.12+(v.co.z-.12)*2.04
 ob=bpy.data.objects.new('rodin_boot_'+side,mesh);COL.objects.link(ob);g=ob.vertex_groups.new(name='part_foot_'+side);g.add(list(range(len(mesh.vertices))),1,'REPLACE');hand_parts.append(ob)
for part in hand_parts:
 bpy.context.view_layer.objects.active=part;dec=part.modifiers.new('limb_mobile_budget','DECIMATE');dec.ratio=.80;bpy.ops.object.modifier_apply(modifier=dec.name)
g=body.vertex_groups.new(name='part_body');g.add(list(range(len(body.data.vertices))),1,'REPLACE')
bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
for ob in hand_parts:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
# Preserve semantic membership through decimation; no coordinate-based reclassification.
dec=body.modifiers.new('final_mobile_budget','DECIMATE');dec.ratio=1.0;bpy.ops.object.modifier_apply(modifier=dec.name)
for polygon in body.data.polygons:polygon.use_smooth=True
body.data.normals_split_custom_set([(0,0,0)]*len(body.data.loops))
parts_by_vertex={v.index:next(body.vertex_groups[g.group].name for g in v.groups if body.vertex_groups[g.group].name.startswith('part_') and g.weight>.5) for v in body.data.vertices}
arm=bpy.data.armatures.new('hanhan_v4_skeleton');rig=bpy.data.objects.new('hanhan_rig',arm);COL.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT');origins={}
def bone(n,h,t=None,parent=None):
 b=arm.edit_bones.new(n);b.inherit_scale='NONE';b.head=h;b.tail=t if t else Vector(h)+Vector((0,0,.1));origins[n]=Vector(h)
 if parent:b.parent=arm.edit_bones[parent]
 return b
bone('root',(0,0,0));bone('body',(0,0,1.18),parent='root');bone('head',(0,0,1.24),parent='body')
for side,s in [('l',1),('r',-1)]:
 bone('eye_'+side,(s*.10,-.575,1.25),parent='head')
 bone('arm_'+side,(s*.67,0,1.17),(s*.85,0,1.17),'body');bone('forearm_'+side,(s*.85,0,1.17),(s*1.105,0,1.17),'body');bone('hand_'+side,(s*1.105,0,1.17),(s*1.28,0,1.17),'body')
 for j,(h,t,end) in enumerate([((1.19,0,1.27),(1.235,0,1.37),(1.25,0,1.455)),((1.29,0,1.265),(1.40,0,1.28),(1.48,0,1.29)),((1.30,0,1.16),(1.405,0,1.16),(1.48,0,1.16)),((1.29,0,1.065),(1.395,0,1.035),(1.45,0,1.015))]):
  h=Vector((s*h[0],h[1],h[2]));t=Vector((s*t[0],t[1],t[2]));end=Vector((s*end[0],end[1],end[2]));bone(f'finger{j}_a_{side}',h,t,'hand_'+side);bone(f'finger{j}_b_{side}',t,end,f'finger{j}_a_{side}')
 bone('leg_'+side,(s*.18,0,.4),(s*.18,0,.23),'root');bone('foot_'+side,(s*.18,-.015,.17),(s*.18,-.2,.06),'root')
for n in ['magnifier','pencil','clipboard','monocle','bell','cuff_l','cuff_r']:bone('prop_'+n+'_bone',(0,0,0),parent='root')
for i in range(8):
 angle=math.tau*i/8+math.pi/8;bone(f'fur_{i}',(.52*math.cos(angle),-.66,1.22+.52*math.sin(angle)),(.94*math.cos(angle),-.30,1.22+.94*math.sin(angle)),parent='body')
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
for b in rig.pose.bones:b.rotation_mode='QUATERNION'
rest={b.name:b.matrix_local.copy() for b in arm.bones}
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def segdist(p,a,b):
 d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));return (p-a-t*d).length,t
# Continuous skin weights preserve the actual Rodin hand mesh and separated digits.
groups={b.name:body.vertex_groups.new(name=b.name) for b in arm.bones}
for v in body.data.vertices:
 x,y,z=v.co;ax=abs(x);part=parts_by_vertex[v.index];side=part[-1];w={}
 if part.startswith('part_hand_'):
  thumb=smooth(1.28,1.39,z)*(1-smooth(1.27,1.35,ax));finger=smooth(1.30,1.445,ax)*(1-thumb)
  w={'hand_'+side:1-thumb-finger}
  distances=[segdist(v.co,origins[f'finger{j}_a_{side}'],arm.bones[f'finger{j}_b_{side}'].tail_local)[0] for j in range(1,4)]
  soft=[math.exp(-d*d/(2*.038**2)) for d in distances];total_soft=max(1e-12,sum(soft))
  for j,factor in [(0,thumb)]+[(j,finger*soft[j-1]/total_soft) for j in range(1,4)]:
   a=origins[f'finger{j}_a_{side}'];dist,t=segdist(v.co,a,arm.bones[f'finger{j}_b_{side}'].tail_local);second=smooth(.44,.82,t)
   w[f'finger{j}_a_{side}']=factor*(1-second);w[f'finger{j}_b_{side}']=factor*second
 elif part.startswith('part_foot_'):
  w={'foot_'+side:1}
 else:
  d=v.co-Vector((0,0,1.22));theta=math.acos(max(-1,min(1,-d.y/max(d.length,.001))))
  amount=.82*smooth(.62,1.10,theta)*(1-.45*smooth(2.3,math.pi,theta))
  phase=((math.atan2(d.z,d.x)-math.pi/8)%math.tau)/math.tau*8;lo=int(phase)%8;f=phase-int(phase);f=f*f*(3-2*f)
  w={'body':1-amount,f'fur_{lo}':amount*(1-f),f'fur_{(lo+1)%8}':amount*f}
 total=sum(w.values())
 for n,a in w.items():
  if a>1e-6:groups[n].add([v.index],a/total,'REPLACE')
for group in list(body.vertex_groups):
 if group.name.startswith('part_'):body.vertex_groups.remove(group)
mod=body.modifiers.new('skeletal_deformation','ARMATURE');mod.object=rig;body.parent=rig
import mesh_helpers_v4 as mh
mh.COL=COL;mh.rig=rig;Mesh=mh.Mesh
limb_material=cap_material;limbs=Mesh('hanhan_limbs',[limb_material])
# One continuous arm surface per side, blending elbow and wrist joints.
arm_weights={}
for side,sign in [('l',1),('r',-1)]:
 vs=[];fs=[];segments=12;xs=[.60,.67,.76,.81,.85,.89,.95,1.02,1.07,1.105,1.14]
 for x in xs:
  radius=.061 if x<1.02 else .056
  for j in range(segments):
   angle=math.tau*j/segments;vs.append((sign*x,radius*math.sin(angle),1.17+radius*math.cos(angle)))
 for ring in range(len(xs)-1):
  for j in range(segments):
   a=ring*segments+j;b=ring*segments+(j+1)%segments;fs.append((a,b,b+segments,a+segments) if sign>0 else (a,a+segments,b+segments,b))
 fs.extend([tuple(reversed(range(segments))),tuple((len(xs)-1)*segments+j for j in range(segments))])
 ids=limbs.add(vs,fs,0,'forearm_'+side,(.95,.46,.58,1))
 for idx,co in zip(ids,vs):
  x=abs(co[0]);hand=smooth(1.015,1.12,x);fore=smooth(.78,.92,x)
  arm_weights[idx]={'arm_'+side:(1-fore)*(1-hand),'forearm_'+side:fore*(1-hand),'hand_'+side:hand}
limb_mesh=limbs.finish()
for group in list(limb_mesh.vertex_groups):limb_mesh.vertex_groups.remove(group)
for idx,weights in arm_weights.items():
 for name,w in weights.items():
  if w>0:
   group=limb_mesh.vertex_groups.get(name) or limb_mesh.vertex_groups.new(name=name);group.add([idx],w,'REPLACE')
# Hair is the continuous outer shell, with broad smooth guide weights.
# No separate spikes, rods, cards or glued-on tufts.
bpy.ops.object.select_all(action='DESELECT')
for ob in [body,limb_mesh]:ob.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join();limb_mesh=None
fac=Mesh('hanhan_expression',[ink]);DARK=(.004,.005,.012,1);WHITE=(1,.96,.90,1);parts=[]
for side,s in [('l',1),('r',-1)]:
 c=np.array([s*.10,-.579,1.25]);regular=fac.sphere(c,(.042,.021,.055),0,'eye_'+side,DARK,seg=16,rings=10)
 regular+=fac.sphere(c+[-.011,-.019,.018],(.010,.005,.012),0,'eye_'+side,WHITE,seg=8,rings=5)
 def stroke(points):return fac.tube([c+np.array(p) for p in points],.0075,0,'eye_'+side,DARK,sides=5)
 happy=stroke([(x,0,.027*math.cos(x/.043*math.pi/2)) for x in np.linspace(-.043,.043,10)])
 squeeze=stroke([(s*.036,0,.029),(-s*.018,0,0),(s*.036,0,-.029)])
 spiral=stroke([(.042*t*math.cos(t*math.pi*4.5),-.006,.045*t*math.sin(t*math.pi*4.5)) for t in np.linspace(.10,1,32)])
 parts.append((c,regular,happy,squeeze,spiral))
mc=np.array([0,-.574,1.153]);mouth=fac.sphere(mc,(.029,.012,.009),0,'head',DARK,seg=18,rings=8)
for s in [-1,1]:fac.sphere((s*.205,-.558,1.15),(.032,.008,.021),0,'head',(1,.25,.37,1),seg=10,rings=5)
face=fac.finish();face.shape_key_add(name='Basis');full=np.array(fac.v);base=full.copy()
for c,regular,happy,squeeze,spiral in parts:
 for ids in [happy,squeeze,spiral]:base[ids]=c+(full[ids]-c)*.001
for v,p in zip(face.data.vertices,base):v.co=p
for v,p in zip(face.data.shape_keys.key_blocks['Basis'].data,base):v.co=p
for name in ['blink','happy','squeeze','spiral','mouth_open','mouth_round','mouth_smile','mouth_frown','viseme_a','viseme_e','viseme_i','viseme_o','viseme_u']:
 arr=base.copy()
 for c,regular,happy,squeeze,spiral in parts:
  if name=='blink':arr[regular,2]=c[2]+(arr[regular,2]-c[2])*.07
  if name in ['happy','squeeze','spiral']:
   arr[regular]=c+(full[regular]-c)*.001;chosen={'happy':happy,'squeeze':squeeze,'spiral':spiral}[name];arr[chosen]=full[chosen]
 if name.startswith(('mouth_','viseme_')):
  for i in mouth:
   x,y,z=base[i]-mc
   if name=='mouth_open':z*=5;x*=1.15
   if name=='mouth_round':z*=3.7;x*=.8
   if name=='mouth_smile':z+=.015*(x/.029)**2
   if name=='mouth_frown':z-=.015*(x/.029)**2
   if name.startswith('viseme_'):
    sx,sz={'viseme_a':(1.45,5.5),'viseme_e':(1.8,2.8),'viseme_i':(1.6,1.5),'viseme_o':(1.15,3.7),'viseme_u':(.72,2.7)}[name];x*=sx;z*=sz
   arr[i]=mc+[x,y,z]
 key=face.shape_key_add(name=name)
 for v,p in zip(key.data,arr):v.co=p
# Conform every mouth shape to the rebuilt recessed face, with a small constant
# surface clearance. A large open vowel must not sink through the lower cheek.
from mathutils.bvhtree import BVHTree
body.data.calc_loop_triangles()
surface=BVHTree.FromPolygons([v.co for v in body.data.vertices],[t.vertices[:] for t in body.data.loop_triangles],all_triangles=True)
for key in face.data.shape_keys.key_blocks:
 for index in mouth:
  p=key.data[index].co;hit,_,_,_=surface.ray_cast(Vector((p.x,-3,p.z)),Vector((0,1,0)))
  if hit:p.y=hit.y-.022+(p.y-mc[1])
for v,p in zip(face.data.vertices,face.data.shape_keys.key_blocks['Basis'].data):v.co=p.co
face['mouth_vertex_indices']=mouth
# Standalone props: retain local shapes, add rigid bone weights and remove QA sockets.
props=[]
for name in ['magnifier','pencil','clipboard','monocle','bell','rolled_cuff']:
 before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(O/'hanhan_props_v4'/f'{name}.glb'));new=set(bpy.data.objects)-before;ob=next(x for x in new if x.type=='MESH')
 for x in new:
  if x!=ob:bpy.data.objects.remove(x,do_unlink=True)
 ob.name='prop_'+name
 ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
 for c in list(ob.users_collection):c.objects.unlink(ob)
 COL.objects.link(ob)
 if name=='rolled_cuff':
  bpy.context.view_layer.objects.active=ob;dec=ob.modifiers.new('cuff_mobile','DECIMATE');dec.ratio=.38;bpy.ops.object.modifier_apply(modifier=dec.name)
  copies=[ob,ob.copy()];copies[1].data=ob.data.copy();COL.objects.link(copies[1])
  for c,side,s in zip(copies,['l','r'],[1,-1]):
   c.name='prop_cuff_'+side
   for v in c.data.vertices:v.co=Vector((s*1.115,0,1.17))+v.co*.85
   g=c.vertex_groups.new(name='prop_cuff_'+side+'_bone');g.add(list(range(len(c.data.vertices))),1,'REPLACE');m=c.modifiers.new('rig','ARMATURE');m.object=rig;c.parent=rig;props.append(c)
 else:
  g=ob.vertex_groups.new(name='prop_'+name+'_bone');g.add(list(range(len(ob.data.vertices))),1,'REPLACE');m=ob.modifiers.new('rig','ARMATURE');m.object=rig;ob.parent=rig;props.append(ob)
manifest=json.loads((O/'hanhan_mobile_v3_states.json').read_text());manifest.update(version='4.4',asset='hanhan_rodin_v4_4.glb',source='Hyper3D Rodin Gen-1.5; local rig and animation');manifest['states']['review']['props']+=['prop_monocle'];manifest['states']['resume']['props']=['prop_cuff_l','prop_cuff_r'];manifest['states']['alert']['props']=['prop_bell'];manifest['runtime_gaze_scale']=[.043,.032];manifest['interaction']={'touch_duration':1.8,'touch_cooldown':1.2};manifest['states']['playful']={'label':'逗趣','duration':2.4,'loop':False,'next':'idle','props':[]};manifest['states']['briefing']['props']=['prop_clipboard'];manifest['default_props_visible']=True;manifest['visemes']=['A','E','I','O','U'];manifest['states']['alert']['loop']=True;manifest['states']['alert']['duration']=2.4;manifest['states']['resume']['duration']=2.4
manifest['hair_physics']={'solver':'spring_mass_guide_v1','bones':[{'name':f'fur_{i}','length':arm.bones[f'fur_{i}'].length} for i in range(8)],'stiffness':145,'damping':13,'max_offset':.085,'collision_radius':.90,'center':[0,1.22,0],'gravity':.12}
from motion_v4_4 import Motion
motion=Motion(rig,face,origins,rest,manifest,body);pose=motion.pose
# Sample a real neutral pose and QA arm/finger configurations before authoring actions.
for n in manifest['states']:
 spec=manifest['states'][n];dur=spec['duration'];rig.animation_data_create();face.data.shape_keys.animation_data_create();rig.animation_data.action=None;face.data.shape_keys.animation_data.action=None
 for frame in range(round(dur*30)+1):
  scene.frame_set(frame);pose(n,frame/30,dur)
  for pb in rig.pose.bones:
   for path in ['location','rotation_quaternion','scale']:pb.keyframe_insert(path,frame=frame,group=pb.name)
  for key in face.data.shape_keys.key_blocks:
   if key.name!='Basis':key.keyframe_insert('value',frame=frame)
 for owner,suffix in [(rig,'_skeleton'),(face.data.shape_keys,'_expression')]:
  ac=owner.animation_data.action;ac.name=n+suffix;ac.use_fake_user=True;tr=owner.animation_data.nla_tracks.new();tr.name=n;tr.strips.new(n,0,ac);tr.mute=True;owner.animation_data.action=None
 print('ACTION_DONE',n,flush=True)
scene.frame_set(0);pose('idle',0,4)
rig['asset_version']='4.4';rig['source']='Rodin original preserved in reference/rodin_v4';rig['motion_method']='Locally authored animation from static reference poses; no paid motion generation'
for p in props:p.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for ob in [rig,body,face]+props:ob.select_set(True)
for owner in [rig,face.data.shape_keys]:
 for tr in owner.animation_data.nla_tracks:tr.mute=False
scene.frame_start=0;scene.frame_end=120
bpy.ops.export_scene.gltf(filepath=str(O/'hanhan_rodin_v4_4.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_nla_strips=True,export_anim_slide_to_zero=True,export_extras=True,export_cameras=False,export_lights=False)
for owner in [rig,face.data.shape_keys]:
 for tr in owner.animation_data.nla_tracks:tr.mute=True
rig.animation_data.action=bpy.data.actions['idle_skeleton'];face.data.shape_keys.animation_data.action=bpy.data.actions['idle_expression'];scene.frame_set(0)
scene.camera.location=(0,-6,1.4);scene.camera.rotation_euler=(Vector((0,0,1.05))-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=3.2;scene.render.resolution_x=720;scene.render.resolution_y=720;scene.cycles.samples=12;scene.render.film_transparent=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'hanhan_rodin_v4_4.blend'),compress=True)
(O/'hanhan_rodin_v4_4_states.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
for name in ['hanhan_rodin_v4_4.glb','hanhan_rodin_v4_4_states.json']:shutil.copy2(O/name,B/'web/public/assets'/name)
report={'triangles_body':sum(len(p.vertices)-2 for p in body.data.polygons),'triangles_limbs':0,'triangles_face':sum(len(p.vertices)-2 for p in face.data.polygons),'bones':len(arm.bones),'glb_bytes':(O/'hanhan_rodin_v4_4.glb').stat().st_size,'states':list(manifest['states'])};(Q/'build_report.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
for n in ['idle','briefing','progress','review','pause','resume','decision','alert']:
 rig.animation_data.action=bpy.data.actions[n+'_skeleton'];face.data.shape_keys.animation_data.action=bpy.data.actions[n+'_expression'];scene.frame_set(round(manifest['states'][n]['duration']*30*.46))
 for p in props:p.hide_render=p.name not in manifest['states'][n]['props']
 scene.render.filepath=str(Q/f'{n}_front.png');bpy.ops.render.render(write_still=True)
