import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {HanhanController} from '../src/hanhan_controller.js';
globalThis.self=globalThis;globalThis.createImageBitmap=async()=>({width:512,height:512,close(){}});
const data=await fs.readFile(new URL('../public/assets/hanhan_rodin_v4_4.glb',import.meta.url));
const manifest=JSON.parse(await fs.readFile(new URL('../public/assets/hanhan_rodin_v4_4_states.json',import.meta.url),'utf8'));
async function load(){const gltf=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');return{gltf,c:new HanhanController(gltf,manifest)};}
function step(c,s,dt=1/60){for(let i=0;i<Math.ceil(s/dt);i++)c.update(dt);}
test('v4.4 retains clips, vowels, budgets and uses constant guide animation tracks',async()=>{const{gltf,c}=await load();assert.equal(gltf.animations.length,15);assert.equal(c.hairPhysics.guides.length,8);assert.ok(data.length<5000000);assert.equal(manifest.visemes.length,5);
 for(const clip of gltf.animations){assert.ok(Math.abs(clip.duration-manifest.states[clip.name].duration)<.002);for(const t of clip.tracks){const n=t.getValueSize();if(manifest.states[clip.name].loop)for(let i=0;i<n;i++)assert.ok(Math.abs(t.values[i]-t.values[t.values.length-n+i])<.0001);if(t.name.startsWith('fur_')&&t.name.endsWith('.quaternion'))assert.ok(Array.from(t.values).every((v,i)=>Math.abs(v-t.values[i%n])<.0001));}}
 for(const state of Object.keys(manifest.states)){c.setState(state);step(c,.4);let tri=2,draw=1;c.root.traverse(o=>{if(!o.isMesh||!o.visible)return;tri+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;draw+=Array.isArray(o.material)?o.material.length:1;});assert.ok(tri<20000);assert.ok(draw<=8);}c.dispose();});
test('physical guide tips lag animation, obey limits and settle after an impulse',async()=>{const{c}=await load();step(c,.3);const p=c.hairPhysics;
 for(const g of p.guides){assert.ok(g.target.distanceTo(p.center)>.95);assert.ok(g.target.distanceTo(p.center)<1.1);}
 c.setState('working');let peak=0;for(let i=0;i<240;i++){c.update(1/60);peak=Math.max(peak,p.maxDisplacement);assert.ok(p.maxDisplacement<=.08501);assert.ok(p.guides.every(g=>g.position.distanceTo(p.center)>=.8999));}assert.ok(peak>.015);
 c.currentAction.paused=true;step(c,5);const rest=p.guides.map(g=>g.position.clone());p.impulse(.7,.3,0);step(c,.1);assert.ok(p.guides.some((g,i)=>g.position.distanceTo(rest[i])>.015));step(c,6);assert.ok(p.maxSpeed<.003);assert.ok(p.maxDisplacement<.003);
 c.setActive(false);assert.equal(p.initialized,false);c.setActive(true);step(c,.05);assert.ok(p.maxDisplacement<.003);p.setEnabled(false);step(c,.1);assert.equal(p.maxDisplacement,0);c.dispose();});
test('spring integration stays consistent at 30, 60 and 120 fps',async()=>{const outcomes=[];for(const fps of [30,60,120]){const{c}=await load();c.update(0);const p=c.hairPhysics;p.update(1/120);for(let i=1;i<=fps*2;i++){p.restore();c.body.rotation.z=.09*Math.sin(i/fps*Math.PI*2);p.update(1/fps);}outcomes.push(p.guides.map(g=>g.position.clone()));c.dispose();}for(let i=0;i<8;i++){assert.ok(outcomes[0][i].distanceTo(outcomes[2][i])<.008);assert.ok(outcomes[1][i].distanceTo(outcomes[2][i])<.004);}});
test('quick interruptions and laughter keep hair finite without stale simulation',async()=>{const{c}=await load();for(let i=0;i<60;i++){c.setState(['pause','resume','error','speak'][i%4]);if(i%4===3){c.setViseme('A');c.touchBody();}step(c,.08);assert.ok(c.hairPhysics.guides.every(g=>[...g.position,...g.velocity].every(Number.isFinite)));assert.ok(c.hairPhysics.maxDisplacement<.086);}c.setActive(false);const t=c.mixer.time;step(c,10);assert.equal(c.mixer.time,t);c.setActive(true);step(c,.1);assert.ok(c.hairPhysics.maxDisplacement<.086);c.dispose();});
test('real skinned outer hair moves under physics while the face stays anchored',async()=>{
 const{c}=await load();step(c,.3);c.currentAction.paused=true;c.hairPhysics.setEnabled(false);c.update(1/60);
 let shell;c.root.traverse(o=>{if(o.isSkinnedMesh&&o.material?.name==='radial_fur_shell')shell=o;});assert.ok(shell);
 const sample=[];const idx=shell.geometry.attributes.skinIndex,weights=shell.geometry.attributes.skinWeight;
 for(let i=0;i<idx.count;i++){let amount=0;for(let k=0;k<4;k++){if(shell.skeleton.bones[idx.array[i*4+k]]?.name.startsWith('fur_'))amount+=weights.array[i*4+k];}if(amount>.7)sample.push(i);}
 const point=(mesh,i)=>{const v=c.body.position.clone().fromBufferAttribute(mesh.geometry.attributes.position,i);mesh.applyBoneTransform(i,v);return mesh.localToWorld(v);};
 shell.skeleton.update();c.face.skeleton.update();const before=sample.map(i=>point(shell,i)),faceBefore=point(c.face,0);
 c.hairPhysics.setEnabled(true);c.update(1/60);c.hairPhysics.impulse(.7,.2,0);step(c,.1);shell.skeleton.update();c.face.skeleton.update();
 assert.ok(sample.some((id,i)=>point(shell,id).distanceTo(before[i])>.008));assert.ok(point(c.face,0).distanceTo(faceBefore)<.0001);c.dispose();
});
