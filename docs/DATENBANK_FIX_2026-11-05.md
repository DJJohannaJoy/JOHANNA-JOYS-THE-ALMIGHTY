# Datenbankaufbau und neue Scan-Beschriftungen

Aktueller Stand: [abgesicherter Aufbau mit Zwischenständen und echter Fortschrittsanzeige](AUFBAU_FORTSCHRITT.md).
Der Laufzeitwechsel allein beseitigte den nativen Engine-Absturz nicht vollständig;
deshalb wird der Aufbau jetzt in isolierten, wiederaufnehmbaren Abschnitten ausgeführt.

Der gemeldete Fehlercode 3221225477 wurde mit der vorhandenen
Python-3.15.0rc3-Umgebung reproduziert. Nach 134 Titeln brach die native
Laufzeit in der audfprint-Routine zur Bildung von Fingerabdruck-Paaren ab.
Der zuletzt bearbeitete Titel funktionierte einzeln; es wird deshalb keine
Musikdatei aufgrund dieses Absturzes als beschädigt markiert oder ausgelassen.

Das Update legt mit dem bereits vorhandenen finalen Python 3.12 eine eigene
Umgebung `.venv_py312` an. Der Startknopf verwendet diese Umgebung. Die frühere
`.venv` und sämtliche Musik-, Einstellungs- und Datenbankdateien bleiben erhalten.
Eine Vorabversion wird bei der automatischen Auswahl abgelehnt. Die
Fingerabdruck-Algorithmen und Originaldateien der Erkennungs-Engine bleiben
unverändert. Das Update ersetzt keine Musikdateien.

Ein- und Ausgabe zwischen Prozessen verwenden ausdrücklich UTF-8, damit auch
Umlaute, griechische Zeichen und andere Sonderzeichen korrekt bleiben.
Die Engine schreibt Fortschritt sofort und aktiviert eine Absturzdiagnose;
ein zukünftiger Fehler liefert dadurch ein brauchbares Protokoll. Eine neue
Datenbank ersetzt die bisherige weiterhin erst nach erfolgreichem Aufbau.

Die Scan-Schritte heißen jetzt:

1. Dateien vorbereiten
2. Schnellscan
3. Tiefenscan 1
4. Tiefenscan 2
5. Shazam
6. Ergebnis speichern

Die Schritte benennen die vorhandenen Abläufe um. Tiefenscan 2 verwendet
weiterhin die optionale mix-id-Integration mit Shazam; diese Online-Nutzung
bleibt in den Einstellungen und Ergebnisquellen erkennbar.

Technische Prüfungen: stabile Laufzeitauswahl, Ablehnung von Vorabversionen,
UTF-8-Prozessausgabe, UI-Bedienung bei drei Fenstergrößen, Paketabhängigkeiten
und tatsächlicher Offline-Test einschließlich aller 20 Tempo-Varianten und
TXT-Ausgabe. Mit der stabilen Laufzeit wurde außerdem eine echte Datenbank
aus den ersten 200 Titeln der vorhandenen Bibliothek erstellt und erneut
geladen: 200 Titel, 2.902.619 Fingerabdrücke, alle Dateinamen erhalten,
kein Absturz. Die vollständige Musiksammlung und Online-Dienste sind
separat von diesen Prüfungen zu beurteilen.
