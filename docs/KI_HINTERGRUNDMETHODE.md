# Eigenständige KI-Nachprüfung

Die KI startet bei neuen Scans automatisch, sofern die neue Einstellung `local_ai_method` aktiv ist (Standard: an) und das gewählte lokale Modell bereit ist. Sie verarbeitet neue Treffer während des Scans, wartet nicht auf einen abschließenden Textbericht und hat einen eigenen Fortschrittsbalken. Die normalen Scan-Ergebnisse werden gespeichert und bedienbar, auch wenn die KI noch arbeitet. „KI-BEFUNDE“ öffnet die laufenden und gespeicherten Bewertungen. „Nur KI erneut prüfen“ wiederholt ausschließlich diese Methode.

## Was tatsächlich geprüft wird

- Original-/Remix-/Edit-Versionen werden als getrennte Kandidaten behandelt. Verschiedene Titel desselben Künstlers sind keine Dubletten. Unbestätigte Offline-Kandidaten werden ausdrücklich als solche eingeordnet.
- YouTube und SoundCloud werden über die bereits installierte yt-dlp-Suche nach echten Metadaten und Links abgefragt. An die Plattformen gehen Künstler und Titel; das Set-Audio und lokale Dateipfade werden nicht hochgeladen. Suchtreffer bestätigen die Audio-Version nicht. Soundeo und Beatport bleiben ohne zusätzliche verifizierte Quelle Suchlinks.
- Passende Referenzdateien werden aus der lokalen Musikbibliothek ausgewählt. An den tatsächlichen Erkennungspositionen werden bis zu zwei getrennte 20-Sekunden-Ausschnitte mit mehreren Tempofaktoren über die vorhandene Fingerprint-Engine geprüft. Ein extrapolierter Trackanfang ersetzt dabei nicht die tatsächliche Erkennungsposition.
- Audio-Nachprüfungen warten auf freie Offline-Scan-Kapazität und laufen mit niedrigerer Prozesspriorität. Fingerprint-Ergebnisse enthalten Hashzahlen, Unterstützungslänge, Tempo, Referenzdatei und Zahl unabhängiger Ausschnitte. Ein stärkerer Gegentreffer verhindert eine eindeutige Zuordnung.
- Das lokale Sprachmodell erhält diese Belege und beurteilt Grenzfälle sowie passende Fundstellen. Nur vorgegebene Fall- und Quellen-IDs werden akzeptiert. Erfundenen URLs wird nicht gefolgt; das Modell führt keine Befehle aus und schreibt keine Titel um.

## Ergebnisse, Grenzen und Wiederholungen

Das Befundfenster trennt KI-Einschätzung, Audio-Befund und tatsächlich gefundene Quellen. Ein starker Fingerprint-Treffer ist ein überprüfbarer lokaler Beleg; eine textuelle KI-Einschätzung allein ist keine Musikerkennung. Mehrdeutige Versionen bleiben entsprechend markiert. Es werden keine bestehenden Titel automatisch umbenannt, zusammengeführt oder gelöscht.

Fundstellen und unveränderte Bewertungen werden zwischengespeichert. Bei veränderter Musikdatei, veränderter Datenbank oder neuen Erkennungsbelegen wird neu geprüft. Eine ausdrückliche KI-Wiederholung erzwingt neue Abfragen. Quellenfehler werden sichtbar gespeichert; nach wiederholten Verbindungsfehlern läuft der lokale Teil weiter. Fehlendes Modell und ungültige Modellantworten werden als übersprungen bzw. fehlgeschlagen ausgewiesen.

Befunde liegen getrennt unter `Datenbank/KI-Nachpruefung` und neben dem Ergebnis als `*_KI_METHODE.json`. Die Set-Bibliothek speichert sie mit. Reset und ein neues Set stoppen den alten KI-Auftrag; verspätete Antworten können den geleerten Arbeitsstand nicht erneut füllen.

## Verifikation am 6. November 2026

