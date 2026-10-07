import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {HanhanController} from './hanhan_controller.js';
import {BodyInteraction} from './body_interaction.js';
import {LaughAudio} from './laugh_audio.js';
import {StateAccents} from './state_accents.js';
import {initialLanguage,translate,stateLabel} from './i18n.js';
import './style.css';
const $ = s => document.querySelector(s);
const canvas=$('#hero'), stage=$('#stage');
let savedLanguage;try{savedLanguage=localStorage.getItem('hanhan-language');}catch{}
let language=initialLanguage({search:location.search,saved:savedLanguage,browserLanguage:navigator.language});
const t=(key,values)=>translate(language,key,values);
const label=name=>stateLabel(language,name);
const assetUrl=name=>`${import.meta.env.BASE_URL}assets/${name}`;
let assetMetrics=null,recordMessage=null,lastFps=null;
function setRecordMessage(key,params={},saved=false){recordMessage={key,params,saved};renderRecordMessage();}
function renderRecordMessage(){if(!recordMessage)return;const params={...recordMessage.params};if(params.name)params.state=label(params.name);$('#record-status').textContent=t(recordMessage.key,params)+(recordMessage.saved?t('savedLocal'):'');}

const laughAudio=new LaughAudio(assetUrl('hanhan_laugh_v1.wav'));
document.addEventListener('pointerdown',()=>void laughAudio.unlock(),{capture:true});
document.addEventListener('keydown',()=>void laughAudio.unlock(),{capture:true});
const renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(30,1,.01,100);
camera.position.set(0,1.23,5.5);camera.lookAt(0,1.12,0);
scene.add(new THREE.HemisphereLight(0xfff3e3,0x46567b,2.1));
const key=new THREE.DirectionalLight(0xffeddf,3.2);key.position.set(-3,5,4);scene.add(key);
const fill=new THREE.DirectionalLight(0xd3dfff,1.4);fill.position.set(4,2,-3);scene.add(fill);
const requestedVersion=new URLSearchParams(location.search).get('version');
const version=requestedVersion==='3'?3:requestedVersion==='4'?4:requestedVersion==='4.1'?'4.1':requestedVersion==='4.2'?'4.2':requestedVersion==='4.3'?'4.3':requestedVersion==='4.4'?'4.4':requestedVersion==='4.5'?'4.5':requestedVersion==='4.6'?'4.6':'4.7';
const assetStem=version===3?'hanhan_mobile_v3':version===4?'hanhan_rodin_v4':version==='4.1'?'hanhan_rodin_v4_1':version==='4.2'?'hanhan_rodin_v4_2':version==='4.3'?'hanhan_rodin_v4_3':version==='4.4'?'hanhan_rodin_v4_4':version==='4.5'?'hanhan_rodin_v4_5':version==='4.6'?'hanhan_rodin_v4_6':'hanhan_rodin_v4_7';
const manifest=await fetch(assetUrl(assetStem+'_states.json')).then(r=>r.json());
$('.edition').textContent=version===3?'03 / MOBILE':version===4?'04 / RODIN':version==='4.1'?'04.1 / PLAY':version==='4.2'?'04.2 / REFINED':version==='4.3'?'04.3 / ALIVE':version==='4.4'?'04.4 / SOFT':version==='4.5'?'04.5 / GAZE':version==='4.6'?'04.6 / LOOK':'04.7 / FACE';
$('#model-download').href=assetUrl(manifest.asset);
$('#video-download').download=assetStem+'_overview.webm';
const accents=['4.2','4.3','4.4','4.5','4.6','4.7'].includes(version)?new StateAccents(scene):null;
let controller,model,bodyInteraction,raf=0,last=0,frames=0,elapsed=0,recording=null,angle='front';
function renderAssetInfo(){if(!assetMetrics)return;$('#asset-info').textContent=t('assetInfo',assetMetrics);$('#metrics').innerHTML=`<dt>${t('size')}</dt><dd>${assetMetrics.size} MiB</dd><dt>${t('clips')}</dt><dd>${assetMetrics.clips}</dd><dt>${t('bones')}</dt><dd>${assetMetrics.bones}</dd>`;}
function applyLanguage(){
 document.documentElement.lang=language==='zh'?'zh-CN':'en';document.title=t('title');
 document.querySelectorAll('[data-i18n]').forEach(el=>el.textContent=t(el.dataset.i18n));
 document.querySelectorAll('[data-i18n-aria]').forEach(el=>el.setAttribute('aria-label',t(el.dataset.i18nAria)));
 document.querySelectorAll('[data-lang]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.lang===language)));
 document.querySelectorAll('#states button[data-state]').forEach(button=>{const number=button.querySelector('span');button.replaceChildren(number,document.createTextNode(label(button.dataset.state)));});
 if(controller){syncState(controller.state);$('#active').textContent=t(controller.active?'pausePreview':'resumePreview');}
 renderAssetInfo();renderRecordMessage();if(lastFps!==null)$('#runtime-info').textContent=t('fps',{fps:lastFps});
 if(canvas.dataset.error)$('#loading').textContent=t('loadError');
}
document.querySelectorAll('[data-lang]').forEach(button=>button.onclick=()=>{language=button.dataset.lang;try{localStorage.setItem('hanhan-language',language);}catch{}const url=new URL(location.href);url.searchParams.set('lang',language);history.replaceState(null,'',url);applyLanguage();});
applyLanguage();

const small=[...document.querySelectorAll('[data-size]')].map(c=>{c.style.width=c.dataset.size+'px';c.style.height=c.dataset.size+'px';return {canvas:c,ctx:c.getContext('2d')};});
function resize(){const r=stage.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe(stage);
function setAngle(view){angle=view;const target=new THREE.Vector3(0,1.12,0);camera.position.set(...({front:[0,1.23,5.5],side:[5.5,1.23,0],rear:[0,1.23,-5.5]}[view]));camera.lookAt(target);document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===view)));}
function syncState(name){$('#state-name').textContent=label(name);document.querySelectorAll('#states button[data-state]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.state===name)));canvas.dataset.state=name;}
function draw(){accents?.update(controller.state,controller.showProps,controller.clock);renderer.render(scene,camera);for(const s of small){const w=canvas.width,h=canvas.height,d=Math.min(w,h);s.ctx.clearRect(0,0,s.canvas.width,s.canvas.height);s.ctx.drawImage(canvas,(w-d)/2,(h-d)/2,d,d,0,0,s.canvas.width,s.canvas.height);}canvas.dataset.hairOffset=(controller.hairPhysics?.maxDisplacement??0).toFixed(5);canvas.dataset.hairSpeed=(controller.hairPhysics?.maxSpeed??0).toFixed(5);canvas.dataset.sound=laughAudio.status;canvas.dataset.audioRms=laughAudio.rms().toFixed(5);canvas.dataset.drawCalls=renderer.info.render.calls;canvas.dataset.triangles=renderer.info.render.triangles;canvas.dataset.mouth=controller.morph('mouth_open').toFixed(4);canvas.dataset.viseme=controller.viseme??'';canvas.dataset.visemeWeights=controller.visemeWeights.map(v=>v.toFixed(3)).join(',');canvas.dataset.blink=controller.morph('blink').toFixed(4);canvas.dataset.gaze=controller.eyeOffsets.map(v=>[v.x,v.y]);canvas.dataset.happy=controller.morph('happy').toFixed(4);canvas.dataset.touch=controller.touchWeight.toFixed(4);canvas.dataset.mixerTime=controller.mixer.time.toFixed(3);}
function tick(ms){raf=0;if(!controller?.active || document.hidden)return;const dt=last?Math.min((ms-last)/1000,.1):1/60;last=ms;
 if($('#voice-auto').checked){const level=Math.max(0,Math.sin(ms*.012))*(.5+.4*Math.sin(ms*.003)**2);controller.setSpeechLevel(level);if(manifest.visemes&&level>.02)controller.setViseme(manifest.visemes[Math.floor(ms/230)%5],level);}
 controller.update(dt);draw();frames++;elapsed+=dt;
 if(elapsed>1){lastFps=Math.round(frames/elapsed);$('#runtime-info').textContent=t('fps',{fps:lastFps});frames=0;elapsed=0;}
 if(recording)recordFrame(ms);
 raf=requestAnimationFrame(tick);
}
function run(){if(!raf&&controller?.active&&!document.hidden){last=0;raf=requestAnimationFrame(tick);}}
function active(value){controller.setActive(value);$('#active').textContent=t(value?'pausePreview':'resumePreview');$('#active').setAttribute('aria-pressed',String(!value));canvas.dataset.active=String(value);if(value)run();else{cancelAnimationFrame(raf);raf=0;draw();}}
try{
 const gltf=await new GLTFLoader().loadAsync(assetUrl(manifest.asset));model=gltf.scene;scene.add(model);controller=new HanhanController(gltf,manifest);controller.onStateChange=syncState;$('#props').checked=controller.showProps;controller.onLaugh=({kind})=>void laughAudio.play({delay:kind==='playful'?.18:0});controller.onLaughStop=()=>laughAudio.stop();bodyInteraction=new BodyInteraction(controller,camera);
 const info=await fetch(assetUrl(manifest.asset)).then(r=>r.arrayBuffer());
 assetMetrics={size:(info.byteLength/1048576).toFixed(2),clips:gltf.animations.length,morphs:Object.keys(controller.face.morphTargetDictionary).length,bones:(()=>{let n=0;model.traverse(o=>{if(o.isBone)n++});return n})()};renderAssetInfo();
 Object.entries(manifest.states).forEach(([name,spec],i)=>{const b=document.createElement('button');b.dataset.state=name;b.innerHTML=`<span>${String(i+1).padStart(2,'0')}</span>${label(name)}`;b.onclick=()=>controller.setState(name);$('#states').append(b);});
 $('#viseme-controls').hidden=!manifest.visemes;document.querySelectorAll('[data-viseme]').forEach(button=>button.onclick=()=>{$('#voice-auto').checked=false;controller.setState('speak');controller.setSpeechLevel(0);controller.setViseme(button.dataset.viseme||null);$('#speech').value=0;$('#speech-value').value='0%';});$('#state-count').textContent=gltf.animations.length;$('#loading').hidden=true;syncState('idle');canvas.dataset.ready='true';canvas.dataset.active='true';resize();run();
}catch(e){$('#loading').textContent=t('loadError');canvas.dataset.error=e.message;console.error(e);}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setAngle(b.dataset.view));
$('#speech').oninput=e=>{controller.setSpeechLevel(Number(e.target.value));$('#speech-value').value=Math.round(e.target.value*100)+'%';if(e.target.value>0&&!['speak','briefing'].includes(controller.state))controller.setState('speak');};
$('#voice-auto').onchange=e=>{if(e.target.checked)controller.setState('speak');else controller.setSpeechLevel(Number($('#speech').value));};
$('#hair-physics').hidden=!manifest.hair_physics;$('#hair-physics-toggle').onchange=e=>controller.hairPhysics?.setEnabled(e.target.checked);
$('#props').onchange=e=>controller.setPropsVisible(e.target.checked);
$('#sound').onchange=e=>{laughAudio.setEnabled(e.target.checked);if(e.target.checked)void laughAudio.unlock();};
$('#active').onclick=()=>active(!controller.active);
$('#gaze').onchange=e=>{if(!e.target.checked)controller.setGaze(0,0);};
function pointerReaction(e, pressed=false){
 if(!controller || recording)return;
 const r=canvas.getBoundingClientRect();
 if($('#gaze').checked){
  const face=model.getObjectByName('head').getWorldPosition(new THREE.Vector3()).project(camera);
  const cx=r.left+(face.x+1)*r.width/2,cy=r.top+(1-face.y)*r.height/2;
  controller.setGaze((e.clientX-cx)/(r.width*.22),(cy-e.clientY)/(r.height*.26));
 }
 const within=e.clientX>=r.left&&e.clientX<=r.right&&e.clientY>=r.top&&e.clientY<=r.bottom;
 if(within){const result=bodyInteraction.move(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,1-(e.clientY-r.top)/r.height*2),pressed);canvas.style.cursor=result.hit?'pointer':'';if(pressed&&result.hit&&!result.triggered&&controller.touchWeight>0&&!laughAudio.hasVoice)void laughAudio.play({offset:controller.touchElapsed});}
 else {bodyInteraction.leave();canvas.style.cursor='';}
}
window.addEventListener('pointermove',e=>pointerReaction(e));
canvas.addEventListener('pointerdown',e=>pointerReaction(e,true));
canvas.addEventListener('pointerleave',()=>bodyInteraction?.leave());
window.addEventListener('blur',()=>{controller?.setGaze(0,0);bodyInteraction?.leave();});
let manuallyPaused=false;
document.addEventListener('visibilitychange',()=>{if(!controller)return;if(document.hidden){manuallyPaused=!controller.active;active(false);if(recording)stopRecord(true);}else if(!manuallyPaused)active(true);});
// Public bridge: no credentials, audio capture, network inference or Android modification.
window.hanhan={setState:n=>controller.setState(n),setGaze:(x,y)=>controller.setGaze(x,y),setSpeechLevel:v=>controller.setSpeechLevel(v),setViseme:(name,amount)=>controller.setViseme(name,amount),setActive:active,touchBody:()=>controller.touchBody()};

