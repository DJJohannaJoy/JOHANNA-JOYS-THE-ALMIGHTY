"""Bounded parallel scan jobs. Each tempo job has isolated temporary files."""
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from dataclasses import replace
from pathlib import Path
import threading
import tempfile
import shutil
import audio_core as C
import engine_external as X
import online_requests as O


def accepted_hits(hits,duration):
    accepted,weak=C.grouped_hits(hits,duration)
    strong=[]
    for hit in accepted:
        (strong if hit['score']>=180 or hit['score']>=75 and hit['samples']>=2 else weak).append(hit)
    return strong,weak


def offline_scan(mix,cfg,duration,notify,cancel,split,match,known_windows=None):
    env=C.env_with_ffmpeg(cfg['ffmpeg_dir'])
    hits=[];errors=[];quick=[];hit_lock=threading.Lock()
    enabled=set(cfg.get('_scan_stages',('A','B')))
    with tempfile.TemporaryDirectory(prefix='almighty-parallel-') as td:
        root=Path(td)
        for key in enabled & {'A','B'}:
            notify('stage',key,'running','Gemeinsame Audio-Vorbereitung')
            notify('stage_progress',key,0,1,'Audio einmal vorbereiten')
        parts=split(mix,root/'original',cfg,1.,'tempo',cancel)
        if cancel.is_set():raise RuntimeError('Scan wurde abgebrochen.')
        factors=[f for f in C.SPEEDS if abs(f-1)>1e-8]
        if not cfg.get('exhaustive_tempo',False):factors=[f for f in factors if f in (.94,1.06,.97,1.03,.90,1.10)]
        modes=[('tempo',f) for f in factors]
        if cfg.get('tempo_pitch'):modes += [('pitch',f) for f in factors]
        if 'B' not in enabled:modes=[]
        selected=list(enumerate(parts))
        def windows(key,done,total,detail,prepared=False):
            notify('stage_progress',key,total+done if prepared else done,2*total if prepared else max(1,total),detail)
            notify('stage_progress',key+'/schnipsel',done,max(1,total),f'{detail} · Ausschnitte geprüft')
        def original():
            nonlocal quick
            notify('stage','A','running','Originaltempo · parallel zum Tiefenscan')
            found,err=match(parts,1.,'tempo',root,env,cancel,lambda msg:notify('log',msg),
                progress=lambda d,t:windows('A',d,t,f'Originaltempo · {d}/{t} Fenster'))
            with hit_lock:
                quick,_=accepted_hits(found,duration)
            notify('hits',quick)
            if not err:notify('stage_progress','A',1,1,f'{len(quick)} Treffer')
            notify('stage','A','failed' if err else 'done',f'{len(quick)} Treffer'+(' · '+err[0] if err else ''))
            return found,err
        if modes:
            notify('stage','B','running',f'{len(modes)} Tempo-Varianten · starten vor dem Schnellscan')
            notify('stage_progress','B',0,len(modes),'Tempo-Varianten starten')
        def variant(kind,factor):
            key=f'B/{kind}/{factor:.2f}'
            notify('stage_progress',key,0,2,f'{kind} {factor:.2f}× · vorbereiten')
            folder=root/f'{kind}-{factor:.2f}';folder.mkdir()
            covered=known_windows() if known_windows else []
            with hit_lock:
                covered += [(max(0,h['first_detection']-25),min(duration,h['last_detection']+35))
                            for h in quick if h['score']>=200 or h['samples']>=2]
            current=[(i,p) for i,p in selected if not any(a<=i*C.SEGMENT_SECONDS+C.SEGMENT_SECONDS/2<=b for a,b in covered)]
            if not current:
                notify('stage_progress',key,2,2,f'{kind} {factor:.2f}× · Fenster bereits online erkannt')
                return [],[]
            concat=folder/'fenster.txt'
            concat.write_text(''.join("file '"+p.as_posix().replace("'","'\\''")+"'\n" for _,p in current),encoding='utf-8')
            ffmpeg=shutil.which('ffmpeg',path=env['PATH'])
            args=[ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),
                  '-vn','-af',C.mode_args(kind,factor),'-ac','1','-ar','11025','-c:a','pcm_s16le',
                  '-f','segment','-segment_time',str(C.SEGMENT_SECONDS/factor),'-reset_timestamps','1',str(folder/'part-%04d.wav')]
            code,msg=C.run_cmd(args,env,cancel=cancel)
            if code:raise RuntimeError('Tempo-Vorbereitung: '+msg[-300:])
            pieces=sorted(p for p in folder.glob('part-*.wav') if p.stat().st_size>20000)
            # Last short chunks can differ by a few resampling samples.
            pieces=pieces[:len(current)]
            notify('stage_progress',key,1,2,f'{kind} {factor:.2f}× · vergleichen')
            found,err=match(pieces,factor,kind,folder,env,cancel,lambda msg:notify('log',msg),
                progress=lambda d,t:windows(key,d,t,f'{kind} {factor:.2f}× · {d}/{t} Fenster',True))
            corrected=[]
            for hit in found:
                number=C.SEGMENT_RE.search(Path(hit.segment).name)
                if not number or int(number[1])>=len(current):continue
                original,original_path=current[int(number[1])]
                corrected.append(replace(hit,time=original*C.SEGMENT_SECONDS+hit.query_start*factor,
                                         segment=str(original_path)))
            notify('stage_progress',key,2,2,f'{kind} {factor:.2f}× · {len(corrected)} Kandidaten'+(' · Fehler' if err else ''))
            return corrected,err
        workers=max(1,min(3,int(cfg.get('scan_workers',3))))
        pool=ThreadPoolExecutor(max_workers=workers);pending={};done=0;b_errors=[]
        try:
            for kind,factor in modes:
                notify('stage_progress',f'B/{kind}/{factor:.2f}',0,2,f'{kind} {factor:.2f}× · wartet')
            # Give the slow tempo jobs the first slots, without making the
            # original-speed query wait behind the whole tempo queue.
            first_count=min(len(modes),max(1,workers-1))
            for kind,factor in modes[:first_count]:
                pending[pool.submit(variant,kind,factor)]=(kind,factor)
            if 'A' in enabled:pending[pool.submit(original)]=('original',1.)
            for kind,factor in modes[first_count:]:
                pending[pool.submit(variant,kind,factor)]=(kind,factor)
            while pending:
                if cancel.is_set():raise RuntimeError('Scan wurde abgebrochen.')
                finished,_=wait(pending,timeout=.1,return_when=FIRST_COMPLETED)
                for future in finished:
                    kind,factor=pending.pop(future)
                    try:
                        found,err=future.result();hits.extend(found);errors.extend(err)
                        if kind!='original':b_errors.extend(err)
                    except Exception as exc:
                        if cancel.is_set():raise
                        message=f'{kind} {factor:.2f}: {exc}';errors.append(message)
                        if kind!='original':b_errors.append(message)
                        else:notify('stage','A','failed',message)
                    if kind!='original':
                        done+=1
                        notify('stage_progress','B',done,len(modes),f'{done}/{len(modes)} Varianten fertig')
                    strong,_=accepted_hits(hits,duration);notify('hits',strong)
        finally:
            for future in pending:future.cancel()
            pool.shutdown(wait=True,cancel_futures=True)
        strong,weak=accepted_hits(hits,duration)
        if modes:notify('stage','B','failed' if b_errors else 'done',f'{len(strong)} Offline-Treffer'+(' · '+b_errors[0] if b_errors else ''))
        return strong,weak,errors


