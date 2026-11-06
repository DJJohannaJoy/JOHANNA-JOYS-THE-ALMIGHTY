# Format und BPM · 05.11.2026

Die Trefferliste zeigt NR., ZEIT, TITEL, FORMAT, BPM, METHODE und QUELLE.
Bei lokalen Referenzdateien wird das Dateiformat angezeigt. Vorhandene
BPM-Tags werden bevorzugt; andernfalls wird ein maximal 40 Sekunden langer
Ausschnitt lokal analysiert. Geschätzte Werte tragen ≈. Halbes/doppeltes Tempo
und andere Schätzabweichungen bleiben möglich. Ohne belastbaren Wert steht —.
Tags unter 90 BPM werden am Audio überprüft. Zum Beispiel kann ein 72,5-BPM-Tag
bei einem tatsächlichen 145-BPM-Signal korrigiert werden. Der ursprüngliche
Tag wird für die Detailansicht erhalten; die Originaldatei wird nicht geändert.
Wenn keine Schätzung möglich ist, wird ein fraglicher Tag mit ? gekennzeichnet.

Online gefundene Titel verraten ihr ursprüngliches Dateiformat nicht:
dort bleibt FORMAT —. Falls die Set-Datei vorliegt, wird die BPM aus dem
zugehörigen Set-Ausschnitt geschätzt; das ist nicht zwingend das Originaltempo.
Metadaten werden im Hintergrund ermittelt und pro Datei/Änderungsstand unter
Datenbank/Metadaten gespeichert. Die Musikdatenbank muss nicht neu aufgebaut werden.
TXT und JSON enthalten nun die gemeinsame nummerierte Tracklist mit Methoden
und Quellen. Format und BPM sind zusätzliche Angaben in der Oberfläche.

Prüfdatei: tests/metadata_test.py. Prüft synthetische Tempi und Stille,
BPM-Tags und Cache sowie FFmpeg und die asynchrone Tabelle.
Diese Prüfungen wurden ausgeführt und bestehen, einschließlich realer
FFmpeg-Decodierung und der asynchronen Anzeige in der Benutzeroberfläche.
