from pathlib import Path
import sys,threading,time,asyncio,types,tempfile
import uuid,shutil
from contextlib import contextmanager
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import scan_jobs as J
import audio_core as C
import online_requests as O

barrier=threading.Barrier(3);events=[];cancel=threading.Event()
record={'title':'Song','artist':'Artist','time':12}
def offline(*args,**kwargs):
    barrier.wait(timeout=3);time.sleep(.05)
    args[3]('hits',[{**record,'source':'offline','full_path':'Artist - Song.wav','methods':['Schnellscan Â· Originaltempo']}])
    return [record],[],[]
def mixid(*args,progress=None,on_hit=None):
    barrier.wait(timeout=3);time.sleep(.05)
    if progress:progress(99,100,'test')
    return [{**record,'source':'mix-id'}],''
async def shazam(*args,progress=None,on_hit=None):
    barrier.wait(timeout=3);await asyncio.sleep(.05)
    item={**record,'source':'shazam'}
    if on_hit:on_hit(item)
    if progress:progress(1,1)
    return [item],[]
cfg={'ffmpeg_dir':'','mixid':True,'shazam':True,'max_shazam':1,'_online_gate':O.RequestGate(3,0)}
with patch.object(J,'offline_scan',side_effect=offline),patch.object(J.X,'run_mixid',side_effect=mixid),patch.object(C,'shazam_probes',side_effect=shazam):
    data,status,errors=J.parallel_scan(Path('set.wav'),cfg,120,lambda *e:events.append(e),cancel,None,None)
    assert not errors,errors
    assert len(data['observations'])==3 and len(status)==3
    assert all(data[k] for k in ('offline','mixid','shazam'))
    assert len({x['_observed_order'] for x in data['observations']})==3

# Test actual bounded Shazam scheduling without any network requests.
cfg={**cfg,'_online_gate':O.RequestGate(4,0)}
running=[0];peak=[0];paths=[];progress=[]
class Client:
    def __init__(self,**kwargs):pass
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    async def recognize(self,path):
        paths.append(path);running[0]+=1;peak[0]=max(peak[0],running[0])
        try:await asyncio.sleep(.015);return {'track':{'title':'Song','subtitle':'Artist'}}
        finally:running[0]-=1
def extract(argv,*args,**kwargs):Path(argv[-1]).write_bytes(b'fixture');return 0,''
@contextmanager
def scratch_directory(**kwargs):
    parent=Path(__file__).resolve().parent
    directory=parent/('probe-fixture-'+uuid.uuid4().hex);directory.mkdir()
    try:yield str(directory)
    finally:
        assert directory.resolve().parent==parent
        shutil.rmtree(directory)
with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=Client)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch_directory):
    hits,errors=asyncio.run(C.shazam_probes(Path('set.wav'),[0,30,60,90],cfg,lambda _:None,cancel,
                          progress=lambda a,b:progress.append((a,b))))
    assert len(hits)==4 and not errors and peak[0]==4
    assert len(set(paths))==4 and progress[-1]==(4,4)
print('PARALLEL SCAN OK: three methods overlap, live provenance retained, Shazam concurrency bounded at four, isolated samples and real request counts.')


class Failure(Client):
    count=0
    async def recognize(self,path):
        Failure.count+=1
        raise ConnectionError('offline fixture')
with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=Failure)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch_directory):
    counts=[]
    hits,errors=asyncio.run(C.shazam_probes(Path('set.wav'),list(range(10)),cfg,lambda _:None,cancel,
                         progress=lambda d,t:counts.append(d)))
assert Failure.count==30 and counts[-1]==10 and len(errors)==10
assert all('Online-Antwort' in e and 'drei Versuchen' in e for e in errors)
class Hanging(Client):
    async def recognize(self,path):await asyncio.sleep(100)
cancel_test=threading.Event();timer=threading.Timer(.15,cancel_test.set);timer.start();started=time.monotonic()
with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=Hanging)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch_directory):
    try:asyncio.run(C.shazam_probes(Path('set.wav'),[0,30],cfg,lambda _:None,cancel_test))
    except RuntimeError as exc:assert 'abgebrochen' in str(exc)
    else:raise AssertionError('Online cancellation was ignored')
assert time.monotonic()-started<2
print('ONLINE FAILURE HANDLING OK: all excerpts attempted despite failures, bounded deferred retry, truthful errors, prompt cancellation.')

