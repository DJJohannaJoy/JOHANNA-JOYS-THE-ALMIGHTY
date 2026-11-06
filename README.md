# Johanna Joy’s THE ALMIGHTY

**Version 1.13 · EMBER · Windows 64 Bit**

DJ-Sets analysieren, Songs mit ihren Fundstellen zusammenführen und die Trackliste als Playlist für Rekordbox exportieren. Schwarz-rote Oberfläche, deutsche und englische Bedienung.

## Windows-Anwendung

Download unter [Releases](https://github.com/DJJohannaJoy/THE-ALMIGHTY/releases). Das Windows-ZIP vollständig entpacken und **THE_ALMIGHTY.exe** öffnen. Die Ordner **APP** und **runtime** bleiben neben der EXE. Python 3.12, FFmpeg, Node.js und die Scan-Abhängigkeiten werden mitgeliefert.

Eine vorhandene Installation unter `Desktop/SET SCANNER` wird für Datenbank, Einstellungen und Ergebnisse weiterverwendet. Ohne vorhandene Installation liegen die Nutzerdaten im entpackten `APP`-Ordner. Musikdateien und persönliche Scan-Ergebnisse sind kein Bestandteil dieses Repositorys oder der öffentlichen Downloads.

Online-Erkennung benötigt Internet. Die optionale lokale KI benötigt ein separat laufendes LM Studio oder Ollama mit geladenem Modell. Der lokale Fingerprint-Abgleich benötigt eine zuvor eingelesene Musikdatenbank.

## Funktionen

- Schnellscan und Tempo-Abgleich mit audfprint; Tiefenscan 2 mit mix-id und zusätzliche ShazamIO-Proben laufen parallel.
- Begrenzte parallele Online-Anfragen, gemeinsame Dienstlimits, Wiederholungen und gespeicherte erfolgreiche Proben.
- Nummerierte Ergebnisse mit Methoden, Quellen, Dateiformat und BPM. Originale und Remixes bleiben unterscheidbar.
- Einzelne Methoden erneut prüfen, ohne den kompletten Scan zu wiederholen.
- Lokale KI prüft Belege, Versionskonflikte und zusätzliche Audio-Referenzen im Hintergrund. Modellmeinungen ersetzen keine Audio-Nachweise; unklare Fälle bleiben sichtbar.
- KI-Fallzahlen, aktueller Arbeitsschritt, Sekundenanzeige und tatsächliche Teilfortschritte direkt im Hauptfenster.
- Set-Bibliothek, großes Ergebnisfenster, Suchlinks für Soundeo, SoundCloud, YouTube, Beatport und Spotify. Suchlinks sind keine bestätigten Fundstellen.
- Rekordbox-Export als M3U8 und XML: vorhandene lokale Dateien werden zugeordnet; fehlende oder mehrdeutige Dateien bleiben sichtbar. Ein Export erzeugt keine fehlenden Audiodateien.

## Quellprojekt

`APP/`: Anwendung · `tests/`: Prüfungen · `scripts/`: Bauwerkzeuge · `design/`: Referenzgrafiken · `docs/`: Dokumentation.

Die freigegebene Bildvorlage ist `design/01_MASTER_MOCKUP_FIRST_SPARK.png`. Spätere Anpassungen sind im Quellcode und den Änderungsdokumenten enthalten.

Für die Python-Variante unter Windows weiterhin `1_INSTALLIEREN_ODER_AKTUALISIEREN.bat` und danach `2_SET_SCANNER_STARTEN.bat` im installierten Ordner verwenden. Dieser Weg kann fehlende Komponenten nachladen.

## Prüfen und bauen

Mit einer eingerichteten Python-3.12-Umgebung die Tests unter `tests/` ausführen. Die portable Anwendung baut `scripts/build_windows.py`; Details und Prüfumfang stehen in [WINDOWS_PROGRAMM.md](docs/WINDOWS_PROGRAMM.md). Die Windows-EXE benötigt ihre mitgelieferten Ordner; sie ist keine einzelne selbstentpackende Datei.

[KI-Wiederholung und Fortschritt](docs/KI_ANTWORT_WIEDERHOLUNG.md) · [Rekordbox-Export](docs/REKORDBOX_EXPORT.md) · [KI-Hintergrundmethode](docs/KI_HINTERGRUNDMETHODE.md)

Fremdkomponenten behalten ihre jeweiligen Lizenzen. Hinweise stehen im Programm unter `THIRD_PARTY/` und bei den Komponenten selbst.
