# KI-Antworten automatisch nachprüfen

Eine abgeschnittene Modellantwort beendete früher den gesamten KI-Lauf: Beim gemeldeten Set waren dadurch nur 12 von 24 Fällen geprüft.

LM Studio erhält jetzt ein begrenztes JSON-Schema und mehr Platz für die Antwort. Abgeschnittene, fehlende oder ungültige Antworten werden nicht übernommen. Betroffene Fälle werden automatisch einzeln mit erweitertem Ausgabelimit erneut angefragt. Alle übrigen Fälle laufen weiter. Jeder abgeschlossene Fall wird sofort gespeichert.

Kann ein Fall auch nach den begrenzten Wiederholungen nicht bewertet werden, bleibt er ausdrücklich als unvollständig sichtbar. Die Originalerkennungen und Belege bleiben erhalten. Ein erneuter KI-Lauf übernimmt erfolgreiche unveränderte Bewertungen aus dem Cache und prüft fehlende/fehlerhafte Fälle erneut. Dafür ist kein kompletter Set-Scan nötig.

Regression: `tests/ai_recovery_test.py` simuliert die Abschneidung exakt bei 12/24, automatische Wiederholung, dauerhaft fehlerhafte Einzelantworten und eine Antwort mit fehlendem Fall.

Live geprüft: Der tatsächlich bei 12/24 stehengebliebene Lauf wurde mit dem geladenen Modell `google/gemma-4-e4b` fortgesetzt. Die zwölf vorhandenen Bewertungen wurden übernommen; die restlichen zwölf Fälle wurden abgearbeitet. Nach 98,27 Sekunden: 24/24 Fälle, vollständig, keine fehlgeschlagenen Bewertungen. Das bedeutet geprüfte Fälle, keine automatische Audio-Bestätigung aller Songs. Die Zusammenfassung steht in `docs/proof/KI_RESUME_24_OF_24.json`.

Schema-Schnittstelle: https://lmstudio.ai/docs/developer/openai-compat/structured-output

Die Hauptanzeige unter **Fortschritt** zeigt nun direkt `KI: 9/24 geprüft`, den aktuellen Arbeitsschritt und den Titel. Eine laufende Sekundenanzeige zeigt, wie lange dieser Schritt dauert. Fertige Fälle werden einzeln gezählt; echte erledigte Unterschritte gehen anteilig in die KI- und Gesamtprozente ein. Die verstrichene Zeit erzeugt keinen künstlichen Fortschritt. Die Anzeige nutzt die vorhandene Kopfzeile, ohne den Ergebnisbereich zu verkleinern.
