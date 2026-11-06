from pathlib import Path
import sys,json,uuid,shutil,threading
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import almighty as S,ai_method as A,local_ai as L
folder=Path(__file__).resolve().parent/('ai-ui-fixture-'+uuid.uuid4().hex);folder.mkdir()
release=threading.Event();started=threading.Event()
def judge(self,rows,provider,model):
    started.set();assert release.wait(5)
    return [{'case_id':row['case_id'],'verdict':'uncertain','reason':'Keine sichere Versionsbestätigung.','source_ids':[]} for row in rows]
try:
    with patch.object(S.C,'DATA',folder/'data'),patch.object(S.C,'OUTPUT',folder/'results'),patch.object(S.C,'LOGS',folder/'logs'),patch.object(S.C,'CONFIG_FILE',folder/'settings.json'),patch.object(S.AppGUI,'check_local_ai'),patch.object(L,'detect',return_value=('LM Studio','fixture/model','ready')),patch.object(A.Audit,'source_lookup',return_value=([],[])),patch.object(A.Audit,'judge',judge),patch.object(S,'show_completion'):
        app=S.AppGUI()
        try:
            sample=folder/'set.wav';sample.write_bytes(b'not played');report=folder/'results/set.txt';report.parent.mkdir(exist_ok=True);report.write_text('Scan saved')
            tracks=[{'artist':'Artist','title':'Song (Remix)','time':30,'source':'mix-id'}]
            app.set_path.set(str(sample));app._scan_path=str(sample);app._running(True)
            worker=app._start_audit(sample,{'ai_audio_check':False},60,tracks);worker.finish(report)
            assert started.wait(2)
            for key in app.stages:
                if key!='KI':app._stage_ui(key,'done','core done')
            app._notify('scan_finished',{'path':str(sample),'report':str(report),'results':{'observations':tracks},'statuses':{},'errors':[]})
            app._notify('done','core finished');app._events()
            assert not app.running and not app.start_button.disabled,'AI blocked the completed core scans'
            assert app.stage_status['KI']['state']=='running' and app.progressbar.value<1,'Unfinished AI was shown at 100%'
            release.set();worker.worker.join(5);assert not worker.worker.is_alive();app._events()
            assert app.stage_status['KI']['state']=='done' and app.progressbar.value==1
            assert app.last_scan['results']['ai_review']['complete']
            app.show_ai_findings();app.root.update();assert app.ai_window.winfo_exists()
            app.reset_set();assert app._ai_worker is None and not app._ai_findings
        finally:release.set();app.root.destroy()
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent;shutil.rmtree(folder)
print('AI UI LIFECYCLE OK: core results available while AI runs, truthful independent progress, late findings saved, visible evidence and reset cleanup.')
