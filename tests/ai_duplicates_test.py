from pathlib import Path
import json,sys,uuid,shutil
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import track_results as R,duplicates as D,engine_external as X,audio_core as C
raw=[{'artist':'Artist A & Artist B','title':'Song','time':60,'source':'mix-id','_observed_order':1},
     {'artist':'Artist B, Artist A','title':'Song (Extended Mix)','time':80,'source':'ShazamIO','_observed_order':2}]
base=R.merge_records(raw);assert len(base)==2
row={'case_id':'case','tracks':base}
ids=[r['track_id'] for r in base]
answer={'duplicate_track_ids':ids,'reason':'Identische Künstler und dieselbe Set-Stelle; alternative Metadaten.'}
validated=D.validate_ids(row,answer,'uncertain');assert validated==ids
review={**row,'duplicate_track_ids':validated,'verdict':'uncertain','reason':answer['reason']}
groups=D.groups([review],'local-model')
merged=R.merge_records(raw,duplicate_groups=groups)
assert len(merged)==1 and merged[0]['number']==1 and len(merged[0]['evidence'])==2
assert merged[0]['methods']==['mix-id','ShazamIO','KI · Dublettenprüfung']
assert len(merged[0]['sources'])==2 and len(merged[0]['merged_track_ids'])==2
assert merged[0]['first_detection']==60 and merged[0]['last_detection']==80
assert len(R.merge_records([{**raw[0],'title':'Song'},{**raw[1],'title':'Song'}]))==1,'Credit order duplicated the same recording'
for changed in ({'title':'Different Song'},{'title':'Song (Special Remix)'},{'time':900},{'artist':'Other Artist'}):
    records=R.merge_records([raw[0],{**raw[1],**changed}]);decisions=[{'track_ids':[r['track_id'] for r in records],'reason':'wrong'}]
    assert len(R.merge_records([raw[0],{**raw[1],**changed}],duplicate_groups=decisions))==2,changed
repeat=[raw[0],{'artist':'Another','title':'Intervening','source':'mix-id','time':75,'_observed_order':3},raw[1]]
records=R.merge_records(repeat);assert len(R.merge_records(repeat,duplicate_groups=groups))==3
try:D.validate_ids(row,{'duplicate_track_ids':['invented'],'reason':'bad'},'supported')
except RuntimeError:pass
else:raise AssertionError('Invented AI IDs accepted')
assert not D.validate_ids(row,answer,'version_conflict')
assert len(R.merge_records(raw,duplicate_groups=[{'track_ids':[{}]}]))==2
catalog_raw=[{**r,'url':'https://www.shazam.com/track/123/song'} for r in raw]
catalog_tracks=R.merge_records(catalog_raw)
catalog_review={'case_id':'proof','tracks':catalog_tracks,'verdict':'uncertain','reason':'Audio noch unsicher','duplicate_track_ids':[]}
proof=D.groups([catalog_review],'local-model')
assert len(proof)==1 and proof[0]['decision_origin']=='catalog_identity'
assert len(R.merge_records(catalog_raw,duplicate_groups=proof))==1
assert D.catalog_ids({'url':'https://www.shazam.com/song/123/song'})!={'shazam:123'},'Apple song and Shazam track ID namespaces mixed'
folder=Path(__file__).resolve().parent/('ui-fixture-duplicates-'+uuid.uuid4().hex);folder.mkdir()
try:
    with patch.object(C,'OUTPUT',folder):
        report,_=X.merged_report(Path('set.wav'),120,[],[],[],[],{},[],observations=raw)
        X.refresh_ai_report(report,{'duplicate_groups':groups,'cases':[review]})
        saved=json.loads(report.with_suffix('.json').read_text(encoding='utf-8'))
        assert saved['observations']==raw and len(saved['tracks'])==1 and saved['ai_review']['duplicate_groups']==groups
        assert 'KI · Dublettenprüfung' in report.read_text(encoding='utf-8-sig')
    import almighty as S
    from types import SimpleNamespace
    with patch.object(C,'DATA',folder/'data'),patch.object(C,'OUTPUT',folder/'results'),patch.object(C,'LOGS',folder/'logs'),patch.object(C,'CONFIG_FILE',folder/'settings.json'),patch.object(S.AppGUI,'check_local_ai'):
        app=S.AppGUI()
        try:
            app._render_hits(raw);assert len(app.current_hits)==2
            app._ai_worker=SimpleNamespace(run_id='dedupe',mix=Path('fixture-missing.wav'))
            payload={'version':3,'cases':[review],'duplicate_groups':groups,'complete':True}
            app._handle_ai_event('dedupe','findings',{'findings':payload})
            assert len(app.current_hits)==1 and len(app.result_table.get_children())==1
            app.set_path.set('fixture-missing.wav')
            app.last_scan={'path':'fixture-missing.wav','duration':120,'results':{'observations':raw},'statuses':{},'errors':[]}
            app._handle_ai_event('dedupe','findings',{'findings':payload})
            entry=app.save_current_set(quiet=True)
            snapshot=json.loads(Path(entry).read_text(encoding='utf-8'))
            assert len(snapshot['tracks'])==1 and len(snapshot['observations'])==2 and snapshot['ai_review']['duplicate_groups']==groups
        finally:app._ai_worker=None;app.root.destroy()
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent;shutil.rmtree(folder)
print('AI DUPLICATES OK: validated model IDs merge nearby identity aliases; credits and all provenance retained; remixes, different artists/titles and genuine repeats remain separate; TXT/JSON persist the same result.')
