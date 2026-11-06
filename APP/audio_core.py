#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JOHANNA JOY\'S THE ALMIGHTY shared core | Windows | Local audfprint + optional ShazamIO.
The original audio files remain unchanged. This is a prototype, not a certified
identification system: cross-check every result before publishing tracklists.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import hashlib
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import online_requests as O
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from dataclasses import dataclass, asdict
from contextlib import contextmanager

APP = Path(__file__).resolve().parent
USER_ROOT = Path(os.environ.get('ALMIGHTY_DATA_ROOT') or APP.parent/'Daten')
DATA = USER_ROOT / "Datenbank"
OUTPUT = USER_ROOT / "Ergebnisse"
LOGS = USER_ROOT / "Protokolle"
VENDOR = APP / "engine" / "audfprint"
DB = DATA / "musik.pklz"
CONFIG_FILE = USER_ROOT / "einstellungen.json"
EXTS = {".mp3", ".wav", ".flac", ".aiff", ".aif", ".m4a", ".ogg", ".opus", ".wma"}
AUDIOFILETYPES = "*.mp3 *.wav *.flac *.aiff *.aif *.m4a *.ogg *.opus *.wma"
DEFAULT_LIBRARY = str(Path.home()/'Music')
DEFAULT_AUDIO = Path.home() / "Downloads"

SPEEDS = [1.00, 0.94, 1.06, 0.97, 1.03, 0.90, 1.10,
          0.92, 1.08, 0.96, 1.04, 0.98, 1.02,
          0.91, 1.09, 0.93, 1.07, 0.95, 1.05, 0.99, 1.01]
SEGMENT_SECONDS = 30
MIN_SCORE = 45
STRONG_SCORE = 150
CONFIRM_GAP_SECONDS = 105
DEFAULT_MAX_SHAZAM = 50

RANGE_RE = re.compile(
    r"^Matched\s+(?P<support>[\d.]+)\s+s starting at\s+(?P<qstart>[\d.]+)\s+s in\s+"
    r"(?P<query>.*?)\s+to time\s+(?P<refstart>[\d.]+)\s+s in\s+"
    r"(?P<ref>.*?)\s+with\s+(?P<count>\d+)\s+of\s+", re.I)
SIMPLE_RE = re.compile(
    r"^Matched\s+(?P<query>.*?)\s+[\d.]+\s+sec\s+\d+\s+raw hashes\s+as\s+"
    r"(?P<ref>.*?)\s+at\s+(?P<refstart>[\d.]+)\s+s with\s+(?P<count>\d+)\s+of", re.I)
SEGMENT_RE = re.compile(r"part-(\d{4,})", re.I)


def stamp():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hhmmss(seconds: float) -> str:
    s = int(max(0, round(seconds)))
    return f"{s // 3600:02}:{(s // 60) % 60:02}:{s % 60:02}"


def read_config() -> dict:
    defaults = {"library": DEFAULT_LIBRARY, "shazam": True, "max_shazam": DEFAULT_MAX_SHAZAM,
                "tempo_pitch": False, "ffmpeg_dir": "", "audfprint_source": ""}
    try:
        result = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        if isinstance(result, dict):
            defaults.update(result)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return defaults


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def locate_ffmpeg(cfg: dict) -> str:
    """Bundled FFmpeg only. First-start bootstrap installs it into this folder."""
    path = APP / "tools" / "ffmpeg"
    if (path / "ffmpeg.exe").is_file() and (path / "ffprobe.exe").is_file():
        return str(path)
    return ""


def env_with_ffmpeg(folder: str) -> dict:
    env = os.environ.copy()
    dirs = [str(APP / "tools" / "node"), str(APP / "tools" / "ffmpeg")]
    if folder:
        dirs.insert(0, str(folder))
    env["PATH"] = os.pathsep.join(dirs) + os.pathsep + env.get("PATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[name]='1'
    return env


def locate_source(cfg: dict) -> Path | None:
    """Never make the user search for any engine files."""
    if all((VENDOR / name).is_file() for name in
           ("audfprint.py", "audfprint_analyze.py", "audfprint_match.py", "audio_read.py", "hash_table.py", "stft.py")):
        return VENDOR
    return None


def install_engine(cfg: dict, log) -> Path:
    src = locate_source(cfg)
    if src is None:
        raise RuntimeError("Offline-Engine fehlt. Bitte das vollständige Programmpaket neu entpacken.")
    return src


def run_cmd(argv: list[str], env: dict, cwd: Path | None = None, log=None,
            cancel: threading.Event | None = None, echo: bool = False,
            idle_timeout: float | None = None) -> tuple[int, str]:
    """Read stdout+stderr incrementally, allow cancellation, avoid shell=True."""
    kwargs = dict(cwd=str(cwd or APP), env=env, stdout=subprocess.PIPE,
                  stderr=subprocess.STDOUT, text=True, encoding='utf-8',errors="replace", bufsize=1)
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        if env.get('ALMIGHTY_BACKGROUND')=='1':kwargs['creationflags'] |= getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0x00004000)
    p = subprocess.Popen(argv, **kwargs)
    lines = [];last_output=time.monotonic()
    assert p.stdout is not None
    output_queue=queue.Queue()
    def read_output():
        try:
            for line in p.stdout:output_queue.put(line)
        finally:output_queue.put(None)
    reader=threading.Thread(target=read_output,daemon=True);reader.start()
    try:
        while True:
            if cancel is not None and cancel.is_set():
                p.terminate()
                raise RuntimeError("Vorgang vom Benutzer abgebrochen.")
            if idle_timeout and time.monotonic()-last_output>idle_timeout:
                p.kill();p.wait()
                return 124,''.join(lines)+'\nZeitlimit: Prozess hat keinen Fortschritt mehr gemeldet.'
            try:line=output_queue.get(timeout=.1)
            except queue.Empty:continue
            if line is None:break
            last_output=time.monotonic()
            lines.append(line)
            if echo and log:
                log(line.rstrip("\n"))
        code = p.wait()
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
        reader.join(timeout=2)
        p.stdout.close()
    return code, "".join(lines)


