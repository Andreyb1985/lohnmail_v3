/* Only allowlisted reports from the Python diagnostics service are transmitted. */
(function(){
  'use strict';
  var bridge, state = {reports:[]}, dialog, previousFocus, poll;
  var seenReport, notice;
  var $ = function(id){ return document.getElementById(id); };
  var errorTitles = {
    SMTP_AUTH: 'Anmeldung am Mailserver fehlgeschlagen',
    SMTP_RECIPIENT: 'Empfänger wurde abgelehnt',
    SMTP_SENDER: 'Absender wurde abgelehnt',
    SMTP_ERROR: 'E-Mail-Versand fehlgeschlagen',
    SQLITE_ERROR: 'Datenbankfehler',
    ARCHIVE_ERROR: 'Archiv konnte nicht geöffnet werden',
    HTTP_FORBIDDEN: 'Zugriff verweigert',
    HTTP_ERROR: 'Serveranfrage fehlgeschlagen',
    OUTLOOK_ERROR: 'Outlook-Verbindung fehlgeschlagen',
    NETWORK_DNS: 'Server nicht gefunden',
    NETWORK_TIMEOUT: 'Server antwortet nicht',
    NETWORK_TLS: 'Sichere Verbindung fehlgeschlagen',
    FILE_ACCESS: 'Dateizugriff verweigert',
    FILE_MISSING: 'Datei nicht gefunden',
    IO_ERROR: 'Datei- oder Verbindungsfehler',
    INVALID_INPUT: 'Eingaben konnten nicht verarbeitet werden',
    OPERATION_FAILED: 'Vorgang fehlgeschlagen'
  };
  function errorTitle(code){ return errorTitles[code] || errorTitles.OPERATION_FAILED; }
  var advice = {
    SMTP_AUTH: 'Die Anmeldung am Mailserver wurde abgelehnt. Benutzername, Passwort und Freigaben beim Anbieter prüfen.',
    SMTP_RECIPIENT: 'Der Mailserver hat den Empfänger abgelehnt. Adresse und Versandbericht prüfen.',
    SMTP_SENDER: 'Der Mailserver hat den Absender abgelehnt. Absenderadresse und Berechtigungen prüfen.',
    SMTP_ERROR: 'Der Mailserver hat die Übertragung abgebrochen. Einstellungen und Versandbericht prüfen.',
    SQLITE_ERROR: 'Die lokale Datenbank konnte nicht verarbeitet werden. Dateien nicht löschen; wenden Sie sich an den Support.',
    ARCHIVE_ERROR: 'Das Archiv konnte nicht gelesen werden. Download oder Kopie prüfen.',
    HTTP_FORBIDDEN: 'Der Server hat den Zugriff abgelehnt. Bitte den Support kontaktieren.',
    HTTP_ERROR: 'Die Serveranfrage ist fehlgeschlagen. Später erneut versuchen.',
    OUTLOOK_ERROR: 'Outlook Classic konnte die Aktion nicht abschließen. Anmeldung und Verbindung prüfen.',
    NETWORK_DNS: 'Der Servername konnte nicht aufgelöst werden. Serveradresse und Internetverbindung prüfen.',
    NETWORK_TIMEOUT: 'Der Server antwortet nicht rechtzeitig. Verbindung prüfen und später erneut versuchen.',
    NETWORK_TLS: 'Die sichere Verbindung konnte nicht hergestellt werden. Datum/Uhrzeit und Serverkonfiguration prüfen.',
    FILE_ACCESS: 'Der Zugriff auf eine Datei ist gesperrt. Schreibrechte und geöffnete Dateien prüfen.',
    FILE_MISSING: 'Eine benötigte Datei ist nicht mehr verfügbar. Datei oder Ordner erneut auswählen.',
    IO_ERROR: 'Eine Datei oder Verbindung konnte nicht verarbeitet werden. Speicher und Verbindung prüfen.',
    INVALID_INPUT: 'Die Eingaben konnten nicht verarbeitet werden. Dateiformat und Einstellungen prüfen.',
    OPERATION_FAILED: 'Der Vorgang konnte nicht abgeschlossen werden. Details prüfen und bei Bedarf den Support kontaktieren.',
    SUPPORT_REQUEST: 'Manuell erstellter Zustandsbericht für den Support.'
  };
  function call(method, args){
    return new Promise(function(resolve, reject){
      if (!bridge || typeof bridge[method] !== 'function') { reject(new Error('Unavailable')); return; }
      var finished = false;
      var timeout = method === 'exportDiagnosticReport' ? null : setTimeout(function(){ if (!finished) { finished = true; reject(new Error('Timeout')); } }, 15000);
      try {
        bridge[method].apply(bridge, (args || []).concat(function(value){
          if (finished) return; finished = true; clearTimeout(timeout);
          try { resolve(typeof value === 'string' ? JSON.parse(value) : value); } catch(error){ reject(error); }
        }));
      } catch(error){ finished = true; clearTimeout(timeout); reject(error); }
    });
  }
  function status(message){ if ($('diagnostics-status')) $('diagnostics-status').textContent = message; }
  function render(data){
    if (!data || !Array.isArray(data.reports)) return;
    state = data;
    var newest = data.reports[0] && data.reports[0].report;
    if (newest && seenReport !== undefined && newest.id !== seenReport && newest.code !== 'SUPPORT_REQUEST') {
      if (!notice) { notice = document.createElement('button'); notice.type = 'button'; notice.className = 'diagnostics-notice'; document.body.appendChild(notice); }
      notice.textContent = errorTitle(newest.code);
      notice.hidden = false;
      notice.onclick = function(){ showBriefError(newest.code, newest.stage); };
    }
    seenReport = newest ? newest.id : '';
    $('diagnostics-auto').checked = data.automatic === true;
    status((data.storage_ok === false ? 'Lokaler Diagnosejournal konnte nicht gespeichert werden. ' : '') +
      (data.sending ? 'Bericht wird übermittelt. ' : '') + 'Wartende Berichte: ' + data.pending + '. ' + (data.last_send || 'Noch keine Übertragung.'));
    var select = $('diagnostics-report'), selected = select.value;
    select.replaceChildren();
    data.reports.forEach(function(entry){
      var r = entry.report, option = document.createElement('option'); option.value = r.id;
      option.textContent = r.occurred_at + ' · ' + r.code + ' · ' + (r.company.name || 'Programmweit') + (entry.sent ? ' · gesendet' : '');
      select.appendChild(option);
    });
    if (Array.from(select.options).some(function(o){return o.value === selected;})) select.value = selected;
    $('diagnostics-details').disabled = !data.reports.length;
  }
  async function refresh(){ try { render(await call('getDiagnosticsState')); } catch (_) { status('Diagnose momentan nicht erreichbar.'); } }
  function selectedReport(){
    return (state.reports.find(function(e){ return e.report.id === $('diagnostics-report').value; }) || state.reports[0] || {}).report;
  }
  function element(tag, text){ var node = document.createElement(tag); node.textContent = text; return node; }
  function close(){ if (dialog && dialog.open) dialog.close(); }
  function prepareDialog(compact){
    if (notice) notice.hidden = true;
    if (!dialog) {
      dialog = document.createElement('dialog'); dialog.className = 'diagnostics-dialog';
      dialog.setAttribute('aria-labelledby', 'diagnostics-dialog-title'); document.body.appendChild(dialog);
      dialog.addEventListener('close', function(){ if (previousFocus && previousFocus.isConnected) previousFocus.focus(); });
    }
    if (!dialog.open) previousFocus = document.activeElement;
    dialog.className = 'diagnostics-dialog' + (compact ? ' diagnostics-error-dialog' : '');
    dialog.replaceChildren();
  }
  function showBriefError(code, stage){
    prepareDialog(true);
    var mailError = /^SMTP_/.test(code || '') || code === 'OUTLOOK_ERROR' ||
      (/^NETWORK_/.test(code || '') && ['mail_test', 'send', 'mass_message'].indexOf(stage) !== -1);
    var titleText = errorTitle(code);
    var explanation = advice[code] || advice.OPERATION_FAILED;
    if (mailError && /^NETWORK_/.test(code)) {
      var mode = document.querySelector('[data-settings-field="mail_mode"]');
      var server = mode && mode.value === 'smtp' ? 'SMTP-Server' : 'E-Mail-Server';
      if (code === 'NETWORK_DNS') {
        titleText = server + ' nicht gefunden';
        explanation = 'Die Adresse des E-Mail-Servers konnte nicht gefunden werden. Bitte prüfen Sie die SMTP-Serveradresse und Ihre Internetverbindung.';
      } else if (code === 'NETWORK_TIMEOUT') {
        titleText = server + ' antwortet nicht';
        explanation = 'Die Verbindung zum E-Mail-Server hat zu lange gedauert. Bitte prüfen Sie Serveradresse, Port und Internetverbindung.';
      } else {
        titleText = 'Sichere Verbindung zum E-Mail-Server fehlgeschlagen';
        explanation = 'Bitte prüfen Sie die Sicherheitseinstellung (TLS/SSL), den Port sowie Datum und Uhrzeit Ihres Computers.';
      }
    }
    var title = element('h2', titleText); title.id = 'diagnostics-dialog-title';
    dialog.appendChild(title);
    var description = element('p', explanation); description.id = 'diagnostics-error-description';
    dialog.appendChild(description);
    dialog.setAttribute('aria-describedby', description.id);
    var actions = element('div', ''); actions.className = 'diagnostics-actions';
    if (mailError && typeof window.lohnmailOpenMailSettings === 'function') {
      var settings = element('button', 'E-Mail-Einstellungen öffnen'); settings.type = 'button';
      settings.onclick = function(){ previousFocus = null; close(); window.lohnmailOpenMailSettings(); };
      actions.appendChild(settings);
    }
    var ok = element('button', 'OK'); ok.type = 'button'; ok.className = 'diagnostics-primary';
    ok.onclick = close; actions.appendChild(ok); dialog.appendChild(actions);
    if (!dialog.open) dialog.showModal();
    ok.focus({preventScroll:true});
    dialog.scrollTop = 0;
  }
  function show(report, manual, message){
    prepareDialog(false);
    dialog.removeAttribute('aria-describedby');
    var title = element('h2', manual ? 'Diagnosebericht senden?' : 'Fehlerdetails'); title.id = 'diagnostics-dialog-title'; title.tabIndex = -1; dialog.appendChild(title);
    if (message) dialog.appendChild(element('p', message));
    if (report) {
      dialog.appendChild(element('p', advice[report.code] || advice.OPERATION_FAILED));
      dialog.appendChild(element('p', 'Code: ' + report.code + ' · ' + report.occurred_at + '\nBericht: ' + report.id));
      dialog.appendChild(element('p', 'Unternehmen: ' + (report.company.name || 'Programmweit') + ' · ID: ' + (report.company.id || '—')));
    }
    if (manual) dialog.appendChild(element('p', 'Die unten gezeigten technischen Daten werden an den LohnMail-Lizenzserver übertragen und dort Ihrer Lizenz zugeordnet (Aufbewahrung 30 Tage). Lizenzschlüssel und Computer-ID werden zur Authentifizierung mitübertragen, aber nicht im Bericht gespeichert. Ohne Verbindung wird dieser Bericht bis zu 14 Tage zur Übertragung vorgemerkt. Die automatische Übertragung wird dadurch nicht eingeschaltet.'));
    var details = element('details', ''); details.open = true;
    details.appendChild(element('summary', 'Vollständiger bereinigter Bericht'));
    var copyText = report ? JSON.stringify(report, null, 2) : (message || 'Kein technischer Bericht vorhanden.');
    var pre = element('pre', copyText); pre.tabIndex = 0; details.appendChild(pre); dialog.appendChild(details);
    var feedback = element('p', ''); feedback.setAttribute('role', 'status'); dialog.appendChild(feedback);
    var actions = element('div', ''); actions.className = 'diagnostics-actions';
    var copy = element('button', 'Details kopieren'); copy.type = 'button';
    copy.onclick = async function(){
      try { await navigator.clipboard.writeText(copyText); feedback.textContent = 'Kopiert.'; }
      catch (_) { var range = document.createRange(); range.selectNodeContents(pre); var selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); feedback.textContent = 'Text markiert. Bitte mit Strg+C / Cmd+C kopieren.'; }
    }; actions.appendChild(copy);
    var cancel = element('button', manual ? 'Abbrechen' : 'Schließen'); cancel.type = 'button'; cancel.onclick = close; actions.appendChild(cancel);
    if (manual && report) {
      var send = element('button', 'Diesen Bericht senden'); send.type = 'button'; send.className = 'diagnostics-primary';
      send.onclick = async function(){
        send.disabled = true;
        try { var result = await call('sendDiagnosticReport', [report.id]); feedback.textContent = result.message; await refresh(); }
        catch (_) { feedback.textContent = 'Übertragung konnte nicht freigegeben werden. Bitte erneut versuchen.'; send.disabled = false; }
      }; actions.appendChild(send);
    }
    dialog.appendChild(actions);
    if (!dialog.open) dialog.showModal();
    title.focus({preventScroll:true});
    dialog.scrollTop = 0;
  }
  async function showError(payload){
    try {
      var data = typeof payload === 'string' ? JSON.parse(payload) : payload;
      await refresh();
      var recent = state.reports[0] && state.reports[0].report;
      if (recent && Math.abs(Date.now() - Date.parse(recent.occurred_at)) > 60000) recent = null;
      var code = data && (data.code || (data.status && data.status.code));
      var stage = data && (data.stage || (data.status && data.status.stage));
      if (!code || (recent && recent.code === code)) {
        stage = stage || (recent && recent.stage);
      }
      showBriefError(code || (recent && recent.code), stage);
    } catch (_) { showBriefError('OPERATION_FAILED'); }
  }
  function attach(api){
    bridge = api;
    if (!$('diagnostics-auto')) return;
    $('diagnostics-auto').onchange = async function(){
      var enabled = this.checked; this.disabled = true;
      try { render(await call('setDiagnosticsConsent', [enabled])); }
      catch (_) { status('Einstellung konnte nicht gespeichert werden.'); this.checked = !enabled; }
      finally { this.disabled = false; }
    };
    $('diagnostics-send').onclick = async function(){
      try {
        await refresh();
        if (!state.reports.length) render(await call('createSupportReport'));
        show(selectedReport(), true);
      } catch (_) { status('Bericht konnte nicht vorbereitet werden.'); }
    };
    $('diagnostics-export').onclick = async function(){
      try {
        if (!state.reports.length) render(await call('createSupportReport'));
        var result = await call('exportDiagnosticReport'); status(result.message);
      } catch (_) { status('Export konnte nicht abgeschlossen werden.'); }
    };
    $('diagnostics-details').onclick = function(){ show(selectedReport(), false); };
    ['processingError','shippingError','massMessageError'].forEach(function(name){ if (bridge[name]) bridge[name].connect(showError); });
    if (bridge.diagnosticsStateChanged) bridge.diagnosticsStateChanged.connect(function(payload){ try { render(JSON.parse(payload)); } catch (_) {} });
    refresh();
    clearInterval(poll); poll = setInterval(refresh, 5000);
  }
  window.LohnMailDiagnostics = {attach:attach, showError:showError};
})();
