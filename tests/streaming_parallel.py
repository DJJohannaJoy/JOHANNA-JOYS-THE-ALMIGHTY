from pathlib import Path
import asyncio,sys,threading,time,uuid,shutil
from contextlib import contextmanager
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import almighty as S,scan_jobs as J,audio_core as C
@contextmanager
def scratch(**kwargs):
    parent=Path(__file__).resolve().parent;folder=parent/('stream-fixture-'+uuid.uuid4().hex);folder.mkdir()
    try:yield str(folder)
    finally:assert folder.resolve().parent==parent;shutil.rmtree(folder)
all_started=threading.Event();barrier=threading.Barrier(4,action=all_started.set)
seen=set();lock=threading.Lock();events=[]
def enter(method):
    with lock:
        if method in seen:return
        seen.add(method)
    barrier.wait(timeout=5)
def split(mix,folder,cfg,factor,kind,cancel,on_part=None):
    folder.mkdir(parents=True);parts=[]
    for i in range(3):
        p=folder/f'part-{i:04d}.wav';p.write_bytes(bytes(21000));parts.append(p);on_part(p)
        if i==0:assert all_started.wait(5),'Offline matching waited for complete audio preparation'
    return parts
split.streams_parts=True
def convert(argv,*args,**kwargs):
    folder=Path(argv[-1]).parent
    count=len(Path(argv[argv.index('-i')+1]).read_text().splitlines())
    for i in range(count):(folder/f'part-{i:04d}.wav').write_bytes(bytes(21000))
    return 0,''
def match(parts,factor,kind,folder,env,cancel,log,progress=None):
    enter('A' if factor==1 else 'B')
    if progress:progress(len(parts),len(parts))
    return [C.OfflineHit('Artist - Song.flac',factor,220,factor,kind,0,1,str(p),10) for p in parts],[]
def mixid(*args,**kwargs):enter('M');return [],''
async def shazam(*args,**kwargs):enter('S');return [],[]
with patch.object(J.tempfile,'TemporaryDirectory',scratch),patch.object(C,'run_cmd',side_effect=convert),patch.object(J.X,'run_mixid',side_effect=mixid),patch.object(C,'shazam_probes',side_effect=shazam):
    data,status,errors=J.parallel_scan(Path('set.wav'),{'ffmpeg_dir':'','mixid':True,'shazam':True,'max_shazam':1},90,
        lambda *e:events.append(e),threading.Event(),split,match)
assert not errors,errors
assert seen=={'A','B','M','S'} and all_started.is_set()
assert data['offline'] and data['offline'][0]['samples']==3,data['offline']
assert any(e[0]=='stage_progress' and e[1]=='B' and 0<e[2]<e[3] for e in events)
assert any(e[:4]==('stage_progress','B',1,1) for e in events)
# Test the real splitter's closed-segment CSV callback without decoding fixture bytes.
with scratch() as td:
    folder=Path(td)/'original';ready=[]
    def command(argv,env,log=None,**kwargs):
        assert '-segment_list' in argv and kwargs['echo']
        first=folder/'part-0000.wav';first.write_bytes(bytes(21000));log('part-0000.wav,0.000000,30.000000')
        assert ready==[first],'Closed segment callback was deferred until FFmpeg exit'
        second=folder/'part-0001.wav';second.write_bytes(bytes(21000));log('part-0001.wav,30.000000,60.000000')
        return 0,''
    with patch.object(S.C,'run_cmd',side_effect=command),patch.object(S.shutil,'which',return_value='ffmpeg'):
        parts=S.split_audio(Path('set.wav'),folder,{'ffmpeg_dir':''},1,'tempo',threading.Event(),on_part=ready.append)
    assert parts==ready and len(parts)==2
print('TRUE PARALLEL START OK: quick scan, tempo matching, mix-id and Shazam all enter before the second audio segment is prepared; real fractional deep progress and original timeline retained.')
