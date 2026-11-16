"""Snapshot the chosen set source and parse genuine downloader progress."""
from pathlib import Path
import math

def resolve(local,link,kind,cache,provider):
    path=Path(local) if local else None
    if kind=='file' and path:return (path if path.is_file() else None),''
    if link:
        if not provider(link):raise ValueError('Bitte einen gültigen YouTube-, SoundCloud- oder Mixcloud-Link eingeben.')
        cached=Path(cache[link]) if cache.get(link) else None
        return (cached if cached and cached.is_file() else None),link
    return (path if path and path.is_file() else None),''

def download_progress(line):
    if line.startswith('ALMIGHTY_DOWNLOAD:'):
        fields=line.split(':')
        if len(fields)!=4:return
        def number(value):
            try:n=float(value);return n if math.isfinite(n) and n>=0 else 0
            except (ValueError,TypeError):return 0
        done,total,estimate=map(number,fields[1:]);estimated=not total and bool(estimate);total=total or estimate
        if total:detail=f"Download · {'≈ ' if estimated else ''}{min(100,100*done/total):.1f} % · {done/1048576:.1f} MB"
        else:detail=f'Download · {done/1048576:.1f} MB · Gesamtgröße noch unbekannt'
        return 'setup/download',min(done,total) if total else 0,total,detail
    if line.startswith('ALMIGHTY_PROCESS:'):
        state=line.split(':',1)[1].strip()
        done=1 if state=='finished' else 0
        return 'setup/convert',done,1,'Audio-Verarbeitung abgeschlossen' if done else 'Audio wird verarbeitet …'
