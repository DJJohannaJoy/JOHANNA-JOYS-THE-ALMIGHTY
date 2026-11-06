# Gemeinsame Tracklist, Parallelität und Fortschritt

Die Oberfläche und TXT/JSON verwenden dieselbe chronologische Tracklist.
Einträge werden automatisch nummeriert. Identische Titel/Interpreten aus
mehreren Methoden werden in zeitlich zusammenhängenden Beobachtungsgruppen
vereinigt. Andere Remixe/Edits, andere Interpreten und spätere erneute Plays
bleiben getrennt. Original-Mix-Zusätze gelten als Namensalias. Unbekannte
Namensvarianten werden nicht durch aggressive Ähnlichkeitssuche gleichgesetzt.
Fehlen zwischen zwei Plays alle Beobachtungen, kann eine zeitbasierte
Zusammenführung weiterhin unsicher sein.

METHODE zeigt den Erkennungsweg: Originaltempo, konkrete Tempo-/Pitch-Variante,
mix-id und ShazamIO. QUELLE nennt audfprint mit Referenzdatei oder den
Shazam-Katalog mit Adapter. mix-id und ShazamIO sind keine unabhängigen
Musikdatenbanken. Ein Doppelklick öffnet sämtliche Methoden, Quellen,
Beobachtungszeiten, lokalen Pfade und verfügbaren Links. Lange Zellen werden
passend gekürzt; die Tabelle besitzt eine horizontale Bildlaufleiste.

Offline, mix-id und ShazamIO starten unabhängig voneinander. Offline zerlegt
das Set einmal. Danach werden die ersten Tempo-Varianten vor der Originaltempo-Abfrage eingeplant; beide laufen im selben begrenzten Pool mit höchstens drei Arbeitern gleichzeitig. Tiefenscan 1 wartet nicht mehr auf das Ende des Schnellscans.
Bereits belegte Offline-Fenster sowie tatsächlich online erkannte
Probenausschnitte reduzieren die verbleibende Arbeit. Zeitmarken aus
zusammengefügten Fenstern werden auf ihre ursprünglichen Setpositionen
zurückgerechnet. Derselbe Zeitabschnitt zählt nicht durch viele Varianten
plötzlich als mehrere unabhängige Offline-Belege.

mix-id verteilt die vorhandenen 60-Sekunden-Scanstellen auf drei versetzte
Durchläufe. Seine Pause zwischen Anfragen bleibt erhalten. Wiederholte
Erkennungen werden live übernommen, damit lange Tracks zusammenhängend
bleiben. ShazamIO verwendet allein höchstens zwei Arbeiter; bei gleichzeitigem
mix-id einen. Standardmäßig laufen dadurch höchstens vier Online-Anfragen
gleichzeitig. ShazamIO hat eine begrenzte Antwortwartezeit (Standard 20 s,
konfigurierbar) und einen Wiederholungsversuch je Probe. Nach drei weiterhin fehlerhaften Proben stoppt die Methode sichtbar. mix-id setzt einen abgestürzten oder 75 Sekunden stillstehenden Durchlauf einmal an der nächsten noch nicht erledigten Scanposition fort. Fehler und Teilresultate stehen im Bericht.

Sechs sichtbare Stufenbalken, Gesamtfortschritt und Format/BPM-Balken zeigen
wirklich erledigte Arbeit. EINZELSCHRITTE öffnet die einzelnen Tempo-Varianten
mit Vorbereiten/Vergleichen und Fensterzählern. Prozentwerte stehen für
Arbeitseinheiten, nicht für eine garantierte Restzeit. Ein fehlgeschlagener
Abschnitt wird nicht als erfolgreicher Treffer ausgegeben.

ERNEUT PRÜFEN erlaubt Schnellscan, Tiefenscan 1, Tiefenscan 2 oder Shazam einzeln zu starten. Die anderen Methoden und vorhandene Treffer bleiben erhalten; der Bericht wird gemeinsam neu gespeichert. Während eines laufenden Jobs sind Wiederholungen gesperrt. Nach Abbruch bleiben vorhandene Live-Treffer für Wiederholungen erhalten. Ein beendeter Gesamtlauf steht auf 100 % mit ausdrücklichem Fehlerstatus; die einzelnen fehlerhaften Methoden behalten ihre tatsächlich abgefragten Prozente und rote Kreuze. 100 % Gesamtabschluss bedeutet nicht, dass jede Probe erfolgreich abgefragt wurde. Die hellen gestrichelten Klickrahmen an Schaltflächen und Zahnrad sind entfernt; Tastaturbedienung bleibt erhalten.

Messung mit echtem FFmpeg/audfprint und einem deterministischen
36-Sekunden-Signal, erzwungenen 20 Tempo-Varianten und ohne Online-Anfragen:
vorher 36,23 s, parallel 12,44 s (2,91×). Beide Läufe erkannten denselben
bekannten Titel ohne Fehler. Das ist kein Nachweis einer festen Laufzeit
für beliebig lange DJ-Sets oder wechselnde Antwortzeiten der Online-Dienste.

