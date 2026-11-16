from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
CODE=ROOT/'APP'
modules=['almighty.py','audio_core.py','engine_external.py','local_ai.py','ai_method.py','ai_adaptive.py','ui_ai_review.py','ui_theme.py','ui_workspace.py','ui_text.py','set_library.py','components.py','audfprint_utf8.py','scan_jobs.py','online_requests.py','track_results.py']
modules += ['ui_lifetime.py','offline_pipeline.py','duplicates.py']
for mod in modules:
    path=CODE/mod
    assert path.is_file(),f'Missing {mod}'
    ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
for mod in ('rekordbox_export.py','ui_rekordbox.py'):
    ast.parse((CODE/mod).read_text(encoding='utf-8'),filename=mod)
assert (ROOT/'design/01_MASTER_MOCKUP_EMBER.png').is_file()
assert (ROOT/'design/JOHANNA_JOY_ORIGINAL_LOGO_WEISS.png').is_file()
assert (CODE/'assets/drop_texture_left.png').is_file()
assert (CODE/'assets/drop_texture_right.png').is_file()
assert (CODE/'assets/almighty_icon.png').is_file()
assert (CODE/'assets/almighty_icon.ico').is_file()
print(f'STATIC CHECK OK: {len(modules)} Python modules parse + required design images present.')

assert (CODE/'mixid_probe.mjs').is_file()

# The first ICO frame must be large enough for viewers, while Windows retains native sizes.
import struct
from PIL import Image
icon=(CODE/'assets/almighty_icon.ico').read_bytes()
assert struct.unpack_from('<HH',icon)==(0,1) and icon[6:8]==b'\0\0'
with Image.open(CODE/'assets/almighty_icon.ico') as picture:
    assert {(16,16),(20,20),(24,24),(32,32),(40,40),(48,48),(64,64),(96,96),(128,128),(256,256)}==picture.ico.sizes()
    for size in picture.ico.sizes():assert picture.ico.getimage(size).size==size
with Image.open(CODE/'assets/almighty_icon.png') as picture:assert min(picture.size)>=1024
with Image.open(CODE/'assets/johanna_joy_logo.png') as picture:assert picture.mode=='RGBA' and picture.getchannel('A').getextrema()==(0,255)
print('BRAND ASSETS OK: HD master, largest-first ICO with ten genuine sizes and transparent source logo.')
