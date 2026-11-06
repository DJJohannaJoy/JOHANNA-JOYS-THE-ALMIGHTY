# -*- coding: utf-8 -*-
"""Local mix-id Shazam adapter.
The local offline engine is audfprint. The separate TrackID API service is not used.
"""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable
import scanner_core as C
import track_results as R

ROOT = Path(__file__).resolve().parent
MIX_COPY = ROOT / 'engine' / 'mix-id'


def locate_mixid(preferred='') -> Path | None:
    """Engine is bundled into the SET SCANNER directory after first-run setup."""
    if (MIX_COPY / 'cli.mjs').is_file() and (MIX_COPY / 'lib' / 'audio.mjs').is_file():
        return MIX_COPY
    return None


def mixid_ready(cfg):
    return bool((ROOT / 'tools' / 'node' / 'node.exe').is_file() and
                locate_mixid() is not None and
                (MIX_COPY / 'node_modules' / 'shazam-api').is_dir())


def ensure_mixid_copy(cfg: dict, log: Callable[[str],None]) -> Path:
    if not mixid_ready(cfg):
        raise RuntimeError('mix-id ist nicht eingerichtet. Bitte den SET SCANNER mit 2_SET_SCANNER_STARTEN.bat starten, damit alle Engines automatisch installiert werden.')
    target = MIX_COPY
    p = target/'lib'/'audio.mjs'
    s = p.read_text(encoding='utf-8')
    edited = s.replace('`which ${cmd}`','`where.exe ${cmd}`').replace('2>/dev/null','2>nul')
    if edited != s:
        p.write_text(edited,encoding='utf-8')
    return target


def parse_hms(value) -> float:
    if isinstance(value,(int,float)):
        return float(value)
    parts = str(value or '').strip(' []').split(':')
    try:
        s = 0.
        for part in parts:
            s = s*60 + float(part)
        return s
    except ValueError:
        return 0.


def parse_mixid_json(data: str | dict) -> list[dict]:
    payload = json.loads(data) if isinstance(data,str) else data
    result = []
    for tr in payload.get('tracks',[]):
        if not isinstance(tr,dict) or not tr.get('title'):
            continue
        t = tr.get('position_sec',None)
        if t is None:
            t = parse_hms(tr.get('timestamp','0'))
        result.append({'time':float(t),'artist':str(tr.get('artist') or '').strip(),
                       'title':str(tr['title']).strip(),'source':'mix-id',
                       'confidence':'ungeprüfter Online-Treffer'})
    return result


