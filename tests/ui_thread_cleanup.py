"""Real Tk dialogs, concurrent progress and worker GC must not finalize Tcl off-thread."""
from pathlib import Path
import json,os,shutil,subprocess,sys,uuid
root=Path(__file__).resolve().parents[1]
if '--child' not in sys.argv:
    folder=root/'tests'/('ui-fixture-thread-'+uuid.uuid4().hex);folder.mkdir()
    try:
        env={**os.environ,'ALMIGHTY_DATA_ROOT':str(folder/'data')}
        run=subprocess.run([sys.executable,'-X','faulthandler','-X','utf8',__file__,'--child'],cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        assert run.returncode==0,run.stdout+'\n'+run.stderr
        result=json.loads(run.stdout.strip().splitlines()[-1])
        assert result['unsafe']==0 and result['deferred']>0 and result['pending']==0,result
        print('TCL THREAD SAFETY OK: real dialog cycles and parallel scan/AI events; deferred '+str(result['deferred'])+' off-thread cleanups safely; no Tcl finalizers run in workers.')
    finally:
        assert folder.resolve().parent==(root/'tests').resolve();shutil.rmtree(folder)
    raise SystemExit(0)
import gc,threading,time,tkinter as tk
from PIL import ImageTk,Image
from tkinter.font import Font
from unittest.mock import patch
sys.path.insert(0,str(root/'APP'))
import almighty as S
owner=threading.get_ident();unsafe=[]
for cls in (tk.Variable,tk.Image,Font,ImageTk.PhotoImage):
    original=cls.__del__
    def instrument(self,original=original):
        if threading.get_ident()!=owner:unsafe.append(type(self).__name__)
        return original(self)
    cls.__del__=instrument
stop=threading.Event();errors=[]
inventory={'models':[],'downloaded':[],'info':'Test inventory','model':''}
with patch.object(S.AppGUI,'check_local_ai'),patch.object(S.AppGUI,'_refresh_readiness'),patch.object(S.AppGUI,'restore_last_scan'),patch.object(S.L,'inventory',return_value=inventory):
    app=S.AppGUI();app.root.report_callback_exception=lambda *e:errors.append(repr(e));app.root.update();app.root.withdraw()
    def background():
        for n in range(900):
            if stop.is_set():return
            app._notify('stage_progress','S',n%50,50,'Shazam · Testprobe')
            app._notify('stage_progress','KI/case-1',n%3,3,'KI-Nachprüfung · Test')
            allocation=[{'loop':n,'data':list(range(80))} for _ in range(15)]
            if n%10==0:gc.collect()
            time.sleep(.008)
    worker=threading.Thread(target=background,name='Scan-AI-GC-Test',daemon=True);worker.start()
    cycles=[0]
    def dialogs():
        cycles[0]+=1
        app.toggle_language()
        app.show_results();app.results_window.window.destroy()
        app.configure_local_ai()
        for window in app.root.winfo_children():
            if isinstance(window,tk.Toplevel) and window is not app.settings_window:window.destroy()
        # Exercise every protected resource family with a genuine Python cycle.
        for resource in (tk.StringVar(master=app.root,value='test'),tk.PhotoImage(master=app.root,width=2,height=2),
                         Font(root=app.root,family='Segoe UI',size=8),ImageTk.PhotoImage(Image.new('RGBA',(2,2)),master=app.root)):
            resource._test_cycle=resource
        if cycles[0]<16:app.root.after(180,dialogs)
    app.root.after(50,dialogs)
    started=time.monotonic()
    def finish():
        import ui_lifetime as U
        if (worker.is_alive() or cycles[0]<16) and time.monotonic()-started<60:
            app.root.after(100,finish);return
        stop.set();worker.join(1);U.drain()
        print(json.dumps({'unsafe':len(unsafe),'deferred':U.deferred_count,'pending':U._pending.qsize(),'cycles':cycles[0],'errors':errors}),flush=True)
        assert not worker.is_alive() and cycles[0]==16 and not errors
        app.root.destroy()
    app.root.after(100,finish)
    app.root.mainloop()
