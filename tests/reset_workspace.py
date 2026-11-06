from pathlib import Path
import sys,uuid,shutil,json
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import almighty as S
folder=Path(__file__).resolve().parent/('reset-fixture-'+uuid.uuid4().hex);folder.mkdir()
try:
    with patch.object(S.C,'DATA',folder/'data'),patch.object(S.C,'OUTPUT',folder/'results'),patch.object(S.C,'LOGS',folder/'logs'),patch.object(S.AppGUI,'check_local_ai'):
        app=S.AppGUI()
        try:
            sample=folder/'set.mp3';sample.write_bytes(b'source audio must survive')
            saved=folder/'results/old.json';saved.write_text('{"saved":true}')
            app.set_path.set(str(sample));app.media_url.set('https://example.com/set')
            app._render_hits([{'source':'mix-id','artist':'Artist','title':'Song','time':30}])
            app.last_scan={'path':str(sample),'report':str(saved)};app._resume_pending={'S'}
            app._notify('stage_progress','M/probe/1',2,3,'Old request');app._events()
            app.reset_set();app.root.update()
            assert not app.current_hits and not app.raw_hits and not app.progress_tasks and not app._resume_pending
            assert not app.set_path.get() and not app.media_url.get() and app.last_scan is None
            assert app.progressbar.value==0 and app.metadata_progress.value==0
            assert not app.result_table.get_children() and not app.restore_last_scan()
            assert json.loads((S.C.DATA/'arbeitsstand.json').read_text())['empty'] is True
            assert sample.read_bytes()==b'source audio must survive' and saved.exists()
            app.set_path.set(str(sample));app._render_hits([{'source':'mix-id','title':'Before cancellation','time':0}])
            app._running(True);app.reset_set()
            assert app.cancel.is_set() and app._reset_requested and app.reset_button.disabled
            with patch.object(S,'show_completion') as completion,patch.object(S.messagebox,'showerror') as error:
                app._notify('hits',[{'source':'ShazamIO','title':'Late old result','time':60}])
                app._notify('stage_progress','S',1,1,'Late old progress')
                app._notify('error','cancelled');app._events()
                completion.assert_not_called();error.assert_not_called()
            assert not app.running and not app._reset_requested and not app.raw_hits and not app.progress_tasks
            assert not app.reset_button.disabled and not app.start_button.disabled and not app.cancel.is_set()
            app._set_workspace_empty(False)
            assert not json.loads((S.C.DATA/'arbeitsstand.json').read_text())['empty']
        finally:app.root.destroy()
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent
    shutil.rmtree(folder)
print('RESET OK: empty current workspace, late job events discarded, cancellation finishes first, no auto-restore or source/library deletion.')
