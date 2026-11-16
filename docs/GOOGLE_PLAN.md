# Google-Songerkennung – aktualisierter Plan

Stand: 16.11.2026. **Google ist nicht in ALMIGHTY eingebaut. Es wurde noch kein eigener funktionierender App-Key gewonnen.**

Der Versuch auf dem normalen Android-Handy ist in der getesteten Reqable-Konfiguration gescheitert: Ohne Aufzeichnung funktioniert die Songsuche, mit Aufzeichnung entstehen abgebrochene CONNECT-Verbindungen. Das genaue TLS-Problem ist nicht bewiesen; die Fotos zeigen keine entschlüsselte S3Bidi-Anfrage.

**Kein Google-Login heißt nicht keine App-Kennung.** Der untersuchte Client nutzt einen App-Key, aber kein OAuth und keine Konto-Cookies. Es ist nicht belegt, dass jeder Nutzer eigene Werte erfassen muss. Das bevorzugte Ziel ist ein auf Entwicklerseite geprüfter Zugang, den der Nutzer nur aktiviert. Gemeinsame Wiederverwendbarkeit ist noch zu testen.

Ein eigener einzelner Aufruf ohne App-Key, Android-Identitätsheader und Konto-Anmeldung lieferte HTTP 200 mit gRPC 7 / PERMISSION_DENIED. Verwendet wurde nur ein selbst erzeugter Testton. Damit ist dieser nackte Aufruf gescheitert; die genaue fehlende Voraussetzung lässt sich aus dem Status allein nicht bestimmen. [Testprotokoll](evidence/GOOGLE_KEYLESS_PROBE_2026-11-16.json).

Die ursprüngliche Annahme, dass eine einfache Benutzerzertifikat-Installation auf jedem Android-Gerät genügt, ist kein tragfähiger Einsteigerweg. Der Entwickler-Prototyp soll stattdessen eine isolierte Android-Testumgebung und interne Cronet-Netzwerkdiagnose prüfen, ohne Zertifikatsaustausch. Eine direkte Auswertung der unveränderten Google-App-Datei ist eine zusätzliche, noch unbewiesene Abkürzung. Ein geführter PC-Assistent für jeden Nutzer ist erst dann sinnvoll, wenn sich installationsbezogene Werte als notwendig erweisen.

- [Deep Dive: belegte Möglichkeiten, Grenzen, Größen und technische Abnahme](GOOGLE_DEEP_DIVE.md)
- [Entwurf des einfachen Nutzerablaufs](GOOGLE_SETUP_EINFACH.md)

Zuerst müssen Google-App, Diagnose und ein echter Windows-Erkennungstest gemeinsam funktionieren. Erst dann wird daraus eine Google-Methode in ALMIGHTY. Die bestehende Anwendung bleibt bis dahin bei ihren vorhandenen Erkennungsmethoden. Ein beliebiger Cloud-/Gemini-Key ist nicht als Zugang zu diesem privaten Dienst belegt.

Der untersuchte Windows-Client ist [humtosong, Quellstand 7e0e5c8](https://github.com/niizam/humtosong/tree/7e0e5c8daf956a6781df247e8337bac7fbeeefd1). Die neue Diagnosemöglichkeit steht in [Chromiums Originaldokumentation](https://github.com/chromium/chromium/blob/main/components/cronet/tracing.md#gathering-unredacted-netlogs).
