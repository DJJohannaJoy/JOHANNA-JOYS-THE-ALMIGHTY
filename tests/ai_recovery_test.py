"""A truncated reply at 50% must not abandon the remaining half of the set."""
from pathlib import Path
import sys,json,uuid,shutil
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import ai_method as A,local_ai as L
folder=Path(__file__).resolve().parent/('ai-recovery-'+uuid.uuid4().hex);folder.mkdir()
try:
    mix=folder/'set.wav';mix.write_bytes(b'fixture')
    tracks=[{'artist':'Artist','title':f'Song {i:02}','time':i*240,'source':'mix-id'} for i in range(24)]
    events=[];requests=[];broken=[False]
    def llm(url,payload,timeout):
        rows=json.loads(payload['messages'][1]['content'])['cases'];requests.append((len(rows),payload['max_tokens']))
        assert payload['response_format']['type']=='json_schema'
        if rows[0]['tracks'][0]['title']=='Song 12' and not broken[0]:
            broken[0]=True
            return {'choices':[{'finish_reason':'length','message':{'content':'{"reviews":[{"case_id":'}}]}
        return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'reviews':[
            {'case_id':r['case_id'],'verdict':'uncertain','reason':'Keine Audio-Referenz verfügbar.',
             'source_ids':[],'next_test_ids':[]} for r in rows]})}}]}
    cfg={'ai_audio_check':False,'ai_web_lookup':False,'ai_adaptive_rounds':0}
    with patch.object(L,'detect',return_value=('LM Studio','test/model','ready')),patch.object(L,'request_json',side_effect=llm):
        audit=A.Audit(mix,cfg,folder/'data',lambda *e:events.append(e))
        audit.offer(tracks);audit.finish();audit.start();audit.worker.join(10)
        assert not audit.worker.is_alive() and broken[0]
        assert len(audit.reviews)==24 and events[-1][3]['state']=='done',events[-1]
        assert any(e[2]=='progress' and e[3]['done']==12 for e in events)
        assert all(any(e[2]=='progress' and e[3]['done']==n for e in events) for n in (10,11,13,14)), 'Progress waited for a whole batch'
        assert (1,4096) in requests and all(not r.get('adaptive_failed') for r in audit.reviews.values())
        assert json.loads(next(audit.root.glob('*.json')).read_text())['complete']
    # A permanently broken case remains visibly incomplete, but later songs still get checked.
    events=[]
    def permanent(url,payload,timeout):
        rows=json.loads(payload['messages'][1]['content'])['cases']
        if any(r['tracks'][0]['title']=='Song 12' for r in rows):
            return {'choices':[{'finish_reason':'length','message':{'content':'{}'}}]}
        return llm(url,payload,timeout)
    with patch.object(L,'detect',return_value=('LM Studio','test/model','ready')),patch.object(L,'request_json',side_effect=permanent):
        audit=A.Audit(mix,cfg,folder/'partial',lambda *e:events.append(e))
        audit.offer(tracks);audit.finish();audit.start();audit.worker.join(10)
        assert not audit.worker.is_alive() and len(audit.reviews)==24
        bad=[r for r in audit.reviews.values() if r.get('adaptive_failed')]
        assert len(bad)==1 and bad[0]['tracks'][0]['title']=='Song 12' and bad[0]['review_error']
        assert events[-1][3]['state']=='failed'
        assert not json.loads(next(audit.root.glob('*.json')).read_text())['complete']
    # A nominally complete response with a missing case also triggers individual recovery.
    with patch.object(L,'request_json',side_effect=llm):
        row=audit.current_cases()[0]
        with patch.object(audit,'_judge_once',side_effect=[[],[{'case_id':row['case_id'],'verdict':'uncertain','reason':'Recovered','source_ids':[]}]]) as once:
            assert audit.judge([row],'LM Studio','test')[0]['reason']=='Recovered' and once.call_count==2
    print('AI RECOVERY OK: truncation at 12/24 recovers automatically; permanent case failure does not abandon later songs; invalid/missing output is never marked verified.')
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent;shutil.rmtree(folder)
