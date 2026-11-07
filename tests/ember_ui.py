from pathlib import Path
import sys,json,uuid,shutil
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import almighty as S
from ui_theme import SectionHeading
directory=Path(__file__).resolve().parent/('ember-fixture-'+uuid.uuid4().hex);directory.mkdir()
try:
    with patch.object(S.C,'DATA',directory/'data'),patch.object(S.C,'OUTPUT',directory/'results'),patch.object(S.C,'LOGS',directory/'logs'),patch.object(S.C,'CONFIG_FILE',directory/'settings.json'),patch.object(S.AppGUI,'check_local_ai'):
        app=S.AppGUI();errors=[];app.root.report_callback_exception=lambda *e:errors.append(e)
        try:
            for geometry in ('1250x900','1570x990','1920x1000'):
                app.root.geometry(geometry);app.root.update();app.progress_panel.update();app.root.update()
                assert abs(app.progressbar.winfo_width()-app.metadata_progress.winfo_width())<=1
                assert app.progressbar.winfo_rooty()==app.metadata_progress.winfo_rooty()
                assert app.result_table.winfo_height()>=190
                for bar in app.method_progress.values():
                    assert bar.winfo_ismapped() and bar.winfo_height()>=26
                    assert bar.winfo_rooty()>app.progressbar.winfo_rooty()
                    parent=bar.master;bottom=bar.winfo_rooty()+bar.winfo_height()
                    while parent:
                        assert bottom<=parent.winfo_rooty()+parent.winfo_height(),(geometry,str(parent),bottom)
                        parent=parent.master
                header=app.header
                assert header.version_bounds[2]<=header.language_bounds[0]-8
                assert header.language_bounds[2]<header.library_bounds[0]<header.gear_bounds[0]
                assert header.itemcget(header.find_withtag('version')[0],'text')=='Version 1.14.1 - EMBER'
                buttons=(app.save_button,app.reset_button,app.retry_button)
                widths=[b.winfo_width() for b in buttons]
                assert max(widths)-min(widths)<=1,(geometry,widths)
                assert app.reset_button.caption=='RESET' and app.reset_button.symbol is None
                assert app.save_button.symbol is None
                for button in (*buttons,app.ai_model_button,app.ai_review_button):
                    text=[i for i in button.find_all() if button.type(i)=='text']
                    box=button.bbox(text[0])
                    assert 0<=box[0]<box[2]<=button.winfo_width(),(geometry,button.caption,box)
                assert abs(app.ai_model_button.winfo_width()-app.ai_review_button.winfo_width())<=1
                assert app.ai_model_button.winfo_rooty()==app.ai_review_button.winfo_rooty()
                assert app.ai_status_box.winfo_height()>=50,(geometry,app.ai_status_box.winfo_height())
                assert app.ai_status_box.winfo_rooty()>app.ai_model_button.winfo_rooty()+app.ai_model_button.winfo_height()
                app.ai_status_text.set('LM Studio: google/gemma-4-e4b · geladen\nModell verbunden · Nachprüfung bereit')
                assert app.ai_status_box.get('1.0','end-1c')==app.ai_status_text.get()
                assert app.ai_status_box.cget('state')=='disabled'
                flow=app.start_button.master.master.master
                group=app.start_button.master.master
                center=lambda w:w.winfo_rooty()+w.winfo_height()/2
                assert abs(center(group)-center(flow))<=1,(geometry,center(group),center(flow))
                assert abs(center(app.stagebar)-center(group))<20
            app._render_hits([{'source':'mix-id','artist':'Tiefenscan Artist','title':'Ergebnis Song','time':0}])
            originals=repr(app.current_hits)
            app.toggle_language();app.root.update()
            assert app.language.code=='en' and json.loads(S.C.CONFIG_FILE.read_text())['language']=='en'
            assert app.result_heading.cget('text')=='RESULTS'
            assert app.result_table.heading('title','text')=='TITLE'
            assert any(app.start_button.itemcget(i,'text')=='SCAN' for i in app.start_button.find_all() if app.start_button.type(i)=='text')
            assert repr(app.current_hits)==originals,'Language changed song data'
            app.show_library();app.language.apply(app.root);app.root.update()
            assert 'Set library' in app.library_window.title();app.library_window.destroy()
            app.toggle_language();app.root.update()
            assert app.language.code=='de' and app.result_heading.cget('text')=='ERGEBNIS'
            assert app.result_table.heading('title','text')=='TITEL'
            assert not errors,errors
        finally:app.root.destroy()
finally:
    assert directory.resolve().parent==Path(__file__).resolve().parent
    shutil.rmtree(directory)
print('EMBER UI OK: equal half-width bars, visible method row, preserved result area, unclipped reset, collision-free version and persistent reversible DE/EN without modifying songs.')
