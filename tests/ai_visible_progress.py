from pathlib import Path
import sys,uuid,shutil,time
from types import SimpleNamespace
from unittest.mock import patch
from tkinter.font import Font
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import scanner as S,ui_workspace as U
folder=Path(__file__).resolve().parent/('ai-progress-'+uuid.uuid4().hex);folder.mkdir()
try:
    with patch.object(S.C,'DATA',folder/'data'),patch.object(S.C,'OUTPUT',folder/'results'),patch.object(S.C,'LOGS',folder/'logs'),patch.object(S.C,'CONFIG_FILE',folder/'settings.json'),patch.object(S.AppGUI,'check_local_ai'):
        app=S.AppGUI();errors=[];app.root.report_callback_exception=lambda *e:errors.append(e)
        try:
            app._ai_worker=SimpleNamespace(run_id='test')
            app._stage_ui('KI','running','Modell verbindet')
            app._handle_ai_event('test','progress',{'done':9,'total':24,'detail':'KI · 9/24 Fälle geprüft'})
            app._handle_ai_event('test','case_progress',{'case_id':'current','done':2,'total':7,'detail':'Artist – Song (Remix) · KI bewertet Belege'})
            app._events();app.root.update();app.progress_panel.update();app.root.update()
            before=U.ai_progress(app)[2]
            assert 37.5<before<40 and '9/24' in app.method_progress['KI'].caption
            for geometry in ('1250x980','1570x990','1920x1000'):
                app.root.geometry(geometry);app.root.update();app.progress_panel.update();app.root.update()
                label=app.ai_live_label;text=label.cget('text')
                assert '9/24 geprüft' in text and 'Belege' in text,(geometry,text)
                assert Font(root=app.root,font=label.cget('font')).measure(text)<=label.winfo_width()-6
                assert app.result_table.winfo_height()>=190
            app._ai_live_started=time.monotonic()-12;app.progress_panel.update()
            assert '12 s' in app.ai_live_label.cget('text')
            assert U.ai_progress(app)[2]==before,'Elapsed time fabricated percentage progress'
            app._handle_ai_event('test','case_activity',{'case_id':'current','detail':'Artist – Song · KI-Einzelprüfung 1/2'})
            app._events();app.progress_panel.update()
            assert U.ai_progress(app)[2]==before and 'Einzelprüfung' in app.ai_live_label.cget('text')
            app._handle_ai_event('test','case_progress',{'case_id':'current','done':4,'total':7,'detail':'Artist – Song (Remix) · KI bewertet neue Belege'})
            app._events();app.progress_panel.update()
            assert U.ai_progress(app)[2]>before
            app._handle_ai_event('test','progress',{'done':10,'total':24,'detail':'KI · 10/24 Fälle geprüft'})
            app._events();app.progress_panel.update();assert '10/24' in app.ai_live_label.cget('text')
            app._handle_ai_event('other-run','case_progress',{'case_id':'old','done':1,'total':1,'detail':'STALE'})
            assert 'STALE' not in app._ai_live_detail
            app._stage_ui('KI','done','KI fertig');app.progress_panel.update()
            assert ' s ' not in app.ai_live_label.cget('text')
            app._clear_current_set();app.progress_panel.update();assert app.ai_live_label.cget('text')==''
            assert not errors,errors
        finally:app.root.destroy()
    print('VISIBLE AI PROGRESS OK: case counts and current action in main footer; real substeps update fractional percent; live elapsed activity does not invent progress; three sizes, results area and reset preserved.')
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent;shutil.rmtree(folder)
