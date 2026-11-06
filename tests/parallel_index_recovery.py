"""Parallel subprocess failure, per-file resume, errors and safe publication."""
from pathlib import Path
import json,sys,threading,uuid,shutil,time,os
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import scanner_core as C

parent=Path(__file__).resolve().parent
scratch=parent/('index-fixture-'+uuid.uuid4().hex);scratch.mkdir()
try:
    music=scratch/'music';music.mkdir()
    for n in range(75):(music/f'{n:03d}.wav').write_bytes(b'fixture')
    cfg={'library':str(music),'ffmpeg_dir':'','index_workers':2}
    C.APP=scratch;C.DATA=scratch/'data';C.DATA.mkdir()
    C.DB=C.DATA/'musik.pklz';C.LOGS=scratch/'logs'
    previous=b'previous active database';C.DB.write_bytes(previous)
    attempts=[];failed_once=[False];merge_failed=[False];mutex=threading.Lock()
    def engine(argv,*args,log=None,cancel=None,**kwargs):
        if '--cache-batch' in argv:
            batch=json.loads(Path(argv[-1]).read_text(encoding='utf-8'))
            for entry in batch:
                if cancel.is_set():raise RuntimeError('abgebrochen')
                with mutex:
                    attempts.append(entry['source'])
                    if not failed_once[0]:
                        failed_once[0]=True;return 3221225477,'native fault'
                if Path(entry['source']).name=='074.wav':return 1,'invalid audio'
                Path(entry['cache']).write_bytes(b'audfprinthashV00'+bytes(8))
                log('CACHE_DONE '+entry['key'])
            return 0,''
        assert '--merge-cache' in argv
        assert C.DB.read_bytes()==previous,'Active DB replaced before merge success'
        if not merge_failed[0]:merge_failed[0]=True;return 3221225477,'merge native fault'
        manifest=json.loads(Path(argv[-2]).read_text(encoding='utf-8'))
        names=[e['source'] for e in manifest['entries']]
        log('MERGE_DONE '+str(len(names)))
        Path(argv[-1]).write_text(json.dumps(names)+' '*200)
        return 0,''
    cancel=threading.Event();events=[]
    def update(value):
        events.append(value)
        if value['done']>=8 and value['phase']=='index':cancel.set()
    with patch.object(C,'install_engine',return_value=scratch),patch.object(C,'run_cmd',side_effect=engine):
        try:C.build_database(cfg,lambda _:None,cancel,update)
        except RuntimeError as error:assert 'abgebrochen' in str(error).lower()
        else:raise AssertionError('Cancellation did not stop the build')
        assert C.DB.read_bytes()==previous
        assert not any(e['percent']==100 for e in events)
        cached={p.stem for p in (C.DATA/'Fingerabdruck_Cache').glob('*.afpt')}
        assert cached
        first_resume_call=len(attempts)
        C.build_database(cfg,lambda _:None,threading.Event(),events.append)
        import hashlib
        for name in attempts[first_resume_call:]:
            p=Path(name);record=(str(p),p.stat().st_size,p.stat().st_mtime_ns)
            key=hashlib.sha256(json.dumps(record,ensure_ascii=False).encode('utf-8')).hexdigest()
            assert key not in cached
        result=json.loads(C.DB.read_text());issues=json.loads((C.DATA/'nicht_lesbar.json').read_text())
        assert len(result)==74 and len(set(result))==74 and len(issues)==1
        assert Path(issues[0]['source']).name=='074.wav'
        assert events[-1]['phase']=='done' and events[-1]['percent']==100 and events[-1]['errors']==1
        assert any(e['phase']=='retry' for e in events)
        assert any(e['eta'] is not None for e in events)
        assert all(e['percent']<100 for e in events if e['phase']!='done')
    silent_cancel=threading.Event();timer=threading.Timer(.2,silent_cancel.set);timer.start()
    started=time.monotonic()
    try:C.run_cmd([sys.executable,'-c','import time;time.sleep(20)'],os.environ.copy(),scratch,cancel=silent_cancel)
    except RuntimeError:pass
    else:raise AssertionError('Silent child ignored cancellation')
    assert time.monotonic()-started<3
    print('INDEX RECOVERY OK: parallel crash retry, durable resume, invalid-file report, safe merge, truthful progress, silent-worker cancellation.')
finally:
    assert scratch.resolve().parent==parent
    shutil.rmtree(scratch)
