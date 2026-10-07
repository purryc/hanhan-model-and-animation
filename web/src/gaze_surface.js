import * as THREE from 'three';

/** Stylized eye-surface rotation with a slower, bounded body/head response. */
export class GazeSurface {
  constructor(controller, config) {
    this.c=controller;this.config=config;this.head=new THREE.Vector2();this.before=null;
    this.q=new THREE.Quaternion();this.parentQ=new THREE.Quaternion();this.rootQ=new THREE.Quaternion();this.delta=new THREE.Quaternion();this.euler=new THREE.Euler(0,0,0,'YXZ');
  }
  restore() { if(this.before){this.c.body.quaternion.copy(this.before);this.before=null;} }
  reset() { this.restore();this.head.set(0,0); }
  update(dt, block) {
    const c=this.c,g=c.gazeSmooth,visible=1-block;
    // L1 clamp keeps diagonal sums <= 1, avoiding additive corner overshoot.
    const divisor=Math.max(1,Math.abs(g.x)+Math.abs(g.y));
    for(const [name,v] of [['gaze_left',-g.x],['gaze_right',g.x],['gaze_up',g.y],['gaze_down',-g.y]]){
      const down=this.config.down_priority&&g.y<0;
      const weight=down?(name==='gaze_down'?-g.y:name==='gaze_up'?0:Math.max(0,v)*(1+g.y)):Math.max(0,v)/divisor;
      c.setMorph(name,weight*visible);
    }
    const strength=this.config.head_states[c.state]??0;
    this.head.lerp(new THREE.Vector2(g.x,g.y).multiplyScalar(strength),1-Math.exp(-dt*this.config.head_response));
    // Contact poses suppress the layer immediately, including during state blends.
    if(!strength || !c.body)return;
    this.before=c.body.quaternion.clone();c.root.updateMatrixWorld(true);
    c.body.getWorldQuaternion(this.q);c.body.parent.getWorldQuaternion(this.parentQ);c.root.getWorldQuaternion(this.rootQ);
    this.euler.set(-this.head.y*(this.head.y<0?(this.config.head_pitch_down??this.config.head_pitch):this.config.head_pitch),this.head.x*this.config.head_yaw,0);
    this.delta.setFromEuler(this.euler).premultiply(this.rootQ).multiply(this.rootQ.clone().invert());
    c.body.quaternion.copy(this.parentQ.invert().multiply(this.delta).multiply(this.q));
  }
}