def get_duration(path: Path, env: dict) -> float:
    tool = shutil.which("ffprobe", path=env.get("PATH", ""))
    if tool:
        code, result = run_cmd([tool, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], env)
        if code == 0:
            try:
                return float(result.strip().splitlines()[-1])
            except (ValueError, IndexError):
                pass
    raise RuntimeError("ffprobe.exe wurde nicht gefunden oder konnte die Audio-Länge nicht lesen.")


def audio_files(directory: Path) -> list[Path]:
    return sorted((p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in EXTS), key=lambda p: str(p).casefold())



def estimate_bpm(samples, sample_rate=11025):
    """Onset autocorrelation; may resolve to half or double tempo."""
    import numpy as np
    data=np.asarray(samples,dtype=np.float32)
    hop=128;frame=512
    if len(data)<sample_rate*8:return None
    frames=np.lib.stride_tricks.sliding_window_view(data,frame)[::hop]
    energy=np.sqrt(np.mean(frames*frames,axis=1))
    onset=np.maximum(0,np.diff(energy))
    if np.max(onset,initial=0)<1e-5:return None
    onset=onset-onset.mean()
    n=1<<(2*len(onset)-1).bit_length()
    spectrum=np.fft.rfft(onset,n=n)
    corr=np.fft.irfft(spectrum*np.conj(spectrum),n=n)[:len(onset)]
    corr/=np.maximum(1,len(onset)-np.arange(len(onset)))
    rate=sample_rate/hop
    lo=int(rate*60/210);hi=min(len(corr)-2,int(rate*60/70))
    if hi<=lo or corr[0]<=0:return None
    candidates=[i for i in range(lo+1,hi) if corr[i]>=corr[i-1] and corr[i]>corr[i+1]]
    if not candidates:return None
    def peak_strength(i):
        a,b,c=corr[i-1:i+2]
        d=.5*(a-c)/(a-2*b+c) if abs(a-2*b+c)>1e-12 else 0
        return (b-.25*(a-c)*d)*(1+np.exp(-.5*(np.log((60*rate/i)/130)/.45)**2))
    lag=max(candidates,key=peak_strength)
    if corr[lag]/corr[0]<.15:return None
    a,b,c=corr[lag-1:lag+2]
    delta=.5*(a-c)/(a-2*b+c) if abs(a-2*b+c)>1e-12 else 0
    return round(float(60*rate/(lag+float(np.clip(delta,-.5,.5)))),1)


