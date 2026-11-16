"""Independent Google Song Search workers. Credentials stay in personal data.

Fingerprints/network run in a child process. Each clip is cached independently;
no-match, permission errors and transport failures remain distinct.
"""
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path
import json,re,shutil,tempfile,threading,time
import audio_core as C
import online_requests as O

HEADER_NAMES=('x-goog-api-key','x-android-package','x-android-cert','user-agent')
def access_path(cfg):
    return Path(cfg.get('google_headers_file') or C.USER_ROOT/'Google'/'zugang.json')

def read_headers(path):
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
    data={str(k).lower():v for k,v in data.items()}
    if not re.fullmatch(r'AIza[\w-]{35}',str(data.get('x-goog-api-key',''))):raise ValueError('Ungültige Google-Kennung.')
    if data.get('x-android-package')!='com.google.android.googlequicksearchbox':raise ValueError('Google-App-Paket fehlt.')
    if not re.fullmatch(r'[a-fA-F0-9]{40}',str(data.get('x-android-cert',''))):raise ValueError('Google-App-Zertifikat fehlt.')
    return {key:str(data[key]) for key in HEADER_NAMES if data.get(key)}

def import_access(source,target):
    headers=read_headers(source);target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.tmp');temporary.write_text(json.dumps(headers,indent=2),encoding='utf-8');temporary.replace(target)
    return target

def readiness(cfg):
    try:read_headers(access_path(cfg))
    except (OSError,ValueError,TypeError,AttributeError):return False,'Google-Zugang importieren'
    if not (C.APP/'tools/node/node.exe').is_file():return False,'Lokales Node.js fehlt'
    return True,'Google · Zugang eingerichtet (wird beim Scan geprüft)'

def scan(mix,cfg,duration,notify,cancel):
    headers_file=access_path(cfg);read_headers(headers_file)
    env=C.env_with_ffmpeg(cfg['ffmpeg_dir']);ffmpeg=shutil.which('ffmpeg',path=env.get('PATH'))
    node=C.APP/'tools/node/node.exe';helper=Path(cfg.get('_google_helper') or C.APP/'google_probe.mjs')
    if not node.is_file():raise RuntimeError('Google: Lokales Node.js fehlt.')
    # Independent of the Shazam service budget: Google never queues behind MIX-ID.
    gate=O.RequestGate(limit=2,interval=.25)
    points=C.unknown_probe_times(duration,[],max(1,min(150,int(cfg.get('max_google',50)))))
    points=[max(0,min(float(p),max(0,duration-20))) for p in points]
    points=list(dict.fromkeys(points)) or ([0.] if duration>0 else [])
    mutex=threading.RLock();phases={};completed=0;records=[];errors=[];fatal=threading.Event()
    notify('stage','G','running',f'Google · parallel gestartet · {len(points)} Ausschnitte')
    notify('stage_progress','G',0,max(1,len(points)),'Google startet parallel')
    def detail(position,phase,caption):
        with mutex:
            phases[position]=phase
            notify('stage_progress',f'G/probe/{position:09.2f}',phase,3,f'Google · {C.hhmmss(position)} · {caption}')
            notify('stage_progress','G',sum(phases.values())/3,max(1,len(points)),f'Google · {completed}/{len(points)} geprüft · {caption}')
    def probe(position):
        nonlocal completed
        if cancel.is_set() or fatal.is_set():return
        detail(position,0,'Ausschnitt vorbereiten')
        cache=O.probe_cache(C.DATA,mix,position,'Google-20s-v1');cached=O.read_probe(cache);record=None
        try:
            if cached is not None:record=cached.get('record')
            else:
                with tempfile.TemporaryDirectory(prefix='almighty-google-') as folder:
                    clip=Path(folder)/'clip.aac'
                    code,output=C.run_cmd([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',str(position),'-i',str(mix),
                        '-t','20','-vn','-ac','1','-ar','16000','-c:a','aac','-f','adts',str(clip)],env,cancel=cancel,idle_timeout=25)
                    if code:raise RuntimeError('Audioausschnitt konnte nicht vorbereitet werden.')
                    detail(position,1,'Ausschnitt bereit')
                    for attempt in range(2):
                        if cancel.is_set() or fatal.is_set():return
                        gate.acquire(cancel)
                        try:
                            detail(position,2,'Google-Anfrage läuft'+(' · Wiederholung' if attempt else ''))
                            code,output=C.run_cmd([str(node),str(helper),str(headers_file),str(clip)],env,cancel=cancel,idle_timeout=30)
                        finally:gate.release()
                        try:answer=json.loads(output.strip().splitlines()[-1])
                        except (ValueError,IndexError):answer={'status':'error','error':'Google-Prozess beendet','retryable':True}
                        if not code and answer.get('status')=='ok':break
                        if str(answer.get('grpc_status')) in ('7','16'):fatal.set()
                        if not answer.get('retryable') or attempt:raise RuntimeError(answer.get('error','Google-Anfrage fehlgeschlagen'))
                        if cancel.wait(2 if str(answer.get('grpc_status'))!='8' else 10):return
                    else:raise RuntimeError('Google-Anfrage fehlgeschlagen')
                    matches=answer.get('matches',[])
                    if matches:
                        # Keep the service's top candidate. Alternatives are recorded for AI review,
                        # never manufactured as multiple simultaneous detections.
                        top=matches[0];youtube=top.get('youtube_id','')
                        record={**top,'time':position,'source':'Google','confidence':'Google-Online-Stichprobe',
                            'url':'https://www.youtube.com/watch?v='+youtube if youtube else '',
                            'catalog_id':'google:youtube:'+youtube if youtube else '', 'alternatives':matches[1:]}
                    O.save_probe(cache,record)
            with mutex:
                if record:records.append(record);notify('hits',[record])
                completed+=1;detail(position,3,'Treffer' if record else 'geprüft · kein Treffer')
        except Exception as exc:
            if cancel.is_set():return
            with mutex:errors.append('Google '+C.hhmmss(position)+': '+str(exc))
            detail(position,0,'Fehler · '+str(exc)[:100])
    with ThreadPoolExecutor(max_workers=2,thread_name_prefix='Google') as pool:
        # Keep only two probes in flight; permission errors stop promptly.
        todo=iter(points);pending=set()
        def fill():
            while len(pending)<2 and not cancel.is_set() and not fatal.is_set():
                position=next(todo,None)
                if position is None:break
                pending.add(pool.submit(probe,position))
        fill()
        while pending:
            done,_=wait(pending,timeout=.1,return_when=FIRST_COMPLETED)
            for task in done:pending.remove(task);task.result()
            fill()
    if cancel.is_set():raise RuntimeError('Scan wurde abgebrochen.')
    return records,errors,f'{completed}/{len(points)} geprüft · {len(records)} Beobachtungen'
