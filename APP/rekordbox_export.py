"""Ordered playlists pointing only to real local audio, with explicit unresolved titles."""
from pathlib import Path
from datetime import datetime
from urllib.parse import quote,urlsplit,unquote
import os,json,csv,re,xml.etree.ElementTree as ET
import track_results as R
import set_library as L

EXTENSIONS={'.mp3','.wav','.aif','.aiff','.flac','.fla','.m4a','.mp4','.aac','.alac'}

def identity(track):return R.identity(track)[:2]
def path_key(path):return os.path.normcase(str(Path(path).resolve()))
def file_uri(path):
    uri=Path(path).resolve().as_uri()
    return 'file://localhost/'+uri[len('file:///'):] if uri.startswith('file:///') else uri
def uri_path(uri):
    parsed=urlsplit(uri)
    if parsed.scheme!='file':return None
    value=unquote(parsed.path)
    if parsed.netloc and parsed.netloc!='localhost':value='//'+parsed.netloc+value
    elif re.match(r'^/[A-Za-z]:/',value):value=value[1:]
    return Path(value)

class Resolver:
    def __init__(self,paths=(),xml=None):
        self.index={}
        for path in paths:self.add(path)
        if xml:self.load_xml(xml)
    def add(self,path,artist=None,title=None,mix=''):
        path=Path(path)
        if path.suffix.lower() not in EXTENSIONS:return
        if title and mix and R.normalized(mix) not in R.normalized(title) and R.normalized(mix) not in ('original','originalmix'):
            title+=' ('+mix+')'
        track={'full_path':str(path),'title':title or path.stem,'artist':artist or ''}
        self.index.setdefault(identity(track),{})[path_key(path)]=str(path)
    def load_xml(self,path):
        path=Path(path)
        if path.stat().st_size>100*1024*1024:raise ValueError('Bibliotheks-XML ist zu groß (maximal 100 MB).')
        root=ET.parse(path).getroot()
        if root.tag!='DJ_PLAYLISTS':raise ValueError('Keine Rekordbox-Bibliotheks-XML.')
        for row in root.findall('./COLLECTION/TRACK'):
            path=uri_path(row.get('Location',''))
            if path:self.add(path,row.get('Artist'),row.get('Name'),row.get('Mix',''))
    def resolve(self,tracks,assignments=None):
        assignments=assignments or {};rows=[]
        ordered=sorted(enumerate(tracks),key=lambda pair:(float(pair[1].get('time',0)),pair[0]))
        for number,(_,track) in enumerate(ordered,1):
            chosen=assignments.get(identity(track));hints=[]
            if chosen and (not Path(chosen).is_file() or Path(chosen).suffix.lower() not in EXTENSIONS):
                rows.append({'number':number,'track':dict(track),'state':'missing','path':'','candidates':[],
                             'reason':'Zugewiesene Datei fehlt oder Dateiformat wird nicht unterstützt'})
                continue
            if chosen:hints=[chosen]
            else:
                if track.get('full_path'):hints.append(track['full_path'])
                hints.extend(e.get('path') for e in track.get('evidence',[]) if e.get('path'))
            ready={path_key(p):str(Path(p).resolve()) for p in hints if p and Path(p).is_file() and Path(p).suffix.lower() in EXTENSIONS}
            reason='Zugewiesen' if chosen else 'Erkannte Referenzdatei'
            if not ready:
                ready={k:str(Path(p).resolve()) for k,p in self.index.get(identity(track),{}).items() if Path(p).is_file()}
                reason='Eindeutig in der Bibliothek gefunden'
            state='ready' if len(ready)==1 else 'ambiguous' if ready else 'missing'
            rows.append({'number':number,'track':dict(track),'state':state,'path':next(iter(ready.values())) if len(ready)==1 else '',
                         'candidates':list(ready.values()),'reason':reason if state=='ready' else 'Mehrere Dateien · bitte zuweisen' if ready else 'Audiodatei fehlt'})
        return rows

