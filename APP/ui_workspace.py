"""Large results, local set library and live progress, in FIRST SPARK colours."""
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font
import time
import webbrowser
import set_library as library
from ui_text import tr,TEXT as UI_TEXT
from ui_first_spark import BloodButton,GlowProgress,PANEL,FIELD,TEXT,MUTE,HOT,LINE,resizable_columns

NAMES={'setup':'Dateien vorbereiten','A':'Schnellscan','B':'Tiefenscan 1','M':'Tiefenscan 2','S':'Shazam','E':'Ergebnis','KI':'KI-Prüfung'}
PLATFORMS=(('soundeo','Soundeo',100),('soundcloud','SoundCloud',124),('youtube','YouTube',100),('beatport','Beatport',100),('spotify','Spotify',100))

def ai_progress(app):
    """Count completed cases plus real partial steps; elapsed time never invents progress."""
    task=app.progress_tasks.get('KI',{})
    done=int(task.get('done',0));total=int(task.get('total',0))
    if not task and getattr(app,'_ai_findings',{}):
        done=len(app._ai_findings.get('cases',[]));total=int(app._ai_findings.get('total_cases',done))
    state=app.stage_status.get('KI',{}).get('state')
    active=state in ('running','retrying') or state=='waiting' and bool(task or getattr(app,'_ai_live_detail',''))
    completed={case['case_id'] for case in getattr(app,'_ai_findings',{}).get('cases',[])}
    partial=sum(min(.95,max(0,item.get('percent',0)/100))
                for key,item in app.progress_tasks.items() if key.startswith('KI/') and
                key[3:] not in completed and item.get('percent',0)<100) if active else 0
    percent=min(99.9 if active else 100,100*(done+partial)/total) if total else 0
    return done,total,percent,active

class NamedProgress(GlowProgress):
    def __init__(self,parent):
        self.caption='';super().__init__(parent)
    def draw(self):
        super().draw()
        self.create_text(max(20,self.winfo_width())/2,max(10,self.winfo_height())/2,text=tr(self,self.caption),fill=TEXT,font=('Segoe UI',9,'bold'))

def shell(app,title,size):
    window=tk.Toplevel(app.root);window.title('THE ALMIGHTY · '+title)
    window.configure(bg=PANEL);window.geometry(size);window.minsize(800,500)
    if hasattr(app,'_app_icon'):window.iconphoto(False,app._app_icon)
    heading=tk.Label(window,text=title.upper(),bg=PANEL,fg=TEXT,font=('Segoe UI',19,'bold'),anchor='w');heading.pack(fill='x',padx=20,pady=(14,8))
    if title not in UI_TEXT and title.upper() not in UI_TEXT:window._literal_title=True;heading._no_translate=True
    tk.Frame(window,bg=HOT,height=2).pack(fill='x',padx=20,pady=(0,10))
    return window

