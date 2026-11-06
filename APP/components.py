#!/usr/bin/env python3
# coding: utf-8
"""JOHANNA JOY\'S THE ALMIGHTY first-start bootstrap. Everything ends up INSIDE JOHANNA JOY\'S THE ALMIGHTY.
No user-selected dependency folders, no system PATH edits, no API keys.
First run requires Internet for upstream program source, FFmpeg and Python wheels.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

APP = Path(__file__).resolve().parent
TOOLS = APP/'tools'
FFMPEG = TOOLS/'ffmpeg'
NODE = TOOLS/'node'
AUD = APP/'engine'/'audfprint'
MIX = APP/'engine'/'mix-id'
RUNTIME = APP.parent/'runtime'
PY = RUNTIME/'python.exe' if os.name == 'nt' else RUNTIME/'bin'/'python'
LOGS = Path(os.environ.get('ALMIGHTY_DATA_ROOT') or APP.parent/'Daten')/'Protokolle'
LOGS.mkdir(parents=True,exist_ok=True)
LOGFILE = LOGS/'EINRICHTUNG.txt'
REQUIRED_AUD = {'audfprint.py','audfprint_analyze.py','audfprint_match.py',
                'audio_read.py','hash_table.py','stft.py'}


def out(message):
    line = str(message)
    print(line, flush=True)
    with LOGFILE.open('a', encoding='utf-8') as f:
        f.write(line + '\n')


def fetch(url: str, output: Path, *, max_mb=450):
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix+'.downloading')
    if temp.exists(): temp.unlink()
    req = urllib.request.Request(url, headers={'User-Agent':'Almighty-Windows/1.14'})
    with urllib.request.urlopen(req, timeout=65) as source, temp.open('wb') as sink:
        total=0
        while block:=source.read(1024*1024):
            total += len(block)
            if total > max_mb*1024*1024:
                raise RuntimeError('Download größer als erwartete Obergrenze: '+url)
            sink.write(block)
    if not zipfile.is_zipfile(temp) and output.suffix.lower()=='.zip':
        raise RuntimeError('Download ist kein gültiges ZIP-Archiv: '+url)
    temp.replace(output)


def zip_member(z: zipfile.ZipFile, endings: list[str]) -> dict[str,str]:
    """Read only named files, never extract arbitrary untrusted paths."""
    result={}
    for info in z.infolist():
        if info.is_dir(): continue
        path=info.filename.replace('\\','/')
        for suffix in endings:
            if path.lower().endswith('/'+suffix.lower()) or path.lower()==suffix.lower():
                result[suffix]=info.filename
    return result


def audfprint():
    out('[1/4] Offline-Musikerkennung (audfprint)')
    if all((AUD/name).is_file() for name in REQUIRED_AUD):
        out('  ✓ Vollständig im JOHANNA JOY\'S THE ALMIGHTY vorhanden')
        return
    # Official upstream source under permissive MIT License.
    url='https://github.com/dpwe/audfprint/archive/refs/heads/master.zip'
    with tempfile.TemporaryDirectory(prefix='almighty_aud_') as t:
        file=Path(t)/'audfprint.zip'
        out('  Lade Original-Engine automatisch ins Programmpaket ...')
        fetch(url,file,max_mb=15)
        with zipfile.ZipFile(file) as z:
            members={}
            for member in z.namelist():
                parts=Path(member).parts
                if len(parts)==2 and parts[0].startswith('audfprint-') and (
                    member.endswith('.py') or parts[-1].upper()=='LICENSE'):
                    members[parts[-1]]=member
            missing=REQUIRED_AUD-set(members)
            if missing:
                raise RuntimeError('audfprint ZIP unvollständig: '+', '.join(sorted(missing)))
            AUD.mkdir(parents=True,exist_ok=True)
            for name, member in members.items():
                (AUD/name).write_bytes(z.read(member))
    out(f'  ✓ {len(members)} Originaldateien in {AUD}')


def ffmpeg():
    out('[2/4] FFmpeg und FFprobe')
    if all((FFMPEG/(name+'.exe')).is_file() for name in ('ffmpeg','ffprobe')):
        out('  ✓ Beide Programme sind im JOHANNA JOY\'S THE ALMIGHTY vorhanden')
        return
    # Copy from the existing installed executables without asking the user to locate a folder.
    # This is an optional acceleration; a fresh download works without prior installation.
    candidates=[]
    for name in ('ffmpeg.exe','ffprobe.exe'):
        p=shutil.which(name)
        if p: candidates.append(Path(p).parent)
    music=Path.home()/'Music'
    if music.is_dir():
        for directory in music.glob('ffmpeg*'):
            candidates.extend(p.parent for p in directory.glob('**/ffmpeg.exe'))
    for directory in candidates:
        if (directory/'ffmpeg.exe').is_file() and (directory/'ffprobe.exe').is_file():
            FFMPEG.mkdir(parents=True,exist_ok=True)
            for filename in ('ffmpeg.exe','ffprobe.exe'):
                shutil.copy2(directory/filename, FFMPEG/filename)
            out('  ✓ Vorhandenes FFmpeg automatisch in den JOHANNA JOY\'S THE ALMIGHTY übernommen')
            return
    out('  Lade FFmpeg (offizielle Windows-Builds) automatisch ...')
    with tempfile.TemporaryDirectory(prefix='almighty_ffmpeg_') as temp:
        archive=Path(temp)/'ffmpeg.zip'
        fetch('https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip', archive, max_mb=400)
        with zipfile.ZipFile(archive) as z:
            members=zip_member(z, ['ffmpeg.exe','ffprobe.exe'])
            if len(members)!=2:
                raise RuntimeError('FFmpeg ZIP enthält nicht ffmpeg.exe und ffprobe.exe')
            FFMPEG.mkdir(parents=True,exist_ok=True)
            for name,member in members.items():
                (FFMPEG/name).write_bytes(z.read(member))
    out('  ✓ FFmpeg / FFprobe im Programmordner installiert')


def node():
    out('[3/4] Node.js und mix-id (Original)')
    NODE.mkdir(parents=True,exist_ok=True)
    local=NODE/'node.exe'
    npm=None
    # Keep a local copy of the runtime; use existing npm only during setup if available.
    if not local.is_file():
        installed_node=shutil.which('node')
        installed_npm=shutil.which('npm')
        if installed_node and installed_npm:
            original_npm_cli=Path(installed_node).parent/'node_modules'/'npm'/'bin'/'npm-cli.js'
            if original_npm_cli.is_file():
                shutil.copy2(installed_node, local)
                shutil.copytree(original_npm_cli.parent.parent, NODE/'node_modules'/'npm',dirs_exist_ok=True)
                npm=str(NODE/'node_modules'/'npm'/'bin'/'npm-cli.js')
                out('  ✓ Vorhandenes Node.js + npm automatisch ins JOHANNA JOY\'S THE ALMIGHTY-Verzeichnis kopiert')
    if not local.is_file():
        out('  Lade portable Node.js LTS Version automatisch ...')
        request=urllib.request.Request('https://nodejs.org/dist/index.json',headers={'User-Agent':'Almighty/1.14'})
        with urllib.request.urlopen(request,timeout=45) as r:
            items=json.loads(r.read(3*1024*1024).decode('utf-8'))
        entry=next((v for v in items if v.get('lts') and 'win-x64-zip' in v.get('files',[])),None)
        if not entry: raise RuntimeError('Keine Windows-x64 LTS-Version bei nodejs.org gefunden.')
        version=entry['version']
        with tempfile.TemporaryDirectory(prefix='almighty_node_') as temp:
            archive=Path(temp)/'node.zip'
            fetch(f'https://nodejs.org/dist/{version}/node-{version}-win-x64.zip',archive,max_mb=120)
            with zipfile.ZipFile(archive) as z:
                prefix=f'node-{version}-win-x64/'
                for info in z.infolist():
                    if info.is_dir() or not info.filename.startswith(prefix):continue
                    rel=Path(info.filename[len(prefix):])
                    if not rel.parts or '..' in rel.parts:continue
                    target=NODE/rel
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(z.read(info.filename))
        npm=str(NODE/'npm.cmd')
    if npm is None:
        npm=str(NODE/'node_modules'/'npm'/'bin'/'npm-cli.js')
    if not Path(npm).is_file():
        raise RuntimeError('Node.js ist vorhanden, aber npm-cli.js fehlt.')
    if not local.is_file(): raise RuntimeError('Node.exe fehlt nach der Einrichtung.')
    if not (MIX/'cli.mjs').is_file() or not (MIX/'lib'/'audio.mjs').is_file():
        out('  Lade mix-id Originalprojekt automatisch ...')
        with tempfile.TemporaryDirectory(prefix='almighty_mix_') as temp:
            archive=Path(temp)/'mixid.zip'
            fetch('https://github.com/skip5this/mix-id/archive/refs/heads/main.zip',archive,max_mb=20)
            with zipfile.ZipFile(archive) as z:
                for info in z.infolist():
                    if info.is_dir(): continue
                    parts=Path(info.filename).parts
                    if len(parts)<2 or not parts[0].startswith('mix-id-') or '..' in parts:continue
                    rel=Path(*parts[1:])
                    if not (len(rel.parts)==1 and rel.name in {'cli.mjs','package.json','package-lock.json','README.md','LICENSE'}
                            or rel.parts[0]=='lib'):
                        continue
                    dest=MIX/rel
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(z.read(info.filename))
        if not (MIX/'cli.mjs').is_file(): raise RuntimeError('mix-id ZIP enthält cli.mjs nicht.')
    # Windows compatibility patch from the original testing; never edit upstream files elsewhere.
    path=MIX/'lib'/'audio.mjs'
    text=path.read_text(encoding='utf-8')
    fixed=text.replace('`which ${cmd}`','`where.exe ${cmd}`').replace('2>/dev/null','2>nul')
    if fixed!=text:path.write_text(fixed,encoding='utf-8')
    if not (MIX/'node_modules'/'shazam-api').is_dir():
        if not npm: raise RuntimeError('npm fehlt. Die lokale Node-Installation ist unvollständig.')
        out('  Installiere mix-id-Abhängigkeit automatisch und lokal ...')
        env=os.environ.copy()
        env['PATH']=str(NODE)+os.pathsep+str(FFMPEG)+os.pathsep+env.get('PATH','')
        cache=APP/'Cache'/'npm'
        cache.mkdir(parents=True,exist_ok=True)
        cmd=[str(local),str(npm),'install','--omit=dev','--ignore-scripts',
             '--no-audit','--no-fund','--cache',str(cache)]
        done=subprocess.run(cmd,cwd=MIX,env=env,check=False)
        if done.returncode or not (MIX/'node_modules'/'shazam-api').is_dir():
            raise RuntimeError('npm install für mix-id ist fehlgeschlagen.')
    out('  ✓ mix-id + Node + npm-Pakete im JOHANNA JOY\'S THE ALMIGHTY vorhanden')


def stable_python(path):
    """Use the tested final Python 3.12 runtime, never a candidate/preview build."""
    try:
        probe=subprocess.run([str(path),'-I','-c',
            'import json,sys;print(json.dumps([sys.version_info.major,sys.version_info.minor,sys.version_info.releaselevel]))'],
            capture_output=True,text=True,timeout=10)
        return probe.returncode==0 and json.loads(probe.stdout)==[3,12,'final']
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return False


def find_stable_python():
    candidates=[Path(sys.executable),APP/'tools/python312/python.exe']
    if os.name=='nt':
        local=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))
        candidates.append(local/'Programs/Python/Python312/python.exe')
        if os.environ.get('ProgramFiles'):
            candidates.append(Path(os.environ['ProgramFiles'])/'Python312/python.exe')
        launcher=shutil.which('py')
        if launcher:
            try:
                p=subprocess.run([launcher,'-3.12','-c','import sys;print(sys.executable)'],
                                 capture_output=True,text=True,timeout=10)
                if p.returncode==0:candidates.append(Path(p.stdout.strip()))
            except (OSError,subprocess.TimeoutExpired):pass
    else:
        located=shutil.which('python3.12')
        if located:candidates.append(Path(located))
    for candidate in dict.fromkeys(candidates):
        if candidate.is_file() and stable_python(candidate):return candidate
    raise RuntimeError('Für den stabilen Programmbetrieb wird Python 3.12 benötigt. '
                       'Offizielle Windows-Installation: https://www.python.org/downloads/release/python-31210/ '
                       'Danach das Programm erneut starten. Vorhandene Musikdaten bleiben erhalten.')


def libraries():
    out('[4/4] Python-Bibliotheken, lokal im Programmordner')
    if not PY.is_file():raise RuntimeError('Die eigene Python-Laufzeit fehlt. Bitte das vollständige Programmpaket neu entpacken.')
    if not stable_python(PY):
        raise RuntimeError('Die Python-Umgebung ist keine finale Python-3.12-Version. '
                           'Die bisherige Umgebung und Nutzerdaten wurden nicht verändert.')
    # Skip pip entirely if the prior fully working environment already has packages.
    cmd=[str(PY),'-c','import numpy, scipy, docopt, joblib, psutil, shazamio, tkinterdnd2, yt_dlp, PIL']
    if subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
        out('  ✓ Python-Abhängigkeiten bereits installiert')
        return
    env=os.environ.copy()
    env['PIP_NO_CACHE_DIR']='1'
    env['PIP_DISABLE_PIP_VERSION_CHECK']='1'
    out('  Installiere fehlende Python-Pakete ohne defekten pip-Cache ...')
    result=subprocess.run([str(PY),'-m','pip','install','--no-cache-dir','--retries','3',
                           '-r',str(APP/'requirements.txt')],env=env)
    if result.returncode:
        raise RuntimeError('Python-Paketinstallation fehlgeschlagen (siehe Ausgabe).')
    if subprocess.run(cmd).returncode:
        raise RuntimeError('Python-Pakete nicht vollständig importierbar.')
    out('  ✓ Python-Umgebung vollständig eingerichtet')


def verify():
    checks={
        'audfprint':all((AUD/n).is_file() for n in REQUIRED_AUD),
        'ffmpeg':(FFMPEG/'ffmpeg.exe').is_file() and (FFMPEG/'ffprobe.exe').is_file(),
        'Node':(NODE/'node.exe').is_file(),
        'mix-id':(MIX/'cli.mjs').is_file() and (MIX/'node_modules'/'shazam-api').is_dir(),
        'Python':PY.is_file(),
    }
    out('\n'+'-'*52)
    for name,okay in checks.items():out(('OK  ' if okay else 'FEHLT  ')+name)
    out('-'*52)
    if not all(checks.values()):raise RuntimeError('Ein oder mehrere Programmbausteine fehlen noch.')
    return True


def main():
    out('=== JOHANNA JOY\'S THE ALMIGHTY 1.14 | VOLLAUTOMATISCHE EINRICHTUNG ===')
    out('Alle Programmbestandteile werden ausschließlich in JOHANNA JOY\'S THE ALMIGHTY gespeichert.')
    out('Beim ersten Start wird Internet benötigt. Spätere Offline-Scans laufen lokal.\n')
    audfprint()
    ffmpeg()
    node()
    libraries()
    verify()
    out('FERTIG. Ab jetzt bitte nur die Programm-EXE verwenden.')

if __name__=='__main__':
    try:
        if len(sys.argv)==3 and sys.argv[1]=='--component':
            component=sys.argv[2]
            actions={'audfprint':audfprint,'ffmpeg':ffmpeg,'mixid':node,
                     'libraries':libraries}
            if component not in actions:
                raise ValueError('Unbekannter Baustein: '+component)
            out('JOHANNA JOY\'S THE ALMIGHTY | Selbstreparatur: '+component)
            actions[component]()
            out('Baustein eingerichtet: '+component)
        else:
            main()
    except Exception as exc:
        out(f'\nFEHLER: {type(exc).__name__}: {exc}')
        out(f'Details/Protokoll: {LOGFILE}')
        sys.exit(1)
