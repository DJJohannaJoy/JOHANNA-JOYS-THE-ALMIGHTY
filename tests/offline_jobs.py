from pathlib import Path
import sys,threading,uuid,shutil
from contextlib import contextmanager
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import scan_jobs as J
import scanner_core as C

@contextmanager
def scratch(prefix='',**kwargs):
    parent=Path(__file__).resolve().parent;folder=parent/('offline-fixture-'+uuid.uuid4().hex);folder.mkdir()
    try:yield str(folder)
    finally:
        assert folder.resolve().parent==parent
        shutil.rmtree(folder)
for exhaustive,total in [(False,6),(True,20)]:
    calls=[];events=[]
    def split(mix,folder,*args):
        folder.mkdir();parts=[]
        for i in range(3):
            p=folder/f'part-{i:04d}.wav';p.write_bytes(bytes(21000));parts.append(p)
        return parts
    def convert(argv,*args,**kwargs):
        concat=Path(argv[argv.index('-i')+1]);files=concat.read_text().splitlines();calls.append(files)
        assert len(files)==2 and 'part-0000' not in '\n'.join(files)
        folder=Path(argv[-1]).parent
        for i in range(len(files)):(folder/f'part-{i:04d}.wav').write_bytes(bytes(21000))
        return 0,''
    def match(parts,factor,kind,folder,env,cancel,log,progress=None):
        if factor==1:return [],[]
        if progress:progress(len(parts),len(parts))
        return [C.OfflineHit('Artist - Song.flac',factor,220,factor,kind,0,1,str(parts[0]),10)],[]
    with patch.object(J.tempfile,'TemporaryDirectory',scratch),patch.object(C,'run_cmd',side_effect=convert):
        hits,weak,errors=J.offline_scan(Path('set.wav'),{'ffmpeg_dir':'','exhaustive_tempo':exhaustive},90,
            lambda *e:events.append(e),threading.Event(),split,match,known_windows=lambda:[(0,18)])
    assert len(calls)==total and not errors and len(hits)==1
    assert 30.8<hits[0]['time']<31.2,hits
    assert hits[0]['samples']==1,'Variants of the same window inflated independent support'
    assert any(e[:4]==('stage_progress','B',total,total) for e in events)
print('OFFLINE JOBS OK: 6/20 speed profiles, unresolved-window selection, exact original timeline mapping, unique-window evidence and completed counts.')

# The slow path must start while the original-speed query is still busy.
tempo_started=threading.Event();original_started=threading.Event();tempo_matched=threading.Event()
def early_convert(argv,*args,**kwargs):
    tempo_started.set()
    assert original_started.wait(3),'Original-speed query was queued behind all variants'
    return convert(argv,*args,**kwargs)
def overlapping_match(parts,factor,*args,**kwargs):
    if factor==1:
        original_started.set()
        assert tempo_started.wait(3),'Tempo scan waited for the original-speed result'
        assert tempo_matched.wait(3),'Tempo query did not overlap original query'
    else:tempo_matched.set()
    return [],[]
with patch.object(J.tempfile,'TemporaryDirectory',scratch),patch.object(C,'run_cmd',side_effect=early_convert):
    J.offline_scan(Path('set.wav'),{'ffmpeg_dir':''},90,lambda *e:None,threading.Event(),
                   split,overlapping_match,known_windows=lambda:[(0,18)])
assert tempo_started.is_set() and tempo_matched.is_set()
print('EARLY DEEP SCAN OK: tempo conversion and matching overlap the unfinished quick query.')