def run_mixid(mix: Path, cfg: dict, env: dict, log, cancel: threading.Event, progress=None, on_hit=None):
    import online_requests as O
    from concurrent.futures import ThreadPoolExecutor
    import queue
    project=ensure_mixid_copy(cfg,log)
    node=ROOT/'tools/node/node.exe'
    if not node.is_file():raise RuntimeError('Lokales Node.js fehlt. Bitte Starter erneut ausführen.')
    helper=Path(cfg.get('_mixid_helper') or ROOT/'mixid_probe.mjs')
    if not helper.is_file():raise RuntimeError('mixid_probe.mjs fehlt. Bitte Programm aktualisieren.')
    duration=C.get_duration(mix,env)
    points=list(range(0,max(0,int(duration-18))+1,60)) if duration>=18 else []
    jobs=queue.Queue()
    for point in points:jobs.put(point)
    gate=cfg.get('_online_gate') or O.RequestGate()
    mutex=threading.Lock();stopped=threading.Event();records=[];errors=[];completed=0;failures=0
    ffmpeg=shutil.which('ffmpeg',path=env.get('PATH'))
    def worker(number):
      nonlocal completed,failures
      with tempfile.TemporaryDirectory(prefix='set-scanner-mixid-') as folder:
        pcm=Path(folder)/'probe.raw'
        while not stopped.is_set():
            if cancel.is_set():raise RuntimeError('Scan wurde abgebrochen.')
            try:position=jobs.get_nowait()
            except queue.Empty:return
            cache=O.probe_cache(C.DATA,mix,position,'mix-id-18s')
            cached=O.read_probe(cache);record=None;ok=False
            def detail(done,caption):
                if cfg.get('_probe_progress'):cfg['_probe_progress'](f'probe/{position:06d}',done,3,f'Tiefenscan 2 · {C.hhmmss(position)} · '+caption)
            detail(0,'vorbereiten')
            try:
                if cached is not None:
                    record=cached.get('record');ok=True
                else:
                    prepared=O.probe_cache(C.DATA,mix,position,'mix-id-signature-v1') or Path(folder)/'signature.json'
                    try:
                        signature=json.loads(prepared.read_text(encoding='utf-8'))
                        ready=isinstance(signature.get('uri'),str) and signature['uri'].startswith('data:') and signature.get('numberSamples',0)>0 and signature.get('sampleRateHz')==16000
                    except (OSError,ValueError,TypeError,AttributeError):ready=False
                    if not ready:
                        log(f'Arbeiter {number} · {C.hhmmss(position)} · Fingerabdruck vorbereiten')
                        code,output=C.run_cmd([ffmpeg,'-v','error','-y','-ss',str(position),'-i',str(mix),
                            '-t','18','-vn','-ac','1','-ar','16000','-f','s16le',str(pcm)],env,cancel=cancel,idle_timeout=30)
                        if code:raise RuntimeError('Audioausschnitt fehlgeschlagen: '+output[-180:])
                        detail(1,'Ausschnitt bereit')
                        prepared.parent.mkdir(parents=True,exist_ok=True)
                        temporary=Path(folder)/'signature-ready.json'
                        for preparation_attempt in range(2):
                            code,output=C.run_cmd([str(node),str(helper),str(project),str(pcm),'--prepare',str(temporary)],env,
                                cwd=project,cancel=cancel,idle_timeout=30)
                            if not code and temporary.is_file():break
                        else:raise RuntimeError('Fingerabdruck fehlgeschlagen: '+output[-180:])
                        # Only publish a fully written fingerprint; retries reuse it.
                        signature_temp=prepared.with_suffix(f'.{threading.get_ident()}.tmp')
                        shutil.copyfile(temporary,signature_temp);signature_temp.replace(prepared)
                    detail(2,'Fingerabdruck bereit · Online-Suche')
                    attempt=0
                    while True:
                        epoch=gate.acquire(cancel,lambda s:log(s))
                        try:
                            if stopped.is_set():return
                            log(f'Arbeiter {number} · {C.hhmmss(position)} · Anfrage'+(' erneut' if attempt else ''))
                            code,output=C.run_cmd([str(node),str(helper),str(project),str(prepared),'--send'],env,
                                cwd=project,cancel=cancel,idle_timeout=15)
                        finally:gate.release()
                        try:answer=json.loads(output.strip().splitlines()[-1])
                        except (ValueError,IndexError):answer={'status':'error','error':f'Prozessfehler {code}'}
                        if code and answer.get('status') not in {'error','rate_limit'}:
                            answer={'status':'error','error':f"Prozessfehler {code}; Phase: {answer.get('phase','Start')}"}
                        if answer.get('status')=='rate_limit':
                            error=O.RateLimited('mix-id: Shazam-Anfragelimit (HTTP 429) · später erneut prüfen',O.retry_delay(answer.get('retry_after')))
                            gate.recover(error,epoch)
                            continue
                        if not code and answer.get('status')=='ok':
                            gate.successful(epoch)
                            track=answer.get('track')
                            if track and track.get('title'):
                                record={'time':position,'artist':str(track.get('artist') or ''),'title':str(track['title']),
                                        'source':'mix-id','confidence':'Online-Stichprobe'}
                            O.save_probe(cache,record);ok=True;break
                        attempt+=1
                        if attempt>=2:raise RuntimeError(str(answer.get('error','Unbekannter Fehler')))
                        if cancel.wait(.5):raise RuntimeError('Scan wurde abgebrochen.')
                with mutex:
                    failures=0
                    if record:
                        records.append(record)
                        if on_hit:on_hit(record)
            except Exception as exc:
                if cancel.is_set():raise
                with mutex:
                    errors.append('mix-id '+C.hhmmss(position)+': '+str(exc));failures+=1
                    detail(0,'Fehler · '+str(exc)[:90])
                    if failures>=3:
                        stopped.set();errors.append('mix-id nach drei aufeinanderfolgenden fehlerhaften Proben beendet.')
            finally:
                with mutex:
                    if ok:completed+=1
                    if ok:detail(3,'Treffer' if record else 'geprüft · kein Treffer')
                    if progress:progress(completed,len(points),f'mix-id · {completed}/{len(points)} · Arbeiter {number}'+(' · gespeichert' if cached is not None else ''))
                jobs.task_done()
    with ThreadPoolExecutor(max_workers=max(1,min(4,int(cfg.get('mixid_workers',4))))) as pool:
        futures=[pool.submit(worker,i+1) for i in range(max(1,min(4,int(cfg.get('mixid_workers',4)))))]
        for future in futures:future.result()
    return sorted(records,key=lambda r:r['time']), ' / '.join(dict.fromkeys(errors))