class ResultsWindow:
    def __init__(self,app,supplier,title='Titelliste'):
        self.app,self.supplier=app,supplier;self.last=None;self.rows={}
        self.window=shell(app,title,'1500x800');self.window.minsize(960,600)
        def closed(event):
            if event.widget==self.window:
                for name in ('_refresh_job','_fit_job'):
                    job=getattr(self,name,None)
                    if job:self.window.after_cancel(job);setattr(self,name,None)
        self.window.bind('<Destroy>',closed,add='+')
        bar=tk.Frame(self.window,bg=PANEL);bar.pack(fill='x',padx=20,pady=(0,8))
        tk.Label(bar,text='Titel / Künstler suchen',bg=PANEL,fg=MUTE).pack(side='left',padx=(0,12))
        self.query=tk.StringVar();tk.Entry(bar,textvariable=self.query,bg=FIELD,fg=TEXT,insertbackground=TEXT,font=('Segoe UI',12),relief='flat').pack(side='left',fill='x',expand=True,ipady=7)
        BloodButton(bar,'MAXIMIEREN',self.maximize,width=150,height=36,outline_only=True).pack(side='right',padx=(12,0))
        def export():
            from ui_rekordbox import show_export
            name=title if title!='Titelliste' else __import__('pathlib').Path(app.set_path.get().strip()).stem or 'Set'
            show_export(app,list(supplier()),name)
        BloodButton(bar,'REKORDBOX-EXPORT',export,width=200,height=36,outline_only=True).pack(side='right',padx=(12,0))
        frame=tk.Frame(self.window,bg=PANEL);frame.pack(fill='both',expand=True,padx=20)
        columns=('number','time','title','format','bpm','method','source',*[key for key,_,_ in PLATFORMS])
        # A separate native row style avoids the main table's fixed grid-image offsets.
        style=ttk.Style(self.window)
        style.configure('Results.Treeview',background=FIELD,foreground=TEXT,fieldbackground=FIELD,
                        rowheight=30,borderwidth=0,font=('Segoe UI',10))
        style.configure('Results.Treeview.Heading',background='#252627',foreground=TEXT,font=('Segoe UI',10,'bold'),relief='flat')
        style.map('Results.Treeview',background=[('selected','#812031')],foreground=[('selected',TEXT)])
        self.table=ttk.Treeview(frame,columns=columns,show='headings',style='Results.Treeview')
        spec=[('number','NR.',45),('time','ZEIT',85),('title','TITEL',320),('format','FORMAT',70),
              ('bpm','BPM',65),('method','METHODE',155),('source','QUELLE',185),
              *[(key,provider.upper(),width) for key,provider,width in PLATFORMS]]
        for key,name,width in spec:
            anchor='w' if key in ('title','method','source') else 'center'
            self.table.heading(key,text=name,anchor=anchor)
            self.table.column(key,width=width,minwidth=min(width,60),stretch=key=='title',anchor=anchor)
        vertical=ttk.Scrollbar(frame,orient='vertical',command=self.table.yview)
        horizontal=ttk.Scrollbar(frame,orient='horizontal',command=self.table.xview)
        frame.columnconfigure(0,weight=1);frame.rowconfigure(0,weight=1)
        self.table.grid(row=0,column=0,sticky='nsew');vertical.grid(row=0,column=1,sticky='ns');horizontal.grid(row=1,column=0,sticky='ew')
        self.table.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        self.table.bind('<ButtonRelease-1>',self.click)
        self.table.bind('<<TreeviewSelect>>',lambda e:self.selected())
        resizable_columns(self.table,app,'large_results',self.queue_fit)
        actions=tk.Frame(self.window,bg=PANEL);actions.pack(fill='x',padx=20,pady=10)
        for index,(_,provider,_) in enumerate(PLATFORMS):
            actions.columnconfigure(index,weight=1,uniform='platforms')
            BloodButton(actions,provider.upper(),lambda p=provider:self.open_search(p),width=150,height=39,outline_only=True).grid(row=0,column=index,sticky='ew',padx=(0,8) if index<4 else (0,0))
        self.detail=tk.StringVar(value='Suchlinks öffnen die jeweilige Suche. Verfügbarkeit und kostenlose Downloads sind nicht bestätigt.')
        detail_label=tk.Label(self.window,textvariable=self.detail,bg=PANEL,fg=MUTE,anchor='w',justify='left',wraplength=1400,font=('Segoe UI',10));detail_label.pack(fill='x',padx=20,pady=(0,14))
        detail_label._no_translate=True
        self.refresh()
    def maximize(self):
        try:self.window.state('zoomed')
        except tk.TclError:self.window.geometry(f'{self.window.winfo_screenwidth()}x{self.window.winfo_screenheight()-70}+0+0')
    def current(self):
        chosen=self.table.selection()
        return self.rows.get(chosen[0]) if chosen else None
    def selected(self):
        hit=self.current()
        if hit:self.detail.set(f"{hit.get('artist','')} – {hit.get('title','')}\n"+' → '.join(hit.get('methods',[]))+' | '+' + '.join(hit.get('sources',[])))
    def open_search(self,provider):
        hit=self.current()
        if hit:webbrowser.open(library.search_links(hit)[provider])
    def click(self,event):
        if self.table.identify_region(event.x,event.y)=='separator':return
        row=self.table.identify_row(event.y);column=self.table.identify_column(event.x)
        index=int(column[1:])-8 if column.startswith('#') else -1
        if row and 0<=index<len(PLATFORMS):
            self.table.selection_set(row);self.open_search(PLATFORMS[index][1])
    def queue_fit(self,event=None):
        if getattr(self,'_fit_job',None):self.window.after_cancel(self._fit_job)
        def fit():
            self._fit_job=None;self.last=None;self.refresh()
        self._fit_job=self.window.after(70,fit)
    def refresh(self):
        if not self.window.winfo_exists():return
        if getattr(self,'_refresh_job',None):self.window.after_cancel(self._refresh_job)
        tracks=list(self.supplier());needle=self.query.get().strip().casefold()
        visible=[t for t in tracks if needle in (str(t.get('artist',''))+' '+str(t.get('title',''))).casefold()]
        signature=repr(visible)
        if signature!=self.last:
            selected=self.current();identity=selected.get('track_id') if selected else None;view=self.table.yview()[0]
            self.table.delete(*self.table.get_children());self.rows={}
            from tkinter.font import Font
            font=Font(root=self.window,family='Segoe UI',size=10)
            def fit(text,column):
                text=str(text);width=self.table.column(column,'width')-14
                if font.measure(text)<=width:return text
                lo,hi=0,len(text)
                while lo<hi:
                    middle=(lo+hi+1)//2
                    if font.measure(text[:middle]+'…')<=width:lo=middle
                    else:hi=middle-1
                return text[:lo]+'…'
            for i,t in enumerate(visible,1):
                bpm=t.get('bpm');bpm=('≈' if t.get('bpm_estimated') else '')+f'{bpm:g}' if isinstance(bpm,(float,int)) else '—'
                name=(t.get('artist','')+' – ' if t.get('artist') else '')+t.get('title','')
                row=self.table.insert('','end',values=(t.get('number',i),self.app._time(t.get('time',0)),fit(name,'title'),t.get('audio_format','—'),bpm,fit(' → '.join(t.get('methods',[])),'method'),fit(' + '.join(t.get('sources',[])),'source'),*[tr(self.table,'SUCHEN')]*len(PLATFORMS)))
                self.rows[row]=t
                if identity and t.get('track_id')==identity:self.table.selection_set(row)
            self.table.yview_moveto(view);self.last=signature
        self._refresh_job=self.window.after(400,self.refresh)

