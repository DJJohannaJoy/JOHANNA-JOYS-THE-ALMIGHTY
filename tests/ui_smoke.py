"""Exercise actual widgets without starting downloads or contacting recognition services."""
from pathlib import Path
import sys
import tempfile
import shutil
import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import scanner as S
from ui_first_spark import Header, SectionHeading, BrandRail

def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)

@contextmanager
def fixture_directory():
    parent=Path(__file__).resolve().parent
    directory=parent/('ui-fixture-'+uuid.uuid4().hex)
    directory.mkdir()
    try:
        yield directory
    finally:
        assert directory.resolve().parent==parent
        shutil.rmtree(directory)

with fixture_directory() as td:
    sample=Path(td)/'test set.wav'
    sample.write_bytes(b'test fixture, not played')
    app=S.AppGUI()
    callback_errors=[]
    app.root.report_callback_exception=lambda *error:callback_errors.append(error)
    try:
        app.root.update()
        # Confirm the minimum supported width and the main desktop sizes.
        for geometry in ('1250x900','1570x970','1920x1000'):
            app.root.geometry(geometry)
            app.root.update()
            assert app.file_button.winfo_width()==app.link_button.winfo_width()
            assert app.file_button.winfo_height()==app.link_button.winfo_height()
            assert app.file_button.winfo_rootx()==app.link_button.winfo_rootx()
            for widget in descendants(app.root):
                if isinstance(widget,SectionHeading):
                    box=widget.bbox('title')
                    assert box[2]<=widget.winfo_width()+1,(geometry,widget.title,box)
            # Header plus at least two complete 30-pixel result rows.
            assert app.result_table.winfo_height()>=190,(geometry,app.result_table.winfo_height())
            # Progress bars and their labels must fit every containing card,
            # not merely exist in the widget tree below its clipped viewport.
            for bar in (app.stagebar,app.progressbar,app.metadata_progress):
                assert bar.winfo_ismapped(),(geometry,bar)
                assert bar.winfo_height()>=24,(geometry,bar.winfo_height())
                bottom=bar.winfo_rooty()+bar.winfo_height()
                parent=bar.master
                while parent is not None:
                    assert bottom<=parent.winfo_rooty()+parent.winfo_height(),(geometry,bar,parent,bottom)
                    parent=parent.master
            assert app.stagebar.bbox('all')[3]<=app.stagebar.winfo_height(),geometry
            assert not any(app.stagebar.type(i)=='rectangle' for i in app.stagebar.find_all())
            assert len(app.progress_panel.rows)==7
            assert abs(app.save_button.winfo_width()-app.retry_button.winfo_width())<=1
            assert app.start_button.winfo_height()>=64
            assert app.reset_button.grid_info()['column']==1 and app.retry_button.grid_info()['column']==2
            assert app.result_heading.cget('text')=='ERGEBNIS'
            assert app.start_button.caption=='SCANNEN' and app.retry_button.outline_only
            assert app.large_results_button.winfo_ismapped()
            header=next(w for w in app.root.winfo_children() if isinstance(w,Header))
            x0,y0,x1,y1=header.gear_bounds
            bx0,by0,bx1,by1=header.library_bounds
            assert (x1-x0,y1-y0)==(bx1-bx0,by1-by0)
            assert bx1<x0 and by0==y0
            assert header.winfo_width()-x1>=38
            assert abs((y0+y1)/2-header.winfo_height()/2)<=2
            assert header.in_gear(SimpleNamespace(x=(x0+x1)/2,y=(y0+y1)/2))
            assert not header.in_gear(SimpleNamespace(x=header.winfo_width()-5,y=30))
            # Keep the designed rail and remove only its two unwanted text groups.
            rails=[w for w in app.root.winfo_children() if isinstance(w,BrandRail)]
            assert len(rails)==1 and rails[0].winfo_height()==49
            assert not any(rails[0].type(i)=='text' for i in rails[0].find_all())
            assert len(app.root.grid_slaves())==3
            assert not callback_errors,callback_errors
            drop_labels=[''.join(str(w.itemcget(i,'text')) for i in w.find_all()
                                if w.type(i)=='text')
                         for w in descendants(app.root) if hasattr(w,'_letter_fonts')]
            assert any(t.startswith('HIER REINZIEHEN') for t in drop_labels)
        with patch.object(S.filedialog,'askopenfilename',return_value=str(sample)):
            app.file_button._keyboard(None)
            assert app.set_path.get()==str(sample)
        app.set_path.set('')
        app._dropped(SimpleNamespace(data=app.root.tk.call('list',str(sample))))
        assert app.set_path.get()==str(sample)
        app.media_url.set('not a media url')
        with patch.object(S.messagebox,'showwarning') as warning:
            app.link_button._keyboard(None)
            warning.assert_called_once()
        header=next(w for w in app.root.winfo_children() if isinstance(w,Header))
        x0,y0,x1,y1=header.gear_bounds
        header.click(SimpleNamespace(x=(x0+x1)/2,y=(y0+y1)/2))
        assert app.settings_open
        app.toggle_settings()
        assert not app.settings_open
        app._running(True)
        app.root.update()
        assert app.start_button.disabled and app.stop_button.winfo_manager()
        app._running(False)
        assert not app.start_button.disabled and not app.stop_button.winfo_manager()
        app._notify('index_progress',{'percent':50,'done':40,'total':80,'eta':60,'phase':'index'})
        app._events()
        assert '50,0 %' in app.progress.get() and '40/80 Titel' in app.progress.get()
        assert app.progressbar.value==.5
        for key in app.stages:
            for state in ('running','done','failed','skipped','waiting'):
                app._stage_ui(key,state,'test')
        app._notify('stage_progress','A',1,4,'1/4 echte Prüfschritte')
        app._notify('stage_progress','B/tempo/0.94',1,2,'Tempo 0.94 · vergleichen')
        app._events()
        assert app.stagebar.percentages['A']==25
        app.show_progress_details();app.root.update()
        assert app.progress_dialog.winfo_exists()
        app.progress_dialog.destroy()
        app.raw_hits.clear();app.current_hits.clear();app.set_path.set('')
        records=[{'source':'offline','title':'Artist - Song (Original Mix)',
                  'full_path':'very-long-reference-filename-'*9+'.flac','time':100,'bpm':145,'_observed_order':1},
                 {'source':'mix-id','artist':'Artist','title':'Song','time':150,'_observed_order':2},
                 {'source':'ShazamIO','artist':'Artist','title':'Song','time':180,'_observed_order':3}]
        app._render_hits(records);app.root.update()
        assert len(app.current_hits)==1
        row=app.result_table.get_children()[0]
        assert app.result_table.item(row,'values')[0]=='1'
        from tkinter.font import Font
        font=Font(root=app.root,family='Segoe UI',size=10)
        for geometry in ('1250x900','1570x970','1920x1000'):
            app.root.geometry(geometry);app.root.update();app._render_hits([]);app.root.update()
            row=app.result_table.get_children()[0]
            values=app.result_table.item(row,'values')
            for column,index in [('method',5),('source',6)]:
                assert font.measure(values[index])<=app.result_table.column(column,'width')-10
            assert app.result_table.bbox(row,'source')[0]+app.result_table.bbox(row,'source')[2]<=app.result_table.winfo_width()+2
        app.result_table.selection_set(row);app.show_hit_detail();app.root.update()
        assert app.hit_dialog.winfo_exists()
        app.hit_dialog.destroy()
        # Focus retains keyboard activation without drawing pale boxes.
        app.start_button.focus_force();app.root.update();app.start_button._paint()
        assert not any(app.start_button.type(i)=='rectangle' for i in app.start_button.find_all())
        app.show_retry_methods();app.root.update()
        retry_buttons=[w for w in descendants(app.retry_dialog) if isinstance(w,S.BloodButton)]
        assert len(retry_buttons)==5 and all(not b.disabled for b in retry_buttons)
        app.retry_dialog.destroy()
        app._running(True);before=dict(app.raw_hits)
        app.start_scan(stages={'S'})
        assert app.raw_hits==before,'Starting a method while busy cleared existing results'
        app.show_retry_methods();app.root.update()
        assert all(w.disabled for w in descendants(app.retry_dialog) if isinstance(w,S.BloodButton))
        app.retry_dialog.destroy();app._running(False)
        app.set_path.set(str(sample))
        seed=list(app.raw_hits.values())
        app.last_scan={'path':str(sample),'results':{'offline':[records[0]],'weak':[],
            'mixid':[records[1]],'shazam':[records[2]],'observations':seed},
            'statuses':{'Offline':'1 Treffer','mix-id':'mit Fehlern'},'errors':['mix-id: fixture failure']}
        app._stage_ui('M','failed','mix-id: fixture failure')
        def isolated_method(path,cfg,duration,notify,cancel,split,match,stages=None,seed_observations=()):
            assert stages=={'S'} and list(seed_observations)==seed
            new={'source':'ShazamIO','artist':'Artist','title':'Recovered','time':300,'_observed_order':4}
            notify('hits',[new]);notify('stage','S','done','Erfolgreich wiederholt')
            return {'offline':[],'weak':[],'mixid':[],'shazam':[new],'observations':[*seed,new]}, {'ShazamIO':'1 Beobachtung'},[]
        import track_results as R
        with patch.object(app,'_launch',side_effect=lambda job:job({'ffmpeg_dir':'','local_ai_review':False})), \
             patch.object(S.C,'get_duration',return_value=600), \
             patch.object(S.J,'parallel_scan',side_effect=isolated_method), \
             patch.object(S.X,'merged_report',side_effect=lambda *a,**kw:(sample.with_suffix('.txt'),R.merge_records(kw['observations']))):
            app.start_scan(stages={'S'});app._events()
        assert app.last_scan['results']['offline']==[records[0]] and app.last_scan['results']['mixid']==[records[1]]
        assert len(app.current_hits)==2 and 0<app.progressbar.value<1
        assert 'Methoden offen' in app.progress.get() and app.stage_status['M']['state']=='failed'
        assert app.start_button.caption=='SCANNEN' and 'M' in app._resume_pending and 'S' not in app._resume_pending
        # Existing reports from before this update can be reopened and used
        # as the seed for an isolated retry after restarting the program.
        import json
        saved=Path(td)/'previous_Tracklist_20261105.json'
        saved.write_text(json.dumps({'tracks':R.merge_records(seed),'statuses':{'Offline':'1 Treffer',
            'mix-id':'mit Fehlern','ShazamIO':'mit Fehlern'},'errors':['Shazam timeout']}),encoding='utf-8')
        saved.with_suffix('.txt').write_text('Datei: '+str(sample)+'\n',encoding='utf-8-sig')
        app.raw_hits.clear();app.current_hits.clear();app.set_path.set('');app.last_scan=None
        assert app.restore_last_scan(saved)
        assert len(app.current_hits)==1 and len(app.last_scan['results']['observations'])==len(seed)
        assert app.last_scan['path']==str(sample) and app.stage_status['S']['state']=='failed'
        assert 0<app.progressbar.value<1 and 'SCANNEN' in app.progress.get()
        saved_data=json.loads(saved.read_text(encoding='utf-8'))
        saved_data['errors']=['Shazam: Anfragelimit (HTTP 429)']
        saved_data['progress']={'tasks':{'S':{'done':7,'total':50,'percent':14,'detail':'7/50 Proben'}},
                                'states':{'S':{'state':'paused','detail':'HTTP 429'}}}
        saved.write_text(json.dumps(saved_data),encoding='utf-8')
        app.raw_hits.clear();app.current_hits.clear();app.set_path.set('')
        assert app.restore_last_scan(saved)
        assert app.stage_status['S']['state']=='waiting' and app.stagebar.percentages['S']==14
        assert app.stagebar.progress_labels['M']=='Unvollständig'
        assert 'SCANNEN' in app.progress.get() and app.start_button.caption=='SCANNEN'
        def finish_open_methods(path,cfg,duration,notify,cancel,split,match,stages=None,seed_observations=()):
            assert stages=={'M','S'},'FORTSETZEN restarted completed offline scans'
            for key in stages:
                notify('stage_progress',key,1,1,'Gültige Antwort');notify('stage',key,'done','Fertig')
            return {'offline':[],'weak':[],'mixid':[],'shazam':[],'observations':list(seed_observations),'progress':{}}, {'mix-id':'Fertig','ShazamIO':'Fertig'},[]
        with patch.object(app,'_launch',side_effect=lambda job:job({'ffmpeg_dir':'','local_ai_review':False})), \
             patch.object(S.C,'get_duration',return_value=600),patch.object(S.J,'parallel_scan',side_effect=finish_open_methods), \
             patch.object(S.X,'merged_report',side_effect=lambda *a,**kw:(saved.with_suffix('.txt'),R.merge_records(kw['observations']))):
            app.start_scan();app._events()
        assert not app._resume_pending and app.start_button.caption=='SCANNEN' and app.progressbar.value==1
        assert all(app.stage_status[k]['state']=='done' for k in ('M','S'))
        app.raw_hits.clear();app.current_hits.clear();app.set_path.set('');assert app.restore_last_scan(saved)
        original=dict(app.current_hits)
        with patch.object(app,'_launch',side_effect=lambda job:job({'ffmpeg_dir':'','local_ai_model':'test/gemma'})), \
             patch.object(S.L,'review_report',return_value=saved.with_suffix('.KI.txt')) as ai, \
             patch.object(S.J,'parallel_scan') as not_scanning:
            app.start_ai_review();app._events()
            ai.assert_called_once();not_scanning.assert_not_called()
        assert app.current_hits==original and 'KI-Textprüfung gespeichert' in app.progress.get()
        # Branded completion preserves errors and has working result/retry actions.
        app._completion_context=app.last_scan
        with patch.object(S.messagebox,'showinfo') as native,patch.object(app,'_refresh_readiness'):
            app._notify('done','Scan beendet');app._events();app.root.update_idletasks()
            native.assert_not_called()
        dialog=app.completion_dialog
        for widget in descendants(dialog):
            parent=widget.master
            assert widget.winfo_ismapped(),widget
            assert widget.winfo_rooty()+widget.winfo_height()<=parent.winfo_rooty()+parent.winfo_height()+1,widget
        buttons={w.caption:w for w in descendants(dialog) if isinstance(w,S.BloodButton)}
        assert set(buttons)=={'ERGEBNIS ÖFFNEN','ORDNER ÖFFNEN','ERNEUT PRÜFEN','SCHLIESSEN'}
        with patch.object(S.os,'startfile') as opened:
            buttons['ERGEBNIS ÖFFNEN']._keyboard(None);opened.assert_called_once_with(saved.with_suffix('.txt'))
        with patch.object(app,'_open') as opened:
            buttons['ORDNER ÖFFNEN']._keyboard(None);opened.assert_called_once_with(saved.parent)
        with patch.object(app,'show_retry_methods') as retry:
            buttons['ERNEUT PRÜFEN']._keyboard(None);retry.assert_called_once()
        assert not dialog.winfo_exists()
        for context in ({**app.last_scan,'errors':[]},None):
            dialog=S.show_completion(app,'Datenbank fertig',context);app.root.update_idletasks()
            for widget in descendants(dialog):
                assert widget.winfo_ismapped(),widget
                assert widget.winfo_rooty()+widget.winfo_height()<=widget.master.winfo_rooty()+widget.master.winfo_height()+1,widget
            next(w for w in descendants(dialog) if isinstance(w,S.BloodButton) and w.caption=='SCHLIESSEN')._keyboard(None)
        app._notify('log','smoke-test diagnostic')
        app._events()
        assert 'smoke-test diagnostic' in app.logbox.get('1.0','end')
        app._refresh_readiness()
        with patch.object(S.L,'inventory',return_value={'models':[{'id':'test/gemma','loaded':True}],
                'downloaded':[],'model':'test/gemma','info':'LM Studio: test/gemma · geladen'}):
            app.configure_local_ai()
            app.root.update()
            app.ai_dialog.update_idletasks()
            assert app.ai_dialog.winfo_exists()
            assert app.ai_dialog.winfo_height()>=440
            app.ai_dialog.destroy()
        for key in app.statuses:
            status=app.statuses[key][1]
            action=app.status_actions[key]
            assert bool(status.winfo_manager()) != bool(action.winfo_manager())
        # Busy and disabled buttons must never invoke their action.
        with patch.object(app.start_button,'action') as action:
            app.start_button.configure(state='disabled')
            app.start_button._keyboard(None)
            action.assert_not_called()
        print('UI SMOKE OK: three sizes, aligned buttons, browse, drop handler, invalid URL, settings, running/cancel state, all six stages, diagnostics, prerequisites, keyboard gating.')
    finally:
        app.root.destroy()
