"""Build a relocatable Windows GUI application with a private stable Python runtime.

Run using the fully prepared 3.12 environment; --components points at its scanner engines/tools.
No music, user settings, databases, downloaded sets or scan results enter the public package.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,zipfile
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--components',type=Path,required=True)
p.add_argument('--output',type=Path,default=root/'outputs/THE_ALMIGHTY_1_13_EMBER_Windows')
p.add_argument('--node-license',type=Path,required=True);p.add_argument('--ffmpeg-notices',type=Path,required=True)
a=p.parse_args();out=a.output.resolve()
assert os.name=='nt' and sys.version_info[:2]==(3,12) and sys.version_info.releaselevel=='final'
if out.exists():raise SystemExit('Choose a new output folder; existing builds are never overwritten.')
for expected in ('engine/audfprint/audfprint.py','engine/mix-id/cli.mjs','tools/node/node.exe','tools/ffmpeg/ffmpeg.exe','tools/ffmpeg/ffprobe.exe'):
    assert (a.components/expected).is_file(),expected
out.mkdir(parents=True);app=out/'APP';app.mkdir();runtime=out/'runtime';runtime.mkdir()
ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','test','tests','idlelib','turtledemo','ensurepip','*.whl')
for source in (root/'APP').iterdir():
    if source.suffix in ('.py','.mjs','.url') or source.name=='requirements.txt':shutil.copy2(source,app/source.name)
shutil.copytree(root/'APP/assets',app/'assets',ignore=ignore)
base=Path(sys.base_prefix)
for name in ('python.exe','pythonw.exe','python3.dll','python312.dll','vcruntime140.dll','vcruntime140_1.dll','LICENSE.txt'):
    shutil.copy2(base/name,runtime/name)
for name in ('DLLs','tcl'):shutil.copytree(base/name,runtime/name,ignore=ignore)
shutil.copytree(base/'Lib',runtime/'Lib',ignore=shutil.ignore_patterns('__pycache__','*.pyc','site-packages','test','idlelib','turtledemo','ensurepip'))
shutil.copytree(Path(sys.prefix)/'Lib/site-packages',runtime/'Lib/site-packages',ignore=ignore)
(runtime/'python312._pth').write_text('.\nLib\nDLLs\nLib/site-packages\n../APP\nimport site\n',encoding='utf-8')
for name in ('engine','tools'):shutil.copytree(a.components/name,app/name,ignore=ignore)
notices=out/'THIRD_PARTY';notices.mkdir();shutil.copy2(a.node_license,notices/'NODE_LICENSE.txt')
for file in a.ffmpeg_notices.iterdir():
    if file.is_file():shutil.copy2(file,notices/('FFMPEG_'+file.name))
(notices/'README.txt').write_text('Python license: runtime/LICENSE.txt\nPython package notices: runtime/Lib/site-packages/*dist-info/licenses and LICENSE files.\nOffline engine: APP/engine/audfprint/LICENSE\nmix-id and its dependencies: APP/engine/mix-id/LICENSE and node_modules/*/LICENSE*\nNode.js: NODE_LICENSE.txt\nFFmpeg: FFMPEG_LICENSE and FFMPEG_README.txt; FFmpeg is a separate GPL-licensed executable.\n',encoding='utf-8')
compiler=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
subprocess.run([str(compiler),'/nologo','/target:winexe','/platform:x64','/optimize+',
               '/reference:System.Windows.Forms.dll','/win32icon:'+str(root/'APP/assets/almighty_icon.ico'),
               '/out:'+str(out/'THE_ALMIGHTY.exe'),str(root/'scripts/AlmightyLauncher.cs')],check=True)
(out/'START_HIER.txt').write_text('THE ALMIGHTY · Version 1.13 – EMBER\n\nZIP vollständig entpacken. THE_ALMIGHTY.exe doppelklicken.\nAPP und runtime bleiben neben der EXE. Python, FFmpeg und Node sind enthalten.\nEine bestehende Desktop/SET SCANNER-Installation wird für Einstellungen, Datenbank und Ergebnisse automatisch weiterbenutzt.\nOhne bestehende Installation werden Daten im APP-Ordner angelegt.\nLokale KI benötigt weiterhin ein separat laufendes LM Studio oder Ollama mit geladenem Modell. Online-Musikerkennung benötigt Internet.\n\nEnglish: Extract the complete ZIP and open THE_ALMIGHTY.exe. Keep APP and runtime beside it. No separate Python installation is required. Existing Desktop/SET SCANNER user data is reused.\n',encoding='utf-8-sig')
files=[]
for file in sorted(out.rglob('*')):
    if file.is_file():files.append({'path':file.relative_to(out).as_posix(),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
(out/'BUILD_MANIFEST.json').write_text(json.dumps({'version':'1.13','python':sys.version.split()[0],'files':files},indent=2),encoding='utf-8')
print(json.dumps({'build':str(out),'files':len(files),'megabytes':round(sum(f['bytes'] for f in files)/1048576)},ensure_ascii=True),flush=True)
