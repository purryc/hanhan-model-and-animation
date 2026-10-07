"""Frame-deterministic original motion, designed from the user's static references."""
import math
from mathutils import Vector,Matrix,Euler

def ease(t):t=max(0,min(1,t));return t*t*(3-2*t)
def ramp(a,b,t):return ease((t-a)/(b-a))
def beat(p,a,b):
 if p<=a or p>=b:return 0.0
 return math.sin(math.pi*(p-a)/(b-a))**2
def lerp(a,b,t):return Vector(a).lerp(Vector(b),t)
def around(c,rot):return Matrix.Translation(c)@Euler(rot).to_matrix().to_4x4()@Matrix.Translation(-Vector(c))
class Motion:
 def __init__(self,rig,face,origins,rest,manifest,body):
  self.rig=rig;self.face=face;self.origins=origins;self.rest=rest;self.manifest=manifest
  self.foot_points={side:[v.co.copy() for v in body.data.vertices if any(body.vertex_groups[g.group].name=='foot_'+side and g.weight>.99 for g in v.groups)] for side in ['l','r']}
 def assign(self,n,D):
  self.rig.pose.bones[n].matrix=D@self.rest[n]
  import bpy;bpy.context.view_layer.update()
 def segment(self,n,a,b,aa,bb):
  a,b,aa,bb=map(Vector,[a,b,aa,bb]);d=(b-a).normalized();rot=(b-a).rotation_difference(bb-aa).to_matrix().to_4x4();stretch=Matrix.Identity(4);ratio=(bb-aa).length/(b-a).length
  for i in range(3):
   for j in range(3):stretch[i][j]+=(ratio-1)*d[i]*d[j]
  self.assign(n,Matrix.Translation(aa)@rot@stretch@Matrix.Translation(-a))
 def pose(self,state,t,dur):
  p=t/dur;wave=math.sin(math.tau*p);pulse=.5-.5*math.cos(math.tau*p)
  idle={'l':Vector((.28,-1.02,.90)),'r':Vector((-.28,-1.02,.90))}
  hands={k:v.copy() for k,v in idle.items()};rot={k:[0,0,math.pi] for k in hands};curl={k:[.55,.55,.55,.55] for k in hands}
  expr={k:0 for k in ['blink','happy','squeeze','spiral','mouth_open','mouth_round','mouth_smile','mouth_frown','viseme_a','viseme_e','viseme_i','viseme_o','viseme_u']};expr['mouth_smile']=.45
  roll=0;pitch=0;yaw=0;sit=0;lift=0;gaze=(0,0);breathe=.004*wave
  if state=='idle':
   roll=.012*wave;hands['l'].z+=.005*wave;hands['r'].z+=.005*wave
  elif state=='playful':
   envelope=math.sin(math.pi*p)**2;giggle=math.sin(math.tau*p*5)
   roll=.075*giggle*envelope;pitch=-.035*envelope;lift=.018*abs(giggle)*envelope
   for side,sign in [('l',1),('r',-1)]:
    hands[side]=Vector((sign*(.31+.12*envelope),-1.03,.90+.11*envelope+.018*giggle))
    rot[side]=[.12*envelope,sign*.15*giggle*envelope,math.pi];curl[side]=[.35]*4
   expr['happy']=envelope;expr['mouth_smile']=.45+.55*envelope;expr['mouth_open']=envelope*(.35+.20*abs(giggle))
  elif state=='listen':
   roll=-.06;pitch=.015*wave;hands['l']=Vector((.70,-.76,1.46+.012*wave));rot['l']=[0,-1.15,0];curl['l']=[.12,.10,.2,.3];gaze=(.006,0)
  elif state=='think':
   roll=.065+.015*wave;pitch=-.02;hands['r']=Vector((-.10,-.95,.91+.012*pulse));rot['r']=[-.65,1.22,0];curl['r']=[.42,.10,.7,.8];gaze=(.008,.018);expr['mouth_smile']=0;expr['mouth_round']=.3
  elif state=='speak':
   gesture=math.sin(math.tau*p);hands['l']=Vector((.67+.055*pulse,-.89,1.05+.055*gesture));rot['l']=[-.2,-.4-.12*gesture,0];curl['l']=[.20,.12,.18,.22];pitch=.035*math.sin(math.tau*p*2);roll=.015*wave
  elif state=='briefing':
   hands['l']=Vector((.67,-.81,1.24+.025*wave));rot['l']=[0,-1.25,0];curl['l']=[.65,0,1.05,1.05];pitch=.025*math.sin(math.tau*p*2);gaze=(.006,.003)
  elif state=='working':
   roll=.025*wave;pitch=.025*pulse
   for side,s in [('l',1),('r',-1)]:
    hands[side]=Vector((s*(.43+.045*pulse),-1.03+.035*s*wave,.91+.095*s*wave));rot[side]=[.12*s*wave,s*.18*wave,math.pi];curl[side]=[.65,.8,.8,.8]
   expr['mouth_smile']=0;expr['mouth_round']=.25;expr['squeeze']=.8
  elif state=='progress':
   pitch=.065;roll=.025*wave;hands['l']=Vector((.38+.045*wave,-1.04,.96+.020*math.cos(math.tau*p)));hands['r']=Vector((-.68,-.69,.76));rot['l']=[0,0,math.pi];curl['l']=[.8,.8,.8,.8];gaze=(.018*wave,-.006);expr['mouth_round']=.45;expr['mouth_smile']=0
  elif state=='alert':
   rise=ramp(.05,.32,p);hands['l']=lerp(idle['l'],(.76,-.72,1.56),rise);rot['l']=[0,-1.4*rise,math.pi*(1-rise)];curl['l']=[.55*(1-rise)]*4;lift=.055*math.sin(math.pi*ramp(0,.65,p));expr['mouth_smile']=0;expr['mouth_round']=.7;expr['blink']=.65*(1-ramp(0,.18,p))
  elif state=='review':
   writing=ramp(.10,.22,p)*(1-ramp(.62,.76,p));pitch=.085*writing;gaze=(.014,-.013*writing)
   hands['l']=Vector((.55,-1.09,.82));hands['r']=Vector((-.50+.025*math.sin(math.tau*p*3)*writing,-1.15,.92+.012*math.cos(math.tau*p*3)*writing));curl={k:[.9]*4 for k in hands};rot['r']=[0,.40,math.pi];expr['mouth_smile']=.25+.4*(1-writing)
  elif state=='decision':
   hands['l']=Vector((-.10,-1.13,1.00));hands['r']=Vector((.16,-1.00,.82));roll=.06+.013*wave;pitch=-.015;curl={k:[.55]*4 for k in hands};expr['mouth_smile']=0;expr['mouth_round']=.35;gaze=(.005*wave,.004)
  elif state=='pause':
   sit=1
   hands={'l':Vector((.52,-1.05,.94)),'r':Vector((-.52,-1.05,.94))};rot={k:[.15,0,math.pi] for k in hands};expr['mouth_smile']=.20
  elif state=='resume':
   sit=1-ramp(0,.40,p);pull=ramp(.35,.55,p)*(1-ramp(.68,.86,p))
   start={'l':(.52,-1.05,.94),'r':(-.52,-1.05,.94)};ready={'l':(.43,-1.03,.91),'r':(-.43,-1.03,.91)}
   for side in hands:hands[side]=lerp(start[side],ready[side],ramp(0,.85,p))
   hands['l']=hands['l'].lerp(Vector((.48,-.98,.79)),pull);hands['r']=hands['r'].lerp(Vector((.29+.045*ramp(.42,.67,p),-1.12,.98)),pull);rot['l']=[0,.95*pull,math.pi*(1-pull)];rot['r']=[0,-.55*pull,math.pi];curl={k:[.80]*4 for k in hands};expr['mouth_smile']=0;expr['squeeze']=.6*pull;pitch=-.025*pull;breathe=0
   if p>=1:return self.pose('working',0,2)
  elif state=='error':
   scratch=math.sin(math.tau*p*3)*ramp(.06,.18,p)*(1-ramp(.77,.93,p));hands['l']=Vector((.67,-.65,1.64+.030*scratch));hands['r']=Vector((-.68,-.65,.75));rot['l']=[-.35,-1.35,0];curl['l']=[.3,.45+.18*scratch,.55+.18*scratch,.7];roll=.025*wave;expr['spiral']=1;expr['mouth_smile']=0;expr['mouth_frown']=.9
  elif state=='awaken':
   raisehand=ramp(.07,.26,p)*(1-ramp(.70,.96,p));rub=math.sin(math.tau*(p-.22)*4)*ramp(.22,.3,p)*(1-ramp(.58,.7,p))
   hands['l']=idle['l'].lerp(Vector((.13+.026*rub,-.84,1.24+.017*rub)),raisehand);rot['l']=[-.45*raisehand,-1.25*raisehand,math.pi*(1-raisehand)];curl['l']=[.65]*4
   pitch=-.035*(1-ramp(.7,1,p));expr['blink']=1-ramp(.62,.93,p);expr['mouth_open']=.65*math.sin(math.pi*ramp(.1,.8,p));expr['mouth_smile']=.45*ramp(.75,1,p);breathe=0
   if p>=1:return self.pose('idle',0,4)
  # Acting phrases: anticipation, gesture, brief hold and return; never a static pose loop.
  nod=beat(p,.10,.35)-.65*beat(p,.40,.62)
  if state=='idle':
   roll=.032*wave;yaw=.035*math.sin(math.tau*p);breathe=.011*wave
   for side,sign in [('l',1),('r',-1)]:hands[side]+=Vector((sign*.025*pulse,0,.025*pulse))
  elif state=='listen':
   yaw=.095*wave;roll=-.06+.038*math.sin(math.tau*p);pitch=.07*nod
   hands['l']+=Vector((.055*wave,-.045*pulse,.07*pulse));rot['l'][0]+=.14*wave
  elif state=='think':
   question=beat(p,.25,.68);yaw=.065*wave;roll=.04+.065*wave;pitch=-.035+.04*nod
   hands['r']+=Vector((-.20*question,-.06*question,.045*question));rot['r'][0]-=.20*question;gaze=(.022*wave,.020)
  elif state=='speak':
   phrase=beat(p,.05,.52);reply=beat(p,.48,.95);roll=.045*wave;pitch=.065*nod;yaw=.065*wave
   hands['l']+=Vector((.12*phrase,-.07*phrase,.10*phrase));rot['l'][0]-=.28*phrase
   hands['r']=hands['r'].lerp(Vector((-.55,-1.00,1.06)),reply);rot['r'][1]-=.35*reply;curl['r']=[.55-.35*reply]*4
  elif state=='briefing':
   point=beat(p,.10,.52);pitch=.055*nod;roll=.035*wave;yaw=.04*wave
   hands['l']+=Vector((.06*point,-.025*point,.13*point-.07*beat(p,.65,.92)));rot['l'][1]-=.15*point
  elif state=='working':
   roll=.06*wave;yaw=.055*math.sin(math.tau*p*2);pitch=.055*pulse
   for side,sign in [('l',1),('r',-1)]:hands[side]+=Vector((sign*.06*wave,-.05*math.sin(math.tau*p*2),sign*.065*wave))
  elif state=='progress':
   pitch=.035+.085*pulse;roll=.05*wave;yaw=.045*wave;hands['l']+=Vector((.08*wave,-.025*pulse,.035*pulse));gaze=(.025*wave,-.013*pulse)
  elif state=='alert':
   signal=beat(p,.08,.60);hands['l']=Vector((.68+.05*signal,-.78,1.35+.20*signal));rot['l']=[.14*wave,-1.30-.13*signal,0];curl['l']=[.12]*4
   lift=.035*signal;pitch=.04*nod;roll=.03*wave;expr['blink']=0;expr['mouth_round']=.35+.35*signal
  elif state=='review':
   hands['r']=hands['r'].lerp(Vector((.16,-1.20,.94)),writing)
   pitch=.035+.10*beat(p,.08,.78);roll=.025*wave;hands['r'].x+=.025*math.sin(math.tau*p*4)*writing;hands['r'].z+=.025*math.cos(math.tau*p*4)*writing
  elif state=='decision':
   roll=.085*wave;pitch=.02+.05*pulse;yaw=.065*math.sin(math.tau*p);hands['l'].z+=.025*wave;hands['r'].z-=.022*wave;gaze=(.021*wave,.008*pulse)
  elif state=='pause':
   breathe=.009*wave;roll=.024*wave
   for side in hands:hands[side].z+=.025*pulse
  elif state=='error':
   roll=.05*wave;yaw=.055*wave;hands['l'].x+=.035*scratch;hands['l'].z+=.025*scratch
  # State-local hands are evaluated against the moving body, preserving coordinated contact.
  D=Matrix.Translation((0,0,-.21*sit+lift+breathe))@around((0,0,1.16),(pitch,roll,yaw))
  self.assign('root',Matrix.Identity(4));self.assign('body',D);self.assign('head',D)
  for side,s in [('l',1),('r',-1)]:
   self.assign('eye_'+side,D@Matrix.Translation((gaze[0],0,gaze[1])))
   c=Vector((s*1.25,0,1.17));R=Euler(rot[side]).to_matrix().to_4x4();handD=D@Matrix.Translation(hands[side])@R@Matrix.Translation(-c)
   shoulder=self.origins['arm_'+side];elbow=self.origins['forearm_'+side];wrist=self.origins['hand_'+side];target=handD@wrist
   target_local=D.inverted()@target;mid=Vector((s*.52,-.28,min(1.35,max(.66,target_local.z-.10))))
   self.segment('arm_'+side,shoulder,elbow,D@shoulder,D@mid);self.segment('forearm_'+side,elbow,wrist,D@mid,target);self.assign('hand_'+side,handD);self.assign('prop_cuff_'+side+'_bone',handD)
   for j in range(4):
    n=f'finger{j}_a_{side}';a=self.origins[n];rotA=(curl[side][j]*.8,0,0) if j==0 else (0,0,-s*min(curl[side][j],.9)*.68)
    A=around(a,rotA);self.assign(n,handD@A);n2=f'finger{j}_b_{side}';rotB=(curl[side][j]*.7,0,0) if j==0 else (0,0,-s*min(curl[side][j],.9)*.72);self.assign(n2,handD@A@around(self.origins[n2],rotB))
   footcenter=self.origins['foot_'+side];F=Matrix.Translation((s*.12*sit,-.73*sit,0))@around(footcenter,(-.95*sit,0,0))
   floor=min((F@v).z for v in self.foot_points[side]);F=Matrix.Translation((0,0,-floor))@F
   self.assign('foot_'+side,F);self.segment('leg_'+side,self.origins['leg_'+side],footcenter,D@self.origins['leg_'+side],F@footcenter)
  for i in range(8):self.assign(f'fur_{i}',D) # Physics owns secondary motion at runtime.
  # Props follow authored grips, with clear front faces and no real-time glass.
  configs={'magnifier':(hands['l']+Vector((-.07,-.085,-.025)),(0,-.35,0),.92),
           'clipboard':((Vector((.86,-.81,1.70)) if state=='briefing' else hands['l']+Vector((-.16,.005,.10))),(0,0,-.06),1.0),
           'pencil':(hands['r']+Vector((.075,-.065,.045)),(0,.65,.12),1.2),
           'monocle':(Vector((.10,-.63,1.25)),(0,0,0),.50),
           'bell':(Vector((.91,-.04,1.67)),(0,.15*wave,0),.65)}
  for n,(pos,angles,scale) in configs.items():self.assign('prop_'+n+'_bone',D@Matrix.Translation(pos)@Euler(angles).to_matrix().to_4x4()@Matrix.Scale(scale,4))
  if state not in ['error','awaken','alert']:
   expr['blink']=max(0,1-abs(p-.78)/.035)**2*(1-max(expr['happy'],expr['squeeze'],expr['spiral']))
  for n,v in expr.items():self.face.data.shape_keys.key_blocks[n].value=v