Ein realer Prüffall aus dem vorhandenen Set wurde mit dem tatsächlich geladenen Modell `google/gemma-4-e4b` in LM Studio vollständig ausgeführt. Die Methode lieferte einen starken lokalen Fingerprint-Befund, sechs tatsächliche YouTube-/SoundCloud-Fundstellen und eine lokale Referenz (insgesamt sieben Quellen). Zwei getrennte Set-Ausschnitte wurden geprüft. Der gesamte Prüffall dauerte 21,48 Sekunden; Quellenfehler wurden dabei nicht gemeldet. Dies ist eine Messung dieses Falls und keine Laufzeitgarantie für ein vollständiges Set.

Zusätzliche Tests prüfen Remix-Konflikte, unterschiedliche Titel, fremde Quellen-IDs, Cache-Wiederverwendung, Abbruch, stärkere Gegenreferenzen sowie den unabhängigen UI-Lebenszyklus: Der Kernscan ist fertig und bedienbar, während die KI weiterläuft. Alle bisherigen Regressionstests bestehen.

Die Plattformabfragen verwenden die Such- und Metadatenfunktionen von [yt-dlp](https://github.com/yt-dlp/yt-dlp); es werden dabei keine Audiodateien von den Fundstellen heruntergeladen.

## Adaptive Nachprüfung

Bei unklaren Befunden bekommt das Modell jetzt einen Katalog tatsächlich ausführbarer Folgetests. Es wählt konkrete Test-IDs für weitere Ausschnitte, feinere Tempofaktoren (0,97/1,03), Pitch-Varianten, bereits gefundene weitere lokale Referenzen oder eine Suche ohne Versionszusatz. Das Programm führt nur angebotene Tests aus und gibt die neuen Belege zur erneuten Bewertung zurück. Freie Modellbefehle, erfundene Test-IDs oder URLs werden nicht ausgeführt. Falls keine gültige Auswahl kommt, wird höchstens ein vorbereiteter Rückfalltest gewählt und ausdrücklich so protokolliert.

Standardmäßig sind zwei Nachprüfrunden mit höchstens drei ausgewählten Tests je Runde erlaubt. Eine eigene Zeitgrenze begrenzt zusätzliche Arbeit; die übrigen Scans bleiben unabhängig bedienbar. Ausgeführte Tests werden nicht erneut angeboten. Fingerprint-Proben werden anhand Musikdatei, Datenbankstand, Position, Tempo und Modus zwischengespeichert. Überlappende Ausschnitte gelten nicht als unabhängige Bestätigungen. Weicht die benannte starke Audioreferenz vom bisherigen Titel ab, wird ein Konflikt ausgewiesen, auch wenn das Sprachmodell ihn übersehen hat.

Die Befundansicht zeigt jede Runde, die Auswahl durch Modell bzw. Rückfalllogik, die ausgeführten Tests und den anschließenden Befund. Fehlgeschlagene Nachbewertungen bleiben sichtbar und werden nicht als vollständig geprüft gespeichert. Erreichen zusätzliche Tests keine Eindeutigkeit, bleibt das Ergebnis unklar; es wird weder künstlich bestätigt noch endlos weitergesucht.

Live-Prüfung mit dem geladenen Gemma-Modell: Für „Doing Drugs Selling Drugs 2012 (Slugos Remix)“ wählte das Modell selbst sechs Tempo-/Pitch-Tests in zwei Runden aus. Neue Ausschnitte wurden ausgeführt und die neuen Belege erneut bewertet. Der Fall wurde in 55,53 Sekunden abgearbeitet. Da die Version dabei nicht sicher belegt werden konnte, blieb der Befund korrekt als unklar markiert. Diese Messung ist keine Laufzeit- oder Genauigkeitsgarantie für sämtliche Sets.

Eine zusätzliche Prüfung mit zwei tatsächlich vorhandenen, bekannten Audiodateien bestätigte die passende Referenz „In Verruf – Fassade“ als starken lokalen Treffer. Bei absichtlich falscher Zuordnung einer anderen Aufnahme zur Fassade-Referenz wurde keine Bestätigung erteilt; die Engine fand stattdessen „In Verruf – Ewigkeit“. Beide Prüfungen zusammen dauerten 28,2 Sekunden. Auch dies ist ein begrenzter Kontrolltest und keine gemessene Genauigkeitsquote für vollständige DJ-Sets.
