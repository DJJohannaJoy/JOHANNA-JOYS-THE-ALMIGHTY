"""Inspectable AI findings: model opinions, audio evidence and real source links."""
import tkinter as tk
from tkinter import ttk
import webbrowser
from ui_workspace import shell
from ui_theme import BloodButton,PANEL,FIELD,TEXT,MUTE,HOT
import ai_method as A

def show_findings(app):
    existing=getattr(app,'ai_window',None)
    if existing is not None and existing.winfo_exists():existing.lift();return existing
    window=shell(app,'KI-Nachprüfung','1250x790');app.ai_window=window
    controls=tk.Frame(window,bg=PANEL);controls.pack(fill='x',padx=20,pady=(0,10))
    BloodButton(controls,'NUR KI ERNEUT PRÜFEN',lambda:app.start_ai_method(force=True),width=255,height=40,outline_only=True).pack(side='left')
    state=tk.StringVar();tk.Label(controls,textvariable=state,bg=PANEL,fg=MUTE,anchor='w',wraplength=850).pack(side='left',fill='x',expand=True,padx=15)
    style=ttk.Style(window)
    style.configure('AIReview.Treeview',background=FIELD,foreground=TEXT,fieldbackground=FIELD,rowheight=30,font=('Segoe UI',10))
    style.configure('AIReview.Treeview.Heading',background='#252627',foreground=TEXT,font=('Segoe UI',10,'bold'))
    style.map('AIReview.Treeview',background=[('selected','#812031')],foreground=[('selected',TEXT)])
    table=ttk.Treeview(window,columns=('name','verdict','audio','sources'),show='headings',height=9,style='AIReview.Treeview')
    for key,caption,width in [('name','TITEL / VERSION',470),('verdict','KI-BEWERTUNG',200),('audio','AUDIO-PRÜFUNG',210),('sources','FUNDSTELLEN',110)]:table.heading(key,text=caption,anchor='w');table.column(key,width=width,stretch=key=='name')
    table.pack(fill='x',padx=20)
    body=tk.Frame(window,bg=PANEL);body.pack(fill='both',expand=True,padx=20,pady=12)
    detail=tk.Text(body,bg=FIELD,fg=TEXT,wrap='word',font=('Segoe UI',11),relief='flat',padx=12,pady=12)
    scroll=ttk.Scrollbar(body,orient='vertical',command=detail.yview);scroll.pack(side='right',fill='y');detail.configure(yscrollcommand=scroll.set);detail.pack(fill='both',expand=True)
    rows={};last=[None]
    def show_case(event=None):
        chosen=table.selection();case=rows.get(chosen[0]) if chosen else None
        detail.configure(state='normal');detail.delete('1.0','end')
        if case:
            detail.insert('end','KI-Einschätzung\n'+case['reason']+'\n\nAudio-Befund (Fingerprint, unabhängig vom Sprachmodell)\n')
            if case.get('review_error'):detail.insert('end','KI-Prüfung unvollständig: '+case['review_error']+'\n\n')
            audio=case.get('audio',{});detail.insert('end',audio.get('reason') or audio.get('state','Nicht geprüft'))
            for hit in audio.get('matches',[]):detail.insert('end',f"\n{hit['title']} · {hit['score']} Hashes · {hit['support_seconds']} s · Tempo {hit['factor']:.2f}×")
            for error in audio.get('errors',[]):detail.insert('end','\n'+str(error))
            if case.get('adaptive_history'):
                detail.insert('end','\n\nAdaptive Nachprüfungen\n')
                for round_ in case['adaptive_history']:
                    detail.insert('end',f"\nRunde {round_['round']} · Auswahl: {'KI' if round_['selected_by']=='model' else 'automatische Rückfallauswahl'}\n")
                    for test in round_['tests']:detail.insert('end','• '+test['label']+' · '+test.get('status','ausgeführt')+'\n')
                    detail.insert('end',round_.get('error') or f"Neuer Befund: {round_.get('after_verdict','offen')}\n")
                detail.insert('end',case.get('adaptive_stop','')+'\n')
            detail.insert('end','\n\nAbgeglichene Fundstellen (Metadaten, keine Audio-Bestätigung)\n')
            for i,source in enumerate(case.get('sources',[])):
                matched=source.get('source_id') in case.get('matched_source_ids',[])
                detail.insert('end',('\n✓ KI hält diese Fundstelle für passend: ' if matched else '\nKandidat: ')+source.get('provider','')+' · '+source.get('title','')+'\n')
                url=source.get('url','')
                if A.safe_source(url):
                    tag='link'+str(i);detail.insert('end',url+'\n',tag);detail.tag_configure(tag,foreground='#FF5365',underline=True)
                    detail.tag_bind(tag,'<Button-1>',lambda e,u=url:webbrowser.open(u))
                elif source.get('path'):detail.insert('end',source['path']+'\n')
            for issue in case.get('source_issues',[]):detail.insert('end','\nNicht verfügbar: '+str(issue))
            detail.insert('end','\n\nOriginale und Remixes werden durch diese Bewertung nicht automatisch umbenannt oder zusammengeführt.')
        else:detail.insert('end','Die KI prüft neue Erkennungen im Hintergrund. Ihre Befunde erscheinen hier.\nEin Audio-Befund entsteht nur durch einen echten Vergleich mit lokalen Referenzdateien.')
        detail.configure(state='disabled')
    table.bind('<<TreeviewSelect>>',show_case)
    verdicts={'supported':'Name durch Belege gestützt','uncertain':'Unklar','version_conflict':'Versionskonflikt'}
    audio_states={'strong_local_match':'Starker lokaler Treffer','ambiguous':'Mehrdeutig','no_match':'Kein Fingerprint-Treffer','not_tested':'Referenz fehlt','deferred':'Wartet auf Offline-Engine','failed':'Prüffehler'}
    def update():
        if not window.winfo_exists():return
        status=app.stage_status.get('KI',{});state.set(status.get('detail','Noch nicht gestartet'))
        cases=app._ai_findings.get('cases',[]);signature=repr(cases)
        if signature!=last[0]:
            selected=table.selection();identity=rows.get(selected[0],{}).get('case_id') if selected else None
            table.delete(*table.get_children());rows.clear()
            for case in cases:
                name=' / '.join((str(t.get('artist') or '')+' – '+t['title']).strip(' –') for t in case['tracks'])
                audio=case.get('audio',{}).get('state','not_tested')
                row=table.insert('','end',values=(name,'Prüfung unvollständig' if case.get('adaptive_failed') else verdicts.get(case['verdict'],case['verdict']),audio_states.get(audio,audio),len(case.get('matched_source_ids',[]))))
                rows[row]=case
                if case['case_id']==identity:table.selection_set(row)
            last[0]=signature;show_case()
        window.after(500,update)
    update();return window
