# Aktueller Befund: Onlinesuche unvollständig

## Aktueller Ablauf: automatisch bis zu gültigen Antworten

Der zwischenzeitlich eingebaute endgültige Pausenzustand ist entfernt. HTTP 429 beendet den Suchauftrag nicht mehr. Der Auftrag bleibt aktiv, respektiert den vorgeschriebenen Wartezeitpunkt und wiederholt die offene Probe automatisch. Auch mehrere aufeinanderfolgende Ablehnungen erfordern keinen manuellen Neustart. Das gemeinsame Startintervall steigt bei wiederholter Begrenzung vorsichtig bis maximal zwölf Sekunden. Abbrechen bleibt jederzeit möglich.

100 Prozent bedeuten gültige Antworten auf alle geplanten Proben, einschließlich regulärer Kein-Treffer-Antworten. Verweigert der externe Dienst Antworten dauerhaft, kann keine ehrliche Laufzeit oder vollständige Erkennung garantiert werden; die Anwendung darf deshalb keine erfundenen 100 Prozent melden.

Gespeicherte alte Teilstände werden als offen geladen. Der Hauptknopf FORTSETZEN startet ausschließlich deren offene Methoden und erhält die vorhandenen Treffer. Neue laufende Aufträge wechseln bei HTTP 429 in automatische Wiederholungen, nicht in einen endgültigen Pausenstopp.

Die Tests simulieren mehrere HTTP-429-Antworten hintereinander für beide Adapter und prüfen das anschließende Erreichen echter 100 Prozent sowie sofortiges Abbrechen während einer Dienstwartezeit.

Die folgenden Abschnitte dokumentieren den vorherigen Live-Versuch und die historische Fehlerursache.

Der komplette verbleibende Online-Durchlauf des betroffenen In-Verruf-Sets wurde am 05.11.2026 versucht. Nach weiteren gültigen Antworten lieferte Shazam erneut HTTP 429. Das Set ist weiterhin nicht vollständig geprüft. Der frühere Vier-Proben-Test in 3,53 Sekunden war kein Nachweis einer stabilen vollständigen Suche.

Der gültige neue Versuch dauerte 37,27 Sekunden und speicherte sieben zusammengeführte Tracks. Im dauerhaften Probencache liegen 26 von 90 gültigen mix-id-Proben und neun von 50 gültigen ShazamIO-Proben. Fehlgeschlagene und nur wartende Anfragen zählen nicht als erfolgreich geprüft. Die Online-Suche bleibt pausiert, solange der Dienst weitere Anfragen ablehnt.

## Änderungen

- Beide Adapter teilen jetzt Anfragenabstand und Dienstpausen über eine kurz gesperrte Zustandsdatei. Auch zwei gleichzeitig offene Programmfenster teilen diesen Takt.
- Zunächst zwei Sekunden Abstand zwischen Anfragestarts; nach HTTP 429 bis zu vier Sekunden. Eine kurze serverseitige Pause wird mit Countdown angezeigt und einmal automatisch erneut versucht. Längere Sperren oder erneute Ablehnung bleiben als pausierter Teilstand sichtbar. Ein Dienstlimit wird nicht umgangen.
- Erfolgreiche positive und negative Proben bleiben gespeichert. Wiederholungen setzen die fehlenden Proben fort.
- Berichte speichern nun die Aufgaben- und Prozentstände. Beim Laden alter Berichte ohne diese Zähler steht bei unvollständigen Methoden „Unvollständig“ statt einer erfundenen 0-Prozent-Angabe.
- Die Gesamtanzeige benennt die pausierte und unvollständige Onlinesuche ausdrücklich.

## Lokale KI

Gemma in LM Studio hat den tatsächlichen Bericht lokal in 14,11 Sekunden geprüft. Die Hinweise liegen separat neben dem Scannerbericht als `_KI_PRUEFUNG.txt`. Das Modell ändert keine erkannten Tracks und erkennt hier kein Audio. Der neue Knopf „BERICHT MIT KI PRÜFEN“ startet ausschließlich diese Textprüfung. Die automatische Nachprüfung wurde nicht stillschweigend eingeschaltet. Der Status zeigt „auf Abruf“.

Die Vorgaben unterscheiden nun verschiedene Titel desselben Künstlers von Dubletten. Eine vom Modell abgeschnittene Antwort wird als unvollständig markiert. Modellhinweise bleiben unverbindliche Hinweise zum vorhandenen Textbericht.

## Verifikation

Syntax, UI mit pausierten/restaurierten Prozentständen, einzelne Wiederholungen, lokale KI, Originaldaten-Erhalt, gemeinsame Dateisperre, geteilte Drosselung und Wiederaufnahme wurden geprüft. Der vollständige Live-Versuch wurde durch den externen Dienst begrenzt. Deshalb ist die vollständige Onlinesuche ausdrücklich noch offen.