def show_library(app):
    window=shell(app,'Set-Bibliothek','1120x720');app.library_window=window
    query=tk.StringVar();entry=tk.Entry(window,textvariable=query,bg=FIELD,fg=TEXT,insertbackground=TEXT,font=('Segoe UI',12),relief='flat')
    entry.pack(fill='x',padx=20,pady=(0,10),ipady=9)
    tk.Label(window,text='Suche nach Set, Künstler oder Titel · Doppelklick öffnet die Titelliste',bg=PANEL,fg=MUTE,anchor='w').pack(fill='x',padx=20,pady=(0,8))
    frame=tk.Frame(window,bg=PANEL);frame.pack(fill='both',expand=True,padx=20)
    table=ttk.Treeview(frame,columns=('name','date','count'),show='headings',style='Almighty.Treeview')
    for key,title,width in [('name','SET',650),('date','GESPEICHERT',190),('count','TITEL',80)]:table.heading(key,text=title);table.column(key,width=width,stretch=key=='name')
    scroll=ttk.Scrollbar(frame,orient='vertical',command=table.yview);scroll.pack(side='right',fill='y');table.configure(yscrollcommand=scroll.set);table.pack(fill='both',expand=True)
    rows={}
    def selected():
        chosen=table.selection();return rows.get(chosen[0]) if chosen else None
    def open_tracks(event=None):
        item=selected()
        if item:ResultsWindow(app,lambda:item['tracks'],item['name'])
    def load():
        item=selected()
        if item and not app.running:
            if app.load_library_entry(item):window.destroy()
    def refresh(*args):
        table.delete(*table.get_children());rows.clear()
        for item in library.entries(app.C_DATA/'Set-Bibliothek',app.C_OUTPUT,query.get()):
            row=table.insert('','end',values=(item['name'],item['created'].replace('T',' '),item['count']));rows[row]=item
    query.trace_add('write',refresh);table.bind('<Double-1>',open_tracks)
    actions=tk.Frame(window,bg=PANEL);actions.pack(fill='x',padx=20,pady=15)
    for caption,command in [('GROSS ANZEIGEN',open_tracks),('ZUM PRÜFEN LADEN',load),('AKTUALISIEREN',refresh)]:BloodButton(actions,caption,command,width=235,height=43,outline_only=True).pack(side='left',padx=(0,10))
    refresh();entry.focus_set()

