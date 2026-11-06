"""Local, self-contained set snapshots and explicit platform search links."""
import hashlib,json,os,uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode,quote

def report_paths(output):
    return [p for p in Path(output).glob('*_Tracklist_*.json') if not p.stem.endswith(('_KI_METHODE','_KI_PRUEFUNG'))]

def search_links(track):
    query=' '.join(str(track.get(k,'')).strip() for k in ('artist','title')).strip()
    return {
        'Soundeo':'https://www.google.com/search?'+urlencode({'q':'site:soundeo.com '+query}),
        'SoundCloud':'https://soundcloud.com/search/sounds?'+urlencode({'q':query}),
        'YouTube':'https://www.youtube.com/results?'+urlencode({'search_query':query}),
        'Beatport':'https://www.beatport.com/search?'+urlencode({'q':query}),
        'Spotify':'https://open.spotify.com/search/'+quote(query,safe=''),
    }

def save_snapshot(folder,scan,tracks,source_url='',progress=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    report=str(scan.get('report',''))
    identity=report or str(scan.get('path',''))+'|'+str(scan.get('started_at','current'))
    target=folder/(hashlib.sha256(identity.encode()).hexdigest()[:24]+'.json')
    results=scan.get('results',{})
    payload={'library_version':1,'created':datetime.now().isoformat(timespec='seconds'),
        'file':str(scan.get('path','')),'duration':scan.get('duration',0),'source_report':report,
        'source_url':source_url,'tracks':[{**t,'search_links':search_links(t)} for t in tracks],
        'observations':results.get('observations',[]),'statuses':scan.get('statuses',{}),
        'errors':scan.get('errors',[]),'progress':progress or results.get('progress',{})}
    if results.get('ai_review'):payload['ai_review']=results['ai_review']
    temp=target.with_suffix('.'+uuid.uuid4().hex+'.tmp')
    try:
        temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(temp,target)
    finally:
        if temp.exists():temp.unlink()
    return target

def entries(folder,output,query=''):
    records=[];archived=set();needle=query.casefold().strip()
    for path in sorted(Path(folder).glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)+sorted(report_paths(output),key=lambda p:p.stat().st_mtime,reverse=True):
        try:
            item=json.loads(path.read_text(encoding='utf-8'))
            if 'tracks' not in item:continue
            tracks=item['tracks']
            if not isinstance(tracks,list):continue
            if item.get('library_version'):archived.add(str(item.get('source_report','')))
            elif str(path.with_suffix('.txt')) in archived:continue
            title=Path(item.get('file') or path.stem).stem
            haystack=' '.join([title,item.get('source_url',''),*[str(t.get('artist',''))+' '+str(t.get('title','')) for t in tracks]])
            if needle and needle not in haystack.casefold():continue
            records.append({**item,'entry_path':str(path),'name':title,'count':len(tracks),
                'created':item.get('created') or datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds')})
        except (OSError,ValueError,TypeError,AttributeError):continue
    return sorted(records,key=lambda r:r['created'],reverse=True)
