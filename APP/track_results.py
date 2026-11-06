"""One chronological tracklist shared by the UI and exports."""
from __future__ import annotations
import hashlib
import re
import unicodedata
from pathlib import Path


def normalized(value):
    value=unicodedata.normalize('NFKD',str(value)).casefold()
    return ''.join(c for c in value if c.isalnum() and not unicodedata.combining(c))


def identity(item):
    artist=str(item.get('artist') or '').strip()
    title=str(item.get('title') or '').strip()
    if item.get('full_path') and not artist:
        title=re.sub(r'^\d{1,3}[. _-]+','',title)
        parts=re.split(r'\s+[-–—]\s+',title,maxsplit=1)
        if len(parts)==2:artist,title=parts
    # "Original Mix" is an alias; every other remix/edit/version remains part
    # of the identity, so an original and a remix never merge by substring.
    title=re.sub(r'[\[(]\s*original(?:\s+(?:mix|version))?\s*[\])]','',title,flags=re.I).strip()
    return normalized(artist),normalized(title),artist,title


def evidence(item):
    source=str(item.get('source') or 'Unbekannt')
    if source.casefold()=='offline':
        factor=float(item.get('factor',1))
        method='Schnellscan · Originaltempo' if abs(factor-1)<.001 else f"Tiefenscan · {item.get('mode','tempo')} {factor:.2f}×"
        methods=item.get('methods') or [method]
        detail='audfprint · '+Path(item.get('full_path') or item.get('title','')).name
        catalog='Lokale Musikdatenbank'
    else:
        methods=[source if source.lower()!='shazam' else 'ShazamIO']
        detail='Shazam-Katalog · '+('mix-id' if source.lower()=='mix-id' else 'ShazamIO')
        catalog='Shazam'
    return {'time':float(item.get('time',0)),'methods':list(methods),'source':detail,
            'catalog':catalog,'path':item.get('full_path',''),'url':item.get('url',''),
            'order':item.get('_observed_order',item.get('_received_order',0))}


def merge_records(observations, max_gap=180):
    """Merge continuous observations, preserving distinct later plays/versions.

    A new observation may extend a cluster using its most recent detection,
    rather than always comparing with the first timestamp of a long track.
    """
    groups=[]
    for serial,raw in enumerate(observations):
        if not raw.get('title'):continue
        item=dict(raw);a,t,artist,title=identity(item)
        first=float(item.get('first_detection',item.get('time',0)))
        last=float(item.get('last_detection',item.get('last_seen',first)))
        if last<first:last=first
        item['_identity']=(a,t);item['_artist']=artist;item['_title']=title
        item['_first']=first;item['_last']=last;item['_serial']=serial
        groups.append(item)
    clusters=[]
    for item in sorted(groups,key=lambda x:(x['_first'],x['_serial'])):
        a,t=item['_identity'];candidate=None
        for cluster in reversed(clusters):
            if cluster['identity'][1]!=t:continue
            if a and cluster['identity'][0] and a!=cluster['identity'][0]:continue
            if item['_first']-cluster['last_detection']>max_gap:continue
            # An intervening different track separates two plays even when
            # their timestamps happen to be near each other.
            intervening=any(c is not cluster and c['identity'][1]!=t
                and cluster['last_detection']<c['first_detection']<item['_first'] for c in clusters)
            if not intervening:candidate=cluster;break
        ev=evidence(item)
        if candidate is None:
            candidate={**item,'artist':item['_artist'],'title':item['_title'],
                'identity':(a,t),'first_detection':item['_first'],'last_detection':item['_last'],
                'observations':[],'evidence':[],'samples':0}
            clusters.append(candidate)
        candidate['observations'].append(item)
        candidate['evidence'].append(ev)
        candidate['first_detection']=min(candidate['first_detection'],item['_first'])
        candidate['last_detection']=max(candidate['last_detection'],item['_last'])
        candidate['time']=min(float(candidate.get('time',0)),float(item.get('time',0)))
        if not candidate.get('artist') and item['_artist']:candidate['artist']=item['_artist']
        if item.get('full_path'):candidate['full_path']=item['full_path']
        candidate['samples']+=int(item.get('samples',1))
        for key in ('audio_format','bpm','bpm_estimated','bpm_tag','bpm_suspect'):
            if key in item:candidate[key]=item[key]
    output=[]
    for number,cluster in enumerate(sorted(clusters,key=lambda x:x['time']),1):
        evs=sorted(cluster['evidence'],key=lambda e:e['order'])
        methods=[];sources=[];catalogs=[]
        for ev in evs:
            for method in ev['methods']:
                if method not in methods:methods.append(method)
            if ev['source'] not in sources:sources.append(ev['source'])
            if ev['catalog'] not in catalogs:catalogs.append(ev['catalog'])
        anchor=min(e['order'] for e in evs)
        cluster.update(number=number,methods=methods,sources=sources,catalogs=catalogs,
            evidence=evs,source='offline' if cluster.get('full_path') else 'online',
            track_id=hashlib.sha256(repr((cluster['identity'],anchor)).encode()).hexdigest()[:20])
        for key in ('_identity','_artist','_title','_first','_last','_serial','observations'):cluster.pop(key,None)
        output.append(cluster)
    return output
