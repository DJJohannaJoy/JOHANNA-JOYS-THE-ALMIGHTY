from pathlib import Path
import os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import scanner_core as core
env=os.environ.copy()
env['PYTHONIOENCODING']='utf-8'
code,output=core.run_cmd([sys.executable,'-c',"print('Λä🔥')"],env)
assert code==0 and output.strip()=='Λä🔥',repr(output)
print('COMMAND ENCODING OK: Unicode file/track characters preserved across child process output.')
import time
start=time.monotonic()
code,output=core.run_cmd([sys.executable,'-c','import time;time.sleep(10)'],env,idle_timeout=.2)
assert code==124 and 'Zeitlimit' in output and time.monotonic()-start<3
print('PROCESS WATCHDOG OK: silent stalled process terminates within its deadline.')
