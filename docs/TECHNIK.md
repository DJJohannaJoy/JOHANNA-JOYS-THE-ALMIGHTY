# Technology / known limits

Application: Python/Tkinter, graphical elements in `APP/ui_first_spark.py`, orchestration `APP/scanner.py`, main pipeline `APP/scanner_core.py`, external engines `APP/engine_external.py`.

Stage 1: audfprint offline at original tempo; Stage 2: audfprint with tempo/pitch variations; Stage 3: mix-id (it uses Shazam online); Stage 4: ShazamIO for remaining gaps; Stage 5: results written to TXT. These are the intended steps; neither matching accuracy nor complete real-Windows end-to-end behavior has been verified in this handoff.

TrackID (the early separate CLI using AudD/ACRCloud) was intentionally removed: it reported exhausted unauthenticated AudD quota and cannot serve as free offline recognition. Shazam and mix-id share underlying recognition; double-check redundant API use.

LM Studio, Ollama and Llama are not interchangeable: LM Studio and Ollama are software that host models, Llama/Qwen are model families. Local LLM can validate metadata and conflicts but does not know copyrighted tracks by fingerprint without an audio-reference library.

The ZIP contains **source and assets**, not a running Windows venv, full FFmpeg executable, Node distribution, or installed private music database. `APP/setup_components.py` is designed to acquire dependencies during initial setup (Internet needed). Inspect downloads, versions and checksums before production release.

Code and brand assets are here to continue work with the user. Do not publish the user's personal music, credentials, or original logo without their consent.
