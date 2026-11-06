# Die erkannte Trackliste als Playlist übernehmen

Im Bereich **ABLAUF** direkt neben **SCANNEN** oder im großen Titelfenster **REKORDBOX-EXPORT** öffnen. Scannen belegt 3/5 und Export 2/5 der gemeinsamen Knopfzeile. Alle erkannten Titel erscheinen in Set-Reihenfolge. Eindeutig passende lokale Audiodateien werden automatisch zugeordnet. Original und Remix bleiben getrennt; mehrere mögliche Dateien müssen ausdrücklich zugewiesen werden. Alternativ lässt sich eine bestehende Rekordbox-Bibliotheks-XML zum Dateiabgleich laden.

Standardmäßig wird nur eine vollständige Playlist exportiert. Fehlende Dateien lassen sich über **DATEI ZUWEISEN** ergänzen. **TEILEXPORT / SUCHLISTE** erstellt ausdrücklich eine Teilplaylist und eine Liste aller fehlenden Titel mit Suchlinks. Suchlinks erzeugen keine abspielbaren Dateien.

Zuordnungen werden dauerhaft unter `Datenbank/rekordbox_export_zuordnungen.json` gespeichert und beim nächsten Öffnen übernommen. **ZUORDNUNG LÖSCHEN** nimmt eine manuelle Auswahl zurück. **MUSIKORDNER ABGLEICHEN** ergänzt vorhandene Dateien aus einem gewählten Ordner im Hintergrund; der Dateiabgleich benötigt keinen neuen Set-Scan. Mehrere passende Dateien erscheinen bei Auswahl des Titels im Feld **Passende Dateien** und lassen sich mit **DATEI ÜBERNEHMEN** bestätigen. Eine geladene Bibliotheks-XML wird für spätere Exporte ebenfalls wiederverwendet.

Teilplaylists tragen `TEILPLAYLIST` und die Anzahl vorhandener/erkannter Titel im Dateinamen und im XML-Playlistnamen. Exporte werden zunächst vollständig geschrieben und auf konsistente Track-IDs, Dateipfade und Anzahlen geprüft. Erst danach erscheint der fertige Ausgabeordner. Schreibfehler hinterlassen keinen scheinbar fertigen Export.

Die Ausgabe liegt unter `Ergebnisse/Rekordbox-Export/` in einem neuen Ordner. Die `.m3u8` importiert man in Rekordbox über **Datei > Importieren > Wiedergabeliste importieren** (English: **File > Import > Import Playlist**). Eine Rekordbox-XML liegt zusätzlich bei. Die Originaldateien müssen unter ihren angegebenen Pfaden verfügbar bleiben.

`ALLE_TITEL.csv`, `FEHLENDE_DATEIEN.csv` und `EXPORT_STATUS.json` dokumentieren die Zuordnung und Vollständigkeit. Der Export verändert weder Audiodateien noch die Rekordbox-Datenbank. Geschätzte Set-BPM werden nicht auf Originaldateien übertragen. Dies ist eine Playlist einzelner vorhandener Songs; die Set-Aufnahme wird nicht zerschnitten.

Referenzen: https://cdn.rekordbox.com/files/20260409151936/rekordbox7.214_manual_EN.pdf (Import Playlist, Seite 40); https://cdn.rekordbox.com/files/20200410160904/xml_format_list.pdf (XML-Schema).
