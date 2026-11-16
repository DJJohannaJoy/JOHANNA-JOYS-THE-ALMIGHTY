# Google-Songerkennung – Plan, noch nicht eingebaut

Stand: 16.11.2026. Der Nutzer hat ein Android-Handy mit funktionierender Google-Songsuche. Die frühere Recherche wurde wieder aufgenommen; eigene Google-App-Zugangsdaten wurden bisher nicht erfasst. Google bleibt ausdrücklich außerhalb dieser Programmversion.

## Praktischer Weg

1. Einen kurzen Test auf dem vorhandenen Android-Handy durchführen. Eine eigene Songsuche der Google-App aufzeichnen und die vier von humtosong benötigten Header lokal übernehmen: App-Key, Android-Paket, Zertifikat-Fingerabdruck und User-Agent. Keine Konto-Cookies oder Passwörter anfordern; Aufzeichnung auf diese eigene Anfrage begrenzen. Die Erfassungsmöglichkeit muss zuerst am konkreten Handy geprüft werden, da App-Version und Zertifikatsprüfung sie beeinflussen können.
2. Den quelloffenen MIT-Client [niizam/humtosong](https://github.com/niizam/humtosong) prüfen, auf einen konkreten Commit festlegen und für Windows als EXE bauen. FFmpeg ist bereits in ALMIGHTY enthalten. Android wird nach diesem Ansatz für die einmalige Erfassung benötigt; die spätere Erkennung läuft vom Windows-PC aus, ohne Android-Emulator. Go ist nur zum Bauen nötig.
3. Zuerst einen echten bekannten Audioclip und einen unbekannten Clip testen: Treffer, Kein-Treffer, Zugang abgelehnt, Zeitüberschreitung und Abbruch sauber unterscheiden. Erst nach diesem Nachweis als separate optionale Google-Methode einbauen. Zugangsdaten bleiben im privaten Datenordner, niemals in Git, Downloads oder Protokollen.
4. Im späteren ALMIGHTY-Adapter zunächst nur Lücken nach den vorhandenen Methoden prüfen. Maximal zwei kurze Ausschnitte gleichzeitig, Ergebnisse zwischenspeichern, echte Prozent-/Schnipselangaben und einzelnes Wiederholen unterstützen. Google als eigenen Katalog in der Quellenspalte nennen. Vorhandene Titel nicht ohne Belege ersetzen; Dubletten und Versionen mit den übrigen Ergebnissen abgleichen.

## Nachweis und Grenzen

Der ursprüngliche Client beschreibt Windows-Builds, einen lokalen HTTP-Server und eine Datei-Schnittstelle. Er sendet Audio über Googles privates HTTP/2-gRPC-Protokoll. Laut Autor gelangen Musikdateien zu Google, ohne OAuth-Konto-Token; ein beliebiger Google-Cloud-Key ist nicht als funktionierend belegt. Die dokumentierten Live-Tests stammen vom Autor, nicht von diesem ALMIGHTY-Projekt.

Das ist keine offiziell freigegebene öffentliche Musikerkennungs-API. Dauerhafte Verfügbarkeit, erlaubte Automatisierung und kostenlose Kontingente sind nicht zugesichert. Keine erfundenen Header oder fremden Keys verwenden, keine Dienstsperren umgehen. Ohne eigenen erfolgreichen Verbindungstest keine fertige Google-Erkennung behaupten oder grüne Bereitschaft anzeigen.

Primärquelle: [Projekt-README und Protokollbeschreibung](https://github.com/niizam/humtosong/blob/main/README.md). Hintergrund: [Google Research – Music Recognition](https://research.google/blog/googles-next-generation-music-recognition/).
