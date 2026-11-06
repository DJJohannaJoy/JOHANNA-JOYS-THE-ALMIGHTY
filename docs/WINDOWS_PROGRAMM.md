# Windows-Programm 1.13 · EMBER

Die portable Anwendung enthält eine Windows-GUI-EXE mit Anwendungssymbol, eine eigene finale Python-3.12-Laufzeit, Tk/Tkinter, native Python-Abhängigkeiten, audfprint, mix-id, FFmpeg und Node.js. Installiertes Python oder npm ist beim Benutzer nicht erforderlich. Der Start zeigt kein Konsolenfenster.

ZIP vollständig entpacken und `THE_ALMIGHTY.exe` doppelklicken. EXE, `APP/` und `runtime/` bilden zusammen das Programm. Die optionale KI bleibt ein separat laufendes Modell in LM Studio/Ollama.

Existiert `Desktop/SET SCANNER/einstellungen.json`, wird die bisherige Installation als Datenordner weiterbenutzt. Alternativ setzt `ALMIGHTY_DATA_ROOT` einen eigenen Datenordner. Ohne bestehende Installation wird `APP/` benutzt. Persönliche Musik, Datenbanken und Ergebnisse werden nicht mitveröffentlicht.

## Bauen

Windows x64, finale Python-3.12-Umgebung mit `APP/requirements.txt`, vorbereitete Scanner-Komponenten und der mit Windows gelieferte .NET-Framework-C#-Compiler werden benötigt. Die EXE startet den privaten Interpreter. `python312._pth` begrenzt dessen Suchpfade auf mitgelieferte Dateien.

```powershell
python scripts/build_windows.py --components C:\Pfad\SET_SCANNER --node-license licenses/NODE_LICENSE.txt --ffmpeg-notices licenses/ffmpeg --output outputs/THE_ALMIGHTY_1_13_EMBER_Windows
```

Die Komponenten enthalten `engine/audfprint`, `engine/mix-id`, `tools/node/node.exe` und `tools/ffmpeg/{ffmpeg,ffprobe}.exe`. Auf einer neuen Entwicklungsinstallation kann `APP/setup_components.py` diese vorbereiten. Ein neuer Bau benötigt einen neuen Ausgabeordner; vorhandene Builds werden nicht überschrieben.

```powershell
outputs/THE_ALMIGHTY_1_13_EMBER_Windows/THE_ALMIGHTY.exe --self-test C:\Pfad\Pruefbericht.json
```

Dieser Offline-Test startet über die tatsächliche EXE, prüft native Imports, getrennte Laufzeit, FFmpeg/FFprobe/Node, audfprint, mix-id und das echte Tk-Fenster. Er benutzt isolierte Testdaten. Er ersetzt keinen vollständigen Online-Erkennungstest. Laufende Benutzersitzungen werden nicht geschlossen; der neue Stand ist beim nächsten Programmstart aktiv.
