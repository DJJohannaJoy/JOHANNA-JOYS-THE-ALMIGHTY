# Datenbank: Fortschritt, Wiederaufnahme und Programmsymbol

> Historischer Prüfstand. Der aktuelle parallele Aufbau und die Behandlung
> nicht lesbarer Dateien stehen in [PARALLEL_UND_LOKALE_KI.md](PARALLEL_UND_LOKALE_KI.md).

Der Aufbau zeigt jetzt echte Prozentwerte, verarbeitete Titel / Gesamtzahl
und nach den ersten Titeln eine geschätzte Restzeit. Die Zeit ist eine
Schätzung aus dem tatsächlichen bisherigen Durchsatz. Während des Speicherns
wird dieser Schritt ausdrücklich angezeigt. 100 % erscheint erst, nachdem
die neue Datenbank erfolgreich veröffentlicht wurde.

Die Erkennungs-Engine wird nach jeweils höchstens 32 Titeln neu gestartet.
Jeder erfolgreiche Abschnitt wird gesichert. Scheitert ein Abschnitt,
wird er in kleinere Abschnitte bis hin zum Einzeltitel aufgeteilt und erneut
versucht. Es werden keine Titel stillschweigend ausgelassen. Nach drei
gescheiterten Einzelversuchen wird der konkrete Titel gemeldet; die bereits
gesicherten Abschnitte bleiben erhalten.

Abbruch, Programmende oder ein weiterer Fehler löschen den Zwischenstand
nicht. Beim nächsten Anlegen wird er verwendet, sofern Dateiliste, Größen
und Änderungszeiten weiterhin übereinstimmen. Die bisherige fertige Datenbank
wird erst nach vollständigem Erfolg ersetzt. Eine Sperre verhindert zwei
gleichzeitige Datenbankaufbauten im selben Programmordner.

Das vom Nutzer bereitgestellte Bild dient als Windows-Fenster- und
Programmsymbol. PNG und ICO mit mehreren Auflösungen sind im Paket enthalten.

Tests prüfen einen erzwungenen nativen Prozessfehler, Abbruch und Fortsetzen,
Erhalt der alten Datenbank, Vollständigkeit aller Titel und echte Prozentwerte.
Die UI-Prüfung umfasst die Prozent-/Zeit-Anzeige und drei Fenstergrößen.
Ein echter Wiederaufnahmetest setzte eine 200-Titel-Datenbank auf 320 Titel
fort; alle 320 Namen blieben erhalten. Die echte Fortschrittsansicht wurde
bei 58 von 64 Titeln, 90,6 Prozent und einer Restzeitschätzung geprüft.
