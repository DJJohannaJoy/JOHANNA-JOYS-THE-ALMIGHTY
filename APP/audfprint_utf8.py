# -*- coding: utf-8 -*-
"""UTF-8 list-file wrapper; audfprint upstream sources are copied unmodified."""
from __future__ import annotations
from pathlib import Path
import sys
import faulthandler
import json
import os
import gzip
import pickle
import subprocess
import random

if os.name=='nt':
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x0001|0x0002)

faulthandler.enable()
if hasattr(sys.stdout,'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8',errors='replace',line_buffering=True)

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "engine" / "audfprint"
sys.path.insert(0, str(UPSTREAM))
import audfprint  # noqa: E402


def utf8_iterator(filelist, wavdir, wavext, listflag):
    query_progress=len(sys.argv)>1 and sys.argv[1]=='match' and '--ncores' not in sys.argv
    completed=0
    if not listflag:
        for f in filelist:
            yield str(Path(wavdir) / (f + wavext)) if wavdir else f + wavext
            completed+=1
            if query_progress:print('QUERY_DONE '+str(completed),flush=True)
    else:
        for listfilename in filelist:
            with open(listfilename, "r", encoding="utf-8-sig") as stream:
                for raw in stream:
                    f = raw.rstrip("\r\n")
                    if f:
                        yield str(Path(wavdir) / (f + wavext)) if wavdir else f + wavext
                        completed+=1
                        if query_progress:print('QUERY_DONE '+str(completed),flush=True)


audfprint.filename_list_iterator = utf8_iterator


def read_mono(filename,sr=None,channels=None):
    """Identical signed-16-bit FFmpeg PCM, without thousands of queue transfers."""
    import numpy as np
    if channels!=1 or sr is None:raise ValueError('Index decoder expects mono and an explicit sample rate.')
    flags={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    result=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-threads','1',
        '-i',str(filename),'-f','s16le','-ac','1','-ar',str(sr),'-threads','1','-'],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,**flags)
    if not result.stdout:raise OSError('Keine Audiodaten: '+str(filename))
    return np.frombuffer(result.stdout,dtype='<i2').astype(np.float32)*(1./32768),sr


def cache_batch(manifest):
    """Small disposable analysis worker. Each track is committed independently."""
    import audfprint_analyze as analyze
    analyze.audio_read.audio_read=read_mono
    engine=analyze.Analyzer()
    original=engine.peaks2landmarks
    # Same integer coordinates, fewer NumPy scalar calls in the pairing hot loop.
    engine.peaks2landmarks=lambda peaks:original([(int(t),int(f)) for t,f in peaks])
    for entry in json.loads(Path(manifest).read_text(encoding='utf-8')):
        target=Path(entry['cache'])
        try:
            size=target.stat().st_size
            with target.open('rb') as stream:valid=size>=16 and (size-16)%8==0 and stream.read(16)==b'audfprinthashV00'
        except OSError:valid=False
        if not valid:
            hashes=engine.wavfile2hashes(entry['source'])
            temp=target.with_name(target.name+f'.{os.getpid()}.tmp')
            target.parent.mkdir(parents=True,exist_ok=True)
            analyze.hashes_save(str(temp),hashes)
            temp.replace(target)
        print('CACHE_DONE '+entry['key'],flush=True)


def merge_cache(manifest,output):
    """Combine cached fingerprints once, keeping the original audio filenames."""
    import audfprint_analyze as analyze
    import hash_table
    data=json.loads(Path(manifest).read_text(encoding='utf-8'))
    table=hash_table.HashTable(data['base']) if data.get('base') else hash_table.HashTable(maxtime=1<<16)
    table.params['samplerate']=11025
    values=memoryview(table.table).cast('B').cast('I')
    counts=memoryview(table.counts).cast('B').cast('i')
    mask=(1<<table.hashbits)-1;timemask=(1<<table.maxtimebits)-1
    depth=table.depth
    for i,entry in enumerate(data['entries'],1):
        # Same reservoir insertion as HashTable.store, using Python integers
        # instead of millions of temporary NumPy scalar objects.
        identifier=table.name_to_id(entry['source'],add_if_missing=True)
        payload=Path(entry['cache']).read_bytes()
        if payload[:16]!=b'audfprinthashV00' or (len(payload)-16)%8:raise ValueError('Invalid fingerprint cache')
        hashes=memoryview(payload)[16:].cast('i')
        idvalue=(identifier+1)<<table.maxtimebits
        for pos in range(0,len(hashes),2):
            hash_=hashes[pos+1]&mask;count=counts[hash_]
            slot=count if count<depth else random.randint(0,count)
            if slot<depth:values[hash_*depth+slot]=idvalue+(hashes[pos]&timemask)
            counts[hash_]=count+1
        table.hashesperid[identifier]+=len(hashes)//2
        table.dirty=True
        if i%16==0 or i==len(data['entries']):print('MERGE_DONE '+str(i),flush=True)
    # Same gzip/pickle format as upstream, compressed once at a faster level.
    with gzip.open(output,'wb',compresslevel=1) as stream:
        pickle.dump(table,stream,pickle.HIGHEST_PROTOCOL)
    print('MERGE_SAVED',flush=True)


if __name__ == "__main__":
    if len(sys.argv)==3 and sys.argv[1]=='--cache-batch':cache_batch(sys.argv[2])
    elif len(sys.argv)==4 and sys.argv[1]=='--merge-cache':merge_cache(sys.argv[2],sys.argv[3])
    else:audfprint.main([str(UPSTREAM / "audfprint.py")] + sys.argv[1:])
