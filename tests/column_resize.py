"""Drag native column separators; widths must survive refresh, scrolling and reopening."""
from pathlib import Path
import json,sys,uuid,shutil,time
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import almighty as S
folder=Path(__file__).resolve().parent/('columns-fixture-'+uuid.uuid4().hex);folder.mkdir()
def settle(app):
    end=time.monotonic()+.22
    while time.monotonic()<end:app.root.update();time.sleep(.01)
def close(app):
    for job in app.root.tk.splitlist(app.root.tk.call('after','info')):app.root.tk.call('after','cancel',job)
    app.root.destroy()
def drag(app,table,column,delta):
    table.xview_moveto(0);app.root.update()
    first=table.get_children()[0];box=table.bbox(first,column);assert box,(column,table.xview())
    edge=box[0]+box[2];y=max(4,box[1]//2)
    x=next((v for v in sorted(range(edge-4,edge+4),key=lambda value:abs(value-edge)) if 0<v<table.winfo_width() and table.identify_region(v,y)=='separator'),None)
    assert x is not None,(column,edge,table.winfo_width())
    before=table.column(column,'width')
    table.event_generate('<ButtonPress-1>',x=x,y=y);app.root.update()
    table.event_generate('<B1-Motion>',x=x+delta,y=y,state=0x100);app.root.update()
    table.event_generate('<ButtonRelease-1>',x=x+delta,y=y);settle(app)
    after=table.column(column,'width');assert abs(after-before-delta)<=2,(column,before,after,delta)
    return after
try:
    with patch.object(S.C,'DATA',folder/'data'),patch.object(S.C,'OUTPUT',folder/'out'),patch.object(S.C,'LOGS',folder/'logs'),patch.object(S.C,'CONFIG_FILE',folder/'cfg.json'),patch.object(S.AppGUI,'check_local_ai'):
        app=S.AppGUI();errors=[];app.root.report_callback_exception=lambda *e:errors.append(e)
        try:
            app._render_hits([{'source':'mix-id','artist':'Artist','title':'A long title '+('abcdefghij '*30),'time':15}]);settle(app)
            title=drag(app,app.result_table,'title',-120)
            method=drag(app,app.result_table,'method',40)
            for _ in range(3):app._render_hits([]);settle(app)
            assert app.result_table.column('title','width')==title and app.result_table.column('method','width')==method
            app.result_table.xview_moveto(1);settle(app)
            assert app.result_table.column('title','width')==title
            stored=json.loads((folder/'data/spaltenbreiten.json').read_text());assert stored['results']['title']==title
            viewer=app.show_results();settle(app)
            large=drag(app,viewer.table,'title',-190);assert large<260,'Old hard minimum still blocks shrinking'
            viewer.refresh();settle(app);assert viewer.table.column('title','width')==large
            viewer.window.destroy();viewer=app.show_results();settle(app)
            assert viewer.table.column('title','width')==large,'Large view forgot saved widths'
            assert not errors,errors
        finally:close(app)
        app=S.AppGUI()
        try:
            settle(app);assert app.result_table.column('title','width')==title and app.result_table.column('method','width')==method
        finally:close(app)
    print('COLUMN RESIZE OK: real separator drags, shrinking/enlarging, live refresh and horizontal scrolling preserve widths; main and large views restore their own saved sizes.')
finally:
    assert folder.resolve().parent==Path(__file__).resolve().parent;shutil.rmtree(folder)
