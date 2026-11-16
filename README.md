# JOHANNA JOY'S THE ALMIGHTY

**Version 3.00 · IGNITION · Windows x64**

Datei oben auswählen oder Link unten einfügen und einmal **SCANNEN** drücken: Das Set wird automatisch geladen und verarbeitet, anschließend von den parallelen Methoden erkannt und von der lokalen KI nachgeprüft. Echte Download- und Verarbeitungsschritte erscheinen im Fortschritt. Die zuletzt gewählte Quelle hat Vorrang; bereits geladene Links werden bei Einzelprüfungen wiederverwendet.

Google Song Search ist als eigene parallele Methode eingebaut. Auf diesem PC ist der getestete Zugang eingerichtet. Bei der öffentlichen ZIP wird eine separate Zugangsdatei unter **Einstellungen → GOOGLE-ZUGANG IMPORTIEREN** benötigt. [Google einrichten](docs/GOOGLE_SETUP_EINFACH.md).

Schnellscan und Tiefenscan beginnen mit dem ersten fertig dekodierten Abschnitt. MIX-ID, Shazam, Google und die KI laufen unabhängig daneben. MIX-ID und Shazam teilen sich fair das Anfragebudget ihres gemeinsamen Dienstes; Google verwendet eine eigene Anfrageverteilung. Der Tiefenscan zeigt den Fortschritt pro Schnipsel statt erst nach einer ganzen Tempo-Variante. Die KI-Nachprüfung führt abgesicherte Dubletten zusammen; Quellen, Methoden und rohe Beobachtungen bleiben erhalten. Unterschiedliche Remixes und spätere erneute Abspielungen bleiben getrennt.

Stabilitätskorrektur 1.14.5: Shazams native Fingerabdruckberechnung läuft in einem getrennten Prozess. Die zyklische Speicherbereinigung wird durch das Hauptfenster gesteuert; der periodische Sprachabgleich liest den Python-Fensterbaum statt Tcl rekursiv abzufragen. Die Bereinigung von Fensterobjekten bleibt auch während paralleler Scans und KI-Prüfungen im Oberflächenthread. Native Abstürze werden mit Zeitstempel, Fehlercode und Python-Stack protokolliert.

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

Alle persönlichen Daten bleiben im Programmordner. `APP`, `runtime` und `licenses` gehören zur Anwendung. Externe Musikdateien bleiben an ihrem ursprünglichen Ort. Die optionale lokale KI verwendet ein separat laufendes LM Studio mit geladenem Modell.

## Funktionen

Paralleler Schnellscan, Tempo-Abgleich, MIX-ID, ShazamIO und Google Song Search; nummerierte Ergebnisse mit Quellen, Methoden, Format und BPM; Wiederholung einzelner Methoden; eigenständige KI-Nachprüfung; Set-Bibliothek; gespeicherte Spaltenbreiten; Rekordbox-Export als M3U8/XML mit dauerhaften Dateizuordnungen.

## Quellprojekt

`APP/` enthält den aktuellen Programmcode, `tests/` die Funktionsprüfungen, `scripts/` Bau- und Prüfwerkzeuge, `docs/` die aktuelle Anleitung und `design/` die freigegebene Vorlage sowie die Original-Logos. Frühere Versionen bleiben über die Git-Historie abrufbar.

Große Laufzeitdateien und das vollständige startbare Windows-Paket stehen unter **Releases**. Musikdateien, Datenbanken, Einstellungen und private Ergebnisse werden nicht veröffentlicht.

```powershell
python scripts/test.py --components "C:\Pfad\JOHANNA JOY'S THE ALMIGHTY\APP"
python scripts/build_windows.py --components "C:\Pfad\JOHANNA JOY'S THE ALMIGHTY\APP"
```

Die Startdatei wird mit dem Windows-.NET-Framework-Compiler erstellt. Der vollständige Programmordner enthält die private Laufzeit; die EXE wird zusammen mit diesen Ordnern weitergegeben.

[Bedienung](docs/BEDIENUNG.md) · [Rekordbox-Export](docs/REKORDBOX_EXPORT.md) · [KI-Nachprüfung](docs/KI_HINTERGRUNDMETHODE.md)
