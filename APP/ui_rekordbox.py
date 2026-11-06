"""Review file assignments and export the entire recognized playlist in one action."""
import json,tkinter as tk
from tkinter import ttk,filedialog
from pathlib import Path
from ui_workspace import shell
from ui_first_spark import BloodButton,PANEL,FIELD,TEXT,MUTE
from ui_text import tr
import rekordbox_export as E

def show_export(app,tracks,name):
    if not tracks:
        app.progress.set('Noch keine Titel zum Exportieren vorhanden');return
    previous=getattr(app,'rekordbox_window',None)
    if previous is not None and previous.winfo_exists():previous.destroy()
    window=shell(app,'Rekordbox-Export','1150x780');app.rekordbox_window=window
    try:files=json.loads((app.C_DATA/'bibliothek.json').read_text(encoding='utf-8')).get('files',[])
    except (OSError,ValueError):files=[]
    resolver=E.Resolver(files);assignments={};rows=[]
    status=tk.StringVar();message=tk.StringVar()
    tk.Label(window,textvariable=status,bg=PANEL,fg=TEXT,font=('Segoe UI',12,'bold'),anchor='w').pack(fill='x',padx=20,pady=(0,7))
    tk.Label(window,text='Alle erkannten Titel in Set-Reihenfolge. Es werden echte Audiodateien benötigt; Suchlinks reichen nicht.',bg=PANEL,fg=MUTE,anchor='w').pack(fill='x',padx=20,pady=(0,10))
    frame=tk.Frame(window,bg=PANEL);frame.pack(fill='both',expand=True,padx=20)
    style=ttk.Style(window);style.configure('Export.Treeview',background=FIELD,foreground=TEXT,fieldbackground=FIELD,rowheight=30,font=('Segoe UI',10))
    style.configure('Export.Treeview.Heading',background='#252627',foreground=TEXT,font=('Segoe UI',10,'bold'))
    style.map('Export.Treeview',background=[('selected','#812031')],foreground=[('selected',TEXT)])
    table=ttk.Treeview(frame,columns=('number','title','state','path'),show='headings',style='Export.Treeview')
    for key,title,width in [('number','NR.',45),('title','TITEL',360),('state','ZUORDNUNG',245),('path','AUDIODATEI',450)]:table.heading(key,text=title,anchor='w');table.column(key,width=width,stretch=key in ('title','path'))
    frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
    vertical=ttk.Scrollbar(frame,orient='vertical',command=table.yview);horizontal=ttk.Scrollbar(frame,orient='horizontal',command=table.xview)
    table.grid(row=0,column=0,sticky='nsew');vertical.grid(row=0,column=1,sticky='ns');horizontal.grid(row=1,column=0,sticky='ew')
    table.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
    strict=tk.BooleanVar(value=True)
    tk.Checkbutton(window,text='Nur als vollständige Playlist exportieren',variable=strict,command=lambda:refresh(),bg=PANEL,fg=TEXT,selectcolor=FIELD,activebackground=PANEL,activeforeground=TEXT).pack(anchor='w',padx=20,pady=(10,4))
    tk.Label(window,textvariable=message,bg=PANEL,fg=MUTE,wraplength=1100,justify='left',anchor='w').pack(fill='x',padx=20,pady=(0,8))
    actions=tk.Frame(window,bg=PANEL);actions.pack(fill='x',padx=20,pady=(0,16))
    def refresh():
        nonlocal rows
        rows=resolver.resolve(tracks,assignments);chosen=table.selection();selected=chosen[0] if chosen else None
        table.delete(*table.get_children())
        for index,row in enumerate(rows):
            t=row['track'];table.insert('','end',iid=str(index),values=(row['number'],(str(t.get('artist') or '')+' – '+t['title']).strip(' –'),tr(window,row['reason']),row['path'] or ''))
        if selected and table.exists(selected):table.selection_set(selected)
        available=sum(r['state']=='ready' for r in rows)
        status.set(f'{available}/{len(rows)} Audiodateien verfügbar · {len(rows)-available} fehlen oder sind mehrdeutig')
        export.configure(state='normal' if available and (not strict.get() or available==len(rows)) else 'disabled')
    def assign():
        chosen=table.selection()
        if not chosen:return
        row=rows[int(chosen[0])]
        path=filedialog.askopenfilename(parent=window,title=tr(window,'Audiodatei für diesen Titel auswählen'),filetypes=[('Audio','*.mp3 *.wav *.aiff *.aif *.flac *.m4a *.mp4 *.aac')])
        if path:assignments[E.identity(row['track'])]=path;refresh()
    def load_xml():
        path=filedialog.askopenfilename(parent=window,title='Rekordbox XML',filetypes=[('Rekordbox XML','*.xml')])
        if path:
            try:resolver.load_xml(path);message.set('Rekordbox-Bibliothek eingelesen');refresh()
            except Exception as exc:message.set(str(exc))
    def write(partial=False):
        try:
            result=E.write_bundle(app.C_OUTPUT/'Rekordbox-Export',name,rows,strict=False if partial else strict.get())
            message.set(f"{result['exported']}/{result['recognized']} Titel exportiert.\n"+result['folder'])
            window._last_export=result
            app._open(Path(result['folder']))
        except Exception as exc:message.set(str(exc))
    for i,(caption,command) in enumerate([('DATEI ZUWEISEN',assign),('BIBLIOTHEKS-XML LADEN',load_xml),('NEU ZUORDNEN',refresh),('TEILEXPORT / SUCHLISTE',lambda:write(True))]):
        actions.columnconfigure(i,weight=1,uniform='export')
        BloodButton(actions,caption,command,width=180,height=39,font_size=9,outline_only=True).grid(row=0,column=i,sticky='ew',padx=4)
    export=BloodButton(window,'PLAYLIST FÜR REKORDBOX EXPORTIEREN',write,height=48,font_size=13)
    export.pack(fill='x',padx=20,pady=(0,17));window._export_button=export
    refresh();return window
