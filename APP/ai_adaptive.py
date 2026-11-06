"""Bounded model-selected follow-up tests. Only enumerated, local tools may run."""
import hashlib,json,time,tempfile,shutil,re
from pathlib import Path
import audio_core as C
import track_results as R

def key(value):return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()

class Deadline:
    def __init__(self,stop,seconds):self.stop=stop;self.end=time.monotonic()+seconds
    def is_set(self):return self.stop.is_set() or time.monotonic()>=self.end
    def wait(self,seconds):
        self.stop.wait(max(0,min(seconds,self.end-time.monotonic())))
        return self.is_set()

def observations(audio):
    if 'observations' in audio:return list(audio['observations'])
    result=[]
    for match in audio.get('matches',[]):
        for position,window in match.get('window_scores',{}).items():
            result.append({**match,'window':float(position),'score':window['score'],'support_seconds':window['support']})
    return result

def summarize(matches,candidates,previous=None,errors=(),trials=()):
    previous=previous or {};all_matches=observations(previous)+matches;by_path={}
    for item in all_matches:
        windows=by_path.setdefault(item['path'],{})
        slot=str(round(float(item['window']),2))
        if item['score']>windows.get(slot,{}).get('score',0):windows[slot]=item
    ranked=[]
    for path,windows in by_path.items():
        independent=[]
        for row in sorted(windows.values(),key=lambda row:-row['score']):
            if all(abs(row['window']-old['window'])>=20 for old in independent):independent.append(row)
        leader=max(windows.values(),key=lambda row:row['score'])
        ranked.append({**leader,'independent_windows':len(independent),
            'window_scores':{p:{'score':w['score'],'support':w['support_seconds']} for p,w in windows.items()},
            'independent_score':sum(w['score'] for w in independent),
            'supported_windows':sum(w['score']>=80 and w['support_seconds']>=8 for w in independent)})
    ranked.sort(key=lambda row:-row['independent_score'])
    sufficient=bool(ranked and (ranked[0]['score']>=180 and ranked[0]['support_seconds']>=8 or ranked[0]['supported_windows']>=2))
    strong=bool(ranked and ranked[0]['path'] in candidates and sufficient and
                (len(ranked)==1 or ranked[0]['independent_score']>=ranked[1]['independent_score']*1.5))
    return {**previous,'state':'strong_local_match' if strong else 'ambiguous' if ranked else 'failed' if errors else 'no_match',
            'matches':ranked,'observations':all_matches,'tested_files':list(candidates),
            'errors':list(previous.get('errors',[]))+list(errors),'adaptive_trials':list(previous.get('adaptive_trials',[]))+list(trials)}

def run_audio(audit,tests,candidates,previous):
    deadline=getattr(audit,'_adaptive_deadline',None)
    remaining=max(1,deadline-time.monotonic()) if deadline else 35
    stop=Deadline(audit.stop,min(35,remaining));matches=[];errors=[];trials=[]
    cache_root=audit.root/'Audio-Proben';cache_root.mkdir(exist_ok=True)
    db_revision=C.DB.stat().st_mtime_ns if C.DB.is_file() else None
    with tempfile.TemporaryDirectory(prefix='almighty-ai-adaptive-') as td:
        root=Path(td);ffmpeg=shutil.which('ffmpeg',path=audit.env['PATH'])
        for i,test in enumerate(tests):
            if stop.is_set():break
            cache=cache_root/(key((audit.file_key,db_revision,{k:test[k] for k in ('position','factor','mode')}))+'.json')
            trial={**test,'status':'pending'}
            try:
                cached=None
                if not audit.cfg.get('ai_force',False):
                    try:cached=json.loads(cache.read_text(encoding='utf-8'))
                    except (OSError,ValueError):pass
                if cached and cached.get('completed') is True:
                    found_rows=cached['matches'];trial['cached']=True
                else:
                    folder=root/str(i);folder.mkdir();part=folder/'part-0000.wav'
                    command=[ffmpeg,'-v','error','-y','-ss',str(test['position']),'-i',str(audit.mix),'-t','20','-vn',
                             '-af','aresample=11025,'+C.mode_args(test['mode'],test['factor']),'-ac','1','-ar','11025','-c:a','pcm_s16le',str(part)]
                    code,text=C.run_cmd(command,audit.env,cancel=stop,idle_timeout=15)
                    if code:raise RuntimeError('Ausschnitt konnte nicht vorbereitet werden')
                    found,warnings=audit.match([part],test['factor'],test['mode'],folder,audit.env,stop,lambda message:None)
                    if warnings:raise RuntimeError(' / '.join(warnings))
                    found_rows=[{'path':str(h.song),'title':Path(h.song).stem,'score':int(h.score),'support_seconds':round(h.support,2),
                                 'factor':test['factor'],'mode':test['mode'],'window':test['position'],
                                 'set_position':round(test['position']+h.time,2)} for h in found]
                    cache.write_text(json.dumps({'completed':True,'matches':found_rows}),encoding='utf-8')
                matches.extend(found_rows);trial['status']='complete';trial['matches']=len(found_rows)
            except Exception as exc:
                if audit.stop.is_set():return {**previous,'state':'cancelled'}
                trial['status']='failed';trial['error']=str(exc)[:250];errors.append(trial['error'])
            trials.append(trial)
    if len(trials)<len(tests):errors.append('Zeitlimit für diese Nachprüfrunde erreicht; restliche Tests nicht ausgeführt')
    return summarize(matches,candidates,previous,errors,trials)

