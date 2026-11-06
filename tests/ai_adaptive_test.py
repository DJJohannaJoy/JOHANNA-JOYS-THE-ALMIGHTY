from pathlib import Path
import sys,json,uuid,shutil,wave
from unittest.mock import patch
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import ai_method as A,ai_adaptive as D,scanner_core as C
folder=Path(__file__).resolve().parent/('adaptive-fixture-'+uuid.uuid4().hex);folder.mkdir()
@contextmanager
def scratch(**kwargs):
    path=folder/uuid.uuid4().hex;path.mkdir()
    try:yield str(path)
    finally:
        assert path.resolve().parent==folder.resolve();shutil.rmtree(path)
try:
    mix=folder/'set.wav'
    with wave.open(str(mix),'wb') as stream:stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(11025);stream.writeframes(b'\0\0'*11025*100)
    reference=folder/'Artist - Song Remix.wav';reference.write_bytes(b'local reference');db=folder/'db.pklz';db.write_bytes(b'fixture')
    cfg={'ffmpeg_dir':r'C:\Users\JOY\Desktop\SET SCANNER\tools\ffmpeg','ai_web_lookup':False}
    calls=[];judged=[]
    def match(parts,factor,kind,directory,env,cancel,log):
        calls.append((factor,kind));assert parts[0].is_file()
        return [C.OfflineHit(str(reference),0,100,factor,kind,0,0,str(parts[0]),12)],[]
    with patch.object(C,'DB',db),patch.object(D.tempfile,'TemporaryDirectory',scratch):
        audit=A.Audit(mix,cfg,folder/'data',lambda *args:None,match=match,duration=100)
        case=A.build_cases([{'artist':'Artist','title':'Song (Remix)','source':'mix-id','time':0}])[0]
        row={**case,'sources':[{'source_id':'wrong','title':'Artist Live DJ Set'}],
             'audio':{'state':'no_match','tested_files':[str(reference)],'positions':[0,45],'factors':[1,.94,1.06],'matches':[]}}
        menu=audit.test_menu(row)
        selected=[t['test_id'] for t in menu if t['kind']=='audio' and t['factor']==.97 and t['mode']=='tempo' and t['position'] in (0,25)]
        assert len(selected)==2
        initial={'case_id':case['case_id'],'verdict':'uncertain','reason':'Tempo unklar.','source_ids':['wrong'],'next_test_ids':selected+['invented-test']}
        def judge(rows,provider,model):
            judged.append(rows)
            assert rows[0]['audio']['state']=='strong_local_match'
            return [{'case_id':case['case_id'],'verdict':'supported','reason':'Zwei getrennte Fingerprint-Fenster passen.','source_ids':[],'next_test_ids':[]}]
        audit.judge=judge
        result=audit.refine_case(row,initial,'LM Studio','fixture')
        assert len(calls)==2 and len(judged)==1 and result['audio']['state']=='strong_local_match'
        assert result['audio']['matches'][0]['independent_windows']==2
        assert len(result['adaptive_history'])==1 and result['adaptive_history'][0]['selected_by']=='model'
        assert all(t['test_id']!='invented-test' for r in result['adaptive_history'] for t in r['tests'])
        assert result['matched_source_ids']==[],'A complete DJ set was accepted as a direct song source'
        audit.refine_case(row,initial,'LM Studio','fixture');assert len(calls)==2,'Identical probes were not cached'
        def hit(position):return {'path':str(reference),'title':'Song','window':position,'score':100,'support_seconds':12,'factor':1,'set_position':position}
        overlap=D.summarize([hit(0),hit(6)],[str(reference)])
        assert overlap['state']=='ambiguous' and overlap['matches'][0]['independent_windows']==1
        separate=D.summarize([hit(0),hit(25)],[str(reference)])
        assert separate['state']=='strong_local_match'
        mismatched={**row,'audio':{**separate,'matches':[{**separate['matches'][0],'path':str(folder/'Artist - Different Song.wav')}]}}
        guarded=audit.validate_review(mismatched,{'case_id':case['case_id'],'verdict':'supported','reason':'Falsche Modellbehauptung','source_ids':[]})
        assert guarded['verdict']=='version_conflict','A differently named audio reference was silently accepted'
        # Invalid IDs can only fall back to one generated local test, never run model commands.
        audit.cfg['ai_adaptive_rounds']=1
        audit.judge=lambda *args:[{'case_id':case['case_id'],'verdict':'uncertain','reason':'Ein Fenster reicht nicht.','source_ids':[],'next_test_ids':['shell:erase']}]
        invalid={**initial,'next_test_ids':['shell:erase']}
        fallback=audit.refine_case(row,invalid,'LM Studio','fixture')
        assert fallback['adaptive_history'][0]['selected_by']=='fallback' and len(fallback['adaptive_history'])==1
        assert all(t['kind']=='audio' for t in fallback['adaptive_history'][0]['tests'])
        audit.abort();before=len(calls);audit.refine_case(row,initial,'LM Studio','fixture');assert len(calls)==before
    print('ADAPTIVE AI OK: model-selected clips/tempi executed, new evidence rejudged, bounded rounds, invalid IDs rejected, probe cache reused and overlapping clips never counted as independent.')
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent;shutil.rmtree(folder)
