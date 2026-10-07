/** Local sample playback. No network voice service, microphone, or delayed autoplay. */
export class LaughAudio {
  constructor(url, {contextFactory=()=>new AudioContext(), fetcher=fetch, now=()=>performance.now()}={}) {
    this.contextFactory=contextFactory; this.now=now; this.enabled=true; this.armed=false;
    this.context=null; this.voice=null; this.pending=false; this.ticket=0; this.failed=false;
    this.bytes=fetcher(url).then(r=>{if(!r.ok)throw new Error('Laugh audio unavailable');return r.arrayBuffer();}).catch(()=>{this.failed=true;return null;});
  }
  unlock() {
    if(!this.enabled)return Promise.resolve();
    try {
      if(!this.context){
        this.context=this.contextFactory(); this.gain=this.context.createGain();this.gain.gain.value=.65;
        this.analyser=this.context.createAnalyser();this.analyser.fftSize=256;this.levels=new Float32Array(256);
        this.gain.connect(this.analyser);this.analyser.connect(this.context.destination);
        this.buffer=this.bytes.then(bytes=>bytes?this.context.decodeAudioData(bytes.slice(0)):null).catch(()=>{this.failed=true;return null;});
      }
      this.armed=true;this.unlocking=this.context.resume().catch(()=>{this.armed=false;});return this.unlocking;
    } catch {this.failed=true;return Promise.resolve();}
  }
  async play({offset=0,delay=0}={}) {
    if(!this.enabled||!this.armed||this.failed)return false;
    this.stop();const ticket=this.ticket,requested=this.now();this.pending=true;
    const [buffer]=await Promise.all([this.buffer,this.unlocking]);
    if(ticket!==this.ticket)return false;
    this.pending=false;
    if(!this.enabled||!buffer||this.context.state!=='running'||this.now()-requested>300||offset>=buffer.duration)return false;
    const source=this.context.createBufferSource();source.buffer=buffer;source.connect(this.gain);this.voice=source;
    source.onended=()=>{source.disconnect();if(this.voice===source)this.voice=null;};
    source.start(this.context.currentTime+delay,Math.max(0,offset));return true;
  }
  stop(){this.ticket++;this.pending=false;if(this.voice){this.voice.onended=null;try{this.voice.stop();}catch{}this.voice.disconnect();this.voice=null;}}
  setEnabled(value){this.enabled=Boolean(value);if(!this.enabled)this.stop();}
  get hasVoice(){return Boolean(this.voice||this.pending);}
  get status(){return !this.enabled?'muted':this.failed?'unavailable':!this.armed?'locked':this.hasVoice?'playing':'ready';}
  rms(){if(!this.analyser)return 0;this.analyser.getFloatTimeDomainData(this.levels);return Math.sqrt(this.levels.reduce((s,x)=>s+x*x,0)/this.levels.length);}
  captureStream(){if(!this.context)return null;this.stopCapture();this.capture=this.context.createMediaStreamDestination();this.gain.connect(this.capture);this.captureClock=this.context.createConstantSource();this.captureClock.offset.value=0;this.captureClock.connect(this.capture);this.captureClock.start();return this.capture.stream;}
  stopCapture(){if(this.capture){this.captureClock?.stop();this.captureClock?.disconnect();this.captureClock=null;this.gain.disconnect(this.capture);this.capture.stream.getTracks().forEach(t=>t.stop());this.capture=null;}}
  dispose(){this.stop();this.stopCapture();this.context?.close();}
}
