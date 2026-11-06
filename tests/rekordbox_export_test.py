from pathlib import Path
import sys,json,uuid,shutil,xml.etree.ElementTree as ET,csv
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import rekordbox_export as E,scanner as S,ui_rekordbox as U
folder=Path(__file__).resolve().parent/('export-fixture-'+uuid.uuid4().hex);folder.mkdir()
try:
    audio=folder/'audio';audio.mkdir()
    original=audio/'Ärtist - Song #1 (Original Mix).aiff';original.write_bytes(b'audio fixture')
    remix=audio/'Ärtist - Song #1 (Joy Remix).mp3';remix.write_bytes(b'audio fixture')
    duplicate=audio/'copy';duplicate.mkdir();second=duplicate/remix.name;second.write_bytes(b'fixture')
    tracks=[{'artist':'Ärtist','title':'Song #1 (Joy Remix)','time':90,'bpm':156},
            {'artist':'Ärtist','title':'Song #1','time':10,'bpm':150},
            {'artist':'Missing','title':'Unavailable','time':120},
            {'artist':'Ärtist','title':'Song #1','time':180}]
    resolver=E.Resolver([original,remix,second]);rows=resolver.resolve(tracks)
    assert [r['state'] for r in rows]==['ready','ambiguous','missing','ready'],rows
    assert [r['number'] for r in rows]==[1,2,3,4] and rows[0]['path']==str(original)
    try:E.write_bundle(folder/'out','Set',rows)
    except ValueError:pass
    else:raise AssertionError('Incomplete playlist was presented as complete')
    partial=E.write_bundle(folder/'out','Ä Set #1',rows,strict=False)
    assert partial['exported']==2 and partial['unresolved']==2 and not partial['complete']
    tree=ET.parse(partial['xml']).getroot()
    assert len(tree.findall('./COLLECTION/TRACK'))==1
    assert len(tree.findall('./PLAYLISTS/NODE/NODE/TRACK'))==2
    collection=tree.find('./COLLECTION/TRACK')
    assert E.uri_path(collection.get('Location')).resolve()==original.resolve()
    assert '%23' in collection.get('Location') and not any(k in collection.attrib for k in ('AverageBpm','Bpm','TotalTime'))
    assert Path(partial['playlist']).read_text(encoding='utf-8').count(str(original))==2
    assignment={E.identity(tracks[0]):str(remix),E.identity(tracks[2]):str(remix)}
    ready=resolver.resolve(tracks,assignment);assert all(r['state']=='ready' for r in ready)
    complete=E.write_bundle(folder/'out','Set',ready);assert complete['complete'] and complete['exported']==4
    assert E.write_bundle(folder/'out','Set',ready)['folder']!=complete['folder'],'Overwrote a previous export'
    imported=E.Resolver(xml=complete['xml']);assert imported.resolve([tracks[0]])[0]['state']=='ready'
    remix.unlink()
    try:E.write_bundle(folder/'out','Changed after preview',ready)
    except ValueError:pass
    else:raise AssertionError('Disappeared file was exported as ready')
    assert resolver.resolve(tracks,assignment)[1]['state']=='missing'
    with (Path(partial['folder'])/'FEHLENDE_DATEIEN.csv').open(encoding='utf-8-sig',newline='') as stream:
        missing=list(csv.reader(stream,delimiter=';'));assert len(missing)==3 and 'Spotify' in missing[0]
    # Real Tk dialog: strict full export disabled for missing files; explicit partial export works.
    data=folder/'data';data.mkdir();(data/'bibliothek.json').write_text(json.dumps({'files':[str(original)]}))
    with patch.object(S.C,'DATA',data),patch.object(S.C,'OUTPUT',folder/'results'),patch.object(S.C,'LOGS',folder/'logs'),patch.object(S.AppGUI,'check_local_ai'):
        app=S.AppGUI();errors=[];app.root.report_callback_exception=lambda *e:errors.append(e)
        try:
            app._render_hits([{'source':'mix-id',**t} for t in tracks]);window=app.show_rekordbox_export();app.root.update()
            window=app.rekordbox_window
            assert window._export_button.disabled
            with patch.object(U.filedialog,'askopenfilename',return_value=str(original)),patch.object(app,'_open'):
                # Assign every unresolved row, preserving the user's deliberate choice.
                def descendants(widget):
                    for child in widget.winfo_children():
                        yield child;yield from descendants(child)
                table=next(w for w in descendants(window) if w.winfo_class()=='Treeview')
                assign=next(w for w in descendants(window) if isinstance(w,U.BloodButton) and w.caption=='DATEI ZUWEISEN')
                for iid in table.get_children():
                    table.selection_set(iid);assign.action()
                app.root.update();assert not window._export_button.disabled
                window._export_button.action();assert window._last_export['complete']
            assert not errors,errors
        finally:app.root.destroy()
    print('REKORDBOX EXPORT OK: exact versions, ambiguity/missing files, ordered repeats, Unicode paths, valid XML references, strict/partial exports, file revalidation and real Tk assignment/export flow.')
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent;shutil.rmtree(folder)
