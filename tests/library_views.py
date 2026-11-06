from pathlib import Path
import json,sys,uuid,shutil
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
from types import SimpleNamespace
from tkinter.font import Font
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import scanner as S,set_library as L
directory=Path(__file__).resolve().parent/('library-fixture-'+uuid.uuid4().hex);directory.mkdir()
try:
    data=directory/'data';output=directory/'results';output.mkdir()
    tracks=[{'number':1,'track_id':'a','artist':'Ärtist & Joy','title':'Song #1 (Remix)','time':12,'methods':['mix-id'],'sources':['Shazam-Katalog'],'bpm':145},
            {'number':2,'track_id':'b','artist':'Second','title':'Other Song','time':100,'methods':['ShazamIO'],'sources':['ShazamIO']}]
    report=output/'Set_Tracklist_20261105_120000.txt'
    report.with_suffix('.json').write_text(json.dumps({'file':str(directory/'missing.mp3'),'tracks':tracks}),encoding='utf-8')
    sidecar=report.with_name(report.stem+'_KI_METHODE.json')
    sidecar.write_text(json.dumps({'cases':[],'total_cases':2}),encoding='utf-8')
    assert L.report_paths(output)==[report.with_suffix('.json')],'AI sidecar replaced the actual tracklist'
    scan={'path':str(directory/'missing.mp3'),'report':str(report),'results':{'observations':[{'artist':t['artist'],'title':t['title'],'time':t['time'],'source':'mix-id'} for t in tracks]},'statuses':{'mix-id':'2 Treffer'}}
    saved=L.save_snapshot(data/'Set-Bibliothek',scan,tracks)
    assert L.save_snapshot(data/'Set-Bibliothek',scan,tracks)==saved
    listed=L.entries(data/'Set-Bibliothek',output)
    assert len(listed)==1 and listed[0]['count']==2
    assert L.entries(data/'Set-Bibliothek',output,'ärtist')[0]['entry_path']==str(saved)
    assert not L.entries(data/'Set-Bibliothek',output,'does not exist')
    assert 'Song #1 (Remix)' in parse_qs(urlparse(L.search_links(tracks[0])['YouTube']).query)['search_query'][0]
    assert parse_qs(urlparse(L.search_links(tracks[0])['SoundCloud']).query)['q'][0]=='Ärtist & Joy Song #1 (Remix)'
    assert urlparse(L.search_links(tracks[0])['Spotify']).hostname=='open.spotify.com'
    (data/'Set-Bibliothek/broken.json').write_text('broken')
    assert len(L.entries(data/'Set-Bibliothek',output))==1
    with patch.object(S.C,'DATA',data),patch.object(S.C,'OUTPUT',output),patch.object(S.C,'LOGS',directory/'logs'),patch.object(S.AppGUI,'check_local_ai'):
        app=S.AppGUI();errors=[];app.root.report_callback_exception=lambda *e:errors.append(e)
        try:
            app.set_path.set(scan['path']);app.last_scan=scan
            app._render_hits(scan['results']['observations']);app.root.update()
            viewer=app.show_results();app.root.update()
            assert len(viewer.table.get_children())==2 and len(viewer.table['columns'])==12
            assert viewer.table.heading('soundcloud','text')=='SOUNDCLOUD'
            assert viewer.table.heading('spotify','text')=='SPOTIFY'
            assert viewer.table.cget('style')=='Results.Treeview'
            for column in ('title','method','source'):
                assert str(viewer.table.heading(column,'anchor'))=='w' and str(viewer.table.column(column,'anchor'))=='w'
            for geometry in ('960x600','1500x800','1900x900'):
                viewer.window.geometry(geometry);app.root.update();viewer.last=None;viewer.refresh();app.root.update()
                font=Font(root=app.root,family='Segoe UI',size=10)
                for row in viewer.table.get_children():
                    values=viewer.table.item(row,'values')
                    for column,index in [('title',2),('method',5),('source',6)]:
                        assert font.measure(values[index])<=viewer.table.column(column,'width')-10
            first=viewer.table.get_children()[0];viewer.table.selection_set(first)
            with patch('ui_workspace.webbrowser.open') as browser:
                viewer.open_search('YouTube');browser.assert_called_once()
            viewer.table.xview_moveto(1);app.root.update()
            first=viewer.table.get_children()[0];viewer.table.selection_set(first)
            box=viewer.table.bbox(first,'spotify');assert box
            with patch('ui_workspace.webbrowser.open') as browser:
                viewer.click(SimpleNamespace(x=box[0]+box[2]//2,y=box[1]+box[3]//2))
                assert browser.call_args.args[0].startswith('https://open.spotify.com/search/')
            viewer.query.set('other');viewer.refresh();assert len(viewer.table.get_children())==1
            viewer.window.destroy()
            app.show_library();app.root.update();assert app.library_window.winfo_exists();app.library_window.destroy()
            assert app.load_library_entry(listed[0]) and len(app.current_hits)==2
            assert app.set_path.get().endswith('missing.mp3'),'Missing audio blocked the saved results'
            app._notify('stage_progress','M/probe/0001',2,3,'Tiefenscan 2 · 00:00:00 · Online-Suche')
            app._notify('stage_progress','S/probe/0001',3,3,'Shazam · geprüft');app._events();app.progress_panel.update();app.root.update()
            assert len(app.progress_panel.subrows)==2
            assert round(app.progress_panel.subrows['M/probe/0001'][2].value*100)==67
            assert app.save_current_set() and len(L.entries(data/'Set-Bibliothek',output))==1
            assert not errors,errors
        finally:app.root.destroy()
finally:
    assert directory.resolve().parent==Path(__file__).resolve().parent
    shutil.rmtree(directory)
print('LIBRARY / VIEWS OK: atomic snapshots, legacy deduplication, Unicode search, missing audio, large live/filterable list, platform links and real snippet bars.')
