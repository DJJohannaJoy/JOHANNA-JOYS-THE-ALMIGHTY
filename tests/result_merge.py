from pathlib import Path
import sys,json,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import track_results as R
import engine_external as X
import scanner_core as C

observations=[
 {'artist':'Artist','title':'Song','source':'mix-id','time':120,'_observed_order':1},
 {'title':'Artist - Song (Original Mix)','source':'offline','full_path':'Artist - Song.flac','time':105,'_observed_order':2},
 {'artist':'Artist','title':'Song','source':'ShazamIO','time':180,'_observed_order':3},
 {'artist':'Artist','title':'Song','source':'ShazamIO','time':300,'_observed_order':4},
 {'artist':'Artist','title':'Song','source':'ShazamIO','time':420,'_observed_order':5},
 {'artist':'Artist','title':'Song (Another Remix)','source':'ShazamIO','time':500,'_observed_order':6},
 {'artist':'Other','title':'Song','source':'ShazamIO','time':510,'_observed_order':7},
 {'artist':'Artist','title':'Song','source':'mix-id','time':560,'_observed_order':8}]
tracks=R.merge_records(observations)
assert len(tracks)==4,tracks
assert [t['number'] for t in tracks]==[1,2,3,4]
assert tracks[0]['methods']==['mix-id','Schnellscan · Originaltempo','ShazamIO']
assert tracks[0]['catalogs']==['Shazam','Lokale Musikdatenbank']
assert tracks[0]['first_detection']==105 and tracks[0]['last_detection']==420
assert tracks[0]['full_path']=='Artist - Song.flac'
assert len(tracks[0]['evidence'])==5
assert R.merge_records([{'artist':'A','title':'T','time':0,'source':'mix-id'},
 {'artist':'B','title':'U','time':90,'source':'mix-id'},
 {'artist':'A','title':'T','time':150,'source':'ShazamIO'}])[-1]['number']==3
assert len(R.merge_records([{'artist':'歌手','title':'曲甲','source':'mix-id','time':0},
                           {'artist':'歌手','title':'曲乙','source':'mix-id','time':30}]))==2
print('RESULT MERGE OK: cross-source duplicates, chronological numbering, source order, long plays, remixes, artists and later repeats.')
from unittest.mock import patch
import uuid,shutil
td=Path(__file__).resolve().parent/('ui-fixture-export-'+uuid.uuid4().hex);td.mkdir()
try:
    with patch.object(C,'OUTPUT',td):
        report,exported=X.merged_report(Path('fixture-set.wav'),600,[],[],[],[],{'Offline':'fixture'},[],observations=observations)
    saved=json.loads(report.with_suffix('.json').read_text(encoding='utf-8'))
    assert saved['file']=='fixture-set.wav' and saved['duration']==600
    assert saved['observations']==observations and len(saved['tracks'])==len(tracks)
finally:
    assert td.resolve().parent==Path(__file__).resolve().parent
    shutil.rmtree(td)
print('RESUME EXPORT OK: file, duration and original evidence persist for isolated reruns after restart.')
