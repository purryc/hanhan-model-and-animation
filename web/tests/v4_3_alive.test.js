import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {HanhanController} from '../src/hanhan_controller.js';
globalThis.self=globalThis;
globalThis.createImageBitmap=async()=>({width:512,height:512,close(){}});
const data=await fs.readFile(new URL('../public/assets/hanhan_rodin_v4_3.glb',import.meta.url));
const manifest=JSON.parse(await fs.readFile(new URL('../public/assets/hanhan_rodin_v4_3_states.json',import.meta.url),'utf8'));
async function load(){const gltf=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');return {gltf,c:new HanhanController(gltf,manifest)};}
function step(c,s){for(let i=0;i<Math.ceil(s*60);i++)c.update(1/60);}
test('v4.3 actual GLB retains 15 timed clips and seamless loop endpoints',async()=>{const{gltf,c}=await load();assert.equal(gltf.animations.length,15);for(const clip of gltf.animations){assert.ok(Math.abs(clip.duration-manifest.states[clip.name].duration)<.002);if(!manifest.states[clip.name].loop)continue;for(const t of clip.tracks){const size=t.getValueSize();for(let i=0;i<size;i++)assert.ok(Math.abs(t.values[i]-t.values[t.values.length-size+i])<.0001,clip.name+':'+t.name);}}c.dispose();});
test('all generated accessories appear in their assigned states by default and can hide',async()=>{const{c}=await load();assert.equal(c.showProps,true);const seen=new Set();for(const name of Object.keys(manifest.states)){c.setState(name);step(c,.3);const visible=c.props.filter(p=>p.visible).map(p=>p.name);assert.deepEqual(visible.sort(),[...manifest.states[name].props].sort());visible.forEach(n=>seen.add(n));}assert.equal(seen.size,7);c.setState('review');c.setPropsVisible(false);assert.ok(c.props.every(p=>!p.visible));c.dispose();});
test('repaired GLB stays within mobile limits including a reference symbol sprite',async()=>{const{c}=await load();assert.ok(data.length<5242880);for(const name of Object.keys(manifest.states)){c.setState(name);step(c,.35);let tri=2,draw=1;c.root.traverse(o=>{if(!o.isMesh||!o.visible)return;tri+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;draw+=Array.isArray(o.material)?o.material.length:1;if(o.isSkinnedMesh){o.computeBoundingBox();assert.ok(o.boundingBox.min.y>-.05);assert.ok(o.boundingBox.max.x-o.boundingBox.min.x<3.5);}});assert.ok(tri<=20000,name+' triangles');assert.ok(draw<=8,name+' draws');}c.dispose();});
test('sitting touch laugh, stronger gaze, audio events and interrupted recovery survive repair',async()=>{const{c}=await load();const events=[];c.onLaugh=e=>events.push(e.kind);c.setGaze(1,1);step(c,.5);assert.ok(c.eyeOffsets[0].x>.04);c.setState('pause');step(c,.4);c.touchBody();step(c,.25);assert.equal(c.state,'pause');assert.ok(c.morph('happy')>.99);assert.deepEqual(events,['touch']);c.setState('resume');step(c,.3);c.setState('error');step(c,2);assert.equal(c.state,'error');assert.ok(c.morph('spiral')>.99);c.setState('playful');step(c,.8);assert.deepEqual(events,['touch','playful']);c.setActive(false);const time=c.mixer.time;step(c,3);assert.equal(c.mixer.time,time);c.dispose();});

test('five independent vowel shapes blend without stacking and reset on silence or interruption',async()=>{
 const{c}=await load();assert.deepEqual(manifest.visemes,['A','E','I','O','U']);const attrs=c.face.geometry.morphAttributes.position;
 for(const a of manifest.visemes){const ia=c.face.morphTargetDictionary['viseme_'+a.toLowerCase()];assert.ok(ia>=0);for(const b of manifest.visemes){if(a===b)continue;const ib=c.face.morphTargetDictionary['viseme_'+b.toLowerCase()];assert.ok(attrs[ia].array.some((v,i)=>Math.abs(v-attrs[ib].array[i])>.001));}}
 c.setState('speak');c.setSpeechLevel(.8);c.setViseme('A');step(c,.5);assert.ok(c.morph('viseme_a')>.99);assert.equal(c.morph('mouth_open'),0);
 c.setViseme('U');for(let i=0;i<30;i++){c.update(1/60);assert.ok(c.visemeWeights.reduce((a,b)=>a+b,0)<=1.00001);}assert.ok(c.morph('viseme_u')>.99);
 c.setSpeechLevel(0);assert.ok(c.visemeWeights.every(v=>v===0));assert.equal(c.morph('viseme_u'),0);
 c.setViseme('E');step(c,.3);c.setState('error');step(c,.25);assert.ok(manifest.visemes.every(v=>c.morph('viseme_'+v.toLowerCase())===0));
 c.setState('speak');c.setViseme('O');step(c,.3);c.setActive(false);assert.equal(c.morph('viseme_o'),0);c.setActive(true);step(c,.25);assert.equal(c.morph('viseme_o'),0);
 c.setViseme('A');step(c,.3);c.setViseme('A',-1);assert.equal(c.morph('viseme_a'),0);c.setViseme('A');step(c,.3);c.touchBody();step(c,.2);assert.ok(c.morph('viseme_a')<.001);assert.ok(c.morph('happy')>.99);step(c,2);assert.ok(c.morph('viseme_a')>.99);
 assert.throws(()=>c.setViseme('X'),RangeError);assert.throws(()=>c.setViseme('A',NaN),TypeError);c.dispose();
});
test('persistent states keep hands and eight fur clusters moving',async()=>{
 const{gltf,c}=await load();const bones=[];c.root.traverse(o=>{if(o.isBone)bones.push(o);});assert.equal(bones.length,46);assert.equal(bones.filter(o=>o.name.startsWith('fur_')).length,8);
 for(const clip of gltf.animations){if(!manifest.states[clip.name].loop)continue;const moving=(prefix)=>clip.tracks.filter(t=>t.name.startsWith(prefix)&&(t.name.endsWith('.quaternion')||t.name.endsWith('.position'))).some(t=>{const q=Array.from(t.values);return q.some((v,i)=>Math.abs(v-q[i%t.getValueSize()])>.003);});assert.ok(moving('hand_'),clip.name+' hands');assert.ok(moving('fur_'),clip.name+' fur');}c.dispose();
});
