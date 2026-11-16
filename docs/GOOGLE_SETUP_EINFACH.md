# Google einrichten – so soll der einfache Weg aussehen

**Status: Entwurf für einen noch zu bauenden und zu testenden Assistenten. Die aktuelle ALMIGHTY-Version kann Google noch nicht automatisch einrichten.**

## Warum wir den Handy-Weg verlassen

Deine Songsuche funktioniert ohne Reqable. Mit der Aufzeichnung bricht sie ab; in den Fotos fehlen die benötigten Zugangsdaten. Deshalb ist weiterer Zertifikatsexport auf diesem Handy gerade keine sinnvolle Anleitung.

## Das bevorzugte Ziel für normale Nutzer

**Google aktivieren → Testclip prüfen → verwenden.** Kein Google-Konto und kein selbst erzeugter Cloud-Schlüssel sollen erforderlich sein. Der untersuchte Client arbeitet ohne Konto-Token. Wir müssen zuerst auf Entwicklerseite prüfen, ob seine App-Kennung unabhängig von Gerät und Sitzung wiederverwendbar ist. Ein gemeinsamer funktionierender Zugang ist bisher nicht nachgewiesen.

Dass Googles eigene App ohne Login arbeitet, beweist keine offene API ohne App-Kennung. Unser einzelner Test ohne sämtliche Kennungen wurde mit „Zugriff verweigert“ beantwortet. Das Programm darf einen solchen Fehler nicht als erfolgreichen Test anzeigen.

## Rückfalllösung: geführte Einrichtung am PC

Nur wenn tatsächlich installationsbezogene Werte benötigt werden, soll dieser aufwendigere Ablauf nötig werden:

1. In ALMIGHTY **Google einrichten** öffnen.
2. Den angezeigten Download starten. Der PC bereitet ein getrenntes Android-Testsystem vor. Die bisher ermittelten Android-Pakete umfassen rund 2,2 bis 2,4 GB; zusätzlicher Platz ist nötig.
3. **Test starten** wählen und einen eigenen bekannten Musikausschnitt auswählen. Der Assistent soll Googles Songsuche starten und die passende Anfrage automatisch auslesen.
4. Das Programm prüft, ob dieser Zugang vom Windows-Client wirklich funktioniert.
5. Erst bei einem gültigen Test wird Google als verfügbar angezeigt. Danach soll die vorübergehende Android-Umgebung geschlossen werden können.

Du sollst keinen API-Schlüssel suchen oder abtippen müssen. Dein persönliches Handy braucht für diesen vorgesehenen PC-Weg keine Änderung.

## Was daran noch entwickelt werden muss

Das automatische Vorbereiten, Auslesen und Testen ist ein Produktkonzept. Zuerst muss ein echter Durchlauf beweisen, dass die konkrete Google-App in der Testumgebung funktioniert und ihre benötigten Angaben liefert. Bisher wurden Quellen, Paketgrößen und Voraussetzungen untersucht; noch kein funktionierender Schlüssel gewonnen.

Der technisch relevante neue Ansatz ist eine eingebaute Netzwerkdiagnose von Cronet, beschrieben in der [Chromium-Dokumentation](https://github.com/chromium/chromium/blob/main/components/cronet/tracing.md#gathering-unredacted-netlogs). Er benötigt eine geeignete Testumgebung. Googles Verbindung wird dabei nicht durch ein anderes HTTPS-Zertifikat ersetzt.

Nach diesem Nachweis lässt sich eine echte Klick-für-Klick-Anleitung schreiben. Eine angeblich schon funktionierende Ein-Klick-Lösung wäre zum jetzigen Stand irreführend.

[Ausführliche Recherche und Quellen](GOOGLE_DEEP_DIVE.md)
