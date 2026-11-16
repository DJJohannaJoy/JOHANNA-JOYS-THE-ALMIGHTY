# Google Song Search · reproduzierbarer Stand vom 16.11.2026

## Ergebnis

Die zuvor nur geplante Anbindung funktioniert als eigenständige Windows-Methode. Ein angemeldetes Google-Konto ist für die getesteten Anfragen nicht erforderlich. Eine leere beziehungsweise nicht vorhandene Kennung wurde dagegen abgelehnt. Das Fehlen einer Anmeldung bedeutet deshalb nicht, dass der Dienst ohne App-Identität nutzbar ist.

## Herkunft der eigenen App-Identität

Untersucht wurde das offizielle Google-APIs-Systemabbild:

`https://dl.google.com/android/repository/sys-img/google_apis/x86_64-34_r14.zip`

- Verifizierte veröffentlichte ZIP-SHA1: `e0f6c9a0691aa27bd597d0deb1bcfdc943ac8ca7`.
- Extrahiertes APK: `/product/priv-app/Velvet/Velvet.apk`.
- APK-SHA256: `03694961b35e9e4f10ed70b0a80848f2685e41b361d268a352acba4c6bb72b40`.
- Paket `com.google.android.googlequicksearchbox`, Version `13.17.16.23.x86_64`, Versionscode `301194889`.
- Die Klasse `com.google.android.apps.search.soundsearch.g.i`, Methode `d`, setzt die Sound-Search-Header `X-Goog-Api-Key`, `X-Android-Package` und `X-Android-Cert`.
- Das öffentliche App-Signaturmerkmal lautet `58E1C4133F7441EC3D2C270270A14802DA47BA0E`.

Der Schlüssel wurde gezielt aus dieser Sound-Search-Stelle gewonnen. Andere eingebettete Schlüssel wurden nicht gegen den Dienst durchprobiert. Die Kennung und rohe Mitschnitte bleiben außerhalb des Repositories. Das untersuchte Abbild wurde nicht installiert; das Handy wurde dafür nicht verändert.

## Protokoll und produktive Verarbeitung

Der Client verwendet HTTP/2 und gRPC für `/speech.s3.S3StubbyClientConnectorService/S3Bidi` auf `speechs3proto2-pa.googleapis.com`. FFmpeg erstellt einen kurzen AAC/ADTS-Ausschnitt mit 16 kHz und einem Kanal. Die Anwendung setzt eine feste Frist pro Anfrage, begrenzt Antwortgröße und Parallelität und wertet HTTP- sowie gRPC-Status aus. Komprimierte Antworten werden strikt geprüft. Der erste Kandidat wird als Online-Beobachtung übernommen; Alternativen bleiben am Datensatz erhalten.

Das öffentliche MIT-Projekt [niizam/humtosong](https://github.com/niizam/humtosong), Stand `7e0e5c8daf956a6781df247e8337bac7fbeeefd1`, lieferte das Schema als Ausgangspunkt. Die zugehörige Lizenz liegt unter `licenses/humtosong-MIT.txt`.

## Messungen

| Test | Ergebnis |
|---|---|
| Synthetischer Ton ohne Kennung | HTTP 200, gRPC 7 / PERMISSION_DENIED |
| Synthetischer Ton mit App-Kennung | HTTP 200, gRPC 0, 26 Byte, kein Treffer, 197 ms |
| Eigener vorhandener Set-Ausschnitt, 20 s | HTTP 200, gRPC 0, 1051 Byte, Kandidat nach 3244 ms |
| Zweiter Ausschnitt, neuer Prozess | HTTP 200, gRPC 0, 26 Byte, kein Treffer nach 2318 ms |
| Produktiver ALMIGHTY-Adapter | 1/1 geprüft, ein Kandidat, keine Fehler |

Zurückgegebener Kandidat: **Darkness Is Beauty in the Right Hands – Tanzanfall**, YouTube-ID `-q9ucvgMHRw`. Die Erkennung wurde nicht durch eine unabhängige Soll-Trackliste bestätigt. Die Tests wurden auf einem Windows-PC ausgeführt, nicht auf verschiedenen PCs oder Netzwerken. Daraus folgt keine Garantie einer öffentlichen, unbegrenzt kostenlosen oder dauerhaft stabilen API.

## Einordnung der Handyversuche

Die Fotos zeigten überwiegend CONNECT-Tunnel mit 241 Byte Headern und leerem Body; später brachen TLS-Verbindungen ab. Solche Einträge enthalten weder eine auslesbare Song-Antwort noch automatisch den benötigten Schlüssel. Zertifikatsinstallation allein garantiert bei der Google-App keinen entschlüsselbaren Mitschnitt. Die APK-Untersuchung umgeht diese fehleranfällige Einrichtung für den hier getesteten Zugang.
