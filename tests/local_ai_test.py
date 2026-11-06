"""LM Studio model discovery, explicit provider selection and report routing."""
from pathlib import Path
import sys,json,threading,uuid,shutil
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import local_ai as L

calls=[];mode=['v1']
class API(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,data,code=200):
        raw=json.dumps(data).encode();self.send_response(code);self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        calls.append(('GET',self.path))
        if self.path=='/api/v1/models' and mode[0]=='v1':
            return self.reply({'models':[
                {'type':'embedding','key':'embedding','loaded_instances':[{'id':'embedding'}]},
                {'type':'llm','key':'google/gemma','loaded_instances':[{'id':'google/gemma'}]},
                {'type':'llm','key':'other','loaded_instances':[]}]})
        if self.path=='/api/v0/models' and mode[0]=='v0':
            return self.reply({'data':[{'id':'google/gemma','type':'llm','state':'loaded'}]})
        if self.path=='/v1/models' and mode[0]=='compat':return self.reply({'data':[{'id':'google/gemma'}]})
        if self.path=='/api/tags':return self.reply({'models':[{'name':'local-chat'}]})
        return self.reply({},404)
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        calls.append(('POST',self.path,data))
        return self.reply({'choices':[{'message':{'content':'Keine Widersprüche in den gelieferten Befunden.'}}]})
server=ThreadingHTTPServer(('127.0.0.1',0),API)
threading.Thread(target=server.serve_forever,daemon=True).start()
cfg={'local_ai_provider':'LM Studio','local_ai_base_url':f'http://127.0.0.1:{server.server_port}'}
parent=Path(__file__).resolve().parent;scratch=parent/('ai-fixture-'+uuid.uuid4().hex);scratch.mkdir()
try:
    for api in ('v1','v0','compat'):
        mode[0]=api;info=L.inventory(cfg)
        assert info['ready'] and info['model']=='google/gemma'
    mode[0]='v1'
    unavailable=L.inventory({**cfg,'local_ai_model':'other'})
    assert not unavailable['ready'] and 'bitte' in unavailable['info']
    missing=L.inventory({**cfg,'local_ai_model':'not-installed'})
    assert not missing['ready'] and 'nicht gefunden' in missing['info']
    assert not any(c[1]=='/api/tags' for c in calls),'LM Studio silently fell back to Ollama'
    assert L.inventory({**cfg,'local_ai_provider':'Ollama'})['model']=='local-chat'
    report=scratch/'test.txt';report.write_text('00:05 · bekannte Referenz · offline',encoding='utf-8')
    original=report.read_bytes()
    out=L.review_report(report,cfg={**cfg,'local_ai_model':'google/gemma'})
    post=next(c for c in calls if c[0]=='POST')
    assert post[1]=='/v1/chat/completions' and post[2]['model']=='google/gemma'
    assert report.read_bytes()==original and out.is_file()
    exe=scratch/'LM Studio.exe';exe.touch()
    assert L.find_lmstudio({'lmstudio_path':str(exe)})==str(exe)
    for bad in ('https://example.com','http://192.168.1.1:1234','http://localhost@evil.test','http://127.0.0.1.evil.test'):
        try:L.local_base(bad)
        except ValueError:pass
        else:raise AssertionError('Remote endpoint accepted: '+bad)
    print('LOCAL AI OK: LM Studio v1/v0/compatible discovery, loaded vs downloaded, manual path, selected model/provider, local-only report review.')
finally:
    server.shutdown();server.server_close()
    assert scratch.resolve().parent==parent;shutil.rmtree(scratch)
