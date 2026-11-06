# JOHANNA JOY'S THE ALMIGHTY

**Version 1.14.1 · EMBER · Windows x64**

Shazam verarbeitet auch nach mehreren Zeitüberschreitungen alle übrigen Ausschnitte. Fehlgeschlagene Proben werden anschließend automatisch erneut geprüft; erfolgreiche Antworten bleiben gespeichert. Dienstfehler werden mit Verarbeitungsschritt angezeigt und nicht als „kein Treffer“ gespeichert. Shazams Anfragelimit wird automatisch berücksichtigt.

[Fertiges Programm herunterladen](https://github.com/DJJohannaJoy/JOHANNA-JOYS-THE-ALMIGHTY/releases/latest)

ZIP vollständig entpacken und **JOHANNA JOY'S THE ALMIGHTY.exe** öffnen. Die mitgelieferte eigene Python-3.12-Version und alle benötigten Python-Bibliotheken, FFmpeg, Node.js, audfprint und mix-id sind enthalten. Das Programm benötigt kein systemweit installiertes Python.

## Programmordner

```text
JOHANNA JOY'S THE ALMIGHTY/
├── JOHANNA JOY'S THE ALMIGHTY.exe
├── APP/       Anwendung, Bilder und Erkennungs-Engines
├── runtime/   eigene Python-Version und Bibliotheken
├── Daten/     persönliche Einstellungen, Musikindex, Sets und Ergebnisse
├── licenses/  Lizenzen der mitgelieferten Komponenten
├── README.txt
└── VERSION.json
```

Alle persönlichen Daten bleiben im Programmordner. `APP`, `runtime` und `licenses` gehören zur Anwendung. Externe Musikdateien bleiben an ihrem ursprünglichen Ort. Die optionale lokale KI verwendet ein separat laufendes LM Studio/Ollama mit geladenem Modell.

## Funktionen

Paralleler Schnellscan, Tempo-Abgleich, mix-id und ShazamIO; nummerierte Ergebnisse mit Quellen, Methoden, Format und BPM; Wiederholung einzelner Methoden; eigenständige KI-Nachprüfung; Set-Bibliothek; gespeicherte Spaltenbreiten; Rekordbox-Export als M3U8/XML mit dauerhaften Dateizuordnungen.

## Quellprojekt

`APP/` enthält den aktuellen Programmcode, `tests/` die Funktionsprüfungen, `scripts/` Bau- und Prüfwerkzeuge, `docs/` die aktuelle Anleitung und `design/` die freigegebene Vorlage sowie die Original-Logos. Frühere Versionen bleiben über die Git-Historie abrufbar.

Große Laufzeitdateien und das vollständige startbare Windows-Paket stehen unter **Releases**. Musikdateien, Datenbanken, Einstellungen und private Ergebnisse werden nicht veröffentlicht.

```powershell
python scripts/test.py --components "C:\Pfad\JOHANNA JOY'S THE ALMIGHTY\APP"
python scripts/build_windows.py --components "C:\Pfad\JOHANNA JOY'S THE ALMIGHTY\APP"
```

Die Startdatei wird mit dem Windows-.NET-Framework-Compiler erstellt. Der vollständige Programmordner enthält die private Laufzeit; die EXE wird zusammen mit diesen Ordnern weitergegeben.

[Bedienung](docs/BEDIENUNG.md) · [Rekordbox-Export](docs/REKORDBOX_EXPORT.md) · [KI-Nachprüfung](docs/KI_HINTERGRUNDMETHODE.md)
