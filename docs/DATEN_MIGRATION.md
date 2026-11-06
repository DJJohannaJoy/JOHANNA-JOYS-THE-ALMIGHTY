# Importing user's local Desktop SET SCANNER data

This exported project cannot access the user’s Windows desktop. It preserves all source code and available reference files from the conversation. But the user's live `Desktop\SET SCANNER` may contain a fingerprint database, installed runtime engines and old scan results not available in this export.

On the user's PC, after extracting the ZIP to their desired development directory, double-click `2_BESTEHENDE_SCANNER_DATEN_IMPORTIEREN.bat`. This copies **Datenbank, Ergebnisse, Protokolle and available config JSON** to `APP/` without deleting the originals. Existing destination files are not overwritten by the default import. The script deliberately does **not** copy `.venv`, `node_modules`, huge `.exe` runtimes, or arbitrary music files into the project.

For a full Windows runtime test, install the tool on that Windows machine via `1_INSTALLIEREN_ODER_AKTUALISIEREN.bat`; it may download third-party components on first run.

Do not commit the copied data, private paths, keys or results to a public repository. `.gitignore` excludes them.
