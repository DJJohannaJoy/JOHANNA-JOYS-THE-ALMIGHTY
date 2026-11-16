"""Google parser, independent concurrency, cache, failure and saved provenance."""
from pathlib import Path
import asyncio,json,os,subprocess,sys,tempfile,threading,time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import audio_core as C,google_method as G,scan_jobs as J,online_requests as O,track_results as R
from test_paths import COMPONENTS
root=Path(__file__).resolve().parents[1]

# Four blockers prove that adding Google does not consume an offline/online slot.
barrier=threading.Barrier(4);entered=[]
def enter(name):entered.append((name,time.monotonic()));barrier.wait(timeout=3)
def offline(*a,**kw):enter('offline');return [],[],[]
def mixid(*a,**kw):enter('mix-id');return [],''
async def shazam(*a,**kw):enter('shazam');return [],[]
def google(*a,**kw):enter('google');return [],[],'0 matches'
cfg={'ffmpeg_dir':'','mixid':True,'shazam':True,'max_shazam':1,'google':True}
with patch.object(O,'save_probe'),patch.object(J,'offline_scan',side_effect=offline),patch.object(J.X,'run_mixid',side_effect=mixid),patch.object(C,'shazam_probes',side_effect=shazam),patch.object(G,'readiness',return_value=(True,'')),patch.object(G,'scan',side_effect=google):
 data,status,errors=J.parallel_scan(Path('set.wav'),cfg,120,lambda *a:None,threading.Event(),None,None)
 assert not errors and len(entered)==4 and max(t for _,t in entered)-min(t for _,t in entered)<.5,(errors,entered)
 entered.clear()
 with patch.object(J,'offline_scan') as off,patch.object(J.X,'run_mixid') as mix,patch.object(C,'shazam_probes') as sha:
  with patch.object(G,'scan',return_value=([{'source':'Google','title':'Song','artist':'Artist','time':12}],[],'1 match')):
   data,status,errors=J.parallel_scan(Path('set.wav'),cfg,120,lambda *a:None,threading.Event(),None,None,stages={'G'},seed_observations=[{'source':'ShazamIO','title':'Song','artist':'Artist','time':15}])
  off.assert_not_called();mix.assert_not_called();sha.assert_not_called()
  tracks=R.merge_records(data['observations']);assert len(tracks)==1 and set(tracks[0]['catalogs'])=={'Google','Shazam'},tracks

# A ready MIX-ID request goes before queued ShazamIO requests, without exceeding budget.
gate=O.RequestGate(1,0);first=gate._ticket('ShazamIO');assert gate._try(first)
sha=gate._ticket('ShazamIO');mix=gate._ticket('mix-id');gate.release()
assert not gate._try(sha) and gate._try(mix);gate.release();assert gate._try(sha);gate.release()

with tempfile.TemporaryDirectory(prefix='almighty-google-test-') as td:
 folder=Path(td);credential=folder/'access.json'
 credential.write_text(json.dumps({'x-goog-api-key':'AIza'+'x'*35,'x-android-package':'com.google.android.googlequicksearchbox','x-android-cert':'a'*40}),encoding='utf-8')
 sample=folder/'set.wav';sample.write_bytes(b'test');events=[];requests=[]
 def command(argv,*a,**kw):
  if '-ss' in argv:Path(argv[-1]).write_bytes(b'aac fixture');return 0,''
  requests.append(1);return 0,json.dumps({'status':'ok','matches':[]})
 config={'ffmpeg_dir':str(COMPONENTS/'tools/ffmpeg'),'google_headers_file':str(credential),'max_google':3}
 with patch.object(C,'APP',COMPONENTS),patch.object(C,'DATA',folder/'cache'),patch.object(C,'run_cmd',side_effect=command):
  records,errors,status=G.scan(sample,config,120,lambda *e:events.append(e),threading.Event())
  assert not records and not errors and len(requests)==3,(requests,errors,status)
  records,errors,status=G.scan(sample,config,120,lambda *e:None,threading.Event())
  assert len(requests)==3,'No-match cache must prevent repeated network requests'
  main=[e for e in events if e[:2]==('stage_progress','G')];assert main[-1][2]==main[-1][3]==3
  assert any(0<e[2]<e[3] for e in main),'Preparation must be visible before the first reply'
 with patch.object(C,'APP',COMPONENTS),patch.object(C,'DATA',folder/'fatal-cache'),patch.object(C,'run_cmd',side_effect=lambda argv,*a,**kw:command(argv,*a,**kw) if '-ss' in argv else (0,json.dumps({'status':'error','grpc_status':'7','error':'PERMISSION_DENIED','retryable':False}))):
  records,errors,status=G.scan(sample,{**config,'max_google':50},3600,lambda *e:None,threading.Event())
  assert errors and len(errors)<=2 and 'PERMISSION_DENIED' in errors[0],errors
 # Node parser accepts valid no-match and compressed matches; rejects truncated frames.
 js=folder/'parser.mjs'
 js.write_text("""import {decodeResponse,packets} from %s;
import {gzipSync} from 'node:zlib';import assert from 'node:assert/strict';
const v=n=>{let a=[];do{let b=n%%128;n=Math.floor(n/128);a.push(b+(n?128:0));}while(n);return Buffer.from(a);};
const b=(id,data)=>{if(typeof data==='string')data=Buffer.from(data);return Buffer.concat([v(id*8+2),v(data.length),data]);};
const song=Buffer.concat([b(1,'Artist'),b(2,'Song'),b(22,'video-id')]);
const payload=b(35351945,b(1,b(1,b(3,song))));
const f=(data,flag=0)=>{const h=Buffer.alloc(5);h[0]=flag;h.writeUInt32BE(data.length,1);return Buffer.concat([h,data]);};
assert.deepEqual(decodeResponse(f(Buffer.alloc(0))),[]);
assert.equal(decodeResponse(f(payload))[0].title,'Song');
assert.equal(decodeResponse(f(gzipSync(payload),1))[0].artist,'Artist');
assert.throws(()=>decodeResponse(Buffer.from([0,0,0,0,9])));
assert.ok(packets(Buffer.alloc(3000)).length>3000);console.log('GOOGLE PARSER OK');
""" % json.dumps((root/'APP/google_probe.mjs').as_uri()),encoding='utf-8')
 subprocess.run([str(COMPONENTS/'tools/node/node.exe'),str(js)],check=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
print('GOOGLE INTEGRATION OK: four concurrent methods, independent rerun, catalog provenance, fair MIX-ID scheduling, cached no-match, truthful permission failures and strict compressed protobuf parser.')