def track_metadata(path, cfg, segment_start=None):
    """Local file format and BPM tag, otherwise a bounded excerpt estimate.

    For an online match, the original format stays unknown and mix BPM tags
    are ignored. Never infer original format from the downloaded set.
    """
    path=Path(path)
    empty={'audio_format':'—','bpm':None,'bpm_estimated':False}
    if not path.is_file():return empty
    stat=path.stat()
    record=('bpm-v3',str(path),stat.st_size,stat.st_mtime_ns,segment_start)
    key=hashlib.sha256(json.dumps(record,ensure_ascii=False).encode('utf-8')).hexdigest()
    cache=DATA/'Metadaten'/(key+'.json')
    try:return json.loads(cache.read_text(encoding='utf-8'))
    except (OSError,ValueError):pass
    env=env_with_ffmpeg(cfg.get('ffmpeg_dir',''))
    ffprobe=shutil.which('ffprobe',path=env['PATH'])
    ffmpeg=shutil.which('ffmpeg',path=env['PATH'])
    result={**empty,'audio_format':path.suffix[1:].upper() if segment_start is None else '—'}
    flags={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    duration=0
    if ffprobe:
        probe=subprocess.run([ffprobe,'-v','error','-show_format','-show_streams','-of','json',str(path)],
            env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12,**flags)
        if probe.returncode==0:
            info=json.loads(probe.stdout.decode('utf-8',errors='replace'))
            fmt=info.get('format',{});duration=float(fmt.get('duration') or 0)
            tags=dict(fmt.get('tags',{}))
            for stream in info.get('streams',[]):
                if stream.get('codec_type')=='audio':tags.update(stream.get('tags',{}))
            if segment_start is None:
                for name,value in tags.items():
                    if name.lower() not in {'bpm','tbpm','tempo'}:continue
                    try:bpm=float(str(value).strip().replace(',','.'))
                    except ValueError:continue
                    if 20<=bpm<=400:result.update(bpm=bpm,bpm_estimated=False);break
    if result['bpm'] is not None and result['bpm']<90:
        result['bpm_tag']=result['bpm']
        result['bpm']=None
    if result['bpm'] is None and ffmpeg:
        import numpy as np
        start=max(0,float(segment_start)) if segment_start is not None else min(30,max(0,duration/4))
        audio=subprocess.run([ffmpeg,'-v','error','-nostdin','-ss',str(start),'-i',str(path),
            '-t','40','-vn','-ac','1','-ar','11025','-f','f32le','-'],env=env,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,**flags)
        if audio.returncode==0 and len(audio.stdout)%4==0:
            bpm=estimate_bpm(np.frombuffer(audio.stdout,dtype='<f4'))
            result.update(bpm=bpm,bpm_estimated=bpm is not None)
    if result['bpm'] is None and result.get('bpm_tag'):
        result.update(bpm=result['bpm_tag'],bpm_estimated=False,bpm_suspect=True)
    try:
        cache.parent.mkdir(parents=True,exist_ok=True)
        temp=cache.with_suffix('.tmp');temp.write_text(json.dumps(result),encoding='utf-8');temp.replace(cache)
    except OSError:pass
    return result


def write_utf8_list(path: Path, values):
    # The wrapper makes audfprint's --list accept UTF-8 even on German Windows.
    path.write_text("".join(str(v) + "\n" for v in values), encoding="utf-8")


@contextmanager
def database_lock():
    DATA.mkdir(parents=True,exist_ok=True)
    with (DATA/'aufbau.lock').open('a+b') as handle:
        if handle.tell()==0:handle.write(b'0');handle.flush()
        handle.seek(0)
        locked=False
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            locked=True
        except OSError:
            raise RuntimeError('Der Datenbankaufbau läuft bereits in einem anderen Fenster.')
        try:yield
        finally:
            if locked:
                handle.seek(0)
                if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(handle,fcntl.LOCK_UN)


def build_database(cfg: dict, log, cancel: threading.Event, progress=None):
    with database_lock():
        return _build_database(cfg,log,cancel,progress)


def _build_database(cfg: dict, log, cancel: threading.Event, progress=None):
    """Analyze independently in bounded parallel workers; merge exactly once."""
    from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
    from collections import deque
    import uuid
    src=install_engine(cfg,log)
    folder=Path(cfg['library'])
    if not folder.is_dir():raise RuntimeError(f'Musikordner nicht vorhanden: {folder}')
    tracks=audio_files(folder)
    if not tracks:raise RuntimeError('Keine Musikdateien im ausgewählten Ordner.')
    records=[(str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in tracks]
    signature=hashlib.sha256(json.dumps(records,ensure_ascii=False).encode('utf-8')).hexdigest()
    cache=DATA/'Index_Aufbau'/signature[:24]
    cache.mkdir(parents=True,exist_ok=True)
    files_cache=DATA/'Fingerabdruck_Cache';files_cache.mkdir(exist_ok=True)
    LOGS.mkdir(parents=True,exist_ok=True)
    write_utf8_list(DATA/'bibliothek_liste.txt',tracks)
    total=len(tracks);base_count=0;base=None
    try:
        state=json.loads((cache/'fortschritt.json').read_text(encoding='utf-8'))
        n=int(state['done']);candidate=cache/f'checkpoint-{n:08d}.pklz'
        if (not state.get('finished') and state.get('signature')==signature
                and 0<n<=total and candidate.is_file() and candidate.stat().st_size>100):
            base_count=n;base=candidate
    except (OSError,ValueError,KeyError,TypeError):pass
    entries=[]
    for record in records[base_count:]:
        key=hashlib.sha256(json.dumps(record,ensure_ascii=False).encode('utf-8')).hexdigest()
        entries.append({'source':record[0],'cache':str(files_cache/(key+'.afpt')),'key':key})
    def valid(entry):
        path=Path(entry['cache'])
        try:
            size=path.stat().st_size
            with path.open('rb') as stream:magic=stream.read(16)
            return size>=16 and (size-16)%8==0 and magic==b'audfprinthashV00'
        except OSError:return False
    completed={e['key'] for e in entries if valid(e)}
    issues_path=cache/'nicht_lesbar.json'
    try:issues=json.loads(issues_path.read_text(encoding='utf-8'))
    except (OSError,ValueError):issues={}
    issues={e['key']:issues[e['key']] for e in entries if e['key'] in issues and e['key'] not in completed}
    completed.update(issues)
    initial=base_count+len(completed)
    started=time.monotonic();merge_started=None
    mutex=threading.RLock();stop=threading.Event()
    class WorkerCancel:
        def is_set(self):return cancel.is_set() or stop.is_set()
    worker_cancel=WorkerCancel()
    def emit(phase='index',merged=0):
        with mutex:
            count=base_count+len(completed)
            newly=count-initial
            eta=(time.monotonic()-started)*(total-count)/newly if newly>=5 else None
            if phase=='merge':
                eta=(time.monotonic()-merge_started)*(len(entries)-len(issues)-merged)/merged if merged else None
            data={'done':count,'total':total,'phase':phase,'merged':merged,
                  'merge_total':len(entries)-len(issues),'errors':len(issues),'eta':eta,
                  'percent':100.0 if phase=='done' else min(99.9,100*count/total)}
            temp=LOGS/'datenbank_fortschritt.tmp'
            temp.write_text(json.dumps(data),encoding='utf-8');temp.replace(LOGS/'datenbank_fortschritt.json')
            if progress:progress(data)
    workers=min(32,max(1,(os.cpu_count() or 2)-2))
    try:
        import psutil
        workers=min(workers,max(1,int(psutil.virtual_memory().available/(700*1024*1024))))
    except ImportError:workers=min(workers,2)
    workers=max(1,min(32,int(cfg.get('index_workers',workers))))
    env=env_with_ffmpeg(cfg['ffmpeg_dir'])
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[name]='1'
    wrapper=str(APP/'audfprint_utf8.py')
    log(f'Datenbank: {workers} parallele Arbeiter · {initial}/{total} Titel bereits gesichert.')
    emit()
    missing=[e for e in entries if e['key'] not in completed]
    batches=deque((missing[i:i+16],0) for i in range(0,len(missing),16))
    def run_batch(batch):
        manifest=cache/('job-'+uuid.uuid4().hex+'.json')
        manifest.write_text(json.dumps(batch,ensure_ascii=False),encoding='utf-8')
        expected={e['key']:e for e in batch}
        def line(text):
            if text.startswith('CACHE_DONE '):
                key=text.split()[-1]
                if key in expected and valid(expected[key]):
                    with mutex:completed.add(key);emit()
            else:log(text)
        try:
            return run_cmd([sys.executable,'-u',wrapper,'--cache-batch',str(manifest)],
                           env,src,log=line,cancel=worker_cancel,echo=True)
        finally:manifest.unlink(missing_ok=True)
    pool=ThreadPoolExecutor(max_workers=workers)
    pending={}
    try:
        while batches or pending:
            if cancel.is_set():raise RuntimeError('Abgebrochen. Fertige Fingerabdrücke bleiben gesichert.')
            while batches and len(pending)<workers:
                batch,retries=batches.popleft()
                batch=[e for e in batch if not valid(e) and e['key'] not in issues]
                if batch:pending[pool.submit(run_batch,batch)]=(batch,retries)
            if not pending:continue
            finished,_=wait(pending,timeout=.2,return_when=FIRST_COMPLETED)
            for future in finished:
                batch,retries=pending.pop(future)
                code,output=future.result()
                remaining=[e for e in batch if not valid(e)]
                with mutex:
                    completed.update(e['key'] for e in batch if valid(e));emit()
                if remaining:
                    emit('retry')
                    if len(remaining)==1:
                        if retries>=2:
                            entry=remaining[0]
                            issues[entry['key']]={'source':entry['source'],'error':f'Engine-Code {code}: '+output[-1200:]}
                            issues_path.write_text(json.dumps(issues,ensure_ascii=False,indent=2),encoding='utf-8')
                            with mutex:completed.add(entry['key']);emit()
                            log('NICHT LESBAR (siehe Datenbank/nicht_lesbar.json): '+entry['source'])
                        else:batches.appendleft((remaining,retries+1))
                    else:
                        middle=len(remaining)//2
                        batches.appendleft((remaining[middle:],0));batches.appendleft((remaining[:middle],0))
                    log('Arbeitsabschnitt wird wiederholt; fertige Titel bleiben erhalten.')
    finally:
        stop.set();pool.shutdown(wait=True,cancel_futures=True)
    if cancel.is_set():raise RuntimeError('Abgebrochen. Fertige Fingerabdrücke bleiben gesichert.')
    if not all(valid(e) or e['key'] in issues for e in entries):raise RuntimeError('Fingerabdrücke unvollständig; keine Datenbank ersetzt.')
    if base_count+len(entries)-len(issues)==0:raise RuntimeError('Keine lesbaren Musikdateien; bisherige Datenbank bleibt erhalten.')
    good_entries=[e for e in entries if e['key'] not in issues]
    manifest=cache/('merge-'+uuid.uuid4().hex+'.json')
    manifest.write_text(json.dumps({'base':str(base) if base else None,'entries':good_entries},ensure_ascii=False),encoding='utf-8')
    working=cache/('fertig-'+uuid.uuid4().hex+'.pklz')
    merge_started=time.monotonic();emit('merge')
    def merge_line(text):
        if text.startswith('MERGE_DONE '):emit('merge',int(text.split()[-1]))
        else:log(text)
    try:
        for attempt in range(3):
            code,output=run_cmd([sys.executable,'-u',wrapper,'--merge-cache',str(manifest),str(working)],
                                env,src,log=merge_line,cancel=cancel,echo=True)
            if cancel.is_set():raise RuntimeError('Abgebrochen. Fertige Fingerabdrücke bleiben gesichert.')
            if code==0 and working.is_file() and working.stat().st_size>100:break
        else:raise RuntimeError(f'Zusammenführen fehlgeschlagen ({code}). Fingerabdrücke sind gesichert. '+output[-700:])
        emit('save',len(good_entries))
        working.replace(DB)
        (DATA/'nicht_lesbar.json').write_text(json.dumps(list(issues.values()),ensure_ascii=False,indent=2),encoding='utf-8')
        (DATA/'bibliothek.json').write_text(json.dumps({'library':str(folder),'file_count':total-len(issues),
            'failed_count':len(issues),'created':stamp(),'files':[str(p) for p in tracks if str(p) not in {v['source'] for v in issues.values()}]},ensure_ascii=False,indent=2),encoding='utf-8')
        (cache/'fortschritt.json').write_text(json.dumps({'signature':signature,'done':total,
            'total':total,'finished':True}),encoding='utf-8')
        emit('done',len(good_entries))
        log(f'Datenbank gespeichert: {total-len(issues)} Titel · {len(issues)} nicht lesbar (Datenbank/nicht_lesbar.json).')
    finally:manifest.unlink(missing_ok=True)


@dataclass
class OfflineHit:
    song: str
    time: float
    score: int
    factor: float
    kind: str
    ref_time: float
    query_start: float
    segment: str
    support: float


def parse_matches(output: str, factor: float, kind: str) -> list[OfflineHit]:
    hits = []
    for row in output.splitlines():
        m = RANGE_RE.search(row)
        if m:
            d = m.groupdict()
            seg = SEGMENT_RE.search(d["query"])
            if not seg:
                continue
            segment_number = int(seg.group(1))
            qstart = float(d["qstart"])
            refstart = float(d["refstart"])
            duration = float(d["support"])
            if qstart < 0 or qstart > SEGMENT_SECONDS + 3:
                continue
            # This is only an approximation: some remix/transition edits break time alignment.
            set_time = (segment_number * SEGMENT_SECONDS + qstart) * factor
            hits.append(OfflineHit(d["ref"].strip(), max(0., set_time), int(d["count"]), factor,
                                   kind, refstart, qstart, d["query"], duration))
        else:
            m2 = SIMPLE_RE.search(row)
            if m2:
                d = m2.groupdict()
                seg = SEGMENT_RE.search(d["query"])
                if not seg:
                    continue
                set_time = int(seg.group(1)) * SEGMENT_SECONDS * factor
                hits.append(OfflineHit(d["ref"].strip(), set_time, int(d["count"]), factor,
                                       kind, float(d["refstart"]), 0, d["query"], 0))
    return hits


def grouped_hits(hits: list[OfflineHit], total_duration: float):
    # Keep the strongest variant for each song in each 30-s location; variants alone
    # are *not* independent confirmation.
    per_slot: dict[tuple[str,int], OfflineHit] = {}
    for h in hits:
        if h.score < MIN_SCORE:
            continue
        slot = int(h.time // SEGMENT_SECONDS)
        key = (h.song.casefold(), slot)
        if key not in per_slot or h.score > per_slot[key].score:
            per_slot[key] = h
    songs: dict[str,list[OfflineHit]] = {}
    for h in per_slot.values():
        songs.setdefault(h.song, []).append(h)
    accepted = []
    rejected = []
    for song, item in songs.items():
        item.sort(key=lambda h: h.time)
        group = []
        groups = []
        for h in item:
            if group and h.time - group[-1].time > CONFIRM_GAP_SECONDS:
                groups.append(group)
                group = []
            group.append(h)
        if group:
            groups.append(group)
        for g in groups:
            maximum = max(h.score for h in g)
            windows=len({h.segment for h in g})
            confident = maximum >= STRONG_SCORE or windows >= 2
            best = max(g, key=lambda h: h.score)
            # Estimate song start based on track-time alignment; approximate only.
            estimated_start = max(0., best.time - best.ref_time * best.factor)
            record = {"title": Path(song).stem, "full_path": song,
                      "time": min(total_duration, estimated_start),
                      "first_detection": min(h.time for h in g),
                      "last_detection": max(h.time for h in g),
                      "score": maximum, "samples": windows,
                      "methods":list(dict.fromkeys('Schnellscan · Originaltempo' if abs(h.factor-1)<.001
                          else f'Tiefenscan · {h.kind} {h.factor:.2f}×' for h in g)),
                      "factor": best.factor, "mode": best.kind,
                      "source": "offline", "confidence": "hoch" if confident else "unsicher"}
            (accepted if confident else rejected).append(record)
    accepted.sort(key=lambda x: x["time"])
    rejected.sort(key=lambda x: x["time"])
    return accepted, rejected


def mode_args(kind: str, factor: float) -> str:
    if kind == "tempo":
        return f"atempo={factor:.5f}"
    # Simulates DJ speed changes *without* key lock (pitch shifts too).
    return f"aresample=44100,asetrate={round(44100*factor)},aresample=11025"


def scan_offline(mix: Path, cfg: dict, duration: float, log, cancel: threading.Event):
    env = env_with_ffmpeg(cfg["ffmpeg_dir"])
    ffmpeg = shutil.which("ffmpeg", path=env["PATH"])
    if not ffmpeg:
        raise RuntimeError("ffmpeg.exe ist nicht verfügbar.")
    if not DB.is_file():
        raise RuntimeError("Offline-Datenbank ist nicht vorhanden. Bitte einmal 'Datenbank aufbauen' verwenden.")
    modes = [("tempo", f) for f in SPEEDS]
    if cfg.get("tempo_pitch"):
        modes += [("pitch", f) for f in SPEEDS if abs(f - 1.0) > 1e-6]
    all_hits = []
    errors = []
    with tempfile.TemporaryDirectory(prefix="set-almighty-") as tmp:
        directory = Path(tmp)
        for i, (kind, factor) in enumerate(modes, 1):
            if cancel.is_set():
                raise RuntimeError("Scan wurde abgebrochen.")
            log(f"Offline {i}/{len(modes)}: {kind} | Tempofaktor {factor:.2f}")
            files_dir = directory/"segmente"
            files_dir.mkdir(exist_ok=True)
            for old in files_dir.glob("part-*.*"):
                old.unlink()
            ffargs = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(mix),
                      "-map", "0:a:0", "-vn", "-af", mode_args(kind, factor),
                      "-ac", "1", "-ar", "11025", "-c:a", "pcm_s16le", "-f", "segment",
                      "-segment_time", str(SEGMENT_SECONDS), "-reset_timestamps", "1",
                      str(files_dir/"part-%04d.wav")]
            code, msg = run_cmd(ffargs, env, cancel=cancel)
            if code != 0:
                errors.append(f"ffmpeg {kind}/{factor}: {msg[-500:]}")
                log("  Warnung: Audio-Segmentierung fehlgeschlagen.")
                continue
            pieces = sorted(p for p in files_dir.glob("part-*.wav") if p.stat().st_size > 20000)
            if not pieces:
                errors.append(f"Keine Segmente bei {kind}/{factor}")
                continue
            filelist = directory/"query.txt"
            write_utf8_list(filelist, pieces)
            args = [sys.executable, str(APP/"audfprint_utf8.py"), "match", "--dbase", str(DB),
                    "--exact-count", "--find-time-range", "--max-matches", "1", "--min-count", str(MIN_SCORE),
                    "--list", str(filelist)]
            code, result = run_cmd(args, env, cwd=VENDOR, cancel=cancel)
            if code != 0:
                errors.append(f"audfprint {kind}/{factor}: {result[-500:]}")
                log("  Warnung: audfprint ist bei dieser Tempo-Variante fehlgeschlagen.")
            else:
                this = parse_matches(result, factor, kind)
                all_hits.extend(this)
                log(f"  {len(pieces)} Segmente, {len(this)} Trefferkandidaten")
    accepted, rejected = grouped_hits(all_hits, duration)
    log(f"Offline beendet: {len(accepted)} bestätigte Kandidaten, {len(rejected)} unsichere Kandidaten.")
    return accepted, rejected, errors


def unknown_probe_times(duration: float, confirmed: list[dict], limit: int) -> list[float]:
    """Choose spaced query points; avoid regions with confirmed offline hits."""
    # A match is centered near the timestamp at which the detection was confirmed,
    # not necessarily the estimated song start.
    known = [(max(0, x["first_detection"]-45), min(duration, x["last_detection"]+65)) for x in confirmed]
    probes = []
    step = max(45.0, duration / max(1, limit))
    t = 12.0
    while t + 12 < duration:
        if not any(a <= t <= b for a,b in known):
            probes.append(t)
        t += step
    return probes[:limit]


async def shazam_probes(mix: Path, points: list[float], cfg: dict, log, cancel: threading.Event, progress=None, on_hit=None):
    try:
        from shazamio import Shazam
    except ImportError:
        log("ShazamIO fehlt. Offline-Ergebnis bleibt erhalten; bitte Setup erneut ausführen.")
        return [], ["ShazamIO ist nicht installiert"]
    env = env_with_ffmpeg(cfg["ffmpeg_dir"])
    ffmpeg = shutil.which("ffmpeg", path=env["PATH"])
    results, errors = [], []
    semaphore=asyncio.Semaphore(max(1,min(4,int(cfg.get('shazam_workers',4)))))
    gate=cfg.get('_online_gate') or O.RequestGate()
    completed=0
    failures=0;stopped=False
    with tempfile.TemporaryDirectory(prefix="set-shazam-") as tmp:
        tmp=Path(tmp)
        async def probe(i,t):
            nonlocal completed,failures,stopped
            async with semaphore:
                if stopped:return
                if cancel.is_set():
                    raise RuntimeError("Scan wurde abgebrochen.")
                cache=O.probe_cache(DATA,mix,t,'ShazamIO-12s')
                cached=O.read_probe(cache)
                def detail(done,caption):
                    if cfg.get('_probe_progress'):cfg['_probe_progress'](f'probe/{i:04d}',done,3,f'Shazam · {hhmmss(t)} · '+caption)
                detail(0,'Ausschnitt vorbereiten')
                if cached is not None:
                    record=cached.get('record')
                    if record:
                        results.append(record)
                        if on_hit:on_hit(record)
                    completed+=1
                    detail(3,'gespeicherte Probe übernommen')
                    if progress:progress(completed,len(points))
                    log(f'Shazam {i}/{len(points)}: gespeicherte Probe übernommen')
                    return
                chunk = tmp / f"sample-{i:04d}.wav"
                args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(t),
                        "-i", str(mix), "-t", "12", "-map", "0:a:0", "-vn", "-ac", "1",
                        "-ar", "16000", "-c:a", "pcm_s16le", str(chunk)]
                code, msg = await asyncio.to_thread(run_cmd, args, env, cancel=cancel,idle_timeout=45)
                ok=False
                try:
                    if code!=0 or not chunk.is_file():raise RuntimeError('Ausschnitt nicht lesbar: '+msg[-200:])
                    detail(1,'Ausschnitt bereit')
                    # Local fingerprint work runs ahead of the shared HTTP budget.
                    preparer=Shazam(http_client=O.ShazamHTTP())
                    signature=None
                    if hasattr(preparer,'core_recognizer'):
                        signature=await asyncio.wait_for(preparer.core_recognizer.recognize_path(value=str(chunk)),timeout=30)
                    detail(2,'Fingerabdruck bereit · Online-Suche')
                    async def request():
                        async with O.ShazamHTTP() as http:
                            async with Shazam(http_client=http) as client:
                                if signature is not None:return await client.send_recognize_request_v2(sig=signature)
                                return await client.recognize(str(chunk))
                    attempt=0
                    while True:
                        if cancel.is_set():raise RuntimeError('Scan wurde abgebrochen.')
                        epoch=await gate.async_acquire(cancel,lambda s:log('Shazam: '+s))
                        try:
                            log(f'Shazam {i}/{len(points)} {hhmmss(t)}: Anfrage'+(' · erneuter Versuch' if attempt else ''))
                            response=await asyncio.wait_for(request(),timeout=max(3,min(35,float(cfg.get('shazam_timeout',20)))))
                            gate.successful(epoch)
                            break
                        except O.RateLimited as exc:
                            gate.recover(exc,epoch)
                            log('Shazam: Anfragelimit · Scan bleibt aktiv und wiederholt automatisch')
                        except Exception:
                            attempt+=1
                            if attempt>=2:raise
                            log(f'Shazam {i}/{len(points)}: kurzzeitiger Fehler · ein Wiederholungsversuch')
                        finally:gate.release()
                        await asyncio.sleep(.75)
                    track = response.get("track") if isinstance(response, dict) else None
                    if isinstance(track, dict) and track.get("title"):
                        results.append({"title": str(track.get("title", "")).strip(),
                                        "artist": str(track.get("subtitle", "")).strip(),
                                        "time": t, "source": "shazam", "confidence": "vorläufig",
                                        "url": str(track.get("url", ""))})
                        if on_hit:on_hit(results[-1])
                        O.save_probe(cache,results[-1])
                        log(f"Shazam {i}/{len(points)} {hhmmss(t)}: {track.get('subtitle','')} - {track.get('title')}")
                    else:
                        O.save_probe(cache,None)
                        log(f"Shazam {i}/{len(points)} {hhmmss(t)}: kein Treffer")
                    failures=0
                    ok=True
                except Exception as exc:
                    if cancel.is_set():raise RuntimeError('Scan wurde abgebrochen.')
                    errors.append(f"Shazam {hhmmss(t)}: {type(exc).__name__}: {exc}")
                    failures+=1
                    if failures>=3 and not stopped:
                        stopped=True
                        errors.append('ShazamIO nach drei aufeinanderfolgenden Fehlern beendet; verbleibende Proben wurden nicht abgefragt.')
                    log(f"Shazam {i}/{len(points)} {hhmmss(t)}: Fehler (Details im Ergebnis)")
                    detail(0,'Fehler · '+str(exc)[:90])
                finally:
                    if ok:completed+=1
                    if ok:detail(3,'geprüft')
                    if progress:progress(completed,len(points))
                await asyncio.sleep(0.5)
        tasks=[asyncio.create_task(probe(i,t)) for i,t in enumerate(points,1)]
        try:
            while tasks:
                if cancel.is_set():raise RuntimeError('Scan wurde abgebrochen.')
                _,pending=await asyncio.wait(tasks,timeout=.1)
                # Read completed exceptions before dropping task references.
                for task in set(tasks)-pending:task.result()
                tasks=list(pending)
        finally:
            for task in tasks:task.cancel()
            if tasks:await asyncio.gather(*tasks,return_exceptions=True)
    # Independent observations of the same recording at nearby positions support a stronger claim.
    for a in results:
        if any(b is not a and b["title"].casefold()==a["title"].casefold()
               and b["artist"].casefold()==a["artist"].casefold()
               and abs(b["time"]-a["time"]) <= 250 for b in results):
            a["confidence"] = "mehrfach erkannt"
    return results, errors


def consolidate_shazam(observations: list[dict]) -> list[dict]:
    """One tracklist entry per contiguous cluster; separate later repeats."""
    result: list[dict] = []
    for obs in sorted(observations, key=lambda r: r["time"]):
        key = (obs["artist"].casefold(), obs["title"].casefold())
        previous = next((r for r in reversed(result)
                         if (r["artist"].casefold(), r["title"].casefold()) == key
                         and obs["time"] - r["last_seen"] < 360), None)
        if previous:
            previous["last_seen"] = obs["time"]
            previous["samples"] += 1
            if previous["samples"] > 1:
                previous["confidence"] = "mehrfach erkannt"
        else:
            item = dict(obs)
            item["last_seen"] = obs["time"]
            item["samples"] = 1
            result.append(item)
    return sorted(result, key=lambda r: r["time"])


def final_report(mix: Path, duration: float, offline, weak, shazam, errors, cfg):
    lines = ["JOHANNA JOY\'S THE ALMIGHTY | TRACKLIST", "="*70, f"Set: {mix}",
             f"Länge: {hhmmss(duration)}", f"Erstellt: {stamp()}",
             f"Offline-Datenbank: {DB}",
             f"Onlinesuche: {'Shazam (inoffiziell)' if cfg['shazam'] else 'deaktiviert'}", "",
             "ERKANNTE TRACKS (vor Veröffentlichung anhören und prüfen)", "-"*70]
    combined = []
    for x in offline:
        combined.append((x["time"], f"{hhmmss(x['time'])} | {x['title']} | OFFLINE | {x['confidence']} | {x['score']} Hashes, {x['samples']} Fenster, Tempofaktor {x['factor']:.2f}, {x['mode']}"))
    for x in consolidate_shazam(shazam):
        combined.append((x["time"], f"{hhmmss(x['time'])} | {x['artist']} - {x['title']} | SHAZAM | {x['confidence']} ({x['samples']} Abfragen) | Zeitpunkt der ersten Abfrage, nicht exakter Trackbeginn"))
    if combined:
        lines.extend(line for _, line in sorted(combined, key=lambda x: x[0]))
    else:
        lines.append("Keine ausreichend sicheren Treffer. Das ist kein Beweis, dass die Musik nicht vorhanden ist.")
    lines += ["", "UNSICHERE OFFLINE-KANDIDATEN (nicht in die Tracklist übernehmen)", "-"*70]
    if weak:
        for x in weak[:100]:
            lines.append(f"{hhmmss(x['first_detection'])} | {x['title']} | {x['score']} Hashes, {x['samples']} Fenster")
        if len(weak) > 100:
            lines.append(f"... weitere {len(weak)-100} Kandidaten ausgeblendet")
    else:
        lines.append("Keine")
    lines += ["", "METHODIK / GRENZEN", "-"*70,
              "Offline: audfprint, Tempoanpassungen in 1-%-Schritten zwischen -10 % und +10 %.",
              "Tempo-Korrektur über ffmpeg/atempo; optional auch Pitch-Korrektur ohne Key-Lock.",
              "Bestätigte Offline-Treffer: mindestens 2 Zeitfenster oder ein sehr starker Einzeltreffer.",
              "Zeitpunkte sind Schätzungen; Übergänge, Remixe, Key-Lock und BPM-Variationen können Abweichungen verursachen.",
              "Shazam: nur für Stichproben unbekannter Bereiche, über eine inoffizielle Online-Schnittstelle.",
              "Shazam-Zeitstempel markieren die gescannte Stelle und NICHT den exakten Titelanfang.",
              "Auch mehrfach erkannte Tracks können falsch sein. Ergebnisse vor Veröffentlichung prüfen.", ""]
    if errors:
        lines += ["FEHLER / HINWEISE", "-"*70, *errors[:80]]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    base = re.sub(r'[^\w. -]+', '_', mix.stem, flags=re.UNICODE).strip()[:70] or "Mix"
    filename = f"{base}_Tracklist_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report = OUTPUT/filename
    report.write_text("\n".join(lines)+"\n", encoding="utf-8-sig")
    return report
