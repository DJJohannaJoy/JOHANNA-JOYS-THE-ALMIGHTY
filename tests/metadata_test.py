"""Offline fixtures for format, BPM tags, estimation, cache and online provenance."""
from test_paths import COMPONENTS
from pathlib import Path
import sys,uuid,shutil,json,threading,time,subprocess,wave
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import audio_core as C
import almighty as S

root=Path(__file__).resolve().parent
scratch=root/('metadata-fixture-'+uuid.uuid4().hex);scratch.mkdir()
old_data=C.DATA;C.DATA=scratch/'data'
try:
    sr=11025
    silence=np.zeros(sr*24,dtype=np.float32)
    assert C.estimate_bpm(silence) is None
    for bpm in (80,100,120,128,130,145,160,172):
        signal=silence.copy()
        for beat in np.arange(.4,23.5,60/bpm):
            start=int(beat*sr);n=min(500,len(signal)-start)
            signal[start:start+n]=np.exp(-np.arange(n)/90)*np.sin(2*np.pi*150*np.arange(n)/sr)
        result=C.estimate_bpm(signal)
        assert result is not None and abs(result-bpm)<2,(bpm,result)
        if bpm in (80,120,130,160):
            half=scratch/('half-tag-'+str(bpm)+'.flac');half.write_bytes(b'fixture')
            half_info={'format':{'duration':'24','tags':{'BPM':str(bpm/2)}},'streams':[]}
            replies=[subprocess.CompletedProcess([],0,json.dumps(half_info).encode(),b''),
                     subprocess.CompletedProcess([],0,signal.astype('<f4').tobytes(),b'')]
            with patch.object(C.shutil,'which',return_value='tool'),patch.object(C.subprocess,'run',side_effect=replies):
                corrected=C.track_metadata(half,{'ffmpeg_dir':''})
            assert corrected['bpm_tag']==bpm/2 and corrected['bpm_estimated'] and abs(corrected['bpm']-bpm)<2,corrected
    # A genuine slow pulse must not be blindly doubled when no fast beat is found.
    slow=scratch/'true-60.flac';slow.write_bytes(b'fixture')
    slow_audio=silence.copy()
    for beat in np.arange(.4,23.5,1):
        start=int(beat*sr);n=min(500,len(slow_audio)-start)
        slow_audio[start:start+n]=np.exp(-np.arange(n)/90)*np.sin(2*np.pi*150*np.arange(n)/sr)
    replies=[subprocess.CompletedProcess([],0,json.dumps({'format':{'tags':{'BPM':'60'}}}).encode(),b''),
             subprocess.CompletedProcess([],0,slow_audio.astype('<f4').tobytes(),b'')]
    with patch.object(C.shutil,'which',return_value='tool'),patch.object(C.subprocess,'run',side_effect=replies):
        preserved=C.track_metadata(slow,{'ffmpeg_dir':''})
    assert preserved['bpm']==60 and preserved['bpm_suspect'] and not preserved['bpm_estimated'],preserved
    sample=scratch/'tagged.flac';sample.write_bytes(b'fixture')
    info={'format':{'duration':'60','tags':{'BPM':'145.5'}},'streams':[{'codec_type':'audio'}]}
    output=subprocess.CompletedProcess([],0,json.dumps(info).encode(),b'')
    with patch.object(C.shutil,'which',return_value='tool'),patch.object(C.subprocess,'run',return_value=output) as run:
        value=C.track_metadata(sample,{'ffmpeg_dir':''})
        assert value=={'audio_format':'FLAC','bpm':145.5,'bpm_estimated':False},value
        assert run.call_count==1,'A tagged file unnecessarily underwent audio analysis'
        assert C.track_metadata(sample,{'ffmpeg_dir':''})==value
        assert run.call_count==1,'Cached metadata was recomputed'
    # Real audio extraction: known 145 BPM fixture, no embedded BPM.
    known=scratch/'pulse.wav'
    audio=np.zeros(sr*24,dtype=np.float32)
    for beat in np.arange(.4,23.5,60/145):
        start=int(beat*sr);n=min(500,len(audio)-start)
        audio[start:start+n]=np.exp(-np.arange(n)/90)*np.sin(2*np.pi*150*np.arange(n)/sr)
    with wave.open(str(known),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(sr);f.writeframes((audio*30000).astype('<i2').tobytes())
    desktop=COMPONENTS
    cfg={'ffmpeg_dir':str(desktop/'tools/ffmpeg')}
    actual=C.track_metadata(known,cfg)
    assert actual['audio_format']=='WAV' and actual['bpm_estimated'] and abs(actual['bpm']-145)<2,actual
    tagged=scratch/'half-tempo.flac'
    subprocess.run([str(desktop/'tools/ffmpeg/ffmpeg.exe'),'-v','error','-y','-i',str(known),
                    '-metadata','BPM=72.5',str(tagged)],check=True)
    corrected=C.track_metadata(tagged,cfg)
    assert corrected['bpm_tag']==72.5 and corrected['bpm_estimated'] and abs(corrected['bpm']-145)<2,corrected
    online=C.track_metadata(known,cfg,segment_start=0)
    assert online['audio_format']=='—' and online['bpm_estimated']
    # Main window receives metadata asynchronously and leaves missing data blank.
    app=S.AppGUI();app.cfg.update(cfg);app.root.update()
    try:
        assert tuple(app.result_table['columns'])==('number','time','title','format','bpm','method','source')
        rec={'source':'offline','full_path':str(known),'title':'Pulse','time':0}
        app._render_hits([rec])
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            app.root.update()
            values=app.result_table.item(app.result_table.get_children()[0],'values')
            if values[3]=='WAV' and values[4].startswith('≈'):break
            time.sleep(.02)
        else:raise AssertionError('Background metadata never appeared')
        assert abs(float(values[4][1:])-145)<2,values
        app.current_hits.clear()
        app.raw_hits.clear()
        app._render_hits([{'source':'Shazam','title':'Unknown format','artist':'Artist','time':3}])
        values=app.result_table.item(app.result_table.get_children()[0],'values')
        assert values[3:5]==('—','—'),values
    finally:app.root.destroy()
    print('METADATA OK: BPM fixtures, silence, tags, durable cache, real FFmpeg extraction, online provenance and asynchronous table.')
finally:
    C.DATA=old_data
    shutil.rmtree(scratch)
