import * as THREE from 'three';

// Optional reference symbols live outside the skinned body. One small texture/pass.
export class StateAccents {
  constructor(scene) {
    this.canvas=document.createElement('canvas');this.canvas.width=this.canvas.height=256;
    this.ctx=this.canvas.getContext('2d');this.texture=new THREE.CanvasTexture(this.canvas);
    this.texture.colorSpace=THREE.SRGBColorSpace;
    this.sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:this.texture,transparent:true,depthWrite:false}));
    this.sprite.scale.set(.40,.40,1);this.sprite.position.set(.72,2.06,.12);scene.add(this.sprite);
    this.state=null;
  }
  update(state,visible,time) {
    this.sprite.visible=visible&&!['briefing','review','playful'].includes(state);
    if(state!==this.state){this.state=state;this.paint(state);}
    this.sprite.position.y=2.06+Math.sin(time*2)*.015;
  }
  paint(state) {
    const c=this.ctx;c.clearRect(0,0,256,256);c.lineCap='round';c.lineJoin='round';c.lineWidth=12;
    const line=(pts,color='#4e91ee',width=12)=>{c.strokeStyle=color;c.lineWidth=width;c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();};
    const circle=(x,y,r,color)=>{c.fillStyle=color;c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fill();};
    const star=(x,y,r)=>{c.fillStyle='#ffd24e';c.beginPath();for(let i=0;i<8;i++){const a=i*Math.PI/4,rr=i%2?r*.32:r;const px=x+Math.sin(a)*rr,py=y+Math.cos(a)*rr;i?c.lineTo(px,py):c.moveTo(px,py);}c.closePath();c.fill();};
    const gear=(x,y,r,color)=>{c.strokeStyle=color;c.lineWidth=23;c.beginPath();c.arc(x,y,r*.64,0,Math.PI*2);c.stroke();for(let i=0;i<8;i++){let a=i*Math.PI/4;line([[x+Math.cos(a)*r*.6,y+Math.sin(a)*r*.6],[x+Math.cos(a)*r,y+Math.sin(a)*r]],color,23);}};
    if(state==='awaken'){circle(128,128,42,'#ffd047');for(let i=0;i<8;i++){const a=i*Math.PI/4;line([[128+Math.cos(a)*65,128+Math.sin(a)*65],[128+Math.cos(a)*86,128+Math.sin(a)*86]],'#ffd047',10);}}
    if(state==='idle'){star(90,96,47);star(165,156,33);}
    if(state==='listen'){[48,88,128,168,208].forEach((x,i)=>line([[x,128-[24,47,70,47,24][i]],[x,128+[24,47,70,47,24][i]]]));}
    if(state==='think'){[64,128,192].forEach(x=>circle(x,128,15,'#8870ec'));}
    if(state==='speak'){c.fillStyle='#4e91ee';c.beginPath();[[48,102],[80,102],[118,68],[118,188],[80,154],[48,154]].forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fill();for(const r of [47,76]){c.strokeStyle='#4e91ee';c.lineWidth=12;c.beginPath();c.arc(116,128,r,-.8,.8);c.stroke();}}
    if(state==='working'){gear(104,108,58,'#4e91ee');line([[190,156],[178,184],[183,198],[198,202],[212,193],[214,180],[190,156]],'#60c8f4',9);}
    if(state==='progress'){c.strokeStyle='#4e91ee';c.lineWidth=10;c.beginPath();c.roundRect(24,98,208,59,28);c.stroke();c.fillStyle='#97cc26';c.beginPath();c.roundRect(33,107,119,41,19);c.fill();}
    if(state==='decision'){c.fillStyle='#f6bd22';c.font='bold 180px sans-serif';c.textAlign='center';c.fillText('?',128,194);}
    if(state==='pause'){line([[99,75],[99,181]],'#e7ae28',26);line([[157,75],[157,181]],'#e7ae28',26);}
    if(state==='resume'){c.fillStyle='#21c59e';c.beginPath();c.moveTo(88,58);c.lineTo(198,128);c.lineTo(88,198);c.closePath();c.fill();}
    if(state==='alert'){line([[105,54],[105,121]],'#ffa735',15);circle(105,151,8,'#ffa735');line([[52,102],[34,79]],'#ffa735',10);line([[158,102],[179,79]],'#ffa735',10);}
    if(state==='error'){gear(57,184,36,'#9b91d5');line([[27,40],[50,26],[70,35],[33,67],[21,54],[58,29],[70,48],[42,80]],'#9b91d5',5);c.save();c.translate(86,18);c.scale(.65,.65);c.fillStyle='#f15d68';c.beginPath();c.moveTo(120,29);c.lineTo(226,207);c.lineTo(19,207);c.closePath();c.fill();line([[121,86],[121,143]],'#fff',14);circle(121,173,8,'#fff');c.restore();c.globalCompositeOperation='destination-out';line([[65,145],[48,175],[62,190],[47,218]],'#000',7);c.globalCompositeOperation='source-over';}
    this.texture.needsUpdate=true;
  }
  dispose(){this.sprite.material.dispose();this.texture.dispose();this.sprite.removeFromParent();}
}