def parallel_scan(mix,cfg,duration,notify,cancel,split,match,stages=None,seed_observations=()):
    """Start independent methods together; preserve partial results and errors."""
    results={'offline':[],'weak':[],'mixid':[],'shazam':[]};statuses={};errors=[]
    selected=set(stages if stages is not None else ('A','B','M','S'))
    cfg={**cfg,'_online_gate':O.RequestGate(state_path=C.DATA/'shazam_service.json')}
    snapshot={'tasks':{},'states':{}}
    lock=threading.Lock();counter=[0];live={}
    def emit(kind,*args):
        if kind=='hits':
            ordered=[]
            with lock:
                for item in args[0]:
                    methods=item.get('methods') or [None]
                    for method in methods:
                        token=(item.get('source'),item.get('full_path'),item.get('artist'),item.get('title'),
                               int(float(item.get('time',0))/20),method)
                        if token not in live:counter[0]+=1
                        order=live[token]['_observed_order'] if token in live else item.get('_observed_order',item.get('_received_order',counter[0]))
                        record={**item,'_observed_order':order}
                        if method:record['methods']=[method]
                        live[token]=record;ordered.append(record)
            notify(kind,ordered)
        else:
            if kind=='stage_progress':
                key,done,total,detail=args
                with lock:snapshot['tasks'][key]={'done':done,'total':total,'percent':100*done/total if total else 0,'detail':detail}
            elif kind=='stage':
                with lock:snapshot['states'][args[0]]={'state':args[1],'detail':args[2]}
            notify(kind,*args)
    def online_windows():
        with lock:
            return [(float(r['time']),float(r['time'])+(18 if r.get('source')=='mix-id' else 12))
                    for r in live.values() if not r.get('full_path') and r.get('source') in {'mix-id','ShazamIO'}]
    # Repeated methods update matching evidence without losing the other
    # methods, their successful results, or their original discovery order.
    if seed_observations:
        for record in seed_observations:
            source=record.get('source')
            adapter='mix-id-18s' if source=='mix-id' else 'ShazamIO-12s' if source in {'ShazamIO','shazam'} else None
            if adapter:O.save_probe(O.probe_cache(C.DATA,mix,record.get('time',0),adapter),record)
        counter[0]=max(int(r.get('_observed_order',r.get('_received_order',0))) for r in seed_observations)
        emit('hits',seed_observations)
    def offline():
        a,b,e=offline_scan(mix,{**cfg,'_scan_stages':list(selected & {'A','B'})},duration,emit,cancel,split,match,known_windows=online_windows)
        return {'offline':a,'weak':b},e,f'{len(a)} Treffer'
    def mixid():
        emit('stage','M','running','mix-id · Shazam-Katalog')
        emit('stage_progress','M',0,100,'mix-id starten')
        def mix_log(message):
            emit('log','mix-id: '+message)
            if 'automatischer Wiederholungsversuch' in message:emit('stage','M','retrying',message)
            elif 'Anfrage' in message and 'Anfragelimit' not in message:emit('stage','M','running',message)
        records,warn=X.run_mixid(mix,{**cfg,'_probe_progress':lambda key,d,t,detail:emit('stage_progress','M/'+key,d,t,detail)},C.env_with_ffmpeg(cfg['ffmpeg_dir']),mix_log,cancel,
            progress=lambda done,total,detail:emit('stage_progress','M',done,total,detail),
            on_hit=lambda item:emit('hits',[item]))
        emit('hits',records)
        if not warn:emit('stage_progress','M',100,100,f'{len(records)} Beobachtungen')
        return {'mixid':records},[warn] if warn else [],f'{len(records)} Treffer'
    def shazam():
        points=C.unknown_probe_times(duration,[],cfg.get('max_shazam',50))
        emit('stage','S','running',f'ShazamIO · {len(points)} Proben')
        emit('stage_progress','S',0,max(1,len(points)),'Proben starten')
        sha_cfg={**cfg,'shazam_workers':cfg.get('shazam_workers',4),'_probe_progress':lambda key,d,t,detail:emit('stage_progress','S/'+key,d,t,detail)}
        def shazam_log(message):
            emit('log',message)
            if 'automatischer Wiederholungsversuch' in message:emit('stage','S','retrying',message)
            elif ': Anfrage' in message:emit('stage','S','running',message)
            if str(message).startswith('Shazam'):emit('stage_activity','S',str(message))
        records,err=asyncio.run(C.shazam_probes(mix,points,sha_cfg,shazam_log,cancel,
            progress=lambda d,t:emit('stage_progress','S',d,max(1,t),f'{d}/{t} Proben'),
            on_hit=lambda record:emit('hits',[{**record,'source':'ShazamIO'}])))
        if not err:emit('stage_progress','S',len(points) or 1,len(points) or 1,'ShazamIO abgeschlossen')
        return {'shazam':records},err,f'{len(records)} Beobachtungen'
    jobs=[]
    for enabled,name,key,fn in [(cfg.get('mixid',True),'mix-id','M',mixid),
        (cfg.get('shazam') and cfg.get('max_shazam'),'ShazamIO','S',shazam)]:
        if key not in selected:continue
        if enabled:jobs.append((name,key,fn))
        else:statuses[name]='Deaktiviert';emit('stage',key,'skipped','Deaktiviert')
    # Queue the two slow online searches first; offline starts alongside them.
    if selected & {'A','B'}:jobs.append(('Offline',None,offline))
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending={pool.submit(fn):(name,key) for name,key,fn in jobs}
        while pending:
            if cancel.is_set():
                for future in pending:future.cancel()
                raise RuntimeError('Scan wurde abgebrochen.')
            finished,_=wait(pending,timeout=.1,return_when=FIRST_COMPLETED)
            for future in finished:
                name,key=pending.pop(future)
                try:
                    values,err,status=future.result();results.update(values);errors.extend(err)
                    statuses[name]=status+(' · mit Fehlern' if err else '')
                    if key:emit('stage',key,'failed' if err else 'done',status+(' · '+err[0] if err else ''))
                except Exception as exc:
                    if cancel.is_set():raise
                    errors.append(name+': '+str(exc));statuses[name]='Fehler: '+str(exc)
                    for stage in ([key] if key else selected & {'A','B'}):emit('stage',stage,'failed',str(exc))
    results['observations']=list(live.values())
    results['progress']=snapshot
    return results,statuses,errors
