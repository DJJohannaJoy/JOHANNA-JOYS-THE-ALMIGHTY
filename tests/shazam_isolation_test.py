"""Exercise real native fingerprinting in a killable child, without network."""
from pathlib import Path
import asyncio,json,math,os,struct,subprocess,sys,tempfile,threading,wave
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import audio_core as C,online_requests as O
from test_paths import COMPONENTS
with tempfile.TemporaryDirectory(prefix='almighty-native-') as td:
 folder=Path(td);sample=folder/'clip.wav';output=folder/'signature.json'
 with wave.open(str(sample),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
  f.writeframes(b''.join(struct.pack('<h',int(9000*math.sin(i/16000*2*math.pi*(440+(i//4000)%7*30)))) for i in range(16000*8)))
 run=subprocess.run([sys.executable,'-X','utf8',str(C.APP/'shazam_fingerprint.py'),str(sample),str(output)],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
 assert run.returncode==0,(run.returncode,run.stderr[-500:])
 signature=json.loads(output.read_text());assert signature['signature']['uri'].startswith('data:') and signature['signature']['samples']>0
 # Replace only network transport, retain genuine preparation in the child.
 class Client:
  __module__='shazamio.api'
  def __init__(self,**kw):pass
  async def __aenter__(self):return self
  async def __aexit__(self,*a):pass
  async def send_recognize_request_v2(self,sig):
   assert sig.signature.samples>0 and sig.signature.uri.startswith('data:')
   return {'matches':[]}
 import types
 cfg={'ffmpeg_dir':str(COMPONENTS/'tools/ffmpeg'),'_online_gate':O.RequestGate(4,0)}
 with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=Client)}),patch.object(C,'DATA',folder/'cache'):
  hits,errors=asyncio.run(C.shazam_probes(sample,[0],cfg,lambda _:None,threading.Event()))
  assert not hits and not errors,errors
 # A native exit is converted to a per-probe error and cannot terminate Python/Tk.
 real_command=C.run_cmd
 def crash(argv,*a,**kw):
  if any(str(arg).endswith('shazam_fingerprint.py') for arg in argv):return 3221225477,'native failure fixture'
  return real_command(argv,*a,**kw)
 with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=Client)}),patch.object(C,'DATA',folder/'crash-cache'),patch.object(C,'run_cmd',side_effect=crash):
  hits,errors=asyncio.run(C.shazam_probes(sample,[0],cfg,lambda _:None,threading.Event()))
  assert not hits and len(errors)==1 and 'Prozessfehler' in errors[0],errors
print('SHAZAM PROCESS ISOLATION OK: real native fingerprint and transport handoff; native crash contained to probe, retries bounded, no network used.')
