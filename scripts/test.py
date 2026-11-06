"""Run focused regressions using this interpreter and local bundled components."""
from pathlib import Path
import argparse,json,os,subprocess,sys
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--components',type=Path);a=p.parse_args()
env=os.environ.copy()
if a.components:
    components=a.components.resolve();env['ALMIGHTY_TEST_COMPONENTS']=str(components)
    env['PATH']=str(components/'tools/ffmpeg')+os.pathsep+str(components/'tools/node')+os.pathsep+env.get('PATH','')
tests=sorted(file for file in (root/'tests').glob('*.py') if file.name!='test_paths.py')
for file in tests:subprocess.run([sys.executable,'-X','utf8',str(file)],cwd=root,env=env,check=True)
print(json.dumps({'tests':len(tests),'passed':True}),flush=True)
