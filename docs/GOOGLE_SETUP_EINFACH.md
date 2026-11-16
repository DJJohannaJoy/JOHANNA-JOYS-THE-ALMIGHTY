# Google in ALMIGHTY

**Auf diesem PC ist der getestete Zugang bereits eingerichtet.** Bei einer weitergegebenen öffentlichen ZIP-Datei wird eine Zugangsdatei separat benötigt.

1. ALMIGHTY öffnen und auf das Zahnrad klicken.
2. **GOOGLE-ZUGANG IMPORTIEREN** wählen und die erhaltene `.json`-Datei öffnen.
3. Das Häkchen **Google · eigene Musikerkennung** eingeschaltet lassen.
4. Ein Set auswählen oder einen Link einfügen und **SCANNEN** drücken.

Google läuft gleichzeitig mit den anderen Suchmethoden. Details zu jedem Ausschnitt stehen unter **Methoden / Schnipsel → Google**. **Erneut prüfen → Google** startet nur diesen Dienst neu. Erfolgreich geprüfte Ausschnitte werden aus dem Zwischenspeicher übernommen.

Die importierte Datei steht unter `Daten/Google/zugang.json`. Eine Kopie lässt sich für eine weitere Installation importieren. Sie enthält die Google-App-Kennung, keine Anmeldung. Ein eigener persönlicher Google-Schlüssel ist nicht erforderlich. Die Funktion auf fremden Rechnern und die zukünftige Akzeptanz durch Google sind nicht zugesichert.

Bei **PERMISSION_DENIED**, gRPC **7/16**: Google akzeptiert die Kennung nicht. Nur Google schlägt fehl; andere Scans und Ergebnisse bleiben erhalten. Bei Zeitüberschreitungen erfolgt eine begrenzte automatische Wiederholung. Eine fehlgeschlagene Anfrage wird nicht als „kein Treffer“ behandelt.

Auf dem Handy braucht für diese Desktop-Anbindung nichts mitgeschnitten zu werden. Die offizielle Google-App wurde bereits lokal untersucht. Die öffentliche App-ZIP enthält absichtlich keine Zugangsdatei.
