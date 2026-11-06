"""Review file assignments and export the entire recognized playlist in one action."""
import json,tkinter as tk,threading,queue
from tkinter import ttk,filedialog
from pathlib import Path
from ui_workspace import shell
from ui_theme import BloodButton,PANEL,FIELD,TEXT,MUTE,resizable_columns
from ui_text import tr
import rekordbox_export as E

def show_export(app,tracks,name):
    if not tracks:
        app.progress.set('Noch keine Titel zum Exportieren vorhanden');return
    previous=getattr(app,'rekordbox_window',None)
    if previous is not None and previous.winfo_exists():previous.destroy()
    window=shell(app,'Rekordbox-Export','1150x820');app.rekordbox_window=window
    try:files=json.loads((app.C_DATA/'bibliothek.json').read_text(encoding='utf-8')).get('files',[])
    except (OSError,ValueError):files=[]
    saved=E.SavedMatches(app.C_DATA/'rekordbox_export_zuordnungen.json')
    resolver=E.Resolver([*files,*saved.value['extra_files']]);assignments=saved.assignments(tracks);rows=[]
    status=tk.StringVar();message=tk.StringVar()
    xml=saved.value.get('library_xml')
    if isinstance(xml,str) and xml:
        try:resolver.load_xml(xml)
        except Exception:message.set(tr(window,'Gespeicherte Bibliotheks-XML nicht verfügbar'))
    tk.Label(window,textvariable=status,bg=PANEL,fg=TEXT,font=('Segoe UI',12,'bold'),anchor='w').pack(fill='x',padx=20,pady=(0,7))
    tk.Label(window,text='Alle erkannten Titel in Set-Reihenfolge. Es werden echte Audiodateien benötigt; Suchlinks reichen nicht.',bg=PANEL,fg=MUTE,anchor='w').pack(fill='x',padx=20,pady=(0,10))
    frame=tk.Frame(window,bg=PANEL);frame.pack(fill='both',expand=True,padx=20)
    style=ttk.Style(window);style.configure('Export.Treeview',background=FIELD,foreground=TEXT,fieldbackground=FIELD,rowheight=30,font=('Segoe UI',10))
    style.configure('Export.Treeview.Heading',background='#252627',foreground=TEXT,font=('Segoe UI',10,'bold'))
    style.map('Export.Treeview',background=[('selected','#812031')],foreground=[('selected',TEXT)])
    style.configure('Export.TCombobox',fieldbackground=FIELD,background=PANEL,foreground=TEXT,arrowcolor=TEXT)
    style.map('Export.TCombobox',fieldbackground=[('readonly',FIELD)],foreground=[('readonly',TEXT)],selectbackground=[('readonly','#812031')],selectforeground=[('readonly',TEXT)])
    table=ttk.Treeview(frame,columns=('number','title','state','path'),show='headings',style='Export.Treeview')
    for key,title,width in [('number','NR.',45),('title','TITEL',360),('state','ZUORDNUNG',245),('path','AUDIODATEI',450)]:table.heading(key,text=title,anchor='w');table.column(key,width=width,minwidth=min(width,60),stretch=key in ('title','path'))
    resizable_columns(table,app,'rekordbox_export',lambda:None)
    frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
    vertical=ttk.Scrollbar(frame,orient='vertical',command=table.yview);horizontal=ttk.Scrollbar(frame,orient='horizontal',command=table.xview)
    table.grid(row=0,column=0,sticky='nsew');vertical.grid(row=0,column=1,sticky='ns');horizontal.grid(row=1,column=0,sticky='ew')
    table.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
    window._table=table
    candidate_row=tk.Frame(window,bg=PANEL);candidate_row.pack(fill='x',padx=20,pady=(8,0))
    tk.Label(candidate_row,text=tr(window,'Passende Dateien:'),bg=PANEL,fg=MUTE).pack(side='left',padx=(0,8))
    candidate=tk.StringVar();choices=ttk.Combobox(candidate_row,textvariable=candidate,state='readonly',style='Export.TCombobox');choices.pack(side='left',fill='x',expand=True,padx=(0,8))
    window._candidate=choices
    def selected(event=None):
        chosen=table.selection();row=rows[int(chosen[0])] if chosen else None
        options=row['candidates'] if row else []
        choices.configure(values=options);candidate.set(row['path'] if row and row['path'] else options[0] if options else '')
    def remember(row,path):
        if path:assignments[E.identity(row['track'])]=path
        else:assignments.pop(E.identity(row['track']),None)
        try:saved.assign(row['track'],path)
        except OSError as exc:message.set(tr(window,'Zuordnung konnte nicht gespeichert werden')+': '+str(exc))
        refresh()
    def use_candidate():
        chosen=table.selection()
        if chosen and candidate.get():remember(rows[int(chosen[0])],candidate.get())
    BloodButton(candidate_row,'DATEI ÜBERNEHMEN',use_candidate,width=185,height=34,font_size=9,outline_only=True).pack(side='right')
    table.bind('<<TreeviewSelect>>',selected)
    strict=tk.BooleanVar(value=True)
    tk.Checkbutton(window,text='Nur als vollständige Playlist exportieren',variable=strict,command=lambda:refresh(),bg=PANEL,fg=TEXT,selectcolor=FIELD,activebackground=PANEL,activeforeground=TEXT).pack(anchor='w',padx=20,pady=(10,4))
    tk.Label(window,textvariable=message,bg=PANEL,fg=MUTE,wraplength=1100,justify='left',anchor='w').pack(fill='x',padx=20,pady=(0,8))
    actions=tk.Frame(window,bg=PANEL);actions.pack(fill='x',padx=20,pady=(0,16))
    busy=[False];cancel=threading.Event();results=queue.Queue()
    def refresh():
        nonlocal rows
        rows=resolver.resolve(tracks,assignments);chosen=table.selection();selected=chosen[0] if chosen else None
        table.delete(*table.get_children())
        for index,row in enumerate(rows):
            t=row['track'];table.insert('','end',iid=str(index),values=(row['number'],(str(t.get('artist') or '')+' – '+t['title']).strip(' –'),tr(window,row['reason']),row['path'] or ''))
        if selected and table.exists(selected):table.selection_set(selected)
        available=sum(r['state']=='ready' for r in rows)
        status.set(f'{available}/{len(rows)} Audiodateien verfügbar · {len(rows)-available} fehlen oder sind mehrdeutig')
        export.configure(state='normal' if not busy[0] and available and (not strict.get() or available==len(rows)) else 'disabled')
    def assign():
        chosen=table.selection()
        if not chosen:return
        row=rows[int(chosen[0])]
        path=filedialog.askopenfilename(parent=window,title=tr(window,'Audiodatei für diesen Titel auswählen'),filetypes=[('Audio','*.mp3 *.wav *.aiff *.aif *.flac *.m4a *.mp4 *.aac')])
        if path:remember(row,path)
    table.bind('<Double-1>',lambda event:assign())
    def clear():
        chosen=table.selection()
        if chosen:remember(rows[int(chosen[0])],None)
    def folder():
        if busy[0]:return
        chosen=filedialog.askdirectory(parent=window,title=tr(window,'Musikordner zum Abgleichen auswählen'))
        if not chosen:return
        busy[0]=True;message.set(tr(window,'Musikordner wird abgeglichen …'));refresh()
        def worker():
            try:results.put(('files',E.music_files(chosen,cancel)))
            except Exception as exc:results.put(('error',str(exc)))
        threading.Thread(target=worker,daemon=True,name='Rekordbox-Dateisuche').start()
    def poll():
        if cancel.is_set():return
        try:
            kind,value=results.get_nowait();busy[0]=False
            if kind=='files':
                for path in value:resolver.add(path)
                saved.value['extra_files']=sorted(set(saved.value['extra_files']+value))
                try:saved.save();message.set(str(len(value))+' '+tr(window,'Audiodateien abgeglichen'))
                except OSError as exc:message.set(str(exc))
            else:message.set(value)
            refresh()
        except queue.Empty:pass
        window._poll=window.after(150,poll)
    def load_xml():
        path=filedialog.askopenfilename(parent=window,title='Rekordbox XML',filetypes=[('Rekordbox XML','*.xml')])
        if path:
            try:
                resolver.load_xml(path);saved.value['library_xml']=path;saved.save()
                message.set(tr(window,'Rekordbox-Bibliothek eingelesen'));refresh()
            except Exception as exc:message.set(str(exc))
    def write(partial=False):
        try:
            result=E.write_bundle(app.C_OUTPUT/'Rekordbox-Export',name,rows,strict=False if partial else strict.get())
            message.set(f"{result['exported']}/{result['recognized']} Titel exportiert.\n"+result['folder'])
            window._last_export=result
            app._open(Path(result['folder']))
        except Exception as exc:message.set(str(exc));refresh()
    for i,(caption,command) in enumerate([('DATEI ZUWEISEN',assign),('MUSIKORDNER ABGLEICHEN',folder),('BIBLIOTHEKS-XML LADEN',load_xml),('ZUORDNUNG LÖSCHEN',clear),('TEILEXPORT / SUCHLISTE',lambda:write(True))]):
        actions.columnconfigure(i,weight=1,uniform='export')
        BloodButton(actions,caption,command,width=180,height=39,font_size=9,outline_only=True).grid(row=0,column=i,sticky='ew',padx=4)
    export=BloodButton(window,'PLAYLIST FÜR REKORDBOX EXPORTIEREN',write,height=48,font_size=13)
    export.pack(fill='x',padx=20,pady=(0,17));window._export_button=export
    guide=tk.Label(window,text=tr(window,'In Rekordbox: Datei → Importieren → Wiedergabeliste importieren → die exportierte .m3u8 wählen.'),bg=PANEL,fg=TEXT,anchor='w',justify='left',wraplength=1080)
    guide.pack(fill='x',padx=20,pady=(0,14))
    def closed(event):
        if event.widget==window:
            cancel.set()
            if getattr(window,'_poll',None):window.after_cancel(window._poll)
    window.bind('<Destroy>',closed)
    refresh();poll();return window
