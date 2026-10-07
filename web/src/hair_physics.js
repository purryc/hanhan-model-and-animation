import * as THREE from 'three';

/** Eight persistent mass/spring guide tips. Animation supplies moving anchors;
 * inertia, spring force, damping and constraints supply secondary motion.
 * No elapsed-time wave or random motion is added. Coordinates are world space. */
export class HairPhysics {
  constructor(root, body, config) {
    this.root=root; this.body=body; this.config=config; this.enabled=true;
    root.updateMatrixWorld(true);
    this.centerLocal=body.worldToLocal(root.localToWorld(new THREE.Vector3(...config.center)));
    this.guides=config.bones.map(spec=>{
      const bone=root.getObjectByName(spec.name);
      if(!bone?.isBone)throw new Error('Missing hair guide: '+spec.name);
      return {bone,length:spec.length,base:bone.quaternion.clone(),position:new THREE.Vector3(),velocity:new THREE.Vector3(),target:new THREE.Vector3(),previousTarget:new THREE.Vector3(),anchor:new THREE.Vector3(),previousAnchor:new THREE.Vector3()};
    });
    this.initialized=false;this.maxDisplacement=0;this.maxSpeed=0;
    this.center=new THREE.Vector3();this.target=new THREE.Vector3();this.anchor=new THREE.Vector3();this.force=new THREE.Vector3();this.offset=new THREE.Vector3();this.normal=new THREE.Vector3();this.restDirection=new THREE.Vector3();this.simDirection=new THREE.Vector3();
    this.delta=new THREE.Quaternion();this.world=new THREE.Quaternion();this.parent=new THREE.Quaternion();
  }
  restore(){for(const g of this.guides)g.bone.quaternion.copy(g.base);}
  reset(){this.restore();this.initialized=false;for(const g of this.guides)g.velocity.set(0,0,0);this.maxDisplacement=0;this.maxSpeed=0;}
  setEnabled(value){this.enabled=Boolean(value);this.reset();}
  impulse(x,y,z){if(![x,y,z].every(Number.isFinite))throw new TypeError('Hair impulse must be finite');for(const g of this.guides)g.velocity.add(new THREE.Vector3(x,y,z).clampLength(0,2));}
  update(dt){
    if(!this.enabled)return;
    if(!Number.isFinite(dt)||dt<=0)return;
    if(dt>.12){this.reset();dt=1/60;}
    const c=this.config;this.root.updateMatrixWorld(true);this.center.copy(this.centerLocal);this.body.localToWorld(this.center);
    this.maxDisplacement=0;this.maxSpeed=0;
    const count=Math.max(1,Math.ceil(dt*120)),h=dt/count;
    for(const g of this.guides){
      g.base.copy(g.bone.quaternion);g.bone.getWorldPosition(g.anchor);g.target.set(0,g.length,0);g.bone.localToWorld(g.target);
      if(!this.initialized){g.position.copy(g.target);g.previousTarget.copy(g.target);g.previousAnchor.copy(g.anchor);g.velocity.set(0,0,0);}
      for(let j=1;j<=count;j++){
        this.target.copy(g.previousTarget).lerp(g.target,j/count);this.anchor.copy(g.previousAnchor).lerp(g.anchor,j/count);
        this.force.copy(this.target).sub(g.position).multiplyScalar(c.stiffness);this.force.y-=c.gravity;
        g.velocity.addScaledVector(this.force,h).multiplyScalar(Math.exp(-c.damping*h));g.position.addScaledVector(g.velocity,h);
        // Inextensible guide length and a spherical inner head collider.
        this.offset.copy(g.position).sub(this.anchor).normalize().multiplyScalar(g.length);g.position.copy(this.anchor).add(this.offset);g.velocity.addScaledVector(this.offset,-g.velocity.dot(this.offset)/(g.length*g.length));
        this.normal.copy(g.position).sub(this.center);
        if(this.normal.length()<c.collision_radius){this.normal.normalize();g.position.copy(this.center).addScaledVector(this.normal,c.collision_radius);const inward=g.velocity.dot(this.normal);if(inward<0)g.velocity.addScaledVector(this.normal,-inward);}
        this.offset.copy(g.position).sub(this.target);
        if(this.offset.length()>c.max_offset){this.offset.setLength(c.max_offset);g.position.copy(this.target).add(this.offset);const outward=g.velocity.dot(this.offset.clone().normalize());if(outward>0)g.velocity.addScaledVector(this.offset,-outward/c.max_offset);}
      }
      this.maxDisplacement=Math.max(this.maxDisplacement,g.position.distanceTo(g.target));this.maxSpeed=Math.max(this.maxSpeed,g.velocity.length());
      this.restDirection.copy(g.target).sub(g.anchor).normalize();this.simDirection.copy(g.position).sub(g.anchor).normalize();this.delta.setFromUnitVectors(this.restDirection,this.simDirection);
      g.bone.getWorldQuaternion(this.world);g.bone.parent.getWorldQuaternion(this.parent).invert();g.bone.quaternion.copy(this.parent.multiply(this.delta).multiply(this.world));
      g.previousTarget.copy(g.target);g.previousAnchor.copy(g.anchor);
    }
    this.initialized=true;this.root.updateMatrixWorld(true);
  }
}
