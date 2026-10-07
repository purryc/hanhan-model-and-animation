"""Local, zero-credit accessory kit. Front = -Y; shared vertex-color material."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output/hanhan_props_v4'; OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
COL={'blue':(.055,.20,.72,1),'yellow':(1,.60,.035,1),'navy':(.025,.04,.12,1),'white':(.93,.96,1,1),'silver':(.52,.61,.76,1),'wood':(.78,.50,.24,1),'pink':(1,.32,.46,1)}
mat=bpy.data.materials.new('props_palette'); mat.use_nodes=True
nt=mat.node_tree; bs=nt.nodes.get('Principled BSDF'); bs.inputs['Roughness'].default_value=.36
vc=nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name='Color'; nt.links.new(vc.outputs['Color'],bs.inputs['Base Color'])
parts=[]; assets=[]
def finish(obj,color):
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if obj.type=='CURVE':bpy.ops.object.convert(target='MESH')
 if obj.modifiers:
  for mod in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
 attr=obj.data.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER')
 for datum in attr.data:datum.color=COL[color]
 obj.data.materials.append(mat)
 for p in obj.data.polygons:p.use_smooth=True
 parts.append(obj);return obj

def box(pos,scale,col,bevel=.025):
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos); o=bpy.context.object;o.scale=scale
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 m=o.modifiers.new('soft_corners','BEVEL');m.width=bevel;m.segments=3
 return finish(o,col)
def ring(pos,r,thick,col):
 bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=thick,major_segments=40,minor_segments=8,location=pos,rotation=(math.pi/2,0,0));return finish(bpy.context.object,col)
def rod(a,b,r,col,verts=12,r2=None):
 d=Vector(b)-Vector(a);mid=(Vector(a)+Vector(b))/2
 bpy.ops.mesh.primitive_cone_add(vertices=verts,radius1=r,radius2=r if r2 is None else r2,depth=d.length,location=mid)
 o=bpy.context.object;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();return finish(o,col)
def sphere(pos,r,col):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=r,location=pos);return finish(bpy.context.object,col)
def complete(name,grip,states):
 global parts
 bpy.ops.object.select_all(action='DESELECT')
 for p in parts:p.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
 bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
 # One object/material primitive per prop, separate semantic attachment.
 while len(o.data.materials)>1:o.data.materials.pop(index=1)
 for p in o.data.polygons:p.material_index=0
 o.data.calc_loop_triangles(); socket=bpy.data.objects.new(name+'_grip',None);bpy.context.collection.objects.link(socket);socket.location=grip;socket.parent=o;socket.select_set(True)
 o['source']='Local Blender construction; no paid generation';o['states']=','.join(states)
 bpy.ops.export_scene.gltf(filepath=str(OUT/(name+'.glb')),export_format='GLB',use_selection=True,export_animations=False)
 assets.append({'name':name,'file':name+'.glb','triangles':len(o.data.loop_triangles),'grip':grip,'states':states,'draw_calls':1,'object':o})
 parts=[]
# Magnifier: open aperture avoids costly refractive pass and keeps expressions visible.
ring((0,0,.38),.19,.025,'yellow');rod((0,0,0),(0,0,.20),.031,'blue');rod((0,0,.17),(0,0,.205),.034,'silver');complete('magnifier',(0,0,.07),['progress'])
# Six-sided pencil with pink eraser, ferrule, wood and graphite.
rod((0,0,-.20),(0,0,.18),.025,'yellow',6);rod((0,0,.18),(0,0,.245),.025,'wood',6,r2=.008);rod((0,0,.245),(0,0,.27),.008,'navy',6,r2=0);rod((0,0,-.23),(0,0,-.20),.027,'silver');rod((0,0,-.27),(0,0,-.23),.026,'pink');complete('pencil',(0,0,-.04),['review'])
box((0,0,.02),(.35,.032,.46),'blue',.027);box((0,-.020,.02),(.30,.010,.39),'white',.012);box((0,-.039,.226),(.13,.022,.034),'silver',.012)
for z in [.13,.03,-.07]:
 box((.023,-.029,z),(.19,.007,.011),'silver',.004)
 rod((-.113,-.032,z),(-.099,-.032,z-.013),.005,'blue',8);rod((-.099,-.032,z-.013),(-.075,-.032,z+.014),.005,'blue',8)
complete('clipboard',(.145,.02,-.035),['review'])
ring((0,0,0),.125,.010,'navy');rod((.117,0,-.04),(.142,0,-.095),.009,'silver');complete('monocle',(.0,.01,0),['review'])
# Cuff axis X, open sleeve interior. Shared mesh can be instanced left/right.
for x,r in [(-.047,.090),(0,.094),(.047,.090)]:
 o=ring((x,0,0),r,.020,'blue');o.rotation_euler=(0,math.pi/2,0)
complete('rolled_cuff',(0,0,0),['resume'])
# Lathed bell shell with thickness/open underside and separate clapper.
profile=[(.018,.27),(.06,.258),(.096,.205),(.105,.115),(.137,.045),(.152,.024),(.154,.009),(.145,-.003),(.126,.014),(.086,.10),(.078,.195),(.048,.238),(.018,.247)]
vs=[];fs=[];n=32
for r,z in profile:
 for i in range(n):vs.append((r*math.cos(i*2*math.pi/n),r*math.sin(i*2*math.pi/n),z))
for j in range(len(profile)-1):
 for i in range(n):a=j*n+i;b=j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
mesh=bpy.data.meshes.new('bell_shell');mesh.from_pydata(vs,[],fs);mesh.update();o=bpy.data.objects.new('bell_shell',mesh);bpy.context.collection.objects.link(o);bpy.context.view_layer.objects.active=o;o.select_set(True);finish(o,'yellow')
sphere((0,0,.018),.031,'yellow');ring((0,0,.296),.030,.008,'yellow');complete('bell',(0,0,.30),['alert'])
# A clean inspection board; the individual exports retain their unshifted origins.
for i,a in enumerate(assets):
 a['object'].location=((i%3-1)*.90,0,(1-i//3)*.88)
 a['object'].rotation_euler.z=0
 del a['object']
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
scene.world=bpy.data.worlds.new('studio');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.70,.80,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
for pos,power,size in [((-3,-4,5),450,4),((3,-2,2),250,3)]:
 bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=size;l.rotation_euler=(Vector((0,0,.5))-l.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(.12,-6,2.0));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,.63))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=2.9;scene.camera=cam
scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'hanhan_props_v4.blend'))
scene.render.filepath=str(OUT/'hanhan_props_v4_overview.png');bpy.ops.render.render(write_still=True)
(OUT/'manifest.json').write_text(json.dumps({'credit_cost':0,'assets':assets,'note':'Unrigged props. Actual hand/face fit pending final Rodin mesh.'},indent=2))
print('PROP_KIT_DONE',sum(x['triangles'] for x in assets))
