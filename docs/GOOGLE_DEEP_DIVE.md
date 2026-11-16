# Google-Songerkennung: der einfachste belastbare Einrichtungsweg

Stand: 16.11.2026. Recherche und Konzept; keine fertige Google-Funktion. **Noch kein eigener App-Key und kein erfolgreicher ALMIGHTY→Google-Erkennungstest.**

## Ohne Google-Anmeldung: was daraus folgt

Die Songsuche ohne angemeldetes Konto ist mit einer App-Kennung vereinbar. Google beschreibt Standard-API-Keys als Zuordnung zu einem Projekt, ohne damit einen Benutzer zu authentifizieren. Ein persönlicher Google-Login und eine Kennung der aufrufenden App sind unterschiedliche Dinge. [Googles Erklärung](https://docs.cloud.google.com/docs/authentication/api-keys#standard_api_keys).

Der untersuchte Song-Search-Client verwendet tatsächlich weder OAuth noch Konto-Cookies. Damit ist ein Kontozwang für jeden ALMIGHTY-Nutzer durch diesen Client nicht begründet. Ob dieselbe App-Kennung zwischen Installationen, Versionen und PCs wiederverwendbar ist, muss dagegen noch gemessen werden. Ebenso wenig ist bisher belegt, dass jeder Nutzer eigene Werte erfassen muss.

**Unser eigener Zugangstest am 16.11.2026:** genau eine HTTP/2-gRPC-Anfrage ohne App-Key, Android-Identitätsheader, OAuth und Cookies; ausschließlich ein selbst erzeugter einsekündiger 440-Hz-Testton. Der Server lieferte HTTP 200, aber gRPC-Status **7 / PERMISSION_DENIED**, keinen Antwortinhalt. HTTP 200 allein ist hier kein Erfolg. Dieser nackte Aufruf wurde abgewiesen. Der Status verrät nicht, welche fehlende Kennung oder andere Voraussetzung ausschlaggebend war; er beweist weder, dass der Key allein genügt, noch die Unmöglichkeit jeder anderen anonymen Aufrufvariante. Der Versuch war keine echte Songidentifikation. [Testprotokoll](evidence/GOOGLE_KEYLESS_PROBE_2026-11-16.json), [offizielle Statusdefinition](https://grpc.io/docs/guides/status-codes/).

## Entscheidung

Zuerst gehört die Arbeit auf die **Entwicklerseite**: passende App-Kennung gewinnen und Wiederverwendbarkeit unabhängig von Benutzerkonto, Gerät und Sitzung prüfen. Falls ein gemeinsamer Zugang technisch funktioniert und für die Auslieferung geklärt ist, soll der normale Nutzer lediglich **Google aktivieren → Testclip prüfen** benötigen. Ein Android-Download für jeden Nutzer wäre dann unnötiger Aufwand. Das ist das bevorzugte Produktziel, noch kein nachgewiesenes Ergebnis.

Für den zuverlässiger begründeten Entwickler-Prototyp ist eine **isolierte Android-Testumgebung am PC** der aussichtsreichste Weg. Dort ist die interne Netzwerkdiagnose der Google-App zu prüfen, ohne ein HTTPS-Zertifikat auszutauschen. Ein geführter PC-Assistent zur individuellen Einrichtung bleibt eine Rückfalllösung, falls pro Installation tatsächlich eigene Werte benötigt werden. Er ist noch nicht gebaut oder durchgehend getestet.

Ein kurzer zusätzlicher Entwicklungsversuch kann prüfen, ob sich der passende Schlüssel direkt aus einer unveränderten Google-App-Datei lesen lässt. Das wäre möglicherweise schneller. Für genau den Song-Search-Schlüssel ist dies bisher aber **nicht nachgewiesen** und daher keine belastbare Nutzeranleitung.

## Was für einen Schlüssel wir überhaupt brauchen

Gemeint ist die Kennung des Google-App-Clients für den privaten Song-Search-Dienst. Das ist kein persönlicher Schlüssel, den jeder Nutzer in seinem Google-Konto erzeugt. Der vorhandene Client verwendet den App-Key zusammen mit Android-Paket, App-Zertifikat-Fingerabdruck und User-Agent. Im Quellcode ist nur der Key zwingend, die übrigen Header werden mitgesendet, wenn vorhanden; welche Beschränkungen Google tatsächlich durchsetzt, ist am Dienst zu prüfen. Für einen reproduzierbaren Test sollten alle vier Werte aus derselben App-Version stammen.

Der geprüfte [humtosong-Quellstand 7e0e5c8](https://github.com/niizam/humtosong/tree/7e0e5c8daf956a6781df247e8337bac7fbeeefd1) baut eine HTTP/2-gRPC-Anfrage an `speechs3proto2-pa.googleapis.com/.../S3Bidi` auf. Der Autor berichtet zwei erkannte Musikdateien; das ist noch keine unabhängige Bestätigung durch uns. Ein beliebiger Cloud-Key ist laut Projekt nicht als funktionierend belegt. Ein Web-/Gemini-Schlüssel ist daher kein belegter Ersatz. [Client](https://github.com/niizam/humtosong/blob/7e0e5c8daf956a6781df247e8337bac7fbeeefd1/client.go), [README](https://github.com/niizam/humtosong/blob/7e0e5c8daf956a6781df247e8337bac7fbeeefd1/README.md).

Wichtige Unterscheidung: `x-android-cert` bezeichnet die Signatur der Android-App. Das auf dem Foto gezeigte Google-Trust-Services-Serverzertifikat und das Reqable-CA-Zertifikat liefern diesen Wert nicht. Android-Clientbeschränkungen können Paket und SHA-1-Fingerabdruck verwenden. [Google-Key-Beschränkungen](https://docs.cloud.google.com/api-keys/docs/add-restrictions-api-keys).

## Was der Handy-Versuch tatsächlich bewiesen hat

Die Songsuche funktioniert ohne Reqable. Mit der getesteten Aufzeichnungskonfiguration bricht sie ab. Die gezeigten Aufnahmen enthalten `CONNECT`, 241 Byte, Status `Aborted`, keine entschlüsselte S3Bidi-Anfrage und keinen sichtbaren App-Key. Damit ist das Aufnahmeproblem eingegrenzt, **nicht** dessen exakter Zertifikats-/TLS-Mechanismus. Certificate Pinning darf daraus nicht als bewiesen behauptet werden.

Ein nachinstalliertes Benutzerzertifikat reicht für moderne Android-Apps nicht automatisch aus. Android unterscheidet den Benutzer- und den System-Vertrauensspeicher. Ein weiterer identischer Versuch oder ein erneuter Zertifikatexport löst diese Vertrauensfrage nicht. [Android-Vertrauensmodell](https://developer.android.com/privacy-and-security/security-config), [Reqable-Zertifikatanleitung](https://reqable.com/en-US/docs/getting-started/installation/).

## Vergleich der Wege

| Weg | Aufwand für Nutzer | Stand / Hindernis | Entscheidung |
| --- | --- | --- | --- |
| Normales Android + Reqable + Benutzerzertifikat | Mehrere Handy-Einstellungen und Zertifikatinstallation | Auf diesem Gerät in dieser Konfiguration gescheitert | Kein Standardweg für Einsteiger |
| Google-App-Datei unverändert auslesen | Datei auswählen oder USB-Verbindung durch Assistenten | APK ist analysierbar; der gesuchte Key kann fehlen, anders gespeichert oder dynamisch geliefert werden. Kein funktionierender Song-Key aus einer APK nachgewiesen | Begrenzter Entwicklungsversuch, keine Erfolgszusage |
| Android-Testsystem am PC + interne Cronet-Diagnose | Geplanter geführter Assistent, einmaliger größerer Download | Offiziell dokumentierte Diagnose unter passenden Bedingungen; Google-Song-Search-Ende-zu-Ende-Test fehlt | Primärer Prototyp für einen einfachen PC-Weg |
| PC-Testsystem + System-CA + Proxy | Gut automatisierbar, technisch mehr Eingriffe im Testsystem | Reqable dokumentiert diese Technik; zusätzliche App-Zertifikatsprüfungen können trotzdem scheitern | Zweite Wahl, wenn interne Diagnose nicht verfügbar ist |
| iPhone + Reqable | Profil und Zertifikatvertrauen auf dem Handy | iOS-Zertifikateinrichtung dokumentiert; keine erfolgreiche Google-Songsuche-Aufzeichnung hier belegt, andere App-Identität als Android | Kein belegter schneller Ersatz; kein Gerätekauf empfehlen |
| Logcat / normaler Netzwerkdump am normalen Handy | Scheinbar wenig Aufwand | Verbindungsdaten sind kein entschlüsselter App-Key; ungekürzte Cronet-Daten sind auf Produktionsgerät + Produktions-App ausdrücklich gesperrt | Nicht als einfachen Schlüssel-Export anbieten |
| Root/Magisk/Instrumentierung des persönlichen Handys | Hoher Eingriff, viele mögliche Fehler | Für Einsteiger nicht nötig als erster Forschungsweg | Aus der empfohlenen Einrichtung heraushalten |

## Der neue technische Ansatz: Diagnose statt Zertifikatsaustausch

Chromium dokumentiert für Cronet ungekürzte NetLogs einschließlich HTTP-Inhalten. Voraussetzungen: ausreichend neue Cronet-Version, ADB und ein `userdebug`-/`eng`-System **oder** eine als debuggable markierte App. Eine normale Produktions-App auf einem normalen Produktionshandy erfüllt das nicht. Das erklärt, warum „einfach USB und Logcat“ kein gleichwertiger Ausweg ist.

Im isolierten Testsystem wird `debug.cronet.trace_netlog` auf `everything` gesetzt und die Perfetto-Kategorie `disabled-by-default-netlog.sensitive` aktiviert. Die Aufzeichnung wird auf die Google-App begrenzt. Die Diagnose erfordert dabei keinen Proxy und kein ausgetauschtes HTTPS-Zertifikat. Die Eigenschaft wird beim Neustart zurückgesetzt. **Ob die konkrete Emulator-Google-App geeignete Events liefert, ist zu testen.** [Originaldokumentation mit Google-App-Filterbeispiel](https://github.com/chromium/chromium/blob/main/components/cronet/tracing.md#gathering-unredacted-netlogs).

Google dokumentiert außerdem eine Emulator-Schnittstelle `injectAudio`, die Audio in das virtuelle Mikrofon einspeist. Damit ist eine technische Grundlage für einen automatischen Testclip vorhanden; ein zusätzliches virtuelles Windows-Audiokabel ist nicht als zwingende Voraussetzung belegt. **Einspeisung und Erkennung müssen gemeinsam getestet werden.** [AOSP-Emulator-Schnittstelle](https://android.googlesource.com/platform/prebuilts/android-emulator/+/refs/heads/main/linux-x86_64/lib/emulator_controller.proto).

## So wird daraus eine Einrichtung für Einsteiger

Die folgende Bedienung ist die Rückfalllösung des noch zu bauenden Assistenten, wenn sich ein gemeinsamer Entwicklerzugang nicht bestätigen lässt. Sie ist nicht vorschnell jedem Nutzer aufzuerlegen:

1. **Google einrichten** drücken. Der Assistent prüft Windows-Voraussetzungen und zeigt Downloadgröße und benötigten Speicher an.
2. **Testumgebung vorbereiten.** Originalpakete laden, Prüfsummen kontrollieren, getrenntes Android-System anlegen und Google-App/Diagnosefähigkeit prüfen. Jeder Schritt meldet echten Fortschritt. Keine persönlichen Google-Konten in dieser Diagnoseumgebung verwenden.
3. **Test starten.** Einen eigenen bekannten Musikausschnitt auswählen. Der Assistent startet Googles Songsuche, speist den Clip ein und liest ausschließlich die relevante Anfrage aus. Bis die Audioautomatik funktioniert, bleibt diese Phase ein Entwicklertest.
4. **Zugang prüfen.** Genau die benötigten vier Header lokal übernehmen. Ein eigenständiger Windows-Client muss anschließend einen zweiten Clip anfragen können. Erst ein gültiges Dienstresultat bestätigt den Zugang. „Kein Treffer“ bei gültiger Dienstantwort ist etwas anderes als Schlüssel abgelehnt, Netzwerkfehler oder fehlender Header.
5. **Fertig.** Zugang lokal schützen, Diagnoseaufnahmen entfernen und Testsystem beenden. Ob bzw. wann erneute Einrichtung nötig ist, hängt von der tatsächlichen Gültigkeit des App-Zugangs ab; eine dauerhafte Einmaligkeit ist noch nicht belegt.

Der Nutzer soll keine Header abtippen, keine Root-Anleitung abarbeiten und keine Konsole benutzen müssen. Der Assistent darf bei Fehlschlägen nicht grün werden oder die übrigen Scanmethoden blockieren. Ein fehlender Key löst eine verständliche Diagnose aus.

## Pakete und konkrete Größen

Am 16.11.2026 wurden Googles offizielle Paketverzeichnisse erfolgreich abgerufen und ausgewertet, ohne die großen Pakete zu installieren:

| Originalpaket | Revision | Download |
| --- | --- | --- |
| Windows Platform-Tools | 37.0.1 | 8.044.989 Byte |
| Windows Emulator | 37.2.13 | 455.344.678 Byte |
| Android 15 / API 35, Google APIs, x86_64 | Revision 9 | 1.738.815.903 Byte |
| Optional SDK Command-Line Tools | 23.0.0 | 154.957.218 Byte |

Platform-Tools, Emulator und dieses Systemabbild ergeben rund **2,20 GB Download**, mit den optionalen Command-Line Tools rund **2,36 GB**. Entpackte Dateien und virtuelle Nutzerdaten benötigen zusätzlichen Platz. Java, Diagnoseauswertung oder zusätzliche Laufzeitabhängigkeiten sind damit noch nicht vollständig bilanziert. Es gibt keine gemessene Einrichtungsdauer und keine belastbare Zwei-Minuten-Zusage.

Die Paketdateien enthalten veröffentlichte Prüfsummen; hier wurden die Metadaten geprüft, nicht heruntergeladene Binärpakete. [Paketverzeichnis](https://dl.google.com/android/repository/repository2-1.xml), [Google-APIs-Systemabbilder](https://dl.google.com/android/repository/sys-img/google_apis/sys-img2-1.xml).

Bei der Abbildwahl ist Diagnosefähigkeit ausdrücklich zu prüfen. Ein Standard-Google-Play-Abbild ist nicht gleich einem frei diagnostizierbaren Testsystem; Google beschreibt die Einschränkungen und die Unterschiede der Images. Google APIs stellt Google Play services bereit, aber Verfügbarkeit und Version der benötigten Google-App sind zusätzlich zu kontrollieren. [AVD-Dokumentation](https://developer.android.com/studio/run/managing-avds). Emulator-Beschleunigung ist eine weitere Voraussetzung, keine durch reine RAM-Größe bewiesene Eigenschaft. [Windows-Beschleunigung](https://developer.android.com/studio/run/emulator-acceleration).

## Begrenzter APK-Versuch

ADB kann den Pfad einer installierten App ermitteln und lesbare APK-Dateien kopieren. APK Analyzer kann Manifest, Ressourcen und DEX untersuchen; apksigner kann App-Signaturen prüfen. Das ist eine dokumentierte Werkzeugbasis, **kein Beleg dafür, dass der richtige Google-Song-Key offen in jeder APK steht**. Zertifikat-Fingerabdruck und Paketname sind nur Teile des Zugangs. Unzugeordnete Key-Funde dürfen nicht wahllos gegen Dienste ausprobiert werden. [ADB](https://developer.android.com/tools/adb), [APK Analyzer](https://developer.android.com/tools/apkanalyzer), [apksigner](https://developer.android.com/tools/apksigner).

## Abnahmekriterien, bevor wir eine funktionierende Anleitung veröffentlichen

- Ohne manuelle Änderung am persönlichen Handy reproduzierbar von leerem Testordner bis zur Anfrage kommen.
- Passende Google-App und Diagnosefähigkeit automatisch erkennen; verständliche Fehlermeldung, wenn etwas fehlt.
- Eine echte `sound-search`-/S3Bidi-Anfrage lesen und ihre Werte lokal zuordnen können.
- Mit dem erfassten Zugang einen echten bekannten Clip direkt vom Windows-Client erkennen; eine zweite Probe und eine gültige Kein-Treffer-Antwort getrennt prüfen.
- Dieselben Werte in einem zweiten unabhängigen Windows-Prozess und einer frischen Android-Sitzung ohne Google-Konto testen. Geräte-, Sitzungs-, Versions- und Netzabhängigkeit einzeln prüfen; nicht aus einem einzigen Treffer auf einen universellen Zugang schließen.
- Dienstfehler, Sperren, Zeitüberschreitungen und ungültige Antworten niemals als erfolgreichen Zugang darstellen.
- Keine Keys in Git, Programm-Downloads, Fotosammlungen oder allgemeine Protokolle übernehmen. Nur die eigene relevante Anfrage verwenden.
- Nach dem ersten erfolgreichen Aufbau einen zweiten Durchlauf testen. Genau dessen tatsächliche Bedienung dokumentieren und die benötigte Zeit messen.

## Ergebnis dieser Recherche

Der Nutzer muss sich nicht bei Google anmelden, damit die App eine Kennung mitsendet. Unser direkter Aufruf ohne sämtliche Kennungen wurde abgewiesen. Der nächste Nachweis ist deshalb ein funktionierender App-Zugang und dessen Wiederverwendbarkeit, nicht das Anlegen persönlicher Google-Cloud-Schlüssel.

Der normale Handy-Mitschnitt ist für uns derzeit kein Einsteigerweg. Die **interne Cronet-Diagnose auf einem getrennten PC-Testsystem** ist ein wesentlich besser begründeter Entwickleransatz als weitere CA-Versuche auf dem persönlichen Handy. Der erfolgreiche Gesamtweg zum Song-Key wurde hier noch nicht ausgeführt. Die APK-Abkürzung bleibt eine zusätzliche, enger zu prüfende Hypothese.

Google bleibt ein inoffizieller Dienstzugang: Eine garantierte kostenlose Quote, zulässige öffentliche Weitergabe von App-Zugangsdaten und dauerhafte Verfügbarkeit sind durch diesen Quellcode nicht zugesichert. Die bestehende ALMIGHTY-Version bekommt durch diese Dokumente keine Google-Methode.
