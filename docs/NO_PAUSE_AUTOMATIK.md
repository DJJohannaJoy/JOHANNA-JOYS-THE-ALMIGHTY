# Automatisch weiter bis zu gültigen 100 Prozent

Der endgültige Pausenstopp nach HTTP 429 ist entfernt. Offene Online-Proben werden innerhalb desselben aktiven Auftrags erneut versucht. Mehrere aufeinanderfolgende Begrenzungen verbrauchen kein festes Einmal-Wiederholungsbudget mehr. Ein vom Dienst angegebener Wartezeitpunkt bleibt verbindlich; danach geht es automatisch weiter. Die Anwendung fordert dafür keinen manuellen Neustart.

Der Auftrag bleibt sichtbar aktiv; der Fortschritt zählt ausschließlich gültige Antworten oder wiederverwendete gültige Proben. Auch eine reguläre Antwort ohne Treffer ist gültig. Fehlende Antworten werden nicht zu erfundenen Treffern oder 100 Prozent umgedeutet. Bei dauerhaft verweigerten Antworten ist keine feste Fertigstellungszeit garantiert. Abbrechen bleibt während aller Wiederholungen möglich.

Alte gespeicherte Pausenstände werden als offene Methoden geladen. Der Hauptknopf FORTSETZEN startet gezielt diese offenen Methoden. Bereits erledigte Offline-Scans und vorhandene Treffer bleiben erhalten. Neue laufende Aufträge wechseln bei 429 nicht in den alten Pausen-Endzustand.

Tests: Beide Adapter erhalten mehrfach hintereinander HTTP 429 und erreichen anschließend mit gültigen Antworten 100 Prozent. Zusätzlich geprüft: Dienstwartezeit abbrechen, gemeinsame Drosselung, Wiederverwendung von Proben und gezieltes Fortsetzen eines alten Teilstands.

Der betroffene, rund 90 Minuten lange Set wurde am 5. November 2026 in der installierten Desktop-Version vollständig geprüft: Tiefenscan 2 erreichte 90/90 gültige Proben, Shazam 50/50. Das gespeicherte Ergebnis enthält 26 zusammengeführte Titel und keine gemeldeten Fehler. Alle Schritte stehen auf abgeschlossen. Die Laufzeit betrug 831,7 Sekunden (rund 14 Minuten); gültige vorhandene Proben wurden wiederverwendet, erledigte Offline-Schritte und Treffer blieben erhalten. Ein manueller Pausenstopp oder ein Eingriff zum Fortsetzen war während dieses Durchlaufs nicht nötig. Damit ist der vollständige Abschluss dieses Sets belegt; eine Laufzeit von zwei Minuten oder die Erkennung jedes Titels wird damit nicht zugesichert.

## Anschließende Beschleunigung durch parallele Vorbereitung

Tiefenscan 2 bereitet bis zu vier 18-Sekunden-Ausschnitte parallel vor, Shazam bis zu vier 12-Sekunden-Ausschnitte. Die lokale Fingerabdruckberechnung belegt keinen Online-Anfrageplatz mehr. Tiefenscan-2-Fingerabdrücke werden dauerhaft getrennt von Erkennungsergebnissen gespeichert; beide Adapter verwenden den vorbereiteten Fingerabdruck bei automatischen Wiederholungen erneut. Probenabstände, Probenanzahl und Erkennungsverfahren bleiben gleich. Vorhandene gültige Ergebnisse werden weiterhin übernommen.

Das gemeinsame Anfragebudget lässt bis zu vier gleichzeitige Anfragen mit mindestens zwei Sekunden Startabstand zu. Dienstwartezeiten werden respektiert. Nach jeweils sechs gültigen Antworten sinkt eine zuvor erhöhte Drosselung schrittweise um 25 Prozent bis zum normalen Abstand. Ein No-Match zählt als gültige Antwort, ein Fehler nicht. Dadurch bleibt ein Scan nach einer vorübergehenden Begrenzung nicht dauerhaft im langsamsten Tempo.

Messung der lokalen Pipeline mit acht echten SDK-Fingerabdrücken und kontrollierter, simulierter Antwortzeit von einer Sekunde: vorher 5,782 Sekunden, danach 3,000 Sekunden (Faktor 1,93). Dies ist kein Nachweis für eine halbierte vollständige Online-Scanzeit. Ein zusätzlicher echter Online-Test beider Adapter lieferte 8/8 gültige Antworten ohne Fehler in 69,97 Sekunden, einschließlich einer automatischen Dienstwartezeit. Die vollständige Laufzeit des 90-Minuten-Sets wurde nach diesem Geschwindigkeitsupdate noch nicht erneut gemessen.
