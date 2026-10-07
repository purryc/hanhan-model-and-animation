import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {HanhanController} from '../src/hanhan_controller.js';
import {BodyInteraction} from '../src/body_interaction.js';
globalThis.self=globalThis;
globalThis.createImageBitmap=async()=>({width:512,height:512,close(){}});
const data=await fs.readFile(new URL('../public/assets/hanhan_rodin_v4_1.glb',import.meta.url));
const manifest=JSON.parse(await fs.readFile(new URL('../public/assets/hanhan_rodin_v4_1_states.json',import.meta.url),'utf8'));
async function load(){const gltf=await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),'');return {gltf,c:new HanhanController(gltf,manifest)};}
function step(c,s){for(let i=0;i<Math.ceil(s*60);i++)c.update(1/60);}
test('v4.1 has 15 real clips and playful smiles, moves, then returns idle',async()=>{const{gltf,c}=await load();assert.equal(gltf.animations.length,15);assert.ok(data.length<5242880);c.setState('playful');step(c,1.2);assert.ok(c.morph('happy')>.95);assert.ok(c.morph('mouth_open')>.3);step(c,1.5);assert.equal(c.state,'idle');c.dispose();});
test('gaze offset is clearly stronger yet clamped; smile blocks it',async()=>{const{c}=await load();c.setGaze(10,-10);step(c,.7);assert.ok(c.eyeOffsets[0].x>.04);assert.ok(c.eyeOffsets[0].y<-.03);assert.ok(c.eyeOffsets[0].x<=.043);c.touchBody();step(c,.2);assert.ok(c.eyeOffsets[0].length()<.001);step(c,2);assert.ok(c.eyeOffsets[0].x>.04);c.dispose();});
test('touch laugh preserves sitting/working states, moves body and resets cleanly',async()=>{for(const state of ['pause','working']){const{c}=await load();c.setState(state);step(c,.4);const old=c.currentAction;assert.equal(c.touchBody(),true);step(c,.2);assert.equal(c.state,state);assert.equal(c.currentAction,old);assert.ok(c.morph('happy')>.99);assert.ok(c.bodyBeforeTouch);assert.equal(c.touchBody(),false);step(c,2);assert.equal(c.bodyBeforeTouch,null);assert.equal(c.touchWeight,0);assert.ok(c.morph('happy')<.001);c.dispose();}});
test('hit test rejects blank canvas, triggers once on entry and supports a tap',async()=>{const{c}=await load();step(c,.3);const camera=new THREE.PerspectiveCamera(30,1,.01,100);camera.position.set(0,1.23,5.5);camera.lookAt(0,1.12,0);camera.updateMatrixWorld(true);const touch=new BodyInteraction(c,camera);assert.equal(touch.move(new THREE.Vector2(.95,.95)).hit,false);const p=new THREE.Vector2(.25,0);const hit=touch.move(p);assert.equal(hit.hit,true);assert.equal(hit.triggered,true);step(c,2);assert.equal(touch.move(p).triggered,false);assert.equal(touch.move(p,true).triggered,true);c.dispose();});
test('manual state changes and inactive clear transient touch without stale transforms',async()=>{const{c}=await load();c.touchBody();step(c,.3);c.setState('error');step(c,.3);assert.equal(c.touchWeight,0);assert.ok(c.morph('spiral')>.99);step(c,1.5);c.touchBody();step(c,.3);c.setActive(false);assert.equal(c.bodyBeforeTouch,null);assert.equal(c.touchWeight,0);assert.equal(c.morph('mouth_open'),0);assert.equal(c.touchBody(),false);c.setActive(true);step(c,.2);assert.ok(c.morph('spiral')>.99);c.dispose();});
test('audio cues fire only for accepted laughs and stop on state changes or pause',async()=>{const{c}=await load();const events=[];let stops=0;c.onLaugh=e=>events.push(e.kind);c.onLaughStop=()=>stops++;c.setState('playful');assert.deepEqual(events,['playful']);c.setState('idle');assert.equal(c.touchBody(),true);assert.equal(c.touchBody(),false);assert.deepEqual(events,['playful','touch']);c.setActive(false);assert.ok(stops>=3);assert.equal(c.touchBody(),false);c.dispose();});