def normalize_title(x):
    return re.sub(r'[^a-z0-9]+','',str(x).lower())


def merge_results(offline, mixid, shazam):
    return R.merge_records([*offline,*mixid,*[{**x,'source':'ShazamIO'} for x in shazam]])


def merged_report(mix:Path,duration:float,offline,weak,mixid,shazam,statuses,errors,observations=None,progress=None):
    rec=R.merge_records(observations) if observations is not None else merge_results(offline,mixid,shazam)
    lines=['THE ALMIGHTY | SET SCANNER 1.13 EMBER | GEMEINSAME TRACKLIST','='*72,
           f'Datei: {mix}',f'Dauer: {C.hhmmss(duration)}',
           f'Erstellt: {C.stamp()}','', 'ENGINE-STATUS', '-'*72]
    for k,s in statuses.items():lines.append(f'{k}: {s}')
    lines+=['','TRACKS / KANDIDATEN (Zeit = Näherung, bitte nachhören)','-'*72]
    if not rec:lines+=['Keine ausreichend sicheren Ergebnisse.']
    for r in rec:
        ident=(r['artist']+' – ' if r['artist'] else '') + r['title']
        lines.append(f"{r['number']:02d} | {C.hhmmss(r['time'])} | {ident} | {' → '.join(r['methods'])} | {' + '.join(r['sources'])}")
    lines+=['','UNSICHERE OFFLINE-KANDIDATEN (nicht automatisch bestätigt)','-'*72]
    lines += [f"{C.hhmmss(x.get('first_detection',0))} | {x['title']} | {x['score']} Hashes" for x in weak[:80]] or ['Keine']
    lines+=['','HINWEISE','-'*72,
             'mix-id nutzt bereits Shazam, ist keine zusätzliche Offline-Engine.',
             'ShazamIO prüft verteilte Stichproben parallel. Kein Key erforderlich, aber Internet notwendig.',
             'Die Zeitmarken sind Erkennungspositionen/Schätzungen, nicht exakt ermittelte Trackstarts.',
             'Auch ein online erkannter Titel ist nicht automatisch sicher.',
             'Originaldateien und Rekordbox-Bibliothek bleiben unverändert.']
    if errors:lines+=['','FEHLER / GRENZEN','-'*72,*errors]
    C.OUTPUT.mkdir(exist_ok=True,parents=True)
    base=re.sub(r'[^\w. -]+','_',mix.stem).strip()[:60] or 'Set'
    output=C.OUTPUT/(base+'_Tracklist_'+__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')+'.txt')
    output.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    output.with_suffix('.json').write_text(json.dumps({'file':str(mix),'duration':duration,'tracks':rec,
        'statuses':statuses,'errors':errors,'observations':observations,'progress':progress},ensure_ascii=False,indent=2),encoding='utf-8')
    return output,rec
