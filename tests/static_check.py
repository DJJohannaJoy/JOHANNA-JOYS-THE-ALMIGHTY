from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
CODE=ROOT/'APP'
modules=['scanner.py','scanner_core.py','engine_external.py','local_ai.py','ai_method.py','ai_adaptive.py','ui_ai_review.py','ui_first_spark.py','ui_workspace.py','ui_text.py','set_library.py','setup_components.py','audfprint_utf8.py','scan_jobs.py','online_requests.py','track_results.py']
for mod in modules:
    path=CODE/mod
    assert path.is_file(),f'Missing {mod}'
    ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
for mod in ('rekordbox_export.py','ui_rekordbox.py'):
    ast.parse((CODE/mod).read_text(encoding='utf-8'),filename=mod)
assert (ROOT/'design/01_MASTER_MOCKUP_FIRST_SPARK.png').is_file()
assert (ROOT/'design/JOHANNA_JOY_ORIGINAL_LOGO_WEISS.png').is_file()
assert (CODE/'assets/drop_texture_left.png').is_file()
assert (CODE/'assets/drop_texture_right.png').is_file()
assert (CODE/'assets/almighty_icon.png').is_file()
assert (CODE/'assets/almighty_icon.ico').is_file()
print(f'STATIC CHECK OK: {len(modules)} Python modules parse + required design images present.')

assert (CODE/'mixid_probe.mjs').is_file()