class ProgressPanel:
    def __init__(self,parent,app):
        self.app=app;self.rows={};self.subrows={}
        self.frame=tk.Frame(parent,bg=PANEL);self.frame.pack(fill='both',expand=True)
        self.frame.columnconfigure(0,weight=40,uniform='progress');self.frame.columnconfigure(1,weight=60,uniform='progress');self.frame.rowconfigure(1,weight=1)
        tk.Label(self.frame,text='SCAN-METHODEN',bg=PANEL,fg=MUTE,font=('Segoe UI',9,'bold')).grid(row=0,column=0,sticky='w')
        right=tk.Frame(self.frame,bg=PANEL);right.grid(row=0,column=1,sticky='ew',padx=(16,0))
        tk.Label(right,text='UNTERSCHRITTE / SCHNIPSEL',bg=PANEL,fg=MUTE,font=('Segoe UI',9,'bold')).pack(side='left')
        self.filter=tk.StringVar(value='Alle');self.filter_menu=ttk.Combobox(right,textvariable=self.filter,values=['Alle',*NAMES.values()],state='readonly',width=19);self.filter_menu.pack(side='right')
        self.method_frame,self.method_body=self.viewport(self.frame,0)
        self.sub_frame,self.sub_body=self.viewport(self.frame,1)
        self.method_body.columnconfigure(0,weight=1,uniform='methods');self.method_body.columnconfigure(1,weight=1,uniform='methods')
        for i,(key,title) in enumerate(NAMES.items()):
            self.rows[key]=self.row(self.method_body,title,pack=False,compact=True)
            row=self.rows[key][0];row.pack_forget();row.grid(row=i//2,column=i%2,sticky='ew',padx=(0,9),pady=2)
        self.update()
    def viewport(self,parent,column):
        frame=tk.Frame(parent,bg=PANEL);frame.grid(row=1,column=column,sticky='nsew',padx=(0,8) if column==0 else (16,0))
        canvas=tk.Canvas(frame,bg=PANEL,highlightthickness=0,height=112);scroll=ttk.Scrollbar(frame,orient='vertical',command=canvas.yview)
        scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True);canvas.configure(yscrollcommand=scroll.set)
        body=tk.Frame(canvas,bg=PANEL);win=canvas.create_window(0,0,window=body,anchor='nw')
        body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(win,width=e.width))
        canvas.bind('<MouseWheel>',lambda e:canvas.yview_scroll(-int(e.delta/120),'units'))
        return frame,body
    def row(self,parent,title,pack=True,compact=False):
        row=tk.Frame(parent,bg=PANEL)
        if pack:row.pack(fill='x',pady=3)
        caption=tk.Label(row,text=title,bg=PANEL,fg=TEXT,anchor='w',font=('Segoe UI',9))
        if not compact:caption.pack(fill='x')
        bar=NamedProgress(row) if compact else GlowProgress(row);bar.configure(height=26 if compact else 23);bar.pack(fill='x',padx=(0,5))
        return row,caption,bar
    def update(self):
        if not self.frame.winfo_exists():return
        if getattr(self,'_timer',None):
            self.frame.after_cancel(self._timer);self._timer=None
        tasks=dict(self.app.progress_tasks)
        ai_done,ai_total,ai_percent,ai_active=ai_progress(self.app)
        for key,(row,caption,bar) in self.rows.items():
            value=self.app.stagebar.percentages.get(key,0);state=self.app.stage_status.get(key,{})
            text='Aus' if key in self.app.stagebar.skipped else f'{value:.0f} %'
            if key=='KI' and ai_total:
                value=ai_percent
                text=f'{ai_done}/{ai_total} · {value:.1f} %'
            caption.configure(text=f'{NAMES[key]} · {text}');bar.caption=f'{NAMES[key]} · {text}';bar.set_progress(value/100)
            main=getattr(self.app,'method_progress',{}).get(key)
            if main:
                main.caption=f"{'Dateien' if key=='setup' else 'KI' if key=='KI' and ai_total else NAMES[key]} · {text}";main.set_progress(value/100)
        live=getattr(self.app,'ai_live_label',None)
        if live is not None:
            prefix=tr(live,'KI')+f': {ai_done}/{ai_total} '+tr(live,'geprüft') if ai_total else ''
            detail=getattr(self.app,'_ai_live_detail','') if ai_active else ''
            if ai_active and not detail:detail=self.app.stage_status.get('KI',{}).get('detail','')
            if detail:
                title,separator,action=detail.rpartition(' · ')
                detail=tr(live,action)+' · '+title if separator else tr(live,detail)
            seconds=max(0,int(time.monotonic()-getattr(self.app,'_ai_live_started',time.monotonic())))
            suffix=f' · {seconds} s '+('·','··','···')[seconds%3] if ai_active else ''
            width=max(1,live.winfo_width()-8);font=Font(root=self.app.root,font=live.cget('font'))
            base=(prefix+' · ' if prefix and detail else prefix)
            shown=detail
            while shown and font.measure(base+shown+suffix)>width:shown=shown[:-1]
            if shown!=detail and shown:shown=shown[:-1]+'…'
            live.configure(text=base+shown+suffix if prefix or detail else '',fg=TEXT if ai_active else MUTE)
        wanted={k:v for k,v in tasks.items() if '/' in k or k=='KI'}
        selected=self.filter.get()
        if selected=='All':selected='Alle'
        selected=next((name for name in NAMES.values() if tr(self.frame,name)==selected),selected)
        display_selected=tr(self.frame,selected)
        if self.filter.get()!=display_selected:self.filter.set(display_selected)
        values=['Alle',*NAMES.values()]
        self.filter_menu.configure(values=[tr(self.frame,v) for v in values])
        for key,(row,_,_) in list(self.subrows.items()):
            if key not in wanted:row.destroy();del self.subrows[key]
        for key,item in wanted.items():
            if key not in self.subrows:self.subrows[key]=self.row(self.sub_body,'')
            row,caption,bar=self.subrows[key];prefix=key.split('/')[0]
            if selected!='Alle' and NAMES.get(prefix)!=selected:row.pack_forget();continue
            if not row.winfo_manager():row.pack(fill='x',pady=3)
            caption.configure(text=f"{item['detail']} · {item['done']}/{item['total']} · {item['percent']:.0f} %",wraplength=max(250,self.sub_body.winfo_width()-15))
            bar.set_progress(item['percent']/100)
        order=tuple(sorted((k for k in wanted if selected=='Alle' or NAMES.get(k.split('/')[0])==selected),key=lambda k:(wanted[k]['percent']>=100,k)))
        if order!=getattr(self,'_order',None):
            for key in order:self.subrows[key][0].pack_forget()
            for key in order:self.subrows[key][0].pack(fill='x',pady=3)
            self._order=order
        value=self.app.progressbar.value
        if ai_total and ai_active:
            values=[ai_percent if key=='KI' else percentage for key,percentage in self.app.stagebar.percentages.items()
                    if key not in self.app.stagebar.skipped]
            value=sum(values)/max(1,len(values))/100
            self.app.progressbar.set_progress(value)
        self.app.overall_percent.set(f'{value*100:.0f} %' if value is not None else '…')
        self._timer=self.frame.after(300,self.update)
