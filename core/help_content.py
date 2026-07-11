from html import escape

from .config import APP_NAME, APP_TAGLINE, DSGVO_CLAIM, GESOB_DIR, SETTINGS_PATH


def build_help_html() -> str:
    run_dir = escape(str(GESOB_DIR))
    settings_path = escape(str(SETTINGS_PATH))
    app_name = escape(APP_NAME)
    tagline = escape(APP_TAGLINE)
    dsgvo_claim = escape(DSGVO_CLAIM)

    parts = [
        """
<html>
<head>
<style>
body {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #1f2937;
    margin: 14px;
}
h1, h2, h3 {
    color: #0f172a;
}
h1 {
    margin-bottom: 4px;
}
h2 {
    margin-top: 22px;
    border-bottom: 1px solid #dbe4f0;
    padding-bottom: 4px;
}
h3 {
    margin-top: 18px;
    margin-bottom: 6px;
}
p, li {
    margin-top: 4px;
    margin-bottom: 4px;
}
code {
    background: #f3f4f6;
    padding: 1px 4px;
    border-radius: 4px;
    font-family: Consolas, "Courier New", monospace;
}
.box {
    background: #f8fafc;
    border: 1px solid #dbe4f0;
    border-radius: 8px;
    padding: 10px 12px;
    margin: 10px 0 16px 0;
}
.hint {
    background: #fff8e6;
    border: 1px solid #f2d38a;
    border-radius: 8px;
    padding: 10px 12px;
    margin: 12px 0;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin-top: 8px;
}
th, td {
    border: 1px solid #dbe4f0;
    text-align: left;
    padding: 6px 8px;
    vertical-align: top;
}
th {
    background: #eef4fb;
}
a {
    color: #1d4ed8;
    text-decoration: none;
}
ul, ol {
    margin-top: 6px;
}
</style>
</head>
<body>
""",
        f"<h1>{app_name}</h1>",
        f"<p><b>{tagline}</b></p>",
        f"<p>{dsgvo_claim}</p>",
        """
<div class="box">
<b>Inhalt</b>
<ul>
  <li><a href="#quickstart">Schnellstart</a></li>
  <li><a href="#eingaben">Welche Dateien werden ben&ouml;tigt?</a></li>
  <li><a href="#hauptfenster">Hauptfenster</a></li>
  <li><a href="#einstellungen">Einstellungen</a></li>
  <li><a href="#ablauf">Pr&uuml;fen, Dry-Run und echter Versand</a></li>
  <li><a href="#nachricht">Funktion &bdquo;Nachricht senden&ldquo;</a></li>
  <li><a href="#berichte">Berichte und erzeugte Dateien</a></li>
  <li><a href="#platzhalter">Platzhalter im E-Mail-Text</a></li>
  <li><a href="#fehler">H&auml;ufige Fehler und L&ouml;sungen</a></li>
</ul>
</div>
""",
        """
<h2 id="quickstart">Schnellstart</h2>
<ol>
  <li>&Ouml;ffnen Sie <b>Einstellungen</b> und richten Sie zuerst Versandart, Unternehmen, E-Mail-Text, PDF-Passwort und Zeitraum ein.</li>
  <li>W&auml;hlen Sie im Hauptfenster den <b>Eingabemodus</b>, die <b>PDF-Quelle</b> und die passende <b>Excel-Datei</b>.</li>
  <li>Klicken Sie zuerst auf <b>Adressen pr&uuml;fen</b>. So sehen Sie, ob PersNr, PDFs und E-Mail-Adressen sauber zusammenpassen.</li>
  <li>Pr&uuml;fen Sie Tabelle, Log und Berichte. Beheben Sie zuerst rote Fehler.</li>
  <li>F&uuml;hren Sie danach einen <b>Dry-Run</b> aus. Dabei werden PDF-Anh&auml;nge vorbereitet, aber keine echten E-Mails versendet.</li>
  <li>Wenn alles korrekt aussieht, deaktivieren Sie <b>Dry-Run</b> und starten Sie den echten Versand.</li>
</ol>
<div class="hint">
<b>Empfohlene Reihenfolge:</b> Erst <b>Adressen pr&uuml;fen</b>, dann <b>Dry-Run</b>, danach erst <b>echter Versand</b>.
</div>
""",
        """
<h2 id="eingaben">Welche Dateien werden ben&ouml;tigt?</h2>
<h3>1. Excel-Datei</h3>
<p>Die Excel-Datei muss mindestens die Spalten <code>PersNr</code> und <code>Email</code> enthalten. Optional k&ouml;nnen auch <code>Name</code> und <code>Vorname</code> vorhanden sein.</p>
<ul>
  <li><code>PersNr</code> muss eine ganze Zahl mit maximal 5 Stellen sein.</li>
  <li>Doppelte <code>PersNr</code> oder doppelte E-Mail-Adressen sind nicht erlaubt.</li>
  <li>Dateiformat: nur <code>.xlsx</code> oder <code>.xlsm</code>.</li>
</ul>

<h3>2. PDF-Quelle</h3>
<p>Es gibt zwei Modi:</p>
<table>
  <tr><th>Modus</th><th>Was erwartet das Programm?</th></tr>
  <tr>
    <td><b>PDF-Ordner mit fertigen Dateien</b></td>
    <td>Ein Ordner mit bereits benannten Mitarbeiter-PDFs, z.&nbsp;B. <code>02548.pdf</code>, <code>02548_1.pdf</code>, <code>02548_2.pdf</code>.</td>
  </tr>
  <tr>
    <td><b>Eine Gesamt-PDF zum Aufteilen</b></td>
    <td>Eine einzige PDF. Das Programm trennt die Seiten auf und sucht darin nach der Personalnummer im Muster <code>Pers.-Nr. 2548</code>.</td>
  </tr>
</table>

<h3>Dateinamensregeln im Ordner-Modus</h3>
<ul>
  <li>Erlaubt sind z.&nbsp;B. <code>2548.pdf</code>, <code>02548.pdf</code>, <code>2548_1.pdf</code>, <code>02548_2.pdf</code>.</li>
  <li>Dateien mit falschem Namen werden als ung&uuml;ltig gemeldet.</li>
  <li>Mehrere PDFs mit derselben PersNr werden in der Reihenfolge <code>02548.pdf</code>, <code>02548_1.pdf</code>, <code>02548_2.pdf</code> zusammengef&uuml;hrt.</li>
</ul>

<h3>Was passiert im Modus &bdquo;Eine Gesamt-PDF zum Aufteilen&ldquo;?</h3>
<ul>
  <li>Jede Seite wird einzeln gespeichert.</li>
  <li>Wenn eine PersNr erkannt wird, wird die Seite passend umbenannt.</li>
  <li>Wenn keine PersNr erkannt wird, bleibt die Seite als <code>unmatched_001.pdf</code>, <code>unmatched_002.pdf</code> usw. zur&uuml;ck und wird sp&auml;ter als Problem sichtbar.</li>
</ul>
""",
        """
<h2 id="hauptfenster">Hauptfenster</h2>
<table>
  <tr><th>Bereich</th><th>Bedeutung</th></tr>
  <tr><td><b>Eingabemodus</b></td><td>W&auml;hlt, ob Sie mit einem PDF-Ordner oder einer Gesamt-PDF arbeiten.</td></tr>
  <tr><td><b>PDF-Quelle</b></td><td>Pfad zum Ordner oder zur PDF-Datei.</td></tr>
  <tr><td><b>Excel-Datei</b></td><td>Pfad zur Mitarbeiterliste mit PersNr und E-Mail-Adressen.</td></tr>
  <tr><td><b>Unternehmen</b></td><td>Aktives Unternehmen f&uuml;r Firmenname, Standard-Excel-Datei und Platzhalter <code>{company_name}</code>.</td></tr>
  <tr><td><b>Dry-Run</b></td><td>Bereitet alles vor, versendet aber keine echten E-Mails.</td></tr>
  <tr><td><b>Adressen pr&uuml;fen</b></td><td>Pr&uuml;ft PDFs und Excel, erstellt Audit-Datei und ggf. Sammel-PDF ohne E-Mail.</td></tr>
  <tr><td><b>E-Mails senden</b></td><td>Zeigt zuerst eine Versand-Vorschau und startet danach den Versand an alle passenden Mitarbeiter.</td></tr>
  <tr><td><b>Nur ausgew&auml;hlte senden</b></td><td>Sendet nur an Mitarbeiter, die in der ersten Spalte markiert sind.</td></tr>
  <tr><td><b>Filter</b></td><td>Filtern nach PersNr, E-Mail oder Status; die Tabelle bleibt trotzdem vollst&auml;ndig im Hintergrund erhalten.</td></tr>
  <tr><td><b>Log</b></td><td>Zeigt Fortschritt, Warnungen, Fehler und Speicherorte der erzeugten Dateien.</td></tr>
</table>

<h3>Tabelle und Statusfarben</h3>
<ul>
  <li><b>Gr&uuml;n:</b> <code>OK</code> oder <code>Gesendet</code></li>
  <li><b>Gelb:</b> <code>Dry-Run</code> oder <code>Keine Dateien</code></li>
  <li><b>Rot:</b> <code>Fehler</code> oder <code>Keine E-Mail</code></li>
</ul>
<p>Die Spalte <b>Auswahl</b> ist wichtig f&uuml;r <b>Nur ausgew&auml;hlte senden</b>. Mit <b>Alle markieren</b> und <b>Alle abw&auml;hlen</b> steuern Sie die Auswahl schnell.</p>
""",
        """
<h2 id="einstellungen">Einstellungen</h2>
<h3>E-Mail-Einstellungen</h3>
<ul>
  <li><b>Versandmethode:</b> <code>smtp</code> oder <code>outlook</code>.</li>
  <li><b>SMTP Server / Port / Sicherheit / Benutzer / Passwort / Timeout:</b> nur f&uuml;r SMTP-Versand.</li>
  <li><b>Absender E-Mail:</b> Absenderadresse f&uuml;r SMTP oder Kennung des Outlook-Kontos.</li>
  <li><b>Outlook Konto:</b> auf Windows k&ouml;nnen gefundene Outlook-Konten geladen und ausgew&auml;hlt werden.</li>
  <li><b>Absender Name:</b> erscheint im Absender und steht als Platzhalter <code>{from_name}</code> zur Verf&uuml;gung.</li>
</ul>

<h3>Outlook-Versand mit mehreren Konten</h3>
<ul>
  <li>W&auml;hlen Sie <code>outlook</code> als Versandmethode.</li>
  <li>Klicken Sie auf <b>Konten laden</b>.</li>
  <li>W&auml;hlen Sie das gew&uuml;nschte Outlook-Konto aus der Liste.</li>
  <li>Die Auswahl wird in <b>Absender E-Mail</b> &uuml;bernommen und f&uuml;r den Versand verwendet.</li>
  <li>Wenn Sie <b>Automatisch</b> lassen, kann Outlook das erste Konto im Profil verwenden.</li>
</ul>

<h3>Unternehmen</h3>
<ul>
  <li>Hier pflegen Sie Firmen-ID, Firmenname und die Standard-Excel-Datei pro Unternehmen.</li>
  <li><b>Neu</b> erstellt einen weiteren Unternehmenseintrag.</li>
  <li><b>L&ouml;schen</b> entfernt das aktuell markierte Unternehmen; mindestens ein Unternehmen muss erhalten bleiben.</li>
  <li>Das aktive Unternehmen steuert Standardwerte und den Platzhalter <code>{company_name}</code>.</li>
</ul>

<h3>E-Mail-Text</h3>
<ul>
  <li>Sie k&ouml;nnen <b>Betreff</b> und <b>Text</b> anpassen.</li>
  <li>Formatierung ist m&ouml;glich: <b>Fett</b>, <b>Kursiv</b>, <b>Unterstr.</b>, <b>Liste</b>, Ausrichtung, Schriftgr&ouml;&szlig;e und Farbe.</li>
  <li><b>Vorschau</b> zeigt eine Beispielmail mit Platzhaltern.</li>
  <li><b>Test-E-Mail senden</b> verschickt eine Testmail mit einer kleinen Test-PDF als Anhang.</li>
</ul>

<h3>PDF / Passwort</h3>
<ul>
  <li>Wenn <b>PDF verschl&uuml;sseln</b> aktiv ist, wird f&uuml;r jeden Mitarbeiter eine gesch&uuml;tzte PDF erzeugt.</li>
  <li>Das Passwort wird so aufgebaut: <code>Prefix + PersNr + Suffix</code>.</li>
  <li>Beispiel: Prefix <code>abc-</code> und Suffix <code>-2026</code> ergibt f&uuml;r PersNr <code>02548</code> das Passwort <code>abc-02548-2026</code>.</li>
</ul>

<h3>Zeitraum / UI</h3>
<ul>
  <li><b>automatic_current_month:</b> aktueller Monat</li>
  <li><b>automatic_previous_month:</b> Vormonat</li>
  <li><b>manual:</b> frei gew&auml;hlter Monat und Jahr</li>
  <li>Diese Einstellung beeinflusst die Platzhalter <code>{monat}</code> und <code>{jahr}</code>.</li>
  <li><b>Dry-Run standardm&auml;&szlig;ig aktiv</b> setzt den Startzustand im Hauptfenster.</li>
  <li><b>Letzte Pfade merken</b> speichert zuletzt verwendete PDF- und Excel-Pfade.</li>
</ul>
""",
        """
<h2 id="ablauf">Pr&uuml;fen, Dry-Run und echter Versand</h2>
<h3>1. Adressen pr&uuml;fen</h3>
<p>Diese Funktion sendet nichts. Sie dient nur der Kontrolle:</p>
<ul>
  <li>PDF-Dateien werden gelesen und gruppiert.</li>
  <li>Excel-Daten werden geladen.</li>
  <li>PersNr aus PDFs und Excel werden abgeglichen.</li>
  <li>Eine Audit-Datei wird erzeugt.</li>
  <li>F&uuml;r Mitarbeiter ohne E-Mail wird eine Sammel-PDF erstellt.</li>
</ul>

<h3>2. E-Mails senden mit Dry-Run</h3>
<ul>
  <li>Vor dem eigentlichen Versand sehen Sie eine <b>Versand-Vorschau</b>.</li>
  <li>Mit aktivem <b>Dry-Run</b> werden Mitarbeiter-PDFs vorbereitet und Berichte erzeugt, aber es werden keine E-Mails verschickt.</li>
  <li>Diese Stufe ist ideal f&uuml;r die Endkontrolle von Betreff, Empf&auml;ngern, Anh&auml;ngen und Passw&ouml;rtern.</li>
</ul>

<h3>3. Echter Versand</h3>
<ul>
  <li>Deaktivieren Sie <b>Dry-Run</b>.</li>
  <li>Starten Sie erneut <b>E-Mails senden</b> oder <b>Nur ausgew&auml;hlte senden</b>.</li>
  <li>Das Programm pr&uuml;ft zuerst die Verbindung zu SMTP oder Outlook.</li>
  <li>Danach wird pro Mitarbeiter die PDF erzeugt, optional verschl&uuml;sselt und versendet.</li>
</ul>
""",
        """
<h2 id="nachricht">Funktion &bdquo;Nachricht senden&ldquo;</h2>
<p>Diese Funktion finden Sie im Men&uuml; <b>Nachricht</b>. Sie ist f&uuml;r Rundschreiben gedacht und arbeitet anders als der Versand von Lohnabrechnungen.</p>
<ul>
  <li>Es werden <b>keine PDF-Anh&auml;nge</b> mitgesendet.</li>
  <li>Empf&auml;nger kommen aus der Excel-Datei des gew&auml;hlten Unternehmens.</li>
  <li>Es werden nur Zeilen mit E-Mail-Adresse verwendet.</li>
  <li>Vor dem Start sehen Sie eine Vorschau von Betreff, Nachricht und Empf&auml;ngerliste.</li>
  <li>F&uuml;r diese Funktion gibt es keinen separaten Dry-Run-Modus.</li>
</ul>
""",
        f"""
<h2 id="berichte">Berichte und erzeugte Dateien</h2>
<p>Alle Laufdaten werden aktuell unter folgendem Ordner abgelegt:</p>
<p><code>{run_dir}</code></p>
<table>
  <tr><th>Datei / Ordner</th><th>Bedeutung</th></tr>
  <tr><td><code>audit_check.xlsx</code></td><td>Pr&uuml;fbericht mit PDF-/Excel-Abgleich und Auff&auml;lligkeiten.</td></tr>
  <tr><td><code>ohne_email_gesamt.pdf</code></td><td>Sammel-PDF f&uuml;r Mitarbeiter, zu denen eine PDF vorhanden ist, aber keine E-Mail-Adresse in Excel.</td></tr>
  <tr><td><code>send_report.xlsx</code></td><td>Versandbericht mit Status, Anh&auml;ngen, Passwort und Fehlern.</td></tr>
  <tr><td><code>prepared_pdfs</code></td><td>Erzeugte Mitarbeiter-PDFs bzw. verschl&uuml;sselte Anh&auml;nge aus dem Versandlauf.</td></tr>
  <tr><td><code>output_pages</code></td><td>Nur im Modus Gesamt-PDF: aufgeteilte Einzelseiten.</td></tr>
  <tr><td><code>_test_mail</code></td><td>Tempor&auml;rer Bereich f&uuml;r Testmails.</td></tr>
 </table>

<p>Die Men&uuml;eintr&auml;ge unter <b>Berichte</b> werden erst aktiv, wenn die jeweilige Datei im letzten Lauf erzeugt wurde.</p>

<h3>Wo werden Einstellungen gespeichert?</h3>
<p>Die Benutzereinstellungen werden in folgender Datei gespeichert:</p>
<p><code>{settings_path}</code></p>
""",
        """
<h2 id="platzhalter">Platzhalter im E-Mail-Text</h2>
<p>Diese Platzhalter k&ouml;nnen in Betreff und Text verwendet werden:</p>
<table>
  <tr><th>Platzhalter</th><th>Bedeutung</th></tr>
  <tr><td><code>{persnr}</code></td><td>Personalnummer des Mitarbeiters, z.&nbsp;B. <code>02548</code></td></tr>
  <tr><td><code>{monat}</code></td><td>Monatsname aus den Zeitraum-Einstellungen, z.&nbsp;B. <code>Mai</code></td></tr>
  <tr><td><code>{jahr}</code></td><td>Jahr aus den Zeitraum-Einstellungen, z.&nbsp;B. <code>2026</code></td></tr>
  <tr><td><code>{company_name}</code></td><td>Name des aktuell ausgew&auml;hlten Unternehmens</td></tr>
  <tr><td><code>{from_name}</code></td><td>Absendername aus den E-Mail-Einstellungen</td></tr>
</table>
<p>Wenn ein unbekannter Platzhalter verwendet wird, stoppt Vorschau oder Versand mit einer Fehlermeldung.</p>
""",
        """
<h2 id="fehler">H&auml;ufige Fehler und L&ouml;sungen</h2>
<table>
  <tr><th>Problem</th><th>Ursache / L&ouml;sung</th></tr>
  <tr>
    <td><b>Keine E-Mail</b></td>
    <td>Zur PersNr gibt es in Excel keine E-Mail-Adresse. Pr&uuml;fen Sie die Spalten <code>PersNr</code> und <code>Email</code>.</td>
  </tr>
  <tr>
    <td><b>Keine Dateien</b></td>
    <td>Die PersNr existiert in Excel, aber es wurde keine passende PDF gefunden. Pr&uuml;fen Sie Dateinamen oder den PDF-Inhalt im Modus Gesamt-PDF.</td>
  </tr>
  <tr>
    <td><b>Doppelte PersNr / E-Mail</b></td>
    <td>Die Excel-Datei enth&auml;lt Mehrfacheintr&auml;ge. Entfernen Sie Duplikate und starten Sie erneut.</td>
  </tr>
  <tr>
    <td><b>PDF nicht lesbar</b></td>
    <td>Die PDF ist defekt, leer oder nicht korrekt lesbar. &Ouml;ffnen Sie die Datei manuell und ersetzen Sie sie bei Bedarf.</td>
  </tr>
  <tr>
    <td><b>Unbekannter Platzhalter</b></td>
    <td>Im Betreff oder Text wurde etwas wie <code>{foo}</code> verwendet. Erlaubt sind nur die Platzhalter aus der Tabelle oben.</td>
  </tr>
  <tr>
    <td><b>Outlook sendet &uuml;ber das falsche Konto</b></td>
    <td>W&auml;hlen Sie in den E-Mail-Einstellungen <code>outlook</code>, laden Sie die Konten neu und w&auml;hlen Sie das richtige Konto explizit aus.</td>
  </tr>
  <tr>
    <td><b>SMTP-Verbindung fehlgeschlagen</b></td>
    <td>Pr&uuml;fen Sie Server, Port, Sicherheit, Benutzername, Passwort und ob Ihr Mailserver SMTP-Verbindungen zul&auml;sst.</td>
  </tr>
</table>

<h3>Praxis-Tipps</h3>
<ul>
  <li>Vor jedem echten Versand zuerst <b>Adressen pr&uuml;fen</b> und danach einen <b>Dry-Run</b> machen.</li>
  <li>Behalten Sie die erzeugten Berichte als Nachweis und zur Fehlersuche.</li>
  <li>Wenn Sie nur einzelne Mitarbeiter erneut versenden wollen, verwenden Sie die Auswahlspalte und <b>Nur ausgew&auml;hlte senden</b>.</li>
</ul>
""",
        """
</body>
</html>
""",
    ]
    return "".join(parts)
