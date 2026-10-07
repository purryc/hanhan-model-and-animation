import * as THREE from 'three';
import {HairPhysics} from './hair_physics.js';
import {GazeSurface} from './gaze_surface.js';

/** Renderer-independent controller. Coordinates: x right, y up, each [-1,1]. */
export class HanhanController {
  constructor(gltf, manifest) {
    this.root = gltf.scene; this.manifest = manifest; this.mixer = new THREE.AnimationMixer(this.root);
    this.actions = new Map(gltf.animations.map(c => [c.name, this.mixer.clipAction(c)]));
    for (const name of Object.keys(manifest.states)) if (!this.actions.has(name)) throw new Error(`Missing clip: ${name}`);
    this.face = null; this.eyes = []; this.props = []; this.body = null;
    this.touchElapsed = Infinity; this.touchCooldown = 0; this.bodyBeforeTouch = null; this.touchWeight = 0;
    this.root.traverse(o => {
      if (o.morphTargetDictionary?.mouth_open !== undefined) this.face = o;
      if (o.isBone && o.name === 'body') this.body = o;
      if (/^eye_[lr]$/.test(o.name)) this.eyes.push(o);
      if (o.name.startsWith('prop_') && o.isMesh) this.props.push(o);
      if (o.isMesh) o.frustumCulled = false;
    });
    if (!this.face || this.eyes.length !== 2) throw new Error('Face controls or gaze bones missing');
    this.eyeOffsets = this.eyes.map(() => new THREE.Vector3()); this.faceBase = null;
    this.active = true; this.gaze = new THREE.Vector2(); this.gazeSmooth = new THREE.Vector2();
    this.viseme = null; this.visemeStrength = 0; this.visemeWeights = [0,0,0,0,0];
    this.voice = 0; this.voiceSmooth = 0; this.clock = 0; this.generation = 0; this.showProps = Boolean(manifest.default_props_visible);
    this.finished = e => {
      if (!this.active || e.action !== this.currentAction) return;
      const next = this.manifest.states[this.state].next;
      if (next) this.setState(next);
    };
    this.hairPhysics=manifest.hair_physics?new HairPhysics(this.root,this.body,manifest.hair_physics):null;
    this.gazeSurface=manifest.gaze_surface?new GazeSurface(this,manifest.gaze_surface):null;
    this.mixer.addEventListener('finished', this.finished); this.setState('idle');
  }
  setState(name) {
    const spec = this.manifest.states[name]; if (!spec) throw new RangeError(`Unknown state: ${name}`);
    if (name === this.state) return;
    this.onLaughStop?.(); this.gazeSurface?.restore(); this.restoreTouchBody(); this.touchElapsed = Infinity; this.touchWeight = 0;
    const old = this.currentAction;
    for (const action of this.actions.values()) if (action !== old) action.stop();
    this.state = name; if(!['speak','briefing'].includes(name))this.setViseme(null); this.generation++; this.currentAction = this.actions.get(name);
    const next = this.currentAction; next.reset().setEffectiveTimeScale(1).setEffectiveWeight(1);
    next.setLoop(spec.loop ? THREE.LoopRepeat : THREE.LoopOnce, spec.loop ? Infinity : 1);
    next.clampWhenFinished = !spec.loop;
    if (old) { old.fadeOut(this.manifest.blend_seconds); next.fadeIn(this.manifest.blend_seconds); }
    next.play(); this.updateProps(); this.onStateChange?.(name);
    if (name === 'playful' && this.active) this.onLaugh?.({kind:'playful'});
  }
  setGaze(x, y) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) throw new TypeError('Gaze must be finite');
    this.gaze.set(THREE.MathUtils.clamp(x, -1, 1), THREE.MathUtils.clamp(y*(y<0?(this.manifest.gaze_surface?.down_gain??1):1), -1, 1));
  }
  setSpeechLevel(value) {
    if (!Number.isFinite(value)) throw new TypeError('Speech level must be finite');
    this.voice = THREE.MathUtils.clamp(value, 0, 1);
    if(this.voice===0)this.setViseme(null);
  }
  setViseme(name, strength=1) {
    if(name!==null && !['A','E','I','O','U'].includes(name))throw new RangeError('Unknown viseme: '+name);
    if(!Number.isFinite(strength))throw new TypeError('Viseme strength must be finite');
    this.viseme=name;this.visemeStrength=THREE.MathUtils.clamp(strength,0,1);
    if(name===null || this.visemeStrength===0){this.viseme=null;this.visemeWeights.fill(0);for(const vowel of ['a','e','i','o','u'])if(this.face?.morphTargetDictionary['viseme_'+vowel]!==undefined)this.setMorph('viseme_'+vowel,0);}
  }
  setActive(value) {
    const active = Boolean(value); if (this.active === active) return;
    this.gazeSurface?.reset(); this.active = active; this.generation++; this.voice = 0; this.hairPhysics?.reset();
    if (!active) { this.setViseme(null); this.onLaughStop?.(); this.voiceSmooth = 0; this.touchElapsed = Infinity; this.touchWeight = 0; this.touchCooldown = 0; this.restoreTouchBody(); if (this.faceBase) this.face.morphTargetInfluences.splice(0, this.faceBase.length, ...this.faceBase); this.setMorph('mouth_open', 0); }
  }
  touchBody() {
    if (!this.active || !this.manifest.interaction || this.touchCooldown > 0) return false;
    this.touchElapsed = 0; this.touchCooldown = this.manifest.interaction.touch_cooldown;
    this.onLaugh?.({kind:'touch'});
    return true;
  }
  restoreTouchBody() {
    if (this.bodyBeforeTouch && this.body) {
      this.body.position.copy(this.bodyBeforeTouch.position);
      this.body.quaternion.copy(this.bodyBeforeTouch.quaternion);
      this.bodyBeforeTouch = null;
    }
  }
  setPropsVisible(value) { this.showProps = Boolean(value); this.updateProps(); }
  updateProps() {
    const names = this.manifest.states[this.state].props;
    this.props.forEach(o => { o.visible = this.showProps && names.includes(o.name); });
  }
  morph(name) { return this.face.morphTargetInfluences[this.face.morphTargetDictionary[name]] || 0; }
  setMorph(name, value) { this.face.morphTargetInfluences[this.face.morphTargetDictionary[name]] = THREE.MathUtils.clamp(value, 0, 1); }
  update(dt) {
    if (!this.active) return;
    dt = THREE.MathUtils.clamp(dt, 0, .1); this.clock += dt;
    this.hairPhysics?.restore(); this.gazeSurface?.restore(); this.restoreTouchBody(); this.touchCooldown = Math.max(0, this.touchCooldown-dt);
    this.eyes.forEach((eye,i) => { eye.position.x -= this.eyeOffsets[i].x; eye.position.y -= this.eyeOffsets[i].y; eye.position.z -= this.eyeOffsets[i].z; });
    if (this.faceBase) this.face.morphTargetInfluences.splice(0, this.faceBase.length, ...this.faceBase);
    this.mixer.update(dt);
    this.faceBase = this.face.morphTargetInfluences.slice();
    const blend = 1 - Math.exp(-dt * (this.manifest.gaze_surface?.eye_response ?? 15));
    this.gazeSmooth.lerp(this.gaze, blend);
    this.voiceSmooth += (this.voice - this.voiceSmooth) * (1 - Math.exp(-dt * 22));
    if (['speak','briefing'].includes(this.state)) this.setMorph('mouth_open', this.voiceSmooth * .9);
    if(this.manifest.visemes){
      const speaking=['speak','briefing'].includes(this.state);
      if(speaking && this.viseme){
        for(const n of ['mouth_open','mouth_round','mouth_smile','mouth_frown'])this.setMorph(n,0);
        this.manifest.visemes.forEach((v,i)=>{const target=v===this.viseme?this.visemeStrength:0;this.visemeWeights[i]+=(target-this.visemeWeights[i])*(1-Math.exp(-dt*24));this.setMorph('viseme_'+v.toLowerCase(),this.visemeWeights[i]);});
      }
    }
    this.touchElapsed += dt;
    const left = (this.manifest.interaction?.touch_duration ?? 0) - this.touchElapsed;
    this.touchWeight = Math.max(0, Math.min(1, this.touchElapsed/.12, left/.35));
    if (this.touchWeight > 0) {
      for(const vowel of this.manifest.visemes??[])this.setMorph('viseme_'+vowel.toLowerCase(),this.morph('viseme_'+vowel.toLowerCase())*(1-this.touchWeight));
      const w = this.touchWeight, laugh = Math.sin(this.touchElapsed*Math.PI*6);
      for (const name of ['blink','squeeze','spiral']) this.setMorph(name, this.morph(name)*(1-w));
      this.setMorph('happy', THREE.MathUtils.lerp(this.morph('happy'),1,w));
      this.setMorph('mouth_smile', THREE.MathUtils.lerp(this.morph('mouth_smile'),1,w));
      this.setMorph('mouth_open', THREE.MathUtils.lerp(this.morph('mouth_open'),.35+.20*Math.abs(laugh),w));
      if (this.body) {
        this.bodyBeforeTouch = {position:this.body.position.clone(),quaternion:this.body.quaternion.clone()};
        this.body.position.y += .012*Math.abs(laugh)*w;
        this.body.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),.055*laugh*w));
      }
    }
    const block = Math.max(this.morph('blink'), this.morph('happy'), this.morph('squeeze'), this.morph('spiral'));
    for (const [i, eye] of this.eyes.entries()) {
      // Clip tracks restore baseline each mixer update; post-animation offsets do not accumulate.
      this.eyeOffsets[i].set(this.gazeSmooth.x * (this.manifest.runtime_gaze_scale?.[0] ?? .024) * (1-block), this.gazeSmooth.y * (this.gazeSmooth.y<0?(this.manifest.gaze_surface?.down_scale??this.manifest.runtime_gaze_scale?.[1]??.019):(this.manifest.runtime_gaze_scale?.[1]??.019)) * (1-block), Math.max(0,-this.gazeSmooth.y)**2*(this.manifest.gaze_surface?.down_forward??0)*(1-block));
      eye.position.x += this.eyeOffsets[i].x;
      eye.position.y += this.eyeOffsets[i].y;
      eye.position.z += this.eyeOffsets[i].z;
    }
    this.gazeSurface?.update(dt,block);
    this.root.updateMatrixWorld(true); this.hairPhysics?.update(dt);
  }
  dispose() { this.onLaughStop?.(); this.mixer.removeEventListener('finished', this.finished); this.mixer.stopAllAction(); this.mixer.uncacheRoot(this.root); }
}
