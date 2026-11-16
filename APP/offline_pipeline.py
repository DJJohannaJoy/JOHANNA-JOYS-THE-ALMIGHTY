"""Fan out closed audio segments immediately to independent quick/tempo jobs."""
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from dataclasses import replace
from pathlib import Path
import math,shutil,tempfile,threading
import audio_core as C


def scan(mix,cfg,duration,notify,cancel,split,match,accepted_hits,known_windows=None):
    enabled=set(cfg.get('_scan_stages',('A','B')))
    env=C.env_with_ffmpeg(cfg['ffmpeg_dir']);expected=max(1,math.ceil(duration/C.SEGMENT_SECONDS))
    factors=[f for f in C.SPEEDS if abs(f-1)>1e-8]
    if not cfg.get('exhaustive_tempo',False):factors=[f for f in factors if f in (.94,1.06,.97,1.03,.90,1.10)]
    modes=[('tempo',f) for f in factors] if 'B' in enabled else []
    if modes and cfg.get('tempo_pitch'):modes += [('pitch',f) for f in factors]
    condition=threading.Condition();hit_lock=threading.Lock();progress_lock=threading.Lock()
    parts=[];published=set();prepared=threading.Event();shutdown=threading.Event()
    prep_errors=[];errors={'A':[],'B':[]};hits=[];quick=[];units={mode:0 for mode in modes}
    class Stop:
        def is_set(self):return cancel.is_set() or shutdown.is_set()
        def wait(self,seconds):return cancel.wait(seconds) or shutdown.is_set()
    stop=Stop()
    def check():
        if stop.is_set():raise RuntimeError('Scan wurde abgebrochen.')
    def publish(part):
        part=Path(part)
        with condition:
            if part.name in published:return
            published.add(part.name);parts.append(part);condition.notify_all()
        for stage in enabled:
            notify('stage_progress',stage+'/vorbereitung',len(parts),expected,f'Audio · {len(parts)}/{expected} Schnipsel bereit')
    def batches():
        cursor=0
        while True:
            with condition:
                while cursor==len(parts) and not prepared.is_set():
                    check();condition.wait(.1)
                check()
                if cursor==len(parts):return
                # First match starts with one closed segment, not the whole set.
                end=min(len(parts),cursor+(1 if cursor==0 and not prepared.is_set() else expected))
                current=list(enumerate(parts[cursor:end],cursor));cursor=end
            yield current
    def push(found):
        with hit_lock:
            hits.extend(found);strong,_=accepted_hits(list(hits),duration)
        notify('hits',strong)
    def deep_progress(mode,done,detail):
        with progress_lock:
            units[mode]=max(units[mode],done)
            notify('stage_progress','B',sum(units.values()),max(1,2*expected*len(modes)),detail)
            notify('stage_progress',f'B/{mode[0]}/{mode[1]:.2f}',done,2*expected,detail)
    with tempfile.TemporaryDirectory(prefix='almighty-stream-') as td:
        root=Path(td)
        for stage in enabled:
            notify('stage',stage,'running','Parallel gestartet · erster Audioschnipsel wird vorbereitet')
            notify('stage_progress',stage,0,expected if stage=='A' else max(1,2*expected*len(modes)),'Wartet nur auf den ersten Audioschnipsel')
        def prepare():
            try:
                for part in split(mix,root/'original',cfg,1.,'tempo',stop,on_part=publish):publish(part)
            except Exception as exc:
                if not stop.is_set():prep_errors.append(str(exc))
            finally:
                with condition:prepared.set();condition.notify_all()
        def original():
            nonlocal quick
            done=0
            for current in batches():
                folder=root/f'quick-{current[0][0]:04d}';folder.mkdir()
                notify('stage','A','running','Originaltempo · Schnipsel werden sofort verglichen')
                try:
                    found,err=match([p for _,p in current],1.,'tempo',folder,env,stop,lambda msg:notify('log',msg),
                        progress=lambda d,t:notify('stage_progress','A',done+d,expected,f'Schnellscan · {done+d}/{expected} Schnipsel'))
                    errors['A'].extend(err)
                    with hit_lock:quick.extend(accepted_hits(found,duration)[0])
                    push(found)
                except Exception as exc:
                    check();errors['A'].append(str(exc))
                done+=len(current)
                notify('stage_progress','A',done,expected,f'Schnellscan · {done}/{expected} Schnipsel')
            failed=errors['A']+prep_errors
            notify('stage','A','failed' if failed else 'done',f'{len(quick)} Treffer'+(' · '+failed[0] if failed else ''))
            if not failed:notify('stage_progress','A',1,1,'Schnellscan abgeschlossen')
        def variant(kind,factor):
            mode=(kind,factor);done=0
            for batch in batches():
                covered=list(known_windows() if known_windows else [])
                with hit_lock:
                    covered += [(max(0,h['first_detection']-25),min(duration,h['last_detection']+35)) for h in quick if h['score']>=200 or h['samples']>=2]
                current=[(i,p) for i,p in batch if not any(a<=i*C.SEGMENT_SECONDS+C.SEGMENT_SECONDS/2<=b for a,b in covered)]
                skipped=len(batch)-len(current)
                done+=2*skipped
                if not current:
                    deep_progress(mode,done,f'{kind} {factor:.2f}× · {skipped} bereits erkannte Schnipsel übernommen');continue
                folder=root/f'{kind}-{factor:.2f}-{batch[0][0]:04d}';folder.mkdir()
                concat=folder/'fenster.txt'
                concat.write_text(''.join("file '"+p.as_posix().replace("'","'\\''")+"'\n" for _,p in current),encoding='utf-8')
                ffmpeg=shutil.which('ffmpeg',path=env['PATH'])
                args=[ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),
                    '-vn','-af',C.mode_args(kind,factor),'-ac','1','-ar','11025','-c:a','pcm_s16le',
                    '-f','segment','-segment_time',str(C.SEGMENT_SECONDS/factor),'-reset_timestamps','1',str(folder/'part-%04d.wav')]
                try:
                    notify('stage','B','running',f'Tempo-Abgleich parallel · {kind} {factor:.2f}×')
                    code,msg=C.run_cmd(args,env,cancel=stop)
                    if code:raise RuntimeError('Tempo-Vorbereitung: '+msg[-300:])
                    pieces=sorted(p for p in folder.glob('part-*.wav') if p.stat().st_size>20000)[:len(current)]
                    base=done+len(current)
                    deep_progress(mode,base,f'{kind} {factor:.2f}× · {len(current)} Schnipsel vorbereitet')
                    found,err=match(pieces,factor,kind,folder,env,stop,lambda msg:notify('log',msg),
                        progress=lambda d,t:deep_progress(mode,base+d,f'{kind} {factor:.2f}× · {d}/{t} Schnipsel vergleichen'))
                    errors['B'].extend(err);corrected=[]
                    for hit in found:
                        number=C.SEGMENT_RE.search(Path(hit.segment).name)
                        if not number or int(number[1])>=len(current):continue
                        index,original_part=current[int(number[1])]
                        corrected.append(replace(hit,time=index*C.SEGMENT_SECONDS+hit.query_start*factor,segment=str(original_part)))
                    push(corrected)
                except Exception as exc:
                    check();errors['B'].append(f'{kind} {factor:.2f}: {exc}')
                done+=2*len(current)
                deep_progress(mode,done,f'{kind} {factor:.2f}× · {done//2}/{expected} Schnipsel bearbeitet')
        producer=threading.Thread(target=prepare,name='Audio-Schnipsel',daemon=True)
        workers=max(1,min(2,int(cfg.get('scan_workers',3))-1))+(1 if 'A' in enabled else 0)
        pool=ThreadPoolExecutor(max_workers=max(1,workers));pending=set()
        try:
            if 'A' in enabled:pending.add(pool.submit(original))
            for mode in modes:pending.add(pool.submit(variant,*mode))
            producer.start()
            while pending:
                check();finished,pending=wait(pending,timeout=.1,return_when=FIRST_COMPLETED)
                for future in finished:future.result()
            strong,weak=accepted_hits(hits,duration)
            if modes:
                failed=errors['B']+prep_errors
                if not failed:notify('stage_progress','B',1,1,'Tiefenscan abgeschlossen')
                notify('stage','B','failed' if failed else 'done',f'{len(strong)} Offline-Treffer'+(' · '+failed[0] if failed else ''))
            return strong,weak,prep_errors+errors['A']+errors['B']
        finally:
            shutdown.set()
            with condition:condition.notify_all()
            for future in pending:future.cancel()
            pool.shutdown(wait=True,cancel_futures=True)
            if producer.ident is not None:producer.join()
