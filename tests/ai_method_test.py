from test_paths import COMPONENTS
from pathlib import Path
import sys,json,uuid,shutil,threading,time,wave
from contextlib import contextmanager
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import ai_method as A,audio_core as C,local_ai as L
folder=Path(__file__).resolve().parent/('ai-method-fixture-'+uuid.uuid4().hex);folder.mkdir()
@contextmanager
def scratch(**kwargs):
    path=folder/uuid.uuid4().hex;path.mkdir()
    try:yield str(path)
    finally:
        assert path.resolve().parent==folder.resolve();shutil.rmtree(path)
try:
    mix=folder/'set.wav'
    with wave.open(str(mix),'wb') as stream:stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(11025);stream.writeframes(b'\0\0'*11025*25)
    tracks=[{'source':'mix-id','artist':'Artist','title':'Song (Original Mix)','time':20},
            {'source':'ShazamIO','artist':'Artist','title':'Song (DJ Remix)','time':40},
            {'source':'mix-id','artist':'Artist','title':'Different Song','time':300}]
    cases=A.build_cases(tracks)
    assert len(cases)==2 and len(cases[0]['tracks'])==2 and cases[0]['reason']=='Versionskonflikt'
    assert all(A.safe_source(url) for url in ['https://www.youtube.com/watch?v=abc','https://soundcloud.com/artist/song'])
    assert not any(A.safe_source(url) for url in ['file:///x','https://youtube.com.evil.example/x','http://127.0.0.1/','https://x:password@youtube.com/x'])
    events=[];posts=[]
    def llm(url,payload=None,timeout=4):
        assert url=='http://127.0.0.1:1234/v1/chat/completions'
        rows=json.loads(payload['messages'][1]['content'])['cases'];posts.append(rows)
        return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'reviews':[{
            'case_id':row['case_id'],'verdict':'version_conflict' if len(row['tracks'])>1 else 'uncertain',
            'reason':'Original und Remix bleiben getrennt. Metadaten allein bestätigen keine Audio-Version.',
            'source_ids':['actual-source','invented-source']} for row in rows]})}}]}
    def sources(self,track):return [{'source_id':'actual-source','title':track['title'],'url':'https://soundcloud.com/artist/song','provider':'SoundCloud'}],[]
    with patch.object(L,'detect',return_value=('LM Studio','test/model','ready')),patch.object(L,'request_json',side_effect=llm),patch.object(A.Audit,'source_lookup',sources):
        audit=A.Audit(mix,{'ai_audio_check':False},folder/'data',lambda *event:events.append(event))
        audit.offer(tracks);audit.finish(folder/'result.txt');audit.start();audit.worker.join(5)
        assert not audit.worker.is_alive() and posts
        assert events[-1][2]=='state' and events[-1][3]['state']=='done',events[-1]
        findings=json.loads(next((folder/'data/KI-Nachpruefung').glob('*.json')).read_text())
        assert findings['complete'] and len(findings['cases'])==2
        assert all(case['matched_source_ids']==['actual-source'] for case in findings['cases'])
        assert (folder/'result_KI_METHODE.json').exists()
        previous=len(posts);cached=A.Audit(mix,{'ai_audio_check':False},folder/'data',lambda *event:None)
        cached.offer(tracks);cached.finish();cached.start();cached.worker.join(5)
        assert len(posts)==previous,'Unchanged evidence was needlessly reviewed again'
        cancelled=A.Audit(mix,{},folder/'cancelled',lambda *event:events.append(event));cancelled.abort();n=len(events)
        cancelled.offer(tracks);cancelled.finish();cancelled.start();cancelled.worker.join(3);assert len(events)==n
    # A real FFmpeg clip goes through the fingerprint adapter; the model cannot make this evidence.
    reference=folder/'Artist - Song (DJ Remix).wav';shutil.copy2(mix,reference);db=folder/'fake.pklz';db.write_bytes(b'fixture')
    def match(parts,factor,kind,directory,env,cancel,log):
        assert len(parts)==1 and parts[0].is_file()
        return [C.OfflineHit(str(reference),0,240,factor,kind,0,0,str(parts[0]),12)],[]
    cfg={'ffmpeg_dir':str(COMPONENTS/'tools/ffmpeg')}
    with patch.object(C,'DB',db),patch.object(A.tempfile,'TemporaryDirectory',scratch):
        audit=A.Audit(mix,cfg,folder/'audio',lambda *event:None,match=match,duration=25)
        value=audit.audio_check(cases[0],[str(reference)])
        assert value['state']=='strong_local_match' and len(value['factors'])==3,value
        def competing(*args,**kwargs):return [C.OfflineHit(str(reference),0,240,1,'tempo',0,0,'part-0000.wav',12),C.OfflineHit('other.wav',0,500,1,'tempo',0,0,'part-0000.wav',12)],[]
        audit.match=competing;value=audit.audio_check(cases[0],[str(reference)])
        assert value['state']=='ambiguous','A stronger competing reference was ignored'
    print('AI METHOD OK: remix cases, separate titles, grounded structured verdicts, URL/ID validation, caching, cancellation, saved evidence and real FFmpeg clips with fingerprint-score guards.')
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent
    shutil.rmtree(folder)