Automatische Prüfungen: Identitäten, Remixe, Unicode, spätere Wiederholungen,
Nummerierung, Quellenreihenfolge; gleichzeitiger Start aller drei Methoden;
begrenzte Shazam-Parallelität, einzelne Audiodateien und echte Probenzähler;
mix-id-Aufteilung ohne Verlust von Scanstellen; drei Fenstergrößen,
Zellenbreiten, Einzelschritt- und Treffer-Detailfenster; Format/BPM inklusive
falschem Halbtempo-Tag. Online-Tests verwenden lokale Attrappen und laden
keine Musik zu Erkennungsdiensten hoch.

Das öffentliche GitHub-Repository ist lesbar. Schreiben wurde vom Connector
mit HTTP 403 verweigert; es wurde nichts veröffentlicht. Der lokale
Windows-Teststart funktioniert nach Ergänzen von features.prefer_mxc=true.

Standard: Schnellmodus mit sechs Tempofaktoren (-10, -6, -3, +3, +6, +10 Prozent). Einstellungen bieten die gründliche Suche mit allen 20 Faktoren. Diese kann mehr Treffer finden und dauert länger.

Reales 90-Minuten-Set, echte 2.592-Titel-Datenbank, nur lokal: 20 Varianten 285,05 s; sechs Varianten 113,75 s. Beide fanden denselben einen starken Offline-Titel, Fehler null. Online-Zeiten sind darin nicht enthalten.

Nach drei aufeinanderfolgenden ShazamIO-Fehlern werden keine weiteren Proben gestartet. Laufende Anfragen dürfen noch zurückkehren. Teilresultate und tatsächliche Zähler bleiben erhalten.

Layoutkorrektur: Schrittbalken jetzt 26 Pixel hoch statt 15, mit größerer Prozentanzeige und mehr Abstand zur Beschriftung. Der untere Fortschrittsbereich reserviert 120 Pixel und zeigt Gesamtfortschritt sowie Format/BPM vollständig. Standardfenster 1570×970, Mindestgröße 1250×900. Geometrieprüfung bei 1250×900, 1570×970 und 1920×1000 prüft alle Balken gegen jede umgebende Containerkante; keine abgeschnittenen Balken. Ein bereits laufender Scan wird nicht unterbrochen; das Layout gilt nach Neustart.

Erneute echte Offline-Messung nach dem vorgezogenen Tiefenscan: 90-Minuten-Set in 112,84 Sekunden, ein starker und ein schwacher Kandidat, keine Fehler. Erste Tempo-Variante fertig nach 41,8 s, Schnellscan fertig nach 45,3 s. Online-Wiederholungs- und Fehlerbehandlung wurden mit lokalen Testantworten geprueft; kein neuer Online-Vollscan.

Das letzte gespeicherte Ergebnis wird beim Start automatisch geladen. Auch der bestehende Bericht von 15:07 wurde getestet: 45 zusammengefasste Tracks und beide Methodenfehler wiederhergestellt. Einzelne Wiederholungen verwenden diese Belege weiter. JSON speichert kuenftig Quelldatei und Einzelbeobachtungen mit. Eine Methodenwiederholung startet keine automatische KI-Nachpruefung.

Startweg korrigiert: Der bestehende Desktop-Starter THE ALMIGHTY - STARTEN.bat verwendete noch .venv mit Python 3.15 (laufender Prozess um 15:39 gestartet). Er leitet jetzt wie der nummerierte Starter auf .venv_py312 um. Auch ein direkter Start von scanner.py unter einer anderen Windows-Python-Version startet vor nativen Importen die lokale stabile Python-3.12-Umgebung. Ein schon laufendes altes Fenster wird nicht automatisch unterbrochen.

ONLINE-UPDATE: ShazamIO-HTTP-429 wurde live nach 0,17-0,19 s gemessen; der lokale Fingerabdruck dauerte 0,016 s. Der Standardclient wiederholte intern bis zu 20-mal. Der neue Client meldet 429 sofort und beendet die betroffene Methode klar. Keine Umgehung von Anfragelimits. ShazamIO hat zwei parallele Probenarbeiter; mix-id drei. Eine gemeinsame faire Warteschlange begrenzt auf drei gleichzeitige Anfragen und mindestens 0,8 s Abstand zwischen Starts. Tiefenscan 2 und Shazam werden vor Offline eingeplant.

Tiefenscan 2 verarbeitet nun einzelne 18-s-Proben in isolierten Node-Prozessen statt lang laufender Teilsets. Ein Prozessfehler wird nur fuer diese Probe einmal wiederholt; nach drei aufeinanderfolgenden Fehlern wird beendet. Der mitgelieferte node-fetch-Client ersetzt Node 24 native fetch, das im Diagnoselauf nativ abstuerzte. Zeitlimit je HTTP-Anfrage 10 s, Prozess-Watchdog 15 s. Die bisherige 10/20/40-s-Wiederholungskette des CLI wird nicht mehr verwendet. Erfolgreiche Proben inklusive Kein-Treffer-Antworten werden anhand Datei, Groesse, Aenderungsdatum und Position dauerhaft gespeichert. Bereits belegte positive Beobachtungen aus alten Berichten fuellen diesen Cache. Wiederholungen setzen fehlende/fehlerhafte Proben fort.

Frischer Live-Test mit echten Anfragen, ohne Probe-Cache: vier Proben zusammen 3,53 s. ShazamIO: 2 Treffer, 0 Fehler. mix-id: 1 Treffer und 1 regulaere Kein-Treffer-Antwort, 0 Fehler. Kein neuer Vollscan des gesamten Sets; Netzantworten und Dienstlimits bleiben variabel.
