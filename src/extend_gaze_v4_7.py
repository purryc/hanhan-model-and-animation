"""Extend the accepted v4.4 source with four editable gaze shapes; no paid generation."""
import bpy, json, math, shutil, struct
from pathlib import Path
from mathutils import Vector, Matrix
B=Path(__file__).resolve().parents[1];O=B/'output';Q=B/'qa/v4_7'
bpy.ops.wm.open_mainfile(filepath=str(O/'hanhan_rodin_v4_4.blend'))
scene=bpy.context.scene;face=bpy.data.objects['hanhan_expression'];rig=bpy.data.objects['hanhan_rig']
base=face.data.shape_keys.key_blocks['Basis'];colors=face.data.color_attributes['Color']
eyes=[]
for side,s in [('l',1),('r',-1)]:
 group=face.vertex_groups['eye_'+side].index;c=Vector((s*.10,-.579,1.25))
 ids=[v.index for v in face.data.vertices if any(g.group==group and g.weight>.9 for g in v.groups)]
 white=[i for i in ids if colors.data[i].color[0]>.8]
 # Alternate expression strokes collapse to their center in Basis; leave them alone.
 black=[i for i in ids if i not in white and (base.data[i].co-c).length>.003]
 assert len(white)==54 and len(black)==187,(len(white),len(black))
 eyes.append((c,black,white))
 for i in white:face.data.shape_keys.key_blocks['blink'].data[i].co=c+(base.data[i].co-c)*.001
for name,gx,gy in [('gaze_left',-1,0),('gaze_right',1,0),('gaze_up',0,1),('gaze_down',0,-1)]:
 key=face.shape_key_add(name=name,from_mix=False)
 # Blender is Z up, forward -Y. Rotate the oval and retain its domed volume.
 rot=Matrix.Rotation(math.radians(18)*gx,3,'Z')@Matrix.Rotation(-math.radians(26 if gy<0 else 14)*gy,3,'X')
 for c,black,white in eyes:
  for i in black:key.data[i].co=c+rot@(base.data[i].co-c)
  old=Vector((-.011,-.019,.018));x=old.x+.008*gx;z=old.z+(.014 if gy<0 else .006)*gy
  new=Vector((x,-.021*math.sqrt(max(.05,1-(x/.042)**2-(z/.055)**2))-.0015,z))
  for i in white:key.data[i].co=c+rot@(new+base.data[i].co-c-old)
eye_ids={i for c,black,white in eyes for i in black+white}
for name in ['gaze_left','gaze_right','gaze_up','gaze_down']:
 for i in range(len(base.data)):
  if i not in eye_ids:assert (face.data.shape_keys.key_blocks[name].data[i].co-base.data[i].co).length<1e-8,(name,i)
rig['asset_version']='4.7'
manifest=json.loads((O/'hanhan_rodin_v4_4_states.json').read_text());manifest.update(version='4.7',asset='hanhan_rodin_v4_7.glb')
manifest['runtime_gaze_scale']=[.032,.024]
manifest['gaze_surface']={'shapes':['gaze_left','gaze_right','gaze_up','gaze_down'],'eye_response':19,'head_response':4,'head_yaw':.045,'head_pitch':.026,'head_pitch_down':.065,'down_gain':1.6,'down_scale':.043,'down_forward':.009,'down_priority':True,'head_states':{'idle':1,'listen':.55,'speak':1,'working':.35}}
for owner in [rig,face.data.shape_keys]:
 owner.animation_data.action=None
 for tr in owner.animation_data.nla_tracks:tr.mute=False
for k in face.data.shape_keys.key_blocks:k.value=0
bpy.ops.object.select_all(action='DESELECT')
for ob in scene.objects:
 if ob==rig or ob.parent==rig:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/manifest['asset']),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_nla_strips=True,export_anim_slide_to_zero=True,export_extras=True,export_cameras=False,export_lights=False)
for owner in [rig,face.data.shape_keys]:
 for tr in owner.animation_data.nla_tracks:tr.mute=True
rig.animation_data.action=bpy.data.actions['idle_skeleton'];face.data.shape_keys.animation_data.action=bpy.data.actions['idle_expression'];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'hanhan_rodin_v4_7.blend'),compress=True)
(O/'hanhan_rodin_v4_7_states.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
for n in [manifest['asset'],'hanhan_rodin_v4_7_states.json']:shutil.copy2(O/n,B/'web/public/assets'/n)
# Reopen source and round-trip exported GLB, checking actual delivered geometry.
bpy.ops.wm.open_mainfile(filepath=str(O/'hanhan_rodin_v4_7.blend'))
assert len(bpy.data.objects['hanhan_expression'].data.shape_keys.key_blocks)==18
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(O/manifest['asset']))
face=next(o for o in bpy.data.objects if o.type=='MESH' and o.data.shape_keys and 'gaze_left' in o.data.shape_keys.key_blocks);assert all(n in face.data.shape_keys.key_blocks for n in manifest['gaze_surface']['shapes'])
bones=sum(len(o.data.bones) for o in bpy.data.objects if o.type=='ARMATURE')
raw=(O/manifest['asset']).read_bytes();size=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+size]);assert len(g['animations'])==15 and bones<=48 and len(raw)<5242880
assert all('uri' not in item for item in g.get('images',[])+g.get('buffers',[]))
report={'source_reopened':True,'glb_reimported':True,'bones':bones,'glb_bytes':len(raw),'animations':len(g['animations']),'morphs':[k.name for k in face.data.shape_keys.key_blocks],'textures':[list(i.size) for i in bpy.data.images if i.type=='IMAGE']}
assert all(max(d)<=1024 for d in report['textures'])
(Q/'asset_validation.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
