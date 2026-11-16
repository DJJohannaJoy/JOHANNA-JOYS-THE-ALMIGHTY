# Google Song Search · eingebaut ab 1.14.5

Google ist eine eigene parallele Erkennungsmethode neben Schnellscan, Tiefenscan, MIX-ID und ShazamIO. Die Verarbeitung beginnt nach dem Laden des Sets; Google wartet nicht auf Shazams Anfrageverteilung. Jeweils zwei 20-Sekunden-Ausschnitte werden verarbeitet. Fortschritt und Ausschnitte stehen unter **Google** und **Methoden / Schnipsel**. Unter **Erneut prüfen → Google** lässt sich ausschließlich Google wiederholen; bisherige Treffer bleiben erhalten.

## Einfach einrichten

1. **Zahnrad → GOOGLE-ZUGANG IMPORTIEREN** öffnen.
2. Die bereitgestellte Google-Zugangsdatei (`.json`) auswählen.
3. Datei oder Set-Link auswählen und **SCANNEN** drücken.

Die Verbindung wird mit dem ersten Ausschnitt geprüft. Eine eingerichtete Datei allein bestätigt noch keinen gültigen Netzwerkzugang. Ohne Datei wird Google übersprungen; die übrigen Methoden funktionieren weiter. Ein Berechtigungsfehler wird ausdrücklich als Fehler angezeigt und niemals als „kein Treffer“ gespeichert.

## Können mehrere Nutzer dieselbe Kennung verwenden?

Der verwendete Zugang identifiziert die Google-App. Er enthält kein persönliches Google-Konto, keine Anmelde-Cookies und kein OAuth-Token. Dieselbe App-Kennung wurde in mehreren getrennten Windows-Prozessen ohne Android oder Anmeldung akzeptiert. Nutzer müssen deshalb keinen persönlichen Google-Cloud-Schlüssel erstellen.

Eine Kopie der Zugangsdatei kann in einer weiteren ALMIGHTY-Installation importiert werden. Die Nutzung auf einem anderen PC beziehungsweise Netzwerk wurde noch nicht separat geprüft. Google kann die Kennung, Einschränkungen oder den Dienst jederzeit ändern. Es gibt keine zugesicherte kostenlose Quote und keine Garantie unbegrenzter oder dauerhafter Nutzung.

Die Datei liegt nach dem Import unter `Daten/Google/zugang.json`. Sie gehört zu den privaten Einstellungen und wird nicht in GitHub oder im öffentlichen Programmpaket veröffentlicht. Nur diese Datei ist für eine Weitergabe des App-Zugangs vorgesehen; keine kompletten Traffic-Mitschnitte, Konto-Cookies oder Zertifikatschlüssel weitergeben.

## Ergebnis und Datenschutz

Kurze Audioausschnitte werden an Googles Song-Search-Dienst übertragen. Die Originaldatei bleibt unverändert. Ergebnisse zeigen **Google Song Search · Google-Katalog** als Quelle; Google wird nicht als Shazam-Nachweis ausgegeben. Antworten ohne Treffer werden zwischengespeichert. Dienstfehler, Zeitüberschreitungen und Berechtigungsfehler werden nicht als leere erfolgreiche Ergebnisse gespeichert. Ein zurückgegebener Kandidat ist kein Nachweis der exakten Remix-Version.

Die Anbindung verwendet einen nicht öffentlich zugesicherten Google-App-Endpunkt, keine offizielle Google-Cloud-Musikerkennungs-API. Für diese Integration sind weder Handy-Root noch ein installierter Abfang-Zertifikatsanbieter nötig. Die beim Handyversuch beobachteten TLS-Abbrüche waren kein brauchbarer Zugang.

## Geprüft am 16.11.2026

- Mit App-Kennung: erfolgreicher gRPC-Status 0; ein echter 20-Sekunden-Ausschnitt lieferte **Darkness Is Beauty in the Right Hands – Tanzanfall**. Die musikalische Richtigkeit wurde nicht unabhängig bestätigt.
- Ein zweiter Ausschnitt wurde erfolgreich verarbeitet, aber ohne Treffer beantwortet.
- Die produktive ALMIGHTY-Methode verarbeitete den ersten Ausschnitt erneut erfolgreich: **1/1 geprüft**, ein Kandidat, keine Fehler.
- Ohne App-Kennung: Berechtigungsfehler, kein verwendbares Suchergebnis.
- Automatische Prüfungen: gleichzeitiger Start aller vier Arbeiter, getrennte Einzelwiederholung, Quellenzusammenführung, Antwort-Dekompression, fehlerhafte Antworten, Zwischenspeicherung und Abbruch bei ungültigem Zugang.

[Technischer Nachweis](GOOGLE_DEEP_DIVE.md) · [Kurzanleitung](GOOGLE_SETUP_EINFACH.md)
