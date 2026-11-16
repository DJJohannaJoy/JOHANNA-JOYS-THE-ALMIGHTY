from pathlib import Path
import shutil,sys,uuid,threading
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import almighty as S,scan_input as I,audio_core as C
folder=Path(__file__).resolve().parent/('ui-fixture-one-click-'+uuid.uuid4().hex);folder.mkdir()
try:
    local=folder/'local.wav';downloaded=folder/'download.mp3'
    local.write_bytes(b'fixture');downloaded.write_bytes(b'fixture')
    link='https://www.youtube.com/watch?v=fixture'
    assert I.resolve(str(local),link,'file',{},S.media_provider)==(local,'')
    assert I.resolve(str(folder/'missing'),link,'file',{},S.media_provider)==(None,''), 'Missing selected file silently fell back to an old link'
    assert I.resolve(str(local),link,'link',{},S.media_provider)==(None,link)
    assert I.resolve('',link,'link',{link:str(downloaded)},S.media_provider)==(downloaded,link)
    assert I.resolve('',link,'link',{link:str(folder/'missing')},S.media_provider)==(None,link)
    assert I.download_progress('ALMIGHTY_DOWNLOAD:50:100:NA')[1:3]==(50,100)
    assert '≈' in I.download_progress('ALMIGHTY_DOWNLOAD:50:NA:100')[3]
    assert I.download_progress('ALMIGHTY_DOWNLOAD:5000:NA:NA')[1:3]==(0,0)
    assert I.download_progress('ALMIGHTY_DOWNLOAD:nan:inf:NA')[1:3]==(0,0)
    assert I.download_progress('ALMIGHTY_PROCESS:finished')[1:3]==(1,1)
    assert I.download_progress('unrelated log') is None
    with patch.object(C,'DATA',folder/'data'),patch.object(C,'USER_ROOT',folder/'data'),patch.object(C,'OUTPUT',folder/'results'),patch.object(C,'LOGS',folder/'logs'),patch.object(C,'CONFIG_FILE',folder/'settings.json'),patch.object(C,'DB',local),patch.object(S.AppGUI,'check_local_ai'):
        app=S.AppGUI();jobs=[];order=[]
        app._launch=jobs.append
        cfg={**app.cfg,'ffmpeg_dir':'','local_ai_method':False,'local_ai_review':False}
        def fetch(url,settings,cancel,log,progress=None):
            order.append('download');assert url==link
            progress('setup/download',50,100,'Download · 50 %')
            progress('setup/convert',1,1,'Audio-Verarbeitung abgeschlossen')
            return downloaded
        def scan(path,settings,duration,notify,cancel,*args,**kwargs):
            assert path in (local,downloaded);order.append('scan')
            for stage in ('A','B','M','S'):notify('stage',stage,'running','scan')
            for stage in ('A','B','M','S'):notify('stage',stage,'done','done')
            return {'offline':[],'weak':[],'mixid':[],'shazam':[],'observations':[],'progress':{}},{},[]
        try:
            with patch.object(app.root,'clipboard_get',return_value=link):app.paste_link()
            assert not jobs and app.media_url.get()==link,'Pasting started a separate download'
            with patch.object(S,'download_online',side_effect=fetch),patch.object(C,'get_duration',return_value=120),patch.object(C,'install_engine'),patch.object(S.J,'parallel_scan',side_effect=scan),patch.object(S.messagebox,'showinfo'):
                app.start_scan();assert len(jobs)==1
                jobs.pop()(cfg);app._events()
                assert order==['download','scan'] and app.set_path.get()==str(downloaded)
                assert app._download_cache[link]==str(downloaded)
                assert app.progress_tasks['setup']['percent']==100
                assert app.progress_tasks['setup/download']['percent']==50
                assert app.phase_label.cget('text')=='3 · PRÜFEN / BEARBEITEN'
                app.start_scan(stages={'S'});jobs.pop()(cfg);app._events()
                assert order==['download','scan','scan'],'Retry downloaded an already loaded set'
                app.set_path.set(str(local));app.start_scan();jobs.pop()(cfg);app._events()
                assert order==['download','scan','scan','scan'],'Explicit file selection did not override old link'
            app.media_url.set(link+'2')
            with patch.object(S,'download_online',side_effect=RuntimeError('download failed')),patch.object(S.J,'parallel_scan') as scanner:
                app.start_scan()
                try:jobs.pop()(cfg)
                except RuntimeError:pass
                else:raise AssertionError('Download failure ignored')
                scanner.assert_not_called();app._events()
                assert app.stage_status['setup']['state']=='failed'
            app.media_url.set('invalid')
            with patch.object(S.messagebox,'showwarning') as warning:app.start_scan();warning.assert_called_once()
            assert not jobs
            app._running(True);app.root.update()
            assert app.file_button.disabled and app.link_button.disabled
            app._running(False)
            assert not app.file_button.disabled
        finally:app.root.destroy()
    # Verify the actual downloader argument list and genuine log-to-progress bridge.
    updates=[]
    def command(args,env,**kw):
        assert '--progress-template' in args and '--no-playlist' in args and '--no-progress' not in args
        kw['log']('ALMIGHTY_DOWNLOAD:40:100:NA');kw['log']('ALMIGHTY_PROCESS:finished')
        target=Path(args[args.index('--output')+1]).parent/'fixture.mp3';target.write_bytes(b'fixture')
        return 0,''
    with patch.object(C,'USER_ROOT',folder/'downloader'),patch.object(C,'run_cmd',side_effect=command):
        assert S.download_online(link,{'ffmpeg_dir':''},threading.Event(),lambda message:None,lambda *update:updates.append(update)).is_file()
    assert updates[0][1:3]==(40,100) and updates[1][1:3]==(1,1)
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent;shutil.rmtree(folder)
print('ONE-CLICK WORKFLOW OK: paste performs no download; Scan downloads then recognizes automatically; real download/conversion progress; cached isolated retry; file selection, errors and UI phases preserved.')
