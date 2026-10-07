import * as THREE from 'three';

/** Real skinned-mesh hit test. Blank canvas and prop silhouettes never tickle. */
export class BodyInteraction {
  constructor(controller, camera) {
    this.controller=controller; this.camera=camera; this.ray=new THREE.Raycaster(); this.inside=false;
    this.meshes=[];
    controller.root.getObjectByName('hanhan_rodin_body')?.traverse(o=>{if(o.isMesh)this.meshes.push(o);});
  }
  move(point, pressed=false) {
    this.controller.root.updateMatrixWorld(true); this.camera.updateMatrixWorld(true);
    this.ray.setFromCamera(point,this.camera);
    const hit=this.ray.intersectObjects(this.meshes,false).length>0;
    const triggered=hit&&(!this.inside||pressed)?this.controller.touchBody():false;
    this.inside=hit; return {hit,triggered};
  }
  leave(){this.inside=false;}
}