def write_bundle(destination,name,rows,strict=True):
    """Create a new export folder; never overwrite audio, tags or an existing library."""
    rows=[dict(row) for row in rows]
    if not rows:raise ValueError('Keine erkannten Titel zum Exportieren vorhanden.')
    for row in rows:
        if row['state']=='ready' and (not Path(row['path']).is_file() or Path(row['path']).suffix.lower() not in EXTENSIONS):
            row.update(state='missing',path='',reason='Datei ist nicht mehr verfügbar')
    ready=[r for r in rows if r['state']=='ready'];missing=[r for r in rows if r['state']!='ready']
    if strict and missing:raise ValueError(f'{len(missing)} Audiodateien fehlen oder sind nicht eindeutig zugeordnet.')
    base=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(name)).strip(' .')[:80] or 'Set'
    parent=Path(destination);parent.mkdir(parents=True,exist_ok=True)
    folder=parent/(base+'_Rekordbox_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    suffix=1
    while folder.exists():folder=parent/(base+'_Rekordbox_'+datetime.now().strftime('%Y%m%d_%H%M%S')+f'_{suffix}');suffix+=1
    folder.mkdir()
    playlist=None;xml=None
    if ready:
        playlist=folder/(base+'.m3u8');lines=['#EXTM3U']
        for row in ready:
            track=row['track'];label=((str(track.get('artist') or '')+' - ') if track.get('artist') else '')+track.get('title','')
            label=re.sub(r'[\r\n]',' ',label)
            if '\n' in row['path'] or '\r' in row['path']:raise ValueError('Ungültiger Zeilenumbruch im Dateipfad.')
            lines.extend(['#EXTINF:-1,'+label,row['path']])
        playlist.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        root=ET.Element('DJ_PLAYLISTS',Version='1.0.0');ET.SubElement(root,'PRODUCT',Name='THE ALMIGHTY',Version='1.13',Company='Johanna Joy')
        collection=ET.SubElement(root,'COLLECTION');ids={}
        for row in ready:
            key=path_key(row['path'])
            if key in ids:continue
            ids[key]=str(len(ids)+1);track=row['track']
            ET.SubElement(collection,'TRACK',TrackID=ids[key],Name=str(track.get('title','')),
                          Artist=str(track.get('artist') or ''),Location=file_uri(row['path']))
        collection.set('Entries',str(len(ids)))
        lists=ET.SubElement(root,'PLAYLISTS');node=ET.SubElement(lists,'NODE',Type='0',Name='ROOT',Count='1')
        listing=ET.SubElement(node,'NODE',Type='1',Name=str(name),KeyType='0',Entries=str(len(ready)))
        for row in ready:ET.SubElement(listing,'TRACK',Key=ids[path_key(row['path'])])
        ET.indent(root);xml=folder/(base+'.xml');ET.ElementTree(root).write(xml,encoding='utf-8',xml_declaration=True)
    def csv_file(path,entries):
        with path.open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.writer(stream,delimiter=';');writer.writerow(['Nr','Zeit im Set','Künstler','Titel','Status','Datei',*L.search_links({})])
            for row in entries:
                t=row['track'];writer.writerow([row['number'],t.get('time',0),t.get('artist',''),t.get('title',''),row['reason'],row['path'],*L.search_links(t).values()])
    csv_file(folder/'ALLE_TITEL.csv',rows);csv_file(folder/'FEHLENDE_DATEIEN.csv',missing)
    summary={'name':str(name),'recognized':len(rows),'exported':len(ready),'unresolved':len(missing),
             'complete':not missing,'playlist':str(playlist) if playlist else None,'xml':str(xml) if xml else None,'folder':str(folder)}
    (folder/'EXPORT_STATUS.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'IMPORT_IN_REKORDBOX.txt').write_text(
        f'THE ALMIGHTY · Rekordbox-Export\n{name}\n\n{len(ready)}/{len(rows)} Titel als echte Audiodateien verfügbar.\n'
        +('Vollständige Playlist.\n' if not missing else 'TEILPLAYLIST: Fehlende/mehrdeutige Dateien stehen in FEHLENDE_DATEIEN.csv.\n')
        +'\nImport: In Rekordbox Datei > Importieren > Wiedergabeliste importieren und die .m3u8 auswählen.\n'
        +'English: File > Import > Import Playlist, then choose the .m3u8 file.\n'
        +'Die .xml ist eine zusätzliche Alternative über die Rekordbox-XML-Bibliothek.\n'
        +'Die Reihenfolge entspricht der Set-Trackliste. Originaldateien müssen unter den angegebenen Pfaden erreichbar bleiben.\n'
        +'Es werden keine Audiodateien kopiert oder aus Suchlinks erzeugt. Geschätzte Set-BPM werden nicht auf Originaltitel übertragen.\n',encoding='utf-8-sig')
    return summary