class AdaptiveReview:
    def test_menu(self,row):
        history=row.get('adaptive_history',[])
        spent={t['test_id'] for round_ in history for t in round_.get('tests',[])}
        audio=row.get('audio',{});options=[]
        def add(spec,label):
            identity='test-'+key(spec)[:12]
            if identity not in spent:options.append({'test_id':identity,'label':label,**spec})
        candidates=list(audio.get('tested_files') or [])
        if self.match and C.DB.is_file() and candidates and self.audio_ready.is_set() and self.cfg.get('ai_audio_check',True):
            points=audio.get('positions') or [max(0,float(row['tracks'][0]['time'])+8)]
            first=float(points[0]);new_points=[first,first+25,first+75]
            executed={(round(float(p),2),round(float(f),3),'tempo') for p in audio.get('positions',[]) for f in audio.get('factors',[])}
            executed.update((round(float(t['position']),2),round(float(t['factor']),3),t['mode']) for t in audio.get('adaptive_trials',[]) if t.get('kind')=='audio')
            for offset,position in enumerate(new_points):
                if self.duration:position=min(position,max(0,self.duration-21))
                for mode,factor in [('tempo',.97),('tempo',1.03),('pitch',.97),('pitch',1.03)]:
                    if (round(position,2),round(factor,3),mode) in executed:continue
                    add({'kind':'audio','position':round(position,2),'factor':factor,'mode':mode},
                        f'{C.hhmmss(position)} · {mode} {factor:.2f}× · anderer Tempofaktor' if offset==0 else f'{C.hhmmss(position)} · {mode} {factor:.2f}× · weiterer Ausschnitt')
            for match in audio.get('matches',[]):
                path=match['path']
                if path not in candidates and path in self.library and Path(path).is_file():
                    add({'kind':'reference','path':path},'Weitere tatsächlich gefundene Referenz: '+Path(path).stem)
        if self.cfg.get('ai_web_lookup',True):
            original={(t.get('artist',''),t['title']) for t in row['tracks']}
            for track in row['tracks']:
                title=re.sub(r'[\[(][^\])]*(?:remix|mix|edit|bootleg|vip|version)[^\])]*[\])]','',track['title'],flags=re.I).strip()
                if len(title)>=3 and (track.get('artist',''),title) not in original:
                    add({'kind':'source','artist':track.get('artist',''),'title':title},'Fundstellen ohne Versionszusatz suchen: '+title)
        return options[:18]

    def validate_review(self,row,answer):
        if not isinstance(answer,dict) or answer.get('case_id')!=row['case_id'] or answer.get('verdict') not in ('supported','uncertain','version_conflict') or not isinstance(answer.get('reason'),str):
            raise RuntimeError('Keine gültige KI-Bewertung für '+row['tracks'][0]['title'])
        known={s['source_id'] for s in row.get('sources',[]) if s.get('path') or
               any(R.normalized(R.identity(track)[3].split('(')[0].strip()) in R.normalized(s.get('title','')) for track in row['tracks'])}
        identifiers=answer.get('source_ids',[])
        selected=[s for s in identifiers if isinstance(s,str) and s in known] if isinstance(identifiers,list) else []
        reason=answer['reason'][:1400]
        if 'Ã' in reason or 'Â' in reason:
            try:reason=reason.encode('latin1').decode('utf-8')
            except UnicodeError:pass
        verdict=answer['verdict']
        if row.get('audio',{}).get('state')=='strong_local_match' and row['audio'].get('matches'):
            path=row['audio']['matches'][0]['path']
            reference=R.identity({'title':Path(path).stem,'full_path':path})
            if all(reference[1]!=R.identity(track)[1] for track in row['tracks']):
                verdict='version_conflict'
                reason='Audio-Referenz ist anders benannt: '+Path(path).stem+'. '+reason
        return {**row,'verdict':verdict,'reason':reason,'matched_source_ids':selected}

    def refine_case(self,row,answer,provider,model):
        result=self.validate_review(row,answer);maximum=max(0,min(3,int(self.cfg.get('ai_adaptive_rounds',2))))
        self._adaptive_deadline=time.monotonic()+max(10,min(120,float(self.cfg.get('ai_adaptive_seconds',60))))
        for number in range(maximum):
            if self.stop.is_set():self._adaptive_deadline=None;return result
            if time.monotonic()>=self._adaptive_deadline:result['adaptive_stop']='Nachprüfzeit ausgeschöpft · verbleibende Unsicherheit bleibt sichtbar';break
            if result['audio']['state']=='deferred':break
            if result['verdict']=='supported' and result['audio']['state']=='strong_local_match':
                result['adaptive_stop']='Starker Audiobefund und passende Metadaten';break
            options=self.test_menu(result)
            if not options:result['adaptive_stop']='Keine weiteren ausführbaren Tests mit den vorhandenen Referenzen';break
            allowed={option['test_id']:option for option in options};requested=answer.get('next_test_ids',[])
            chosen=list(dict.fromkeys(t for t in requested if isinstance(t,str) and t in allowed))[:3] if isinstance(requested,list) else []
            selected_by='model'
            if not chosen:
                chosen=[options[0]['test_id']];selected_by='fallback'
            tests=[{**allowed[t],'status':'planned'} for t in chosen]
            self.emit('case_progress',case_id=result['case_id'],done=3+2*number,total=3+2*maximum,
                      detail=result['tracks'][0]['title']+f' · adaptive Nachprüfung {number+1}/{maximum}')
            before=result['verdict'];audio_tests=[];candidates=list(result['audio'].get('tested_files') or [])
            for test in tests:
                if self.stop.is_set():self._adaptive_deadline=None;return result
                if time.monotonic()>=self._adaptive_deadline:break
                if test['kind']=='audio':audio_tests.append(test);test['status']='queued'
                elif test['kind']=='reference':candidates.append(test['path']);test['status']='rechecked_from_fingerprints'
                elif test['kind']=='source':
                    sources,issues=self.source_lookup({'artist':test['artist'],'title':test['title']})
                    result['sources']=list({s['source_id']:s for s in result.get('sources',[])+sources}.values())
                    result['source_issues']=list(dict.fromkeys(result.get('source_issues',[])+issues))
                    test['status']='checked_with_issues' if issues else 'complete'
            if audio_tests:result['audio']=run_audio(self,audio_tests,candidates,result['audio'])
            elif candidates:result['audio']=summarize([],candidates,result['audio'])
            trial_states={t['test_id']:t['status'] for t in result['audio'].get('adaptive_trials',[])}
            for test in tests:
                if test['status']=='queued':test['status']=trial_states.get(test['test_id'],'not_run')
                elif test['status']=='planned':test['status']='not_run'
            if any(t['status'] in ('failed','not_run') for t in tests):result['adaptive_failed']=True
            record={'round':number+1,'selected_by':selected_by,'tests':tests,'before_verdict':before,'audio_state':result['audio']['state']}
            result.setdefault('adaptive_history',[]).append(record)
            result['available_tests']=self.test_menu(result)
            if self.stop.is_set():self._adaptive_deadline=None;return result
            self.emit('case_progress',case_id=result['case_id'],done=4+2*number,total=3+2*maximum,
                      detail=result['tracks'][0]['title']+' · KI bewertet neue Belege')
            try:
                answers=self.judge([result],provider,model)
                answer=next((a for a in answers if isinstance(a,dict) and a.get('case_id')==result['case_id']),None)
                result=self.validate_review(result,answer);record['after_verdict']=result['verdict']
            except Exception as exc:
                result['adaptive_failed']=True;record['error']=str(exc)[:250]
                result['adaptive_stop']='Nachbewertung fehlgeschlagen · Befunde bleiben erhalten';break
        result.pop('available_tests',None)
        self._adaptive_deadline=None
        result.setdefault('adaptive_stop','Nachprüfgrenze erreicht · verbleibende Unsicherheit bleibt sichtbar')
        return result
