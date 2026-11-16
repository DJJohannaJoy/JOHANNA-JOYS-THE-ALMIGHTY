"""Validated AI identity decisions, with temporal/version guards and all evidence retained."""
import re
from urllib.parse import urlsplit
import track_results as R

_GENERIC=r'(?:original|extended)(?:\s+(?:mix|version))?'

def base_title(track):
    title=R.identity(track)[3]
    title=re.sub(r'[\[(]\s*'+_GENERIC+r'\s*[\])]','',title,flags=re.I)
    title=re.sub(r'\s*[-–—]\s*'+_GENERIC+r'\s*$','',title,flags=re.I)
    return R.normalized(title)

def version(track):
    title=R.identity(track)[3]
    chunks=re.findall(r'[\[(]([^\])]+)[\])]',title)
    chunks += re.findall(r'\s[-–—]\s(.+(?:remix|edit|bootleg|rework|vip|mix))\s*$',title,re.I)
    return tuple(sorted(R.normalized(c) for c in chunks if not re.fullmatch(_GENERIC,c.strip(),re.I)))

def compatible(tracks):
    if len(tracks)<2 or any(t.get('_ai_unconfirmed') for t in tracks):return False
    artists={R.artist_key(R.identity(t)[2]) for t in tracks}
    if len(artists)!=1 or not next(iter(artists)):return False
    titles={base_title(t) for t in tracks}
    if len(titles)!=1 or not next(iter(titles)) or len({version(t) for t in tracks})!=1:return False
    ordered=sorted(tracks,key=lambda t:float(t.get('first_detection',t.get('time',0))))
    end=float(ordered[0].get('last_detection',ordered[0].get('time',0)))
    for t in ordered[1:]:
        first=float(t.get('first_detection',t.get('time',0)))
        if first-end>180:return False
        end=max(end,float(t.get('last_detection',t.get('time',0))))
    return True

def validate_ids(row,answer,verdict):
    ids=answer.get('duplicate_track_ids',[])
    known={t['track_id']:t for t in row['tracks']}
    if not isinstance(ids,list) or any(not isinstance(i,str) or i not in known for i in ids):
        raise RuntimeError('KI-Dubletten enthalten unbekannte Track-IDs')
    ids=list(dict.fromkeys(ids))
    if verdict=='version_conflict' or not str(answer.get('reason','')).strip():return []
    return ids if compatible([known[i] for i in ids]) else []

def catalog_ids(track):
    ids=set()
    for evidence in [track,*track.get('evidence',[])]:
        key=str(evidence.get('catalog_id') or '')
        if re.fullmatch(r'shazam:\d+',key):ids.add(key)
        try:
            url=urlsplit(str(evidence.get('url') or ''))
            if url.scheme=='https' and not url.username and not url.password and (url.hostname or '').lower() in ('shazam.com','www.shazam.com'):
                match=re.match(r'/(track|song)/(\d+)(?:/|$)',url.path)
                if match:ids.add(('shazam:' if match[1]=='track' else 'shazam-song:')+match[2])
        except ValueError:pass
    return ids

def groups(cases,model):
    output=[]
    for case in cases:
        ids=validate_ids(case,{'duplicate_track_ids':case.get('duplicate_track_ids',[]),'reason':case.get('reason','')},case.get('verdict'))
        if len(ids)>1:output.append({'track_ids':ids,'reason':case['reason'],'case_id':case['case_id'],'model':model,'identity_only':True,'decision_origin':'model'})
        # The model's audio uncertainty must not defeat an exact catalogue
        # identity proof. Keep this rule decision separate from its verdict.
        by_catalog={}
        for track in case['tracks']:
            for key in catalog_ids(track):by_catalog.setdefault(key,[]).append(track)
        for key,tracks in by_catalog.items():
            if compatible(tracks):
                proven=[t['track_id'] for t in tracks]
                if not any(set(g['track_ids'])==set(proven) for g in output):
                    output.append({'track_ids':proven,'reason':'Gleicher Katalogeintrag '+key+' und dieselbe Set-Stelle; abweichende Metadaten-Schreibweise.',
                        'case_id':case['case_id'],'model':model,'identity_only':True,'decision_origin':'catalog_identity'})
    return output

def apply_groups(records,decisions):
    out=[{**r,'_members':{r['track_id']}} for r in records]
    for decision in decisions:
        if not isinstance(decision,dict):continue
        ids=decision.get('track_ids',[])
        if not isinstance(ids,list) or any(not isinstance(i,str) for i in ids) or len(set(ids))<2:continue
        ids=set(ids);members=[r for r in out if r['_members']&ids]
        if len(members)<2 or not ids<=set().union(*(r['_members'] for r in members)) or not compatible(members):continue
        ordered=sorted(members,key=lambda r:r['first_detection'])
        # A different intervening track may indicate a genuine later replay.
        if any(a['last_detection']<r['first_detection']<b['first_detection'] for a,b in zip(ordered,ordered[1:]) for r in out if r not in members):continue
        evidence=sorted([ev for m in members for ev in m['evidence']],key=lambda ev:ev['order'])
        leader=min(members,key=lambda m:min(ev['order'] for ev in m['evidence']))
        display=max(members,key=lambda m:(bool(m.get('full_path')),len(m['title'])))
        merged={**leader,'artist':display['artist'],'title':display['title'],
            'time':min(m['time'] for m in members),'first_detection':min(m['first_detection'] for m in members),
            'last_detection':max(m['last_detection'] for m in members),'evidence':evidence,
            'samples':sum(m['samples'] for m in members),'_members':set().union(*(m['_members'] for m in members)),
            'ai_duplicates':[d for m in members for d in m.get('ai_duplicates',[])]+[decision]}
        merged['methods']=list(dict.fromkeys(method for ev in evidence for method in ev['methods']))+['KI · Dublettenprüfung']
        merged['sources']=list(dict.fromkeys(ev['source'] for ev in evidence))
        merged['catalogs']=list(dict.fromkeys(ev['catalog'] for ev in evidence))
        for m in members:
            for key in ('full_path','audio_format','bpm','bpm_estimated','bpm_tag','bpm_suspect'):
                if key in m:merged[key]=m[key]
        merged['source']='offline' if merged.get('full_path') else 'online'
        out=[m for m in out if m not in members]+[merged]
    for number,track in enumerate(sorted(out,key=lambda r:r['time']),1):
        track['number']=number
        members=track.pop('_members')
        if len(members)>1:track['merged_track_ids']=sorted(members)
    return sorted(out,key=lambda r:r['time'])
