"""Offline smoke check through the actual Windows executable and bundled interpreter."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,uuid,shutil
target=Path(sys.argv[1]).resolve();app=Path(__file__).resolve().parent
fixture=target.parent/('portable-check-'+uuid.uuid4().hex);fixture.mkdir()
os.environ['ALMIGHTY_DATA_ROOT']=str(fixture)
checks={}
try:
    import numpy,scipy,docopt,joblib,psutil,shazamio,shazamio_core,tkinterdnd2,yt_dlp,PIL
    checks['native_imports']=True
    assert Path(sys.executable).resolve().parent==app.parent/'runtime'
    assert all('AppData/Local/Programs/Python' not in p.replace('\\','/') for p in sys.path)
    checks['isolated_runtime']=True
    import almighty as S,audio_core as C,engine_external as X
    for name,cmd in [('ffmpeg',[str(app/'tools/ffmpeg/ffmpeg.exe'),'-version']),
                     ('ffprobe',[str(app/'tools/ffmpeg/ffprobe.exe'),'-version']),
                     ('node',[str(app/'tools/node/node.exe'),'--version']),
                     ('audfprint',[sys.executable,str(app/'audfprint_utf8.py'),'--help'])]:
        run=subprocess.run(cmd,capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        assert run.returncode==0,(name,run.stderr.decode(errors='replace')[-250:]);checks[name]=True
    assert X.mixid_ready({});checks['mix_id']=True
    gui=S.AppGUI();gui.root.withdraw();gui.root.update()
    assert gui.result_table.winfo_exists() and len(gui.method_progress)==7
    gui.root.destroy();checks['real_gui']=True
    assert C.DATA.parent==fixture and C.CONFIG_FILE.parent==fixture;checks['isolated_test_data']=True
    result={'ok':True,'checks':checks,'python':sys.version.split()[0]}
except Exception as exc:
    import traceback
    result={'ok':False,'checks':checks,'error':str(exc),'traceback':traceback.format_exc()}
finally:
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    assert fixture.resolve().parent==target.parent;shutil.rmtree(fixture,ignore_errors=True)
if not result['ok']:raise SystemExit(1)
