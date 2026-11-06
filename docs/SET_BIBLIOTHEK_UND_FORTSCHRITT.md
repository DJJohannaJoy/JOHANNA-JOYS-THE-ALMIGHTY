# Set-Bibliothek und große Titelliste

Der SETS-Knopf direkt links neben dem Zahnrad öffnet die lokale Set-Bibliothek. Vorhandene Ergebnis-JSON-Dateien im Ergebnisordner werden automatisch angezeigt. Neue Scan-Ergebnisse werden zusätzlich als eigenständige lokale Schnappschüsse unter `Datenbank/Set-Bibliothek` gespeichert. Der Speichern-Knopf sichert auch einen aktuellen Teilstand. Zu einem bestehenden Bericht wird dessen Bibliothekskopie aktualisiert, kein identischer Eintrag vervielfacht. Unterschiedliche Scan-Berichte bleiben als frühere Suchen erhalten.

Die Bibliothek sucht in Setnamen, Künstlern und Titeln. Ein Doppelklick öffnet die gespeicherte Titelliste auch dann, wenn die ursprüngliche Audiodatei nicht mehr vorhanden ist. „Zum Prüfen laden“ übernimmt einen früheren Stand in die Hauptansicht. Für eine erneute Audio-Prüfung muss die Audiodatei vorhanden sein oder neu zugewiesen werden.

„Gross anzeigen“ bei ERGEBNIS öffnet ein großes, maximierbares Fenster mit Suchfeld, vollständigen Titeln und horizontaler/vertikaler Bildlaufleiste. Während eines Scans wird die Liste aktualisiert. Die Hauptaktion SCANNEN ist 64 Pixel hoch. Darüber stehen SPEICHERN, RESET (↺) und ERNEUT PRÜFEN. Die beiden äußeren Knöpfe teilen die verbleibende Breite gleich auf. Die Methodenwahl erlaubt weiterhin die Wiederholung einzelner Scans. Die Bibliothek zeigt ein offenes Buch auf demselben abgerundeten roten Knopfhintergrund und in exakt denselben Abmessungen wie das Zahnrad.

RESET leert den aktuellen Arbeitsstand: Setpfad, Online-Link, Treffer, Scanfortschritt, Protokoll, Metadatenaufträge und Wiederholungszustände. Ein laufender Auftrag wird zuerst abgebrochen; verspätete Treffer können den geleerten Zustand nicht wieder füllen. Originaldateien, Musikdatenbank und gespeicherte Bibliothekseinträge bleiben erhalten. Der leere Zustand wird für den nächsten Programmstart gemerkt; eine bewusste Bibliotheksauswahl oder ein neuer Scan hebt dies wieder auf.

## Fortschritt

FORTSCHRITT / PROTOKOLL ist standardmäßig nur 110 Pixel hoch und zeigt den Gesamtbalken mit Prozentwert und den Metadatenfortschritt. ERGEBNIS behält bei allen drei geprüften Fenstergrößen mindestens 190 Pixel Tabellenhöhe. METHODEN / SCHNIPSEL öffnet die Einzelfortschritte. Bei genügend freiem Platz werden sie im Hauptfenster ausgeklappt; sonst öffnet sich das Detailfenster, statt die Ergebnisliste zusammenzudrücken. Das anklickbare Protokoll öffnet ein eigenes Fenster.

Die Detailansicht zeigt Methoden und Unterschritte. Die ausklappbare Ansicht enthält sechs Methodenbalken und eine separat scrollbarere Liste für Tempo-Varianten und Online-Schnipsel. Aktive Schnipsel stehen vor abgeschlossenen. Ein Filter wählt die Methode. Bei Online-Schnipseln sind Ausschnitt, Fingerabdruck und gültige Antwort die drei Arbeitsschritte; die Prozentangabe ist ein Anteil erledigter Arbeitsschritte und keine erfundene Restzeit. Offline-Unterbalken zeigen die tatsächlich gemeldete Zahl verglichener Fenster.

## Titelsuche

Jeder Titel hat Suchlinks für Soundeo (über eine auf Soundeo begrenzte Websuche), SoundCloud, YouTube, Beatport und Spotify. SoundCloud sucht nach Künstler und Titel ohne zusätzlichen Free-Download-Filter. Die fünf Plattformen stehen im großen Fenster und den Erkennungsdetails bereit und werden mit Bibliothekskopien gespeichert. Es handelt sich um Suchlinks, nicht um bestätigte Fundstellen, Kaufangebote oder bestätigte kostenlose Downloads. Die gesonderte KI-Hintergrundmethode ist in KI_HINTERGRUNDMETHODE.md beschrieben.

Die große Titelliste verwendet einen eigenen Tabellenstil ohne die festen Rasterbilder der Hauptansicht. Überschriften und Zellen sind gemeinsam ausgerichtet. Lange Titel, Methoden und Quellen werden passend zur aktuellen Spaltenbreite gekürzt; die vollständigen Daten bleiben in der Zeilenansicht erhalten. Spotify besitzt eine eigene Spalte und einen gleich breiten Plattformknopf. Größenänderungen und die Klickzuordnung wurden bei drei Fenstergrößen geprüft.
