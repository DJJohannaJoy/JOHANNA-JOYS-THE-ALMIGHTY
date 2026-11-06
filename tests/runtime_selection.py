"""Select the actual installed stable runtime; reject preview/interpreter mismatches."""
from pathlib import Path
import subprocess,sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'APP'))
import components as setup

for response,expected in [('[3,12,"final"]',True),('[3,15,"candidate"]',False),
                          ('[3,12,"candidate"]',False),('[3,15,"final"]',False)]:
    with patch.object(setup.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout=response)):
        assert setup.stable_python('python.exe') is expected
runtime=setup.find_stable_python()
assert setup.stable_python(runtime)
assert setup.RUNTIME.name=='runtime'
print('RUNTIME SELECTION OK: preview versions rejected; installed stable Python 3.12 selected.')
import almighty as S
from types import SimpleNamespace
preview=SimpleNamespace(major=3,minor=15,releaselevel='candidate')
with patch.object(S.sys,'version_info',preview),patch.object(S.Path,'is_file',return_value=True), \
     patch.object(S.subprocess,'run',return_value=subprocess.CompletedProcess([],0,stdout='True\n')), \
     patch.object(S.subprocess,'Popen') as spawn:
    assert S.relaunch_stable_runtime()
    args=spawn.call_args.args[0]
    assert 'runtime' in args[0] and args[1].endswith('almighty.py')
with patch.object(S.subprocess,'Popen') as spawn:
    assert not S.relaunch_stable_runtime()
    spawn.assert_not_called()
launcher=(Path(__file__).resolve().parents[1]/'scripts/AlmightyLauncher.cs').read_text()
assert 'Path.Combine(home,"Daten")' in launcher and 'Path.Combine(home,"runtime")' in launcher
print('BUNDLED START OK: GUI uses the private stable runtime and its own data folder.')