const sequences=Object.entries(manifest.states);let recordUrl=null;
$('#record').onclick=async()=>{
 if(!window.MediaRecorder || !HTMLCanvasElement.prototype.captureStream){setRecordMessage('recordUnsupported');return;}
 const previousGaze=$('#gaze').checked;await laughAudio.unlock();active(true);setAngle('front');$('#voice-auto').checked=false;controller.setGaze(0,0);$('#gaze').checked=false;
 const c=document.createElement('canvas');c.width=c.height=960;const ctx=c.getContext('2d');const stream=c.captureStream(30);const soundStream=laughAudio.captureStream();soundStream?.getAudioTracks().forEach(track=>stream.addTrack(track));
 const mime=['video/webm;codecs=vp9,opus','video/webm;codecs=vp8,opus','video/webm'].find(t=>MediaRecorder.isTypeSupported(t));
 const recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:6000000});const chunks=[];
 recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};recorder.onstop=async()=>{laughAudio.stopCapture();stream.getTracks().forEach(t=>t.stop());if(recordUrl)URL.revokeObjectURL(recordUrl);const blob=new Blob(chunks,{type:'video/webm'});recordUrl=URL.createObjectURL(blob);$('#video-download').href=recordUrl;$('#video-download').hidden=false;$('#record').disabled=false;
   if(import.meta.env.DEV){try{const saved=await fetch('/local-export/overview?version='+version,{method:'POST',headers:{'Content-Type':'video/webm'},body:blob});if(saved.ok&&recordMessage){recordMessage.saved=true;renderRecordMessage();};}catch{/* Browser download remains available. */}}
 };
 recording={canvas:c,ctx,recorder,index:0,start:0,previousGaze};controller.setState(sequences[0][0]);$('#record').disabled=true;$('#video-download').hidden=true;recorder.start();
};
function stopRecord(interrupted=false){const r=recording;recording=null;$('#gaze').checked=r.previousGaze;r.recorder.stop();laughAudio.stop();controller.setSpeechLevel(0);setRecordMessage(interrupted?'recordInterrupted':'recordDone');}
function recordFrame(ms){const r=recording;if(!r.start)r.start=ms;const [name,spec]=sequences[r.index];const t=(ms-r.start)/1000;
 // Override automatic next state during its last fraction, without changing the asset.
 if(t>=spec.duration+.25){r.index++;if(r.index>=sequences.length){stopRecord();return;}r.start=ms;controller.setState(sequences[r.index][0]);return;}
 if(['speak','briefing'].includes(name)){const level=Math.max(0,Math.sin(ms*.013))*.85;controller.setSpeechLevel(level);if(manifest.visemes&&level>.02)controller.setViseme(manifest.visemes[Math.floor(ms/260)%5],level);}else controller.setSpeechLevel(0);
 const c=r.ctx;c.fillStyle='#f4f2ed';c.fillRect(0,0,960,960);c.fillStyle='#263761';c.font='500 27px sans-serif';c.fillText(language==='zh'?'HANHAN / 憨憨':'HANHAN',60,70);c.font='16px sans-serif';c.fillStyle='#747a84';c.fillText(t('mobileCharacter')+' · V'+version,650,70);
 const d=Math.min(canvas.width,canvas.height);c.drawImage(canvas,(canvas.width-d)/2,(canvas.height-d)/2,d,d,120,140,720,720);
 c.fillStyle='#263761';c.font='500 30px sans-serif';c.fillText(label(name),60,900);c.font='18px sans-serif';c.fillStyle='#747a84';c.fillText(name.toUpperCase(),60,929);c.fillText(`${String(r.index+1).padStart(2,'0')} / ${sequences.length}`,825,910);
 setRecordMessage('recording',{index:r.index+1,total:sequences.length,name});
}
window.addEventListener('pagehide',()=>{controller?.dispose();laughAudio.dispose();renderer.dispose();accents?.dispose();if(recordUrl)URL.revokeObjectURL(recordUrl);});
