from pathlib import Path
import sys,threading,time,asyncio,types,uuid,shutil,json
from contextlib import contextmanager
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import audio_core as C
import engine_external as X
import online_requests as O
@contextmanager
def scratch(**kw):
    parent=Path(__file__).resolve().parent;folder=parent/('ui-fixture-online-'+uuid.uuid4().hex);folder.mkdir()
    try:yield str(folder)
    finally:assert folder.resolve().parent==parent;shutil.rmtree(folder)
class Client:
    calls=0;limited=False
    def __init__(self,**kw):assert isinstance(kw.get('http_client'),O.ShazamHTTP)
    async def __aenter__(self):return self
    async def __aexit__(self,*a):pass
    async def recognize(self,path):
        Client.calls+=1
        if Client.limited:
            Client.limited-=1
            raise O.RateLimited('Shazam: Anfragelimit (HTTP 429)',.01)
        return {'track':{'title':'Song','subtitle':'Artist'}}
def extract(argv,*a,**kw):Path(argv[-1]).write_bytes(b'fixture');return 0,''
class FastGate(O.RequestGate):
    def recover(self,error,epoch):
        result=super().recover(error,epoch)
        self.interval=0
        return result
cfg={'ffmpeg_dir':'','_online_gate':FastGate(3,0)}
class Response:
    status=429;headers={'Retry-After':'15'}
    async def __aenter__(self):return self
    async def __aexit__(self,*a):pass
class Session:
    calls=0
    def request(self,*a,**kw):self.calls+=1;return Response()
async def rate_response():
    client=O.ShazamHTTP();client.session=Session()
    try:await client.request('POST','https://fixture.invalid')
    except O.RateLimited as exc:assert '429' in str(exc) and '15' in str(exc)
    else:raise AssertionError('HTTP 429 was silently retried')
    assert client.session.calls==1
asyncio.run(rate_response())
class ValidResponse(Response):
    status=200;content_type='application/json'
    def raise_for_status(self):pass
    async def json(self):return {'matches':[]}
class CaptureSession:
    def request(self,*args,**kwargs):self.payload=kwargs['json'];return ValidResponse()
async def request_timestamp():
    client=O.ShazamHTTP();client.session=CaptureSession()
    original={'timestamp':1,'signature':{'uri':'data:fixture','samplems':12000}}
    with patch.object(O.time,'time',return_value=1700000000):
        assert await client.request('POST','https://fixture.invalid',json=original)=={'matches':[]}
    assert client.session.payload['timestamp']==1700000000000
    assert client.session.payload['signature']==original['signature'] and original['timestamp']==1
asyncio.run(request_timestamp())
with scratch() as td:
    root=Path(td);sample=root/'mix.wav';sample.write_bytes(b'fixture')
    with patch.object(C,'DATA',root/'cache'),patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=Client)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch):
        first=asyncio.run(C.shazam_probes(sample,[0,30],cfg,lambda _:None,threading.Event()))
        second=asyncio.run(C.shazam_probes(sample,[0,30],cfg,lambda _:None,threading.Event()))
        assert len(first[0])==len(second[0])==2 and Client.calls==2
        Client.calls=0;Client.limited=3;counts=[];started=time.monotonic()
        hits,errors=asyncio.run(C.shazam_probes(sample,list(range(100,105)),cfg,lambda _:None,threading.Event(),progress=lambda d,t:counts.append((d,t))))
        assert len(hits)==5 and not errors and Client.calls==8 and counts[-1]==(5,5)
with scratch() as td:
    root=Path(td);(root/'tools/node').mkdir(parents=True);(root/'tools/node/node.exe').touch();(root/'mixid_probe.mjs').touch()
    sample=root/'set.mp3';sample.write_bytes(b'fixture');calls=[];preparations=[];lock=threading.Lock();counts=[];attempts={}
    def command(argv,*args,**kw):
        if '-ss' in argv:Path(argv[-1]).write_text(argv[argv.index('-ss')+1]);return 0,''
        if '--prepare' in argv:
            position=int(Path(argv[3]).read_text());preparations.append(position)
            Path(argv[-1]).write_text(json.dumps({'uri':'data:fixture','numberSamples':288000,'sampleRateHz':16000,'position':position}))
            return 0,json.dumps({'status':'prepared'})
        position=json.loads(Path(argv[3]).read_text())['position']
        with lock:
            calls.append(position);attempts[position]=attempts.get(position,0)+1
            fail=position==0 and attempts[position]==1
        time.sleep(.02)
        if fail:return 3221225477,'native crash fixture'
        if position==0 and attempts[position] in (2,3):return 2,json.dumps({'status':'rate_limit','retry_after':'.01'})
        return 0,json.dumps({'status':'ok','track':{'title':'Song','artist':'Artist'}})
    with patch.object(X,'ROOT',root),patch.object(X,'ensure_mixid_copy',return_value=root),patch.object(C,'DATA',root/'cache'),patch.object(C,'get_duration',return_value=180),patch.object(C,'run_cmd',side_effect=command),patch.object(X.tempfile,'TemporaryDirectory',scratch):
        settings={'mixid_workers':3,'_online_gate':FastGate(3,0)}
        found,warn=X.run_mixid(sample,settings,{},lambda _:None,threading.Event(),progress=lambda d,t,s:counts.append((d,t)))
        previous=len(calls);cached,warn2=X.run_mixid(sample,settings,{},lambda _:None,threading.Event())
    assert not warn and not warn2 and [r['time'] for r in found]==[0,60,120]
    assert calls.count(0)==4 and len(cached)==3 and len(calls)==previous and counts[-1]==(3,3)
    assert sorted(preparations)==[0,60,120],'A retry recalculated its fingerprint'
