# Parallelaufbau und lokale KI · 05.11.2026

Der Datenbankaufbau verteilt die Analyse auf getrennte Prozesse. Auf diesem
Rechner werden 30 Arbeiter genutzt; Anzahl und Speicherbedarf sind begrenzt.
Jeder fertige Titel wird einzeln atomar zwischengespeichert. Die große
Datenbank wird erst am Ende einmal zusammengeführt und komprimiert.
Unveränderte Titel brauchen beim nächsten Aufbau keine erneute Audioanalyse.
Alte Abschnitts-Checkpoints werden weiterhin als Ausgangspunkt übernommen.

Fehlgeschlagene Arbeitsgruppen werden geteilt und wiederholt. Nach drei
gescheiterten Einzelversuchen wird die Datei ausdrücklich in
`Datenbank/nicht_lesbar.json` genannt und im Abschluss angezeigt. Alle anderen
Dateien werden weiterverarbeitet. Eine alte fertige Datenbank bleibt bis zur
erfolgreichen Veröffentlichung erhalten. Abbruch erhält fertige Fingerabdrücke.
Die Anzeige zeigt Prozent, Titelanzahl, geschätzte Analyse-Restzeit und den
anschließenden Zusammenführungs-/Speicherschritt. 100 % gilt erst nach Abschluss.

Messung mit 2.593 tatsächlichen Bibliotheksdateien, ohne vorhandene
Fingerabdruck-Caches: 222,50 Sekunden; 2.592 indexiert, eine Datei nicht lesbar.
Damit ist die geforderte Grenze von zwei Minuten für den Erstaufbau noch
nicht erreicht. Sie wird ausdrücklich nicht garantiert. Die endgültige
Geschwindigkeit hängt auch von Dateigrößen, Laufwerk und CPU ab.

Ein erneuter vollständiger Aufbau aus den gespeicherten Fingerabdrücken wurde
mit 17,88 Sekunden gemessen. Die anschließende Zusammenführung nutzt direkte
Integer-Zugriffe statt einzelner NumPy-Skalaroperationen. Ein Vergleich mit dem
Original bestätigte exakt dieselben Tabellen, Zähler und Namen auch bei
Kollisionen, Zeitüberläufen und identischem Zufallsstart für Reservoir-Sampling.
Native Prozessabstürze wurden auf diesem Rechner weiterhin beobachtet; kurze
Arbeitsprozesse und begrenzte Wiederholungen sichern den Fortschritt, ersetzen
aber keine Garantie gegen weitere native Fehler.

Die FFmpeg-Decodierung liest das gleiche Mono-PCM gesammelt statt über viele
kleine Warteschlangen-Transfers. Ein Vergleich mit fünf echten Dateien
bestätigte identische Samples und Abtastraten. Die Erkennungsparameter und
Originaldateinamen bleiben erhalten; die Musikdateien werden nicht verändert.

## Lokale KI

Die Karte erkennt die LM-Studio-Installation und bietet Öffnen oder manuelle
Programmzuweisung an. Unter MODELL / VERBINDUNG sind Anbieter, lokaler Server,
Modell und Programmpfad einstellbar und werden gespeichert. Die Erkennung
unterscheidet verfügbare und geladene Modelle. Neuere und ältere LM-Studio-APIs
werden unterstützt. Ein reiner kompatibler Server ohne Ladestatus wird als
verfügbar mit unbekanntem Ladestatus angezeigt.

Gemma ist zulässig; ein bestimmter Hersteller oder Qwen ist nicht erforderlich.
Ollama bleibt eine ausdrücklich auswählbare Alternative. Es gibt keinen
stillen Wechsel von LM Studio zu Ollama. Embedding-Modelle werden ausgeschlossen.
Die KI prüft ausschließlich vorhandene Textberichte und erkennt selbst keine
Audio-Titel. Berichte gehen nur an lokale Adressen; Proxy und HTTP-Weiterleitung
sind für diese Anfragen deaktiviert.

API-Referenz: https://lmstudio.ai/docs/developer/rest/list

Prüfungen: paralleler Prozessabsturz und Wiederholung, Abbruch/Wiederaufnahme,
Schutz der aktiven Datenbank, Fehlerliste, echte Abschlusswerte; lokale
HTTP-Testserver für Modellerkennung und Verwendung des ausgewählten Modells;
UI-Prüfung bei drei Fenstergrößen und Prüfung des Modell-Dialogs.
