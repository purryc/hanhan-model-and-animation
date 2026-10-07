"""Topology, deformation, contact, reference views and GLB round-trip checks."""
import bpy,json,math,struct,numpy as np,bmesh
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
B=Path(__file__).resolve().parents[1];O=B/'output';Q=B/'qa/v4_4'
manifest=json.loads((O/'hanhan_rodin_v4_4_states.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(O/'hanhan_rodin_v4_4.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['hanhan_rig'];face=bpy.data.objects['hanhan_expression'];body=bpy.data.objects['hanhan_rodin_body'];cam=scene.camera
scene.cycles.samples=12;scene.render.resolution_x=scene.render.resolution_y=560
mesh=body.data;mesh.calc_loop_triangles();base=np.array([v.co[:] for v in mesh.vertices]);edges=np.array([e.vertices[:] for e in mesh.edges]);lengths=np.linalg.norm(base[edges[:,0]]-base[edges[:,1]],axis=1)
def family(v):
 names=[body.vertex_groups[g.group].name for g in v.groups if g.weight>.0001]
 if all(n=='body' or n.startswith('fur_') for n in names):return 'body'
 if all(n.startswith(('hand_','finger')) and n.endswith('_l') for n in names):return 'hand_l'
 if all(n.startswith(('hand_','finger')) and n.endswith('_r') for n in names):return 'hand_r'
 if names and all(n.startswith('fur_') for n in names):return 'fur'
 if names and all(n.startswith(('arm_','forearm_','hand_')) for n in names):return 'arm'
 if names==['foot_l']:return 'foot_l'
 if names==['foot_r']:return 'foot_r'
 return 'mixed'
families=[family(v) for v in mesh.vertices]
triangles={name:[t.vertices[:] for t in mesh.loop_triangles if all(families[i]==name for i in t.vertices)] for name in set(families)}
report={'source_reopened':True,'bone_count':len(rig.data.bones),'mixed_body_limb_vertices':families.count('mixed'),'semantic_boundary_edges':sum(families[a]!=families[b] for a,b in edges),'states':{},'contact_intersections':{},'topology':{}}
surface=BVHTree.FromPolygons([v.co for v in body.data.vertices],[t.vertices[:] for t in body.data.loop_triangles],all_triangles=True)
clearances=[]
for key in face.data.shape_keys.key_blocks:
 for index in face['mouth_vertex_indices']:
  p=key.data[index].co;hit,_,_,_=surface.ray_cast(Vector((p.x,-3,p.z)),Vector((0,1,0)))
  if hit:clearances.append(hit.y-p.y)
report['minimum_mouth_surface_clearance']=min(clearances)
report['unexpected_semantic_boundary_edges']=sum(families[a]!=families[b] and not ('arm' in {families[a],families[b]} and ({families[a],families[b]}&{'hand_l','hand_r'})) for a,b in edges)
shell=base[[i for i,f in enumerate(families) if f=='body']];shell_center=np.array([0,0,1.22]);outer=shell[shell[:,1]>-.40]
report['round_shell']={'outer_radius':.99,'maximum_outer_radius_error':float(np.abs(np.linalg.norm(outer-shell_center,axis=1)-.99).max()),'width':float(np.ptp(shell[:,0])),'height':float(np.ptp(shell[:,2]))}
for name,ts in triangles.items():
 used=sorted({v for t in ts for v in t});index={old:new for new,old in enumerate(used)};me=bpy.data.meshes.new('qa_topology');me.from_pydata(base[used].tolist(),[],[[index[v] for v in t] for t in ts]);bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00002)
 report['topology'][name]={'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)};bm.free();bpy.data.meshes.remove(me)
for name,spec in manifest['states'].items():
 rig.animation_data.action=bpy.data.actions[name+'_skeleton'];face.data.shape_keys.animation_data.action=bpy.data.actions[name+'_expression'];max_stretch=0;min_z=10;max_collision=0;peak_frame=0
 end=round(spec['duration']*30)
 for frame in range(end+1):
  scene.frame_set(frame);ob=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ob.to_mesh();pts=np.array([v.co[:] for v in me.vertices]);ob.to_mesh_clear()
  current=np.linalg.norm(pts[edges[:,0]]-pts[edges[:,1]],axis=1);valid=(lengths>.001)&np.array([families[a] not in ['arm','fur'] and families[b] not in ['arm','fur'] for a,b in edges]);stretch=float(np.max(current[valid]/lengths[valid]));max_stretch=max(max_stretch,stretch);min_z=min(min_z,float(pts[:,2].min()));assert np.isfinite(pts).all()
  if name in ['pause','resume','decision','review','progress']:
   trees={part:BVHTree.FromPolygons(pts.tolist(),triangles[part],all_triangles=True) for part in ['hand_l','hand_r','foot_l','foot_r']}
   hits=sum(len(trees[h].overlap(trees[f])) for h in ['hand_l','hand_r'] for f in ['foot_l','foot_r'])
   if hits>max_collision:max_collision=hits;peak_frame=frame
 report['states'][name]={'frames_sampled':end+1,'max_edge_stretch':max_stretch,'minimum_z':min_z}
 if name in ['pause','resume','decision','review','progress']:report['contact_intersections'][name]={'hand_boot_triangle_pairs':max_collision,'worst_frame':peak_frame}
 # Independent source views, including state props, without the browser symbol overlay.
 for o in scene.objects:
  if o.name.startswith('prop_'):o.hide_render=o.name not in spec['props']
 scene.frame_set(round(end*.46));cam.location=(0,-6,1.4);cam.rotation_euler=(Vector((0,0,1.05))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(Q/f'{name}_front.png');bpy.ops.render.render(write_still=True)
 if name in ['pause','resume','review','progress','decision']:
  for fraction in [0,.25,.5,.75,1]:
   scene.frame_set(round(end*fraction));cam.location=(4,-6,1.5);cam.rotation_euler=(Vector((0,0,1.05))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(Q/f'{name}_quarter_{round(fraction*100):03}.png');bpy.ops.render.render(write_still=True)
 print('QA_STATE',name,report['states'][name],report['contact_intersections'].get(name),flush=True)
rig.animation_data.action=None;face.data.shape_keys.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
for tr in face.data.shape_keys.animation_data.nla_tracks:tr.mute=True
cam.location=(0,-6,1.3);cam.rotation_euler=(Vector((0,0,1.18))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.05
for o in scene.objects:
 if o.name.startswith('prop_'):o.hide_render=True
for vowel in ['a','e','i','o','u']:
 for k in face.data.shape_keys.key_blocks:
  if k.name!='Basis':k.value=1 if k.name=='viseme_'+vowel else 0
 scene.render.filepath=str(Q/f'viseme_{vowel}.png');bpy.ops.render.render(write_still=True)
cam.data.ortho_scale=3.2
rig.animation_data.action=bpy.data.actions['idle_skeleton'];face.data.shape_keys.animation_data.action=bpy.data.actions['idle_expression'];scene.frame_set(0)
for o in scene.objects:
 if o.name.startswith('prop_'):o.hide_render=True
for view,loc in [('side',(6,0,1.2)),('rear',(0,6,1.2))]:
 cam.location=loc;cam.rotation_euler=(Vector((0,0,1.05))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(Q/(view+'.png'));bpy.ops.render.render(write_still=True)
f=open(O/'hanhan_rodin_v4_4.glb','rb');f.read(12);n,t=struct.unpack('<II',f.read(8));g=json.loads(f.read(n));report['glb_bytes']=(O/'hanhan_rodin_v4_4.glb').stat().st_size
meshes={}
for node in g['nodes']:
 if 'mesh' in node:
  m=g['meshes'][node['mesh']];meshes[node['name']]=(sum(g['accessors'][p['indices']]['count']//3 for p in m['primitives']),len(m['primitives']))
report['mesh_budget']=meshes;report['state_budget']={}
for name,spec in manifest['states'].items():
 visible=[v for k,v in meshes.items() if not k.startswith('prop_') or k in spec['props']];report['state_budget'][name]={'triangles':sum(v[0] for v in visible),'draw_calls':sum(v[1] for v in visible)}
report['animation_names']=[a['name'] for a in g['animations']];report['no_external_uris']=all('uri' not in i for i in g.get('images',[])+g.get('buffers',[]));report['external_images_packed']=all(i.packed_file is not None for i in bpy.data.images if i.type=='IMAGE' and i.source=='FILE')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/'hanhan_rodin_v4_4.glb'));report['glb_reimported']=True;report['texture_dimensions']=[list(im.size) for im in bpy.data.images if im.type=='IMAGE'];bpy.ops.wm.save_as_mainfile(filepath=str(Q/'glb_reimport.blend'))
report['technical_pass']=all([
 max(s['triangles'] for s in report['state_budget'].values())<=20000,
 report['bone_count']<=48,
 max(s['draw_calls'] for s in report['state_budget'].values())<=8,
 report['glb_bytes']<=5242880,report['no_external_uris'],report['external_images_packed'],
 set(report['animation_names'])==set(manifest['states']),
 all(max(sz)<=1024 for sz in report['texture_dimensions']),
 report['mixed_body_limb_vertices']==0,report['minimum_mouth_surface_clearance']>.003,
 report['unexpected_semantic_boundary_edges']==0,
 report['round_shell']['maximum_outer_radius_error']<.012,
 max(v['max_edge_stretch'] for v in report['states'].values())<3,
 not any(v['hand_boot_triangle_pairs'] for v in report['contact_intersections'].values())])
(Q/'asset_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('FINAL_QA',report['technical_pass'],report['topology'],report['contact_intersections'],flush=True)