gate=O.RequestGate(3,0);active=[0];maximum=[0];lock=threading.Lock();round_barrier=threading.Barrier(3)
def gated():
    gate.acquire(threading.Event())
    try:
        with lock:active[0]+=1;maximum[0]=max(maximum[0],active[0])
        round_barrier.wait(3);time.sleep(.02)
    finally:
        with lock:active[0]-=1
        gate.release()
with ThreadPoolExecutor(8) as pool:list(pool.map(lambda _:gated(),range(12)))
assert maximum[0]==3 and gate.active==0 and not gate.waiting
with scratch() as td:
    state=Path(td)/'service.json'
    one=O.RequestGate(1,.05,state);two=O.RequestGate(1,.05,state);cancel=threading.Event()
    epoch=one.acquire(cancel);one.release();started=time.monotonic()
    two.acquire(cancel);two.release()
    assert time.monotonic()-started>=.035,'Independent windows ignored shared pacing'
    assert one.recover(O.RateLimited('HTTP 429',.05),epoch)
    assert json.loads(state.read_text())['pause_until']>time.time()
    epoch2=two.acquire(cancel);two.release()
    assert epoch2==1 and two.recover(O.RateLimited('HTTP 429',.05),epoch2) and two.epoch==2
    # Cancellation remains immediate while a service pause is displayed.
    waiting=O.RequestGate(1,0);waiting.pause_until=time.time()+30
    cancel.set();started=time.monotonic()
    try:waiting.acquire(cancel)
    except RuntimeError:pass
    else:raise AssertionError('Pause ignored cancellation')
    assert time.monotonic()-started<.2 and not waiting.waiting
assert O.retry_delay('15')==15 and O.retry_delay(None)==30
class AlwaysLimited(Client):
    async def recognize(self,path):raise O.RateLimited('HTTP 429',120)
cancel=threading.Event();threading.Timer(.15,cancel.set).start();gate=O.RequestGate(2,0);started=time.monotonic()
with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=AlwaysLimited)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch):
    try:asyncio.run(C.shazam_probes(Path('missing.wav'),[0,30],{'ffmpeg_dir':'','_online_gate':gate},lambda _:None,cancel))
    except RuntimeError:pass
    else:raise AssertionError('Automatic retries ignored cancellation')
assert time.monotonic()-started<2 and gate.active==0 and not gate.waiting
class PreparedClient(Client):
    prepared=0;sent=0
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.core_recognizer=types.SimpleNamespace(recognize_path=self.fingerprint)
    async def fingerprint(self,**kwargs):
        assert prepared_gate.active==0,'Local fingerprint occupied an HTTP slot'
        PreparedClient.prepared+=1
        return 'prepared-signature'
    async def send_recognize_request_v2(self,*,sig):
        assert sig=='prepared-signature' and prepared_gate.active==1
        PreparedClient.sent+=1
        if PreparedClient.sent<=2:raise O.RateLimited('429',.01)
        return {'track':{'title':'Prepared Song','subtitle':'Artist'}}
prepared_gate=FastGate(1,0)
with scratch() as td:
    sample=Path(td)/'input.wav';sample.write_bytes(b'fixture')
    with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=PreparedClient)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch),patch.object(C,'DATA',Path(td)/'data'):
        hits,errors=asyncio.run(C.shazam_probes(sample,[0],{'ffmpeg_dir':'','_online_gate':prepared_gate},lambda _:None,threading.Event()))
    assert len(hits)==1 and not errors and PreparedClient.prepared==1 and PreparedClient.sent==3
for persistent in (False,True):
    with scratch() as td:
        gate=O.RequestGate(4,2,Path(td)/'service.json' if persistent else None)
        gate.recover(O.RateLimited('429',0),0)
        gate.recover(O.RateLimited('429',0),1)
        assert gate.interval==8
        for _ in range(30):gate.successful(gate.epoch)
        assert gate.interval==2,'Successful replies did not restore normal throughput'
        gate.successful(0)
        assert gate.interval==2,'An old response changed the current rate'
print('PIPELINE OK: fingerprints prepared once outside request slots; adaptive throughput recovers after valid replies.')
print('ONLINE REQUESTS OK: repeated 429 automatically recover to real 100%, durable probe reuse, native crash retry, shared pacing and cancellable service waits.')
