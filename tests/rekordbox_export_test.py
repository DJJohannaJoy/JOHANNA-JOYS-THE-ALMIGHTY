from pathlib import Path
import sys,json,uuid,shutil,xml.etree.ElementTree as ET,csv
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import rekordbox_export as E,almighty as S,ui_rekordbox as U
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
    assert 'TEILPLAYLIST_2_von_4' in partial['playlist']
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
    store=E.SavedMatches(folder/'private/choices.json');store.assign(tracks[0],second)
    loaded=E.SavedMatches(store.path);assert loaded.assignments(tracks)[E.identity(tracks[0])]==str(second.resolve())
    assert E.identity(tracks[1]) not in loaded.assignments(tracks),'Remix assignment leaked into original version'
    loaded.assign(tracks[0],None);assert not E.SavedMatches(store.path).assignments(tracks)
    assert set(E.music_files(audio))=={str(original.resolve()),str(second.resolve())}
    assert not list((folder/'out').glob('.rekordbox-*')),'Failed exports left a staging folder behind'
    # A real, decodable audio file also makes the round trip without changing its bytes.
    import wave,hashlib
    playable=audio/'Real Artist - Playable.wav'
    with wave.open(str(playable),'wb') as stream:
        stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(44100);stream.writeframes(b'\0'*44100*4)
    checksum=hashlib.sha256(playable.read_bytes()).hexdigest()
    playable_rows=E.Resolver([playable]).resolve([{'artist':'Real Artist','title':'Playable','time':0}])
    bundle=E.write_bundle(folder/'out','Playable full export',playable_rows)
    assert bundle['complete'] and E.uri_path(ET.parse(bundle['xml']).find('./COLLECTION/TRACK').get('Location'))==playable
    assert checksum==hashlib.sha256(playable.read_bytes()).hexdigest()
    with patch.object(E.csv,'writer',side_effect=OSError('Simulated full disk')):
        before=set((folder/'out').iterdir())
        try:E.write_bundle(folder/'out','Failed write',resolver.resolve([tracks[1]]))
        except OSError:pass
        else:raise AssertionError('Disk failure was hidden')
        assert set((folder/'out').iterdir())==before,'Incomplete export was exposed after failure'
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
                window.destroy();app.show_rekordbox_export();app.root.update();window=app.rekordbox_window
                assert not window._export_button.disabled,'Saved assignments were forgotten on reopening'
                clear=next(w for w in descendants(window) if isinstance(w,U.BloodButton) and w.caption=='ZUORDNUNG LÖSCHEN')
                table=window._table
                missing_row=next(iid for iid in table.get_children() if 'Missing' in table.item(iid,'values')[1])
                table.selection_set(missing_row);clear.action();assert window._export_button.disabled
                # Folder lookup runs independently and persists its file index for future sets.
                music=next(w for w in descendants(window) if isinstance(w,U.BloodButton) and w.caption=='MUSIKORDNER ABGLEICHEN')
                with patch.object(U.filedialog,'askdirectory',return_value=str(audio)):
                    music.action()
                    import time
                    limit=time.monotonic()+3
                    while time.monotonic()<limit:
                        app.root.update()
                        if str(second) in E.SavedMatches(data/'rekordbox_export_zuordnungen.json').value['extra_files']:break
                        time.sleep(.02)
                    assert str(second) in E.SavedMatches(data/'rekordbox_export_zuordnungen.json').value['extra_files']
                remix.write_bytes(b'restored fixture')
                (data/'bibliothek.json').write_text(json.dumps({'files':[str(original),str(remix),str(second)]}))
                E.SavedMatches(data/'rekordbox_export_zuordnungen.json').assign(tracks[0],None)
                window=app.show_rekordbox_export();app.root.update();table=window._table
                iid=next(i for i in table.get_children() if 'Joy Remix' in table.item(i,'values')[1]);table.selection_set(iid);app.root.update()
                assert len(window._candidate.cget('values'))==2
                window._candidate.set(str(second));choose=next(w for w in descendants(window) if isinstance(w,U.BloodButton) and w.caption=='DATEI ÜBERNEHMEN');choose.action()
                assert E.SavedMatches(data/'rekordbox_export_zuordnungen.json').assignments(tracks)[E.identity(tracks[0])]==str(second.resolve())
            assert not errors,errors
        finally:app.root.destroy()
    print('REKORDBOX EXPORT OK: exact versions, ambiguity/missing files, ordered repeats, Unicode paths, valid XML references, strict/partial exports, file revalidation and real Tk assignment/export flow.')
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent;shutil.rmtree(folder)
