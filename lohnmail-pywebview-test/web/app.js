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
  var shippingSelectionDirty = false;
  var shippingTerminalState = null;
  var shippingLiveProgress = {
    companyId: '',
    phase: 'idle',
    total: 0,
    completed: 0,
    sent: 0,
    errors: 0,
    currentPersnr: '',
    currentEmail: '',
    selected: {},
    processed: {}
  };
  var shippingPreviewZoom = 100;
  var reportsSearchQuery = '';
  var reportsTypeFilter = 'all';
  var reportsStatusFilter = 'all';
  var reportsReadyOnly = false;
  var reportsPage = 1;
  var reportsPageSize = 10;
  var reportsRecipientPage = 1;
  var reportsRecipientPageSize = 20;
  var reportsPeriodFilter = 'latest';
  var reportsRecipientFilter = 'all';
  var reportsRecipientSearchQuery = '';
  var selectedReportKind = '';
  var selectedReportId = '';
  var latestReportsState = null;
  var latestCompanyState = null;
  var companySwitchSearchQuery = '';
  var latestLicenseState = null;
  var latestSettingsState = null;
  var UPDATE_STORAGE_KEY = 'lohnmail.update-ui.v1';
  var latestUpdateState = {
    installed_version: '2.0.3',
    installed_build: '2026.09.01.3',
    last_checked_at: '',
    auto_check: true,
    status: 'idle',
    available_version: '',
    available_build: '',
    required: false,
    progress: 0,
    downloaded_bytes: 0,
    total_bytes: 0,
    release_notes: [],
    install_on_exit: false,
    install_supported: false,
    required_reason: '',
    message: ''
  };
  var outlookAccounts = [];
  var warningsAutoOpened = false;
  var latestMassMessageState = null;
  var latestShippingSendPreview = null;
  var processingActivityLog = [];
  var lastProcessingLogKey = '';
  var currentHelpTopic = 'all';
  var helpSearchQuery = '';
  var helpShowAll = false;
  var appDialogConfirm = null;
  var appDialogCancel = null;
  function applyBrandLogoVariant(){
    var source = 'assets/brand/lohnmail-app-icon-previous.png';
    document.documentElement.setAttribute('data-logo-variant', 'production');
    document.querySelectorAll('[data-brand-logo]').forEach(function(image){
      image.setAttribute('src', source);
    });
  }
  function parseUpdatePayload(payload){
    if (!payload) return {};
    if (typeof payload === 'object') return payload;
    try {
      return JSON.parse(payload);
    } catch (error) {
      return { status: 'error', message: 'Die Update-Antwort konnte nicht gelesen werden.' };
    }
  }
  function normalizeUpdateStatus(value){
    var allowed = ['idle', 'checking', 'current', 'available', 'downloading', 'ready', 'installing', 'required', 'error'];
    var normalized = String(value || 'idle').toLowerCase();
    return allowed.indexOf(normalized) === -1 ? 'idle' : normalized;
  }
  function updateIsMandatory(state){
    var reason = String((state || {}).required_reason || '').toLowerCase();
    return (state || {}).required === true
      && (reason === 'security' || reason === 'critical_security' || reason === 'incompatible' || reason === 'critical_incompatibility');
  }
  function updateIsAvailable(state){
    state = state || {};
    var status = normalizeUpdateStatus(state.status);
    return ['available', 'downloading', 'ready', 'required'].indexOf(status) !== -1 || !!state.available_version;
  }
  function formatUpdateBytes(value){
    var bytes = Math.max(0, Number(value || 0));
    if (!bytes) return '0 MB';
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(bytes < 10 * 1024 * 1024 ? 1 : 0) + ' MB';
  }
  function closeAppDialog(confirmed){
    var modal = document.querySelector('[data-app-dialog]');
    if (modal) modal.hidden = true;
    var callback = confirmed ? appDialogConfirm : appDialogCancel;
    appDialogConfirm = null;
    appDialogCancel = null;
    if (typeof callback === 'function') callback();
  }
  function openAppDialog(options){
    options = options || {};
    var modal = document.querySelector('[data-app-dialog]');
    if (!modal) {
      if (typeof options.onConfirm === 'function') options.onConfirm();
      return;
    }
    setText('[data-app-dialog-kicker]', options.kicker || 'LohnMail');
    setText('[data-app-dialog-title]', options.title || 'Hinweis');
    setText('[data-app-dialog-message]', options.message || '');
    var confirmButton = modal.querySelector('[data-app-dialog-action="confirm"]');
    var cancelButton = modal.querySelector('.license-validation-modal-actions [data-app-dialog-action="cancel"]');
    if (confirmButton) confirmButton.textContent = options.confirmLabel || 'OK';
    if (cancelButton) {
      cancelButton.textContent = options.cancelLabel || 'Abbrechen';
      cancelButton.hidden = options.cancelable === false;
    }
    appDialogConfirm = options.onConfirm || null;
    appDialogCancel = options.onCancel || null;
    modal.hidden = false;
    if (confirmButton) window.setTimeout(function(){ confirmButton.focus(); }, 0);
  }
  function loadUpdatePreferences(){
    try {
      var stored = JSON.parse(window.localStorage.getItem(UPDATE_STORAGE_KEY) || '{}');
      if (stored && typeof stored === 'object') latestUpdateState = Object.assign({}, latestUpdateState, stored);
    } catch (error) {
      // Eine beschädigte lokale Präferenz darf die Einstellungen nicht blockieren.
    }
    latestUpdateState.status = normalizeUpdateStatus(latestUpdateState.status);
    if (latestUpdateState.status === 'checking') latestUpdateState.status = 'idle';
    if (latestUpdateState.status === 'downloading') latestUpdateState.status = 'available';
  }
  function saveUpdatePreferences(){
    try {
      window.localStorage.setItem(UPDATE_STORAGE_KEY, JSON.stringify(latestUpdateState));
    } catch (error) {
      // QWebEngine kann lokalen Speicher deaktivieren; der UI-Zustand bleibt trotzdem aktiv.
    }
  }
  function activateSettingsTab(tab){
    document.querySelectorAll('[data-settings-tab]').forEach(function(item){
      item.classList.toggle('active', item.getAttribute('data-settings-tab') === tab);
    });
    document.querySelectorAll('[data-settings-panel]').forEach(function(panel){
      panel.classList.toggle('active', panel.getAttribute('data-settings-panel') === tab);
    });
  }
  function updateStatusCopy(state){
    var version = state.available_version ? 'Version ' + state.available_version : 'Eine neue Version';
    var message = String(state.message || '');
    var normalizedMessage = message.toLowerCase();
    var errorTitle = 'Update-Prüfung nicht verfügbar';
    if (normalizedMessage.indexOf('wiederhergestellt') !== -1 || normalizedMessage.indexOf('rollback') !== -1) {
      errorTitle = 'Vorherige Version wiederhergestellt';
    } else if (normalizedMessage.indexOf('sqlite') !== -1 || normalizedMessage.indexOf('berichtshistorie') !== -1 || normalizedMessage.indexOf('lokale historie') !== -1) {
      errorTitle = 'Lokale Daten konnten nicht geprüft werden';
    } else if (normalizedMessage.indexOf('zugriff') !== -1 || normalizedMessage.indexOf('firewall') !== -1 || normalizedMessage.indexOf('proxy') !== -1) {
      errorTitle = 'Zugriff auf den Update-Server nicht möglich';
    }
    var copies = {
      idle: ['Noch nicht geprüft', 'Starten Sie die manuelle Update-Prüfung.'],
      checking: ['Suche läuft...', 'Der Update-Dienst wird nach einer neueren Version gefragt.'],
      current: ['LohnMail ist aktuell', 'Für diese Installation ist kein neueres Update verfügbar.'],
      available: ['Update verfügbar', version + ' kann heruntergeladen werden.'],
      downloading: ['Download läuft', version + ' wird sicher heruntergeladen.'],
      ready: state.preflight_error
        ? ['Lokale Daten konnten nicht geprüft werden', state.preflight_error]
        : ['Bereit zur Installation', version + ' wurde heruntergeladen und geprüft.'],
      installing: ['Installation wird gestartet', 'LohnMail wird geschlossen und anschließend neu gestartet.'],
      required: ['Kritisches Update erforderlich', version + ' behebt eine kritische Sicherheitslücke oder technische Inkompatibilität.'],
      error: [errorTitle, message || 'Der Update-Dienst ist derzeit nicht erreichbar.']
    };
    return copies[normalizeUpdateStatus(state.status)] || copies.idle;
  }
  function renderUpdateFlow(state){
    var keys = ['check', 'download', 'preflight', 'backup', 'install', 'verify', 'restart'];
    var status = normalizeUpdateStatus(state.status);
    var message = String(state.message || '').toLowerCase();
    var activeIndex = -1;
    var doneThrough = -1;
    var errorIndex = -1;
    if (status === 'idle' || status === 'checking') activeIndex = 0;
    else if (status === 'available' || status === 'required' || status === 'downloading') {
      doneThrough = 0;
      activeIndex = 1;
    } else if (status === 'ready') {
      doneThrough = 1;
      if (state.preflight_error) errorIndex = 2;
      else activeIndex = 2;
    } else if (status === 'installing') {
      doneThrough = 1;
      activeIndex = 2;
    } else if (status === 'current') {
      if (message.indexOf('erfolgreich installiert') !== -1) doneThrough = keys.length - 1;
      else doneThrough = 0;
    } else if (status === 'error') {
      if (message.indexOf('wiederhergestellt') !== -1 || message.indexOf('rollback') !== -1) {
        doneThrough = 4;
        errorIndex = 5;
      } else if (message.indexOf('sqlite') !== -1 || message.indexOf('berichtshistorie') !== -1 || message.indexOf('lokale historie') !== -1) {
        doneThrough = 1;
        errorIndex = 2;
      } else {
        errorIndex = 0;
      }
    }
    keys.forEach(function(key, index){
      var node = document.querySelector('[data-update-step="' + key + '"]');
      if (!node) return;
      node.classList.remove('active', 'done', 'error');
      if (index <= doneThrough) node.classList.add('done');
      if (index === activeIndex) node.classList.add('active');
      if (index === errorIndex) node.classList.add('error');
      var marker = node.firstElementChild;
      if (marker) marker.textContent = index <= doneThrough ? '✓' : (index === errorIndex ? '×' : String(index + 1));
    });
  }
  function setButtonLabel(button, label){
    if (!button) return;
    var labelNode = button.querySelector('.button-label');
    if (!labelNode) {
      labelNode = document.createElement('span');
      labelNode.className = 'button-label';
      Array.prototype.slice.call(button.childNodes).forEach(function(node){
        if (node.nodeType === Node.TEXT_NODE) node.remove();
      });
      button.appendChild(labelNode);
    }
    labelNode.textContent = label;
  }
  function renderUpdateSettings(){
    var state = latestUpdateState;
    var status = normalizeUpdateStatus(state.status);
    var copy = updateStatusCopy(state);
    setText('[data-update="installed-version"]', 'v' + String(state.installed_version || '2.0.3').replace(/^v/i, ''));
    setText('[data-update="installed-build"]', 'Build ' + (state.installed_build || '-'));
    setText('[data-update="last-checked"]', state.last_checked_at ? formatDateTime(state.last_checked_at) : 'Noch nicht geprüft');
    setText('[data-update="status-title"]', copy[0]);
    setText('[data-update="status-detail"]', copy[1]);

    var badge = document.querySelector('[data-update="badge"]');
    if (badge) {
      badge.className = 'update-status-badge ' + (state.preflight_error ? 'error' : status);
      badge.textContent = copy[0];
    }
    var autoCheck = document.querySelector('[data-update-pref="auto-check"]');
    if (autoCheck) autoCheck.checked = state.auto_check !== false;
    var primaryButton = document.querySelector('[data-update-action="primary"], [data-update-primary-action]');
    if (primaryButton) {
      var primaryAction = 'check';
      var primaryLabel = 'Nach Updates suchen';
      if (status === 'available' || status === 'required') {
        primaryAction = 'download';
        primaryLabel = 'Update herunterladen';
      } else if (status === 'downloading') {
        primaryAction = 'download';
        primaryLabel = 'Download läuft...';
      } else if (status === 'ready') {
        primaryAction = 'install-now';
        primaryLabel = state.preflight_error ? 'Erneut prüfen' : 'Schließen und aktualisieren';
      } else if (status === 'checking') {
        primaryLabel = 'Suche läuft...';
      } else if (status === 'installing') {
        primaryAction = 'install-now';
        primaryLabel = 'Installation läuft...';
      }
      primaryButton.setAttribute('data-update-action', primaryAction);
      primaryButton.setAttribute('data-update-primary-action', 'true');
      setButtonLabel(primaryButton, primaryLabel);
      primaryButton.disabled = status === 'checking' || status === 'downloading' || status === 'installing'
        || ((primaryAction === 'download' || primaryAction === 'install-now') && state.install_supported !== true);
      primaryButton.title = primaryButton.disabled && state.install_supported !== true
        ? 'Updates werden in dieser Version nur unter Windows installiert.'
        : '';
    }
    var download = document.querySelector('[data-update-download]');
    if (download) download.hidden = status !== 'downloading' && status !== 'ready';
    var progress = Math.max(0, Math.min(100, Number(state.progress || 0)));
    setText('[data-update="progress-text"]', Math.round(progress) + '%');
    var progressBar = document.querySelector('[data-update="progress-bar"]');
    if (progressBar) progressBar.style.width = progress + '%';
    setText('[data-update="download-title"]', status === 'ready' ? 'Update heruntergeladen' : (status === 'required' ? 'Kritisches Update' : 'Update wird vorbereitet'));
    var downloadDetail = state.total_bytes
      ? formatUpdateBytes(state.downloaded_bytes) + ' von ' + formatUpdateBytes(state.total_bytes)
      : [state.available_version ? 'Version ' + state.available_version : '', state.available_build ? 'Build ' + state.available_build : ''].filter(Boolean).join(' · ');
    setText('[data-update="download-detail"]', downloadDetail || 'Download noch nicht gestartet');
    setText('[data-update="release-version"]', state.available_version ? 'Version ' + state.available_version : 'Installierte Version ' + state.installed_version);
    var notes = document.querySelector('[data-update="release-notes"]');
    if (notes) {
      notes.textContent = '';
      var values = Array.isArray(state.release_notes) ? state.release_notes : String(state.release_notes || '').split(/\r?\n/).filter(Boolean);
      if (!values.length) values = ['Release Notes erscheinen hier, sobald der Update-Dienst eine neue Version meldet.'];
      var list = document.createElement('ul');
      values.forEach(function(value){
        var item = document.createElement('li');
        item.textContent = String(value);
        list.appendChild(item);
      });
      notes.appendChild(list);
    }
    renderUpdateFlow(state);
  }
  function applyUpdateState(payload){
    var next = parseUpdatePayload(payload);
    latestUpdateState = Object.assign({}, latestUpdateState, next);
    latestUpdateState.status = normalizeUpdateStatus(latestUpdateState.status);
    if (latestUpdateState.status === 'required' && !updateIsMandatory(latestUpdateState)) {
      latestUpdateState.status = 'available';
    }
    if (updateIsMandatory(latestUpdateState) && updateIsAvailable(latestUpdateState)) {
      latestUpdateState.status = 'required';
    }
    if (!Object.prototype.hasOwnProperty.call(next, 'last_checked_at') && ['current', 'available', 'required', 'error'].indexOf(latestUpdateState.status) !== -1) {
      latestUpdateState.last_checked_at = new Date().toISOString();
    }
    saveUpdatePreferences();
    renderUpdateSettings();
    updateWarningCenter();
    return latestUpdateState;
  }
  function dispatchUpdateAction(action){
    var bridge = window.lohnmailBridge;
    if (action === 'check') {
      latestUpdateState.status = 'checking';
      latestUpdateState.message = '';
      latestUpdateState.preflight_error = '';
      renderUpdateSettings();
      if (bridge && typeof bridge.checkForUpdates === 'function') {
        bridge.checkForUpdates(function(payload){ applyUpdateState(payload); });
      } else {
        applyUpdateState({
          status: 'error',
          last_checked_at: new Date().toISOString(),
          message: 'Der Update-Dienst ist in dieser Build noch nicht verbunden.'
        });
      }
      return;
    }
    if (action === 'download') {
      var versionLabel = latestUpdateState.available_version ? 'Version ' + latestUpdateState.available_version : 'das Update';
      openAppDialog({
        kicker: 'Softwareupdate',
        title: 'Update herunterladen?',
        message: versionLabel + ' wird heruntergeladen. Danach entscheiden Sie ausdrücklich, wann LohnMail geschlossen und aktualisiert wird.',
        confirmLabel: 'Herunterladen',
        cancelLabel: 'Später',
        onConfirm: function(){
          if (bridge && typeof bridge.downloadUpdate === 'function') {
            applyUpdateState({ status: 'downloading', progress: 0, downloaded_bytes: 0 });
            bridge.downloadUpdate(function(payload){ applyUpdateState(payload); });
          } else {
            latestUpdateState.message = 'Der Download-Dienst ist in dieser Build noch nicht verbunden.';
            latestUpdateState.status = updateIsMandatory(latestUpdateState) ? 'required' : 'available';
            saveUpdatePreferences();
            renderUpdateSettings();
          }
        }
      });
      return;
    }
    if (action === 'install-now') {
      openAppDialog({
        kicker: 'Softwareupdate',
        title: 'LohnMail schließen und aktualisieren?',
        message: 'Settings, Unternehmen und Berichte bleiben unverändert. Vor der Installation werden die lokalen Daten geprüft. Bei einem Fehler wird die vorherige Programmversion wiederhergestellt.',
        confirmLabel: 'Schließen und aktualisieren',
        cancelLabel: 'Abbrechen',
        onConfirm: function(){
          if (bridge && typeof bridge.installUpdateNow === 'function') {
            latestUpdateState.status = 'installing';
            latestUpdateState.preflight_error = '';
            latestUpdateState.message = 'Lokale Daten werden vor dem Schließen geprüft.';
            renderUpdateSettings();
            bridge.installUpdateNow(function(payload){
              var result = parseUpdatePayload(payload);
              if (result && result.started === false) {
                latestUpdateState.status = 'ready';
                latestUpdateState.preflight_error = result.message || 'Die lokalen Daten konnten nicht geprüft werden.';
                latestUpdateState.message = latestUpdateState.preflight_error;
                saveUpdatePreferences();
                renderUpdateSettings();
                openAppDialog({
                  kicker: 'Softwareupdate',
                  title: 'Update konnte nicht gestartet werden',
                  message: result.message || 'Bitte versuchen Sie es erneut.',
                  confirmLabel: 'OK',
                  cancelable: false
                });
              }
            });
          } else {
            openAppDialog({
              kicker: 'Softwareupdate',
              title: 'Installation nicht verfügbar',
              message: 'Die Update-Installation ist in dieser Version nicht verfügbar.',
              confirmLabel: 'OK',
              cancelable: false
            });
          }
        }
      });
    }
  }
  function persistUpdatePreferences(){
    var payload = {
      auto_check: latestUpdateState.auto_check !== false,
      install_on_exit: latestUpdateState.install_on_exit === true
    };
    saveUpdatePreferences();
    var bridge = window.lohnmailBridge;
    if (bridge && typeof bridge.setUpdatePreferences === 'function') {
      bridge.setUpdatePreferences(JSON.stringify(payload), function(raw){ applyUpdateState(raw); });
      return;
    }
    renderUpdateSettings();
    updateWarningCenter();
  }
  function maybeCheckForUpdates(){
    var bridge = window.lohnmailBridge;
    if (latestUpdateState.auto_check === false || !bridge || typeof bridge.checkForUpdates !== 'function') return;
    var status = String(latestUpdateState.status || 'idle');
    if (['checking', 'downloading', 'available', 'required', 'ready'].indexOf(status) !== -1) return;
    var lastChecked = Date.parse(latestUpdateState.last_checked_at || '');
    if (Number.isFinite(lastChecked) && Date.now() - lastChecked < 24 * 60 * 60 * 1000) return;
    dispatchUpdateAction('check');
  }
  function loadUpdateStateFromBridge(){
    var bridge = window.lohnmailBridge;
    if (bridge && typeof bridge.getUpdateState === 'function') {
      bridge.getUpdateState(function(payload){
        applyUpdateState(payload);
        maybeCheckForUpdates();
      });
      return;
    }
    renderUpdateSettings();
    maybeCheckForUpdates();
  }
  window.lohnmailApplyUpdateState = applyUpdateState;
  window.lohnmailGetUpdatePreferences = function(){ return Object.assign({}, latestUpdateState); };
  window.addEventListener('lohnmail:update-state', function(event){ applyUpdateState(event.detail || {}); });
  var pywebviewSignalHandlers = {};
  window.lohnmailReceiveSignal = function(name, payload){
    (pywebviewSignalHandlers[name] || []).forEach(function(handler){
      try { handler(payload); } catch (error) { console.warn('pywebview signal failed', name, error); }
    });
  };
  function createPywebviewBridge(){
    return new Proxy({}, {
      get: function(target, property){
        if (property === '__lohnmailSignalsBound') return target[property];
        if (property in target) return target[property];
        if (property in pywebviewSignalHandlers || /(?:Changed|Progress|Finished|Error)$/.test(String(property))) {
          return {
            connect: function(handler){
              pywebviewSignalHandlers[property] = pywebviewSignalHandlers[property] || [];
              pywebviewSignalHandlers[property].push(handler);
            }
          };
        }
        if (!window.pywebview || !window.pywebview.api || typeof window.pywebview.api[property] !== 'function') return undefined;
        return function(){
          var args = Array.prototype.slice.call(arguments);
          var callback = typeof args[args.length - 1] === 'function' ? args.pop() : null;
          var promise = window.pywebview.api[property].apply(window.pywebview.api, args);
          if (callback) promise.then(callback).catch(function(error){
            console.error('pywebview bridge call failed', property, error);
            callback(JSON.stringify({ok:false, message:String(error && error.message || error)}));
          });
          return promise;
        };
      },
      set: function(target, property, value){ target[property] = value; return true; }
    });
  }
  function bridgeReady(bridge){
    window.lohnmailBridge = bridge;
    bindBridgeSignals();
    loadDashboardState();
    loadCompanyState();
    loadSettingsState();
    loadProcessingState();
    loadValidationState();
    loadShippingState();
    loadReportsState();
    loadMassMessageState();
    loadUpdateStateFromBridge();
  }
  function initBridge(){
    if (window.pywebview && window.pywebview.api) {
      bridgeReady(createPywebviewBridge());
      return;
    }
    window.addEventListener('pywebviewready', function(){ bridgeReady(createPywebviewBridge()); }, {once:true});
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
        loadReportsState();
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
        var state = consumeShippingPayload(payload);
        if (state && state.status && state.status.finished && state.status.dry_run !== false) {
          shippingSelectionDirty = false;
          updateShippingSelectionSummary();
        }
        loadDashboardState();
        loadReportsState();
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
    if (bridge.updateStateChanged) {
      bridge.updateStateChanged.connect(function(payload){ applyUpdateState(payload); });
    }
    if (bridge.updateProgress) {
      bridge.updateProgress.connect(function(payload){ applyUpdateState(payload); });
    }
  }
  function setText(selector, value){
    var node = document.querySelector(selector);
    if (node && value !== undefined && value !== null) node.textContent = String(value);
  }
  function setPathText(selector, value){
    var node = document.querySelector(selector);
    if (!node || value === undefined || value === null) return;
    var path = String(value || '-');
    node.title = path === '-' ? '' : path;
    node.dataset.fullPath = path;
    fitPathFromEnd(node, path, 0);
  }
  function fitPathFromEnd(node, path, attempt){
    if (!node) return;
    node.textContent = path;
    if (!node.clientWidth) {
      if (attempt < 3) window.setTimeout(function(){ fitPathFromEnd(node, path, attempt + 1); }, 60);
      return;
    }
    if (node.scrollWidth <= node.clientWidth || path.length < 5) return;
    var low = 1;
    var high = path.length - 1;
    var best = path.slice(-1);
    while (low <= high) {
      var count = Math.floor((low + high) / 2);
      var candidate = '…' + path.slice(-count);
      node.textContent = candidate;
      if (node.scrollWidth <= node.clientWidth) {
        best = path.slice(-count);
        low = count + 1;
      } else {
        high = count - 1;
      }
    }
    node.textContent = '…' + best;
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
    var text = String(value);
    var normalized = text.toLowerCase();
    var level = normalized === 'fehler' ? 'error' : (
      normalized === 'offen' || normalized === 'warnung' ? 'warning' : (
        normalized === 'läuft' ? 'running' : 'ok'
      )
    );
    node.textContent = text;
    node.classList.toggle('warning-text', level === 'warning');
    var row = node.parentElement;
    if (row) {
      row.classList.remove('status-ok', 'status-warning', 'status-error', 'status-running');
      row.classList.add('status-' + level);
      var icon = row.querySelector('.check');
      if (icon) icon.textContent = level === 'error' ? '×' : (level === 'warning' ? '!' : (level === 'running' ? '…' : '✓'));
    }
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
    var latest = (latestReportsState && latestReportsState.latest) || {};
    Object.keys(latest).forEach(function(key){ result[key] = latest[key]; });
    [latestDashboardState, latestValidationState, latestShippingState].forEach(function(state){
      var reports = (state && state.reports) || {};
      Object.keys(reports).forEach(function(key){
        if (!result[key] || !result[key].exists) result[key] = reports[key];
      });
    });
    return result;
  }
  function reportIcon(type, kind){
    if (type === 'pdf') return 'doc';
    if (kind === 'send') return 'report';
    return 'table';
  }
  function reportDate(value){
    if (!value) return '-';
    var date = new Date(value);
    return isNaN(date.getTime()) ? String(value) : date.toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' });
  }
  function reportSize(value){
    var bytes = Number(value || 0);
    if (!bytes) return '-';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1).replace('.', ',') + ' KB';
    return (bytes / 1048576).toFixed(1).replace('.', ',') + ' MB';
  }
  function normalizeReportMetrics(value){
    value = value || {};
    return {
      employees: Number(value.employees || 0),
      missing_email: Number(value.missing_email || 0),
      processed: Number(value.processed || 0),
      warnings: Number(value.warnings || 0),
      errors: Number(value.errors || 0),
      sent: Number(value.sent || 0),
      delivered: Number(value.delivered || 0),
      failed: Number(value.failed || 0),
      prepared: Number(value.prepared || 0)
    };
  }
  function reportRows(){
    var sessions = (latestReportsState && latestReportsState.sessions) || [];
    return sessions.map(function(session){
      var metrics = normalizeReportMetrics(session.metrics);
      var files = (session.files || []).map(function(file){
        var type = String(file.type || 'file').toLowerCase();
        return {
          id: String(file.id || ''),
          kind: String(file.kind || 'other'),
          type: type,
          icon: reportIcon(type, file.kind),
          title: String(file.filename || file.title || 'Bericht'),
          path: String(file.path || ''),
          exists: !!file.exists,
          size: reportSize(file.size)
        };
      });
      var statusKey = String(session.status_key || '').toLowerCase();
      if (!statusKey) statusKey = metrics.failed || metrics.errors ? 'error' : (session.dry_run === true ? 'prepared' : 'completed');
      return {
        id: String(session.id || session.run_id || ''),
        runId: String(session.run_id || session.id || ''),
        companyId: String(session.company_id || ''),
        companyName: String(session.company_name || 'Mandant'),
        createdAt: String(session.created_at || ''),
        created: reportDate(session.created_at),
        status: String(session.status || (session.dry_run === true ? 'Vorbereitet' : 'Abgeschlossen')),
        statusKey: statusKey,
        dryRun: session.dry_run === true,
        metrics: metrics,
        files: files,
        recipients: (session.recipients || []).slice(),
        exists: files.some(function(file){ return file.exists; })
      };
    }).sort(function(a, b){
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });
  }
  function isRealSendReport(row){
    return row && row.dryRun !== true && Number(row.metrics.sent || 0) > 0;
  }
  function reportRowsForPeriod(){
    var rows = reportRows();
    if (reportsPeriodFilter === 'latest') {
      var latestSent = rows.filter(isRealSendReport)[0];
      return latestSent ? [latestSent] : (rows.length ? [rows[0]] : []);
    }
    if (reportsPeriodFilter === 'all') return rows;
    var now = new Date();
    var threshold = new Date(now);
    if (reportsPeriodFilter === '7d') threshold.setDate(now.getDate() - 7);
    if (reportsPeriodFilter === '30d') threshold.setDate(now.getDate() - 30);
    if (reportsPeriodFilter === 'month') threshold = new Date(now.getFullYear(), now.getMonth(), 1);
    return rows.filter(function(row){
      var date = new Date(row.createdAt);
      return !isNaN(date.getTime()) && date >= threshold;
    });
  }
  function filteredReportRows(){
    var rows = reportRowsForPeriod();
    if (reportsTypeFilter === 'sent') rows = rows.filter(isRealSendReport);
    if (reportsTypeFilter === 'prepared') rows = rows.filter(function(row){ return row.dryRun; });
    if (reportsStatusFilter !== 'all') rows = rows.filter(function(row){ return row.statusKey === reportsStatusFilter; });
    if (reportsReadyOnly) rows = rows.filter(function(row){ return row.exists; });
    if (reportsSearchQuery) {
      var query = reportsSearchQuery.toLowerCase();
      rows = rows.filter(function(row){
        var files = row.files.map(function(file){ return file.title + ' ' + file.path; }).join(' ');
        var recipients = row.recipients.map(function(recipient){ return [recipient.employee, recipient.persnr, recipient.email].join(' '); }).join(' ');
        return [row.companyName, row.status, row.created, row.runId, files, recipients]
          .join(' ').toLowerCase().indexOf(query) !== -1;
      });
    }
    return rows;
  }
  function reportMetricValues(row){
    var metrics = row ? row.metrics : normalizeReportMetrics();
    var employees = Math.max(metrics.employees, metrics.processed, row ? row.recipients.length : 0);
    return {
      sent: metrics.sent,
      missingEmail: metrics.missing_email,
      employees: employees,
      failed: Math.max(metrics.failed, metrics.errors),
      rate: employees ? Math.round((metrics.sent / employees) * 100) : 0,
      hasData: !!row
    };
  }
  function setReportsDetailText(key, value){ setText('[data-reports-detail="' + key + '"]', value); }
  function selectedReportRow(){
    return reportRows().filter(function(row){ return row.id === selectedReportId; })[0] || null;
  }
  function applyReportDetail(row){
    var detail = document.querySelector('.report-details');
    var reportsGrid = document.querySelector('.reports-grid');
    if (row && detail) {
      detail.hidden = false;
      if (reportsGrid) reportsGrid.classList.remove('detail-hidden');
    }
    selectedReportId = row ? row.id : '';
    selectedReportKind = '';
    var statusNode = document.querySelector('[data-reports-detail="status"]');
    var iconNode = document.querySelector('[data-reports-detail="icon"]');
    if (iconNode) iconNode.setAttribute('data-icon', row ? 'report' : 'doc');
    if (statusNode) {
      statusNode.textContent = row ? row.status : 'Nicht ausgewählt';
      statusNode.className = 'state ' + (row && row.statusKey === 'error' ? 'error' : (row ? 'ready' : 'warning'));
    }
    setReportsDetailText('title', row ? row.companyName : 'Kein Bericht ausgewählt');
    setReportsDetailText('subtitle', row ? 'Versandvorgang vom ' + row.created : 'Bitte einen Eintrag wählen.');
    setReportsDetailText('id', row ? row.id.toUpperCase() : '-');
    setReportsDetailText('period', row ? (row.runId || row.created) : '-');
    setReportsDetailText('created', row ? row.created : '-');
    setReportsDetailText('owner', 'LohnMail');
    var existingFiles = row ? row.files.filter(function(file){ return file.exists; }) : [];
    setReportsDetailText('path', existingFiles.length ? existingFiles[0].path : '-');
    var metrics = row ? row.metrics : normalizeReportMetrics();
    setReportsDetailText('employees', Math.max(metrics.employees, metrics.processed, row ? row.recipients.length : 0));
    setReportsDetailText('errors', metrics.errors);
    setReportsDetailText('warnings', metrics.warnings);
    setReportsDetailText('sent', metrics.sent);
    setReportsDetailText('delivered', metrics.delivered);
    setReportsDetailText('failed', metrics.failed);
    var filesNode = document.querySelector('[data-reports-detail="files"]');
    if (filesNode) {
      filesNode.innerHTML = row && row.files.length ? row.files.map(function(file, index){
        return '<button type="button" class="report-detail-file" data-report-file-index="' + index + '" ' + (file.exists ? '' : 'disabled') + '>' +
          '<span class="file-dot ' + escapeHtml(file.type) + '"><span data-icon="' + escapeHtml(file.icon) + '"></span></span>' +
          '<span><b>' + escapeHtml(file.title) + '</b><small>' + escapeHtml(file.exists ? file.size : 'Nicht erstellt') + '</small></span>' +
          '<span data-icon="arrow-up-right"></span></button>';
      }).join('') : '<div class="report-detail-file empty">Keine Berichtsdateien vorhanden.</div>';
      filesNode.querySelectorAll('[data-report-file-index]').forEach(function(button){
        button.addEventListener('click', function(){
          var file = row.files[Number(button.getAttribute('data-report-file-index'))];
          if (file) openReportEntry(file);
        });
      });
    }
  }
  function openReportEntry(file){
    var selected = selectedReportRow();
    file = file || (selected && selected.files.filter(function(item){ return item.exists; })[0]);
    var bridge = window.lohnmailBridge;
    if (!file || !file.exists) return setReportsMessage('Bitte einen vorhandenen Bericht auswählen.');
    if (!bridge || !bridge.openReportEntry) return openReport(file.kind);
    bridge.openReportEntry(file.id, function(payload){
      try {
        var result = JSON.parse(payload || '{}');
        setReportsMessage(result.ok ? 'Bericht geöffnet: ' + result.path : (result.message || 'Bericht konnte nicht geöffnet werden.'));
      } catch (error) {
        setReportsMessage('Bericht konnte nicht geöffnet werden.');
      }
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
      tbody.innerHTML = '<tr><td colspan="8">Keine Versandvorgänge für diesen Filter.</td></tr>';
      setReportsMessage('Zeige 0 Einträge');
    } else {
      tbody.innerHTML = pageRows.map(function(row, index){
        return '<tr data-reports-row="' + index + '" class="' + (row.id === selectedReportId ? 'selected' : '') + '">' +
          '<td>' + escapeHtml(row.created) + '</td>' +
          '<td><b>' + escapeHtml(row.companyName) + '</b><small>' + escapeHtml(row.runId || '-') + '</small></td>' +
          '<td><span class="state ' + (row.statusKey === 'error' ? 'error' : 'ready') + '">' + escapeHtml(row.status) + '</span></td>' +
          '<td>' + Math.max(row.metrics.employees, row.metrics.processed, row.recipients.length) + '</td>' +
          '<td>' + row.metrics.missing_email + '</td>' +
          '<td>' + row.metrics.sent + '</td>' +
          '<td>' + Math.max(row.metrics.failed, row.metrics.errors) + '</td>' +
          '<td><div class="report-row-actions">' +
            '<button type="button" data-reports-row-action="select" title="Details anzeigen" aria-label="Details anzeigen"><span data-icon="arrow-up-right"></span></button>' +
          '</div></td>' +
        '</tr>';
      }).join('');
      tbody.querySelectorAll('[data-reports-row]').forEach(function(tr){
        tr.addEventListener('click', function(event){
          var row = pageRows[Number(tr.getAttribute('data-reports-row'))];
          if (!row) return;
          selectedReportId = row.id;
          reportsRecipientPage = 1;
          updateReportsScreen();
        });
      });
      setReportsMessage('Zeige ' + (start + 1) + ' bis ' + end + ' von ' + rows.length + ' Einträgen');
    }
    setText('[data-reports="session-context"]', rows.length ? rows.length + ' Versandvorgänge' : 'Noch keine Versandvorgänge');
    setText('[data-reports="page-current"]', String(reportsPage));
    var reportPageSize = document.querySelector('[data-reports="page-size"]');
    if (reportPageSize) reportPageSize.value = String(reportsPageSize);
    var prev = document.querySelector('[data-reports-action="page-prev"]');
    var next = document.querySelector('[data-reports-action="page-next"]');
    if (prev) prev.disabled = reportsPage <= 1;
    if (next) next.disabled = reportsPage >= totalPages;
  }
  function reportRecipientRows(){
    var row = selectedReportRow();
    return row ? row.recipients.slice() : [];
  }
  function reportRecipientFilterKey(row){
    var status = String(row && row.status || '');
    var validation = row && row.email_validation || {};
    if (status === 'Gesendet') return 'sent';
    if (validation.code === 'missing' || status === 'Keine E-Mail') return 'missing';
    if (validation.sendable === false || status === 'Fehler' || status === 'Keine Dateien') return 'failed';
    return 'ready';
  }
  function reportRecipientStatusLabel(row){
    var status = String(row && row.status || '');
    return {
      'Gesendet': 'Gesendet',
      'Dry-Run': 'Vorbereitet',
      'Bereit': 'Versandbereit',
      'Wird gesendet': 'Wird gesendet',
      'Wartet': 'Wartet',
      'Keine E-Mail': 'Nicht gesendet',
      'Doppelte E-Mail': 'Doppelte E-Mail',
      'Ungültige E-Mail': 'Ungültige E-Mail',
      'Ungültige Zeichen': 'Ungültige Zeichen',
      'Ungültiges Format': 'Ungültiges Format',
      'Domain nicht gefunden': 'Domain nicht gefunden',
      'Keine MX-Einträge': 'Keine MX-Einträge',
      'Keine Dateien': 'Nicht versendbar',
      'Fehler': 'Fehler'
    }[status] || (status || 'Versandbereit');
  }
  function reportRecipientHint(row){
    var validation = row && row.email_validation || {};
    if (row && row.error) return String(row.error);
    if (validation.hint) return String(validation.hint);
    var status = String(row && row.status || '');
    if (status === 'Keine E-Mail') return 'E-Mail-Adresse fehlt';
    if (status === 'Doppelte E-Mail') return 'Diese E-Mail-Adresse ist mehreren Mitarbeitern zugeordnet';
    if (status === 'Keine Dateien') return 'Abrechnung fehlt';
    if (status === 'Fehler') return 'Versand prüfen';
    return '-';
  }
  function renderReportRecipients(){
    var tbody = document.querySelector('[data-reports-recipients="body"]');
    if (!tbody) return;
    var allRows = reportRecipientRows();
    var counts = { all: allRows.length, sent: 0, ready: 0, missing: 0, failed: 0 };
    allRows.forEach(function(row){ counts[reportRecipientFilterKey(row)] += 1; });
    Object.keys(counts).forEach(function(key){
      setText('[data-reports-recipient-count="' + key + '"]', counts[key]);
    });
    var selected = selectedReportRow();
    setText('[data-reports-recipients="context"]', allRows.length
      ? String(selected && selected.companyName || 'Aktiver Mandant') + ' · ' + allRows.length + ' Einträge'
      : 'Noch keine Versanddaten');

    var rows = allRows.filter(function(row){
      if (reportsRecipientFilter !== 'all' && reportRecipientFilterKey(row) !== reportsRecipientFilter) return false;
      if (!reportsRecipientSearchQuery) return true;
      var validation = row.email_validation || {};
      return [row.employee, row.persnr, row.email, row.document, row.status, row.error, validation.label, validation.mx_status]
        .join(' ').toLowerCase().indexOf(reportsRecipientSearchQuery.toLowerCase()) !== -1;
    });
    var totalPages = Math.max(1, Math.ceil(rows.length / reportsRecipientPageSize));
    reportsRecipientPage = Math.max(1, Math.min(reportsRecipientPage, totalPages));
    var start = rows.length ? (reportsRecipientPage - 1) * reportsRecipientPageSize : 0;
    var end = Math.min(start + reportsRecipientPageSize, rows.length);
    var pageRows = rows.slice(start, end);
    if (!pageRows.length) {
      tbody.innerHTML = '<tr><td colspan="8"><div class="report-recipient-empty">' +
        (allRows.length ? 'Keine Empfänger für diesen Filter.' : 'Noch keine Empfängerdaten. Führen Sie zuerst eine Prüfung oder Versandvorbereitung aus.') +
        '</div></td></tr>';
    } else {
      tbody.innerHTML = pageRows.map(function(row){
        var email = String(row.email || '').trim();
        var status = String(row.status || 'Bereit');
        var validation = row.email_validation || {};
        var statusLabel = reportRecipientStatusLabel(row);
        var person = String(row.employee || '').trim() || '-';
        var persnr = String(row.persnr || '').trim();
        var validationLabel = String(validation.label || (email ? 'Keine Prüfdaten (alter Bericht)' : 'Fehlt'));
        var validationClass = validation.code === 'valid' ? 'ready' : 'warning';
        return '<tr>' +
          '<td><span class="report-recipient-person"><b title="' + escapeHtml(person) + '">' + escapeHtml(person) + '</b><small>' + escapeHtml(persnr || '-') + '</small></span></td>' +
          '<td title="' + escapeHtml(email || 'Keine E-Mail-Adresse') + '">' + escapeHtml(email || '-') + '</td>' +
          '<td title="' + escapeHtml(reportRecipientHint(row)) + '"><span class="report-recipient-check ' + validationClass + '"><span data-icon="' + (validationClass === 'ready' ? 'checkcircle' : 'warning') + '"></span>' + escapeHtml(validationLabel) + '</span></td>' +
          '<td>' + escapeHtml(validation.mx_status || '-') + '</td>' +
          '<td>' + escapeHtml(validation.checked_at ? reportDate(validation.checked_at) : '-') + '</td>' +
          '<td><span class="state ' + shippingStatusClass(status) + '">' + escapeHtml(statusLabel) + '</span></td>' +
          '<td title="' + escapeHtml(row.document || '-') + '">' + escapeHtml(row.document || '-') + '</td>' +
          '<td title="' + escapeHtml(reportRecipientHint(row)) + '">' + escapeHtml(reportRecipientHint(row)) + '</td>' +
        '</tr>';
      }).join('');
    }
    setText('[data-reports-recipients="footer"]', rows.length ? 'Zeige ' + (start + 1) + ' bis ' + end + ' von ' + rows.length + ' Einträgen' : '0 Einträge');
    setText('[data-reports-recipients="page-current"]', String(reportsRecipientPage));
    var recipientPageSize = document.querySelector('[data-reports-recipients="page-size"]');
    if (recipientPageSize) recipientPageSize.value = String(reportsRecipientPageSize);
    var previous = document.querySelector('[data-reports-action="recipient-page-prev"]');
    var next = document.querySelector('[data-reports-action="recipient-page-next"]');
    if (previous) previous.disabled = reportsRecipientPage <= 1;
    if (next) next.disabled = reportsRecipientPage >= totalPages;
    document.querySelectorAll('[data-reports-recipient-filter]').forEach(function(button){
      button.classList.toggle('active', button.getAttribute('data-reports-recipient-filter') === reportsRecipientFilter);
    });
  }
  function reportPeriodLabel(){
    return { latest: 'Letzter Versand', month: 'Dieser Monat', '7d': 'Letzte 7 Tage', '30d': 'Letzte 30 Tage', all: 'Gesamter Zeitraum' }[reportsPeriodFilter];
  }
  function updateReportsScreen(){
    var filteredRows = filteredReportRows();
    var selected = selectedReportRow();
    if (!filteredRows.length) {
      selected = null;
      selectedReportId = '';
      selectedReportKind = '';
      reportsRecipientPage = 1;
    } else if (!selected || !filteredRows.some(function(row){ return row.id === selected.id; })) {
      selected = filteredRows[0];
      selectedReportId = selected ? selected.id : '';
      selectedReportKind = '';
      reportsRecipientPage = 1;
    }
    var metrics = reportMetricValues(selected);
    var periodLabel = reportPeriodLabel();
    var contextLabel = selected ? selected.companyName + ' · ' + selected.created : periodLabel;
    setText('[data-reports-metric="sent"]', metrics.sent);
    setText('[data-reports-metric="missing-email"]', metrics.missingEmail);
    setText('[data-reports-metric="employees"]', metrics.employees);
    setText('[data-reports-metric="failed"]', metrics.failed);
    setText('[data-reports-metric="rate"]', metrics.rate + '%');
    setText('[data-reports-metric="sent-label"]', metrics.hasData ? contextLabel : 'Noch kein Versand durchgeführt');
    setText('[data-reports-metric="missing-email-label"]', metrics.hasData ? (metrics.missingEmail ? 'Nicht versandfähig' : 'Keine fehlenden Adressen') : 'Keine Versanddaten');
    setText('[data-reports-metric="employees-label"]', metrics.hasData ? contextLabel : 'Keine Versanddaten');
    setText('[data-reports-metric="failed-label"]', metrics.failed ? 'Bitte prüfen' : 'Keine Fehler');
    setText('[data-reports-metric="rate-label"]', metrics.hasData ? metrics.sent + ' von ' + metrics.employees : 'Keine Versanddaten');
    setText('[data-reports="period-label"]', periodLabel);
    setText('[data-reports="type-label"]', { all: 'Alle Typen', sent: 'Gesendet', prepared: 'Vorbereitet' }[reportsTypeFilter] || 'Alle Typen');
    setText('[data-reports="status-label"]', { all: 'Alle Status', completed: 'Abgeschlossen', prepared: 'Vorbereitet', error: 'Fehler' }[reportsStatusFilter] || 'Alle Status');
    setText('[data-reports="filter-label"]', reportsReadyOnly ? 'Nur erstellt' : 'Filter');
    document.querySelectorAll('[data-reports-action="period"]').forEach(function(button){ button.classList.toggle('active', reportsPeriodFilter !== 'all'); });
    document.querySelectorAll('[data-reports-action="type"]').forEach(function(button){ button.classList.toggle('active', reportsTypeFilter !== 'all'); });
    document.querySelectorAll('[data-reports-action="status"]').forEach(function(button){ button.classList.toggle('active', reportsStatusFilter !== 'all'); });
    document.querySelectorAll('[data-reports-action="toggle-ready"]').forEach(function(button){ button.classList.toggle('active', reportsReadyOnly); });
    renderReportsTable();
    applyReportDetail(selected);
    renderReportRecipients();
  }
  function exportReportsCsv(includeAll){
    var rows = includeAll ? reportRows() : filteredReportRows();
    var headers = ['Datum', 'Mandant', 'Status', 'Mitarbeiter', 'Ohne E-Mail', 'Gesendet', 'Fehler', 'Run-ID'];
    var csvRows = [headers].concat(rows.map(function(row){
      return [row.created, row.companyName, row.status, Math.max(row.metrics.employees, row.metrics.processed, row.recipients.length), row.metrics.missing_email, row.metrics.sent, Math.max(row.metrics.failed, row.metrics.errors), row.runId];
    }));
    var csv = csvRows.map(function(row){
      return row.map(function(cell){ return '"' + String(cell === undefined || cell === null ? '' : cell).replace(/"/g, '""') + '"'; }).join(';');
    }).join('\n');
    var companyId = latestReportsState && latestReportsState.company && latestReportsState.company.id || 'mandant';
    var filename = 'lohnmail_berichte_' + String(companyId).replace(/[^a-zA-Z0-9_-]/g, '_') + '_' + new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19) + '.csv';
    var bridge = window.lohnmailBridge;
    if (bridge && bridge.exportReportsCsv) {
      bridge.exportReportsCsv(csv, filename, function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          setReportsMessage(result.ok ? 'Export gespeichert: ' + result.path : (result.message || 'Export fehlgeschlagen'));
        } catch (error) { setReportsMessage('Export fehlgeschlagen'); }
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
    if (action === 'export-csv' || action === 'export-all-csv') return exportReportsCsv(action === 'export-all-csv');
    if (action === 'type') {
      reportsTypeFilter = { all: 'sent', sent: 'prepared', prepared: 'all' }[reportsTypeFilter] || 'all';
      reportsPage = 1;
      return updateReportsScreen();
    }
    if (action === 'status') {
      reportsStatusFilter = { all: 'completed', completed: 'prepared', prepared: 'error', error: 'all' }[reportsStatusFilter] || 'all';
      reportsPage = 1;
      return updateReportsScreen();
    }
    if (action === 'toggle-ready') {
      reportsReadyOnly = !reportsReadyOnly;
      reportsPage = 1;
      return updateReportsScreen();
    }
    if (action === 'period') {
      reportsPeriodFilter = { latest: 'month', month: '7d', '7d': '30d', '30d': 'all', all: 'latest' }[reportsPeriodFilter] || 'latest';
      reportsPage = 1;
      return updateReportsScreen();
    }
    if (action === 'page-prev' || action === 'page-next') {
      reportsPage += action === 'page-next' ? 1 : -1;
      return renderReportsTable();
    }
    if (action === 'recipient-page-prev' || action === 'recipient-page-next') {
      reportsRecipientPage += action === 'recipient-page-next' ? 1 : -1;
      return renderReportRecipients();
    }
    if (action === 'detail-close') {
      var detail = document.querySelector('.report-details');
      var reportsGrid = document.querySelector('.reports-grid');
      if (detail) detail.hidden = true;
      if (reportsGrid) reportsGrid.classList.add('detail-hidden');
      return;
    }
    if (action === 'open-selected') return openReportEntry();
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
  function activeCompanyId(){
    return String((latestCompanyState && latestCompanyState.selected_company_id) || '').trim();
  }
  function workflowStateMatchesActiveCompany(state){
    var activeId = activeCompanyId();
    var stateId = String(state && state.company && state.company.id || '').trim();
    return !activeId || !stateId || activeId === stateId;
  }
  function resetWorkflowUiForCompanyChange(){
    latestProcessingState = null;
    latestValidationState = null;
    latestShippingState = null;
    latestReportsState = null;
    selectedReportId = '';
    selectedReportKind = '';
    selectedShippingPersnr = {};
    shippingSelectionDirty = false;
    shippingTerminalState = null;
    resetShippingLiveProgress();
    latestShippingSendPreview = null;
    currentValidationPage = 1;
    currentShippingPage = 1;
    closeShippingSendModal();
    applyValidationState({ ready: false, company: { id: '', name: '' }, summary: {}, filters: {}, rows: [], reports: {} });
    applyShippingState({ company: { id: '', name: '' }, status: {}, metrics: {}, rows: [], reports: {} });
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
    if (status === 'device_mismatch') {
      return { level: 'error', title: 'Anderer Computer erkannt', text: 'Diese Lizenz ist an einen anderen Computer gebunden. Bitte wenden Sie sich an den LohnMail-Support.' };
    }
    if (status === 'past_due' || status === 'unpaid') {
      return { title: 'Lizenzzahlung offen', text: 'Bitte offene Rechnung begleichen oder Zahlungsdaten im Kundenportal prüfen.' };
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
      warnings.push({ level: 'warning', title: 'E-Mail-Versand nicht konfiguriert', text: 'E-Mail-Versand ist erst nach SMTP- oder Outlook-Classic-Konfiguration möglich.', action: 'open-settings' });
    }
    if (workflowWarnings && license && !licenseIsUsable(license)) {
      var licenseWarning = licenseWarningText(license);
      warnings.push({ level: licenseWarning.level || 'warning', title: licenseWarning.title, text: licenseWarning.text, action: 'open-license' });
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
    if (updateIsAvailable(latestUpdateState)) {
      var mandatoryUpdate = updateIsMandatory(latestUpdateState);
      warnings.push({
        level: mandatoryUpdate ? 'error' : 'info',
        title: mandatoryUpdate ? 'Kritisches Update erforderlich' : 'Update verfügbar',
        text: mandatoryUpdate
          ? 'Dieses Update behebt eine kritische Sicherheitslücke oder technische Inkompatibilität.'
          : ((latestUpdateState.available_version
            ? 'Version ' + latestUpdateState.available_version
            : 'Eine neue Version') + ' kann heruntergeladen werden.'),
        action: 'open-updates'
      });
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
    if (action === 'open-updates') {
      setPage('Einstellungen');
      activateSettingsTab('updates');
    }
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
          resetWorkflowUiForCompanyChange();
          loadProcessingState();
          loadValidationState();
          loadShippingState();
          loadMassMessageState();
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
    var mode = String(period.mode || 'automatic_current_month');
    var date = new Date();
    var label = 'Automatisch';
    var month;
    var year;
    if (mode === 'manual') {
      label = 'Manuell';
      month = Number(period.month || 0);
      year = Number(period.year || 0);
      if (!month || !year) return label;
    } else {
      if (mode === 'automatic_previous_month') date.setMonth(date.getMonth() - 1);
      month = date.getMonth() + 1;
      year = date.getFullYear();
    }
    return label + ' · ' + String(month).padStart(2, '0') + '.' + year;
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
    setText('[data-company="detail-name"]', state.selected_company_name || '-');
    setText('[data-company="detail-id"]', state.selected_company_id || '-');
    setPathText('[data-company="detail-excel"]', selectedExcel.path || '-');
    setPathText('[data-company="detail-output"]', output.path || '-');
    setText('[data-company="detail-period"]', formatCompanyPeriod(state.period));
    setText('[data-company="detail-mail-mode"]', (smtp.scope === 'custom' ? 'Eigene SMTP' : ('Global ' + (smtp.mode || 'smtp'))));
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
    document.querySelectorAll('[data-company-action="delete-company"]').forEach(function(button){
      button.disabled = !state.selected_company_id || (state.companies || []).length <= 1;
      button.title = button.disabled
        ? 'Der letzte Mandant kann nicht gelöscht werden.'
        : 'Aktiven Mandant löschen';
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
    if (action === 'edit-company') {
      var editCard = document.querySelector('[data-company-edit-card]');
      var nameField = companyEditField('name');
      if (editCard) editCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (nameField) setTimeout(function(){ nameField.focus(); nameField.select(); }, 350);
      setCompanyMessage('Änderungen unten bearbeiten und anschließend speichern.');
      return;
    }
    if (action === 'select-company' && bridge.selectCompany) {
      var previousId = activeCompanyId();
      bridge.selectCompany(value || '', function(payload){
        var state = consumeCompanyPayload(payload);
        if (!state || state.ok === false) {
          setCompanyMessage((state && state.message) || 'Mandant konnte nicht gewechselt werden.');
          return;
        }
        if (previousId !== String(state.selected_company_id || '').trim()) {
          resetWorkflowUiForCompanyChange();
        }
        loadProcessingState();
        loadValidationState();
        loadShippingState();
        loadMassMessageState();
        loadDashboardState();
        loadReportsState();
        setCompanyMessage(state.message || 'Aktiver Mandant wurde gewechselt.');
      });
      return;
    }
    if (action === 'choose-excel' && bridge.chooseCompanyExcelInput) {
      bridge.chooseCompanyExcelInput(function(payload){
        consumeCompanyPayload(payload);
        resetWorkflowUiForCompanyChange();
        loadProcessingState();
        loadValidationState();
        loadShippingState();
        loadMassMessageState();
        loadDashboardState();
        loadReportsState();
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
    if (action === 'delete-company' && bridge.deleteCompany) {
      var companyId = activeCompanyId();
      var companyName = latestCompanyState && latestCompanyState.selected_company_name
        ? latestCompanyState.selected_company_name
        : companyId;
      if (!companyId) {
        setCompanyMessage('Bitte zuerst einen Mandant auswählen.');
        return;
      }
      openAppDialog({
        kicker: 'Mandantenverwaltung',
        title: 'Mandant löschen?',
        message: 'Mandant "' + companyName + '" wird aus LohnMail entfernt. Excel- und Ausgabedateien auf dem Datenträger bleiben erhalten.',
        confirmLabel: 'Mandant löschen',
        cancelLabel: 'Abbrechen',
        onCancel: function(){ setCompanyMessage('Löschen wurde abgebrochen.'); },
        onConfirm: function(){
          setCompanyMessage('Mandant wird gelöscht...');
          bridge.deleteCompany(companyId, function(payload){
            var state = consumeCompanyPayload(payload);
            if (!state || state.ok === false) {
              setCompanyMessage((state && state.message) || 'Mandant konnte nicht gelöscht werden.');
              return;
            }
            resetWorkflowUiForCompanyChange();
            loadProcessingState();
            loadValidationState();
            loadShippingState();
            loadMassMessageState();
            loadDashboardState();
            loadReportsState();
            loadSettingsState();
            setCompanyMessage(state.message || 'Mandant wurde gelöscht.');
          });
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
    setText('[data-license="key-label"]', state.key_label || 'Lizenzschlüssel');
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
    applyLicenseeState(state.licensee || {});

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
  function collectLicenseeForm(){
    var payload = {};
    document.querySelectorAll('[data-licensee-field]').forEach(function(field){
      payload[field.getAttribute('data-licensee-field')] = field.value || '';
    });
    return payload;
  }
  function applyLicenseeState(licensee){
    licensee = licensee || {};
    document.querySelectorAll('[data-licensee-field]').forEach(function(field){
      var key = field.getAttribute('data-licensee-field');
      field.value = licensee[key] || '';
    });
  }
  function saveLicensee(callback){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.saveLicenseeState) {
      setLicenseMessage('Lizenznehmer kann im Bridge nicht gespeichert werden.');
      if (callback) callback(false);
      return;
    }
    bridge.saveLicenseeState(JSON.stringify(collectLicenseeForm()), function(payload){
      try {
        var result = JSON.parse(payload || '{}');
        if (result.state) applyLicenseState(result.state);
        setLicenseMessage(result.message || (result.ok ? 'Lizenznehmer wurde gespeichert.' : 'Lizenznehmer konnte nicht gespeichert werden.'));
        if (callback) callback(!!result.ok);
      } catch (error) {
        setLicenseMessage('Lizenznehmer konnte nicht gespeichert werden.');
        if (callback) callback(false);
      }
    });
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
  function openLicensePaymentModal(){
    var modal = document.querySelector('[data-license-payment-modal]');
    if (modal) modal.hidden = false;
  }
  function closeLicensePaymentModal(){
    var modal = document.querySelector('[data-license-payment-modal]');
    if (modal) modal.hidden = true;
  }
  function closeLicenseValidationModal(){
    var modal = document.querySelector('[data-license-validation-modal]');
    if (modal) modal.hidden = true;
  }
  function validateLicenseeForPayment(method){
    var values = collectLicenseeForm();
    var required = [
      {key: 'name', label: 'Firma / Kanzlei'},
      {key: 'email', label: 'E-Mail'}
    ];
    if (method === 'invoice') required.push({key: 'address', label: 'Anschrift'});
    document.querySelectorAll('[data-licensee-field]').forEach(function(field){
      field.classList.remove('licensee-field-missing');
    });
    return required.filter(function(item){ return !String(values[item.key] || '').trim(); });
  }
  function showLicenseValidationModal(method, missing){
    closeLicensePaymentModal();
    var modal = document.querySelector('[data-license-validation-modal]');
    var message = document.querySelector('[data-license-validation-message]');
    var list = document.querySelector('[data-license-validation-list]');
    if (message) {
      message.textContent = method === 'invoice'
        ? 'Für die Zahlung auf Rechnung werden folgende Rechnungsdaten benötigt:'
        : 'Bevor die Kartenzahlung geöffnet werden kann, ergänzen Sie bitte:';
    }
    if (list) list.innerHTML = missing.map(function(item){ return '<li>' + escapeHtml(item.label) + '</li>'; }).join('');
    missing.forEach(function(item){
      var field = document.querySelector('[data-licensee-field="' + item.key + '"]');
      if (field) field.classList.add('licensee-field-missing');
    });
    if (modal) modal.hidden = false;
    setLicenseMessage('Bitte zuerst die fehlenden Lizenznehmerdaten ergänzen.');
  }
  function focusFirstMissingLicenseeField(){
    closeLicenseValidationModal();
    var field = document.querySelector('.licensee-field-missing');
    if (!field) return;
    field.scrollIntoView({behavior: 'smooth', block: 'center'});
    window.setTimeout(function(){ field.focus(); }, 350);
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
    if (action === 'buy') {
      openLicensePaymentModal();
      return;
    }
    if (action === 'buy-card' && window.lohnmailBridge && window.lohnmailBridge.buyLicense) {
      var missingCardFields = validateLicenseeForPayment('card');
      if (missingCardFields.length) {
        showLicenseValidationModal('card', missingCardFields);
        return;
      }
      closeLicensePaymentModal();
      setLicenseMessage('Lizenznehmer wird gespeichert...');
      saveLicensee(function(saved){
        if (!saved) return;
        setLicenseMessage('Kartenzahlung wird geöffnet...');
        window.lohnmailBridge.buyLicense(function(payload){
          try {
            var result = JSON.parse(payload || '{}');
            if (result.state) applyLicenseState(result.state);
            setLicenseMessage(result.ok
              ? licenseMessageFromState(result.state, result.message || 'Kartenzahlung wurde geöffnet.')
              : (result.message || 'Kartenzahlung konnte nicht geöffnet werden.'));
          } catch (error) {
            setLicenseMessage('Kartenzahlung konnte nicht geöffnet werden.');
          }
        });
      });
      return;
    }
    if (action === 'buy-invoice' && window.lohnmailBridge && window.lohnmailBridge.buyLicenseByInvoice) {
      var missingInvoiceFields = validateLicenseeForPayment('invoice');
      if (missingInvoiceFields.length) {
        showLicenseValidationModal('invoice', missingInvoiceFields);
        return;
      }
      closeLicensePaymentModal();
      setLicenseMessage('Rechnungsdaten werden gespeichert...');
      saveLicensee(function(saved){
        if (!saved) return;
        setLicenseMessage('Rechnungszahlung wird eingerichtet...');
        window.lohnmailBridge.buyLicenseByInvoice(function(payload){
          try {
            var result = JSON.parse(payload || '{}');
            if (result.state) applyLicenseState(result.state);
            setLicenseMessage(
              result.ok
                ? (result.message || 'Rechnungszahlung wurde eingerichtet.')
                : (result.message || 'Rechnungszahlung konnte nicht eingerichtet werden.')
            );
          } catch (error) {
            setLicenseMessage('Rechnungszahlung konnte nicht eingerichtet werden.');
          }
        });
      });
      return;
    }
    if (action === 'save-licensee') {
      setLicenseMessage('Lizenznehmer wird gespeichert...');
      saveLicensee();
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
  function setSettingsSecurityMessage(message){
    setText('[data-settings="security-message"]', message);
  }
  function mailTextToHtml(value){
    var text = String(value === undefined || value === null ? '' : value)
      .replace(/\r\n?/g, '\n');
    if (!text) return '';
    return '<div>' + escapeHtml(text).replace(/\n/g, '<br>') + '</div>';
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
    updateOutlookAccountControl();
    updateWarningCenter();
  }
  function updateOutlookAccountControl(){
    var modeField = document.querySelector('[data-settings-field="mail_mode"]');
    var smtpLabel = document.querySelector('[data-settings-smtp-from]');
    var outlookLabel = document.querySelector('[data-settings-outlook-from]');
    var input = document.querySelector('[data-settings-field="smtp.from_email"]');
    var select = document.querySelector('[data-outlook-account-select]');
    var isOutlook = !!modeField && modeField.value === 'outlook';
    if (smtpLabel) smtpLabel.hidden = isOutlook;
    if (outlookLabel) outlookLabel.hidden = !isOutlook;
    if (!select) return;
    var current = String(input && input.value || '');
    select.innerHTML = '<option value="">Outlook-Konto auswählen…</option>' + outlookAccounts.map(function(account){
      var value = account.smtp_address || account.identifier || '';
      var label = account.label || value;
      return '<option value="' + escapeHtml(value) + '">' + escapeHtml(label) + '</option>';
    }).join('');
    if (current && !outlookAccounts.some(function(account){ return (account.smtp_address || account.identifier || '') === current; })) {
      select.innerHTML += '<option value="' + escapeHtml(current) + '">' + escapeHtml(current) + ' (gespeichert)</option>';
    }
    select.value = current;
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
    if (action === 'save-security') {
      saveSettingsForm(setSettingsSecurityMessage, 'PDF-Verschlüsselung wurde gespeichert.');
      return;
    }
    if (action === 'test-mail') {
      testMailConnectionAfterSave();
      return;
    }
    if (action === 'load-outlook') {
      if (!bridge || !bridge.getOutlookAccounts) {
        setSettingsMailMessage('Outlook-Classic-Konten sind im Bridge nicht verfügbar.');
        return;
      }
      bridge.getOutlookAccounts(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          if (!result.ok) {
            setSettingsMailMessage(result.message || 'Outlook-Classic-Konten konnten nicht geladen werden.');
            return;
          }
          var accounts = result.accounts || [];
          outlookAccounts = accounts;
          updateOutlookAccountControl();
          setSettingsMailMessage(accounts.length ? 'Outlook-Konten wurden geladen. Bitte das Absenderkonto auswählen.' : 'Outlook Classic ist erreichbar. Unter macOS steht keine Kontenliste zur Verfügung; Outlook verwendet das dort konfigurierte Absenderkonto.');
        } catch (error) {
          setSettingsMailMessage('Outlook-Classic-Konten konnten nicht verarbeitet werden.');
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
  function setMassPreviewText(key, value){
    var node = document.querySelector('[data-mass-preview="' + key + '"]');
    if (!node) return;
    if ('value' in node) node.value = value || '';
    else node.textContent = value || '';
  }
  function closeMassSendModal(){
    var modal = document.querySelector('[data-mass-send-modal]');
    if (modal) modal.hidden = true;
  }
  function openMassSendPreview(){
    var state = latestMassMessageState || {};
    var preview = state.preview || {};
    var rows = preview.rows || [];
    if (!preview.ready || !rows.length) {
      setMassMessage('Bitte zuerst eine gültige Vorschau laden.');
      return;
    }

    setMassPreviewText('company', preview.company_name || (state.company && state.company.name) || '-');
    setMassPreviewText('total', String(preview.total_count || rows.length));
    setMassPreviewText('mode', state.mail_mode || 'smtp');
    setMassPreviewText('subject', preview.subject_preview || massSubject());
    setMassPreviewText('body', preview.body_preview || massBody());
    setMassPreviewText('message', 'Bitte Empfänger, Betreff und Nachricht vor dem Senden prüfen.');

    var tbody = document.querySelector('[data-mass-preview="rows"]');
    if (tbody) {
      tbody.innerHTML = rows.map(function(row){
        var name = [row.Name, row.Vorname].filter(Boolean).join(', ') || '-';
        return '<tr>' +
          '<td>' + escapeHtml(row.PersNr || '-') + '</td>' +
          '<td>' + escapeHtml(name) + '</td>' +
          '<td>' + escapeHtml(row.Email || '-') + '</td>' +
          '</tr>';
      }).join('');
    }

    var modal = document.querySelector('[data-mass-send-modal]');
    if (modal) modal.hidden = false;
  }
  function startMassMessageSend(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.startMassMessage) {
      setMassPreviewText('message', 'Bridge ist noch nicht bereit.');
      return;
    }
    var confirmButton = document.querySelector('[data-mass-send-action="confirm"]');
    if (confirmButton) confirmButton.disabled = true;
    setMassPreviewText('message', 'Nachricht-Versand wird gestartet...');
    setMassMessage('Nachricht-Versand wird gestartet...');
    bridge.startMassMessage(massSubject(), massBody(), function(payload){
      consumeMassMessagePayload(payload);
      closeMassSendModal();
      if (confirmButton) confirmButton.disabled = false;
    });
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
      rows.map(function(row){
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
      sendButton.title = preview.ready ? 'Öffnet die finale Prüfung vor dem Versand.' : 'Bitte zuerst Vorschau laden.';
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
      openMassSendPreview();
      return;
    }
  }
  var helpArticles = [
    {
      id: 'first-run', topic: 'start', category: 'Erste Schritte', tag: 'green', updated: '13.07.2026',
      title: 'Erster vollständiger Lauf: vom Mandanten bis zum Prüfbericht',
      summary: 'Diese Anleitung führt durch die sichere Grundeinrichtung und den ersten Prüflauf, ohne bereits E-Mails zu versenden.',
      keywords: 'start installation einrichtung mandant excel pdf workflow neuer lauf',
      sections: [
        {title: '1. Mandant auswählen oder anlegen', steps: ['Öffnen Sie Unternehmen und legen Sie den betreuten Mandanten mit Name und eindeutiger Mandanten-ID an.', 'Wählen Sie die zu diesem Mandanten gehörende Excel-Stammdatendatei aus und speichern Sie die Zuordnung.', 'Kontrollieren Sie im Header, dass der richtige aktive Mandant und „Excel bereit“ angezeigt werden.']},
        {title: '2. Eingaben in Verarbeitung festlegen', steps: ['Wählen Sie bei Lohnjournal entweder Ordner für bereits getrennte PDF-Dateien oder Gesamt-PDF für eine zusammengefasste Datei.', 'Prüfen Sie den automatisch geladenen Excel-Pfad des aktiven Mandanten.', 'Öffnen Sie bei Bedarf den festen Ausgabeordner und stellen Sie sicher, dass er beschreibbar ist.']},
        {title: '3. Prüfung ausführen', steps: ['Klicken Sie auf Verarbeitung starten. LohnMail prüft zunächst Eingaben und Zuordnungen.', 'Beobachten Sie Verarbeitungs-Status und Aktivitätsprotokoll. Bei Fehlern bleiben Sie auf der Seite und korrigieren die genannte Ursache.', 'Nach erfolgreichem Abschluss öffnen Sie Prüfung, lesen Warnungen und kontrollieren insbesondere Empfänger ohne E-Mail-Adresse.']},
        {title: '4. Erst danach Versand vorbereiten', text: ['Öffnen Sie Versand erst, wenn die Prüfergebnisse plausibel sind. Markieren Sie nur sendbare Empfänger, öffnen Sie die Vorschau und kontrollieren Sie Empfänger, Betreff, Text und Anhang.'], note: 'Ein Prüflauf sendet keine E-Mails. Der tatsächliche Versand startet erst nach der gesonderten Bestätigung im Versanddialog.'}
      ]
    },
    {
      id: 'company-setup', topic: 'start', category: 'Unternehmen', tag: 'neutral', updated: '13.07.2026',
      title: 'Mandanten verwalten und die richtige Excel-Datei zuordnen',
      summary: 'LohnMail trennt den Lizenznehmer von den betreuten Mandanten. Jeder Mandant kann eigene Stammdaten und optional eigene Mail-Einstellungen besitzen.',
      keywords: 'unternehmen mandant excel stammdaten wechseln kanzlei firma',
      sections: [
        {title: 'Mandant und Lizenznehmer sind nicht dasselbe', text: ['Der Lizenznehmer ist die Kanzlei oder Organisation, die LohnMail verwendet. Mandanten sind die Unternehmen, deren Abrechnungen bearbeitet werden. Eine Arbeitsplatzlizenz kann mehrere Mandanten verwalten.']},
        {title: 'Excel-Zuordnung', bullets: ['Ordnen Sie jedem Mandanten seine eigene Mitarbeiterliste zu.', 'Beim Wechsel des aktiven Mandanten wird dessen gespeicherte Excel-Datei in Verarbeitung geladen.', 'Fehlt die Datei oder wurde sie verschoben, zeigt der Header eine Warnung und der Prüflauf bleibt gesperrt.']},
        {title: 'Mandant wechseln', steps: ['Öffnen Sie die Mandantenauswahl rechts oben im Header.', 'Suchen Sie nach Name oder Mandanten-ID.', 'Wählen Sie den Mandanten und kontrollieren Sie den Excel-Status direkt unter seinem Namen.']},
        {title: 'Eigene Mail-Einstellungen', text: ['Standardmäßig verwendet ein Mandant die globalen E-Mail-Einstellungen. Unter Unternehmen können Sie auf eigene SMTP-Einstellungen umstellen, speichern und die Verbindung separat testen.']}
      ]
    },
    {
      id: 'pdf-input', topic: 'processing', category: 'Verarbeitung', tag: 'green', updated: '13.07.2026',
      title: 'PDF-Eingang wählen: Ordner oder Gesamt-PDF',
      summary: 'Der Eingabemodus muss zum ausgewählten Pfad passen. Ein Ordner ist keine Gesamt-PDF und eine einzelne Datei ist kein PDF-Ordner.',
      keywords: 'pdf ordner gesamt-pdf gesamt pdf falscher typ lohnjournal import',
      sections: [
        {title: 'Modus Ordner', text: ['Verwenden Sie Ordner, wenn die Abrechnungen bereits als einzelne PDF-Dateien vorliegen. Wählen Sie den Ordner, der die zu prüfenden Dokumente enthält.']},
        {title: 'Modus Gesamt-PDF', text: ['Verwenden Sie Gesamt-PDF, wenn alle Abrechnungen in einer einzelnen PDF-Datei zusammengefasst sind. Nach dem Umschalten muss eine echte PDF-Datei ausgewählt werden.']},
        {title: 'Status „Falscher Typ“', bullets: ['Im Modus Gesamt-PDF zeigt ein noch gespeicherter Ordnerpfad „Falscher Typ“.', 'Im Modus Ordner zeigt eine ausgewählte Einzeldatei ebenfalls „Falscher Typ“.', 'Wählen Sie nach dem Moduswechsel den Eingang erneut aus; dadurch wird der Pfad korrekt validiert.']},
        {title: 'Vor dem Start prüfen', bullets: ['Status des PDF-Eingangs: Bereit', 'Status der Excel-Datei: Bereit', 'Status des Ausgabeordners: Bereit', 'Aktiver Mandant im Header stimmt mit den Unterlagen überein']}
      ]
    },
    {
      id: 'processing-status', topic: 'processing', category: 'Verarbeitung', tag: 'green', updated: '13.07.2026',
      title: 'Verarbeitungs-Status und Aktivitätsprotokoll verstehen',
      summary: 'Statuskarte und Protokoll zeigen, was LohnMail gerade prüft, welche Eingaben erkannt wurden und an welcher Stelle ein Lauf abgebrochen ist.',
      keywords: 'verarbeitungs-status fortschritt aktivitätsprotokoll fehler warnung lauf',
      sections: [
        {title: 'Statusangaben', bullets: ['Aktueller Schritt beschreibt die laufende oder zuletzt abgeschlossene Phase.', 'Gesamtfortschritt zeigt den Ablauf in Prozent.', 'Mitarbeiter gesamt und Verarbeitet dienen der Vollständigkeitskontrolle.', 'Warnungen erlauben meist eine Fortsetzung; Fehler verhindern einen erfolgreichen Abschluss.']},
        {title: 'Aktivitätsprotokoll', text: ['Jeder relevante Eingabe-, Fortschritts-, Abschluss- und Fehlerzustand wird in der Sitzung protokolliert. Mit Alle anzeigen erweitern Sie die Liste; Weniger anzeigen reduziert sie wieder.']},
        {title: 'Bei einem Abbruch', steps: ['Lesen Sie die letzte rote oder orange Protokollzeile vollständig.', 'Korrigieren Sie nur die dort genannte Eingabe oder Installation.', 'Laden Sie die betroffene Datei neu und starten Sie die Prüfung erneut.']},
        {title: 'Typische Abhängigkeiten', bullets: ['PyMuPDF bzw. PyPDF2 für PDF-Verarbeitung', 'openpyxl für Excel-Dateien', 'Schreibbarer Ausgabeordner', 'Gültige Personalnummern für die Zuordnung']}
      ]
    },
    {
      id: 'validation-results', topic: 'validation', category: 'Prüfung', tag: 'violet', updated: '13.07.2026',
      title: 'Prüfergebnisse, Warnungen und kritische Fehler lesen',
      summary: 'Die Prüfung zeigt alle Mitarbeiter, nicht nur fehlerhafte Datensätze. Filter und Suche grenzen die Ansicht ein, ohne Ergebnisse zu verändern.',
      keywords: 'prüfung kritisch warnungen hinweise alle mitarbeiter keine email filter',
      sections: [
        {title: 'Bedeutung der Kategorien', bullets: ['Kritisch: Der Datensatz muss vor dem Versand korrigiert werden.', 'Warnung: Bitte prüfen; häufig fehlt eine E-Mail-Adresse oder eine Zuordnung ist unvollständig.', 'Hinweis: Information ohne unmittelbare Sperrwirkung.', 'OK: Für den Mitarbeiter wurden keine Auffälligkeiten gefunden.']},
        {title: 'Tabelle bedienen', bullets: ['Alle zeigt jeden geprüften Mitarbeiter.', 'Kritisch, Warnungen und Hinweise filtern nach Schweregrad.', 'Die Tabellensuche berücksichtigt Name, Personalnummer, E-Mail, Dokument und Beschreibung.', 'Gruppieren ordnet die sichtbaren Ergebnisse; Export übernimmt den aktuellen Filter und Suchbegriff.']},
        {title: 'Mitarbeiter ohne E-Mail', text: ['Diese Mitarbeiter bleiben in der Gesamtliste sichtbar und erscheinen unter Warnungen. Wenn der Sammelbericht erzeugt wurde, öffnet PDF ohne E-Mail die Datei ohne_email_gesamt.pdf.']},
        {title: 'Vor dem Versand', note: 'Kontrollieren Sie die Anzahl „versandbereit“ in der Toolbar. Nur Datensätze mit gültiger E-Mail-Adresse und passendem Dokument können für den Versand ausgewählt werden.'}
      ]
    },
    {
      id: 'validation-tools', topic: 'validation', category: 'Prüfung', tag: 'violet', updated: '13.07.2026',
      title: 'Suche, Filter, Gruppierung und CSV-Export in Prüfung',
      summary: 'Alle Tabellenwerkzeuge arbeiten auf dem aktuellen Prüfergebnis und helfen bei Kontrolle oder Weitergabe der sichtbaren Ansicht.',
      keywords: 'suche filter gruppierung csv export prüfbericht',
      sections: [
        {title: 'Suchen', text: ['Geben Sie einen Teil von Name, Personalnummer, E-Mail-Adresse, PDF-Dateiname oder Beschreibung ein. Die Treffer werden sofort aktualisiert.']},
        {title: 'Filtern und gruppieren', text: ['Wählen Sie zuerst den Schweregrad. Der zusätzliche Filter beschränkt die Ansicht auf Auffälligkeiten. Gruppieren fasst die Treffer nach ihrem Status zusammen.']},
        {title: 'Export', text: ['Export erstellt eine CSV-Datei aus der aktuell sichtbaren Auswahl. Aktiver Schweregrad, Suchtext und Zusatzfilter werden berücksichtigt. Prüfbericht exportieren öffnet den erzeugten Audit-Bericht.']},
        {title: 'Nichts gefunden', bullets: ['Suchfeld leeren', 'Auf Alle wechseln', 'Zusatzfilter deaktivieren', 'Prüfung erneut laden, wenn zuvor der Mandant gewechselt wurde']}
      ]
    },
    {
      id: 'shipping-safe', topic: 'shipping', category: 'Versand', tag: 'blue', updated: '13.07.2026',
      title: 'Versand sicher vorbereiten, kontrollieren und starten',
      summary: 'Der Versand besteht bewusst aus Auswahl, Vorbereitung, Vorschau und finaler Bestätigung. Keine dieser Kontrollen sollte übersprungen werden.',
      keywords: 'versand vorbereiten jetzt senden vorschau empfänger checkbox testversand',
      sections: [
        {title: '1. Empfänger auswählen', steps: ['Öffnen Sie den Filter Versandbereit.', 'Kontrollieren Sie Name, Personalnummer, E-Mail und Dokument.', 'Nutzen Sie die Kopf-Checkbox für alle sichtbaren sendbaren Einträge oder wählen Sie einzelne Mitarbeiter manuell.']},
        {title: '2. Versand vorbereiten', text: ['Versand vorbereiten erstellt die Warteschlange für die markierten Empfänger. Einträge ohne E-Mail-Adresse bleiben ausgeschlossen und können nicht versehentlich versendet werden.']},
        {title: '3. Vorschau prüfen', bullets: ['Empfängeradresse', 'Betreff und Nachrichtentext', 'Dateiname und Anzahl der Anhänge', 'Versandmethode SMTP oder Outlook Classic', 'Ausgewählter Mandant und Abrechnungszeitraum']},
        {title: '4. Final senden', text: ['Jetzt senden öffnet den abschließenden Bestätigungsdialog. Erst Versand starten löst die tatsächliche Übergabe an SMTP oder Outlook Classic aus.'], note: 'Für einen Funktionstest zunächst nur einen internen Empfänger markieren und Testversand verwenden.'}
      ]
    },
    {
      id: 'shipping-errors', topic: 'shipping', category: 'Fehlerbehebung', tag: 'orange', updated: '13.07.2026',
      title: 'Versandprobleme: Empfänger fehlen, Vorschau leer oder Verbindung fehlerhaft',
      summary: 'Die häufigsten Versandprobleme lassen sich auf fehlende Prüfergebnisse, nicht markierte Empfänger oder unvollständige Mail-Einstellungen zurückführen.',
      keywords: 'versand fehler smtp outlook vorschau leer keine empfänger warteschlange',
      sections: [
        {title: 'Liste ist leer', bullets: ['Prüfung muss für den aktiven Mandanten abgeschlossen sein.', 'Mindestens ein Mitarbeiter benötigt E-Mail-Adresse und zugeordnetes PDF.', 'Filter Alle oder Versandbereit wählen und Suchfeld leeren.']},
        {title: 'Vorschau ist deaktiviert', text: ['Markieren Sie mindestens einen sendbaren Eintrag. Nach Änderungen an der Auswahl muss der Versand gegebenenfalls erneut vorbereitet werden.']},
        {title: 'SMTP-Fehler', bullets: ['Server, Port und Sicherheit prüfen', 'Benutzername und Passwort neu speichern', 'Absenderadresse kontrollieren', 'Verbindung testen', 'Bei Microsoft 365 oder Gmail mögliche App-Passwörter bzw. Administrationsrichtlinien beachten']},
        {title: 'Outlook-Classic-Fehler', bullets: ['Versandmethode Outlook Classic wählen', 'Unter Windows Microsoft 365 Desktop, Outlook 2016, 2019 oder 2021 verwenden', 'Das neue Outlook für Windows wird nicht unterstützt; alternativ SMTP verwenden', 'Unter macOS eine Outlook-Version mit AppleScript-Unterstützung verwenden', 'Outlook-Konten laden', 'Absender E-Mail muss einem verfügbaren Outlook-Konto entsprechen']}
      ]
    },
    {
      id: 'reports-overview', topic: 'reports', category: 'Berichte', tag: 'green', updated: '13.07.2026',
      title: 'Berichte öffnen, unterscheiden und weiterverwenden',
      summary: 'LohnMail erzeugt getrennte Berichte für Prüfung, fehlende E-Mail-Adressen und Versand. Die Dateien liegen im Ausgabeordner des Laufs.',
      keywords: 'berichte audit_check ohne_email_gesamt send_report xlsx pdf export',
      sections: [
        {title: 'audit_check.xlsx', text: ['Enthält das Prüfergebnis mit erkannten Mitarbeitern, Status und Auffälligkeiten. Verwenden Sie diesen Bericht zur fachlichen Nachkontrolle und Dokumentation.']},
        {title: 'ohne_email_gesamt.pdf', text: ['Fasst die Abrechnungen der Mitarbeiter zusammen, für die keine nutzbare E-Mail-Adresse vorhanden ist. Die Datei ist für alternative interne Übergabe oder Ausdruck vorgesehen.']},
        {title: 'send_report.xlsx', text: ['Dokumentiert den Versandstatus je Empfänger. Nach einem Versand kontrollieren Sie hier erfolgreiche, übersprungene und fehlerhafte Einträge.']},
        {title: 'Berichte-Seite', bullets: ['Suche nach Dateiname oder Beschreibung', 'Filter nach Dateityp und Status', 'Datei direkt öffnen', 'Ausgabeordner öffnen', 'Nur tatsächlich erzeugte Dateien sind verfügbar']}
      ]
    },
    {
      id: 'mail-settings', topic: 'settings', category: 'Einstellungen', tag: 'neutral', updated: '28.08.2026',
      title: 'E-Mail-Verbindung mit SMTP oder Outlook Classic einrichten',
      summary: 'Konfigurieren Sie genau die Versandmethode, die auf dem Arbeitsplatz verwendet werden soll, speichern Sie und führen Sie anschließend den Verbindungstest aus.',
      keywords: 'smtp outlook port tls ssl passwort absender verbindung testen email',
      sections: [
        {title: 'SMTP einrichten', steps: ['Einstellungen > E-Mail öffnen und Versandmethode SMTP wählen.', 'SMTP Server, Port, Sicherheit, Benutzer, Passwort, Absender E-Mail und Absender Name eintragen.', 'Als Absender E-Mail immer eine vollständige Adresse mit @ und Domain verwenden, zum Beispiel lohnbuchhaltung@firma.de.', 'E-Mail speichern klicken.', 'Verbindung testen ausführen und das Ergebnis unter den Feldern lesen.']},
        {title: 'Typische SMTP-Werte', bullets: ['TLS verwendet häufig Port 587.', 'SSL verwendet häufig Port 465.', 'SMTP Benutzer ist meistens die vollständige E-Mail-Adresse.', 'Absender E-Mail darf nicht nur aus dem Postfachnamen bestehen; lohnbuchhaltung ohne @firma.de wird vom Server häufig abgelehnt.', 'Die verbindlichen Werte liefert der E-Mail-Anbieter oder Administrator.', 'Das Passwortfeld leer lassen, wenn ein bereits gespeichertes Passwort beibehalten werden soll.']},
        {title: 'Outlook Classic einrichten', steps: ['Versandmethode Outlook Classic wählen.', 'Unter Windows Microsoft 365 Desktop, Outlook 2016, 2019 oder 2021 öffnen und das gewünschte Konto anmelden.', 'Das neue Outlook für Windows wird nicht unterstützt; verwenden Sie dafür SMTP.', 'Unter macOS ist eine Outlook-Version mit AppleScript-Unterstützung erforderlich.', 'Outlook-Konten laden klicken.', 'Als Absender E-Mail eines der erkannten Konten verwenden und speichern.']},
        {title: 'Globale oder mandanteneigene Einstellungen', text: ['Globale Einstellungen gelten für alle Mandanten, die unter Unternehmen „Globale E-Mail Einstellungen verwenden“ ausgewählt haben. „Eigene SMTP Einstellungen“ überschreibt die globalen SMTP-Daten nur für den aktiven Mandanten. Nach dem Umschalten immer „Änderungen speichern“ klicken und anschließend „Mandant SMTP testen“ ausführen. Ein nur im Auswahlfeld angezeigter Wechsel ist noch nicht gespeichert.']},
        {title: 'Vor dem echten Versand', bullets: ['Nach jeder Änderung an Versandmethode, SMTP-Server, Benutzer oder Absender die E-Mail-Einstellungen speichern.', 'Versand für den aktiven Mandanten erneut vorbereiten, damit Vorschau und echter Versand dieselben Einstellungen verwenden.', 'Im Versandbericht bedeutet nur der Status „Gesendet“, dass der SMTP-Server die Nachricht angenommen hat. „Fehler“ enthält die konkrete Ablehnung des Servers.', 'Eine erfolgreiche Verbindungsprüfung bestätigt Anmeldung und Erreichbarkeit, aber noch nicht die spätere Zustellung an das Empfängerpostfach.']}
      ]
    },
    {
      id: 'templates-period', topic: 'settings', category: 'Einstellungen', tag: 'neutral', updated: '13.07.2026',
      title: 'Abrechnungszeitraum, E-Mail-Vorlagen und PDF-Passwort',
      summary: 'Diese Einstellungen steuern die sichtbare Periode, den Nachrichtentext beim Lohnversand und optional den Schutz erzeugter PDFs.',
      keywords: 'vorlage betreff text html zeitraum monat jahr pdf passwort sicherheit',
      sections: [
        {title: 'Abrechnungszeitraum', text: ['Automatisch verwendet den aktuellen Monat. Manuell erlaubt Monat und Jahr fest vorzugeben. Speichern Sie die Änderung vor dem nächsten Lauf.']},
        {title: 'E-Mail-Vorlagen', bullets: ['Betreff für den Lohnabrechnungsversand', 'Text als zuverlässige Standarddarstellung', 'Optionaler HTML-Text für formatierte Nachrichten', 'Vorlage speichern, bevor eine neue Versandvorschau erzeugt wird']},
        {title: 'PDF-Passwort', text: ['Unter Sicherheit kann ein Passwortschema aus Präfix und Suffix aktiviert werden. Verwenden Sie nur ein intern abgestimmtes Schema und testen Sie eine erzeugte Datei, bevor Sie den Massenversand starten.']},
        {title: 'Benachrichtigungen', text: ['Kritische Hinweise bleiben immer sichtbar. Weitere Workflow-, Prüfungs-, Versand- und Berichtshinweise sowie das automatische Öffnen beim Start können separat gesteuert werden.']}
      ]
    },
    {
      id: 'license-help', topic: 'settings', category: 'Lizenzen', tag: 'green', updated: '13.07.2026',
      title: 'Testphase, Lizenzkauf, Aktivierung und Kundenportal',
      summary: 'Die Lizenz ist an den Lizenznehmer und Arbeitsplatz gebunden, nicht an einen einzelnen betreuten Mandanten. Mandanten können innerhalb des erlaubten Umfangs verwaltet werden.',
      keywords: 'lizenz testphase kaufen aktivieren schlüssel kundenportal arbeitsplatz mandanten',
      sections: [
        {title: 'Lizenznehmer', text: ['Tragen Sie Kanzlei bzw. Firma, E-Mail, Anschrift und Unternehmensnummer ein und speichern Sie diese Angaben vor dem Kauf. Der aktive Mandant im Header ist davon unabhängig.']},
        {title: 'Testphase und bezahlte Periode', text: ['Eine vorhandene Testphase bleibt bei einem Kauf erhalten. Die bezahlte Laufzeit wird serverseitig berücksichtigt und die resultierende Gültigkeit in der Anwendung angezeigt.']},
        {title: 'Aktionen', bullets: ['Lizenz kaufen öffnet die Auswahl zwischen automatischer Zahlung und monatlicher Rechnung.', 'Automatische Zahlung öffnet Stripe Checkout für Karte, Apple Pay oder Link und verlängert die Lizenz monatlich.', 'Zahlung auf Rechnung richtet eine monatliche Rechnung mit 14 Tagen Zahlungsziel ein.', 'Lizenz prüfen synchronisiert den aktuellen Serverstatus.', 'Lizenzschlüssel eingeben aktiviert einen manuell ausgestellten Schlüssel.', 'Kundenportal öffnen verwaltet Zahlung und Abonnement.', 'Lizenz deaktivieren löst den Arbeitsplatz von der Lizenz.']},
        {title: 'Verbindungsproblem', note: 'Bei fehlender Serververbindung nicht mehrfach kaufen. Prüfen Sie Internetzugang und klicken Sie zuerst auf Lizenz prüfen.'}
      ]
    },
    {
      id: 'troubleshooting', topic: 'processing', category: 'Fehlerbehebung', tag: 'orange', updated: '13.07.2026',
      title: 'Häufige technische Fehler und ihre Lösung',
      summary: 'Nutzen Sie die exakte Fehlermeldung im Aktivitätsprotokoll. Installationsfehler, ungültige Pfade und Datenprobleme benötigen unterschiedliche Korrekturen.',
      keywords: 'fehler fitz pymupdf pypdf2 static directory nicht gefunden excel pfad',
      sections: [
        {title: '„Directory static/ does not exist“ oder falsches fitz', text: ['Das Paket fitz ist nicht PyMuPDF. Entfernen Sie im aktiven virtuellen Python-Umfeld das falsche Paket fitz und installieren Sie PyMuPDF. Starten Sie danach LohnMail neu.']},
        {title: '„PyPDF2 ist nicht installiert“', text: ['Installieren Sie PyPDF2 im selben virtuellen Umfeld, mit dem main.py gestartet wird. Prüfen Sie im Terminal, dass python3 und pip zum gleichen venv gehören.']},
        {title: 'Datei nicht gefunden oder falscher Typ', bullets: ['Datenträger ist nicht mehr verbunden', 'Datei oder Ordner wurde verschoben', 'Ordner/Gesamt-PDF-Modus passt nicht zum Pfad', 'Mandanten-Excel wurde umbenannt'], note: 'Wählen Sie den betroffenen Eingang neu aus, statt den alten Pfad manuell zu übernehmen.'},
        {title: 'Daten werden nicht zugeordnet', bullets: ['Personalnummern in PDF und Excel vergleichen', 'Führende Nullen beachten', 'Richtigen Mandanten kontrollieren', 'Aktuelle Excel-Datei speichern und erneut auswählen']}
      ]
    },
    {
      id: 'data-security', topic: 'start', category: 'Datenschutz', tag: 'neutral', updated: '13.07.2026',
      title: 'Lokale Datenverarbeitung, Datenschutz und sichere Arbeitsweise',
      summary: 'Lohnunterlagen werden lokal verarbeitet. Eine externe Übertragung erfolgt nur durch einen ausdrücklich gestarteten E-Mail-Versand; Lizenzdaten werden getrennt davon geprüft.',
      keywords: 'datenschutz lokal cloud tracking sicherheit löschung backup lohndaten',
      sections: [
        {title: 'Was lokal bleibt', bullets: ['Ausgewählte PDF- und Excel-Dateien', 'Prüfergebnisse und erzeugte Berichte', 'Anwendungseinstellungen und Mandantenzuordnungen', 'Versandvorbereitung bis zum aktiv bestätigten Versand']},
        {title: 'Wann Daten übertragen werden', text: ['Lohnunterlagen werden nur übertragen, wenn ein Benutzer den Versand über SMTP oder Outlook Classic final bestätigt. Die Online-Lizenzprüfung enthält keine Lohnunterlagen.']},
        {title: 'Sichere Praxis', bullets: ['Ausgabeordner mit passenden Zugriffsrechten verwenden', 'Nicht benötigte Exporte nach interner Aufbewahrungsregel löschen', 'Vor dem Versand Empfänger und Anhang kontrollieren', 'Keine vollständigen Lohnunterlagen unaufgefordert an den Support senden']},
        {title: 'Sicherung', text: ['Sichern Sie die benötigten Eingabe- und Ergebnisdateien nach den Regeln Ihrer Organisation. LohnMail ersetzt kein zentrales Backup- oder Dokumentenmanagementsystem.']}
      ]
    },
    {
      id: 'guided-tutorials', topic: 'start', category: 'Kurzanleitungen', tag: 'green', updated: '13.07.2026',
      title: 'Kurzanleitungen für wiederkehrende Aufgaben',
      summary: 'Kompakte Ablaufpläne für Mandantenwechsel, Prüflauf, Einzelversand und Monatsabschluss.',
      keywords: 'tutorial video kurzanleitung schritt für schritt workflow',
      sections: [
        {title: 'Mandant wechseln', steps: ['Mandant im Header auswählen.', 'Status Excel bereit kontrollieren.', 'Verarbeitung öffnen und PDF-Eingang des Mandanten wählen.']},
        {title: 'Nur einen Empfänger senden', steps: ['Prüfung abschließen.', 'Versand öffnen und alle Markierungen entfernen.', 'Gewünschten Empfänger markieren.', 'Vorschau kontrollieren, vorbereiten und final bestätigen.']},
        {title: 'Mitarbeiter ohne E-Mail bearbeiten', steps: ['Prüfung > Warnungen öffnen.', 'Einträge ohne E-Mail kontrollieren.', 'PDF ohne E-Mail öffnen oder Bericht ohne_email_gesamt.pdf unter Berichte verwenden.']},
        {title: 'Monatsabschluss', steps: ['Prüfbericht kontrollieren.', 'Versandbericht nach erfolgreichem Versand öffnen.', 'Ausgabeordner nach interner Ablagevorgabe sichern.', 'Nächsten Abrechnungszeitraum in Einstellungen kontrollieren.']}
      ]
    },
    {
      id: 'manual', topic: 'start', category: 'Handbuch', tag: 'neutral', updated: '13.07.2026',
      title: 'LohnMail v2 Handbuch: Funktionen und empfohlener Arbeitsablauf',
      summary: 'Das Handbuch erklärt die Bereiche der Anwendung und verweist auf die detaillierten Artikel der lokalen Wissensdatenbank.',
      keywords: 'handbuch dokumentation alle funktionen übersicht',
      sections: [
        {title: 'Arbeitsbereiche', bullets: ['Dashboard: Status, letzte Berichte und Schnellaktionen', 'Verarbeitung: Eingaben, Prüfungslauf und Aktivitätsprotokoll', 'Prüfung: vollständige Mitarbeiterliste, Auffälligkeiten und Exporte', 'Versand: Empfängerauswahl, Vorschau und Versandstatus', 'Berichte: erzeugte Prüf-, Fehladress- und Versanddateien', 'Nachricht: freie Nachricht an ausgewählte Empfänger']},
        {title: 'Verwaltung', bullets: ['Unternehmen: betreute Mandanten und deren Stammdaten', 'Lizenzen: Lizenznehmer, Laufzeit und Aktivierung', 'Einstellungen: Zeitraum, Mail, Vorlagen, Hinweise und Sicherheit', 'Hilfe: lokale Dokumentation und Support-Checkliste']},
        {title: 'Empfohlene Reihenfolge', steps: ['Lizenznehmer und Mail-Verbindung einrichten.', 'Mandant anlegen und Excel zuordnen.', 'PDF-Eingang wählen und Prüfung starten.', 'Warnungen lesen und Daten korrigieren.', 'Versand auswählen, vorbereiten, prüfen und bestätigen.', 'Berichte archivieren.']},
        {title: 'Navigation', text: ['Die breite Workflow-Leiste auf Verarbeitung, Prüfung und Versand zeigt den aktuellen Stand. Bereits verfügbare Schritte können direkt geöffnet werden. Der Header hält Lizenz, Hinweise und aktiven Mandanten sichtbar.']}
      ]
    },
    {
      id: 'support-checklist', topic: 'support', category: 'Support', tag: 'orange', updated: '13.07.2026',
      title: 'Support-Anfrage vorbereiten: benötigte Angaben und Datenschutz',
      summary: 'Mit vollständigen technischen Angaben kann ein Problem schneller eingegrenzt werden, ohne unnötig sensible Lohnunterlagen zu übertragen.',
      keywords: 'support email diagnose fernwartung problem ticket',
      sections: [
        {title: 'Kontakt', text: ['E-Mail: support@lohn-mail.de. Beschreiben Sie das Problem sachlich und nennen Sie, auf welcher Seite und nach welcher Aktion es auftritt.']},
        {title: 'Bitte mitsenden', bullets: ['LohnMail-Version aus Über LohnMail', 'Betriebssystem und Python-Version', 'Exakter Wortlaut der Fehlermeldung', 'Zeitpunkt des Fehlers', 'Verwendeter Eingabemodus Ordner oder Gesamt-PDF', 'Ob SMTP oder Outlook Classic verwendet wird']},
        {title: 'Nur wenn erforderlich', bullets: ['Anonymisierter Screenshot ohne personenbezogene Daten', 'Relevanter Ausschnitt aus dem Aktivitätsprotokoll', 'Beispieldatei ausschließlich nach ausdrücklicher Abstimmung und möglichst anonymisiert']},
        {title: 'Nicht unaufgefordert senden', bullets: ['Vollständige Lohnabrechnungen', 'Unverschlüsselte Mitarbeiterlisten', 'SMTP-Passwörter', 'Lizenz- oder Administrationsgeheimnisse'], note: 'Fernsupport wird nur nach Termin gestartet. Sie müssen jede Sitzung aktiv freigeben und können sie jederzeit beenden.'}
      ]
    }
  ];
  var helpTopicNames = {
    all: 'Alle Themen', start: 'Erste Schritte', processing: 'Verarbeitung', validation: 'Prüfung',
    shipping: 'Versand', reports: 'Berichte', settings: 'Einstellungen', support: 'Support'
  };
  function helpArticleById(id){
    return helpArticles.find(function(article){ return article.id === id; }) || null;
  }
  function helpArticleSearchText(article){
    var sectionText = (article.sections || []).map(function(section){
      return [section.title, section.text, section.steps, section.bullets, section.note].flat().filter(Boolean).join(' ');
    }).join(' ');
    return [article.title, article.summary, article.category, article.keywords, sectionText].join(' ').toLocaleLowerCase('de');
  }
  function filteredHelpArticles(){
    var query = helpSearchQuery.trim().toLocaleLowerCase('de');
    return helpArticles.filter(function(article){
      var topicMatches = currentHelpTopic === 'all' || article.topic === currentHelpTopic;
      return topicMatches && (!query || helpArticleSearchText(article).indexOf(query) !== -1);
    });
  }
  function renderHelpKnowledge(){
    var body = document.querySelector('[data-help-results]');
    if (!body) return;
    var matches = filteredHelpArticles();
    var visible = (!helpShowAll && currentHelpTopic === 'all' && !helpSearchQuery) ? matches.slice(0, 7) : matches;
    body.innerHTML = visible.map(function(article){
      return '<tr tabindex="0" data-help-article="' + escapeHtml(article.id) + '">' +
        '<td><span data-icon="doc"></span><b>' + escapeHtml(article.title) + '</b><small>' + escapeHtml(article.summary) + '</small></td>' +
        '<td><b class="tag ' + escapeHtml(article.tag || 'neutral') + '">' + escapeHtml(article.category) + '</b></td>' +
        '<td>' + escapeHtml(article.updated) + '</td></tr>';
    }).join('');
    var empty = document.querySelector('[data-help-empty]');
    if (empty) empty.hidden = matches.length > 0;
    var table = document.querySelector('.knowledge-table');
    if (table) table.hidden = matches.length === 0;
    var summary = document.querySelector('[data-help-result-summary]');
    if (summary) {
      if (helpSearchQuery) summary.textContent = matches.length + ' Treffer für „' + helpSearchQuery + '“';
      else if (currentHelpTopic !== 'all') summary.textContent = matches.length + ' Artikel · ' + (helpTopicNames[currentHelpTopic] || 'Thema');
      else summary.textContent = visible.length + ' von ' + matches.length + ' lokalen Hilfeartikeln';
    }
    var clear = document.querySelector('[data-help-action="clear"]');
    if (clear) clear.hidden = currentHelpTopic === 'all' && !helpSearchQuery;
    var allButton = document.querySelector('[data-help-action="articles"]');
    if (allButton) allButton.hidden = helpShowAll || currentHelpTopic !== 'all' || !!helpSearchQuery || matches.length <= visible.length;
    document.querySelectorAll('[data-help-topic]').forEach(function(button){
      button.classList.toggle('active', button.getAttribute('data-help-topic') === currentHelpTopic);
    });
    body.querySelectorAll('[data-help-article]').forEach(function(row){
      function open(){ openHelpArticle(row.getAttribute('data-help-article')); }
      row.addEventListener('click', open);
      row.addEventListener('keydown', function(event){
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          open();
        }
      });
    });
  }
  function renderHelpSection(section, index){
    var html = '<section><h3>' + escapeHtml(section.title || ('Abschnitt ' + (index + 1))) + '</h3>';
    (section.text || []).forEach(function(paragraph){ html += '<p>' + escapeHtml(paragraph) + '</p>'; });
    if (section.steps && section.steps.length) {
      html += '<ol>' + section.steps.map(function(step){ return '<li>' + escapeHtml(step) + '</li>'; }).join('') + '</ol>';
    }
    if (section.bullets && section.bullets.length) {
      html += '<ul>' + section.bullets.map(function(item){ return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul>';
    }
    if (section.note) html += '<div class="help-note"><span data-icon="info"></span><p>' + escapeHtml(section.note) + '</p></div>';
    return html + '</section>';
  }
  function openHelpArticle(id){
    var article = helpArticleById(id);
    var modal = document.querySelector('[data-help-modal]');
    if (!article || !modal) return false;
    setText('[data-help-detail="category"]', article.category);
    setText('[data-help-detail="title"]', article.title);
    setText('[data-help-detail="summary"]', article.summary);
    setText('[data-help-detail="updated"]', article.updated);
    var body = modal.querySelector('[data-help-detail="body"]');
    if (body) body.innerHTML = (article.sections || []).map(renderHelpSection).join('');
    var related = helpArticles.filter(function(item){ return item.id !== article.id && item.topic === article.topic; }).slice(0, 3);
    var relatedWrap = modal.querySelector('[data-help-related-wrap]');
    var relatedBody = modal.querySelector('[data-help-related]');
    if (relatedWrap) relatedWrap.hidden = related.length === 0;
    if (relatedBody) {
      relatedBody.innerHTML = related.map(function(item){
        return '<button data-help-related-id="' + escapeHtml(item.id) + '"><span data-icon="doc"></span><span><b>' + escapeHtml(item.title) + '</b><small>' + escapeHtml(item.category) + '</small></span><i>›</i></button>';
      }).join('');
      relatedBody.querySelectorAll('[data-help-related-id]').forEach(function(button){
        button.addEventListener('click', function(){ openHelpArticle(button.getAttribute('data-help-related-id')); });
      });
    }
    var modalBody = modal.querySelector('.help-article-body');
    if (modalBody) modalBody.scrollTop = 0;
    modal.hidden = false;
    return true;
  }
  function closeHelpArticle(){
    var modal = document.querySelector('[data-help-modal]');
    if (modal) modal.hidden = true;
  }
  function focusHelpKnowledge(){
    var card = document.querySelector('.knowledge-card');
    if (card) card.scrollIntoView({behavior:'smooth', block:'start'});
  }
  function runHelpAction(action, source){
    if (action === 'email') {
      openProductContact('email');
      return;
    }
    if (action === 'release') {
      setPage('Über LohnMail');
      return;
    }
    if (action === 'status') {
      setPage('Dashboard');
      return;
    }
    if (action === 'topic') {
      currentHelpTopic = (source && source.getAttribute('data-help-topic')) || 'all';
      helpSearchQuery = '';
      helpShowAll = true;
      var search = document.querySelector('[data-help-search]');
      if (search) search.value = '';
      renderHelpKnowledge();
      focusHelpKnowledge();
      return;
    }
    if (action === 'search') {
      var field = document.querySelector('[data-help-search]');
      helpSearchQuery = field ? field.value.trim() : '';
      currentHelpTopic = 'all';
      helpShowAll = true;
      renderHelpKnowledge();
      focusHelpKnowledge();
      return;
    }
    if (action === 'clear') {
      currentHelpTopic = 'all';
      helpSearchQuery = '';
      helpShowAll = false;
      var searchField = document.querySelector('[data-help-search]');
      if (searchField) searchField.value = '';
      renderHelpKnowledge();
      return;
    }
    if (action === 'articles') {
      currentHelpTopic = 'all';
      helpSearchQuery = '';
      helpShowAll = true;
      renderHelpKnowledge();
      focusHelpKnowledge();
      return;
    }
    var articleActions = {
      video: 'guided-tutorials', manual: 'manual', diagnostics: 'support-checklist',
      remote: 'support-checklist', request: 'support-checklist'
    };
    if (articleActions[action]) {
      openHelpArticle(articleActions[action]);
      return;
    }
    setInfoBanner('Hilfeaktion konnte nicht geöffnet werden.', false);
  }
  var aboutLegalContent = {
    privacy: {
      title: 'Datenschutzerklärung',
      intro: 'LohnMail verarbeitet Lohnunterlagen lokal auf diesem Rechner. Die Anwendung sammelt keine Nutzungsanalyse, überträgt keine Lohnunterlagen an Cloud-Dienste und sendet keine personenbezogenen Daten an den Hersteller.',
      sections: [
        ['Welche Daten verarbeitet werden', 'Verarbeitet werden nur die vom Benutzer ausgewählten PDF-Dateien, Excel-Listen, Ausgabepfade, E-Mail-Adressen und Versandinformationen, die für Prüfung, Berichtserstellung und Versand benötigt werden.'],
        ['Keine automatische Übertragung', 'LohnMail lädt keine Lohnunterlagen, Mitarbeiterdaten oder Prüfberichte automatisch ins Internet hoch. Eine Übertragung erfolgt nur, wenn der Benutzer aktiv einen Versand über SMTP oder Outlook Classic auslöst.'],
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
        ['Verwendete Komponenten', 'Zu den Komponenten gehören unter anderem Python, pywebview, SQLite, PyPDF2, openpyxl und weitere technische Bibliotheken.'],
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
      release: 'Release Notes werden als Produktinformation angezeigt.',
      details: 'Technische Details sind in der Komponentenübersicht sichtbar.',
      support: 'Supportbereich wird geöffnet.'
    };
    if (renderAboutLegal(action)) {
      return;
    }
    if (action === 'website') {
      openProductContact('website');
      return;
    }
    if (action === 'support') {
      openProductContact('email');
      return;
    }
    setInfoBanner(messages[action] || 'Produktaktion ausgewählt.', true);
  }
  function openProductContact(action){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.openProductContact) {
      setInfoBanner('Kontakt konnte nicht geöffnet werden. Bitte starten Sie LohnMail neu.', false);
      return;
    }
    bridge.openProductContact(action, function(payload){
      try {
        var result = JSON.parse(payload || '{}');
        setInfoBanner(result.message || 'Kontakt konnte nicht geöffnet werden.', !!result.ok);
      } catch (error) {
        setInfoBanner('Kontakt konnte nicht geöffnet werden.', false);
      }
    });
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
    var validationReports = validation.reports || {};
    var shippingReports = shipping.reports || {};

    var pdfReady = !!(inputs.pdf && inputs.pdf.valid);
    var excelReady = !!(inputs.excel && inputs.excel.valid);
    var processingFailed = !!processingStatus.failed;
    var validationReady = !!(validation.ready || validationRows.length || validationSummary.total || processingStatus.finished);
    var validationWarnings = validationRows.some(function(row){ return row.severity === 'warning' || row.status === 'Keine E-Mail'; });
    var validationErrors = validationRows.some(function(row){ return row.severity === 'critical' || row.status === 'Fehler' || row.status === 'Keine Dateien'; });
    var processingDone = !!processingStatus.finished;
    var shippingReady = Number(shippingMetrics.total || 0) > 0 || validationReady;
    var shippingDone = Number(shippingMetrics.sent || 0) > 0 || (!!shippingStatus.finished && shippingStatus.dry_run === false);
    var reportsReady = !!(
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
    setDashboardPipelineStep('processing', processingDone ? 'done' : (processingStatus.running ? 'active' : 'muted'), processingDone ? 'Bereit' : (processingStatus.running ? 'Läuft' : 'Wartet'));
    setDashboardPipelineStep('shipping', shippingDone ? 'done' : (shippingReady ? 'active' : 'muted'), shippingDone ? 'Abgeschlossen' : (shippingReady ? 'Bereit' : 'Wartet'));
    setDashboardPipelineStep('reports', reportsReady ? 'done' : (shippingDone || validationReady ? 'active' : 'muted'), reportsReady ? 'Erstellt' : 'Wartet');

    var doneCount = [pdfReady, excelReady, validationReady, processingDone, shippingDone, reportsReady].filter(Boolean).length;
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
  function renderDashboardLastRun(run){
    var empty = document.querySelector('[data-dashboard-last-run="empty"]');
    var content = document.querySelector('[data-dashboard-last-run="content"]');
    if (empty) empty.hidden = !!run;
    if (content) content.hidden = !run;
    if (!run) return;
    var metrics = normalizeReportMetrics(run.metrics || {});
    setText('[data-dashboard-last-run="status"]', run.status || 'Lauf abgeschlossen');
    setText('[data-dashboard-last-run="date"]', reportDate(run.created_at));
    setText('[data-dashboard-last-run="employees"]', metrics.employees || metrics.processed || 0);
    setText('[data-dashboard-last-run="sent"]', metrics.sent || 0);
    setText('[data-dashboard-last-run="warnings"]', metrics.errors || metrics.warnings || metrics.missing_email || 0);
  }
  function renderDashboardActivity(runs){
    var empty = document.querySelector('[data-dashboard-activity="empty"]');
    var list = document.querySelector('[data-dashboard-activity="list"]');
    runs = Array.isArray(runs) ? runs : [];
    if (empty) empty.hidden = runs.length > 0;
    if (!list) return;
    list.hidden = runs.length === 0;
    list.innerHTML = runs.map(function(run){
      var metrics = normalizeReportMetrics(run.metrics || {});
      var level = String(run.status || '').toLowerCase().indexOf('fehler') !== -1 ? 'error' : (
        String(run.status || '').toLowerCase().indexOf('warnung') !== -1 ? 'warning' : 'success'
      );
      var detail = (metrics.employees || metrics.processed || 0) + ' Mitarbeiter';
      if (metrics.sent) detail += ' · ' + metrics.sent + ' gesendet';
      else if (metrics.missing_email) detail += ' · ' + metrics.missing_email + ' ohne E-Mail';
      return '<button class="dashboard-activity-row ' + level + '" data-dashboard-action="open-last-run">' +
        '<span class="dashboard-activity-dot"></span>' +
        '<span><strong>' + escapeHtml(run.status || run.operation || 'Lauf abgeschlossen') + '</strong><small>' + escapeHtml(detail) + '</small></span>' +
        '<time>' + escapeHtml(reportDate(run.created_at)) + '</time>' +
      '</button>';
    }).join('');
    list.querySelectorAll('[data-dashboard-action="open-last-run"]').forEach(function(button){
      button.addEventListener('click', function(){ runDashboardAction('open-last-run'); });
    });
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
    var lastRunLabel = state.last_run ? 'Letzter Lauf: ' + reportDate(state.last_run.created_at) : 'Noch kein Lauf';
    setText('[data-dashboard-metric-label="employees"]', lastRunLabel);
    setText('[data-dashboard-metric-label="sent"]', metrics.sent ? 'Im letzten Lauf gesendet' : 'Noch kein Versand');
    setText('[data-dashboard-metric-label="missing-email"]', metrics.missing_email ? 'Im letzten Lauf' : lastRunLabel);
    renderDashboardLastRun(state.last_run || null);
    renderDashboardActivity(state.activity || []);

    var license = state.license || {};
    var mail = state.mail || {};
    if (license.status || license.label) {
      latestLicenseState = license;
    }
    setText('[data-dashboard="license-pill"]', 'Lizenz: ' + (license.label || 'Unbekannt'));
    setText('.side-status-title', (state.system && state.system.ready) ? 'System bereit' : 'System prüfen');
    setText('.side-status-subtitle', 'Mail: ' + (mail.label || 'Unbekannt'));
    setLabeledIconText('[data-dashboard="footer-license"]', 'Lizenz: ' + (license.label || 'Unbekannt'));
    setLabeledIconText('[data-dashboard="footer-mail"]', (mail.mode === 'outlook' ? 'Outlook Classic: ' : 'SMTP: ') + (mail.label || 'Unbekannt'));
    setLabeledIconText('[data-dashboard="footer-outlook"]', mail.mode === 'outlook' ? 'Outlook Classic: Bereit' : 'Outlook Classic: Nicht aktiv');
    setLabeledIconText('[data-dashboard="footer-mode"]', 'Modus: Lokal');
    setLabeledIconText('[data-dashboard="footer-system"]', (state.system && state.system.ready) ? 'System bereit' : 'System prüfen');

    var system = state.system || {};
    setStatus('[data-dashboard="status-processing"]', system.processing || 'Bereit');
    setStatus('[data-dashboard="status-pdf"]', system.pdf || 'Offen');
    setStatus('[data-dashboard="status-excel"]', system.excel || 'Offen');
    setStatus('[data-dashboard="status-mail"]', system.mail || 'Offen');
    setStatus('[data-dashboard="status-license"]', system.license || 'Offen');
    setStatus('[data-dashboard="status-filesystem"]', system.filesystem || 'Offen');

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
  function closeNewRunModal(){
    var modal = document.querySelector('[data-new-run-modal]');
    if (modal) modal.hidden = true;
  }
  function startNewRunNow(){
      var bridge = window.lohnmailBridge;
      if (!bridge || !bridge.startNewRun) {
        setPage('Verarbeitung');
        loadProcessingState();
        return;
      }
      bridge.startNewRun(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          if (!result.ok) {
            setInfoBanner(result.message || 'Neuer Lauf konnte nicht gestartet werden.', false);
            return;
          }
          resetWorkflowUiForCompanyChange();
          consumeProcessingPayload(JSON.stringify(result.state || {}), 'state');
          setPage('Verarbeitung');
          loadValidationState();
          loadShippingState();
          loadDashboardState();
          loadReportsState();
          setInfoBanner(result.message || 'Neuer Lauf wurde vorbereitet.', true);
        } catch (error) {
          setInfoBanner('Neuer Lauf konnte nicht gestartet werden.', false);
        }
      });
  }
  function runDashboardAction(action){
    var ready = workflowReadyState();
    if (action === 'new-run') {
      var processingStatus = (latestProcessingState && latestProcessingState.status) || {};
      var hasWorkflowData = !!(
        processingStatus.finished || processingStatus.failed ||
        ((latestValidationState && latestValidationState.rows) || []).length ||
        ((latestShippingState && latestShippingState.rows) || []).length
      );
      if (hasWorkflowData) {
        var modal = document.querySelector('[data-new-run-modal]');
        if (modal) modal.hidden = false;
        return;
      }
      startNewRunNow();
      return;
    }
    if (action === 'open-processing') {
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
    if (action === 'open-reports' || action === 'open-last-run') {
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
    var emailIssues = rows.filter(function(row){ return row.category === 'E-Mail' && row.status !== 'Keine E-Mail'; }).length;
    return { ready: ready, missingEmail: missingEmail, emailIssues: emailIssues, errors: errors };
  }
  function updateValidationShippingStatus(state){
    var summary = validationShippingSummary(state);
    setText('[data-validation="shipping-status"]', summary.ready + ' versandbereit · ' + summary.missingEmail + ' ohne E-Mail · ' + summary.emailIssues + ' E-Mail-Hinweise · ' + summary.errors + ' Fehler');
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
    if (!workflowStateMatchesActiveCompany(state)) return;
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
      rows = rows.filter(function(row){ return ['Fehler', 'Keine Dateien', 'Doppelte E-Mail', 'Ungültige E-Mail', 'Ungültige Zeichen', 'Ungültiges Format', 'Domain nicht gefunden', 'Keine MX-Einträge'].indexOf(row.status) !== -1; });
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
    if (['Keine E-Mail', 'Keine Dateien', 'Doppelte E-Mail', 'Ungültige E-Mail', 'Ungültige Zeichen', 'Ungültiges Format', 'Domain nicht gefunden', 'Keine MX-Einträge', 'Übersprungen'].indexOf(status) !== -1) return 'warning';
    if (status === 'Wird gesendet' || status === 'Wird vorbereitet') return 'sending';
    if (status === 'Wartet') return 'waiting';
    return 'ready';
  }
  function resetShippingLiveProgress(companyId, selectedRows, phase){
    var selected = {};
    (selectedRows || []).forEach(function(row){
      var persnr = String(row && row.persnr || '');
      if (!persnr) return;
      selected[persnr] = {
        email: String(row.email || ''),
        employee: String(row.employee || '')
      };
    });
    shippingLiveProgress = {
      companyId: String(companyId || ''),
      phase: phase || (selectedRows && selectedRows.length ? 'sending' : 'idle'),
      total: selectedRows ? selectedRows.length : 0,
      completed: 0,
      prepared: 0,
      sent: 0,
      errors: 0,
      currentPersnr: '',
      currentEmail: '',
      operation: '',
      dryRun: phase === 'preparing',
      selected: selected,
      processed: {}
    };
    updateShippingLiveProgressPanel();
  }
  function selectedShippingRows(){
    var rows = (latestShippingState && latestShippingState.rows) || [];
    return rows.filter(function(row){
      var persnr = String(row.persnr || '');
      return shippingRowSelectable(row) && selectedShippingPersnr[persnr] !== false;
    });
  }
  function nextPendingShippingRecipient(){
    var keys = Object.keys(shippingLiveProgress.selected || {}).sort(function(a, b){
      return a.localeCompare(b, undefined, { numeric: true });
    });
    for (var i = 0; i < keys.length; i += 1) {
      if (!shippingLiveProgress.processed[keys[i]]) {
        return {
          persnr: keys[i],
          email: shippingLiveProgress.selected[keys[i]].email || ''
        };
      }
    }
    return null;
  }
  function rememberShippingProgressMessage(message){
    message = String(message || '').trim();
    if (!message || shippingLiveProgress.phase !== 'sending') return;
    var match = message.match(/^Gesendet via .*?:\s*(\S+)\s*->\s*(.+)$/i);
    var kind = 'sent';
    if (!match) {
      match = message.match(/^Fehler bei\s+([^:]+):\s*(.*)$/i);
      kind = 'error';
    }
    if (!match) return;
    var persnr = String(match[1] || '').trim();
    if (!persnr || shippingLiveProgress.processed[persnr]) return;
    var selectedRow = shippingLiveProgress.selected[persnr] || {};
    shippingLiveProgress.processed[persnr] = {
      status: kind === 'sent' ? 'Gesendet' : 'Fehler',
      error: kind === 'error' ? String(match[2] || '').trim() : ''
    };
    shippingLiveProgress.completed += 1;
    shippingLiveProgress[kind === 'sent' ? 'sent' : 'errors'] += 1;
    shippingLiveProgress.currentPersnr = persnr;
    shippingLiveProgress.currentEmail = kind === 'sent'
      ? String(match[2] || '').trim()
      : String(selectedRow.email || '');
  }
  function syncShippingLiveProgress(state, status, metrics){
    var companyId = String(state && state.company && state.company.id || '');
    var live = status.live_progress || {};
    var anyRunning = !!status.running;
    var realSendRunning = !!status.running && status.dry_run === false;
    var anyTerminal = !status.running && (status.finished || status.failed);

    if (anyRunning) {
      var phase = String(live.phase || (realSendRunning ? 'sending' : 'preparing'));
      if (shippingLiveProgress.phase === 'idle' || shippingLiveProgress.companyId !== companyId) {
        resetShippingLiveProgress(companyId, realSendRunning ? selectedShippingRows() : shippingRows(), phase);
      }
      shippingLiveProgress.phase = phase;
      shippingLiveProgress.dryRun = status.dry_run !== false;
      shippingLiveProgress.total = Math.max(0, Number(live.total !== undefined ? live.total : shippingLiveProgress.total) || 0);
      shippingLiveProgress.completed = Math.max(0, Number(live.current || 0));
      shippingLiveProgress.prepared = Math.max(0, Number(live.prepared || 0));
      shippingLiveProgress.sent = Math.max(0, Number(live.sent || 0));
      shippingLiveProgress.errors = Math.max(0, Number(live.errors || 0));
      shippingLiveProgress.currentPersnr = String(live.persnr || '');
      shippingLiveProgress.currentEmail = String(live.email || '');
      shippingLiveProgress.operation = String(live.operation || status.message || '');
      var livePersnr = String(live.persnr || '');
      var liveStatus = String(live.status || 'running');
      if (livePersnr && ['complete', 'error', 'skipped'].indexOf(liveStatus) !== -1) {
        shippingLiveProgress.processed[livePersnr] = {
          status: liveStatus === 'error' ? 'Fehler' : (liveStatus === 'skipped' ? 'Übersprungen' : (shippingLiveProgress.dryRun ? 'Dry-Run' : 'Gesendet')),
          error: liveStatus === 'error' ? shippingLiveProgress.operation : ''
        };
      }
    } else if (anyTerminal) {
      if (shippingLiveProgress.phase === 'idle' || shippingLiveProgress.companyId !== companyId) {
        var terminalTotal = Number(status.dry_run !== false ? metrics.exported : metrics.sent) + Number(metrics.errors || 0);
        resetShippingLiveProgress(companyId, [], status.dry_run !== false ? 'preparing' : 'sending');
        shippingLiveProgress.total = terminalTotal;
      }
      shippingLiveProgress.dryRun = status.dry_run !== false;
      shippingLiveProgress.prepared = Math.max(shippingLiveProgress.prepared, Number(metrics.exported || 0));
      shippingLiveProgress.sent = Math.max(shippingLiveProgress.sent, Number(metrics.sent || 0));
      shippingLiveProgress.errors = Math.max(shippingLiveProgress.errors, Number(metrics.errors || 0));
      shippingLiveProgress.completed = shippingLiveProgress.total || ((shippingLiveProgress.dryRun ? shippingLiveProgress.prepared : shippingLiveProgress.sent) + shippingLiveProgress.errors);
      shippingLiveProgress.total = Math.max(shippingLiveProgress.total, shippingLiveProgress.completed);
      shippingLiveProgress.phase = status.failed ? 'failed' : 'complete';
      shippingLiveProgress.currentPersnr = '';
      shippingLiveProgress.currentEmail = '';
      shippingLiveProgress.operation = String(status.message || '');
    }
    updateShippingLiveProgressPanel(status);
  }
  function updateShippingLiveProgressPanel(status){
    var panel = document.querySelector('[data-shipping-live]');
    if (!panel) return;
    var visible = shippingLiveProgress.phase !== 'idle';
    panel.hidden = !visible;
    if (!visible) return;
    var total = Math.max(0, Number(shippingLiveProgress.total || 0));
    var completed = Math.min(total, Math.max(0, Number(shippingLiveProgress.completed || 0)));
    var remaining = Math.max(0, total - completed);
    var percent = total ? Math.round((completed / total) * 100) : 0;
    var title = shippingLiveProgress.phase === 'preparing' ? 'Versand wird vorbereitet' : 'E-Mails werden versendet';
    var subject = shippingLiveProgress.currentEmail || (shippingLiveProgress.currentPersnr ? ('Personalnr. ' + shippingLiveProgress.currentPersnr) : '');
    var current = [shippingLiveProgress.operation, subject ? ('Aktuell: ' + subject) : ''].filter(Boolean).join(' · ') || 'Vorgang wird gestartet...';
    if (shippingLiveProgress.phase === 'complete') {
      title = shippingLiveProgress.dryRun ? 'Vorbereitung abgeschlossen' : 'Versand abgeschlossen';
      current = shippingLiveProgress.dryRun
        ? shippingLiveProgress.prepared + ' PDF-Dateien vorbereitet' + (shippingLiveProgress.errors ? ' · ' + shippingLiveProgress.errors + ' Fehler' : '')
        : shippingLiveProgress.sent + ' E-Mails gesendet' +
        (shippingLiveProgress.errors ? ' · ' + shippingLiveProgress.errors + ' Fehler' : '');
      percent = 100;
    } else if (shippingLiveProgress.phase === 'failed') {
      title = 'Versand abgebrochen';
      current = String(status && status.message || 'Der Versand konnte nicht abgeschlossen werden.');
    }
    setText('[data-shipping-live="title"]', title);
    var successful = shippingLiveProgress.dryRun ? shippingLiveProgress.prepared : shippingLiveProgress.sent;
    var displayedSent = total > 0 ? Math.min(total, successful) : successful;
    var displayedErrors = total > 0
      ? Math.min(Math.max(0, total - displayedSent), shippingLiveProgress.errors)
      : shippingLiveProgress.errors;
    setText('[data-shipping-live="count"]', completed + '/' + total);
    setText('[data-shipping-live="sent"]', displayedSent);
    setText('[data-shipping-live="success-label"]', shippingLiveProgress.dryRun ? 'Vorbereitet' : 'Gesendet');
    setText('[data-shipping-live="errors"]', displayedErrors);
    setText('[data-shipping-live="remaining"]', remaining);
    setText('[data-shipping-live="current"]', current);
    var bar = document.querySelector('[data-shipping-live="bar"]');
    if (bar) bar.style.width = Math.max(0, Math.min(100, percent)) + '%';
    panel.classList.toggle('is-complete', shippingLiveProgress.phase === 'complete');
    panel.classList.toggle('is-failed', shippingLiveProgress.phase === 'failed');
  }
  function shippingRowPresentation(row){
    var persnr = String(row && row.persnr || '');
    var presented = Object.assign({}, row || {});
    if (shippingLiveProgress.phase === 'idle' || !shippingLiveProgress.selected[persnr]) return presented;
    var processed = shippingLiveProgress.processed[persnr];
    if (processed) {
      presented.status = processed.status;
      if (processed.error) presented.error = processed.error;
      return presented;
    }
    if (shippingLiveProgress.phase === 'sending') {
      presented.status = shippingLiveProgress.currentPersnr === persnr ? 'Wird gesendet' : 'Wartet';
      presented.planned = 'Jetzt';
    }
    if (shippingLiveProgress.phase === 'preparing') {
      presented.status = shippingLiveProgress.currentPersnr === persnr ? 'Wird vorbereitet' : 'Wartet';
      presented.planned = 'Jetzt';
    }
    return presented;
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
  function shippingPreparationReady(){
    var status = (latestShippingState && latestShippingState.status) || {};
    var metrics = (latestShippingState && latestShippingState.metrics) || {};
    return !shippingSelectionDirty &&
      !!status.finished &&
      Number(metrics.exported || 0) > 0 &&
      Number(metrics.ready || 0) > Number(metrics.sent || 0);
  }
  function updateShippingPrimaryAction(){
    var button = document.querySelector('[data-shipping-primary]');
    if (!button) return;
    var label = button.querySelector('[data-shipping="primary-label"]');
    var status = (latestShippingState && latestShippingState.status) || {};
    var metrics = (latestShippingState && latestShippingState.metrics) || {};
    var selected = selectedShippingList().length;
    var prepared = shippingPreparationReady();
    var realSendRunning = !!status.running && status.dry_run === false;
    var realSendFinished = !status.running && !!status.finished && status.dry_run === false &&
      (Number(metrics.sent || 0) + Number(metrics.errors || 0) > 0 || shippingLiveProgress.phase === 'complete');
    var realSendFailed = !status.running && !!status.failed && status.dry_run === false;
    var action = prepared ? 'send-now' : 'start-dry-run';
    var text = prepared ? 'Jetzt senden' : 'Versand vorbereiten';
    var title = prepared ? 'Ausgewählte E-Mails prüfen und senden' : 'Versand für ausgewählte Empfänger vorbereiten';

    if (status.running) {
      text = realSendRunning
        ? 'Versand läuft · ' + shippingLiveProgress.completed + '/' + shippingLiveProgress.total
        : 'Vorbereitung läuft...';
      title = realSendRunning ? 'E-Mails werden versendet' : 'Versand wird vorbereitet';
    } else if (realSendFailed) {
      text = 'Versand fehlgeschlagen';
      title = status.message || 'E-Mail Versand konnte nicht abgeschlossen werden';
    } else if (realSendFinished) {
      text = 'Versand abgeschlossen';
      title = status.message || 'E-Mail Versand wurde abgeschlossen';
    } else if (!selected) {
      title = 'Bitte mindestens einen sendbaren Mitarbeiter auswählen';
    } else if (!status.can_send) {
      title = 'PDF-, Excel- und E-Mail-Einstellungen prüfen';
    }

    button.setAttribute('data-shipping-action', action);
    button.classList.toggle('danger-send', prepared || realSendRunning);
    button.disabled = !!status.running || realSendFinished || realSendFailed || !status.can_send || selected < 1;
    button.classList.toggle('soft-disabled', button.disabled);
    button.title = title;
    if (label) label.textContent = text;
  }
  function invalidateShippingPreparation(){
    if (shippingPreparationReady()) {
      shippingSelectionDirty = true;
      closeShippingSendModal();
    }
  }
  function updateShippingSelectionSummary(){
    var selected = selectedShippingList().length;
    var selectable = ((latestShippingState && latestShippingState.rows) || []).filter(shippingRowSelectable).length;
    var status = (latestShippingState && latestShippingState.status) || {};
    var title = selected + ' von ' + selectable + ' sendbaren Einträgen ausgewählt';
    setText('[data-shipping="selection-title"]', title);
    if (shippingSelectionDirty) {
      setText('[data-shipping="selection-message"]', 'Auswahl geändert. Versand erneut vorbereiten.');
    } else if (status.running) {
      setText('[data-shipping="selection-message"]', status.dry_run === false ? 'E-Mails werden versendet.' : 'Anhänge und Empfänger werden geprüft.');
    } else if (status.finished && status.dry_run === false) {
      setText('[data-shipping="selection-message"]', status.message || 'E-Mail Versand wurde abgeschlossen.');
    } else if (shippingPreparationReady()) {
      setText('[data-shipping="selection-message"]', 'Vorbereitung abgeschlossen. Versand kann geprüft werden.');
    } else if (!selected) {
      setText('[data-shipping="selection-message"]', 'Mindestens einen sendbaren Empfänger auswählen.');
    } else {
      setText('[data-shipping="selection-message"]', status.message || 'Empfänger ausgewählt. Versand kann vorbereitet werden.');
    }
    updateShippingPrimaryAction();
  }
  function shippingFilterCounts(){
    var rows = (latestShippingState && latestShippingState.rows) || [];
    return {
      all: rows.length,
      ready: rows.filter(function(row){ return row.status === 'Bereit' || row.status === 'Dry-Run'; }).length,
      'missing-email': rows.filter(function(row){ return row.status === 'Keine E-Mail'; }).length,
      error: rows.filter(function(row){ return ['Fehler', 'Keine Dateien', 'Doppelte E-Mail', 'Ungültige E-Mail', 'Ungültige Zeichen', 'Ungültiges Format', 'Domain nicht gefunden', 'Keine MX-Einträge'].indexOf(row.status) !== -1; }).length,
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
      var emptyMessages = {
        queue: 'Keine Einträge in der Warteschlange.',
        sent: 'Noch keine E-Mails gesendet.',
        error: 'Keine Versandfehler vorhanden.',
        drafts: 'Keine Entwürfe vorhanden.'
      };
      tbody.innerHTML = '<tr><td colspan="8">' + escapeHtml(emptyMessages[shippingViewFilter] || 'Keine Versanddaten vorhanden.') + '</td></tr>';
      setText('[data-shipping="table-footer"]', 'Zeige 0 Einträge');
      setText('[data-shipping="page-current"]', '1');
      updateShippingPagination(0, 1);
      updateShippingSelectionMaster(rows);
      applyShippingDetail(null);
      updateShippingSelectionSummary();
      return;
    }
    tbody.innerHTML = visibleRows.map(function(row, index){
      var displayRow = shippingRowPresentation(row);
      var selectable = shippingRowSelectable(row);
      var persnr = String(row.persnr || '');
      var checked = selectable && selectedShippingPersnr[persnr] !== false;
      return '<tr data-shipping-row="' + index + '" class="' + (index === 0 ? 'selected' : '') + '">' +
        '<td><input type="checkbox" data-shipping-select="' + escapeHtml(persnr) + '"' + (checked ? ' checked' : '') + (selectable ? '' : ' disabled') + '></td>' +
        '<td><span class="avatar-mini">' + escapeHtml(row.initials || 'MA') + '</span><b>' + escapeHtml(row.employee || '-') + '<small>' + escapeHtml(row.persnr || '-') + '</small></b></td>' +
        '<td>' + escapeHtml(displayRow.email || '-') + '</td>' +
        '<td><span class="file-dot pdf"><span data-icon="doc"></span></span>' + escapeHtml(displayRow.document || '-') + '</td>' +
        '<td>' + escapeHtml(displayRow.size || '-') + '</td>' +
        '<td><span class="state ' + shippingStatusClass(displayRow.status) + '">' + escapeHtml(displayRow.status || 'Bereit') + '</span></td>' +
        '<td>' + escapeHtml(displayRow.planned || 'Dry-Run') + '</td>' +
        '<td>' + escapeHtml(displayRow.error ? 'Fehler' : '') + '</td>' +
      '</tr>';
    }).join('');
    tbody.querySelectorAll('[data-shipping-select]').forEach(function(input){
      input.addEventListener('change', function(event){
        invalidateShippingPreparation();
        var persnr = input.getAttribute('data-shipping-select') || '';
        if (persnr) selectedShippingPersnr[persnr] = !!input.checked;
        updateShippingSelectionMaster(shippingRows());
        updateShippingSelectionSummary();
        event.stopPropagation();
      });
    });
    tbody.querySelectorAll('[data-shipping-row]').forEach(function(tr){
      tr.addEventListener('click', function(event){
        if (event.target && event.target.matches && event.target.matches('input[type="checkbox"]')) return;
        tbody.querySelectorAll('tr').forEach(function(rowNode){ rowNode.classList.remove('selected'); });
        tr.classList.add('selected');
        applyShippingDetail(shippingRowPresentation(visibleRows[Number(tr.getAttribute('data-shipping-row'))]));
      });
    });
    applyShippingDetail(visibleRows[0] ? shippingRowPresentation(visibleRows[0]) : null);
    var end = start + visibleRows.length;
    setText('[data-shipping="table-footer"]', 'Zeige ' + (start + 1) + ' bis ' + end + ' von ' + rows.length + ' Einträgen');
    setText('[data-shipping="page-current"]', String(currentShippingPage));
    updateShippingPagination(currentShippingPage, totalPages);
    updateShippingSelectionMaster(rows);
    updateShippingSelectionSummary();
  }
  function applyShippingState(state){
    if (!workflowStateMatchesActiveCompany(state)) return;
    var metrics = (state && state.metrics) || {};
    var status = (state && state.status) || {};
    var companyId = String(state && state.company && state.company.id || '');
    var total = Number(metrics.total || 0);
    var ready = Number(metrics.ready || 0);
    var sent = Number(metrics.sent || 0);
    var queued = Number(metrics.queued || 0);
    var errors = Number(metrics.errors || 0);
    var exported = Number(metrics.exported || 0);

    if (
      status.running &&
      shippingTerminalState &&
      shippingTerminalState.companyId === companyId
    ) {
      return;
    }

    // Sent/error rows only arrive after the worker has completed. Normalize a
    // stale running payload in case its terminal signal reached WebChannel first.
    if (status.running && total > 0 && queued === 0 && exported === 0 && (sent > 0 || errors > 0)) {
      status = Object.assign({}, status, {
        running: false,
        finished: true,
        dry_run: false,
        current_step: 'Versand abgeschlossen',
        progress: 100,
        message: 'Versand abgeschlossen. ' + sent + ' E-Mails wurden gesendet.'
      });
      state = Object.assign({}, state, { status: status });
    }

    if (!status.running && (status.finished || status.failed)) {
      shippingTerminalState = {
        companyId: companyId,
        failed: !!status.failed,
        dryRun: status.dry_run !== false
      };
    }

    latestShippingState = state || null;
    syncShippingSelectionDefaults();
    syncShippingLiveProgress(state, status, metrics);
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
    updateShippingFilterControls();

    var readyTrack = document.querySelector('[data-shipping="ready-track"]');
    var sentTrack = document.querySelector('[data-shipping="sent-track"]');
    var queuedTrack = document.querySelector('[data-shipping="queued-track"]');
    if (readyTrack) readyTrack.style.width = readyPercent + '%';
    if (sentTrack) sentTrack.style.width = sentPercent + '%';
    if (queuedTrack) queuedTrack.style.width = queuedPercent + '%';

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
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.getReportsState) {
      updateReportsScreen();
      return;
    }
    bridge.getReportsState(function(payload){
      try {
        var state = JSON.parse(payload || '{}');
        if (!workflowStateMatchesActiveCompany(state)) return;
        var previousReportId = selectedReportId;
        latestReportsState = state;
        var rows = reportRows();
        var selectedStillExists = selectedReportId && rows.some(function(row){ return row.id === selectedReportId; });
        if (!selectedStillExists) {
          var preferredId = String(state.latest_session_id || '').trim();
          var preferredRow = rows.find(function(row){ return row.id === preferredId; }) || rows[0] || null;
          selectedReportId = preferredRow ? preferredRow.id : '';
          selectedReportKind = '';
        }
        if (selectedReportId !== previousReportId) reportsRecipientPage = 1;
        updateReportsScreen();
      } catch (error) {
        console.warn('Berichte state konnte nicht verarbeitet werden', error);
        setReportsMessage('Berichte konnten nicht geladen werden.');
      }
    });
  }
  function startShippingDryRun(){
    var bridge = window.lohnmailBridge;
    if (!bridge || !bridge.startShippingDryRun) {
      setShippingMessage('Bridge ist noch nicht bereit.');
      return;
    }
    shippingTerminalState = null;
    resetShippingLiveProgress();
    bridge.startShippingDryRun(function(payload){
      // State updates arrive through shippingStateChanged/shippingFinished.
      // Applying this start response can overwrite a fast finished signal.
      void payload;
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
    shippingTerminalState = null;
    resetShippingLiveProgress(activeCompanyId(), selectedShippingRows());
    setShippingMessage('E-Mail Versand wird gestartet...');
    setShippingPreviewText('message', 'E-Mail Versand wird gestartet...');
    bridge.startSelectedShippingSend(JSON.stringify(selected), function(payload){
      if (confirmButton) confirmButton.disabled = false;
      closeShippingSendModal();
      // The bridge already emitted this state. A short send can finish before
      // this callback runs, so reapplying the start payload would restore
      // running=true after shippingFinished.
      void payload;
      loadDashboardState();
      loadReportsState();
    });
  }
  function setShippingMessage(message){
    setText('[data-shipping="selection-message"]', message);
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

    setPathText('[data-processing="' + kind + '-path"]', state.path || 'Nicht ausgewählt');
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
      if (!workflowStateMatchesActiveCompany(state)) return null;
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
      bridge.choosePdfInput(function(payload){
        consumeProcessingPayload(payload, 'input');
        loadValidationState();
        loadShippingState();
        loadDashboardState();
      });
      return;
    }
    if (action === 'choose-excel' && bridge.chooseExcelInput) {
      bridge.chooseExcelInput(function(payload){
        consumeProcessingPayload(payload, 'input');
        loadValidationState();
        loadShippingState();
        loadMassMessageState();
        loadDashboardState();
      });
      return;
    }
    if (action === 'open-output' && bridge.openOutputFolder) {
      bridge.openOutputFolder(function(payload){
        try {
          var result = JSON.parse(payload || '{}');
          setInfoBanner(result.message || (result.ok ? 'Ausgabeordner geöffnet.' : 'Ausgabeordner konnte nicht geöffnet werden.'), !!result.ok);
          pushProcessingLog(
            result.ok ? 'ok' : 'error',
            result.ok ? 'Ausgabeordner geöffnet' : 'Ausgabeordner nicht verfügbar',
            result.path || result.message || '',
            'open-output|' + String(result.ok) + '|' + (result.path || '')
          );
        } catch (error) {
          setInfoBanner('Ausgabeordner konnte nicht geöffnet werden.', false);
          pushProcessingLog('error', 'Ausgabeordner nicht verfügbar', 'Ungültige Antwort vom Bridge.', 'open-output|invalid');
        }
      });
      return;
    }
    if (action === 'show-log') {
      renderProcessingLog();
      var logCard = document.querySelector('.page-processing .operation-log');
      var logButton = document.querySelector('.page-processing [data-processing-action="show-log"]');
      var expanded = !!(logCard && logCard.classList.toggle('expanded'));
      if (logButton) logButton.textContent = expanded ? 'Weniger anzeigen' : 'Alle anzeigen';
      setInfoBanner(expanded ? 'Aktivitätsprotokoll vollständig geöffnet.' : 'Aktivitätsprotokoll kompakt angezeigt.', true);
      return;
    }
    if (action === 'start-check' && bridge.startCheck) {
      if (
        latestProcessingState &&
        workflowStateMatchesActiveCompany(latestProcessingState) &&
        latestProcessingState.status &&
        latestProcessingState.status.finished
      ) {
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
        loadValidationState();
        loadShippingState();
        loadDashboardState();
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
    if (normalized === 'Berichte') {
      loadReportsState();
      loadShippingState();
    }
    if (normalized === 'Unternehmen') loadCompanyState();
    if (normalized === 'Lizenzen') loadLicenseState();
    if (normalized === 'Einstellungen') loadSettingsState();
    if (normalized === 'Hilfe') setInfoBanner('Hilfe und Supportübersicht geöffnet.', true);
    if (normalized === 'Über LohnMail') setInfoBanner('Produktinformationen geöffnet.', true);
    updateCompactWorkflowTrackers(normalized);
  }
  window.addEventListener('DOMContentLoaded', function(){
    applyBrandLogoVariant();
    renderHelpKnowledge();
    loadUpdatePreferences();
    renderUpdateSettings();
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
        invalidateShippingPreparation();
        var checked = !!shippingSelectVisible.checked;
        shippingRows().forEach(function(row){
          if (shippingRowSelectable(row)) {
            selectedShippingPersnr[String(row.persnr || '')] = checked;
          }
        });
        renderShippingRows();
        setShippingMessage(shippingSelectionDirty
          ? 'Auswahl geändert. Versand erneut vorbereiten.'
          : (checked ? 'Gefilterte sendbare Einträge wurden markiert.' : 'Gefilterte sendbare Einträge wurden abgewählt.'));
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
    var reportRecipientSearch = document.querySelector('[data-reports-recipients="search"]');
    if (reportRecipientSearch) {
      reportRecipientSearch.addEventListener('input', function(){
        reportsRecipientSearchQuery = reportRecipientSearch.value.trim();
        reportsRecipientPage = 1;
        renderReportRecipients();
      });
    }
    var reportPageSize = document.querySelector('[data-reports="page-size"]');
    if (reportPageSize) reportPageSize.addEventListener('change', function(){
      reportsPageSize = Number(reportPageSize.value) || 10;
      reportsPage = 1;
      renderReportsTable();
    });
    var reportRecipientPageSize = document.querySelector('[data-reports-recipients="page-size"]');
    if (reportRecipientPageSize) reportRecipientPageSize.addEventListener('change', function(){
      reportsRecipientPageSize = Number(reportRecipientPageSize.value) || 20;
      reportsRecipientPage = 1;
      renderReportRecipients();
    });
    document.querySelectorAll('[data-reports-recipient-filter]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        reportsRecipientFilter = button.getAttribute('data-reports-recipient-filter') || 'all';
        reportsRecipientPage = 1;
        renderReportRecipients();
      });
    });
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
    document.querySelectorAll('[data-app-dialog-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        closeAppDialog(button.getAttribute('data-app-dialog-action') === 'confirm');
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
    document.querySelectorAll('[data-license-payment-close]').forEach(function(button){
      button.addEventListener('click', closeLicensePaymentModal);
    });
    document.querySelectorAll('[data-license-payment]').forEach(function(button){
      button.addEventListener('click', function(){
        var method = button.getAttribute('data-license-payment');
        runLicenseAction(method === 'invoice' ? 'buy-invoice' : 'buy-card');
      });
    });
    document.querySelectorAll('[data-license-validation-close]').forEach(function(button){
      button.addEventListener('click', closeLicenseValidationModal);
    });
    var licenseValidationEdit = document.querySelector('[data-license-validation-edit]');
    if (licenseValidationEdit) licenseValidationEdit.addEventListener('click', focusFirstMissingLicenseeField);
    document.querySelectorAll('[data-new-run-close]').forEach(function(button){
      button.addEventListener('click', closeNewRunModal);
    });
    var newRunConfirm = document.querySelector('[data-new-run-confirm]');
    if (newRunConfirm) newRunConfirm.addEventListener('click', function(){
      closeNewRunModal();
      startNewRunNow();
    });
    document.querySelectorAll('[data-licensee-field]').forEach(function(field){
      field.addEventListener('input', function(){
        if (String(field.value || '').trim()) field.classList.remove('licensee-field-missing');
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
        activateSettingsTab(button.getAttribute('data-settings-tab'));
      });
    });
    document.querySelectorAll('[data-update-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        if (button.disabled) return;
        dispatchUpdateAction(button.getAttribute('data-update-action'));
      });
    });
    document.querySelectorAll('[data-update-pref]').forEach(function(input){
      input.addEventListener('change', function(){
        var preference = input.getAttribute('data-update-pref');
        if (preference === 'auto-check') {
          latestUpdateState.auto_check = Boolean(input.checked);
        }
        persistUpdatePreferences();
      });
    });
    var mailTextField = document.querySelector('[data-settings-field="mail_text.body"]');
    var mailHtmlField = document.querySelector('[data-settings-field="mail_text.body_html"]');
    if (mailTextField && mailHtmlField) {
      mailTextField.addEventListener('input', function(){
        mailHtmlField.value = mailTextToHtml(mailTextField.value);
      });
    }
    var mailModeField = document.querySelector('[data-settings-field="mail_mode"]');
    if (mailModeField) mailModeField.addEventListener('change', updateOutlookAccountControl);
    var outlookAccountSelect = document.querySelector('[data-outlook-account-select]');
    if (outlookAccountSelect) outlookAccountSelect.addEventListener('change', function(){
      var fromInput = document.querySelector('[data-settings-field="smtp.from_email"]');
      if (fromInput) fromInput.value = outlookAccountSelect.value || '';
    });
    document.querySelectorAll('[data-mass-action]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        event.stopImmediatePropagation();
        if (button.disabled) return;
        runMassMessageAction(button.getAttribute('data-mass-action'));
      });
    });
    document.querySelectorAll('[data-mass-send-close]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        closeMassSendModal();
        setMassMessage('Versand wurde vor dem Start abgebrochen.');
      });
    });
    document.querySelectorAll('[data-mass-send-action="confirm"]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        if (button.disabled) return;
        startMassMessageSend();
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
        runHelpAction(button.getAttribute('data-help-action'), button);
      });
    });
    var helpSearch = document.querySelector('[data-help-search]');
    if (helpSearch) {
      helpSearch.addEventListener('keydown', function(event){
        if (event.key === 'Enter') {
          event.preventDefault();
          runHelpAction('search', helpSearch);
        }
      });
      helpSearch.addEventListener('input', function(){
        if (!helpSearch.value.trim() && helpSearchQuery) {
          helpSearchQuery = '';
          currentHelpTopic = 'all';
          helpShowAll = false;
          renderHelpKnowledge();
        }
      });
    }
    document.querySelectorAll('[data-help-close]').forEach(function(button){
      button.addEventListener('click', function(event){
        event.preventDefault();
        closeHelpArticle();
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
        var appDialog = document.querySelector('[data-app-dialog]');
        if (appDialog && !appDialog.hidden) closeAppDialog(false);
        closeAboutLegalModal();
        closeHelpArticle();
        closeCompanyCreateModal();
      }
    });
    window.addEventListener('resize', function(){
      document.querySelectorAll('[data-full-path]').forEach(function(node){
        fitPathFromEnd(node, node.dataset.fullPath || '-', 0);
      });
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
          loadValidationState();
          loadShippingState();
          loadDashboardState();
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
