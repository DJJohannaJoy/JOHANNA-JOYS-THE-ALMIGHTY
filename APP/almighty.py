#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Johanna Joy's THE ALMIGHTY · 1.14 EMBER | Windows | Anthrazit + Karminrot.
Prototype, source included. Never overwrites the user's source audio/library.
"""
from __future__ import annotations
import asyncio
import datetime as dt
import importlib.util
import json
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
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from urllib.parse import urlparse


def relaunch_stable_runtime():
    """Old shortcuts must not run native audio jobs in a preview Python."""
    if os.name!='nt' or (sys.version_info.major,sys.version_info.minor,sys.version_info.releaselevel)==(3,12,'final'):
        return False
    base=Path(__file__).resolve().parent
    stable=base.parent/'runtime/python.exe'
    if not stable.is_file():
        raise RuntimeError('Bitte das vollständige Programmpaket neu entpacken; die eigene Python-Laufzeit fehlt.')
    flags={'creationflags':subprocess.CREATE_NO_WINDOW}
    check=subprocess.run([str(stable),'-c',"import sys;print((sys.version_info.major,sys.version_info.minor,sys.version_info.releaselevel)==(3,12,'final'))"],
                         capture_output=True,text=True,timeout=10,**flags)
    if check.returncode or check.stdout.strip()!='True':
        raise RuntimeError('Die lokale Python-3.12-Umgebung ist nicht bereit. Bitte das vollständige Programmpaket neu entpacken.')
    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONUTF8']='1';env['PYTHONIOENCODING']='utf-8'
    subprocess.Popen([str(stable),str(base/'almighty.py'),*sys.argv[1:]],cwd=base,env=env,**flags)
    return True


if __name__=='__main__' and relaunch_stable_runtime():
    raise SystemExit(0)

import audio_core as C
import engine_external as X
import local_ai as L
import track_results as R
import scan_jobs as J
import set_library as SL
import ui_text as I
import ai_method as A
messagebox=I.DialogProxy(messagebox)
filedialog=I.DialogProxy(filedialog)
import webbrowser
import importlib
from ui_theme import build_ui, BloodButton, show_completion

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_OK = True
except ImportError:
    TkinterDnD = None
    DND_OK = False

BG = '#090A0B'
PANEL = '#131415'
PANEL2 = '#1A1B1D'
BORDER = '#353638'
RED = '#C8001E'
RED_BRIGHT = '#FF1632'
RED_DARK = '#77101F'
FG = '#F3F0F1'
MUTED = '#B9B4BA'
GREEN = '#20E66C'
YELLOW = '#E4BA79'
BAD = '#FF1632'

# Explicitly identify the two non-offline legacy utilities; we cannot pretend
# the AudD/ACRCloud backend can work without credentials.
LEGACY_MIXID = 'mix-id · benutzt bereits Shazam'
SUPPORTED_SET_EXTS = C.EXTS | {'.mp4','.mkv','.mov','.webm','.m4v'}


def all_local_tracks(root: Path):
    return C.audio_files(root)


def probe_database() -> str:
    if C.DB.is_file() and C.DB.stat().st_size > 100:
        try:
            manifest = json.loads((C.DATA/'bibliothek.json').read_text(encoding='utf-8'))
            count = manifest.get('file_count')
            return 'Bereit' + (f' · {count} Tracks' if count else '')
        except (OSError, ValueError):
            return 'Bereit · importiert'
    return 'Fehlt'


def probe_engine(cfg: dict) -> bool:
    return C.locate_source(cfg) is not None


def select_target_fragments(parts: list[Path], duration: float, confirmed: list[dict], factor: float) -> list[Path]:
    # Time of the transformed segment maps to original timeline by *factor.
    # Reduce work only for well-supported offline regions.
    intervals = [(max(0., x['first_detection'] - 25.),
                  min(duration, x['last_detection'] + 35.)) for x in confirmed
                 if x.get('score', 0) >= 200 or x.get('samples', 0) >= 2]
    if not intervals:
        return parts
    result = []
    for p in parts:
        m = C.SEGMENT_RE.search(p.name)
        if not m:
            continue
        midpoint = (int(m.group(1))*C.SEGMENT_SECONDS + C.SEGMENT_SECONDS/2)*factor
        if not any(left <= midpoint <= right for left, right in intervals):
            result.append(p)
    return result


def do_match(parts: list[Path], factor: float, kind: str, directory: Path, env: dict,
             cancel: threading.Event, log, progress=None) -> tuple[list[C.OfflineHit], list[str]]:
    if not parts:
        return [], []
    flist = directory/'to_match.txt'
    C.write_utf8_list(flist, parts)
    command = [sys.executable, str(C.APP/'audfprint_utf8.py'), 'match',
               '--dbase', str(C.DB), '--exact-count', '--find-time-range',
               '--max-matches', '2', '--min-count', '25', '--list', str(flist)]
    completed=0
    def observe(line):
        nonlocal completed
        if line.startswith('QUERY_DONE '):
            completed=max(completed,min(len(parts),int(line.split()[-1])))
            if progress:progress(completed,len(parts))
        elif log:log(line)
    code, output = C.run_cmd(command, env, cwd=C.VENDOR, cancel=cancel,echo=True,log=observe)
    for retry in range(2):
        if code==0:break
        log('Offline-Abfrage wird nach einem Engine-Fehler wiederholt …')
        code,output=C.run_cmd(command,env,cwd=C.VENDOR,cancel=cancel,echo=True,log=observe)
    if code:
        log(f'Warnung: Offline-Abgleich fehlgeschlagen ({kind} {factor:.2f}): {output[-250:]}')
        return [], [f'{kind} {factor:.2f}: {output[-500:]}']
    return C.parse_matches(output, factor, kind), []


def split_audio(mix: Path, directory: Path, cfg: dict, factor: float,
                kind: str, cancel: threading.Event):
    env = C.env_with_ffmpeg(cfg['ffmpeg_dir'])
    ffmpeg = shutil.which('ffmpeg', path=env['PATH'])
    if not ffmpeg:
        raise RuntimeError('FFmpeg fehlt. Bitte in Einstellungen die ffmpeg.exe auswählen.')
    directory.mkdir(parents=True, exist_ok=True)
    for f in directory.glob('part-*.wav'):
        f.unlink()
    if abs(factor-1.) < 1e-8:
        filter_args = []
    else:
        filter_args = ['-af', C.mode_args(kind, factor)]
    command = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mix),
               '-map', '0:a:0', '-vn', *filter_args,
               '-ac', '1', '-ar', '11025', '-c:a', 'pcm_s16le', '-f', 'segment',
               '-segment_time', str(C.SEGMENT_SECONDS), '-reset_timestamps', '1',
               str(directory/'part-%04d.wav')]
    code, output = C.run_cmd(command, env, cancel=cancel)
    if code:
        raise RuntimeError('FFmpeg konnte Set nicht aufteilen: ' + output[-800:])
    return [p for p in sorted(directory.glob('part-*.wav')) if p.stat().st_size > 20000]


def two_pass_offline(mix: Path, cfg: dict, duration: float, notify, cancel: threading.Event):
    return J.offline_scan(mix,cfg,duration,notify,cancel,split_audio,do_match)


def format_report(mix: Path, duration: float, offline, weak, shazam, errors, cfg):
    """TXT plus optional machine-readable JSON. Timestamps are estimates."""
    output = C.final_report(mix, duration, offline, weak, shazam, errors, cfg)
    # Correct the older static methodology text: v0.2 first runs a normal pass.
    data = output.read_text(encoding='utf-8-sig')
    data += ('\nV0.2: Stufe A audfprint Originaltempo; Stufe B dasselbe audfprint '
             'mit Tempo-Varianten für unklare Stellen. '\
             'mix-id verwendet Shazam online und ist keine zweite Offline-Engine.\n')
    output.write_text(data, encoding='utf-8-sig')
    return output


# Only directly supported media hosts are accepted. No arbitrary URL fetching.
def media_provider(url: str) -> str | None:
    """Return a supported service name (not a guarantee a specific link will work)."""
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
            return None
        if host in ('youtu.be', 'youtube.com') or host.endswith('.youtube.com'):
            return 'YouTube'
        if host in ('soundcloud.com', 'on.soundcloud.com', 'soundcloud.app.goo.gl') or host.endswith('.soundcloud.com'):
            return 'SoundCloud'
        if host == 'mixcloud.com' or host.endswith('.mixcloud.com'):
            return 'Mixcloud'
    except (ValueError, TypeError):
        pass
    return None


def download_online(url: str, cfg: dict, cancel: threading.Event, log) -> Path:
    provider = media_provider(url)
    if not provider:
        raise RuntimeError('Bitte einen YouTube-, SoundCloud- oder Mixcloud-Link eingeben.')
    import yt_dlp  # noqa: F401; installed via requirements.txt
    from uuid import uuid4
    temp = C.USER_ROOT/'Downloads_Online'/uuid4().hex[:10]
    temp.mkdir(parents=True, exist_ok=False)
    template = str(temp/'%(title).100s-%(id)s.%(ext)s')
    env = C.env_with_ffmpeg(cfg['ffmpeg_dir'])
    # --no-playlist: one set/track, never silently download a whole account/playlist.
    cmd = [sys.executable, '-m', 'yt_dlp', '--no-playlist', '--extract-audio',
           '--audio-format', 'mp3', '--no-progress', '--output', template, url]
    code, result = C.run_cmd(cmd, env, cancel=cancel, echo=True, log=log)
    if code != 0:
        raise RuntimeError(f'{provider}-Link konnte nicht geladen werden (Login, Sperre oder Format): ' + result[-800:])
    candidates = sorted(temp.glob('*.mp3'), key=lambda p: p.stat().st_mtime)
    if candidates:
        return candidates[-1]
    raise RuntimeError(f'{provider}-Download abgeschlossen, aber keine MP3 gefunden.')


class AppGUI:
    def __init__(self):
        for p in [C.DATA, C.OUTPUT, C.LOGS]:
            p.mkdir(parents=True, exist_ok=True)
        self.cfg = C.read_config()
        if os.name=='nt':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('JohannaJoy.TheAlmighty.App')
        self.root = TkinterDnD.Tk() if DND_OK else tk.Tk()
        self.language=I.Language(self.cfg.get('language','de'));self.root._almighty_language=self.language
        messagebox.language=self.language;filedialog.language=self.language
        self.root.title("Johanna Joy's THE ALMIGHTY · "+I.VERSION_LABEL)
        self.root.geometry('1150x840')
        self.root.minsize(980, 730)
        self.root.configure(bg=BG)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.running = False
        self.library = tk.StringVar(value=self.cfg.get('library') or C.DEFAULT_LIBRARY)
        self.set_path = tk.StringVar(value='')
        self.media_url = tk.StringVar(value='')
        self.use_shazam = tk.BooleanVar(value=bool(self.cfg.get('shazam', True)))
        self.pitch = tk.BooleanVar(value=bool(self.cfg.get('tempo_pitch', False)))
        self.exhaustive_tempo = tk.BooleanVar(value=bool(self.cfg.get('exhaustive_tempo',False)))
        self.max_shazam = tk.StringVar(value=str(self.cfg.get('max_shazam', 50)))
        self.mixid_enabled = tk.BooleanVar(value=bool(self.cfg.get('mixid', True)))
        self.mixid_dir = tk.StringVar(value=self.cfg.get('mixid_dir',''))
        self.use_local_ai = tk.BooleanVar(value=bool(self.cfg.get('local_ai_review',False)))
        self.use_ai_method=tk.BooleanVar(value=bool(self.cfg.get('local_ai_method',True)))
        self._ai_worker=None;self._ai_findings={};self._ai_by_track={}
        self.stats = tk.StringVar(value='Noch keine Treffer')
        self.stages = {}
        self.statuses = {}
        self.current_hits = {}
        self.raw_hits = {}
        self._received_order = 0
        self.progress_tasks = {}
        self.stage_status = {}
        self.last_scan = None
        self._resume_pending=set()
        self._reset_requested=False
        try:self._skip_restore=bool(json.loads((C.DATA/'arbeitsstand.json').read_text(encoding='utf-8')).get('empty',False))
        except (OSError,ValueError,AttributeError):self._skip_restore=False
        self._metadata_jobs = queue.Queue()
        self._metadata_worker_started = False
        self.settings_open = False
        self.C_APP = C.APP
        self.C_OUTPUT = C.OUTPUT
        self.C_DATA = C.DATA
        self.DND_OK = DND_OK
        self.DND_FILES = DND_FILES if DND_OK else None
        self._ui()
        self.root.after(100,self._language_tick)
        self.root.after(80, self._events)
        self.root.after(150, self.restore_last_scan)
        self.root.after(500, self._refresh_readiness)
        self.root.after(700, lambda:self.check_local_ai(quiet=True))

    def _label(self, parent, text, size=10, bold=False, color=FG, bg=None):
        return tk.Label(parent, text=text, font=('Segoe UI', size, 'bold' if bold else 'normal'),
                        fg=color, bg=bg or parent.cget('bg'), anchor='w')

    def _language_tick(self):
        self.language.apply(self.root)
        self.root.after(300,self._language_tick)

    def toggle_language(self):
        self.language.code='en' if self.language.code=='de' else 'de'
        self.cfg['language']=self.language.code
        try:C.save_config(self.cfg)
        except OSError as exc:self._notify('log',str(exc))
        self.language.apply(self.root)
        def repaint(widget):
            if isinstance(widget,BloodButton):widget._paint()
            elif hasattr(widget,'_language_redraw'):widget._language_redraw()
            for child in widget.winfo_children():repaint(child)
        repaint(self.root)
        self.header._last_width=0;self.header.redraw();self.stagebar.redraw()
        self.progress_panel.update()

    def _button(self, parent, text, command, bg=RED, fg=FG, width=None):
        return BloodButton(parent,text,command,width=width*10 if width else 180,
                           height=42,outline_only=bg==PANEL2,font_size=10,fg=fg)

    def _entry(self, parent, var, width=None):
        entry = tk.Entry(parent, textvariable=var, bg=PANEL2, fg=FG,
                         insertbackground=FG, relief='flat', bd=0,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=RED_BRIGHT, font=('Segoe UI', 10))
        if width: entry.configure(width=width)
        return entry

    def _ui(self):
        # Actual, responsive controls; follows the approved EMBER layout.
        build_ui(self)

    def _build_settings(self):
        """All advanced controls remain available through the top-right gear."""
        self.settings_window=tk.Toplevel(self.root)
        self.settings_window.title("THE ALMIGHTY · Einstellungen")
        self.settings_window.configure(bg=PANEL)
        self.settings_window.geometry('720x790')
        self.settings_window.minsize(620,740)
        self.settings_window.transient(self.root)
        self.settings_window.protocol('WM_DELETE_WINDOW',self.toggle_settings)
        self.settings=tk.Frame(self.settings_window,bg=PANEL,padx=20,pady=16)
        self.settings.pack(fill='both',expand=True)
        self.settings_window.withdraw()
        self._label(self.settings,'MUSIKDATENBANK  ·  Einmalig vorbereiten',10,True,bg=PANEL).pack(anchor='w')
        librow=tk.Frame(self.settings,bg=PANEL)
        librow.pack(fill='x',pady=(5,8))
        self._entry(librow,self.library).pack(side='left',fill='x',expand=True,ipady=6)
        self._button(librow,'...',self.pick_library,bg=PANEL2).pack(side='left',padx=4)
        self.index_button=self._button(self.settings,'DATENBANK AUFBAUEN / ERNEUERN',self.start_index,bg=RED_DARK)
        self.index_button.pack(fill='x',pady=(0,5))
        self._button(self.settings,'Vorhandene .pklz-Datenbank importieren',self.import_db,bg=PANEL2).pack(fill='x')
        trow=tk.Frame(self.settings,bg=PANEL)
        trow.pack(fill='x',pady=7)
        self._check(trow,'ShazamIO · zusätzliche verteilte Proben',self.use_shazam).pack(anchor='w')
        self._check(trow,'Gründliche Suche: 20 statt 6 Tempofaktoren (langsamer)',self.exhaustive_tempo).pack(anchor='w')
        self._check(trow,'Tempoänderungen ohne Key Lock prüfen (langsamer)',self.pitch).pack(anchor='w')
        opt=tk.Frame(self.settings,bg=PANEL)
        opt.pack(fill='x')
        self._label(opt,'Max. Shazam-Anfragen:',9,bg=PANEL).pack(side='left')
        tk.Spinbox(opt,from_=0,to=250,width=5,textvariable=self.max_shazam,
                   bg=PANEL2,fg=FG,buttonbackground=PANEL2,relief='flat').pack(side='left',padx=7)
        self._label(self.settings,'ORIGINAL-PROGRAMM',10,True,bg=PANEL).pack(anchor='w',pady=(12,4))
        self._check(self.settings,'mix-id aktivieren (Shazam-basiert)',self.mixid_enabled).pack(anchor='w')
        self._label(self.settings,'KI-NACHPRÜFUNG · LOKALES MODELL',10,True,bg=PANEL).pack(anchor='w',pady=(12,4))
        self._check(self.settings,'KI-Methode automatisch: Remixes, Grenzfälle und Fundstellen prüfen',self.use_ai_method).pack(anchor='w')
        kirow=tk.Frame(self.settings,bg=PANEL)
        kirow.pack(fill='x',pady=(4,3))
        self._button(kirow,'LM STUDIO HERUNTERLADEN',self.install_local_ai,bg=RED_DARK).pack(side='left',fill='x',expand=True,padx=(0,4))
        self._button(kirow,'KI-VERBINDUNG PRÜFEN',self.check_local_ai,bg=PANEL2).pack(side='left',fill='x',expand=True)
        self._button(self.settings,'ALTERNATIVE: OLLAMA',self.install_ollama,bg=PANEL2).pack(fill='x')
        self._label(self.settings,'Die KI bewertet Remix-Grenzfälle anhand echter Fingerprints und gefundener Metadaten.',
                    9,color=MUTED,bg=PANEL).pack(anchor='w',pady=(8,2))
        self._button(self.settings,'ERGEBNISORDNER ÖFFNEN',lambda:self._open(C.OUTPUT),bg=PANEL2).pack(fill='x',pady=(10,3))
        self._button(self.settings,'SCHLIESSEN',self.toggle_settings,bg=RED_DARK).pack(fill='x',pady=3)

    def _check(self,parent,text,var):
        return tk.Checkbutton(parent,text=text,variable=var,bg=PANEL,fg=FG,selectcolor=PANEL2,
                              activebackground=PANEL,activeforeground=FG,font=('Segoe UI',9),anchor='w')

    def toggle_settings(self):
        self.settings_open=not self.settings_open
        if self.settings_open:
            self.root.update_idletasks()
            x=max(0,min(self.root.winfo_screenwidth()-720,
                        self.root.winfo_x()+(self.root.winfo_width()-720)//2))
            y=max(0,min(self.root.winfo_screenheight()-830,
                        self.root.winfo_y()+(self.root.winfo_height()-790)//2))
            self.settings_window.geometry(f'720x790+{x}+{y}')
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()
        else:
            self.settings_window.withdraw()

    def _dropped(self,event):
        candidates=self.root.tk.splitlist(event.data)
        if candidates:
            name=str(candidates[0]).strip()
            if Path(name).is_file() and Path(name).suffix.lower() in SUPPORTED_SET_EXTS:
                self.set_path.set(name)
            else:
                messagebox.showwarning('JOHANNA JOY\'S THE ALMIGHTY','Bitte eine Audiodatei ablegen.')
            self._refresh_readiness()

    def _stage(self,key,state,detail=''):
        self.events.put(('stage',key,state,detail))

    def _notify(self,kind,*args):
        self.events.put((kind,*args))

    def _stage_ui(self,key,state,detail):
        # Six real scan stages with stable captions; never replace the stage
        # labels with long status strings that break the UI grid.
        if key not in self.stages:
            return
        self.stage_status[key]={'state':state,'detail':detail}
        if state=='failed' and key in self.progress_tasks:self.progress_tasks[key]['detail']='FEHLER · '+detail
        icon,caption = self.stages[key]
        color = {'done':GREEN,'running':RED_BRIGHT,'retrying':RED_BRIGHT,'failed':BAD,'paused':YELLOW,
                 'skipped':YELLOW,'waiting':MUTED}.get(state,MUTED)
        sym = {'done':'✓','running':'◉','retrying':'◉','failed':'✕','paused':'Ⅱ',
               'skipped':'–','waiting':'○'}.get(state,'○')
        icon.configure(text=sym,fg=color)
        caption.configure(fg=FG if state in ('running','retrying','done') else color)
        if state in ('waiting','running','retrying','done','skipped'):self.stagebar.progress_labels.pop(key,None)
        if state=='waiting':self.stagebar.percentages[key]=0;self.stagebar.skipped.discard(key)
        if state=='done':self.stagebar.percentages[key]=100
        if state=='skipped':self.stagebar.skipped.add(key)
        self.stagebar.redraw()
        if detail and state in ('running','retrying','failed','paused'):
            self.progress.set(detail)

    def _events(self):
        try:
            while True:
                event=self.events.get_nowait()
                kind=event[0]
                if self._reset_requested:
                    if kind in ('done','error'):
                        self._running(False);self._clear_current_set()
                    continue
                if kind=='ai_method':
                    self._handle_ai_event(*event[1:]);continue
                if kind=='stage':
                    self._stage_ui(*event[1:])
                elif kind=='stage_activity':
                    _,key,detail=event
                    if key in self.progress_tasks:self.progress_tasks[key]['detail']=detail
                    self.progress.set(detail)
                elif kind=='stage_progress':
                    _,key,done,total,detail=event
                    value=100*max(0,min(done,total))/total if total else 0
                    self.progress_tasks[key]={'done':done,'total':total,'percent':value,'detail':detail}
                    if key in self.stagebar.percentages:
                        self.stagebar.percentages[key]=value
                        self.stagebar.redraw()
                    if key in self.stagebar.percentages or key=='KI':
                        enabled=[v for k,v in self.stagebar.percentages.items() if k not in self.stagebar.skipped]
                        if 'KI' in self.progress_tasks and 'KI' not in self.stagebar.percentages:enabled.append(self.progress_tasks['KI']['percent'])
                        self.progressbar.set_progress(sum(enabled)/max(1,len(enabled))/100)
                    self.progress.set(detail)
                elif kind=='progress':
                    _,phase,msg=event
                    self.progress.set(msg)
                elif kind=='index_progress':
                    value=event[1]
                    percent=f"{value['percent']:.1f}".replace('.',',')
                    if value['phase']=='done':detail='Fertig'+(f" · {value['errors']} nicht lesbar" if value.get('errors') else '')
                    elif value['phase']=='merge':detail=f"Zusammenführen {value.get('merged',0)}/{value.get('merge_total',value['total'])}"
                    elif value['phase']=='save':detail='Datenbank speichern …'
                    elif value['phase']=='retry':detail='Abschnitt wird erneut geprüft …'
                    elif value['eta'] is None:detail='Restzeit wird berechnet …'
                    else:detail='Rest ca. '+C.hhmmss(value['eta'])
                    self.progress.set(f"{percent} % · {value['done']}/{value['total']} Titel · {detail}")
                    self.progressbar.set_progress(value['percent']/100)
                elif kind=='log':
                    self.logbox.configure(state='normal')
                    self.logbox.insert('end',str(event[1])+'\n')
                    self.logbox.see('end')
                    self.logbox.configure(state='disabled')
                elif kind=='hits':
                    self._render_hits(event[1])
                elif kind=='track_metadata':
                    _,key,record,metadata=event
                    if self.current_hits.get(key) is record:
                        record.update(metadata)
                        record.pop('_metadata_pending',None)
                        self._render_hits([])
                elif kind=='ai_status':
                    self.ai_status_text.set(str(event[1]))
                    if len(event)<3 or not event[2]:messagebox.showinfo('Lokale KI · Status',str(event[1]))
                elif kind=='set_path':
                    self.set_path.set(str(event[1]))
                elif kind=='scan_finished':
                    self.last_scan=event[1]
                    if self._ai_findings:self.last_scan['results']['ai_review']=self._ai_findings
                    self._scan_archive_pending=False
                    self._completion_context=event[1]
                    self._resume_pending={k for k,v in self.stage_status.items() if k in {'A','B','M','S'} and v['state'] not in ('done','skipped')}
                    self.start_button.configure(text='SCANNEN')
                    self.save_current_set(quiet=True)
                    enabled=[v for k,v in self.stagebar.percentages.items() if k not in self.stagebar.skipped]
                    ai_active=self.stage_status.get('KI',{}).get('state') not in ('done','skipped',None)
                    self.progressbar.set_progress(sum(enabled)/len(enabled)/100 if self._resume_pending or ai_active else 1)
                    failed=sum(v['state'] in ('failed','paused') for k,v in self.stage_status.items() if k in {'A','B','M','S'})
                    self.progress.set('Teilprüfung gespeichert · Methoden offen · SCANNEN zum Fortsetzen' if self._resume_pending else
                                      f'100 % · Beendet mit {failed} fehlerhaften Methoden · Erneut prüfen' if failed else
                                      'Scan gespeichert · KI-Nachprüfung läuft im Hintergrund' if ai_active else '100 % · Scan beendet · Ergebnis gespeichert')
                elif kind=='ai_review_done':
                    self.ai_review_path=Path(event[1]);self.progressbar.set_progress(1)
                    self.progress.set('KI-Textprüfung gespeichert')
                    self.ai_status_text.set('KI-Textprüfung fertig\n'+self.cfg.get('local_ai_model',''))
                elif kind=='done':
                    self._running(False)
                    self._refresh_readiness()
                    context=getattr(self,'_completion_context',None)
                    self._completion_context=None
                    show_completion(self,str(event[1]),context)
                elif kind=='error':
                    self._running(False)
                    if self._ai_worker:self._ai_worker.abort();self._stage_ui('KI','failed','KI durch Abbruch des Scans beendet')
                    self._refresh_readiness()
                    if self.current_hits:self.save_current_set(quiet=True)
                    self.progress.set('Abgebrochen' if self.cancel.is_set()
                                      else 'Fehler – siehe Protokoll')
                    messagebox.showerror('JOHANNA JOY\'S THE ALMIGHTY',str(event[1]))
        except queue.Empty:
            pass
        self.root.after(100,self._events)

    def _render_hits(self,hits):
        for rec in hits:
            token=(rec.get('source'),rec.get('full_path'),rec.get('artist'),rec.get('title'),
                   int(float(rec.get('time',0))/20),tuple(rec.get('methods') or []))
            if token not in self.raw_hits:self._received_order+=1
            order=self.raw_hits[token]['_received_order'] if token in self.raw_hits else self._received_order
            self.raw_hits[token]={**rec,'_received_order':order}
        previous=self.current_hits;self.current_hits={}
        for rec in R.merge_records(self.raw_hits.values()):
            k=rec['track_id'];hit=previous.get(k,{})
            hit.update(rec);self.current_hits[k]=hit
            if 'bpm' not in hit and not hit.get('_metadata_pending'):
                source=hit.get('full_path') if hit.get('source')=='offline' else self.set_path.get().strip()
                if source and Path(source).is_file():
                    hit['_metadata_pending']=True
                    local=hit.get('source')=='offline'
                    if local:hit['audio_format']=Path(source).suffix[1:].upper()
                    self._metadata_jobs.put((k,hit,source,None if local else max(0,float(hit.get('time',0))+5),dict(self.cfg)))
                    if not self._metadata_worker_started:
                        self._metadata_worker_started=True
                        threading.Thread(target=self._metadata_worker,daemon=True).start()
                else:hit['bpm']=None
        selected={getattr(self,'_hit_rows',{}).get(row,{}).get('track_id') for row in self.result_table.selection()}
        position=self.result_table.yview()[0]
        for item in self.result_table.get_children():
            self.result_table.delete(item)
        from tkinter.font import Font
        font=Font(root=self.root,family='Segoe UI',size=10)
        def fit(text,column):
            text=str(text);width=self.result_table.column(column,'width')-14
            if font.measure(text)<=width:return text
            low,high=0,len(text)
            while low<high:
                middle=(low+high+1)//2
                if font.measure(text[:middle]+'…')<=width:low=middle
                else:high=middle-1
            return text[:low]+'…'
        self._hit_rows={}
        for hit in sorted(self.current_hits.values(),key=lambda r:r.get('time',0)):
            name=(hit.get('artist','')+' – ' if hit.get('artist') else '')+hit['title']
            bpm=hit.get('bpm')
            bpm_text=('≈' if hit.get('bpm_estimated') else '')+f'{bpm:g}' if isinstance(bpm,(int,float)) else ('…' if hit.get('_metadata_pending') else '—')
            if hit.get('bpm_suspect'):bpm_text+='?'
            values=(hit['number'],C.hhmmss(hit.get('time',0)),fit(name,'title'),hit.get('audio_format','—'),bpm_text,
                    fit(' → '.join(hit['methods']),'method'),fit(' + '.join(hit['sources']),'source'))
            row=self.result_table.insert('', 'end', values=values)
            self._hit_rows[row]=hit
            if hit['track_id'] in selected:self.result_table.selection_add(row)
        self.result_table.yview_moveto(position)
        done=sum('bpm' in h for h in self.current_hits.values());total=len(self.current_hits)
        self.metadata_progress.set_progress(done/total if total else 0)
        self.metadata_caption.set(f'Format / BPM · {done}/{total} · {100*done/total if total else 0:.0f} %')
        self.stats.set(f'{total} Tracks')

    def show_hit_detail(self,event=None):
        selection=self.result_table.selection()
        if not selection:return
        hit=getattr(self,'_hit_rows',{}).get(selection[0])
        if not hit:return
        dialog=tk.Toplevel(self.root);dialog.title(f"Track {hit['number']} · Erkennungsdetails")
        self.hit_dialog=dialog
        dialog.geometry('850x520');dialog.configure(bg=PANEL);dialog.transient(self.root)
        text=scrolledtext.ScrolledText(dialog,bg=PANEL,fg=FG,font=('Segoe UI',11),wrap='word')
        text.pack(fill='both',expand=True,padx=15,pady=15)
        lines=[f"{hit['number']:02d} · {C.hhmmss(hit['time'])} · {hit.get('artist','')} – {hit['title']}",
               '','Methoden in Erkennungsreihenfolge:',' → '.join(hit['methods']),'','Quellen:',*hit['sources']]
        if hit.get('bpm_tag'):lines+=['',f"Ursprünglicher BPM-Tag: {hit['bpm_tag']} · angezeigter Wert: {hit.get('bpm')}"]
        for ev in hit['evidence']:
            lines+=['',C.hhmmss(ev['time'])+' · '+' → '.join(ev['methods']),ev['source']]
            if ev.get('path'):lines.append(ev['path'])
            if ev.get('url'):lines.append(ev['url'])
        text.insert('1.0','\n'.join(lines));text.configure(state='disabled')
        actions=tk.Frame(dialog,bg=PANEL);actions.pack(fill='x',padx=15,pady=(0,12))
        for index,(provider,url) in enumerate(SL.search_links(hit).items()):
            actions.columnconfigure(index,weight=1,uniform='providers')
            BloodButton(actions,provider,lambda u=url:webbrowser.open(u),width=135,height=35,outline_only=True).grid(row=0,column=index,sticky='ew',padx=(0,7))

    _time=staticmethod(C.hhmmss)

    def show_results(self):
        from ui_workspace import ResultsWindow
        self.results_window=ResultsWindow(self,lambda:sorted(self.current_hits.values(),key=lambda t:t.get('time',0)))
        return self.results_window

    def show_library(self):
        from ui_workspace import show_library
        show_library(self)

    def show_rekordbox_export(self):
        from ui_rekordbox import show_export
        name=Path(self.set_path.get().strip()).stem or 'Set'
        return show_export(self,list(self.current_hits.values()),name)

    def _start_audit(self,path,cfg,duration=0,observations=(),core_cancel=None,offline_pending=False):
        if self._ai_worker:self._ai_worker.abort()
        self._ai_findings={};self._ai_by_track={}
        self._ai_live_detail='';self._ai_live_started=time.monotonic()
        for key in [k for k in self.progress_tasks if k=='KI' or k.startswith('KI/')]:self.progress_tasks.pop(key,None)
        worker=A.Audit(path,cfg,C.DATA,self._notify,match=do_match,duration=duration,
                       core_cancel=core_cancel,audio_ready=not offline_pending)
        self._ai_worker=worker;self._notify('stage','KI','waiting','KI-Nachprüfung startet')
        worker.offer(observations);worker.start()
        return worker

    def start_ai_method(self,force=False):
        if self.running:return
        if not self.last_scan:
            messagebox.showinfo('KI-Nachprüfung','Bitte zuerst ein Set scannen oder ein Ergebnis laden.');return
        path=Path(self.last_scan['path'])
        if not path.is_file():
            messagebox.showwarning('KI-Nachprüfung','Die Audiodatei fehlt. Bitte zuerst neu zuweisen.');return
        cfg={**self._settings_cfg(),'ai_force':force}
        worker=self._start_audit(path,cfg,self.last_scan.get('duration',0),self.last_scan['results'].get('observations',[]))
        worker.offer_weak(self.last_scan['results'].get('weak',[]))
        worker.finish(self.last_scan.get('report'))

    def _handle_ai_event(self,run_id,kind,value):
        if not self._ai_worker or run_id!=self._ai_worker.run_id:return
        if kind=='state':
            self._stage_ui('KI',value['state'],value['detail'])
            if value['state'] in ('done','failed','skipped'):self.ai_status_text.set(value['detail'])
        elif kind in ('progress','case_progress','case_activity'):
            if kind in ('case_progress','case_activity') and value['detail']!=getattr(self,'_ai_live_detail',''):
                self._ai_live_detail=value['detail'];self._ai_live_started=time.monotonic()
            if kind=='case_activity':
                self._notify('stage_activity','KI/'+value['case_id'],value['detail']);return
            key='KI' if kind=='progress' else 'KI/'+value['case_id']
            self._notify('stage_progress',key,value['done'],value['total'],value['detail'])
        elif kind=='findings':
            self._ai_findings=value['findings'];self._ai_by_track={}
            for case in self._ai_findings.get('cases',[]):
                for track in case.get('tracks',[]):self._ai_by_track[track['track_id']]=case
            if self.last_scan and self.last_scan['path']==str(self._ai_worker.mix):
                self.last_scan['results']['ai_review']=self._ai_findings;self.save_current_set(quiet=True)

    def show_ai_findings(self):
        from ui_ai_review import show_findings
        show_findings(self)

    def save_current_set(self,quiet=False):
        if not self.last_scan and not self.current_hits:
            if not quiet:self.progress.set('Noch kein Ergebnis zum Speichern vorhanden')
            return None
        current_path=getattr(self,'_scan_path',None) or self.set_path.get().strip()
        scan=self.last_scan if self.last_scan and self.last_scan.get('path')==current_path else {'path':current_path,'results':{'observations':list(self.raw_hits.values())}}
        if getattr(self,'_scan_archive_pending',False):scan={**scan,'report':'','started_at':self._active_scan_started}
        snapshot={**scan,'results':{**scan.get('results',{}),'observations':list(self.raw_hits.values())}}
        try:
            path=SL.save_snapshot(C.DATA/'Set-Bibliothek',snapshot,sorted(self.current_hits.values(),key=lambda t:t.get('time',0)),self.media_url.get(),{'tasks':dict(self.progress_tasks),'states':dict(self.stage_status)})
            if not quiet:self.progress.set('In der Set-Bibliothek gespeichert')
            return path
        except OSError as exc:
            self._notify('log','Set-Bibliothek konnte nicht gespeichert werden: '+str(exc))
            if not quiet:self.progress.set('Speichern fehlgeschlagen · siehe Protokoll')
            return None

    def load_library_entry(self,item):
        if self.running:return False
        if self._ai_worker:self._ai_worker.abort();self._ai_worker=None
        self.save_current_set(quiet=True)
        self.raw_hits.clear();self.current_hits.clear();self.set_path.set('');self.progress_tasks.clear()
        if self.restore_last_scan(item['entry_path']):
            self.media_url.set(item.get('source_url',''));self._set_workspace_empty(False);return True
        self.set_path.set(item.get('file',''));self._scan_path=item.get('file','')
        self._render_hits(item.get('observations') or item.get('tracks',[]))
        self.progress.set('Gespeicherte Titelliste geladen · Audiodatei bei Bedarf neu zuweisen')
        self._set_workspace_empty(False)
        return True

    def show_progress_details(self):
        dialog=tk.Toplevel(self.root);dialog.title('Fortschritt · alle Einzelschritte')
        self.progress_dialog=dialog
        dialog.geometry('800x560');dialog.configure(bg=PANEL);dialog.transient(self.root)
        canvas=tk.Canvas(dialog,bg=PANEL,highlightthickness=0)
        scroll=ttk.Scrollbar(dialog,orient='vertical',command=canvas.yview)
        scroll.pack(side='right',fill='y');canvas.pack(fill='both',expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        body=tk.Frame(canvas,bg=PANEL);window=canvas.create_window(0,0,window=body,anchor='nw')
        body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        rows={}
        def update():
            if not dialog.winfo_exists():return
            for key in list(rows):
                if key not in self.progress_tasks:
                    rows[key][0].master.destroy();del rows[key]
            for key,item in list(self.progress_tasks.items()):
                if key not in rows:
                    row=tk.Frame(body,bg=PANEL,padx=12,pady=7);row.pack(fill='x')
                    title=tk.Label(row,bg=PANEL,fg=FG,anchor='w');title.pack(fill='x')
                    bar=ttk.Progressbar(row,maximum=100,style='Spark.Horizontal.TProgressbar');bar.pack(fill='x',pady=(4,0))
                    rows[key]=(title,bar)
                title,bar=rows[key]
                title.configure(text=f"{item['detail']} · {item['done']}/{item['total']} · {item['percent']:.0f} %")
                bar['value']=item['percent']
            dialog.after(200,update)
        update()

    def show_retry_methods(self):
        dialog=tk.Toplevel(self.root);dialog.title('Einzelne Methoden erneut prüfen')
        self.retry_dialog=dialog
        dialog.geometry('820x550');dialog.configure(bg=PANEL);dialog.transient(self.root)
        tk.Label(dialog,text='Erfolgreiche Treffer bleiben erhalten.',bg=PANEL,fg=FG,
                 font=('Segoe UI',12,'bold')).pack(anchor='w',padx=16,pady=(16,8))
        notice=tk.Label(dialog,bg=PANEL,fg=MUTED,anchor='w');notice.pack(fill='x',padx=16)
        rows={}
        def launch(key):
            if self.running:return
            dialog.destroy()
            if key=='KI':self.start_ai_method(force=True)
            else:self.start_scan(stages={key})
        for key,name in [('A','SCHNELLSCAN'),('B','TIEFENSCAN 1'),('M','TIEFENSCAN 2 · mix-id'),('S','SHAZAM · ShazamIO'),('KI','KI · REMIXES / GRENZFÄLLE / FUNDSTELLEN')]:
            row=tk.Frame(dialog,bg=PANEL,padx=16,pady=10);row.pack(fill='x')
            button=BloodButton(row,'ERNEUT STARTEN',lambda k=key:launch(k),width=160,height=35,font_size=10)
            button.pack(side='right',padx=(12,0))
            tk.Label(row,text=name,bg=PANEL,fg=FG,font=('Segoe UI',11,'bold'),anchor='w').pack(fill='x')
            detail=tk.Label(row,bg=PANEL,fg=MUTED,anchor='w',wraplength=550,justify='left')
            detail.pack(fill='x');rows[key]=(button,detail)
        def update():
            if not dialog.winfo_exists():return
            notice.configure(text='Der laufende Scan muss zuerst beendet oder abgebrochen werden.' if self.running
                             else 'Wähle die Methode. Die übrigen Methoden werden nicht neu gestartet.')
            for key,(button,detail) in rows.items():
                status=self.stage_status.get(key,{'state':'waiting','detail':'Noch nicht ausgeführt'})
                detail.configure(text=status['detail'][:180],fg=BAD if status['state']=='failed' else YELLOW if status['state']=='paused' else MUTED)
                button.configure(state='disabled' if self.running else 'normal')
            dialog.after(250,update)
        update()

    def restore_last_scan(self,report=None):
        """Restore saved evidence so restarting never requires a full rerun."""
        if report is None and self._skip_restore:return False
        if self.running or self.raw_hits or self.set_path.get().strip():return False
        try:
            if report is None:
                files=SL.report_paths(C.OUTPUT)
                if not files:return False
                report=max(files,key=lambda p:p.stat().st_mtime)
            report=Path(report);saved=json.loads(report.read_text(encoding='utf-8'))
            text='' if saved.get('file') else report.with_suffix('.txt').read_text(encoding='utf-8-sig')
            path=Path(saved.get('file') or next(line[7:] for line in text.splitlines() if line.startswith('Datei: ')))
            observed=saved.get('observations')
            if observed is None:
                observed=[]
                for track in saved.get('tracks',[]):
                    if not track.get('evidence'):
                        methods=track.get('methods',[])
                        observed.append({**track,'source':'offline' if track.get('full_path') else 'mix-id' if 'mix-id' in methods else 'ShazamIO',
                                         '_observed_order':len(observed)+1})
                    for ev in track.get('evidence',[]):
                        local=bool(ev.get('path'));methods=ev.get('methods',[])
                        item={'artist':track.get('artist',''),'title':track['title'],'time':ev['time'],
                              'source':'offline' if local else 'mix-id' if 'mix-id' in methods else 'ShazamIO',
                              'first_detection':track.get('first_detection',ev['time']),
                              'last_detection':track.get('last_detection',ev['time']),
                              'url':ev.get('url',''),'_observed_order':ev.get('order',len(observed)+1)}
                        if local:item.update(full_path=ev['path'],methods=methods)
                        observed.append(item)
            observed=observed or []
            self.set_path.set(str(path));self._scan_path=str(path)
            self._render_hits(observed)
            metadata={t.get('track_id'):t for t in saved.get('tracks',[]) if t.get('track_id')}
            for hit in self.current_hits.values():
                for field in ('audio_format','bpm','bpm_tag','bpm_estimated','bpm_suspect'):
                    if field in metadata.get(hit['track_id'],{}):hit[field]=metadata[hit['track_id']][field]
            self._render_hits([])
            results={'offline':[r for r in observed if r.get('source')=='offline'],'weak':[],
                     'mixid':[r for r in observed if r.get('source')=='mix-id'],
                     'shazam':[r for r in observed if r.get('source') in {'shazam','ShazamIO'}],
                     'observations':observed}
            statuses=saved.get('statuses',{});errors=saved.get('errors',[])
            self.last_scan={'path':str(path),'duration':saved.get('duration',0),'results':results,'statuses':statuses,'errors':errors,'report':saved.get('source_report') or str(report.with_suffix('.txt'))}
            self._ai_findings=saved.get('ai_review') or {}
            if not self._ai_findings:
                try:self._ai_findings=json.loads(Path(self.last_scan['report']).with_name(Path(self.last_scan['report']).stem+'_KI_METHODE.json').read_text(encoding='utf-8'))
                except (OSError,ValueError):pass
            self._ai_by_track={t['track_id']:case for case in self._ai_findings.get('cases',[]) for t in case.get('tracks',[])}
            ai_pending=bool(self._ai_findings and not self._ai_findings.get('complete'))
            if self._ai_findings:
                results['ai_review']=self._ai_findings
                self._stage_ui('KI','failed' if ai_pending else 'done','KI-Nachprüfung unvollständig · nur KI erneut prüfen' if ai_pending else 'Gespeicherte KI-Befunde geladen')
                if ai_pending:self.stagebar.percentages['KI']=min(99,100*len(self._ai_findings.get('cases',[]))/max(1,self._ai_findings.get('total_cases',1)))
            else:self._stage_ui('KI','skipped','Noch keine KI-Nachprüfung gespeichert')
            progress=saved.get('progress') or {'tasks':{},'states':{}}
            results['progress']=progress
            self.progress_tasks.update(progress.get('tasks',{}))
            self._resume_pending=set()
            for key,name in [('A','Offline'),('B','Offline'),('M','mix-id'),('S','ShazamIO')]:
                status=str(statuses.get(name,'Nicht ausgeführt'))
                state='failed' if 'fehler' in status.casefold() else 'skipped' if name not in statuses or 'deaktiviert' in status.casefold() else 'done'
                if key in {'M','S'} and any('429' in str(e) and (str(e).startswith('mix-id') if key=='M' else str(e).startswith('Shazam')) for e in errors):state='paused'
                state=progress.get('states',{}).get(key,{}).get('state',state)
                if state in ('paused','retrying','running'):
                    state='waiting';self._resume_pending.add(key)
                elif state=='failed':self._resume_pending.add(key)
                self._stage_ui(key,state,'Voriger Lauf: '+status)
                task=progress.get('tasks',{}).get(key)
                if task:
                    self.stagebar.percentages[key]=task.get('percent',100*task['done']/max(1,task['total']))
                elif key in self._resume_pending:self.stagebar.progress_labels[key]='Unvollständig'
            self.stagebar.redraw()
            for key in ('setup','E'):self._stage_ui(key,'done','Gespeichertes Ergebnis geladen')
            enabled=[v for k,v in self.stagebar.percentages.items() if k not in self.stagebar.skipped]
            self.progressbar.set_progress(sum(enabled)/len(enabled)/100 if self._resume_pending or ai_pending else 1)
            self.start_button.configure(text='SCANNEN')
            self.progress.set('Teilstand geladen · SCANNEN startet offene Methoden automatisch' if self._resume_pending else
                              'KI-Nachprüfung unvollständig · nur KI erneut prüfen' if ai_pending else
                              '100 % · Voriger Lauf mit Fehlern · Erneut prüfen' if errors else '100 % · Letztes Ergebnis geladen')
            return True
        except (OSError,ValueError,KeyError,StopIteration,TypeError):return False

    def _metadata_worker(self):
        while True:
            key,record,source,offset,cfg=self._metadata_jobs.get()
            if self.current_hits.get(key) is not record:
                self._metadata_jobs.task_done()
                continue
            try:
                program="import audio_core as C,json,sys; C.DATA=C.Path(sys.argv[4]); print(json.dumps(C.track_metadata(sys.argv[1],{'ffmpeg_dir':sys.argv[2]},None if sys.argv[3]=='None' else float(sys.argv[3]))))"
                code,output=C.run_cmd([sys.executable,'-c',program,source,cfg.get('ffmpeg_dir',''),str(offset),str(C.DATA)],
                                     C.env_with_ffmpeg(cfg.get('ffmpeg_dir','')),cwd=C.APP)
                if code:raise RuntimeError('Metadatenanalyse fehlgeschlagen')
                metadata=json.loads(output.strip())
            except Exception:
                metadata={'audio_format':Path(source).suffix[1:].upper() if offset is None else '—','bpm':None,'bpm_estimated':False}
            self.events.put(('track_metadata',key,record,metadata))
            self._metadata_jobs.task_done()

    def _running(self,state):
        self.running=state
        self.start_button.configure(state='disabled' if state else 'normal')
        self.index_button.configure(state='disabled' if state else 'normal')
        self.retry_button.configure(state='disabled' if state else 'normal')
        self.stop_button.configure(state='normal' if state else 'disabled')
        if state:
            if not self.stop_button.winfo_manager():
                self.stop_button.pack(side='right',padx=(0,9))
        else:
            self.stop_button.pack_forget()
        if state: self.progressbar.start(16)
        else: self.progressbar.stop()

    def _refresh_readiness(self):
        previous=getattr(self,"_refresh_handle",None)
        if previous is not None:
            try:self.root.after_cancel(previous)
            except tk.TclError:pass
        try:
            ff = C.locate_ffmpeg(self.cfg)
            offline = probe_engine(self.cfg)
            mix = X.mixid_ready({**self.cfg,'mixid_dir':self.mixid_dir.get()})
            importlib.invalidate_caches()
            shazam = importlib.util.find_spec('shazamio') is not None
            checks = {
                'ffmpeg':(bool(ff),'Bereit' if ff else 'Fehlt'),
                'db':(C.DB.is_file(),probe_database()),
                'offline':(offline,'Bereit' if offline else 'Fehlt'),
                'mixid':(mix,'Bereit' if mix else 'Fehlt'),
                'shazam':(shazam,'Bereit' if shazam else 'Fehlt')
            }
            if ff:
                self.cfg['ffmpeg_dir']=ff
            for key,(ready,detail) in checks.items():
                icon,txt=self.statuses[key]
                fix=self.status_actions.get(key)
                disabled=(key=='shazam' and not self.use_shazam.get()) or (key=='mixid' and not self.mixid_enabled.get())
                if disabled:
                    icon.configure(text='–',fg=YELLOW)
                    txt.configure(text='Aus',fg=YELLOW)
                else:
                    icon.configure(text='✓' if ready else '✕',fg=GREEN if ready else BAD)
                    txt.configure(text=detail if ready else 'Fehlt',fg=GREEN if ready else BAD)
                if fix:
                    if not ready and not disabled:
                        txt.grid_remove()
                        fix.grid()
                    else:
                        fix.grid_remove()
                        txt.grid()
        finally:
            self._refresh_handle=self.root.after(2500,self._refresh_readiness)

    def fix_prerequisite(self,key):
        """Actionable red X: one click goes to the actual repair, not an inert label."""
        if self.running:
            messagebox.showinfo('JOHANNA JOY\'S THE ALMIGHTY','Es läuft bereits ein Vorgang.')
            return
        if key=='db':
            # The indexer itself needs the two offline prerequisites.
            if not C.locate_ffmpeg(self.cfg):
                messagebox.showinfo('Musikdatenbank','Für den Datenbankaufbau wird zuerst FFmpeg benötigt.')
                self.fix_prerequisite('ffmpeg')
                return
            if not probe_engine(self.cfg):
                messagebox.showinfo('Musikdatenbank','Für den Datenbankaufbau wird zuerst die Offline-Engine benötigt.')
                self.fix_prerequisite('offline')
                return
            # A library requires the user's actual source collection; we never
            # guess its location, delete it, or replace an existing database.
            if not Path(self.library.get()).is_dir():
                self.pick_library()
            if not Path(self.library.get()).is_dir():
                self.toggle_settings() if not self.settings_open else None
                messagebox.showinfo('Musikdatenbank','Wähle unter Einstellungen deinen Musikordner aus und klicke auf DATENBANK AUFBAUEN.')
                return
            self.start_index()
            return
        comp={'ffmpeg':'ffmpeg','offline':'audfprint','mixid':'mixid','shazam':'libraries'}.get(key)
        if not comp:
            return
        label_name={'ffmpeg':'FFmpeg + FFprobe','offline':'Offline-Engine audfprint',
                    'mixid':'mix-id + Node.js','shazam':'ShazamIO'}[key]
        if not messagebox.askyesno('Voraussetzung einrichten',
               f'{label_name} fehlt.\n\nSoll die Komponente jetzt automatisch in den Programmordner installiert werden?\n\nFür den Download wird Internet benötigt.'):
            return
        self.cancel.clear()
        self._running(True)
        self.progress.set(f'Einrichtung: {label_name} ...')
        self._notify('log',f'Einrichtung gestartet: {label_name}')
        def worker():
            try:
                env=os.environ.copy()
                env['PIP_NO_CACHE_DIR']='1'
                args=[sys.executable,str(C.APP/'components.py'),'--component',comp]
                kwargs={'cwd':str(C.APP),'env':env,'stdout':subprocess.PIPE,
                        'stderr':subprocess.STDOUT,'text':True,'errors':'replace'}
                if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW
                process=subprocess.Popen(args,**kwargs)
                with process.stdout as output:
                    for line in output:
                        self._notify('log',line.rstrip())
                        if self.cancel.is_set():
                            process.terminate()
                            raise RuntimeError('Einrichtung abgebrochen.')
                code=process.wait()
                if code != 0:
                    raise RuntimeError(f'{label_name} konnte nicht eingerichtet werden. Details unter Protokolle/EINRICHTUNG.txt (Code {code}).')
                self.events.put(('done',f'{label_name} eingerichtet. Die Voraussetzungen werden erneut geprüft.'))
            except Exception as exc:
                self.events.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=True).start()

    def install_local_ai(self):
        """Open verified official download; user chooses and installs it."""
        webbrowser.open('https://lmstudio.ai/download?os=windows')
        messagebox.showinfo('Lokale KI einrichten',
            '1. LM Studio für Windows installieren.\n'
            '2. Ein Chat-Modell auswählen, z. B. dein vorhandenes Gemma.\n'
            '3. Modell laden und lokalen Server einschalten (Port 1234).\n'
            '4. Hier auf KI-VERBINDUNG PRÜFEN klicken.\n\n'
            'WICHTIG: Das Modell erkennt keine Musik. Es prüft ausschließlich den Trefferbericht.')

    def install_ollama(self):
        webbrowser.open('https://ollama.com/download/windows')

    def open_local_ai(self):
        path=L.find_lmstudio(self.cfg)
        if not path:
            path=filedialog.askopenfilename(title='LM Studio.exe zuweisen',filetypes=[('LM Studio','*.exe')])
            if not path:return
            self.cfg['lmstudio_path']=path;C.save_config(self.cfg)
        os.startfile(path)

    def configure_local_ai(self):
        existing=getattr(self,'ai_dialog',None)
        if existing and existing.winfo_exists():existing.lift();return
        dialog=tk.Toplevel(self.root);self.ai_dialog=dialog
        dialog.title('Lokale KI · Modell und Verbindung');dialog.configure(bg=PANEL)
        self.root.update_idletasks()
        x=self.root.winfo_rootx()+max(0,(self.root.winfo_width()-720)//2)
        y=self.root.winfo_rooty()+max(0,(self.root.winfo_height()-460)//2)
        dialog.geometry(f'720x460+{x}+{y}');dialog.minsize(640,440);dialog.transient(self.root)
        body=tk.Frame(dialog,bg=PANEL,padx=22,pady=16);body.pack(fill='both',expand=True)
        provider=tk.StringVar(value=self.cfg.get('local_ai_provider','LM Studio'))
        _,initial_base=L.connection(self.cfg)
        base=tk.StringVar(value=initial_base);model=tk.StringVar(value=self.cfg.get('local_ai_model',''))
        path=tk.StringVar(value=L.find_lmstudio(self.cfg) or '')
        status=tk.StringVar(value='Modelle werden gesucht …')
        for caption,var in [('Anbieter',provider),('Lokaler Server',base)]:
            self._label(body,caption,bold=True).pack(anchor='w',pady=(7,3))
            if var is provider:field=ttk.Combobox(body,textvariable=var,values=['LM Studio','Ollama'],state='readonly')
            else:field=self._entry(body,var)
            field.pack(fill='x')
        def provider_changed(*_):
            base.set('http://127.0.0.1:1234' if provider.get()=='LM Studio' else 'http://127.0.0.1:11434')
            model.set('')
        provider.trace_add('write',provider_changed)
        self._label(body,'Chat-Modell (z. B. Gemma)',bold=True).pack(anchor='w',pady=(8,3))
        models=ttk.Combobox(body,textvariable=model);models.pack(fill='x')
        self._label(body,'LM Studio · Programmdatei',bold=True).pack(anchor='w',pady=(8,3))
        row=tk.Frame(body,bg=PANEL);row.pack(fill='x')
        self._entry(row,path).pack(side='left',fill='x',expand=True)
        def assign():
            chosen=filedialog.askopenfilename(parent=dialog,title='LM Studio.exe zuweisen',filetypes=[('Programm','*.exe')])
            if chosen:path.set(chosen)
        self._button(row,'ZUWEISEN',assign,bg=PANEL2,width=11).pack(side='right',padx=(8,0))
        tk.Label(body,textvariable=status,bg=PANEL,fg=FG,wraplength=660,justify='left',anchor='w').pack(fill='x',pady=10)
        def config():
            return {**self.cfg,'local_ai_provider':provider.get(),'local_ai_base_url':L.local_base(base.get().strip()),
                    'local_ai_model':model.get().strip(),'lmstudio_path':path.get().strip()}
        results=queue.Queue()
        def refresh():
            try:cfg=config()
            except ValueError as exc:status.set(str(exc));return
            status.set('Verbindung und Modelle werden geprüft …')
            def worker():
                try:results.put(L.inventory(cfg))
                except Exception as exc:results.put({'info':str(exc),'models':[],'downloaded':[]})
            threading.Thread(target=worker,daemon=True).start()
        def poll():
            if not dialog.winfo_exists():return
            try:
                info=results.get_nowait()
                ids=[m['id'] for m in info['models']]
                models.configure(values=ids or info['downloaded'])
                if not model.get() and info.get('model'):model.set(info['model'])
                status.set(info['info'])
            except queue.Empty:pass
            dialog.after(120,poll)
        def save():
            try:
                cfg=config()
                if cfg['lmstudio_path'] and not Path(cfg['lmstudio_path']).is_file():raise ValueError('Programmdatei nicht gefunden.')
                self.cfg=cfg;C.save_config(cfg)
            except ValueError as exc:status.set(str(exc));return
            dialog.destroy();self.check_local_ai(quiet=True)
        buttons=tk.Frame(body,bg=PANEL);buttons.pack(fill='x',side='bottom')
        self._button(buttons,'MODELLE ERKENNEN',refresh,bg=PANEL2).pack(side='left')
        self._button(buttons,'INSTALLIEREN',self.install_local_ai,bg=PANEL2,width=14).pack(side='left',padx=8)
        self._button(buttons,'SPEICHERN',save,width=13).pack(side='right')
        refresh();poll()

    def start_ai_review(self):
        if self.running:return
        report=Path(self.last_scan['report']) if self.last_scan else None
        if report is None or not report.is_file():
            messagebox.showwarning('KI-Textprüfung','Bitte zuerst ein gespeichertes Ergebnis laden.')
            return
        def job(cfg):
            self._notify('progress','KI','Lokale KI prüft den Textbericht · keine Audioerkennung')
            self._notify('stage_progress','KI',0,1,'KI-Textprüfung läuft')
            output=L.review_report(report,cfg=cfg)
            self._notify('stage_progress','KI',1,1,'KI-Textprüfung gespeichert')
            self._notify('ai_review_done',str(output))
            return 'Lokale KI-Textprüfung gespeichert.\nDie erkannten Tracks bleiben unverändert.\n\n'+str(output)
        self._launch(job)

    def check_local_ai(self,quiet=False):
        cfg=dict(self.cfg)
        def worker():
            try:provider,model,status=L.detect(cfg)
            except Exception as exc:status=str(exc)
            self.events.put(('ai_status',status,quiet))
        threading.Thread(target=worker,daemon=True).start()

    def pick_set(self):
        filename=filedialog.askopenfilename(title='Dein fertiges DJ-Set',filetypes=[
            ('DJ-Sets und Video','*.mp3 *.wav *.flac *.aiff *.aif *.m4a *.ogg *.opus *.mp4 *.mkv *.mov *.webm *.m4v'),('Alle Dateien','*.*')])
        if filename:
            self.set_path.set(filename)
            self._refresh_readiness()

    def pick_library(self):
        folder=filedialog.askdirectory(title='Eigene Musikbibliothek auswählen',
                                       initialdir=self.library.get() if Path(self.library.get()).is_dir() else str(Path.home()))
        if folder:self.library.set(folder)

    def pick_ffmpeg(self):
        file=filedialog.askopenfilename(title='ffmpeg.exe auswählen',filetypes=[('FFmpeg','ffmpeg.exe'),('EXE','*.exe')])
        if file:
            self.cfg['ffmpeg_dir']=str(Path(file).parent)
            C.save_config(self.cfg)
            self._notify('log','FFmpeg: '+str(Path(file).parent))
            self._refresh_readiness()

    def pick_audfprint(self):
        folder=filedialog.askdirectory(title='Ordner mit audfprint.py auswählen')
        if folder:
            self.cfg['audfprint_source']=folder
            C.save_config(self.cfg)
            self._refresh_readiness()

    def pick_mixid(self):
        folder=filedialog.askdirectory(title='mix-id-Ordner wählen (cli.mjs + lib/audio.mjs)')
        if folder:
            self.mixid_dir.set(folder)
            self.cfg['mixid_dir']=folder
            C.save_config(self.cfg)
            self._refresh_readiness()

    def import_db(self):
        filename=filedialog.askopenfilename(title='Vorhandene audfprint-Datenbank (.pklz)',
                                             filetypes=[('audfprint Datenbank','*.pklz')])
        if not filename:return
        if C.DB.exists() and not messagebox.askyesno('Import','Vorhandene JOHANNA JOY\'S THE ALMIGHTY-Datenbank ersetzen?'):
            return
        C.DATA.mkdir(parents=True,exist_ok=True)
        shutil.copy2(filename,C.DB)
        (C.DATA/'bibliothek.json').write_text(json.dumps({'source':'importiert','created':C.stamp()}),encoding='utf-8')
        self._notify('log','Datenbank importiert: '+filename)
        self._refresh_readiness()

    def _settings_cfg(self):
        try: limit=int(self.max_shazam.get())
        except ValueError: raise RuntimeError('Shazam-Limit muss eine Zahl sein.')
        base={k:v for k,v in self.cfg.items()
              if k not in {'trackid','trackid_exe','trackid_try_sandbox',
                           'trackid_backend','max_trackid'}}
        cfg={**base,'library':self.library.get().strip(),
             'local_ai_method':self.use_ai_method.get(),
             'shazam':self.use_shazam.get(),
             'tempo_pitch':self.pitch.get(),
             'exhaustive_tempo':self.exhaustive_tempo.get(),
             'max_shazam':max(0,min(limit,250)),
             'mixid':self.mixid_enabled.get(),
             'mixid_dir':self.mixid_dir.get(),
             'local_ai_review':self.use_local_ai.get()}
        ff=C.locate_ffmpeg(cfg)
        if not ff:raise RuntimeError('FFmpeg fehlt. Bitte unter Einstellungen auswählen.')
        cfg['ffmpeg_dir']=ff
        self.cfg=cfg
        C.save_config(cfg)
        return cfg

    def _launch(self,job):
        if self.running:return
        self._completion_context=None
        try:cfg=self._settings_cfg()
        except Exception as exc:
            messagebox.showerror('JOHANNA JOY\'S THE ALMIGHTY',str(exc))
            return
        self.cancel.clear()
        self._running(True)
        def worker():
            try:
                msg=job(cfg)
                self.events.put(('done',msg))
            except Exception as exc:
                C.LOGS.mkdir(parents=True,exist_ok=True)
                (C.LOGS/'letzter_fehler.txt').write_text(traceback.format_exc(),encoding='utf-8')
                self.events.put(('error',f'{exc}\n\nDetails: {C.LOGS/"letzter_fehler.txt"}'))
        threading.Thread(target=worker,daemon=True).start()

    def start_index(self):
        if C.DB.exists() and not messagebox.askyesno('Datenbank','Vorhandene Datenbank wirklich neu erstellen?'):
            return
        def job(cfg):
            self._notify('progress','setup','Musikbibliothek wird gelesen …')
            self._notify('log','Datenbank wird indexiert …')
            C.build_database(cfg,lambda msg:self._notify('log',msg),self.cancel,
                             progress=lambda value:self._notify('index_progress',value))
            issues=json.loads((C.DATA/'nicht_lesbar.json').read_text(encoding='utf-8'))
            if issues:return f'Datenbank fertig. {len(issues)} Dateien konnten nicht gelesen werden.\nListe: {C.DATA / "nicht_lesbar.json"}'
            return 'Datenbank fertig! Jetzt DJ-Set auswählen und SCANNEN klicken.'
        self._launch(job)

    def start_download(self):
        link=self.media_url.get().strip()
        if not media_provider(link):
            messagebox.showwarning('Link','Bitte einen gültigen YouTube-, SoundCloud- oder Mixcloud-Link eingeben.')
            return
        def job(cfg):
            self._notify('stage','setup','running','Online-Audio wird geladen')
            file=download_online(link,cfg,self.cancel,lambda msg:self._notify('log',msg))
            self.events.put(('set_path',str(file)))
            self._notify('stage','setup','done','Online-Audio geladen')
            return f'Datei gespeichert: {file}\nJetzt SCANNEN starten.'
        self._launch(job)

    def start_scan(self,stages=None):
        if self.running:return
        path=Path(self.set_path.get().strip())
        if not path.is_file():
            self.pick_set()
            path=Path(self.set_path.get().strip())
        if not path.is_file():return
        self._set_workspace_empty(False)
        if stages is None and self._resume_pending and self.last_scan and self.last_scan['path']==str(path):
            stages=set(self._resume_pending)
        selected=set(stages if stages is not None else ('A','B','M','S'))
        if selected & {'A','B'} and not C.DB.is_file():
            messagebox.showwarning('Datenbank fehlt', 'Bitte erst unter Einstellungen eine lokale Musikdatenbank erstellen oder importieren.')
            self.toggle_settings() if not self.settings_open else None
            return
        previous=self.last_scan if stages is not None and self.last_scan and self.last_scan['path']==str(path) else None
        if previous is None and stages is not None and getattr(self,'_scan_path',None)==str(path) and self.raw_hits:
            observed=list(self.raw_hits.values())
            previous={'path':str(path),'results':{'offline':[h for h in observed if h.get('source')=='offline'],
                'weak':[],'mixid':[h for h in observed if h.get('source')=='mix-id'],
                'shazam':[h for h in observed if h.get('source') in {'shazam','ShazamIO'}],
                'observations':observed},'statuses':{},'errors':[]}
        self.save_current_set(quiet=True)
        if self._ai_worker:self._ai_worker.abort();self._ai_worker=None
        self._ai_findings={};self._ai_by_track={}
        self._scan_path=str(path)
        self._active_scan_started=dt.datetime.now().isoformat(timespec='microseconds');self._scan_archive_pending=True
        if previous is None:
            self.last_scan=None
            self.current_hits.clear();self.raw_hits.clear();self._received_order=0;self.progress_tasks.clear()
            for item in self.result_table.get_children():self.result_table.delete(item)
            for key in self.stages:self._stage_ui(key,'waiting','Wartet')
            if stages is not None:
                for key in {'A','B','M','S'}-selected:self._stage_ui(key,'skipped','Nicht für diesen Lauf gewählt')
        else:
            for key in list(self.progress_tasks):
                if key.split('/')[0] in selected | {'setup','E','KI'}:del self.progress_tasks[key]
            for key in selected | {'setup','E'}:self._stage_ui(key,'waiting','Erneut prüfen')
        def job(cfg):
            self._resume_pending=set()
            self._notify('stage_progress','setup',0,2,'Datei und Offline-Engine prüfen')
            if cfg.get('local_ai_review') and stages is None:self._notify('stage_progress','KI',0,1,'Lokale KI · wartet auf Bericht')
            if selected & {'A','B'}:C.install_engine(cfg,lambda msg:self._notify('log',msg))
            self._notify('stage_progress','setup',1,2,'Set-Länge lesen')
            env=C.env_with_ffmpeg(cfg['ffmpeg_dir'])
            self._notify('stage','setup','running','Set-Länge und Dateien prüfen')
            duration=C.get_duration(path,env)
            self._notify('log',f'{path.name} | Dauer: {C.hhmmss(duration)}')
            self._notify('stage','setup','done','Datei bereit · '+C.hhmmss(duration))
            self._notify('stage_progress','setup',2,2,'Datei bereit · '+C.hhmmss(duration))
            audit=None;offline_pending=set(selected & {'A','B'})
            if cfg.get('local_ai_method',False):
                audit=self._start_audit(path,cfg,duration,previous['results']['observations'] if previous else (),self.cancel,bool(offline_pending))
            else:self._notify('stage','KI','skipped','KI-Methode deaktiviert')
            def scan_notify(kind,*args):
                if audit:
                    if kind=='hits':audit.offer(args[0])
                    elif kind=='stage' and args[0] in offline_pending and args[1] in ('done','failed','skipped'):
                        offline_pending.discard(args[0])
                        if not offline_pending:audit.audio_ready.set();audit.changed.set()
                self._notify(kind,*args)
            result,engine_status,errors=J.parallel_scan(path,cfg,duration,scan_notify,self.cancel,split_audio,do_match,
                stages=selected,seed_observations=previous['results']['observations'] if previous else ())
            if previous:
                current=result;result={**previous['results'],'observations':current['observations']}
                old_progress=previous['results'].get('progress',{})
                new_progress=current.get('progress',{})
                result['progress']={group:{**old_progress.get(group,{}),**new_progress.get(group,{})} for group in ('tasks','states')}
                for keys,stage in [(('offline','weak'),'A'),(('offline','weak'),'B'),(('mixid',),'M'),(('shazam',),'S')]:
                    if stage in selected:
                        for key in keys:result[key]=current[key]
                engine_status={**previous['statuses'],**engine_status}
                def affected(error):
                    keys={'S'} if str(error).startswith('Shazam') else {'M'} if str(error).startswith('mix-id') else {'A','B'}
                    return bool(keys & selected)
                errors=[e for e in previous['errors'] if not affected(e)]+errors
            offline,weak,mix_hits,sha=(result[k] for k in ('offline','weak','mixid','shazam'))
            self._notify('stage','E','running','Gemeinsame Tracklist speichern')
            self._notify('stage_progress','E',0,1,'TXT und JSON speichern')
            report,merged=X.merged_report(path,duration,offline,weak,mix_hits,sha,engine_status,errors,
                observations=result['observations'],progress=result.get('progress'))
            self._notify('stage_progress','E',1,1,report.name)
            self._notify('stage','E','done',report.name)
            if audit:audit.offer(result['observations']);audit.offer_weak(result['weak']);audit.finish(report)
            if cfg.get('local_ai_review') and not audit and stages is None:
                self._notify('stage_progress','KI',0,1,'Lokale KI prüft den Bericht')
                self._notify('log','Lokale KI-Nachprüfung des TXT-Berichts (keine Musikerkennung) ...')
                try:
                    ai_out=L.review_report(report,cfg=cfg)
                    self._notify('log','KI-Hinweise separat gespeichert: '+str(ai_out))
                except Exception as exc:
                    self._notify('log','Lokale KI optional übersprungen: '+str(exc))
                self._notify('stage_progress','KI',1,1,'Lokale KI-Prüfung abgeschlossen')
            self._notify('scan_finished',{'path':str(path),'duration':duration,'results':result,
                'statuses':engine_status,'errors':errors,'report':str(report)})
            return (f'Scan abgeschlossen: {len(merged)} nummerierte Tracks.\nOffline: {len(offline)} Kandidaten'
                    f'\nmix-id: {len(mix_hits)} Treffer'
                    f'\nShazamIO: {len(sha)} Beobachtungen\nHinweise / Fehler: {len(errors)}\nTXT: {report}')
        self._launch(job)

    def stop(self):
        self.cancel.set()
        if self._ai_worker:self._ai_worker.abort();self._stage_ui('KI','skipped','KI-Nachprüfung abgebrochen')
        self._notify('log','Abbruch angefordert')

    def reset_set(self):
        """Discard the current workspace; a running job must stop before clearing."""
        self._set_workspace_empty(True)
        if self._ai_worker:self._ai_worker.abort();self._ai_worker=None
        if self.running:
            self._reset_requested=True;self.cancel.set()
            self.reset_button.configure(state='disabled')
            self.progress.set('Laufenden Vorgang beenden · Set wird zurückgesetzt')
            return
        self._clear_current_set()

    def _set_workspace_empty(self,empty):
        self._skip_restore=bool(empty)
        try:
            target=C.DATA/'arbeitsstand.json';temporary=target.with_suffix('.tmp')
            temporary.write_text(json.dumps({'empty':bool(empty)}),encoding='utf-8');temporary.replace(target)
        except OSError as exc:self._notify('log','Arbeitsstand konnte nicht gesichert werden: '+str(exc))

    def _clear_current_set(self):
        self._reset_requested=False;self.cancel.clear()
        self._ai_findings={};self._ai_by_track={}
        self._ai_live_detail='';self._ai_live_started=time.monotonic()
        self.last_scan=None;self._completion_context=None;self._resume_pending.clear()
        self._scan_path=None;self._scan_archive_pending=False;self._active_scan_started=None
        self.raw_hits.clear();self.current_hits.clear();self._hit_rows={};self._received_order=0
        self.progress_tasks.clear();self.stage_status.clear()
        self.set_path.set('');self.media_url.set('');self.ai_review_path=None
        while True:
            try:self.events.get_nowait()
            except queue.Empty:break
        while True:
            try:self._metadata_jobs.get_nowait();self._metadata_jobs.task_done()
            except queue.Empty:break
        for name in ('hit_dialog','progress_dialog','retry_dialog','completion_dialog','log_window','ai_window','rekordbox_window'):
            dialog=getattr(self,name,None)
            if dialog is not None and dialog.winfo_exists():dialog.destroy()
        viewer=getattr(self,'results_window',None)
        if viewer is not None and viewer.window.winfo_exists():viewer.window.destroy()
        for row in self.result_table.get_children():self.result_table.delete(row)
        for key in self.stages:self._stage_ui(key,'waiting','Noch nicht ausgeführt')
        self.progressbar.stop();self.progressbar.set_progress(0);self.overall_percent.set('0 %')
        self.metadata_progress.set_progress(0);self.metadata_caption.set('Format / BPM · 0/0 · 0 %')
        self.stats.set('Noch keine Treffer');self.progress.set('Bereit · neues Set auswählen')
        self.logbox.configure(state='normal');self.logbox.delete('1.0','end');self.logbox.configure(state='disabled')
        self.start_button.configure(text='SCANNEN');self.reset_button.configure(state='normal')

    def _open(self,path):
        path.mkdir(exist_ok=True,parents=True)
        if os.name=='nt':os.startfile(str(path))
        else:messagebox.showinfo('JOHANNA JOY\'S THE ALMIGHTY',str(path))

    def run(self):
        self.root.mainloop()


if __name__=='__main__':
    AppGUI().run()
