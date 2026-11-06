"""German/English interface text. Song names, paths and user input stay literal."""
import re
from tkinter import ttk

VERSION_LABEL='Version 1.13 - EMBER'
TEXT={
'KI':'AI','geprüft':'checked','KI bewertet Belege':'AI evaluating evidence',
'Fundstellen abgleichen':'Comparing sources','Remix-Fingerprints testen':'Checking remix fingerprints',
'KI bewertet neue Belege':'AI evaluating new evidence',
'Rekordbox-Export':'Rekordbox export','REKORDBOX-EXPORT':'REKORDBOX EXPORT',
'DATEI ZUWEISEN':'ASSIGN FILE','BIBLIOTHEKS-XML LADEN':'LOAD LIBRARY XML','NEU ZUORDNEN':'MATCH AGAIN',
'TEILEXPORT / SUCHLISTE':'PARTIAL EXPORT / SEARCH LIST','PLAYLIST FÜR REKORDBOX EXPORTIEREN':'EXPORT PLAYLIST FOR REKORDBOX',
'Nur als vollständige Playlist exportieren':'Only export a complete playlist','ZUORDNUNG':'FILE MATCH','AUDIODATEI':'AUDIO FILE',
'Alle erkannten Titel in Set-Reihenfolge. Es werden echte Audiodateien benötigt; Suchlinks reichen nicht.':'All identified tracks in set order. Actual audio files are required; search links are not enough.',
'Erkannte Referenzdatei':'Identified reference file','Eindeutig in der Bibliothek gefunden':'Unique library match',
'Mehrere Dateien · bitte zuweisen':'Multiple files · assign one','Audiodatei fehlt':'Audio file missing','Zugewiesen':'Assigned',
'Audiodatei für diesen Titel auswählen':'Choose the audio file for this track',
'KI-NACHPRÜFUNG':'AI REVIEW','KI-BEFUNDE':'AI FINDINGS','KI-PRÜFUNG':'AI REVIEW',
'Dateien':'Files','KI-NACHPRÜFUNG · LOKALES MODELL':'AI REVIEW · LOCAL MODEL',
'Die KI bewertet Remix-Grenzfälle anhand echter Fingerprints und gefundener Metadaten.':'AI reviews remix ambiguities using real fingerprints and retrieved metadata.',
'NUR KI ERNEUT PRÜFEN':'RERUN AI ONLY','TITEL / VERSION':'TITLE / VERSION',
'KI-BEWERTUNG':'AI ASSESSMENT','AUDIO-PRÜFUNG':'AUDIO CHECK','FUNDSTELLEN':'SOURCES',
'Name durch Belege gestützt':'Name supported by evidence','Unklar':'Uncertain','Versionskonflikt':'Version conflict',
'Starker lokaler Treffer':'Strong local match','Mehrdeutig':'Ambiguous','Kein Fingerprint-Treffer':'No fingerprint match',
'Referenz fehlt':'Missing reference','Wartet auf Offline-Engine':'Waiting for offline engine','Prüffehler':'Check failed',
'KI-Methode automatisch: Remixes, Grenzfälle und Fundstellen prüfen':'Automatic AI method: check remixes, borderline matches and sources',
'ABLAUF':'WORKFLOW','FORTSCHRITT':'PROGRESS','ERGEBNIS':'RESULTS','SCANNEN':'SCAN',
'SPEICHERN':'SAVE','ERNEUT PRÜFEN':'CHECK AGAIN','ERNEUT STARTEN':'RUN AGAIN','ABBRECHEN':'CANCEL',
'DURCHSUCHEN':'BROWSE','LINK LADEN':'LOAD LINK','HIER REINZIEHEN':'DROP FILE HERE',
'VORAUSSETZUNGEN':'REQUIREMENTS','LOKALE KI — OPTIONAL':'LOCAL AI — OPTIONAL',
'LM STUDIO ÖFFNEN':'OPEN LM STUDIO','LM STUDIO ZUWEISEN':'LOCATE LM STUDIO',
'MODELL / VERBINDUNG':'MODEL / CONNECTION','BERICHT MIT KI PRÜFEN':'REVIEW REPORT WITH AI',
'DATEIEN\nVORBEREITEN':'PREPARE\nFILES','SCHNELLSCAN':'QUICK SCAN','TIEFENSCAN 1':'DEEP SCAN 1',
'TIEFENSCAN 2':'DEEP SCAN 2','GESAMT':'OVERALL','GROSS ANZEIGEN':'LARGE VIEW',
'METHODEN / SCHNIPSEL':'METHODS / CLIPS','ZUKLAPPEN':'COLLAPSE','DETAILS':'DETAILS',
'SCAN-METHODEN':'SCAN METHODS','UNTERSCHRITTE / SCHNIPSEL':'SUBSTEPS / CLIPS',
'Alle':'All','Aus':'Off','Dateien vorbereiten':'Prepare files','Schnellscan':'Quick scan',
'Tiefenscan 1':'Deep scan 1','Tiefenscan 2':'Deep scan 2','Ergebnis':'Results','KI-Prüfung':'AI review',
'NR.':'NO.','ZEIT':'TIME','TITEL':'TITLE','METHODE':'METHOD','QUELLE':'SOURCE',
'Set-Bibliothek':'Set library','SET-BIBLIOTHEK':'SET LIBRARY','Titelliste':'Tracklist',
'TITELLISTE':'TRACKLIST','MAXIMIEREN':'MAXIMIZE','Titel / Künstler suchen':'Search title / artist',
'SET':'SET','GESPEICHERT':'SAVED','AKTUALISIEREN':'REFRESH','ZUM PRÜFEN LADEN':'LOAD FOR CHECKING',
'SUCHEN':'SEARCH','SCHLIESSEN':'CLOSE','ERGEBNIS ÖFFNEN':'OPEN RESULTS','ORDNER ÖFFNEN':'OPEN FOLDER',
'ERGEBNIS GESPEICHERT':'RESULTS SAVED','VORGANG ABGESCHLOSSEN':'TASK COMPLETED',
'ERKANNTE\nTRACKS':'IDENTIFIED\nTRACKS','ERGEBNISDATEI':'RESULT FILE','Protokoll':'Log',
'Erfolgreiche Treffer bleiben erhalten.':'Successful matches are retained.',
'Wähle die Methode. Die übrigen Methoden werden nicht neu gestartet.':'Choose a method. Other methods will not be restarted.',
'Der laufende Scan muss zuerst beendet oder abgebrochen werden.':'Finish or cancel the current scan first.',
'Suche nach Set, Künstler oder Titel · Doppelklick öffnet die Titelliste':'Search set, artist or title · Double-click opens the tracklist',
'Suchlinks öffnen die jeweilige Suche. Verfügbarkeit und kostenlose Downloads sind nicht bestätigt.':'Search links open each platform. Availability and free downloads are not confirmed.',
'Bereit für den ersten Scan':'Ready for the first scan','Noch kein Set ausgewählt':'No set selected',
'Bereit · neues Set auswählen':'Ready · choose a new set','Noch keine Treffer':'No matches yet',
'Noch nicht ausgeführt':'Not run yet','Nicht ausgeführt':'Not run','Nicht für diesen Lauf gewählt':'Not selected for this run',
'In der Set-Bibliothek gespeichert':'Saved in the set library','Noch kein Ergebnis zum Speichern vorhanden':'No results to save yet',
'Bereit':'Ready','Fehlt':'Missing','Prüfe …':'Checking …','EINRICHTEN':'SET UP','ANLEGEN':'CREATE',
'Musikdatenbank':'Music database','Offline-Engine':'Offline engine','Offline-Abgleich':'Offline matching',
'MUSIKDATENBANK  ·  Einmalig vorbereiten':'MUSIC DATABASE · One-time setup',
'DATENBANK AUFBAUEN / ERNEUERN':'BUILD / UPDATE DATABASE',
'Vorhandene .pklz-Datenbank importieren':'Import an existing .pklz database',
'ShazamIO · zusätzliche verteilte Proben':'ShazamIO · additional distributed samples',
'Gründliche Suche: 20 statt 6 Tempofaktoren (langsamer)':'Thorough search: 20 instead of 6 tempo factors (slower)',
'Tempoänderungen ohne Key Lock prüfen (langsamer)':'Check tempo changes without key lock (slower)',
'Max. Shazam-Anfragen:':'Maximum Shazam requests:','ORIGINAL-PROGRAMM':'ORIGINAL ENGINE',
'mix-id aktivieren (Shazam-basiert)':'Enable mix-id (Shazam-based)',
'LOKALE KI · OPTIONAL, NUR TEXTPRÜFUNG':'LOCAL AI · OPTIONAL, TEXT REVIEW ONLY',
'Ergebnis-TXT lokal auf Widersprüche prüfen (keine Audio-ID)':'Review result text locally for inconsistencies (no audio identification)',
'LM STUDIO HERUNTERLADEN':'DOWNLOAD LM STUDIO','KI-VERBINDUNG PRÜFEN':'CHECK AI CONNECTION',
'ALTERNATIVE: OLLAMA':'ALTERNATIVE: OLLAMA','ERGEBNISORDNER ÖFFNEN':'OPEN RESULTS FOLDER',
'Das lokale Sprachmodell erkennt keine Songs, sondern prüft den Trefferbericht.':'The local language model reviews the match report; it does not identify songs.',
'Einstellungen':'Settings','Lokale KI · Verbindung':'Local AI · Connection',
'Anbieter':'Provider','Chat-Modell (z. B. Gemma)':'Chat model (e.g. Gemma)',
'LM Studio · Programmdatei':'LM Studio · Executable','VERBINDUNG TESTEN':'TEST CONNECTION',
'SPEICHERN UND SCHLIESSEN':'SAVE AND CLOSE','LM STUDIO INSTALLIEREN':'INSTALL LM STUDIO',
'Deine Tracklist ist gespeichert und bereit.':'Your tracklist is saved and ready.',
'Nummeriert · chronologisch sortiert · gemeinsame Tracklist':'Numbered · chronological · combined tracklist',
'Beobachtungen':'Observations','Trefferkandidaten':'Match candidates',
}
WORDS={
'Audiodateien verfügbar':'audio files available','fehlen oder sind mehrdeutig':'missing or ambiguous',
'adaptive Nachprüfung':'adaptive follow-up','KI bewertet neue Belege':'AI evaluating new evidence',
'KI-Methode':'AI method','KI-Nachprüfung':'AI review','Fälle geprüft':'cases reviewed',
'Fundstellen abgleichen':'Compare sources','Remix-Fingerprints testen':'Test remix fingerprints','KI bewertet Belege':'AI evaluating evidence',
'Einstellungen':'Settings','Erkennungsdetails':'Recognition details','Ergebnis':'Results',
'Set-Bibliothek':'Set library','Titelliste':'Tracklist','Bereit':'Ready','Fehlt':'Missing',
'Fortschritt':'Progress','alle Einzelschritte':'all substeps','Einzelne Methoden erneut prüfen':'Rerun individual methods',
'Dateien vorbereiten':'Prepare files','Schnellscan':'Quick scan','Tiefenscan':'Deep scan',
'vorbereiten':'prepare','vergleichen':'match','Fenster':'windows','Schnipsel':'clips',
'Ausschnitte geprüft':'clips checked','Ausschnitt bereit':'Clip ready','Ausschnitt vorbereiten':'Prepare clip',
'Fingerabdruck bereit':'Fingerprint ready','Fingerabdruck vorbereiten':'Prepare fingerprint',
'Online-Suche':'Online search','geprüft · kein Treffer':'checked · no match','geprüft':'checked',
'gespeicherte Probe übernommen':'cached sample reused','gespeichert':'saved','Treffer':'matches',
'wartet':'waiting','fertig':'complete','Fehler':'Error','Abgebrochen':'Cancelled',
'Format / BPM':'Format / BPM','Voriger Lauf':'Previous run','Arbeiter':'Worker',
'Anfragelimit':'Request limit','automatischer Wiederholungsversuch in':'automatic retry in',
'Scan beendet':'Scan completed','Ergebnis gespeichert':'Results saved','Letztes Ergebnis geladen':'Last results loaded',
'Teilstand geladen':'Partial results loaded','SCANNEN startet offene Methoden automatisch':'SCAN resumes unfinished methods automatically',
'Teilprüfung gespeichert':'Partial results saved','Methoden offen':'Methods unfinished','SCANNEN zum Fortsetzen':'SCAN to continue',
'KI-Textprüfung gespeichert':'AI text review saved','KI-Textprüfung fertig':'AI text review complete',
'LM Studio erkannt · Modell wird geprüft':'LM Studio found · checking model','Optional · LM Studio zuweisen':'Optional · locate LM Studio',
'Laufenden Vorgang beenden · Set wird zurückgesetzt':'Stopping current task · resetting set',
'Bereit für den ersten Scan':'Ready for the first scan','Noch keine Treffer':'No matches yet',
}
REVERSE={v:k for k,v in TEXT.items() if v!=k}