# A timeout burst in the first three excerpts must recover without losing later jobs.
class Burst(Client):
    attempts={}
    async def recognize(self,path):
        n=self.attempts.get(path,0)+1;self.attempts[path]=n
        if int(Path(path).stem.split('-')[-1])<=3 and n<=2:raise TimeoutError()
        return {'track':{'title':'Recovered','subtitle':'Artist'}}
with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=Burst)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch_directory):
    counts=[]
    hits,errors=asyncio.run(C.shazam_probes(Path('set.wav'),list(range(10)),cfg,lambda _:None,threading.Event(),progress=lambda d,t:counts.append(d)))
assert len(hits)==10 and not errors and counts[-1]==10 and counts==sorted(counts)
assert len(Burst.attempts)==10 and sum(Burst.attempts.values())==16

# One persistently throttled sample cannot retain a worker forever.
class Throttled(Client):
    attempts={}
    async def recognize(self,path):
        self.attempts[path]=self.attempts.get(path,0)+1
        if Path(path).stem.endswith('0001'):raise O.RateLimited('HTTP 429',0)
        return {'track':{'title':'Available','subtitle':'Artist'}}
class NoDelay(O.RequestGate):
    def recover(self,error,epoch):
        super().recover(error,epoch);self.interval=0
with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=Throttled)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch_directory):
    counts=[]
    hits,errors=asyncio.run(C.shazam_probes(Path('set.wav'),list(range(6)),{**cfg,'_online_gate':NoDelay(4,0)},lambda _:None,threading.Event(),progress=lambda d,t:counts.append(d)))
assert len(hits)==5 and len(errors)==1 and '429' in errors[0] and counts[-1]==6
assert sorted(Throttled.attempts.values())==[1,1,1,1,1,3]

class InvalidReply(Client):
    async def recognize(self,path):return {'error':'service unavailable'}
with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=InvalidReply)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch_directory),patch.object(O,'save_probe') as save:
    hits,errors=asyncio.run(C.shazam_probes(Path('set.wav'),[0],cfg,lambda _:None,threading.Event()))
    assert not hits and len(errors)==1 and 'Ungültige' in errors[0]
    save.assert_not_called()
class NoMatch(Client):
    async def recognize(self,path):return {'matches':[]}
with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=NoMatch)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch_directory),patch.object(O,'save_probe') as save:
    hits,errors=asyncio.run(C.shazam_probes(Path('set.wav'),[0],cfg,lambda _:None,threading.Event()))
    assert not hits and not errors
    save.assert_called_once_with(None,None)

class Transient(Client):
    attempts={}
    async def recognize(self,path):
        self.attempts[path]=self.attempts.get(path,0)+1
        if self.attempts[path]==1:raise TimeoutError('temporary fixture')
        return {'track':{'title':'Recovered','subtitle':'Artist'}}
with patch.dict(sys.modules,{'shazamio':types.SimpleNamespace(Shazam=Transient)}),patch.object(C,'run_cmd',side_effect=extract),patch.object(C.tempfile,'TemporaryDirectory',scratch_directory):
    counts=[]
    hits,errors=asyncio.run(C.shazam_probes(Path('set.wav'),[0,30],cfg,lambda _:None,threading.Event(),
                         progress=lambda d,t:counts.append((d,t))))
assert len(hits)==2 and not errors and counts[-1]==(2,2)
assert all(n==2 for n in Transient.attempts.values())

async def shazam_only(*args,progress=None,on_hit=None):
    item={**record,'source':'shazam'}
    if on_hit:on_hit(item)
    return [item],[]
with patch.object(J,'offline_scan') as no_offline,patch.object(J.X,'run_mixid') as no_mixid,patch.object(C,'shazam_probes',side_effect=shazam_only):
    seed=data['observations']
    retried,status,errors=J.parallel_scan(Path('set.wav'),cfg,120,lambda *e:None,threading.Event(),None,None,
                                       stages={'S'},seed_observations=seed)
    no_offline.assert_not_called();no_mixid.assert_not_called()
assert not errors and len(retried['observations'])==len(seed)
assert sorted(r['_observed_order'] for r in retried['observations'])==sorted(r['_observed_order'] for r in seed)

print('RETRY OK: transient Shazam recovery, isolated method rerun and preserved evidence order.')
