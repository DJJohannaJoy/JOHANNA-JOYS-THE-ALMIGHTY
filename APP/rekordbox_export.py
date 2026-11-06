"""Ordered playlists pointing only to real local audio, with explicit unresolved titles."""
from pathlib import Path
from datetime import datetime
from urllib.parse import quote,urlsplit,unquote
import os,json,csv,re,uuid,shutil,xml.etree.ElementTree as ET
import track_results as R
import set_library as L

EXTENSIONS={'.mp3','.wav','.aif','.aiff','.flac','.m4a','.mp4','.aac'}

def identity(track):return R.identity(track)[:2]
def assignment_key(track):return '|'.join(identity(track))
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

class SavedMatches:
    """Private user choices survive closing the export window and later scans."""
    def __init__(self,path):
        self.path=Path(path)
        try:self.value=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.value={}
        if not isinstance(self.value,dict):self.value={}
        if not isinstance(self.value.get('assignments'),dict):self.value['assignments']={}
        if not isinstance(self.value.get('extra_files'),list):self.value['extra_files']=[]
        self.value['assignments']={k:v for k,v in self.value['assignments'].items() if isinstance(k,str) and isinstance(v,str)}
        self.value['extra_files']=[p for p in self.value['extra_files'] if isinstance(p,str)]
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix('.'+uuid.uuid4().hex+'.tmp')
        temporary.write_text(json.dumps(self.value,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(self.path)
    def assignments(self,tracks):
        return {identity(t):self.value['assignments'][assignment_key(t)] for t in tracks if assignment_key(t) in self.value['assignments']}
    def assign(self,track,path):
        key=assignment_key(track)
        if path:self.value['assignments'][key]=str(Path(path).resolve())
        else:self.value['assignments'].pop(key,None)
        self.save()

def music_files(folder,cancel=None):
    """Walk a selected folder without following junctions or requiring audio decoding."""
    result=[]
    for directory,dirs,files in os.walk(folder,followlinks=False):
        if cancel is not None and cancel.is_set():break
        dirs[:]=[d for d in dirs if not Path(directory,d).is_symlink() and not Path(directory,d).is_junction()]
        result.extend(str(Path(directory,name).resolve()) for name in files if Path(name).suffix.lower() in EXTENSIONS)
    return result

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
    """Expose an export only after every file and playlist reference is complete."""
    parent=Path(destination);parent.mkdir(parents=True,exist_ok=True)
    staging=parent/('.rekordbox-'+uuid.uuid4().hex);staging.mkdir()
    try:
        summary=_write_bundle(staging,name,rows,strict)
        folder=Path(summary['folder']);target=parent/folder.name;index=1
        while target.exists():target=parent/(folder.name+'_'+str(index));index+=1
        summary['folder']=str(target)
        for key in ('playlist','xml'):
            if summary[key]:summary[key]=str(target/Path(summary[key]).name)
        # IDs, counts and file URIs must agree before this becomes a visible export.
        if summary['xml']:
            xml=ET.parse(folder/Path(summary['xml']).name).getroot()
            collection=xml.find('COLLECTION');listing=xml.find('./PLAYLISTS/NODE/NODE')
            identifiers={track.get('TrackID') for track in collection}
            assert len(identifiers)==len(collection)==int(collection.get('Entries'))
            assert len(listing)==int(listing.get('Entries'))==summary['exported']
            assert all(track.get('Key') in identifiers for track in listing)
            assert all(uri_path(track.get('Location')).is_file() for track in collection)
        (folder/'EXPORT_STATUS.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        folder.rename(target)
        return summary
    finally:
        assert staging.resolve().parent==parent.resolve() and staging.name.startswith('.rekordbox-')
        shutil.rmtree(staging)

def _write_bundle(destination,name,rows,strict=True):
    """Create a new export folder; never overwrite audio, tags or an existing library."""
    rows=[dict(row) for row in rows]
    if not rows:raise ValueError('Keine erkannten Titel zum Exportieren vorhanden.')
    for row in rows:
        if row['state']=='ready' and (not Path(row['path']).is_file() or Path(row['path']).suffix.lower() not in EXTENSIONS):
            row.update(state='missing',path='',reason='Datei ist nicht mehr verfügbar')
    ready=[r for r in rows if r['state']=='ready'];missing=[r for r in rows if r['state']!='ready']
    if strict and missing:raise ValueError(f'{len(missing)} Audiodateien fehlen oder sind nicht eindeutig zugeordnet.')
    base=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(name)).strip(' .')[:56] or 'Set'
    if base.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:base='Set_'+base
    parent=Path(destination);parent.mkdir(parents=True,exist_ok=True)
    folder=parent/(base+'_Rekordbox_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    suffix=1
    while folder.exists():folder=parent/(base+'_Rekordbox_'+datetime.now().strftime('%Y%m%d_%H%M%S')+f'_{suffix}');suffix+=1
    folder.mkdir()
    playlist=None;xml=None
    if ready:
        export_base=base+(f'_TEILPLAYLIST_{len(ready)}_von_{len(rows)}' if missing else '')
        playlist=folder/(export_base+'.m3u8');lines=['#EXTM3U']
        for row in ready:
            track=row['track'];label=((str(track.get('artist') or '')+' - ') if track.get('artist') else '')+track.get('title','')
            label=re.sub(r'[\r\n]',' ',label)
            if '\n' in row['path'] or '\r' in row['path']:raise ValueError('Ungültiger Zeilenumbruch im Dateipfad.')
            lines.extend(['#EXTINF:-1,'+label,row['path']])
        playlist.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        root=ET.Element('DJ_PLAYLISTS',Version='1.0.0');ET.SubElement(root,'PRODUCT',Name="JOHANNA JOY'S THE ALMIGHTY",Version='1.14',Company='Johanna Joy')
        collection=ET.SubElement(root,'COLLECTION');ids={}
        for row in ready:
            key=path_key(row['path'])
            if key in ids:continue
            ids[key]=str(len(ids)+1);track=row['track']
            ET.SubElement(collection,'TRACK',TrackID=ids[key],Name=str(track.get('title','')),
                          Artist=str(track.get('artist') or ''),Location=file_uri(row['path']))
        collection.set('Entries',str(len(ids)))
        lists=ET.SubElement(root,'PLAYLISTS');node=ET.SubElement(lists,'NODE',Type='0',Name='ROOT',Count='1')
        playlist_name=str(name)+(f' (TEILPLAYLIST – {len(ready)}/{len(rows)})' if missing else '')
        listing=ET.SubElement(node,'NODE',Type='1',Name=playlist_name,KeyType='0',Entries=str(len(ready)))
        for row in ready:ET.SubElement(listing,'TRACK',Key=ids[path_key(row['path'])])
        ET.indent(root);xml=folder/(export_base+'.xml');ET.ElementTree(root).write(xml,encoding='utf-8',xml_declaration=True)
    def csv_file(path,entries):
        with path.open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.writer(stream,delimiter=';');writer.writerow(['Nr','Zeit im Set','Künstler','Titel','Status','Datei',*L.search_links({})])
            for row in entries:
                t=row['track'];seconds=max(0,int(float(t.get('time') or 0)));clock=f'{seconds//3600:02}:{seconds//60%60:02}:{seconds%60:02}'
                writer.writerow([row['number'],clock,t.get('artist',''),t.get('title',''),row['reason'],row['path'],*L.search_links(t).values()])
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