class Language:
    def __init__(self,code='de'):self.code=code if code in ('de','en') else 'de'
    def __call__(self,text):
        text=str(text)
        if self.code=='de':return text
        if text in TEXT:return TEXT[text]
        value=text
        for source,target in sorted(WORDS.items(),key=lambda p:len(p[0]),reverse=True):
            value=re.sub(r'(?<!\w)'+re.escape(source)+r'(?!\w)',lambda m:target,value)
        return value
    def apply(self,root):
        def convert(widget,key,current,setter):
            cache=getattr(widget,'_language_values',None)
            if cache is None:widget._language_values={};cache=widget._language_values
            old=cache.get(key)
            source=old[0] if old and current==old[1] else REVERSE.get(current,current)
            value=self(source);cache[key]=(source,value)
            if value!=current:setter(value)
        def visit(widget):
            try:
                if getattr(widget,'_no_translate',False):return
                if widget.winfo_class() in ('Label','Button','Checkbutton','Labelframe','TLabel','TButton','TCheckbutton'):
                    variable=widget.cget('textvariable') if 'textvariable' in widget.keys() else ''
                    if variable:
                        current=str(widget.getvar(variable));convert(widget,'var',current,lambda v:widget.setvar(variable,v))
                    elif 'text' in widget.keys():convert(widget,'text',str(widget.cget('text')),lambda v:widget.configure(text=v))
                if isinstance(widget,ttk.Treeview):
                    for key in widget['columns']:
                        convert(widget,'heading:'+key,str(widget.heading(key,'text')),lambda v,k=key:widget.heading(k,text=v))
                if widget.winfo_class()=='Toplevel' and not getattr(widget,'_literal_title',False):convert(widget,'title',widget.title(),widget.title)
                for child in widget.winfo_children():visit(child)
            except Exception:pass # A transient window may close during an update.
        visit(root)

def tr(widget,text):
    translator=getattr(widget._root(),'_almighty_language',None)
    return translator(text) if translator else str(text)

class DialogProxy:
    def __init__(self,delegate):self.delegate=delegate;self.language=Language()
    def __getattr__(self,name):
        method=getattr(self.delegate,name)
        def call(*args,**kwargs):
            args=tuple(self.language(v) if isinstance(v,str) else v for v in args)
            kwargs={k:self.language(v) if k in ('title','message','detail') and isinstance(v,str) else v for k,v in kwargs.items()}
            return method(*args,**kwargs)
        return call
