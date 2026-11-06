"""Build the complete relocatable Windows application; never include personal data."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys
BRAND="JOHANNA JOY'S THE ALMIGHTY";VERSION='1.14.1'
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--components',type=Path,required=True)
p.add_argument('--output',type=Path,default=root/'outputs'/BRAND)
p.add_argument('--reuse-runtime',type=Path)
a=p.parse_args();out=a.output.resolve()
assert os.name=='nt' and sys.version_info[:2]==(3,12) and sys.version_info.releaselevel=='final'
if out.exists():raise SystemExit('Choose a new output folder. Existing installations are never overwritten.')
for name in ('engine/audfprint/audfprint.py','engine/mix-id/cli.mjs','tools/node/node.exe','tools/ffmpeg/ffmpeg.exe','tools/ffmpeg/ffprobe.exe'):
    assert (a.components/name).is_file(),name
out.mkdir(parents=True);app=out/'APP';app.mkdir();runtime=out/'runtime'
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','tests','test','*.whl')
for source in (root/'APP').iterdir():
    if source.suffix in ('.py','.mjs') or source.name=='requirements.txt':shutil.copy2(source,app/source.name)
shutil.copytree(root/'APP/assets',app/'assets',ignore=ignore)
if a.reuse_runtime:
    assert (a.reuse_runtime/'python.exe').is_file()
    shutil.copytree(a.reuse_runtime,runtime,ignore=ignore)
else:
    runtime.mkdir();base=Path(sys.base_prefix)
    for name in ('python.exe','pythonw.exe','python3.dll','python312.dll','vcruntime140.dll','vcruntime140_1.dll','LICENSE.txt'):shutil.copy2(base/name,runtime/name)
    for name in ('DLLs','tcl'):shutil.copytree(base/name,runtime/name,ignore=ignore)
    shutil.copytree(base/'Lib',runtime/'Lib',ignore=shutil.ignore_patterns('__pycache__','*.pyc','site-packages','test','idlelib','turtledemo','ensurepip'))
    shutil.copytree(Path(sys.prefix)/'Lib/site-packages',runtime/'Lib/site-packages',ignore=ignore)
(runtime/'python312._pth').write_text('.\nLib\nDLLs\nLib/site-packages\n../APP\nimport site\n',encoding='utf-8')
for name in ('engine','tools'):shutil.copytree(a.components/name,app/name,ignore=ignore)
shutil.copytree(root/'licenses',out/'licenses')
compiler=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
subprocess.run([str(compiler),'/nologo','/target:winexe','/platform:x64','/optimize+','/reference:System.Windows.Forms.dll',
               '/win32icon:'+str(root/'APP/assets/almighty_icon.ico'),'/out:'+str(out/(BRAND+'.exe')),
               str(root/'scripts/AlmightyLauncher.cs')],check=True)
(out/'README.txt').write_text(BRAND+'\nVersion '+VERSION+' · EMBER\n\nDas ZIP vollständig entpacken und die gleichnamige EXE starten.\nAPP, runtime und licenses gehören zum Programm. Eigene Einstellungen, Datenbank, Sets und Ergebnisse liegen ausschließlich unter Daten.\nPython 3.12, die Bibliotheken, FFmpeg, Node und die Erkennungs-Engines sind vollständig enthalten. Eine systemweite Python-Installation ist nicht erforderlich.\nDie optionale lokale KI verwendet ein separat laufendes LM Studio/Ollama mit geladenem Modell.\n\nSpaltenbreiten lassen sich im Tabellenkopf ziehen und bleiben gespeichert. Scannen und Rekordbox-Export stehen im Verhältnis 3:2 nebeneinander.\n',encoding='utf-8-sig')
files=[]
for file in sorted(out.rglob('*')):
    if file.is_file() and '__pycache__' not in file.parts and 'Daten' not in file.relative_to(out).parts:
        files.append({'path':file.relative_to(out).as_posix(),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
(out/'VERSION.json').write_text(json.dumps({'name':BRAND,'version':VERSION,'python':sys.version.split()[0],'files':files},indent=2),encoding='utf-8')
print(json.dumps({'name':BRAND,'version':VERSION,'files':len(files),'megabytes':round(sum(f['bytes'] for f in files)/1048576)},ensure_ascii=True),flush=True)
