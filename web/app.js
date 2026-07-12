(function(){
  var latestDashboardState = null;
  var latestProcessingState = null;
  var latestValidationState = null;
  var currentValidationFilter = 'all';
  var currentValidationPage = 1;
  var validationPageSize = 20;
  var validationSearchQuery = '';
  var validationIssuesOnly = false;
  var validationGroupMode = false;
  var latestShippingState = null;
  var shippingSearchQuery = '';
  var shippingViewFilter = 'queue';
  var shippingStatusFilter = 'all';
  var currentShippingPage = 1;
  var shippingPageSize = 20;
  var selectedShippingPersnr = {};
  var shippingPreviewZoom = 100;
  var reportsSearchQuery = '';
  var reportsTypeFilter = 'all';
  var reportsStatusFilter = 'all';
  var reportsReadyOnly = false;
  var reportsPage = 1;
  var reportsPageSize = 10;
  var selectedReportKind = 'audit';
  var latestCompanyState = null;
  var companySwitchSearchQuery = '';
  var latestLicenseState = null;
  var latestSettingsState = null;
  var warningsAutoOpened = false;
  var latestMassMessageState = null;
  var latestShippingSendPreview = null;
  var processingActivityLog = [];
  var lastProcessingLogKey = '';
  function initBridge(){
    if (typeof QWebChannel === 'undefined') {
      setInfoBanner('Bridge nicht verfügbar. Bitte WebEngine neu starten.', false);
      return;
    }
    new QWebChannel(qt.webChannelTransport, function(channel){
      window.lohnmailBridge = channel.objects.lohnmailBridge;
      bindBridgeSignals();
      loadDashboardState();
      loadCompanyState();
      loadSettingsState();
      loadProcessingState();
      loadValidationState();
      loadShippingState();
      loadMassMessageState();
    });
  }
  function bindBridgeSignals(){
    var bridge = window.lohnmailBridge;
    if (!bridge || bridge.__lohnmailSignalsBound) return;
    bridge.__lohnmailSignalsBound = true;
    if (bridge.processingStateChanged) {
      bridge.processingStateChanged.connect(function(payload){ consumeProcessingPayload(payload, 'state'); });
    }
    if (bridge.processingProgress) {
      bridge.processingProgress.connect(function(payload){ consumeProcessingPayload(payload, 'progress'); });
    }
    if (bridge.processingFinished) {
      bridge.processingFinished.connect(function(payload){
        consumeProcessingPayload(payload, 'finished');
        loadDashboardState();
        loadValidationState();
      });
    }
    if (bridge.processingError) {
      bridge.processingError.connect(function(payload){ consumeProcessingPayload(payload, 'error'); });
    }
    if (bridge.shippingStateChanged) {
      bridge.shippingStateChanged.connect(function(payload){ consumeShippingPayload(payload); });
    }
    if (bridge.shippingProgress) {
      bridge.shippingProgress.connect(function(payload){ consumeShippingPayload(payload); });
    }
    if (bridge.shippingFinished) {
      bridge.shippingFinished.connect(function(payload){
        consumeShippingPayload(payload);
        loadDashboardState();
      });
    }
    if (bridge.shippingError) {
      bridge.shippingError.connect(function(payload){ consumeShippingPayload(payload); });
    }
    if (bridge.massMessageStateChanged) {
      bridge.massMessageStateChanged.connect(function(payload){ consumeMassMessagePayload(payload); });
    }
    if (bridge.massMessageProgress) {
      bridge.massMessageProgress.connect(function(payload){ consumeMassMessagePayload(payload); });
    }
    if (bridge.massMessageFinished) {
      bridge.massMessageFinished.connect(function(payload){ consumeMassMessagePayload(payload); });
    }
    if (bridge.massMessageError) {
      bridge.massMessageError.connect(function(payload){ consumeMassMessagePayload(payload); });
    }
  }
  function setText(selector, value){
    var node = document.querySelector(selector);
    if (node && value !== undefined && value !== null) node.textContent = String(value);
  }
  function setLabeledIconText(selector, value){
    var node = document.querySelector(selector);
    if (!node || value === undefined || value === null) return;
    var icon = node.querySelector('[data-icon], .status-dot');
    node.textContent = ' ' + String(value);
    if (icon) node.prepend(icon);
  }
  function setStatus(selector, value){
    var node = document.querySelector(selector);
    if (!node || value === undefined || value === null) return;
    node.textContent = String(value);
    node.classList.toggle('warning-text', value === 'Offen');
  }
  function updateReport(kind, report){
    if (!report) return;
    document.querySelectorAll('[data-report="' + kind + '"]').forEach(function(item){
      var small = item.querySelector('small');
      var button = item.querySelector('button');
      if (small) small.textContent = report.label || 'Nicht erstellt';
      item.classList.toggle('report-ready', !!report.exists);
      if (button) {
        button.disabled = !report.exists;
        button.title = report.exists ? (report.path || report.name || '') : 'Noch nicht erstellt';
      }
    });
  }
  function setReportAction(button, report, hideWhenMissing){
    if (!button) return;
    var exists = !!(report && report.exists);
    button.disabled = !exists;
    button.title = exists ? (report.path || report.name || '') : 'Noch nicht erstellt';
    button.classList.toggle('hidden', !!hideWhenMissing && !exists);
  }
  function updateValidationReportActions(reports){
    reports = reports || {};
    document.querySelectorAll('[data-report-open="audit"]').forEach(function(button){
      setReportAction(button, reports.audit, false);
    });
    document.querySelectorAll('[data-report-open="missing"]').forEach(function(button){
      setReportAction(button, reports.missing, true);
    });
  }
  function setReportsMessage(message){
    setText('[data-reports="table-footer"]', message);
  }
  function openReport(kind){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.openReport) {
      setText('[data-validation="table-footer"]', 'Bericht öffnen ist im Bridge nicht verfügbar.');
      setReportsMessage('Bericht öffnen ist im Bridge nicht verfügbar.');
      return;
    }
    bridge.openReport(kind, function(payload){
      try {
        var result = JSON.parse(payload || '{}');
        if (!result.ok) {
          setText('[data-validation="table-footer"]', result.message || 'Bericht konnte nicht geöffnet werden.');
          setReportsMessage(result.message || 'Bericht konnte nicht geöffnet werden.');
        } else {
          setReportsMessage('Bericht geöffnet: ' + (result.path || kind));
        }
      } catch (error) {
        setText('[data-validation="table-footer"]', 'Bericht konnte nicht geöffnet werden.');
        setReportsMessage('Bericht konnte nicht geöffnet werden.');
      }
    });
  }
  function reportMap(){
    var result = {};
    [latestDashboardState, latestValidationState, latestShippingState].forEach(function(state){
      var reports = (state && state.reports) || {};
      Object.keys(reports).forEach(function(key){
        if (reports[key] && typeof reports[key] === 'object') result[key] = reports[key];
      });
    });
    return result;
  }
  function reportMetricValues(){
    var validationSummary = (latestValidationState && latestValidationState.summary) || {};
    var validationFilters = (latestValidationState && latestValidationState.filters) || {};
    var shippingMetrics = (latestShippingState && latestShippingState.metrics) || {};
    var processingStatus = (latestProcessingState && latestProcessingState.status) || {};
    var reports = reportMap();
    var exported = ['audit', 'missing', 'send'].filter(function(kind){ return reports[kind] && reports[kind].exists; }).length;
    var processed = Number(validationSummary.checked || processingStatus.processed || processingStatus.employees_total || 0);
    var sent = Number(shippingMetrics.sent || 0);
    var delivered = Math.max(0, sent - Number(shippingMetrics.errors || 0));
    var failed = Number(shippingMetrics.errors || processingStatus.errors || validationSummary.critical || 0);
    var warnings = Number(validationSummary.warnings || validationFilters.warnings || processingStatus.warnings || 0);
    var employees = Number(validationSummary.total || processingStatus.employees_total || shippingMetrics.total || 0);
    return {
      processed: processed,
      sent: sent,
      delivered: delivered,
      failed: failed,
      warnings: warnings,
      employees: employees,
      exported: exported
    };
  }
  function reportRows(){
    var reports = reportMap();
    var metrics = reportMetricValues();
    var defs = [
      { kind: 'audit', type: 'xls', icon: 'table', title: 'audit_check.xlsx', subtitle: 'Prüfbericht / Excel', validation: metrics.failed + ' Fehler, ' + metrics.warnings + ' Warnungen', shipping: metrics.sent + ' gesendet' },
      { kind: 'missing', type: 'pdf', icon: 'doc', title: 'ohne_email_gesamt.pdf', subtitle: 'Mitarbeiter ohne E-Mail / PDF', validation: metrics.warnings + ' ohne E-Mail', shipping: 'Nicht versendet' },
      { kind: 'send', type: 'xls', icon: 'report', title: 'send_report.xlsx', subtitle: 'Versandbericht / Excel', validation: metrics.employees + ' geprüft', shipping: metrics.sent + ' gesendet' }
    ];
    return defs.map(function(def){
      var report = reports[def.kind] || {};
      var exists = !!report.exists;
      return {
        kind: def.kind,
        type: def.type,
        icon: def.icon,
        title: def.title,
        subtitle: def.subtitle,
        status: exists ? 'Abgeschlossen' : 'Nicht erstellt',
        exists: exists,
        created: report.label || '-',
        path: report.path || '',
        processing: metrics.processed + ' / ' + metrics.employees,
        validation: def.validation,
        shipping: def.shipping,
        owner: 'LohnMail',
        metrics: metrics
      };
    });
  }
  function filteredReportRows(){
    var rows = reportRows();
    if (reportsTypeFilter !== 'all') {
      rows = rows.filter(function(row){ return row.type === reportsTypeFilter; });
    }
    if (reportsStatusFilter === 'ready') rows = rows.filter(function(row){ return row.exists; });
    if (reportsStatusFilter === 'missing') rows = rows.filter(function(row){ return !row.exists; });
    if (reportsReadyOnly) rows = rows.filter(function(row){ return row.exists; });
    if (reportsSearchQuery) {
      var query = reportsSearchQuery.toLowerCase();
      rows = rows.filter(function(row){
        return [row.title, row.subtitle, row.status, row.created, row.path, row.processing, row.validation, row.shipping]
          .join(' ')
          .toLowerCase()
          .indexOf(query) !== -1;
      });
    }
    return rows;
  }
  function setReportsDetailText(key, value){
    setText('[data-reports-detail="' + key + '"]', value);
  }
  function applyReportDetail(row){
    row = row || reportRows()[0] || null;
    selectedReportKind = row ? row.kind : 'audit';
    var statusNode = document.querySelector('[data-reports-detail="status"]');
    var iconNode = document.querySelector('[data-reports-detail="icon"]');
    if (iconNode && row) iconNode.setAttribute('data-icon', row.icon || 'doc');
    if (statusNode) {
      statusNode.textContent = row ? row.status : 'Nicht erstellt';
      statusNode.className = 'state ' + (row && row.exists ? 'ready' : 'warning');
    }
    setReportsDetailText('title', row ? row.title : 'Kein Bericht ausgewählt');
    setReportsDetailText('subtitle', row ? row.subtitle : 'Bitte einen Eintrag wählen.');
    setReportsDetailText('id', row ? row.kind.toUpperCase() : '-');
    setReportsDetailText('period', 'Aktuelle Sitzung');
    setReportsDetailText('created', row ? row.created : '-');
    setReportsDetailText('owner', row ? row.owner : 'LohnMail');
    setReportsDetailText('path', row && row.path ? row.path : '-');
    var metrics = (row && row.metrics) || reportMetricValues();
    setReportsDetailText('employees', metrics.employees || 0);
    setReportsDetailText('errors', metrics.failed || 0);
    setReportsDetailText('warnings', metrics.warnings || 0);
    setReportsDetailText('sent', metrics.sent || 0);
    setReportsDetailText('delivered', metrics.delivered || 0);
    setReportsDetailText('failed', metrics.failed || 0);
    document.querySelectorAll('[data-reports-action="open-selected"]').forEach(function(button){
      button.disabled = !(row && row.exists);
      button.title = row && row.exists ? row.path : 'Bericht wurde noch nicht erstellt.';
    });
    var reports = reportMap();
    document.querySelectorAll('[data-reports-action="open-pdf"]').forEach(function(button){
      button.disabled = !(reports.missing && reports.missing.exists);
      button.title = reports.missing && reports.missing.exists ? reports.missing.path : 'PDF ohne E-Mail wurde noch nicht erstellt.';
    });
    document.querySelectorAll('[data-reports-action="open-excel"]').forEach(function(button){
      var excelReport = selectedReportKind === 'send' ? reports.send : reports.audit;
      button.disabled = !(excelReport && excelReport.exists);
      button.title = excelReport && excelReport.exists ? excelReport.path : 'Excel-Bericht wurde noch nicht erstellt.';
    });
  }
  function renderReportsTable(){
    var tbody = document.querySelector('[data-reports="table-body"]');
    if (!tbody) return;
    var rows = filteredReportRows();
    var totalPages = Math.max(1, Math.ceil(rows.length / reportsPageSize));
    reportsPage = Math.max(1, Math.min(reportsPage, totalPages));
    var start = rows.length ? (reportsPage - 1) * reportsPageSize : 0;
    var end = Math.min(start + reportsPageSize, rows.length);
    var pageRows = rows.slice(start, end);
    if (!pageRows.length) {
      tbody.innerHTML = '<tr><td colspan="9">Keine Berichte für diesen Filter.</td></tr>';
      setReportsMessage('Zeige 0 Einträge');
      applyReportDetail(null);
    } else {
      tbody.innerHTML = pageRows.map(function(row, index){
        return '<tr data-reports-row="' + index + '" class="' + (row.kind === selectedReportKind ? 'selected' : '') + '">' +
          '<td>' + escapeHtml(row.created) + '</td>' +
          '<td><span class="file-dot ' + escapeHtml(row.type) + '"><span data-icon="' + escapeHtml(row.icon) + '"></span></span></td>' +
          '<td><b>' + escapeHtml(row.title) + '</b><small>' + escapeHtml(row.subtitle) + '</small></td>' +
          '<td><span class="state ' + (row.exists ? 'ready' : 'warning') + '">' + escapeHtml(row.status) + '</span></td>' +
          '<td><b>' + escapeHtml(row.processing) + '</b><small>Aktuell</small></td>' +
          '<td><b>' + escapeHtml(row.validation) + '</b><small>Prüfung</small></td>' +
          '<td><b>' + escapeHtml(row.shipping) + '</b><small>Versand</small></td>' +
          '<td>' + escapeHtml(row.owner) + '</td>' +
          '<td><button data-reports-open-kind="' + escapeHtml(row.kind) + '" ' + (row.exists ? '' : 'disabled') + '><span data-icon="arrow-up-right"></span></button><button data-reports-action="row-details">...</button></td>' +
        '</tr>';
      }).join('');
      tbody.querySelectorAll('[data-reports-row]').forEach(function(tr){
        tr.addEventListener('click', function(event){
          var row = pageRows[Number(tr.getAttribute('data-reports-row'))];
          if (!row) return;
          tbody.querySelectorAll('tr').forEach(function(node){ node.classList.remove('selected'); });
          tr.classList.add('selected');
          applyReportDetail(row);
          var openButton = event.target.closest && event.target.closest('[data-reports-open-kind]');
          if (openButton && !openButton.disabled) openReport(row.kind);
        });
      });
      var selected = pageRows.filter(function(row){ return row.kind === selectedReportKind; })[0] || pageRows[0];
      applyReportDetail(selected);
      setReportsMessage('Zeige ' + (start + 1) + ' bis ' + end + ' von ' + rows.length + ' Einträgen');
    }
    setText('[data-reports="page-current"]', String(reportsPage));
    var prev = document.querySelector('[data-reports-action="page-prev"]');
    var next = document.querySelector('[data-reports-action="page-next"]');
    if (prev) prev.disabled = reportsPage <= 1;
    if (next) next.disabled = reportsPage >= totalPages;
  }
  function updateReportsScreen(){
    var metrics = reportMetricValues();
    setText('[data-reports-metric="processed"]', metrics.processed);
    setText('[data-reports-metric="sent"]', metrics.sent);
    setText('[data-reports-metric="delivered"]', metrics.delivered);
    setText('[data-reports-metric="failed"]', metrics.failed);
    setText('[data-reports-metric="exported"]', metrics.exported);
    setText('[data-reports-metric="processed-label"]', metrics.employees ? 'Von ' + metrics.employees + ' Mitarbeitern' : 'Aktuelle Sitzung');
    setText('[data-reports-metric="sent-label"]', metrics.sent ? 'Versanddaten vorhanden' : 'Noch nicht versendet');
    setText('[data-reports-metric="delivered-label"]', metrics.sent ? 'Ohne bekannte Fehler' : 'Noch nicht versendet');
    setText('[data-reports-metric="failed-label"]', metrics.failed ? 'Bitte prüfen' : 'Keine Fehler');
    setText('[data-reports-metric="exported-label"]', metrics.exported + ' von 3 Berichten');
    setText('[data-reports="type-label"]', reportsTypeFilter === 'all' ? 'Alle Typen' : reportsTypeFilter.toUpperCase());
    setText('[data-reports="status-label"]', reportsStatusFilter === 'all' ? 'Alle Status' : (reportsStatusFilter === 'ready' ? 'Erstellt' : 'Nicht erstellt'));
    setText('[data-reports="filter-label"]', reportsReadyOnly ? 'Filter: Erstellt' : 'Filter');
    document.querySelectorAll('[data-reports-action="type"]').forEach(function(button){
      button.classList.toggle('active', reportsTypeFilter !== 'all');
    });
    document.querySelectorAll('[data-reports-action="status"]').forEach(function(button){
      button.classList.toggle('active', reportsStatusFilter !== 'all');
    });
    document.querySelectorAll('[data-reports-action="toggle-ready"]').forEach(function(button){
      button.classList.toggle('active', reportsReadyOnly);
    });
    var reports = reportMap();
    updateReport('audit', reports.audit);
    updateReport('missing', reports.missing);
    updateReport('send', reports.send);
    renderReportsTable();
  }
  function exportReportsCsv(){
    var rows = filteredReportRows();
    var headers = ['Bericht', 'Typ', 'Status', 'Erstellt', 'Verarbeitung', 'Pruefung', 'Versand', 'Pfad'];
    var csvRows = [headers].concat(rows.map(function(row){
      return [row.title, row.type.toUpperCase(), row.status, row.created, row.processing, row.validation, row.shipping, row.path || ''];
    }));
    var csv = csvRows.map(function(row){
      return row.map(function(cell){
        return '"' + String(cell === undefined || cell === null ? '' : cell).replace(/"/g, '""') + '"';
      }).join(';');
    }).join('\n');
    var filename = 'lohnmail_berichte_' + new Date().toISOString().slice(0, 10) + '.csv';
    if (window.lohnmailBridge && window.lohnmailBridge.exportValidationCsv) {
      window.lohnmailBridge.exportValidationCsv(csv, filename, function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          setReportsMessage(result.ok ? 'Export gespeichert: ' + result.path : 'Export fehlgeschlagen');
        } catch (error) {
          setReportsMessage('Export fehlgeschlagen');
        }
      });
      return;
    }
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    setReportsMessage('Export wurde heruntergeladen.');
  }
  function runReportsAction(action){
    if (action === 'export-csv') {
      exportReportsCsv();
      return;
    }
    if (action === 'type') {
      reportsTypeFilter = reportsTypeFilter === 'all' ? 'pdf' : (reportsTypeFilter === 'pdf' ? 'xls' : 'all');
      reportsPage = 1;
      updateReportsScreen();
      return;
    }
    if (action === 'status') {
      reportsStatusFilter = reportsStatusFilter === 'all' ? 'ready' : (reportsStatusFilter === 'ready' ? 'missing' : 'all');
      reportsPage = 1;
      updateReportsScreen();
      return;
    }
    if (action === 'toggle-ready') {
      reportsReadyOnly = !reportsReadyOnly;
      reportsPage = 1;
      updateReportsScreen();
      return;
    }
    if (action === 'period' || action === 'chart-mode') {
      setReportsMessage('Berichte zeigen aktuell die laufende Sitzung und vorhandene Ausgabedateien.');
      return;
    }
    if (action === 'page-prev' || action === 'page-next') {
      reportsPage += action === 'page-next' ? 1 : -1;
      renderReportsTable();
      return;
    }
    if (action === 'page-size') {
      setReportsMessage('Seitengröße ist aktuell auf 10 Einträge gesetzt.');
      return;
    }
    if (action === 'detail-close') {
      setReportsMessage('Detailansicht ist read-only und bleibt für den ausgewählten Bericht sichtbar.');
      return;
    }
    if (action === 'open-pdf') {
      openReport('missing');
      return;
    }
    if (action === 'open-excel') {
      openReport(selectedReportKind === 'send' ? 'send' : 'audit');
      return;
    }
    if (action === 'open-selected') {
      openReport(selectedReportKind);
    }
  }
  function companyInitials(name){
    var parts = String(name || '').replace(/-/g, ' ').split(/\s+/).filter(Boolean);
    return (parts[0] ? parts[0].slice(0, 1) : 'U').toUpperCase() + (parts[1] ? parts[1].slice(0, 1).toUpperCase() : '');
  }
  function activeCompanyFromState(state){
    state = state || latestCompanyState || {};
    var companies = state.companies || [];
    var selectedId = String(state.selected_company_id || '').trim();
    for (var i = 0; i < companies.length; i += 1) {
      if (String(companies[i].id || '').trim() === selectedId) return companies[i];
    }
    return companies[0] || null;
  }
  function closeCompanySwitchMenu(){
    var menu = document.querySelector('[data-company-switch-menu]');
    if (menu) menu.hidden = true;
  }
  function toggleCompanySwitchMenu(){
    var menu = document.querySelector('[data-company-switch-menu]');
    if (!menu) return;
    menu.hidden = !menu.hidden;
    var input = document.querySelector('[data-company-switch-search]');
    if (!menu.hidden && input) setTimeout(function(){ input.focus(); }, 0);
  }
  function renderCompanySwitcher(state){
    state = state || latestCompanyState || {};
    var active = activeCompanyFromState(state);
    var selectedExcel = state.selected_excel || (active && active.excel) || {};
    var name = state.selected_company_name || (active && active.name) || 'Mandant auswählen';
    var id = state.selected_company_id || (active && active.id) || '-';
    var excelReady = !!selectedExcel.valid;
    var button = document.querySelector('[data-company-switch-toggle]');
    setText('[data-company-switch="initials"]', companyInitials(name));
    setText('[data-company-switch="name"]', name);
    setText('[data-company-switch="status"]', id + ' · Excel ' + (excelReady ? 'bereit' : 'fehlt'));
    if (button) button.classList.toggle('warning', !excelReady);

    var list = document.querySelector('[data-company-switch-list]');
    if (!list) return;
    var query = companySwitchSearchQuery.trim().toLowerCase();
    var companies = (state.companies || []).filter(function(company){
      if (!query) return true;
      return [company.name, company.id, company.excel && company.excel.path].join(' ').toLowerCase().indexOf(query) !== -1;
    });
    if (!companies.length) {
      list.innerHTML = '<div class="company-note">Kein Mandant gefunden.</div>';
      return;
    }
    list.innerHTML = companies.map(function(company){
      var ready = !!(company.excel && company.excel.valid);
      return '<button class="company-switch-row ' + (company.selected ? 'active ' : '') + (ready ? 'ready' : '') + '" data-company-switch-id="' + escapeHtml(company.id) + '">' +
        '<span>' + escapeHtml(companyInitials(company.name)) + '</span>' +
        '<span><strong>' + escapeHtml(company.name || company.id || '-') + '</strong><small>' + escapeHtml(company.id || '-') + ' · ' + escapeHtml((company.excel && company.excel.path) || 'Keine Excel-Datei') + '</small></span>' +
        '<b>' + escapeHtml(ready ? 'Bereit' : 'Excel fehlt') + '</b>' +
      '</button>';
    }).join('');
    list.querySelectorAll('[data-company-switch-id]').forEach(function(row){
      row.addEventListener('click', function(){
        closeCompanySwitchMenu();
        runCompanyAction('select-company', row.getAttribute('data-company-switch-id'));
      });
    });
  }
  function setCompanyMessage(message){
    setText('[data-company="message"]', message);
  }
  function setCompanyCreateMessage(message, error){
    var node = document.querySelector('[data-company-create="message"]');
    if (!node) return;
    node.textContent = message || '';
    node.classList.toggle('error', !!error);
  }
  function normalizeCompanyId(value){
    return String(value || '').trim().toLowerCase()
      .replace(/[^a-z0-9_\-\s]/g, '')
      .replace(/[\s_]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
  }
  function openCompanyCreateModal(){
    var modal = document.querySelector('[data-company-modal]');
    if (!modal) return;
    modal.hidden = false;
    setCompanyCreateMessage('', false);
    var nameInput = document.querySelector('[data-company-create="name"]');
    var idInput = document.querySelector('[data-company-create="id"]');
    if (nameInput) nameInput.value = '';
    if (idInput) {
      idInput.value = '';
      delete idInput.dataset.touched;
    }
    setTimeout(function(){ if (nameInput) nameInput.focus(); }, 0);
  }
  function closeCompanyCreateModal(){
    var modal = document.querySelector('[data-company-modal]');
    if (modal) modal.hidden = true;
  }
  function closeWarningMenu(){
    var menu = document.querySelector('[data-warning-menu]');
    if (menu) menu.hidden = true;
  }
  function toggleWarningMenu(){
    var menu = document.querySelector('[data-warning-menu]');
    if (menu) menu.hidden = !menu.hidden;
  }
  function currentLicenseWarningSource(){
    var sources = [
      latestLicenseState,
      latestDashboardState && latestDashboardState.license,
      latestCompanyState && latestCompanyState.license
    ].filter(Boolean);
    var usable = sources.filter(function(license){ return licenseIsUsable(license); })[0];
    return usable || sources[0] || {};
  }
  function licenseIsUsable(license){
    license = license || {};
    var status = String(license.status || '').toLowerCase();
    var label = String(license.label || '').toLowerCase();
    return !!license.active || status === 'active' || status === 'trialing' || label.indexOf('active') !== -1 || label.indexOf('aktiv') !== -1 || label.indexOf('trial') !== -1;
  }
  function licenseWarningText(license){
    license = license || {};
    var status = String(license.status || '').toLowerCase();
    if (status === 'past_due' || status === 'unpaid') {
      return { title: 'Lizenzzahlung offen', text: 'Die letzte Lizenzzahlung muss geprüft werden.' };
    }
    if (status === 'expired' || status === 'canceled' || status === 'revoked') {
      return { title: 'Lizenz nicht aktiv', text: 'Die Lizenz ist abgelaufen, gekündigt oder wurde deaktiviert.' };
    }
    if (status === 'no_connection') {
      return { title: 'Lizenzserver nicht erreichbar', text: 'Die Lizenz konnte zuletzt nicht online geprüft werden.' };
    }
    return { title: 'Lizenz nicht registriert', text: 'Die Anwendung läuft ohne aktive Lizenzregistrierung.' };
  }
  function collectHeaderWarnings(){
    var warnings = [];
    var notificationSettings = (latestSettingsState && latestSettingsState.notifications) || {};
    var workflowWarnings = notificationSettings.workflow_warnings !== false;
    var validationWarnings = notificationSettings.validation_warnings !== false;
    var processingErrors = notificationSettings.processing_errors !== false;
    var company = latestCompanyState || {};
    var activeCompany = activeCompanyFromState(company);
    var selectedExcel = company.selected_excel || (activeCompany && activeCompany.excel) || {};
    var smtp = company.smtp || {};
    var license = currentLicenseWarningSource();
    var processing = latestProcessingState || {};
    var processingInputs = processing.inputs || {};
    var processingStatus = processing.status || {};
    var validation = latestValidationState || {};
    var summary = validation.summary || {};

    if (!activeCompany && company.companies) {
      warnings.push({ level: 'error', title: 'Kein Mandant ausgewählt', text: 'Bitte zuerst ein Unternehmen auswählen oder neu erstellen.', action: 'open-company' });
    }
    if (activeCompany && !selectedExcel.valid) {
      warnings.push({ level: 'error', title: 'Mitarbeiter Excel fehlt', text: 'Für den aktiven Mandanten ist keine gültige Excel-Datei zugeordnet.', action: 'choose-excel' });
    }
    if (workflowWarnings && smtp && smtp.configured === false) {
      warnings.push({ level: 'warning', title: 'SMTP nicht konfiguriert', text: 'E-Mail-Versand ist erst nach SMTP- oder Outlook-Konfiguration möglich.', action: 'open-settings' });
    }
    if (workflowWarnings && license && !licenseIsUsable(license)) {
      var licenseWarning = licenseWarningText(license);
      warnings.push({ level: 'warning', title: licenseWarning.title, text: licenseWarning.text, action: 'open-license' });
    }
    if (workflowWarnings && processingInputs.pdf && !processingInputs.pdf.valid) {
      warnings.push({ level: 'info', title: 'PDF-Eingang fehlt', text: 'Für den nächsten Lauf muss ein PDF-Ordner oder Gesamt-PDF gewählt werden.', action: 'open-processing' });
    }
    if (processingErrors && processingStatus.failed) {
      warnings.push({ level: 'error', title: 'Prüfung fehlgeschlagen', text: processingStatus.message || 'Der letzte Prüflauf ist fehlgeschlagen.', action: 'open-processing' });
    }
    if (Number(summary.critical || 0) > 0) {
      warnings.push({ level: 'error', title: 'Kritische Prüffehler', text: summary.critical + ' Einträge müssen vor dem Versand geprüft werden.', action: 'open-validation' });
    } else if (validationWarnings && Number(summary.warnings || 0) > 0) {
      warnings.push({ level: 'warning', title: 'Prüfwarnungen vorhanden', text: summary.warnings + ' Warnungen sollten vor dem Versand kontrolliert werden.', action: 'open-validation' });
    }
    return warnings;
  }
  function runWarningAction(action){
    closeWarningMenu();
    if (action === 'choose-excel') {
      setPage('Unternehmen');
      runCompanyAction('choose-excel');
      return;
    }
    if (action === 'open-company') setPage('Unternehmen');
    if (action === 'open-settings') setPage('Einstellungen');
    if (action === 'open-license') setPage('Lizenzen');
    if (action === 'open-processing') setPage('Verarbeitung');
    if (action === 'open-validation') setPage('Prüfung');
  }
  function updateWarningCenter(){
    var warnings = collectHeaderWarnings();
    var notificationSettings = (latestSettingsState && latestSettingsState.notifications) || {};
    var showBadge = notificationSettings.show_badge !== false;
    var autoOpen = notificationSettings.auto_open_on_start === true;
    var badge = document.querySelector('[data-warning-count]');
    var bell = document.querySelector('[data-warning-toggle]');
    var list = document.querySelector('[data-warning-list]');
    var summary = document.querySelector('[data-warning-summary]');
    var hasErrors = warnings.some(function(item){ return item.level === 'error'; });
    if (warnings.length) {
      setLabeledIconText('[data-dashboard="footer-system"]', hasErrors ? 'System prüfen' : 'Hinweise offen');
    } else {
      setLabeledIconText('[data-dashboard="footer-system"]', 'System bereit');
    }
    if (badge) {
      badge.hidden = !showBadge || !warnings.length;
      badge.textContent = String(warnings.length);
    }
    if (bell) {
      bell.classList.toggle('has-warnings', warnings.length > 0);
      bell.classList.toggle('has-errors', hasErrors);
      bell.title = warnings.length ? warnings.length + ' Hinweise' : 'Keine Hinweise';
    }
    if (summary) summary.textContent = warnings.length ? warnings.length + ' offen' : 'Alles bereit';
    if (!list) return;
    if (!warnings.length) {
      list.innerHTML = '<div class="warning-empty">Keine offenen Hinweise.</div>';
      return;
    }
    list.innerHTML = warnings.map(function(item, index){
      var icon = item.level === 'error' ? 'x' : (item.level === 'warning' ? 'warning' : 'info');
      return '<button class="warning-item ' + escapeHtml(item.level) + '" data-warning-action="' + index + '">' +
        '<span data-icon="' + icon + '"></span>' +
        '<span><strong>' + escapeHtml(item.title) + '</strong><small>' + escapeHtml(item.text) + '</small></span>' +
      '</button>';
    }).join('');
    list.querySelectorAll('[data-warning-action]').forEach(function(button){
      button.addEventListener('click', function(){
        var item = warnings[Number(button.getAttribute('data-warning-action'))];
        if (item) runWarningAction(item.action);
      });
    });
    if (autoOpen && !warningsAutoOpened && warnings.length) {
      warningsAutoOpened = true;
      var menu = document.querySelector('[data-warning-menu]');
      if (menu) menu.hidden = false;
    }
  }
  function submitCompanyCreate(chooseExcel){
    var bridge = window.lohnmailBridge;
    var nameInput = document.querySelector('[data-company-create="name"]');
    var idInput = document.querySelector('[data-company-create="id"]');
    var name = nameInput ? nameInput.value.trim() : '';
    var id = idInput ? idInput.value.trim() : '';
    if (!name) {
      setCompanyCreateMessage('Bitte Unternehmensname eingeben.', true);
      if (nameInput) nameInput.focus();
      return;
    }
    if (!id) {
      id = normalizeCompanyId(name);
      if (idInput) idInput.value = id;
    }
    if (!bridge || !bridge.createCompany) {
      setCompanyCreateMessage('Bridge ist noch nicht bereit.', true);
      return;
    }
    setCompanyCreateMessage(chooseExcel ? 'Mandant wird erstellt. Excel-Auswahl wird geöffnet...' : 'Mandant wird erstellt...', false);
    bridge.createCompany(JSON.stringify({ name: name, id: id, choose_excel: !!chooseExcel }), function(payload){
      try {
        var result = JSON.parse(payload || '{}');
        if (result.state) applyCompanyState(result.state);
        if (result.ok) {
          closeCompanyCreateModal();
          loadProcessingState();
          loadDashboardState();
          setCompanyMessage(result.message || 'Mandant wurde erstellt.');
        } else {
          setCompanyCreateMessage(result.message || 'Mandant konnte nicht erstellt werden.', true);
        }
      } catch (error) {
        setCompanyCreateMessage('Mandant konnte nicht erstellt werden.', true);
      }
    });
  }
  function formatCompanyPeriod(period){
    period = period || {};
    var month = Number(period.month || 0);
    var year = Number(period.year || 0);
    if (!month || !year) return 'Automatisch';
    return String(month).padStart(2, '0') + '.' + year;
  }
  function renderCompanyList(companies){
    var list = document.querySelector('[data-company="company-list"]');
    if (!list) return;
    companies = companies || [];
    if (!companies.length) {
      list.innerHTML = '<div class="company-note">Keine Mandanten in settings.json gefunden.</div>';
      return;
    }
    list.innerHTML = companies.map(function(company){
      var excel = company.excel || {};
      var ready = !!excel.valid;
      return '<button class="company-row ' + (company.selected ? 'active ' : '') + (ready ? 'ready' : '') + '" data-company-id="' + escapeHtml(company.id) + '">' +
        '<span class="company-avatar">' + escapeHtml(companyInitials(company.name)) + '</span>' +
        '<span><strong>' + escapeHtml(company.name || company.id || '-') + '</strong><small>' + escapeHtml(excel.path || 'Keine Excel-Datei ausgewählt') + '</small></span>' +
        '<b>' + escapeHtml(company.selected ? 'Aktiv' : (ready ? 'Bereit' : 'Offen')) + '</b>' +
      '</button>';
    }).join('');
    list.querySelectorAll('[data-company-id]').forEach(function(button){
      button.addEventListener('click', function(){
        runCompanyAction('select-company', button.getAttribute('data-company-id'));
      });
    });
  }
  function companyEditField(path){
    return document.querySelector('[data-company-edit-field="' + path + '"]');
  }
  function setCompanyEditValue(path, value){
    var field = companyEditField(path);
    if (!field) return;
    field.value = value === undefined || value === null ? '' : String(value);
  }
  function updateCompanyMailEditVisibility(){
    var scopeField = companyEditField('mail_scope');
    var panel = document.querySelector('[data-company-mail-edit]');
    var custom = !!scopeField && scopeField.value === 'custom';
    if (panel) panel.hidden = !custom;
    document.querySelectorAll('[data-company-action="test-company-mail"]').forEach(function(button){
      button.disabled = !custom || !(latestCompanyState && latestCompanyState.selected_company_id);
      button.title = custom ? 'Eigene SMTP Einstellungen prüfen' : 'Globale E-Mail Einstellungen werden unter Einstellungen geprüft.';
    });
  }
  function applyCompanyEditState(state){
    state = state || {};
    var smtp = state.smtp || {};
    var smtpSettings = smtp.settings || {};
    setCompanyEditValue('name', state.selected_company_name || '');
    setCompanyEditValue('id', state.selected_company_id || '');
    setCompanyEditValue('mail_scope', smtp.scope || 'global');
    setCompanyEditValue('smtp.server', smtpSettings.server || '');
    setCompanyEditValue('smtp.port', smtpSettings.port || 587);
    setCompanyEditValue('smtp.security', smtpSettings.security || 'tls');
    setCompanyEditValue('smtp.username', smtpSettings.username || '');
    setCompanyEditValue('smtp.password', '');
    setCompanyEditValue('smtp.from_email', smtpSettings.from_email || '');
    setCompanyEditValue('smtp.from_name', smtpSettings.from_name || '');
    setCompanyEditValue('smtp.timeout_sec', smtpSettings.timeout_sec || 30);
    var passwordField = companyEditField('smtp.password');
    if (passwordField) passwordField.placeholder = smtp.password_set ? 'Gespeichert - leer lassen = beibehalten' : 'Nicht gesetzt';
    updateCompanyMailEditVisibility();
  }
  function collectCompanyEditForm(){
    var payload = {
      name: (companyEditField('name') && companyEditField('name').value.trim()) || '',
      mail_scope: (companyEditField('mail_scope') && companyEditField('mail_scope').value) || 'global',
      smtp: {}
    };
    [
      'server',
      'port',
      'security',
      'username',
      'password',
      'from_email',
      'from_name',
      'timeout_sec'
    ].forEach(function(key){
      var field = companyEditField('smtp.' + key);
      if (!field) return;
      if (field.type === 'number') payload.smtp[key] = Number(field.value || 0);
      else payload.smtp[key] = field.value;
    });
    if (!String(payload.smtp.password || '')) delete payload.smtp.password;
    return payload;
  }
  function applyCompanyState(state){
    latestCompanyState = state || null;
    state = state || {};
    var selectedExcel = state.selected_excel || {};
    var output = state.output || {};
    var smtp = state.smtp || {};
    var license = state.license || {};
    if (license.status || license.label) {
      latestLicenseState = license;
    }

    setText('[data-company="selected-name"]', state.selected_company_name || '-');
    setText('[data-company="selected-id"]', state.selected_company_id || '-');
    setText('[data-company="excel-status"]', selectedExcel.valid ? 'Bereit' : 'Offen');
    setText('[data-company="excel-updated"]', selectedExcel.updated || '--');
    setText('[data-company="smtp-status"]', smtp.label || 'Nicht konfiguriert');
    setText('[data-company="smtp-from"]', smtp.from || smtp.server || '-');
    setText('[data-company="license-status"]', license.label || 'Nicht registriert');
    setText('[data-company="detail-name"]', state.selected_company_name || '-');
    setText('[data-company="detail-id"]', state.selected_company_id || '-');
    setText('[data-company="detail-excel"]', selectedExcel.path || '-');
    setText('[data-company="detail-output"]', output.path || '-');
    setText('[data-company="detail-period"]', formatCompanyPeriod(state.period));
    setText('[data-company="detail-mail-mode"]', (smtp.scope === 'custom' ? 'Eigene SMTP' : ('Global ' + (smtp.mode || 'smtp'))));
    setText('[data-company="status-excel"]', selectedExcel.valid ? 'Bereit' : 'Offen');
    setText('[data-company="status-output"]', output.valid ? 'Bereit' : 'Offen');
    setText('[data-company="status-smtp"]', smtp.configured ? 'Bereit' : 'Offen');
    setText('[data-company="status-license"]', license.label || 'Nicht registriert');
    applyCompanyEditState(state);
    renderCompanyList(state.companies || []);
    renderCompanySwitcher(state);
    updateWarningCenter();

    document.querySelectorAll('[data-company-action="open-excel"]').forEach(function(button){
      button.disabled = !selectedExcel.valid;
      button.title = selectedExcel.valid ? selectedExcel.path : 'Keine gültige Excel-Datei ausgewählt.';
    });
    document.querySelectorAll('[data-company-action="open-output"]').forEach(function(button){
      button.disabled = !output.valid;
      button.title = output.valid ? output.path : 'Ausgabeordner ist nicht verfügbar.';
    });
    document.querySelectorAll('[data-company-action="save-company"]').forEach(function(button){
      button.disabled = !state.selected_company_id;
    });
    updateCompanyMailEditVisibility();
  }
  function consumeCompanyPayload(payload){
    try {
      var state = JSON.parse(payload || '{}');
      applyCompanyState(state);
      return state;
    } catch (error) {
      console.warn('Unternehmen state konnte nicht verarbeitet werden', error);
      setCompanyMessage('Unternehmensdaten konnten nicht verarbeitet werden.');
    }
    return null;
  }
  function loadCompanyState(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.getCompanyState) {
      setCompanyMessage('Bridge ist noch nicht bereit.');
      return;
    }
    bridge.getCompanyState(function(payload){
      consumeCompanyPayload(payload);
    });
  }
  function runCompanyAction(action, value){
    var bridge = window.lohnmailBridge;
    if (!bridge) {
      setCompanyMessage('Bridge ist noch nicht bereit.');
      return;
    }
    if (action === 'refresh') {
      loadCompanyState();
      loadDashboardState();
      setCompanyMessage('Unternehmensdaten wurden aktualisiert.');
      return;
    }
    if (action === 'new-company') {
      openCompanyCreateModal();
      return;
    }
    if (action === 'select-company' && bridge.selectCompany) {
      bridge.selectCompany(value || '', function(payload){
        consumeCompanyPayload(payload);
        loadProcessingState();
        loadDashboardState();
        setCompanyMessage('Aktiver Mandant wurde gewechselt.');
      });
      return;
    }
    if (action === 'choose-excel' && bridge.chooseCompanyExcelInput) {
      bridge.chooseCompanyExcelInput(function(payload){
        consumeCompanyPayload(payload);
        loadProcessingState();
        loadDashboardState();
        setCompanyMessage('Excel-Datei wurde aktualisiert.');
      });
      return;
    }
    if (action === 'save-company' && bridge.saveCompanyState) {
      setCompanyMessage('Mandant wird gespeichert...');
      bridge.saveCompanyState(JSON.stringify(collectCompanyEditForm()), function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          if (result.state) consumeCompanyPayload(JSON.stringify(result.state));
          loadProcessingState();
          loadDashboardState();
          loadSettingsState();
          setCompanyMessage(result.message || (result.ok ? 'Mandant wurde gespeichert.' : 'Mandant konnte nicht gespeichert werden.'));
        } catch (error) {
          setCompanyMessage('Mandant konnte nicht gespeichert werden.');
        }
      });
      return;
    }
    if (action === 'test-company-mail' && bridge.testCompanyMailConnection) {
      if (bridge.saveCompanyState) {
        setCompanyMessage('Mandant wird gespeichert. SMTP wird danach geprüft...');
        bridge.saveCompanyState(JSON.stringify(collectCompanyEditForm()), function(payload){
          try {
            var result = JSON.parse(payload || '{}');
            if (result.state) consumeCompanyPayload(JSON.stringify(result.state));
            if (!result.ok) {
              setCompanyMessage(result.message || 'Mandant konnte nicht gespeichert werden.');
              return;
            }
            bridge.testCompanyMailConnection(function(testPayload){
              try {
                var testResult = JSON.parse(testPayload || '{}');
                setCompanyMessage(testResult.message || (testResult.ok ? 'Mandant SMTP ist bereit.' : 'Mandant SMTP konnte nicht geprüft werden.'));
              } catch (error) {
                setCompanyMessage('Mandant SMTP konnte nicht geprüft werden.');
              }
            });
          } catch (error) {
            setCompanyMessage('Mandant SMTP konnte nicht geprüft werden.');
          }
        });
      }
      return;
    }
    if (action === 'open-excel' && bridge.openCompanyExcel) {
      bridge.openCompanyExcel(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          setCompanyMessage(result.message || (result.ok ? 'Excel-Datei geöffnet.' : 'Excel-Datei konnte nicht geöffnet werden.'));
        } catch (error) {
          setCompanyMessage('Excel-Datei konnte nicht geöffnet werden.');
        }
      });
      return;
    }
    if (action === 'open-output' && bridge.openOutputFolder) {
      bridge.openOutputFolder(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          setCompanyMessage(result.message || (result.ok ? 'Ausgabeordner geöffnet.' : 'Ausgabeordner konnte nicht geöffnet werden.'));
        } catch (error) {
          setCompanyMessage('Ausgabeordner konnte nicht geöffnet werden.');
        }
      });
      return;
    }
    setCompanyMessage('Aktion ist im Bridge nicht verfügbar.');
  }
  function setLicenseMessage(message){
    setText('[data-license="message"]', message);
  }
  function formatDateTime(value){
    if (!value) return '-';
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
  function firstDateValue(){
    for (var i = 0; i < arguments.length; i += 1) {
      if (arguments[i]) return arguments[i];
    }
    return '';
  }
  function licenseStatusClass(level){
    if (level === 'error') return 'failed';
    if (level === 'warning') return 'warning';
    if (level === 'ready' || level === 'success') return 'ready';
    return 'warning';
  }
  function licenseMessageFromState(state, fallback){
    if (state && state.message) return state.message;
    return fallback || 'Lizenzstatus geladen.';
  }
  function applyLicenseState(state){
    latestLicenseState = state || null;
    state = state || {};
    if (latestCompanyState) {
      latestCompanyState.license = state;
    }
    if (latestDashboardState) {
      latestDashboardState.license = state;
    }
    var active = !!state.active;
    var trialEnd = firstDateValue(state.trial_ends_at, state.related_trial_ends_at);
    var accessEnd = firstDateValue(state.access_ends_at, state.current_period_end, trialEnd);
    var relatedTrialKey = state.related_trial_key_masked || '';
    setText('[data-license="status"]', state.label || 'Nicht registriert');
    setText('[data-license="mode"]', state.mode || 'Lokal');
    setText('[data-license="type"]', state.type || 'Nicht registriert');
    setText('[data-license="plan"]', state.plan || '-');
    setText('[data-license="days"]', state.days_remaining !== null && state.days_remaining !== undefined ? state.days_remaining + ' Tage' : '-');
    setText('[data-license="trial-end"]', accessEnd ? 'bis ' + formatDateTime(accessEnd) : '-');
    setText('[data-license="server"]', state.server || 'Nicht verbunden');
    setText('[data-license="server-note"]', state.server_note || (state.server === 'Verbunden' ? 'Online-Prüfung aktiv' : 'Keine Serverlogik aktiv'));
    setText('[data-license="key"]', state.key_masked || 'Nicht hinterlegt');
    setText('[data-license="detail-mode"]', state.mode || 'Lokal');
    setText('[data-license="detail-company"]', state.company || '-');
    setText('[data-license="machine-id"]', state.machine_id || '-');
    setText('[data-license="access-end"]', accessEnd ? formatDateTime(accessEnd) : '-');
    setText('[data-license="trial-end-detail"]', trialEnd ? formatDateTime(trialEnd) : '-');
    setText('[data-license="period-end"]', state.current_period_end ? formatDateTime(state.current_period_end) : '-');
    setText('[data-license="trial-source"]', relatedTrialKey || (trialEnd && state.type !== 'trial' ? 'Verknüpfter Trial' : '-'));
    setText('[data-license="checked-at"]', new Date().toLocaleString('de-DE'));
    setLicenseMessage(licenseMessageFromState(state));

    var badge = document.querySelector('[data-license="badge"]');
    if (badge) {
      badge.textContent = state.label || 'Nicht registriert';
      badge.className = 'state ' + licenseStatusClass(state.status_level || (active ? 'ready' : 'warning'));
    }

    var stateList = document.querySelector('[data-license="state-list"]');
    var states = state.state_list || [];
    if (stateList && states.length) {
      stateList.innerHTML = states.map(function(item){
        var className = 'license-state ' + escapeHtml(item.level || 'info') + (item.active ? ' current' : '');
        return '<span class="' + className + '"><span>' + escapeHtml(item.label || item.status || '-') + '</span>' + (item.active ? '<b>Aktuell</b>' : '') + '</span>';
      }).join('');
    }

    var historyBody = document.querySelector('[data-license="history-body"]');
    var history = state.history || [];
    if (historyBody) {
      if (!history.length) {
        historyBody.innerHTML = '<tr><td colspan="5">Noch keine lokale Aktivierungshistorie vorhanden.</td></tr>';
      } else {
        historyBody.innerHTML = history.map(function(item){
          return '<tr><td>' + escapeHtml(item.date || '-') + '</td><td>' + escapeHtml(item.action || '-') + '</td><td>' + escapeHtml(item.computer || '-') + '</td><td>' + escapeHtml(item.user || '-') + '</td><td>' + escapeHtml(item.status || '-') + '</td></tr>';
        }).join('');
      }
    }
    updateWarningCenter();
  }
  function consumeLicensePayload(payload){
    try {
      var state = JSON.parse(payload || '{}');
      applyLicenseState(state);
      return state;
    } catch (error) {
      console.warn('Lizenz state konnte nicht verarbeitet werden', error);
      setLicenseMessage('Lizenzdaten konnten nicht verarbeitet werden.');
    }
    return null;
  }
  function loadLicenseState(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.getLicenseState) {
      setLicenseMessage('Bridge ist noch nicht bereit.');
      return;
    }
    bridge.getLicenseState(function(payload){
      consumeLicensePayload(payload);
    });
  }
  function runLicenseAction(action){
    if (action === 'refresh') {
      setLicenseMessage('Lizenzstatus wird aktualisiert...');
      loadLicenseState();
      loadDashboardState();
      return;
    }
    if (action === 'check' && window.lohnmailBridge && window.lohnmailBridge.checkLicense) {
      setLicenseMessage('Lizenz wird online geprüft...');
      window.lohnmailBridge.checkLicense(function(payload){
        consumeLicensePayload(payload);
        loadDashboardState();
      });
      return;
    }
    if (action === 'buy' && window.lohnmailBridge && window.lohnmailBridge.buyLicense) {
      setLicenseMessage('Stripe Checkout wird geöffnet...');
      window.lohnmailBridge.buyLicense(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          if (result.state) applyLicenseState(result.state);
          setLicenseMessage(licenseMessageFromState(result.state, result.ok ? 'Stripe Checkout wurde geöffnet.' : (result.message || 'Checkout konnte nicht geöffnet werden.')));
        } catch (error) {
          setLicenseMessage('Checkout konnte nicht geöffnet werden.');
        }
      });
      return;
    }
    if (action === 'portal' && window.lohnmailBridge && window.lohnmailBridge.openCustomerPortal) {
      setLicenseMessage('Stripe Kundenportal wird geöffnet...');
      window.lohnmailBridge.openCustomerPortal(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          if (result.state) applyLicenseState(result.state);
          setLicenseMessage(licenseMessageFromState(result.state, result.ok ? 'Kundenportal wurde geöffnet.' : (result.message || 'Kundenportal konnte nicht geöffnet werden.')));
        } catch (error) {
          setLicenseMessage('Kundenportal konnte nicht geöffnet werden.');
        }
      });
      return;
    }
    if (action === 'activate' && window.lohnmailBridge && window.lohnmailBridge.promptActivateLicenseKey) {
      setLicenseMessage('Lizenzschlüssel wird abgefragt...');
      window.lohnmailBridge.promptActivateLicenseKey(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          if (result.state) applyLicenseState(result.state);
          setLicenseMessage(licenseMessageFromState(result.state, result.ok ? 'Lizenz wurde aktiviert.' : (result.message || 'Lizenz konnte nicht aktiviert werden.')));
          loadDashboardState();
        } catch (error) {
          setLicenseMessage('Lizenz konnte nicht aktiviert werden.');
        }
      });
      return;
    }
    if (action === 'deactivate' && window.lohnmailBridge && window.lohnmailBridge.deactivateLicense) {
      setLicenseMessage('Lizenz wird deaktiviert...');
      window.lohnmailBridge.deactivateLicense(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          if (result.state) applyLicenseState(result.state);
          setLicenseMessage(licenseMessageFromState(result.state, result.ok ? 'Lizenz wurde deaktiviert.' : (result.message || 'Lizenz konnte nicht deaktiviert werden.')));
          loadDashboardState();
        } catch (error) {
          setLicenseMessage('Lizenz konnte nicht deaktiviert werden.');
        }
      });
      return;
    }
    if (action === 'history') {
      setLicenseMessage('Es gibt aktuell keine lokale Aktivierungshistorie.');
      return;
    }
    setLicenseMessage('Lizenzaktion ist im Bridge nicht verfügbar.');
  }
  function setSettingsMessage(message){
    setText('[data-settings="message"]', message);
  }
  function setSettingsMailMessage(message){
    setText('[data-settings="mail-message"]', message);
  }
  function setSettingsTemplatesMessage(message){
    setText('[data-settings="templates-message"]', message);
  }
  function getNestedValue(source, path){
    return path.split('.').reduce(function(current, key){
      return current && current[key] !== undefined ? current[key] : undefined;
    }, source);
  }
  function setNestedValue(target, path, value){
    var parts = path.split('.');
    var current = target;
    parts.forEach(function(part, index){
      if (index === parts.length - 1) {
        current[part] = value;
      } else {
        if (!current[part] || typeof current[part] !== 'object') current[part] = {};
        current = current[part];
      }
    });
  }
  function formatSettingsPeriod(period){
    period = period || {};
    var month = Number(period.month || 0);
    var year = Number(period.year || 0);
    return month && year ? String(month).padStart(2, '0') + '.' + year : 'Automatisch';
  }
  function applySettingsState(state){
    latestSettingsState = state || null;
    state = state || {};
    document.querySelectorAll('[data-settings-field]').forEach(function(field){
      var key = field.getAttribute('data-settings-field');
      var value = getNestedValue(state, key);
      if (key === 'smtp.password') {
        field.value = '';
        field.placeholder = state.smtp && state.smtp.password_set ? 'Gespeichert - leer lassen = beibehalten' : 'Nicht gesetzt';
        return;
      }
      if (field.type === 'checkbox') {
        field.checked = !!value;
      } else if (value !== undefined && value !== null) {
        field.value = String(value);
      }
    });

    var smtp = state.smtp || {};
    var company = state.company || {};
    var period = state.period || {};
    var ui = state.ui || {};
    setText('[data-settings-summary="mail-mode"]', state.mail_mode || 'smtp');
    setText('[data-settings-summary="smtp-status"]', smtp.server && smtp.from_email ? 'Konfiguriert' : 'Nicht konfiguriert');
    setText('[data-settings-summary="company"]', company.selected_company_name || '-');
    setText('[data-settings-summary="company-id"]', company.selected_company_id || '-');
    setText('[data-settings-summary="period"]', formatSettingsPeriod(period));
    setText('[data-settings-summary="period-mode"]', period.mode || 'automatic_current_month');
    setText('[data-settings-summary="dry-run"]', ui.dry_run_default ? 'Aktiv' : 'Aus');
    updateWarningCenter();
  }
  function collectSettingsForm(){
    var payload = {};
    document.querySelectorAll('[data-settings-field]').forEach(function(field){
      var key = field.getAttribute('data-settings-field');
      var value;
      if (field.type === 'checkbox') value = field.checked;
      else if (field.type === 'number') value = Number(field.value || 0);
      else value = field.value;
      if (key === 'smtp.password' && !String(value || '')) return;
      setNestedValue(payload, key, value);
    });
    return payload;
  }
  function consumeSettingsPayload(payload){
    try {
      var result = JSON.parse(payload || '{}');
      if (result && result.ok === false && result.message) {
        setSettingsMessage(result.message);
        return null;
      }
      if (result.state) {
        applySettingsState(result.state);
        setSettingsMessage(result.message || 'Einstellungen wurden gespeichert.');
        return result.state;
      }
      applySettingsState(result);
      return result;
    } catch (error) {
      console.warn('Einstellungen state konnte nicht verarbeitet werden', error);
      setSettingsMessage('Einstellungen konnten nicht verarbeitet werden.');
    }
    return null;
  }
  function loadSettingsState(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.getSettingsState) {
      setSettingsMessage('Bridge ist noch nicht bereit.');
      return;
    }
    bridge.getSettingsState(function(payload){
      consumeSettingsPayload(payload);
    });
  }
  function saveSettingsForm(messageSetter, successMessage, callback){
    var bridge = window.lohnmailBridge;
    var setMessage = messageSetter || setSettingsMessage;
    if (!bridge || !bridge.saveSettingsState) {
      setMessage('Speichern ist im Bridge nicht verfügbar.');
      return;
    }
    setMessage('Einstellungen werden gespeichert...');
    bridge.saveSettingsState(JSON.stringify(collectSettingsForm()), function(payload){
      var rawResult = {};
      try {
        rawResult = JSON.parse(payload || '{}');
      } catch (error) {
        rawResult = {};
      }
      var state = consumeSettingsPayload(payload);
      loadDashboardState();
      loadCompanyState();
      loadLicenseState();
      loadProcessingState();
      if (!state) {
        setMessage(rawResult.message || 'Einstellungen konnten nicht gespeichert werden.');
        return;
      }
      setMessage(successMessage || 'Einstellungen wurden gespeichert.');
      if (callback) callback(state);
    });
  }
  function testMailConnectionAfterSave(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.testMailConnection) {
      setSettingsMailMessage('Mail-Test ist im Bridge nicht verfügbar.');
      return;
    }
    saveSettingsForm(setSettingsMailMessage, 'E-Mail Einstellungen gespeichert. Verbindung wird geprüft...', function(){
      setSettingsMailMessage('Mail-Verbindung wird geprüft...');
      bridge.testMailConnection(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          setSettingsMailMessage(result.message || (result.ok ? 'Mail-Verbindung ist bereit.' : 'Mail-Verbindung fehlgeschlagen.'));
        } catch (error) {
          setSettingsMailMessage('Mail-Verbindung konnte nicht geprüft werden.');
        }
      });
    });
  }
  function runSettingsAction(action){
    var bridge = window.lohnmailBridge;
    if (action === 'reload') {
      loadSettingsState();
      setSettingsMessage('Einstellungen wurden neu geladen.');
      setSettingsMailMessage('Einstellungen wurden neu geladen.');
      setSettingsTemplatesMessage('Vorlagen wurden neu geladen.');
      return;
    }
    if (action === 'save') {
      saveSettingsForm(setSettingsMessage, 'Einstellungen wurden gespeichert.');
      return;
    }
    if (action === 'save-email') {
      saveSettingsForm(setSettingsMailMessage, 'E-Mail Einstellungen wurden gespeichert.');
      return;
    }
    if (action === 'save-templates') {
      saveSettingsForm(setSettingsTemplatesMessage, 'E-Mail Vorlage wurde gespeichert.');
      return;
    }
    if (action === 'test-mail') {
      testMailConnectionAfterSave();
      return;
    }
    if (action === 'load-outlook') {
      if (!bridge || !bridge.getOutlookAccounts) {
        setSettingsMailMessage('Outlook-Konten sind im Bridge nicht verfügbar.');
        return;
      }
      bridge.getOutlookAccounts(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          if (!result.ok) {
            setSettingsMailMessage(result.message || 'Outlook-Konten konnten nicht geladen werden.');
            return;
          }
          var accounts = result.accounts || [];
          setSettingsMailMessage(accounts.length ? ('Outlook-Konten: ' + accounts.map(function(account){ return account.label || account.identifier; }).join(', ')) : 'Outlook ist unterstützt. Unter macOS liefert Outlook keine Kontenliste; Absender E-Mail wird direkt verwendet.');
        } catch (error) {
          setSettingsMailMessage('Outlook-Konten konnten nicht verarbeitet werden.');
        }
      });
      return;
    }
    if (action === 'open-company') {
      setPage('Unternehmen');
      return;
    }
    if (action === 'open-license') {
      setPage('Lizenzen');
      return;
    }
    if (action === 'open-processing') {
      setPage('Verarbeitung');
      return;
    }
    if (action === 'open-reports') {
      setPage('Berichte');
      return;
    }
    if (
      action === 'clear-cache' ||
      action === 'clear-all-caches' ||
      action === 'export-settings' ||
      action === 'import-settings' ||
      action === 'reset-settings'
    ) {
      setSettingsMessage('Diese Wartungsfunktion ist im Web UI ausgeblendet und noch nicht aktiviert.');
      return;
    }
    setSettingsMessage('Aktion ist nicht verfügbar.');
  }
  function setMassMessageText(key, value){
    setText('[data-mass="' + key + '"]', value);
  }
  function massField(name){
    return document.querySelector('[data-mass-field="' + name + '"]');
  }
  function massSubject(){
    var field = massField('subject');
    return field ? field.value.trim() : '';
  }
  function massBody(){
    var field = massField('body');
    return field ? field.value : '';
  }
  function setMassMessage(message){
    setMassMessageText('message', message);
  }
  function renderMassRecipients(rows){
    var node = document.querySelector('[data-mass="recipients"]');
    if (!node) return;
    rows = rows || [];
    if (!rows.length) {
      node.innerHTML = '<div>Keine Empfänger-Vorschau geladen.</div>';
      return;
    }
    node.innerHTML = '<table><thead><tr><th>PersNr</th><th>Name</th><th>E-Mail</th></tr></thead><tbody>' +
      rows.slice(0, 8).map(function(row){
        var name = [row.Name, row.Vorname].filter(Boolean).join(', ') || '-';
        return '<tr><td>' + escapeHtml(row.PersNr || '-') + '</td><td>' + escapeHtml(name) + '</td><td>' + escapeHtml(row.Email || '-') + '</td></tr>';
      }).join('') +
      '</tbody></table>';
  }
  function applyMassMessageState(state){
    latestMassMessageState = state || null;
    state = state || {};
    var status = state.status || {};
    var preview = state.preview || {};
    var excel = state.excel || {};
    var company = state.company || {};
    var progress = Number(status.progress || 0);
    var total = Number(preview.total_count || status.total_count || 0);
    var sendButton = document.querySelector('[data-mass-action="send"]');
    var progressNode = document.querySelector('[data-mass="progress"]');

    setMassMessageText('mode', state.mail_mode || 'smtp');
    setMassMessageText('company', preview.company_name || company.name || '-');
    setMassMessageText('excel', excel.path || preview.excel_path || 'Excel-Datei prüfen');
    setMassMessageText('recipient-count', total + ' Empfänger');
    setMassMessageText('preview-subject', preview.subject_preview || 'Noch keine Vorschau');
    setMassMessage(status.message || 'Nachricht kann vorbereitet werden.');
    if (progressNode) progressNode.style.width = progress + '%';
    if (sendButton) {
      sendButton.disabled = !preview.ready || !!status.running;
      sendButton.classList.toggle('soft-disabled', !preview.ready || !!status.running);
      sendButton.title = preview.ready ? 'Sendet die Nachricht an alle Empfänger der Vorschau.' : 'Bitte zuerst Vorschau laden.';
    }
    renderMassRecipients(preview.rows || []);
  }
  function consumeMassMessagePayload(payload){
    try {
      var state = JSON.parse(payload || '{}');
      applyMassMessageState(state);
      return state;
    } catch (error) {
      console.warn('Nachricht state konnte nicht verarbeitet werden', error);
      setMassMessage('Nachricht-Status konnte nicht verarbeitet werden.');
    }
    return null;
  }
  function loadMassMessageState(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.getMassMessageState) {
      applyMassMessageState({});
      return;
    }
    bridge.getMassMessageState(function(payload){
      consumeMassMessagePayload(payload);
    });
  }
  function runMassMessageAction(action){
    var bridge = window.lohnmailBridge;
    if (action === 'focus') {
      setPage('Nachricht');
      var card = document.querySelector('[data-message-card]');
      if (card) {
        card.scrollIntoView({behavior:'smooth', block:'center'});
        var subject = massField('subject');
        if (subject) subject.focus();
      }
      return;
    }
    if (action === 'preview') {
      if (!bridge || !bridge.previewMassMessage) {
        setMassMessage('Bridge ist noch nicht bereit.');
        return;
      }
      setMassMessage('Vorschau wird geladen...');
      bridge.previewMassMessage(massSubject(), massBody(), function(payload){
        consumeMassMessagePayload(payload);
      });
      return;
    }
    if (action === 'send') {
      if (!bridge || !bridge.startMassMessage) {
        setMassMessage('Bridge ist noch nicht bereit.');
        return;
      }
      setMassMessage('Nachricht-Versand wird gestartet...');
      bridge.startMassMessage(massSubject(), massBody(), function(payload){
        consumeMassMessagePayload(payload);
      });
      return;
    }
  }
  function runHelpAction(action){
    var messages = {
      search: 'Suche ist vorbereitet. Die lokale Wissensdatenbank wird als statische Übersicht angezeigt.',
      topic: 'Hilfethema ausgewählt.',
      video: 'Video Tutorials sind in dieser lokalen Version nicht hinterlegt.',
      manual: 'PDF Handbuch ist noch nicht als lokale Datei hinterlegt.',
      release: 'Release Notes sind im Bereich Über LohnMail sichtbar.',
      status: 'Systemstatus wird im Dashboard und Footer angezeigt.',
      articles: 'Alle lokalen Hilfeartikel werden aktuell in der Übersicht angezeigt.',
      email: 'Support per E-Mail: support@lohnmail.de',
      phone: 'Telefon Support: +49 209 123456-99',
      remote: 'Remote Support ist in dieser lokalen UI noch nicht gestartet.',
      request: 'Support-Anfrage ist vorbereitet.'
    };
    if (action === 'release') {
      setPage('Über LohnMail');
      return;
    }
    if (action === 'status') {
      setPage('Dashboard');
      return;
    }
    setInfoBanner(messages[action] || 'Hilfeaktion ausgewählt.', true);
  }
  var aboutLegalContent = {
    privacy: {
      title: 'Datenschutzerklärung',
      intro: 'LohnMail verarbeitet Lohnunterlagen lokal auf diesem Rechner. Die Anwendung sammelt keine Nutzungsanalyse, überträgt keine Lohnunterlagen an Cloud-Dienste und sendet keine personenbezogenen Daten an den Hersteller.',
      sections: [
        ['Welche Daten verarbeitet werden', 'Verarbeitet werden nur die vom Benutzer ausgewählten PDF-Dateien, Excel-Listen, Ausgabepfade, E-Mail-Adressen und Versandinformationen, die für Prüfung, Berichtserstellung und Versand benötigt werden.'],
        ['Keine automatische Übertragung', 'LohnMail lädt keine Lohnunterlagen, Mitarbeiterdaten oder Prüfberichte automatisch ins Internet hoch. Eine Übertragung erfolgt nur, wenn der Benutzer aktiv einen Versand über SMTP oder Outlook auslöst.'],
        ['Lokale Speicherung', 'Temporäre Dateien, Berichte, Pfade und Anwendungseinstellungen werden lokal gespeichert. Der Benutzer bestimmt den Ausgabeordner und kann erzeugte Dateien außerhalb der Anwendung verwalten oder löschen.'],
        ['Keine Analyse und kein Tracking', 'Die Anwendung enthält kein Werbe-Tracking, keine Telemetrie und keine automatische Nutzungsstatistik. Es werden keine Gerätekennungen oder Verhaltensdaten an externe Dienste gesendet.'],
        ['Verantwortlichkeit', 'Der Betreiber der Installation bleibt für die Auswahl, Pflege und rechtmäßige Nutzung der Lohn- und Mitarbeiterdaten verantwortlich.']
      ]
    },
    terms: {
      title: 'Nutzungsbedingungen',
      intro: 'LohnMail ist eine lokale Desktop-Anwendung für interne Lohnabrechnungsprozesse. Die Nutzung erfolgt durch autorisierte Benutzer innerhalb der jeweiligen Organisation.',
      sections: [
        ['Zweck der Anwendung', 'Die Anwendung unterstützt Import, Prüfung, Berichtserstellung und Versand von Lohnunterlagen. Sie ersetzt keine fachliche, steuerliche oder rechtliche Prüfung durch den Betreiber.'],
        ['Benutzerverantwortung', 'Der Benutzer ist für korrekte Eingabedaten, gültige Empfängeradressen, passende Versandkonfiguration und die Kontrolle der erzeugten Ergebnisse verantwortlich.'],
        ['Lokale Umgebung', 'Die Funktionsfähigkeit hängt von der lokalen Python-/Qt-Installation, den installierten PDF- und Excel-Komponenten sowie den gewählten E-Mail-Einstellungen ab.']
      ]
    },
    license: {
      title: 'Lizenzvereinbarung',
      intro: 'Die Enterprise Edition ist für die Nutzung innerhalb des lizenzierten Unternehmens vorgesehen. Lizenzstatus und Aktivierung werden lokal in der Anwendung angezeigt.',
      sections: [
        ['Nutzungsumfang', 'Der erlaubte Nutzungsumfang richtet sich nach der aktivierten Edition und den vereinbarten Lizenzbedingungen.'],
        ['Aktivierung', 'Lizenzdaten werden nur zur Prüfung des lokalen Lizenzstatus verwendet. Eine automatische Übertragung von Lohnunterlagen ist damit nicht verbunden.'],
        ['Einschränkungen', 'Weitergabe, Veränderung oder Umgehung der Lizenzprüfung ist nur erlaubt, wenn dies ausdrücklich in der jeweiligen Lizenzvereinbarung vorgesehen ist.']
      ]
    },
    oss: {
      title: 'Open Source Lizenzen',
      intro: 'LohnMail verwendet ausgewählte Open-Source-Komponenten für Oberfläche, PDF-Verarbeitung, Excel-Verarbeitung und lokale Datenspeicherung.',
      sections: [
        ['Verwendete Komponenten', 'Zu den Komponenten gehören unter anderem Python, PySide6/Qt, SQLite, PyPDF2, openpyxl und weitere technische Bibliotheken.'],
        ['Lizenzhinweise', 'Die jeweiligen Lizenzbedingungen der verwendeten Komponenten bleiben gültig. Detaillierte Hinweise können in der Produktdokumentation oder den Paketinformationen eingesehen werden.'],
        ['Keine Datenfreigabe durch Bibliotheken', 'Die verwendeten lokalen Bibliotheken übertragen keine Lohnunterlagen automatisch an externe Dienste.']
      ]
    }
  };
  function renderAboutLegal(action){
    var content = aboutLegalContent[action];
    var modal = document.querySelector('[data-legal-modal]');
    if (!content || !modal) return false;
    var title = modal.querySelector('[data-legal-detail="title"]');
    var intro = modal.querySelector('[data-legal-detail="intro"]');
    var body = modal.querySelector('[data-legal-detail="body"]');
    if (title) title.textContent = content.title;
    if (intro) intro.textContent = content.intro;
    if (body) {
      body.innerHTML = content.sections.map(function(section){
        return '<section><h3>' + section[0] + '</h3><p>' + section[1] + '</p></section>';
      }).join('');
    }
    document.querySelectorAll('.legal-list [data-about-action]').forEach(function(button){
      button.classList.toggle('active', button.getAttribute('data-about-action') === action);
    });
    modal.hidden = false;
    return true;
  }
  function closeAboutLegalModal(){
    var modal = document.querySelector('[data-legal-modal]');
    if (modal) modal.hidden = true;
  }
  function runAboutAction(action){
    var messages = {
      website: 'Website-Link ist in dieser lokalen Version noch nicht hinterlegt.',
      release: 'Release Notes werden als Produktinformation angezeigt.',
      details: 'Technische Details sind in der Komponentenübersicht sichtbar.',
      support: 'Supportbereich wird geöffnet.'
    };
    if (renderAboutLegal(action)) {
      return;
    }
    if (action === 'support') {
      setPage('Hilfe');
      return;
    }
    setInfoBanner(messages[action] || 'Produktaktion ausgewählt.', true);
  }
  function workflowReadyState(){
    var validationReady = !!(latestValidationState && latestValidationState.ready);
    var validationRows = (latestValidationState && latestValidationState.rows) || [];
    var shippingRowsList = (latestShippingState && latestShippingState.rows) || [];
    var reports = (latestValidationState && latestValidationState.reports) || {};
    var shippingReports = (latestShippingState && latestShippingState.reports) || {};
    var reportReady = !!(
      (reports.audit && reports.audit.exists) ||
      (reports.missing && reports.missing.exists) ||
      (shippingReports.send && shippingReports.send.exists)
    );
    return {
      inputs: true,
      validation: validationReady || validationRows.length > 0,
      shipping: validationRows.length > 0 || shippingRowsList.length > 0,
      reports: reportReady,
      warnings: validationRows.some(function(row){ return row.status === 'Keine E-Mail'; }),
      errors: validationRows.some(function(row){ return row.severity === 'critical' || row.status === 'Fehler' || row.status === 'Keine Dateien'; })
    };
  }
  function updateCompactWorkflowTrackers(currentPage){
    var ready = workflowReadyState();
    var page = currentPage || (document.querySelector('.page.active') || {}).dataset.page || 'Dashboard';
    document.querySelectorAll('[data-global-workflow]').forEach(function(tracker){
      tracker.querySelectorAll('[data-workflow-step]').forEach(function(button){
        var step = button.getAttribute('data-workflow-step');
        var target = button.getAttribute('data-workflow-target');
        var key = step === 'pdf' || step === 'excel' || step === 'processing' ? 'inputs' : (step === 'validation' ? 'validation' : (step === 'shipping' ? 'shipping' : 'reports'));
        var isReady = !!ready[key];
        var isCurrent = target === page;
        var isWarning = step === 'validation' && ready.warnings && !ready.errors;
        var isError = step === 'validation' && ready.errors;
        button.disabled = !isReady && target !== 'Verarbeitung';
        button.classList.toggle('done', isReady && !isCurrent && !isWarning && !isError);
        button.classList.toggle('active', isCurrent);
        button.classList.toggle('muted', button.disabled);
        button.classList.toggle('workflow-warning', isWarning && !isCurrent);
        button.classList.toggle('workflow-error', isError && !isCurrent);
        var label = button.querySelector('small');
        if (label) {
          if (isCurrent) label.textContent = 'Aktuell';
          else if (button.disabled) label.textContent = 'Wartet';
          else if (isError) label.textContent = 'Fehler';
          else if (isWarning) label.textContent = 'Warnung';
          else label.textContent = 'Bereit';
        }
      });
    });
  }
  function navigateWorkflowTarget(target){
    if (!target) return;
    if (target === 'Verarbeitung') {
      setPage('Verarbeitung');
      return;
    }
    var ready = workflowReadyState();
    if (target === 'Prüfung' && ready.validation) setPage('Prüfung');
    if (target === 'Versand' && ready.shipping) setPage('Versand');
    if (target === 'Berichte' && ready.reports) setPage('Berichte');
  }
  function setDashboardPipelineStep(key, state, label){
    var step = document.querySelector('[data-dashboard-pipeline-step="' + key + '"]');
    var labelNode = document.querySelector('[data-dashboard-pipeline-label="' + key + '"]');
    if (step) {
      step.classList.remove('done', 'active', 'muted', 'warning', 'error');
      step.classList.add(state || 'muted');
    }
    if (labelNode) labelNode.textContent = label || 'Wartet';
  }
  function updateDashboardPipeline(){
    var processing = latestProcessingState || {};
    var inputs = processing.inputs || {};
    var processingStatus = processing.status || {};
    var validation = latestValidationState || {};
    var validationRows = validation.rows || [];
    var validationSummary = validation.summary || {};
    var shipping = latestShippingState || {};
    var shippingMetrics = shipping.metrics || {};
    var shippingStatus = shipping.status || {};
    var dashboardReports = (latestDashboardState && latestDashboardState.reports) || {};
    var validationReports = validation.reports || {};
    var shippingReports = shipping.reports || {};

    var pdfReady = !!(inputs.pdf && inputs.pdf.valid);
    var excelReady = !!(inputs.excel && inputs.excel.valid);
    var processingFailed = !!processingStatus.failed;
    var validationReady = !!(validation.ready || validationRows.length || validationSummary.total || processingStatus.finished);
    var validationWarnings = validationRows.some(function(row){ return row.severity === 'warning' || row.status === 'Keine E-Mail'; });
    var validationErrors = validationRows.some(function(row){ return row.severity === 'critical' || row.status === 'Fehler' || row.status === 'Keine Dateien'; });
    var shippingReady = Number(shippingMetrics.total || 0) > 0 || validationReady;
    var shippingDone = Number(shippingMetrics.sent || 0) > 0 || !!shippingStatus.finished;
    var reportsReady = !!(
      (dashboardReports.audit && dashboardReports.audit.exists) ||
      (dashboardReports.missing && dashboardReports.missing.exists) ||
      (dashboardReports.send && dashboardReports.send.exists) ||
      (validationReports.audit && validationReports.audit.exists) ||
      (validationReports.missing && validationReports.missing.exists) ||
      (shippingReports.send && shippingReports.send.exists)
    );

    setDashboardPipelineStep('pdf', pdfReady ? 'done' : 'active', pdfReady ? 'Bereit' : 'Prüfen');
    setDashboardPipelineStep('excel', excelReady ? 'done' : (pdfReady ? 'active' : 'muted'), excelReady ? 'Bereit' : 'Wartet');
    if (processingStatus.running) {
      setDashboardPipelineStep('validation', 'active', 'Läuft');
    } else if (processingFailed || validationErrors) {
      setDashboardPipelineStep('validation', 'error', 'Fehler');
    } else if (validationWarnings) {
      setDashboardPipelineStep('validation', 'warning', 'Warnung');
    } else {
      setDashboardPipelineStep('validation', validationReady ? 'done' : (pdfReady && excelReady ? 'active' : 'muted'), validationReady ? 'Bereit' : 'Wartet');
    }
    setDashboardPipelineStep('processing', validationReady ? 'done' : (processingStatus.running ? 'active' : 'muted'), validationReady ? 'Bereit' : (processingStatus.running ? 'Läuft' : 'Wartet'));
    setDashboardPipelineStep('shipping', shippingDone ? 'done' : (shippingReady ? 'active' : 'muted'), shippingDone ? 'Abgeschlossen' : (shippingReady ? 'Bereit' : 'Wartet'));
    setDashboardPipelineStep('reports', reportsReady ? 'done' : (shippingDone || validationReady ? 'active' : 'muted'), reportsReady ? 'Erstellt' : 'Wartet');

    var doneCount = [pdfReady, excelReady, validationReady, validationReady, shippingDone, reportsReady].filter(Boolean).length;
    var progress = processingStatus.running
      ? Math.max(0, Math.min(100, Number(processingStatus.progress || 0)))
      : Math.round((doneCount / 6) * 100);
    var progressBar = document.querySelector('[data-dashboard="pipeline-progress"]');
    if (progressBar) progressBar.style.width = progress + '%';
    setText('[data-dashboard="pipeline-progress-label"]', progress + '%');

    var message = 'Noch kein Lauf gestartet.';
    if (processingStatus.running) message = processingStatus.message || processingStatus.current_step || 'Prüfung läuft.';
    else if (processingFailed) message = processingStatus.message || 'Prüfung fehlgeschlagen.';
    else if (!pdfReady || !excelReady) message = 'PDF- und Excel-Eingaben prüfen.';
    else if (!validationReady) message = 'Eingaben bereit. Prüfung kann gestartet werden.';
    else if (validationErrors) message = 'Prüfung abgeschlossen. Kritische Fehler prüfen.';
    else if (validationWarnings) message = 'Prüfung abgeschlossen. Warnungen prüfen.';
    else if (!shippingDone) message = 'Prüfung abgeschlossen. Versand kann vorbereitet werden.';
    else if (!reportsReady) message = 'Versand vorbereitet. Berichte können erstellt werden.';
    else message = 'Workflow abgeschlossen. Berichte sind verfügbar.';
    setText('[data-dashboard="pipeline-message"]', message);
  }
  function applyDashboardState(state){
    if (!state) return;
    latestDashboardState = state;
    var metrics = state.metrics || {};
    setText('[data-dashboard="employees"]', metrics.employees || 0);
    setText('[data-dashboard="sent"]', metrics.sent || 0);
    setText('[data-dashboard="missing-email"]', metrics.missing_email || 0);
    setText('[data-dashboard="errors"]', metrics.errors || 0);
    setText('[data-dashboard="errors-label"]', metrics.errors ? 'Bitte prüfen' : 'Keine Fehler');

    var license = state.license || {};
    var mail = state.mail || {};
    if (license.status || license.label) {
      latestLicenseState = license;
    }
    setText('[data-dashboard="license-pill"]', 'Lizenz: ' + (license.label || 'Unbekannt'));
    setText('.side-status-title', (state.system && state.system.ready) ? 'System bereit' : 'System prüfen');
    setText('.side-status-subtitle', 'Mail: ' + (mail.label || 'Unbekannt'));
    setLabeledIconText('[data-dashboard="footer-license"]', 'Lizenz: ' + (license.label || 'Unbekannt'));
    setLabeledIconText('[data-dashboard="footer-mail"]', 'SMTP: ' + (mail.label || 'Unbekannt'));
    setLabeledIconText('[data-dashboard="footer-outlook"]', 'Outlook: Nicht geprüft');
    setLabeledIconText('[data-dashboard="footer-mode"]', 'Modus: Lokal');
    setLabeledIconText('[data-dashboard="footer-system"]', (state.system && state.system.ready) ? 'System bereit' : 'System prüfen');

    var system = state.system || {};
    setStatus('[data-dashboard="status-processing"]', system.processing || 'Bereit');
    setStatus('[data-dashboard="status-pdf"]', system.pdf || 'Bereit');
    setStatus('[data-dashboard="status-excel"]', system.excel || 'Bereit');
    setStatus('[data-dashboard="status-mail"]', system.mail || 'Offen');
    setStatus('[data-dashboard="status-license"]', system.license || 'Offen');
    setStatus('[data-dashboard="status-filesystem"]', system.filesystem || 'Bereit');

    var reports = state.reports || {};
    updateReport('audit', reports.audit);
    updateReport('missing', reports.missing);
    updateReport('send', reports.send);
    updateValidationReportActions(reports);
    updateCompactWorkflowTrackers();
    updateDashboardPipeline();
    updateWarningCenter();
    updateReportsScreen();
  }
  function runDashboardAction(action){
    var ready = workflowReadyState();
    if (action === 'new-run' || action === 'open-processing') {
      setPage('Verarbeitung');
      loadProcessingState();
      return;
    }
    if (action === 'open-shipping') {
      if (ready.shipping) {
        setPage('Versand');
        loadShippingState();
      } else {
        setPage('Verarbeitung');
        setInfoBanner('Bitte zuerst Prüfung ausführen. Danach kann Versand vorbereitet werden.', false);
      }
      return;
    }
    if (action === 'open-reports') {
      setPage('Berichte');
      loadReportsState();
      return;
    }
  }
  function loadDashboardState(){
    if (!window.lohnmailBridge || !window.lohnmailBridge.getDashboardState) return;
    window.lohnmailBridge.getDashboardState(function(payload){
      try {
        applyDashboardState(JSON.parse(payload || '{}'));
      } catch (error) {
        console.warn('Dashboard state konnte nicht geladen werden', error);
      }
    });
  }
  function escapeHtml(value){
    return String(value === undefined || value === null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
  function formatActivityTime(){
    var now = new Date();
    return [now.getHours(), now.getMinutes(), now.getSeconds()].map(function(part){
      return String(part).padStart(2, '0');
    }).join(':');
  }
  function pushProcessingLog(level, title, detail, key){
    if (!title) return;
    var logKey = key || [level, title, detail].join('|');
    if (logKey === lastProcessingLogKey) return;
    lastProcessingLogKey = logKey;
    processingActivityLog.unshift({
      time: formatActivityTime(),
      level: level || 'info',
      title: title,
      detail: detail || ''
    });
    processingActivityLog = processingActivityLog.slice(0, 24);
    renderProcessingLog();
  }
  function renderProcessingLog(){
    var list = document.querySelector('[data-processing="activity-log"]');
    if (!list) return;
    if (!processingActivityLog.length) {
      list.innerHTML = '<div class="log-empty"><span class="log-info"><span data-icon="clock"></span></span><b>Noch keine Aktivität</b><em>Der nächste Lauf wird hier protokolliert.</em></div>';
      return;
    }
    list.innerHTML = processingActivityLog.map(function(item){
      var icon = item.level === 'error' ? 'x' : (item.level === 'warning' ? 'warning' : (item.level === 'ok' ? 'checkcircle' : 'info'));
      var className = item.level === 'error' ? 'log-error' : (item.level === 'warning' ? 'log-warn' : (item.level === 'ok' ? 'log-ok' : 'log-info'));
      return '<div><span class="log-time">' + escapeHtml(item.time) + '</span><span class="' + className + '"><span data-icon="' + icon + '"></span></span><b>' + escapeHtml(item.title) + '</b><em>' + escapeHtml(item.detail) + '</em></div>';
    }).join('');
  }
  function appendProcessingLogFromState(state, eventType){
    if (!state || !eventType || eventType === 'state') {
      renderProcessingLog();
      return;
    }
    var status = state.status || {};
    var inputs = state.inputs || {};
    var progress = Math.max(0, Math.min(100, Number(status.progress || 0)));
    var message = status.message || status.current_step || '';
    var key = [eventType, status.current_step, status.message, progress, status.processed, status.warnings, status.errors].join('|');
    if (eventType === 'finished' || status.finished) {
      pushProcessingLog(
        Number(status.errors || 0) > 0 ? 'warning' : 'ok',
        'Prüfung abgeschlossen',
        (status.processed || status.employees_total || 0) + ' verarbeitet · ' + (status.warnings || 0) + ' Warnungen · ' + (status.errors || 0) + ' Fehler',
        key
      );
      return;
    }
    if (eventType === 'error' || status.failed) {
      pushProcessingLog('error', 'Prüfung fehlgeschlagen', message || 'Der letzte Prüflauf wurde mit Fehler beendet.', key);
      return;
    }
    if (eventType === 'progress') {
      pushProcessingLog(
        status.running ? 'info' : 'ok',
        status.current_step || (progress ? 'Prüfung läuft' : 'Eingaben geprüft'),
        message || (progress + '% abgeschlossen'),
        key
      );
      return;
    }
    if (eventType === 'input') {
      pushProcessingLog('info', 'Eingaben aktualisiert', ((inputs.pdf && inputs.pdf.label) || 'PDF') + ' · ' + ((inputs.excel && inputs.excel.label) || 'Excel'), key);
    }
  }
  function severityConfig(severity){
    if (severity === 'critical') return { icon: 'x', color: 'red', label: 'Kritischer Fehler' };
    if (severity === 'warning') return { icon: 'warning', color: 'orange', label: 'Warnung' };
    if (severity === 'info') return { icon: 'info', color: 'blue', label: 'Hinweis' };
    return { icon: 'checkcircle', color: 'green', label: 'OK' };
  }
  function applyValidationDetail(row){
    var config = severityConfig(row && row.severity);
    setText('[data-validation="detail-severity"]', config.label);
    setText('[data-validation="detail-title"]', row ? row.description : 'Keine Auffälligkeiten');
    setText('[data-validation="detail-description"]', row ? row.description : 'Die letzte Prüfung enthält keine offenen Einträge.');
    setText('[data-validation="detail-employee"]', row ? row.employee + ' (' + row.persnr + ')' : '-');
    setText('[data-validation="detail-category"]', row ? row.category : '-');
    setText('[data-validation="detail-document"]', row ? row.document : '-');
    setText('[data-validation="detail-position"]', row ? row.position : '-');
    setText('[data-validation="detail-email"]', row && row.email ? row.email : '-');
    setText('[data-validation="detail-status"]', row ? row.status : '-');
  }
  function renderValidationRows(rows){
    var tbody = document.querySelector('[data-validation="table-body"]');
    if (!tbody) return;
    if (!rows || !rows.length) {
      tbody.innerHTML = '<tr><td colspan="9">Keine Einträge für diesen Filter.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(function(row, index){
      if (row.__group) {
        return '<tr class="validation-group-row"><td colspan="9">' + escapeHtml(row.label) + '</td></tr>';
      }
      var config = severityConfig(row.severity);
      return '<tr data-validation-row="' + index + '" class="' + (index === 0 ? 'selected ' : '') + escapeHtml(row.severity) + '-row">' +
        '<td><input type="checkbox"></td>' +
        '<td><span class="type-dot ' + config.color + '"><span data-icon="' + config.icon + '"></span></span></td>' +
        '<td>' + escapeHtml(row.employee) + '</td>' +
        '<td>' + escapeHtml(row.persnr) + '</td>' +
        '<td>' + escapeHtml(row.category) + '</td>' +
        '<td>' + escapeHtml(row.description) + '</td>' +
        '<td>' + escapeHtml(row.email || '-') + '</td>' +
        '<td>' + escapeHtml(row.document) + '</td>' +
        '<td>' + escapeHtml(row.position || '-') + '</td>' +
      '</tr>';
    }).join('');
    tbody.querySelectorAll('[data-validation-row]').forEach(function(tr){
      tr.addEventListener('click', function(){
        tbody.querySelectorAll('tr').forEach(function(row){ row.classList.remove('selected'); });
        tr.classList.add('selected');
        var row = rows[Number(tr.getAttribute('data-validation-row'))];
        if (!row || row.__group) return;
        applyValidationDetail(row);
      });
    });
  }
  function filteredValidationRows(){
    var rows = (latestValidationState && latestValidationState.rows) || [];
    if (currentValidationFilter !== 'all') {
      rows = rows.filter(function(row){ return row.severity === currentValidationFilter; });
    }
    if (validationIssuesOnly) {
      rows = rows.filter(function(row){ return row.severity !== 'success'; });
    }
    if (validationSearchQuery) {
      var query = validationSearchQuery.toLowerCase();
      rows = rows.filter(function(row){
        return [row.employee, row.persnr, row.category, row.description, row.email, row.document, row.status]
          .join(' ')
          .toLowerCase()
          .indexOf(query) !== -1;
      });
    }
    return rows;
  }
  function groupedValidationRows(rows){
    if (!validationGroupMode || !rows.length) return rows;
    var grouped = {};
    rows.forEach(function(row){
      var key = row.category || 'Ohne Kategorie';
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(row);
    });
    return Object.keys(grouped).sort().reduce(function(result, key){
      result.push({ __group: true, label: key + ' (' + grouped[key].length + ')' });
      return result.concat(grouped[key]);
    }, []);
  }
  function applyValidationFilter(filter){
    var nextFilter = filter || 'all';
    if (nextFilter !== currentValidationFilter) currentValidationPage = 1;
    currentValidationFilter = nextFilter;
    document.querySelectorAll('[data-validation-filter]').forEach(function(button){
      button.classList.toggle('active', button.getAttribute('data-validation-filter') === currentValidationFilter);
    });
    var rows = filteredValidationRows();
    var displayRows = groupedValidationRows(rows);
    var totalPages = Math.max(1, Math.ceil(displayRows.length / validationPageSize));
    currentValidationPage = Math.max(1, Math.min(currentValidationPage, totalPages));
    var start = displayRows.length ? (currentValidationPage - 1) * validationPageSize : 0;
    var end = Math.min(start + validationPageSize, displayRows.length);
    var pageRows = displayRows.slice(start, end);
    setText('[data-validation="table-footer"]', rows.length ? 'Zeige ' + (start + 1) + ' bis ' + end + ' von ' + displayRows.length + ' Zeilen (' + rows.length + ' Einträge)' : 'Zeige 0 Einträge');
    setText('[data-validation="page-current"]', String(currentValidationPage));
    var prev = document.querySelector('[data-validation-page="prev"]');
    var next = document.querySelector('[data-validation-page="next"]');
    if (prev) prev.disabled = currentValidationPage <= 1;
    if (next) next.disabled = currentValidationPage >= totalPages;
    renderValidationRows(pageRows);
    applyValidationDetail(rows[0] || null);
    setText('[data-validation="issues-filter-label"]', validationIssuesOnly ? 'Filter: Probleme' : 'Filter');
    var issuesButton = document.querySelector('[data-validation-action="toggle-issues"]');
    if (issuesButton) issuesButton.classList.toggle('active', validationIssuesOnly);
    var groupButton = document.querySelector('[data-validation-action="toggle-group"]');
    if (groupButton) {
      groupButton.textContent = validationGroupMode ? 'Gruppieren: Kategorie' : 'Gruppieren: Aus';
      groupButton.classList.toggle('active', validationGroupMode);
    }
  }
  function exportValidationCsv(){
    var rows = filteredValidationRows();
    var headers = ['Mitarbeiter', 'Personalnr.', 'Kategorie', 'Beschreibung', 'E-Mail', 'Dokument', 'Status'];
    var csvRows = [headers].concat(rows.map(function(row){
      return [row.employee, row.persnr, row.category, row.description, row.email || '', row.document, row.status];
    }));
    var csv = csvRows.map(function(row){
      return row.map(function(cell){
        return '"' + String(cell === undefined || cell === null ? '' : cell).replace(/"/g, '""') + '"';
      }).join(';');
    }).join('\n');
    var filename = 'lohnmail_pruefung_' + new Date().toISOString().slice(0, 10) + '.csv';
    if (window.lohnmailBridge && window.lohnmailBridge.exportValidationCsv) {
      window.lohnmailBridge.exportValidationCsv(csv, filename, function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          setText('[data-validation="table-footer"]', result.ok ? 'Export gespeichert: ' + result.path : 'Export fehlgeschlagen');
        } catch (error) {
          setText('[data-validation="table-footer"]', 'Export fehlgeschlagen');
        }
      });
      return;
    }
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }
  function validationShippingSummary(state){
    var rows = (state && state.rows) || [];
    var ready = rows.filter(function(row){ return row.status === 'OK' || row.severity === 'success'; }).length;
    var missingEmail = rows.filter(function(row){ return row.status === 'Keine E-Mail'; }).length;
    var errors = rows.filter(function(row){ return row.severity === 'critical' || row.status === 'Fehler' || row.status === 'Keine Dateien'; }).length;
    return { ready: ready, missingEmail: missingEmail, errors: errors };
  }
  function updateValidationShippingStatus(state){
    var summary = validationShippingSummary(state);
    setText('[data-validation="shipping-status"]', summary.ready + ' versandbereit · ' + summary.missingEmail + ' ohne E-Mail · ' + summary.errors + ' Fehler');
    var button = document.querySelector('[data-validation-action="go-shipping"]');
    if (button) {
      button.disabled = !(state && state.ready);
      button.title = state && state.ready ? 'Versand öffnen' : 'Prüfung zuerst ausführen';
    }
  }
  function goToShippingFromValidation(){
    updateValidationShippingStatus(latestValidationState);
    setPage('Versand');
    loadShippingState();
  }
  function applyValidationState(state){
    latestValidationState = state || null;
    var summary = (state && state.summary) || {};
    var filters = (state && state.filters) || {};
    var total = Number(summary.total || 0);
    var checked = Number(summary.checked || 0);
    var percent = total ? Math.round((checked / total) * 100) : 0;

    setText('[data-validation="critical-count"]', summary.critical || 0);
    setText('[data-validation="warning-count"]', summary.warnings || 0);
    setText('[data-validation="info-count"]', summary.info || 0);
    setText('[data-validation="checked-count"]', checked);
    setText('[data-validation="checked-label"]', 'Von ' + total + ' (' + percent + '%)');
    setText('[data-validation="status"]', summary.status || 'Nicht gestartet');
    setText('[data-validation="updated"]', summary.updated || '--');
    setText('[data-validation="filter-all"]', 'Alle (' + (filters.all || 0) + ')');
    setText('[data-validation="filter-critical"]', 'Kritisch (' + (filters.critical || 0) + ')');
    setText('[data-validation="filter-warning"]', 'Warnungen (' + (filters.warnings || 0) + ')');
    setText('[data-validation="filter-info"]', 'Hinweise (' + (filters.info || 0) + ')');
    updateValidationReportActions((state && state.reports) || {});
    updateValidationShippingStatus(state);
    applyValidationFilter(currentValidationFilter);
    updateCompactWorkflowTrackers('Prüfung');
    updateDashboardPipeline();
    updateWarningCenter();
    updateReportsScreen();
  }
  function loadValidationState(){
    if (!window.lohnmailBridge || !window.lohnmailBridge.getValidationState) return;
    window.lohnmailBridge.getValidationState(function(payload){
      try {
        applyValidationState(JSON.parse(payload || '{}'));
      } catch (error) {
        console.warn('Prüfung state konnte nicht geladen werden', error);
      }
    });
  }
  function shippingRows(){
    var rows = (latestShippingState && latestShippingState.rows) || [];
    if (shippingStatusFilter === 'all') {
      if (shippingViewFilter === 'queue') {
        rows = rows.filter(function(row){ return row.status !== 'Gesendet' && row.status !== 'Fehler'; });
      }
      if (shippingViewFilter === 'sent') {
        rows = rows.filter(function(row){ return row.status === 'Gesendet'; });
      }
      if (shippingViewFilter === 'error') {
        rows = rows.filter(function(row){ return row.status === 'Fehler'; });
      }
      if (shippingViewFilter === 'drafts') {
        rows = [];
      }
    }
    if (shippingStatusFilter === 'ready') {
      rows = rows.filter(function(row){ return row.status === 'Bereit' || row.status === 'Dry-Run'; });
    }
    if (shippingStatusFilter === 'missing-email') {
      rows = rows.filter(function(row){ return row.status === 'Keine E-Mail'; });
    }
    if (shippingStatusFilter === 'error') {
      rows = rows.filter(function(row){ return row.status === 'Fehler' || row.status === 'Keine Dateien'; });
    }
    if (shippingStatusFilter === 'sent') {
      rows = rows.filter(function(row){ return row.status === 'Gesendet'; });
    }
    if (!shippingSearchQuery) return rows;
    var query = shippingSearchQuery.toLowerCase();
    return rows.filter(function(row){
      return [row.employee, row.persnr, row.email, row.document, row.status, row.error]
        .join(' ')
        .toLowerCase()
        .indexOf(query) !== -1;
    });
  }
  function shippingStatusClass(status){
    if (status === 'Gesendet' || status === 'Dry-Run' || status === 'Bereit') return 'ready';
    if (status === 'Fehler') return 'failed';
    if (status === 'Keine E-Mail' || status === 'Keine Dateien') return 'warning';
    return 'ready';
  }
  function shippingRowSelectable(row){
    var status = row && row.status;
    return !!(row && row.persnr && row.email && (status === 'Bereit' || status === 'Dry-Run'));
  }
  function syncShippingSelectionDefaults(){
    var rows = (latestShippingState && latestShippingState.rows) || [];
    var known = {};
    rows.forEach(function(row){
      var persnr = String(row.persnr || '');
      if (!persnr) return;
      known[persnr] = true;
      if (shippingRowSelectable(row) && selectedShippingPersnr[persnr] === undefined) {
        selectedShippingPersnr[persnr] = true;
      }
      if (!shippingRowSelectable(row)) {
        selectedShippingPersnr[persnr] = false;
      }
    });
    Object.keys(selectedShippingPersnr).forEach(function(persnr){
      if (!known[persnr]) delete selectedShippingPersnr[persnr];
    });
  }
  function selectedShippingList(){
    var rows = (latestShippingState && latestShippingState.rows) || [];
    return rows
      .filter(function(row){ return shippingRowSelectable(row) && selectedShippingPersnr[String(row.persnr || '')] !== false; })
      .map(function(row){ return String(row.persnr || ''); });
  }
  function updateShippingSelectionSummary(){
    var selected = selectedShippingList().length;
    var selectable = ((latestShippingState && latestShippingState.rows) || []).filter(shippingRowSelectable).length;
    var status = (latestShippingState && latestShippingState.status) || {};
    var metrics = (latestShippingState && latestShippingState.metrics) || {};
    var prepared = Number(metrics.exported || 0);
    var baseDisabled = !!status.running || !status.can_send || !status.finished || prepared < 1 || Number(metrics.ready || 0) <= Number(metrics.sent || 0);
    var title = selected + ' von ' + selectable + ' sendbaren Einträgen ausgewählt';
    setText('[data-shipping="actionbar-title"]', title);
    document.querySelectorAll('[data-shipping-action="send-now"]').forEach(function(button){
      button.disabled = baseDisabled || selected < 1;
      button.classList.toggle('soft-disabled', button.disabled);
      if (selected < 1) button.title = 'Bitte mindestens einen sendbaren Mitarbeiter auswählen';
      else if (!button.disabled) button.title = 'E-Mails an ausgewählte Mitarbeiter senden';
    });
  }
  function shippingFilterCounts(){
    var rows = (latestShippingState && latestShippingState.rows) || [];
    return {
      all: rows.length,
      ready: rows.filter(function(row){ return row.status === 'Bereit' || row.status === 'Dry-Run'; }).length,
      'missing-email': rows.filter(function(row){ return row.status === 'Keine E-Mail'; }).length,
      error: rows.filter(function(row){ return row.status === 'Fehler' || row.status === 'Keine Dateien'; }).length,
      sent: rows.filter(function(row){ return row.status === 'Gesendet'; }).length
    };
  }
  function updateShippingFilterControls(){
    var counts = shippingFilterCounts();
    Object.keys(counts).forEach(function(key){
      setText('[data-shipping-filter-count="' + key + '"]', String(counts[key]));
    });
    document.querySelectorAll('[data-shipping-filter]').forEach(function(button){
      button.classList.toggle('active', button.getAttribute('data-shipping-filter') === shippingStatusFilter);
    });
  }
  function updateShippingPagination(page, totalPages){
    document.querySelectorAll('[data-shipping-action="page-prev"]').forEach(function(button){
      button.disabled = page <= 1;
    });
    document.querySelectorAll('[data-shipping-action="page-next"]').forEach(function(button){
      button.disabled = page >= totalPages;
    });
  }
  function updateShippingSelectionMaster(rows){
    var master = document.querySelector('[data-shipping="select-visible"]');
    if (!master) return;
    rows = rows || shippingRows();
    var selectableRows = rows.filter(shippingRowSelectable);
    var selectedCount = selectableRows.filter(function(row){
      return selectedShippingPersnr[String(row.persnr || '')] !== false;
    }).length;
    master.disabled = !selectableRows.length;
    master.checked = !!selectableRows.length && selectedCount === selectableRows.length;
    master.indeterminate = selectedCount > 0 && selectedCount < selectableRows.length;
  }
  function setShippingDetailText(key, value){
    setText('[data-shipping-detail="' + key + '"]', value);
  }
  function applyShippingDetail(row){
    row = row || {};
    var status = row.status || 'Bereit';
    var employee = row.employee || 'Keine Auswahl';
    var persnr = row.persnr || '-';
    var email = row.email || '-';
    var documentName = row.document || '-';
    var error = row.error || (status === 'Keine E-Mail' ? 'E-Mail-Adresse fehlt.' : '-');
    var statusNode = document.querySelector('[data-shipping-detail="status"]');
    if (statusNode) {
      statusNode.className = 'state ' + shippingStatusClass(status);
      statusNode.textContent = status;
    }
    setShippingDetailText('initials', row.initials || 'MA');
    setShippingDetailText('employee', employee);
    setShippingDetailText('persnr', 'Personalnummer: ' + persnr);
    setShippingDetailText('email', email);
    setShippingDetailText('document', documentName);
    setShippingDetailText('size', row.size || '-');
    setShippingDetailText('planned', row.planned || 'Dry-Run');
    setShippingDetailText('status-text', status);
    setShippingDetailText('error', error);
    setShippingDetailText('preview-title', documentName === '-' ? 'PDF-Vorschau' : documentName);
    setShippingDetailText('preview-status', row.planned || 'Dry-Run');
    setShippingDetailText('preview-employee', employee);
    setShippingDetailText('preview-persnr', 'Personalnummer: ' + persnr);
    setShippingDetailText('preview-document', documentName);
    setShippingDetailText('preview-email', email);
    setShippingDetailText('preview-row-status', status);
    setShippingDetailText('preview-mode', row.planned || 'Dry-Run');
    setShippingDetailText('preview-error', error);
  }
  function renderShippingRows(){
    var tbody = document.querySelector('[data-shipping="table-body"]');
    if (!tbody) return;
    var rows = shippingRows();
    var totalPages = Math.max(1, Math.ceil(rows.length / shippingPageSize));
    currentShippingPage = Math.max(1, Math.min(currentShippingPage, totalPages));
    var start = (currentShippingPage - 1) * shippingPageSize;
    var visibleRows = rows.slice(start, start + shippingPageSize);
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="8">Keine Versanddaten vorhanden. Erst Prüfung ausführen oder Versand vorbereiten.</td></tr>';
      setText('[data-shipping="table-footer"]', 'Zeige 0 Einträge');
      setText('[data-shipping="page-current"]', '1');
      updateShippingPagination(0, 1);
      updateShippingSelectionMaster(rows);
      applyShippingDetail(null);
      return;
    }
    tbody.innerHTML = visibleRows.map(function(row, index){
      var selectable = shippingRowSelectable(row);
      var persnr = String(row.persnr || '');
      var checked = selectable && selectedShippingPersnr[persnr] !== false;
      return '<tr data-shipping-row="' + index + '" class="' + (index === 0 ? 'selected' : '') + '">' +
        '<td><input type="checkbox" data-shipping-select="' + escapeHtml(persnr) + '"' + (checked ? ' checked' : '') + (selectable ? '' : ' disabled') + '></td>' +
        '<td><span class="avatar-mini">' + escapeHtml(row.initials || 'MA') + '</span><b>' + escapeHtml(row.employee || '-') + '<small>' + escapeHtml(row.persnr || '-') + '</small></b></td>' +
        '<td>' + escapeHtml(row.email || '-') + '</td>' +
        '<td><span class="file-dot pdf"><span data-icon="doc"></span></span>' + escapeHtml(row.document || '-') + '</td>' +
        '<td>' + escapeHtml(row.size || '-') + '</td>' +
        '<td><span class="state ' + shippingStatusClass(row.status) + '">' + escapeHtml(row.status || 'Bereit') + '</span></td>' +
        '<td>' + escapeHtml(row.planned || 'Dry-Run') + '</td>' +
        '<td>' + escapeHtml(row.error ? 'Fehler' : '') + '</td>' +
      '</tr>';
    }).join('');
    tbody.querySelectorAll('[data-shipping-select]').forEach(function(input){
      input.addEventListener('change', function(event){
        var persnr = input.getAttribute('data-shipping-select') || '';
        if (persnr) selectedShippingPersnr[persnr] = !!input.checked;
        updateShippingSelectionSummary();
        event.stopPropagation();
      });
    });
    tbody.querySelectorAll('[data-shipping-row]').forEach(function(tr){
      tr.addEventListener('click', function(event){
        if (event.target && event.target.matches && event.target.matches('input[type="checkbox"]')) return;
        tbody.querySelectorAll('tr').forEach(function(rowNode){ rowNode.classList.remove('selected'); });
        tr.classList.add('selected');
        applyShippingDetail(visibleRows[Number(tr.getAttribute('data-shipping-row'))]);
      });
    });
    applyShippingDetail(visibleRows[0] || null);
    var end = start + visibleRows.length;
    setText('[data-shipping="table-footer"]', 'Zeige ' + (start + 1) + ' bis ' + end + ' von ' + rows.length + ' Einträgen');
    setText('[data-shipping="page-current"]', String(currentShippingPage));
    updateShippingPagination(currentShippingPage, totalPages);
    updateShippingSelectionMaster(rows);
    updateShippingSelectionSummary();
  }
  function applyShippingState(state){
    latestShippingState = state || null;
    syncShippingSelectionDefaults();
    var metrics = (state && state.metrics) || {};
    var status = (state && state.status) || {};
    var total = Number(metrics.total || 0);
    var ready = Number(metrics.ready || 0);
    var sent = Number(metrics.sent || 0);
    var queued = Number(metrics.queued || 0);
    var errors = Number(metrics.errors || 0);
    var exported = Number(metrics.exported || 0);
    var readyPercent = total ? Math.round((ready / total) * 100) : 0;
    var sentPercent = total ? Math.round((sent / total) * 100) : 0;
    var queuedPercent = total ? Math.round((queued / total) * 100) : 0;

    setText('[data-shipping="ready-count"]', ready);
    setText('[data-shipping="ready-label"]', total ? readyPercent + '% der Versanddaten' : 'Aus geprüften Daten');
    setText('[data-shipping="sent-count"]', sent);
    setText('[data-shipping="sent-label"]', sentPercent + '%');
    setText('[data-shipping="queued-count"]', queued);
    setText('[data-shipping="queued-label"]', queuedPercent + '%');
    setText('[data-shipping="error-count"]', errors);
    setText('[data-shipping="error-label"]', errors ? 'Bitte prüfen' : 'Keine Fehler');
    setText('[data-shipping="exported-count"]', exported);
    setText('[data-shipping="queue-tab"]', 'Warteschlange (' + queued + ')');
    setText('[data-shipping="sent-tab"]', 'Gesendet (' + sent + ')');
    setText('[data-shipping="error-tab"]', 'Fehler (' + errors + ')');
    setText('[data-shipping="actionbar-title"]', total + ' Einträge in Versandliste');
    setText('[data-shipping="actionbar-subtitle"]', status.message || 'Dry-Run vorbereitet Anhänge und Bericht.');
    updateShippingFilterControls();

    var readyTrack = document.querySelector('[data-shipping="ready-track"]');
    var sentTrack = document.querySelector('[data-shipping="sent-track"]');
    var queuedTrack = document.querySelector('[data-shipping="queued-track"]');
    if (readyTrack) readyTrack.style.width = readyPercent + '%';
    if (sentTrack) sentTrack.style.width = sentPercent + '%';
    if (queuedTrack) queuedTrack.style.width = queuedPercent + '%';

    document.querySelectorAll('[data-shipping-action="start-dry-run"]').forEach(function(button){
      button.disabled = !!status.running;
      button.classList.toggle('soft-disabled', !status.can_send && !status.running);
      button.title = status.running ? 'Versand-Dry-Run läuft' : (status.can_send ? 'Versand vorbereiten' : 'PDF- und Excel-Pfade prüfen');
    });
    document.querySelectorAll('[data-shipping-action="send-now"]').forEach(function(button){
      var prepared = Number(metrics.exported || 0);
      var sendable = !!status.finished && prepared > 0 && Number(metrics.ready || 0) > Number(metrics.sent || 0);
      button.disabled = !!status.running || !status.can_send || !sendable;
      button.classList.toggle('soft-disabled', button.disabled);
      button.title = status.running ? 'Versand läuft' : (sendable ? 'E-Mails jetzt wirklich senden' : 'Erst Versand vorbereiten, dann senden');
    });
    document.querySelectorAll('[data-shipping="start-label"], [data-shipping="actionbar-label"]').forEach(function(label){
      label.textContent = status.running ? (status.dry_run === false ? 'Versand läuft' : 'Dry-Run läuft') : (status.finished ? 'Erneut vorbereiten' : 'Versand vorbereiten');
    });
    document.querySelectorAll('[data-shipping="send-label"]').forEach(function(label){
      label.textContent = status.running ? 'Versand läuft' : 'Jetzt senden';
    });
    document.querySelectorAll('.mailing-tabs [data-shipping-action]').forEach(function(button){
      var action = button.getAttribute('data-shipping-action');
      var active = (
        (action === 'tab-queue' && shippingViewFilter === 'queue') ||
        (action === 'tab-sent' && shippingViewFilter === 'sent') ||
        (action === 'tab-error' && shippingViewFilter === 'error') ||
        (action === 'tab-drafts' && shippingViewFilter === 'drafts')
      );
      button.classList.toggle('active', active);
    });
    renderShippingRows();
    updateCompactWorkflowTrackers('Versand');
    updateDashboardPipeline();
    updateWarningCenter();
    updateReportsScreen();
  }
  function consumeShippingPayload(payload){
    try {
      var state = JSON.parse(payload || '{}');
      applyShippingState(state);
      return state;
    } catch (error) {
      console.warn('Versand state konnte nicht verarbeitet werden', error);
    }
    return null;
  }
  function loadShippingState(){
    if (!window.lohnmailBridge || !window.lohnmailBridge.getShippingState) return;
    window.lohnmailBridge.getShippingState(function(payload){
      consumeShippingPayload(payload);
    });
  }
  function loadReportsState(){
    loadDashboardState();
    loadValidationState();
    loadShippingState();
    updateReportsScreen();
  }
  function startShippingDryRun(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.startShippingDryRun) {
      setText('[data-shipping="actionbar-subtitle"]', 'Bridge ist noch nicht bereit.');
      return;
    }
    bridge.startShippingDryRun(function(payload){
      consumeShippingPayload(payload);
    });
  }
  function setShippingPreviewText(key, value){
    var node = document.querySelector('[data-shipping-preview="' + key + '"]');
    if (!node) return;
    if ('value' in node) node.value = value || '';
    else node.textContent = value || '';
  }
  function closeShippingSendModal(){
    var modal = document.querySelector('[data-shipping-send-modal]');
    if (modal) modal.hidden = true;
  }
  function renderShippingSendPreview(preview){
    latestShippingSendPreview = preview || null;
    preview = preview || {};
    setShippingPreviewText('total', String(preview.total_count || 0));
    setShippingPreviewText('mode', preview.mail_mode || 'smtp');
    setShippingPreviewText('from', preview.from_email || preview.from_name || '-');
    setShippingPreviewText('subject', preview.subject_preview || '');
    setShippingPreviewText('body', preview.body_preview || '');
    setShippingPreviewText('message', '');

    var summary = document.querySelector('[data-shipping-preview="summary"]');
    if (summary) {
      var lines = preview.summary_lines || [];
      summary.innerHTML = lines.length
        ? lines.map(function(line){ return '<span>' + escapeHtml(line) + '</span>'; }).join('')
        : '<span>Keine Zusammenfassung verfügbar.</span>';
    }

    var tbody = document.querySelector('[data-shipping-preview="rows"]');
    if (tbody) {
      var rows = preview.rows || [];
      if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="5">Keine sendbaren Empfänger.</td></tr>';
      } else {
        tbody.innerHTML = rows.map(function(row){
          var name = [row.Name, row.Vorname].filter(Boolean).join(', ') || '-';
          return '<tr>' +
            '<td>' + escapeHtml(row.PersNr || '-') + '</td>' +
            '<td>' + escapeHtml(name) + '</td>' +
            '<td>' + escapeHtml(row.Email || '-') + '</td>' +
            '<td>' + escapeHtml(row.AttachmentPreview || '-') + '</td>' +
            '<td>' + escapeHtml(row.Files || '-') + '</td>' +
            '</tr>';
        }).join('');
      }
    }

    var modal = document.querySelector('[data-shipping-send-modal]');
    if (modal) modal.hidden = false;
  }
  function openShippingSendPreview(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.previewSelectedShippingSend) {
      setShippingMessage('Versand-Vorschau ist im Bridge noch nicht verfügbar.');
      return;
    }
    var selected = selectedShippingList();
    if (!selected.length) {
      setShippingMessage('Bitte mindestens einen sendbaren Mitarbeiter auswählen.');
      return;
    }
    setShippingMessage('Versand-Vorschau wird geladen...');
    bridge.previewSelectedShippingSend(JSON.stringify(selected), function(payload){
      var preview = null;
      try {
        preview = JSON.parse(payload || '{}');
      } catch (error) {
        console.warn('Versand-Vorschau konnte nicht verarbeitet werden', error);
      }
      if (!preview || preview.ok === false) {
        setShippingMessage((preview && preview.message) || 'Versand-Vorschau konnte nicht geladen werden.');
        return;
      }
      renderShippingSendPreview(preview);
      setShippingMessage(preview.message || 'Versand-Vorschau ist bereit.');
    });
  }
  function startShippingSend(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.startSelectedShippingSend) {
      setShippingPreviewText('message', 'Echter Versand ist im Bridge noch nicht verfügbar.');
      return;
    }
    var selected = selectedShippingList();
    if (!selected.length) {
      setShippingPreviewText('message', 'Bitte mindestens einen sendbaren Mitarbeiter auswählen.');
      return;
    }
    var confirmButton = document.querySelector('[data-shipping-send-action="confirm"]');
    if (confirmButton) confirmButton.disabled = true;
    setShippingMessage('E-Mail Versand wird gestartet...');
    setShippingPreviewText('message', 'E-Mail Versand wird gestartet...');
    bridge.startSelectedShippingSend(JSON.stringify(selected), function(payload){
      if (confirmButton) confirmButton.disabled = false;
      closeShippingSendModal();
      consumeShippingPayload(payload);
      loadDashboardState();
      loadReportsState();
    });
  }
  function setShippingMessage(message){
    setText('[data-shipping="actionbar-subtitle"]', message);
  }
  function runShippingAction(action){
    if (action === 'start-dry-run') {
      startShippingDryRun();
      return;
    }
    if (action === 'send-now') {
      openShippingSendPreview();
      return;
    }
    if (action === 'select-all') {
      document.querySelectorAll('[data-shipping="table-body"] input[type="checkbox"]').forEach(function(input){
        input.checked = true;
      });
      setShippingMessage('Alle sichtbaren Einträge wurden markiert.');
      return;
    }
    if (action === 'tab-queue' || action === 'tab-sent' || action === 'tab-error' || action === 'tab-drafts') {
      shippingViewFilter = action.replace('tab-', '');
      shippingStatusFilter = 'all';
      currentShippingPage = 1;
      updateShippingFilterControls();
      renderShippingRows();
      document.querySelectorAll('.mailing-tabs [data-shipping-action]').forEach(function(button){
        button.classList.toggle('active', button.getAttribute('data-shipping-action') === action);
      });
      setShippingMessage('Ansicht gewechselt: ' + (shippingViewFilter === 'queue' ? 'Warteschlange' : shippingViewFilter) + '.');
      return;
    }
    if (action === 'bulk-action') {
      setShippingMessage('Sammelaktionen werden im nächsten Schritt mit echtem Versand verbunden.');
      return;
    }
    if (action === 'test-send') {
      setShippingMessage('Testversand ist noch nicht aktiviert. Aktuell läuft nur sicherer Dry-Run.');
      return;
    }
    if (action === 'preview') {
      setShippingMessage('Vorschau zeigt den aktuell markierten Eintrag.');
      return;
    }
    if (action === 'export-report') {
      var bridge = window.lohnmailBridge;
      if (!bridge || !bridge.openReport) {
        setShippingMessage('Bericht öffnen ist im Bridge nicht verfügbar.');
        return;
      }
      bridge.openReport('send', function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          setShippingMessage(result.ok ? 'Versandbericht wurde geöffnet.' : (result.message || 'Versandbericht wurde noch nicht erstellt.'));
        } catch (error) {
          setShippingMessage('Versandbericht konnte nicht geöffnet werden.');
        }
      });
      return;
    }
    if (action === 'schedule-queue') {
      setShippingMessage('Planung ist noch nicht aktiviert. Aktuell kann der Versand als Dry-Run vorbereitet werden.');
      return;
    }
    if (action === 'page-prev') {
      currentShippingPage = Math.max(1, currentShippingPage - 1);
      renderShippingRows();
      return;
    }
    if (action === 'page-next') {
      currentShippingPage += 1;
      renderShippingRows();
      return;
    }
    if (action === 'preview-pdf' || action === 'preview-mail') {
      document.querySelectorAll('.preview-switch button').forEach(function(button){
        button.classList.toggle('active', button.getAttribute('data-shipping-action') === action);
      });
      setShippingMessage(action === 'preview-pdf' ? 'PDF-Vorschau ausgewählt.' : 'E-Mail-Vorschau wird im nächsten Schritt mit Templates verbunden.');
      return;
    }
    if (action === 'preview-zoom-in' || action === 'preview-zoom-out') {
      shippingPreviewZoom += action === 'preview-zoom-in' ? 10 : -10;
      shippingPreviewZoom = Math.max(70, Math.min(140, shippingPreviewZoom));
      setText('[data-shipping="preview-zoom"]', shippingPreviewZoom + '%');
      setShippingMessage('Vorschau-Zoom: ' + shippingPreviewZoom + '%.');
      return;
    }
    if (action === 'preview-top') {
      var previewScroll = document.querySelector('.mailing-preview-scroll');
      if (previewScroll) previewScroll.scrollTop = 0;
      setShippingMessage('Vorschau nach oben gescrollt.');
      return;
    }
    if (action === 'preview-close') {
      setShippingMessage('Detailansicht bleibt sichtbar, damit die Versanddaten prüfbar bleiben.');
      return;
    }
  }
  function setProcessingText(key, value){
    setText('[data-processing="' + key + '"]', value);
  }
  function setProcessingRow(kind, state){
    var row = document.querySelector('[data-processing-row="' + kind + '"]');
    if (!row || !state) return;
    var valid = !!state.valid;
    var exists = !!state.exists;
    row.classList.toggle('ok', valid);
    row.classList.toggle('pending', !valid && !exists);
    row.classList.toggle('error', !valid && exists);

    var status = document.querySelector('[data-processing="' + kind + '-status"]');
    if (status) {
      status.className = 'row-status ' + (valid ? 'success' : (exists ? 'error' : 'neutral'));
      status.textContent = '';
      if (valid) {
        var icon = document.createElement('span');
        icon.setAttribute('data-icon', 'checkcircle');
        status.appendChild(icon);
      } else if (exists) {
        var errorIcon = document.createElement('span');
        errorIcon.setAttribute('data-icon', 'x');
        status.appendChild(errorIcon);
      } else {
        status.textContent = '-';
      }
    }

    setProcessingText(kind + '-path', state.path || 'Nicht ausgewählt');
    setProcessingText(kind + '-label', state.label || 'Nicht ausgewählt');
    setProcessingText(kind + '-updated', state.updated || '--');
  }
  function setWorkflowState(selector, state, label){
    var step = document.querySelector(selector);
    if (!step) return;
    step.classList.remove('done', 'active', 'muted');
    step.classList.add(state);
    var small = step.querySelector('small');
    if (small) small.textContent = label;
  }
  function setInfoBanner(message, ready){
    var banner = document.querySelector('[data-processing="input-message"]');
    if (!banner) return;
    var icon = banner.querySelector('[data-icon]');
    banner.textContent = ' ' + (message || '');
    if (icon) banner.prepend(icon);
    banner.classList.toggle('ready', !!ready);
    banner.classList.toggle('warning', !ready);
  }
  function applyProcessingState(state){
    if (!state) return;
    var inputs = state.inputs || {};
    var status = state.status || {};
    setProcessingRow('pdf', inputs.pdf || {});
    setProcessingRow('excel', inputs.excel || {});
    setProcessingRow('output', inputs.output || {});

    var modeLabel = state.mode === 'single_pdf' ? 'Einzel-PDF' : 'Ordner';
    setProcessingText('pdf-mode', modeLabel);
    setProcessingText('pdf-kind', state.mode === 'single_pdf' ? 'Einzelne PDF-Datei' : 'PDF-Ordner / DATEV Export');
    document.querySelectorAll('[data-pdf-mode]').forEach(function(button){
      button.classList.toggle('active', button.getAttribute('data-pdf-mode') === (state.mode || 'folder'));
    });
    setWorkflowState('[data-processing-step="pdf"]', inputs.pdf && inputs.pdf.valid ? 'done' : 'active', inputs.pdf && inputs.pdf.valid ? 'Bereit' : 'Prüfen');
    setWorkflowState('[data-processing-step="excel"]', inputs.excel && inputs.excel.valid ? 'done' : (inputs.pdf && inputs.pdf.valid ? 'active' : 'muted'), inputs.excel && inputs.excel.valid ? 'Bereit' : 'Wartet');
    if (status.running) {
      setWorkflowState('[data-processing-step="validation"]', 'active', 'Läuft');
    } else if (status.finished) {
      setWorkflowState('[data-processing-step="validation"]', 'done', 'Abgeschlossen');
    } else if (status.failed) {
      setWorkflowState('[data-processing-step="validation"]', 'active', 'Fehler');
    }

    var progress = Math.max(0, Math.min(100, Number(status.progress || 0)));
    setProcessingText('current-step', status.current_step || 'Eingaben prüfen');
    setProcessingText('progress-label', progress + '%');
    setProcessingText('employees-total', status.employees_total || 0);
    setProcessingText('processed', status.processed || 0);
    setProcessingText('sent', status.sent || 0);
    setProcessingText('warnings', status.warnings || 0);
    setProcessingText('errors', status.errors || 0);
    setProcessingText('elapsed', status.elapsed || '00:00:00');
    setProcessingText('remaining', status.remaining || '--:--:--');

    var progressBar = document.querySelector('[data-processing="progress-bar"]');
    if (progressBar) progressBar.style.width = progress + '%';
    setInfoBanner(status.message, !!status.can_check);

    var startButton = document.querySelector('[data-processing="start-button"]');
    if (startButton) {
      startButton.disabled = !!status.running;
      startButton.classList.toggle('soft-disabled', !status.can_check && !status.running);
      startButton.title = status.running ? 'Prüfung läuft' : (status.can_check ? 'Eingaben bereit' : 'PDF- und Excel-Pfade prüfen');
      var label = startButton.querySelector('[data-processing="start-label"]');
      if (label) {
        label.textContent = status.finished ? 'Prüfung öffnen' : (status.running ? 'Prüfung läuft' : 'Verarbeitung starten');
      }
    }
    updateDashboardPipeline();
    updateWarningCenter();
  }
  function consumeProcessingPayload(payload, eventType){
    try {
      var state = JSON.parse(payload || '{}');
      latestProcessingState = state;
      appendProcessingLogFromState(state, eventType);
      applyProcessingState(state);
      return state;
    } catch (error) {
      console.warn('Verarbeitung state konnte nicht verarbeitet werden', error);
    }
    return null;
  }
  function loadProcessingState(){
    if (!window.lohnmailBridge || !window.lohnmailBridge.getProcessingState) return;
    window.lohnmailBridge.getProcessingState(function(payload){
      consumeProcessingPayload(payload, 'state');
    });
  }
  function getStartCheckBlocker(){
    var processing = latestProcessingState || {};
    var inputs = processing.inputs || {};
    var companyState = latestCompanyState || {};
    var hasCompanyState = !!latestCompanyState;
    var activeCompany = activeCompanyFromState(companyState);
    var selectedExcel = companyState.selected_excel || (activeCompany && activeCompany.excel) || {};

    if (hasCompanyState && !activeCompany) {
      return {
        page: 'Unternehmen',
        message: 'Bitte zuerst ein Unternehmen auswählen oder erstellen.',
        companyMessage: 'Für den Workflow muss ein aktiver Mandant gewählt sein.'
      };
    }
    if (activeCompany && !selectedExcel.valid) {
      return {
        page: 'Unternehmen',
        message: 'Für den aktiven Mandanten fehlt eine gültige Excel-Datei.',
        companyMessage: 'Bitte dem aktiven Mandanten eine Mitarbeiter-Excel zuordnen.'
      };
    }
    if (!(inputs.pdf && inputs.pdf.valid)) {
      return {
        page: 'Verarbeitung',
        message: 'Bitte zuerst einen gültigen PDF-Eingang auswählen.'
      };
    }
    if (!(inputs.excel && inputs.excel.valid)) {
      return {
        page: 'Unternehmen',
        message: 'Bitte zuerst eine gültige Mitarbeiter-Excel auswählen.',
        companyMessage: 'Die Excel-Datei wird pro Mandant verwaltet. Bitte hier zuordnen.'
      };
    }
    return null;
  }
  function showStartCheckBlocker(blocker){
    if (!blocker) return;
    setPage(blocker.page || 'Verarbeitung');
    if (blocker.companyMessage) setCompanyMessage(blocker.companyMessage);
    setInfoBanner(blocker.message || 'Bitte Eingaben prüfen.', false);
    pushProcessingLog('warning', 'Start blockiert', blocker.message || 'Bitte Eingaben prüfen.', 'blocker|' + (blocker.message || ''));
    updateWarningCenter();
  }
  function runBridgeAction(action){
    var bridge = window.lohnmailBridge;
    if (!bridge) {
      setInfoBanner('Bridge wird noch geladen. Bitte kurz warten.', false);
      return;
    }
    if (action === 'choose-pdf' && bridge.choosePdfInput) {
      bridge.choosePdfInput(function(payload){ consumeProcessingPayload(payload, 'input'); });
      return;
    }
    if (action === 'choose-excel' && bridge.chooseExcelInput) {
      bridge.chooseExcelInput(function(payload){ consumeProcessingPayload(payload, 'input'); });
      return;
    }
    if (action === 'show-log') {
      renderProcessingLog();
      setInfoBanner('Aktivitätsprotokoll zeigt die aktuelle Sitzung.', true);
      return;
    }
    if (action === 'start-check' && bridge.startCheck) {
      if (latestProcessingState && latestProcessingState.status && latestProcessingState.status.finished) {
        setPage('Prüfung');
        return;
      }
      var blocker = getStartCheckBlocker();
      if (blocker) {
        showStartCheckBlocker(blocker);
        return;
      }
      setInfoBanner('Prüfung wird gestartet...', true);
      pushProcessingLog('info', 'Prüfung gestartet', 'PDF und Excel werden validiert.', 'start-check|' + Date.now());
      bridge.startCheck(function(payload){
        consumeProcessingPayload(payload, 'progress');
      });
      return;
    }
    setInfoBanner('Aktion ist im Bridge nicht verfügbar.', false);
  }
  function setPage(page){
    var normalized = page || 'Dashboard';
    document.querySelectorAll('.page').forEach(function(p){
      p.classList.toggle('active', p.dataset.page === normalized);
    });
    document.querySelectorAll('.nav-item').forEach(function(i){
      i.classList.toggle('active', i.textContent.trim() === normalized);
    });
    var breadcrumbStrong = document.querySelector('.page-breadcrumb strong');
    var breadcrumbSub = document.querySelector('.page-breadcrumb span');
    if (breadcrumbStrong) breadcrumbStrong.textContent = normalized;
    if (breadcrumbSub) {
      var subtitles = {
        'Dashboard': 'Übersicht & Systemstatus',
        'Nachricht': 'Freie E-Mail an Mitarbeiter senden',
        'Verarbeitung': 'Daten importieren, prüfen und verarbeiten',
        'Prüfung': 'Validierung und Prüfung Ihrer Lohnunterlagen',
        'Versand': 'Lohnabrechnungen per E-Mail senden oder exportieren',
        'Berichte': 'Übersicht und Analyse Ihrer Verarbeitung und Versandaktivitäten',
        'Unternehmen': 'Mandant und Stammdaten-Konfiguration',
        'Lizenzen': 'Lizenzstatus und Lizenzverwaltung',
        'Einstellungen': 'Konfiguration und lokale Defaults',
        'Hilfe': 'Antworten finden, Probleme lösen und Support erhalten',
        'Über LohnMail': 'Informationen über LohnMail und rechtliche Hinweise'
      };
      breadcrumbSub.textContent = subtitles[normalized] || 'LohnMail v2';
    }
    if (window.lohnmailBridge) window.lohnmailBridge.navigate(normalized);
    if (normalized === 'Dashboard') loadDashboardState();
    if (normalized === 'Nachricht') loadMassMessageState();
    if (normalized === 'Verarbeitung') loadProcessingState();
    if (normalized === 'Prüfung') loadValidationState();
    if (normalized === 'Versand') loadShippingState();
    if (normalized === 'Berichte') loadReportsState();
    if (normalized === 'Unternehmen') loadCompanyState();
    if (normalized === 'Lizenzen') loadLicenseState();
    if (normalized === 'Einstellungen') loadSettingsState();
    if (normalized === 'Hilfe') setInfoBanner('Hilfe und Supportübersicht geöffnet.', true);
    if (normalized === 'Über LohnMail') setInfoBanner('Produktinformationen geöffnet.', true);
    updateCompactWorkflowTrackers(normalized);
  }
  window.addEventListener('DOMContentLoaded', function(){
    initBridge();
    document.addEventListener('click', function(event){
      var control = event.target.closest && event.target.closest('[data-processing-action]');
      if (!control) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      setPage('Verarbeitung');
      runBridgeAction(control.getAttribute('data-processing-action'));
    }, true);
    document.querySelectorAll('.nav-item').forEach(function(item){
      item.addEventListener('click', function(){ setPage(item.textContent.trim()); });
    });
    document.querySelectorAll('[data-dashboard-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        runDashboardAction(button.getAttribute('data-dashboard-action'));
      });
    });
    document.querySelectorAll('[data-workflow-target]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        if (button.disabled) return;
        navigateWorkflowTarget(button.getAttribute('data-workflow-target'));
      });
    });
    document.querySelectorAll('[data-validation-filter]').forEach(function(button){
      button.addEventListener('click', function(){
        applyValidationFilter(button.getAttribute('data-validation-filter'));
      });
    });
    document.querySelectorAll('[data-validation-page]').forEach(function(button){
      button.addEventListener('click', function(){
        currentValidationPage += button.getAttribute('data-validation-page') === 'next' ? 1 : -1;
        applyValidationFilter(currentValidationFilter);
      });
    });
    var pageSize = document.querySelector('[data-validation="page-size"]');
    if (pageSize) {
      pageSize.addEventListener('change', function(){
        validationPageSize = Number(pageSize.value) || 20;
        currentValidationPage = 1;
        applyValidationFilter(currentValidationFilter);
      });
    }
    var validationSearch = document.querySelector('[data-validation="search"]');
    if (validationSearch) {
      validationSearch.addEventListener('input', function(){
        validationSearchQuery = validationSearch.value.trim();
        currentValidationPage = 1;
        applyValidationFilter(currentValidationFilter);
      });
    }
    var shippingSearch = document.querySelector('[data-shipping="search"]');
    if (shippingSearch) {
      shippingSearch.addEventListener('input', function(){
        shippingSearchQuery = shippingSearch.value.trim();
        currentShippingPage = 1;
        renderShippingRows();
      });
    }
    var shippingSelectVisible = document.querySelector('[data-shipping="select-visible"]');
    if (shippingSelectVisible) {
      shippingSelectVisible.addEventListener('change', function(){
        var checked = !!shippingSelectVisible.checked;
        shippingRows().forEach(function(row){
          if (shippingRowSelectable(row)) {
            selectedShippingPersnr[String(row.persnr || '')] = checked;
          }
        });
        renderShippingRows();
        setShippingMessage(checked ? 'Gefilterte sendbare Einträge wurden markiert.' : 'Gefilterte sendbare Einträge wurden abgewählt.');
      });
    }
    var shippingPageSizeSelect = document.querySelector('[data-shipping="page-size"]');
    if (shippingPageSizeSelect) {
      shippingPageSizeSelect.addEventListener('change', function(){
        shippingPageSize = Number(shippingPageSizeSelect.value) || 20;
        currentShippingPage = 1;
        renderShippingRows();
      });
    }
    document.querySelectorAll('[data-shipping-filter]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        shippingStatusFilter = button.getAttribute('data-shipping-filter') || 'all';
        currentShippingPage = 1;
        updateShippingFilterControls();
        renderShippingRows();
        setShippingMessage('Filter: ' + button.textContent.trim() + '.');
      });
    });
    var reportsSearch = document.querySelector('[data-reports="search"]');
    if (reportsSearch) {
      reportsSearch.addEventListener('input', function(){
        reportsSearchQuery = reportsSearch.value.trim();
        reportsPage = 1;
        updateReportsScreen();
      });
    }
    document.querySelectorAll('.page-reports [data-reports-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        if (button.disabled) return;
        runReportsAction(button.getAttribute('data-reports-action'));
      });
    });
    document.querySelectorAll('.page-company [data-company-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        if (button.disabled) return;
        runCompanyAction(button.getAttribute('data-company-action'));
      });
    });
    document.querySelectorAll('[data-company-modal-close]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        closeCompanyCreateModal();
      });
    });
    document.querySelectorAll('[data-shipping-send-close]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        closeShippingSendModal();
        setShippingMessage('Versand wurde vor dem Start abgebrochen.');
      });
    });
    document.querySelectorAll('[data-shipping-send-action="confirm"]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        if (button.disabled) return;
        startShippingSend();
      });
    });
    document.querySelectorAll('[data-company-create-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        submitCompanyCreate(button.getAttribute('data-company-create-action') === 'create-excel');
      });
    });
    var companyNameInput = document.querySelector('[data-company-create="name"]');
    var companyIdInput = document.querySelector('[data-company-create="id"]');
    if (companyNameInput && companyIdInput) {
      companyNameInput.addEventListener('input', function(){
        if (!companyIdInput.dataset.touched) companyIdInput.value = normalizeCompanyId(companyNameInput.value);
      });
      companyIdInput.addEventListener('input', function(){
        companyIdInput.dataset.touched = '1';
        companyIdInput.value = normalizeCompanyId(companyIdInput.value);
      });
      [companyNameInput, companyIdInput].forEach(function(input){
        input.addEventListener('keydown', function(event){
          if (event.key === 'Enter') submitCompanyCreate(false);
        });
      });
    }
    document.querySelectorAll('[data-company-edit-field]').forEach(function(field){
      field.addEventListener('change', function(){
        if (field.getAttribute('data-company-edit-field') === 'mail_scope') {
          updateCompanyMailEditVisibility();
        }
      });
    });
    document.querySelectorAll('.page-license [data-license-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        if (button.disabled) return;
        runLicenseAction(button.getAttribute('data-license-action'));
      });
    });
    document.querySelectorAll('.page-settings [data-settings-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        if (button.disabled) return;
        runSettingsAction(button.getAttribute('data-settings-action'));
      });
    });
    document.querySelectorAll('[data-settings-tab]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        var tab = button.getAttribute('data-settings-tab');
        document.querySelectorAll('[data-settings-tab]').forEach(function(item){
          item.classList.toggle('active', item === button);
        });
        document.querySelectorAll('[data-settings-panel]').forEach(function(panel){
          panel.classList.toggle('active', panel.getAttribute('data-settings-panel') === tab);
        });
      });
    });
    document.querySelectorAll('[data-mass-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        if (button.disabled) return;
        runMassMessageAction(button.getAttribute('data-mass-action'));
      });
    });
    document.querySelectorAll('[data-mass-field]').forEach(function(field){
      field.addEventListener('input', function(){
        var sendButton = document.querySelector('[data-mass-action="send"]');
        if (sendButton) sendButton.disabled = true;
        setMassMessage('Eingabe geändert. Bitte Vorschau neu laden.');
      });
    });
    document.querySelectorAll('[data-help-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        runHelpAction(button.getAttribute('data-help-action'));
      });
    });
    document.querySelectorAll('[data-about-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        runAboutAction(button.getAttribute('data-about-action'));
      });
    });
    var warningToggle = document.querySelector('[data-warning-toggle]');
    if (warningToggle) {
      warningToggle.addEventListener('click', function(event){
        event.preventDefault();
        event.stopPropagation();
        closeCompanySwitchMenu();
        toggleWarningMenu();
      });
    }
    var companySwitchToggle = document.querySelector('[data-company-switch-toggle]');
    if (companySwitchToggle) {
      companySwitchToggle.addEventListener('click', function(event){
        event.preventDefault();
        event.stopPropagation();
        closeWarningMenu();
        toggleCompanySwitchMenu();
      });
    }
    var companySwitchSearch = document.querySelector('[data-company-switch-search]');
    if (companySwitchSearch) {
      companySwitchSearch.addEventListener('input', function(){
        companySwitchSearchQuery = companySwitchSearch.value || '';
        renderCompanySwitcher(latestCompanyState || {});
      });
      companySwitchSearch.addEventListener('click', function(event){ event.stopPropagation(); });
    }
    document.querySelectorAll('[data-company-switch-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopPropagation();
        closeCompanySwitchMenu();
        if (button.getAttribute('data-company-switch-action') === 'open-company') setPage('Unternehmen');
      });
    });
    document.querySelectorAll('.company-switcher [data-company-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopPropagation();
        closeCompanySwitchMenu();
        runCompanyAction(button.getAttribute('data-company-action'));
      });
    });
    document.addEventListener('click', function(event){
      if (!event.target.closest || !event.target.closest('.company-switcher')) closeCompanySwitchMenu();
      if (!event.target.closest || !event.target.closest('.warning-center')) closeWarningMenu();
    });
    document.querySelectorAll('[data-legal-close]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        closeAboutLegalModal();
      });
    });
    document.addEventListener('keydown', function(event){
      if (event.key === 'Escape') {
        closeAboutLegalModal();
        closeCompanyCreateModal();
      }
    });
    document.querySelectorAll('.page-mailing [data-shipping-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        if (button.disabled) return;
        runShippingAction(button.getAttribute('data-shipping-action'));
      });
    });
    document.querySelectorAll('[data-validation-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        if (button.disabled) return;
        var action = button.getAttribute('data-validation-action');
        if (action === 'toggle-issues') {
          validationIssuesOnly = !validationIssuesOnly;
          currentValidationPage = 1;
          applyValidationFilter(currentValidationFilter);
        }
        if (action === 'toggle-group') {
          validationGroupMode = !validationGroupMode;
          currentValidationPage = 1;
          applyValidationFilter(currentValidationFilter);
        }
        if (action === 'export-csv') exportValidationCsv();
        if (action === 'go-shipping') goToShippingFromValidation();
      });
    });
    document.querySelectorAll('[data-report-open]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        if (button.disabled) return;
        openReport(button.getAttribute('data-report-open'));
      });
    });
    document.querySelectorAll('[data-report] button').forEach(function(button){
      button.addEventListener('click', function(event){
        var item = button.closest('[data-report]');
        if (!item || button.disabled) return;
        event.preventDefault();
        openReport(item.getAttribute('data-report'));
      });
    });
    document.querySelectorAll('[data-pdf-mode]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopPropagation();
        var bridge = window.lohnmailBridge;
        if (!bridge || !bridge.setPdfInputMode) {
          setInfoBanner('Bridge wird noch geladen. Bitte kurz warten.', false);
          return;
        }
        bridge.setPdfInputMode(button.getAttribute('data-pdf-mode'), function(payload){
          consumeProcessingPayload(payload, 'input');
        });
      });
    });
    document.querySelectorAll('.quick-grid button, .primary, .ghost, .wide-button').forEach(function(btn){
      btn.addEventListener('click', function(){
        var text = btn.textContent.trim();
        if (text.indexOf('Verarbeitung') !== -1 || text.indexOf('Neuer Lauf') !== -1) setPage('Verarbeitung');
        if (text.indexOf('Versand') !== -1) setPage('Versand');
        if (text.indexOf('Berichte') !== -1) setPage('Berichte');
      });
    });
  });
})();
