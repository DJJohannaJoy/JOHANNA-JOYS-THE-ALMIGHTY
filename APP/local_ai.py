# -*- coding: utf-8 -*-
"""Optional local LLM report review. Does not identify audio or invent tracks.

LM Studio: http://127.0.0.1:1234/v1/chat/completions
Ollama:   http://127.0.0.1:11434/api/chat
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error
import urllib.parse
import os
from pathlib import Path


def request_json(url, payload=None, timeout=4):
    local_base(url)
    headers={'Content-Type':'application/json'}
    body=json.dumps(payload).encode('utf-8') if payload is not None else None
    req=urllib.request.Request(url,data=body,headers=headers,method='POST' if body else 'GET')
    # No proxy or redirect may send a almighty report off this computer.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):return None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    with opener.open(req,timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def local_base(url):
    parsed=urllib.parse.urlsplit(url)
    if (parsed.scheme!='http' or parsed.hostname not in {'localhost','127.0.0.1','::1'}
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('Nur lokale HTTP-Adressen sind erlaubt, z. B. http://127.0.0.1:1234')
    return url.rstrip('/')


def find_lmstudio(cfg=None):
    cfg=cfg or {}
    candidates=[cfg.get('lmstudio_path',''),
        str(Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))/'Programs/LM Studio/LM Studio.exe'),
        str(Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'LM Studio/LM Studio.exe')]
    return next((str(Path(p)) for p in candidates if p and Path(p).is_file()),None)


def downloaded_models():
    root=Path.home()/'.lmstudio/models'
    return sorted({str(p.relative_to(root).parent).replace('\\','/')
                   for p in root.glob('*/*/*.gguf') if 'mmproj' not in p.name.lower()})


def connection(cfg=None):
    cfg=cfg or {};provider=cfg.get('local_ai_provider','LM Studio')
    if provider not in {'LM Studio','Ollama'}:raise ValueError('Unbekannter lokaler KI-Anbieter.')
    base=cfg.get('local_ai_base_url') or ('http://127.0.0.1:1234' if provider=='LM Studio' else 'http://127.0.0.1:11434')
    return provider,local_base(base)


def inventory(cfg=None):
    cfg=cfg or {};provider,base=connection(cfg)
    result={'provider':provider,'base':base,'models':[],'ready':False,'model':None,
            'installed':find_lmstudio(cfg),'downloaded':downloaded_models(),'info':''}
    try:
        if provider=='Ollama':
            data=request_json(base+'/api/tags',timeout=1.5)
            result['models']=[{'id':m['name'],'loaded':None} for m in data.get('models',[]) if m.get('name')]
        else:
            try:
                data=request_json(base+'/api/v1/models',timeout=1.5)
                for m in data['models']:
                    if m.get('type')!='llm':continue
                    loaded=m.get('loaded_instances',[])
                    result['models'].append({'id':loaded[0]['id'] if loaded else m['key'],'loaded':bool(loaded)})
            except (OSError,ValueError,KeyError):
                try:
                    data=request_json(base+'/api/v0/models',timeout=1.5)
                    result['models']=[{'id':m['id'],'loaded':m.get('state')=='loaded'}
                        for m in data['data'] if m.get('type') in {'llm','vlm'}]
                except (OSError,ValueError,KeyError):
                    data=request_json(base+'/v1/models',timeout=1.5)
                    result['models']=[{'id':m['id'],'loaded':None} for m in data.get('data',[])
                                      if m.get('id') and 'embed' not in m['id'].lower()]
        selected=cfg.get('local_ai_model','').strip()
        choices=result['models']
        chosen=next((m for m in choices if m['id']==selected),None) if selected else next((m for m in choices if m['loaded']),choices[0] if choices else None)
        if not chosen:
            result['info']='Gewähltes Modell nicht gefunden' if selected else 'Server erreichbar · kein Chat-Modell verfügbar'
        else:
            result['model']=chosen['id'];result['ready']=chosen['loaded'] is not False
            state='geladen' if chosen['loaded'] else ('verfügbar · Ladestatus unbekannt' if chosen['loaded'] is None else 'vorhanden · bitte in LM Studio laden')
            result['info']=f"{provider}: {chosen['id']} · {state}"
    except (OSError,ValueError,KeyError):
        installed='installiert' if result['installed'] and provider=='LM Studio' else 'nicht erkannt'
        result['info']=f'{provider} {installed} · lokalen Server starten ({base})'
        if result['downloaded'] and provider=='LM Studio':result['info']+=' · vorhanden: '+', '.join(result['downloaded'])
    return result


def detect(cfg=None):
    info=inventory(cfg)
    return (info['provider'] if info['ready'] else None,info['model'],info['info'])


SYSTEM = """Du bist eine Prüf- und Formatierungshilfe für DJ-Set-Tracklists.
Nur Belege aus dem gelieferten Prüfbericht dürfen verwendet werden.
ERFINDE NIEMALS Songtitel, Zeitstempel oder Erkennungsquellen.
Wenn es Widersprüche oder zweifelhafte Matches gibt, markiere sie als unsicher.
Korrigiere keine Namen nach Weltwissen; gib lediglich mögliche Dubletten und auffällige Widersprüche an.
Ausgabe in DEUTSCH mit Rubriken: Bestätigte Befunde, Mögliche Dubletten, Unsichere Treffer, Hinweise zur manuellen Prüfung.
Schreibe keine erfundenen Matches und keine geschätzten Zeiten."""
SYSTEM += """ Verschiedene Titel desselben Künstlers sind KEINE Dubletten.
Mehrere Erkennungsmethoden für denselben Eintrag sind KEIN Widerspruch.
Fasse nur konkrete Auffälligkeiten in höchstens 250 Wörtern zusammen.
Kopiere nicht die vollständige Tracklist. Bestätige keine Audioerkennung."""


def review_report(report_path: Path, max_chars=36000, cfg=None):
    """Write a separate *_KI_PRUEFUNG.txt; NEVER overwrite the scan's evidence."""
    report_path=Path(report_path)
    provider,model,info=detect(cfg)
    if not provider:
        raise RuntimeError('Keine lokale KI bereit: '+info)
    _,base=connection(cfg)
    full=report_path.read_text(encoding='utf-8-sig',errors='replace')
    if not full.strip():
        raise RuntimeError('Ergebnisdatei enthält keinen Text.')
    # Restrict to model's context; disclose truncation instead of fabricating coverage.
    excerpt=full[:max_chars]
    clipped=len(full)>len(excerpt)
    prompt='Prüfe ausschliesslich diesen Prüfbericht. Keine neuen Tracks erzeugen.\n\n'+excerpt
    messages=[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}]
    if provider=='LM Studio':
        data=request_json(base+'/v1/chat/completions',
                {'model':model,'messages':messages,'temperature':0,'max_tokens':2400},timeout=180)
        result=data['choices'][0]['message']['content']
        limited=data['choices'][0].get('finish_reason')=='length'
    else:
        data=request_json(base+'/api/chat',
                {'model':model,'messages':messages,'stream':False,'options':{'temperature':0,'num_predict':2400}},timeout=180)
        result=data['message']['content']
        limited=data.get('done_reason')=='length'
    if not isinstance(result,str) or not result.strip():
        raise RuntimeError('Die lokale KI hat keinen auswertbaren Text zurückgegeben.')
    out=report_path.with_name(report_path.stem+'_KI_PRUEFUNG.txt')
    out.write_text('JOHANNA JOY\'S THE ALMIGHTY · OPTIONALE LOKALE KI-PRÜFUNG\n'
                   f'Backend: {provider} / {model}\n'
                   'KEINE AUDIO-ERKENNUNG. Nur Hinweise zu vorhandenen Treffern.\n'
                   + ('ACHTUNG: Bericht wegen Kontextlänge nur teilweise geprüft.\n' if clipped else '')
                   + ('ACHTUNG: Die KI-Ausgabe wurde vom Modell gekürzt und ist unvollständig.\n' if limited else '')
                   + '\n'+result.strip()+'\n',encoding='utf-8-sig')
    return out
