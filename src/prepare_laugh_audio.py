"""Make a small, gently levelled laugh from the archived CC0 recording."""
from pathlib import Path
import subprocess,json,shutil
B=Path(__file__).resolve().parents[1];source=B/'reference/audio/tiny_creatures_laugh_original.ogg';out=B/'output/hanhan_laugh_v1.wav'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-af','highpass=f=100,lowpass=f=8000,loudnorm=I=-19:TP=-3:LRA=7,afade=t=in:d=0.015,afade=t=out:st=1.55:d=0.18','-ac','1','-ar','24000','-c:a','pcm_s16le',str(out)],check=True)
shutil.copy2(out,B/'web/public/assets'/out.name)
(B/'reference/audio/source.json').write_text(json.dumps({'title':'Tiny creatures sounds / laugh.ogg','author':'fvcalderan','license':'CC0 1.0','source':'https://opengameart.org/content/tiny-creatures-sounds','download':'https://opengameart.org/sites/default/files/laugh.ogg','license_url':'https://creativecommons.org/publicdomain/zero/1.0/','processing':'high-pass, low-pass, loudness normalization, edge fades, mono 24kHz PCM','generation_credit_cost':0},indent=2))
print(out, out.stat().st_size)
