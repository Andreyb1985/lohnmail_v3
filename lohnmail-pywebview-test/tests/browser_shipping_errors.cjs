// Real HTML/CSS/renderers, synthetic state, no bridge or network access.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const birthDateIssue = JSON.parse(require('node:child_process').execFileSync(
  process.env.LOHNMAIL_TEST_PYTHON || path.resolve(root, '../.venv/bin/python'),
  ['-c', 'import json, sys; from core.shipping_errors import issue_fields; print(json.dumps(issue_fields(sys.argv[1])))',
    process.env.SHIPPING_ERROR_CODE || 'BIRTH_DATE_MISSING'],
  {cwd:root, encoding:'utf8'}));
const source = fs.readFileSync(path.join(root, 'web/app.js'), 'utf8');
function fn(name) {
  const start = source.indexOf('  function ' + name + '(');
  assert.ok(start >= 0);
  return source.slice(start, source.indexOf('\n  function ', start + 1));
}
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROME_EXECUTABLE ? {executablePath:process.env.CHROME_EXECUTABLE} : {})});
  try {
    const page = await browser.newPage();
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.route('**/*', route => route.abort());
    const html = fs.readFileSync(path.join(root, 'web/index.html'), 'utf8').replace(/<script[\s\S]*?<\/script>/g, '').replace(/<link[^>]+>/g, '');
    await page.setContent(html);
    await page.addStyleTag({content:fs.readFileSync(path.join(root, 'web/styles.css'), 'utf8')});
    await page.addScriptTag({content:`
      var latestShippingState, shippingRevision=-1, shippingTerminalState=null;
      var shippingLiveProgress={phase:'idle'}, shippingViewFilter='error', shippingStatusFilter='all';
      var currentShippingPage=1, shippingPageSize=20, selectedShippingPersnr={};
      function setText(selector,text){document.querySelectorAll(selector).forEach(el=>el.textContent=text);}
      function workflowStateMatchesActiveCompany(){return true;}
      function shippingRows(){return latestShippingState.rows;}
      function selectedShippingRows(){return latestShippingState.rows;}
      function shippingRowSelectable(){return true;}
      function shippingStatusClass(){return 'error';}
      function updateShippingPagination(){} function updateShippingSelectionMaster(){}
      function updateShippingSelectionSummary(){} function applyShippingDetail(){}
      function syncShippingSelectionDefaults(){} function updateShippingFilterControls(){}
      function updateCompactWorkflowTrackers(){} function updateDashboardPipeline(){}
      function updateWarningCenter(){} function updateReportsScreen(){}
      ${['escapeHtml','resetShippingLiveProgress','syncShippingLiveProgress','updateShippingLiveProgressPanel',
          'shippingRowPresentation','renderShippingRows','renderShippingIssues','applyShippingState'].map(fn).join('\n')}
    `});
    await page.evaluate((issue) => {
      document.querySelectorAll('.page').forEach(el => el.classList.toggle('active', el.dataset.page === 'Versand'));
      document.querySelector('.page-breadcrumb strong').textContent = 'Versand';
      window.showFixture = (outcome='failed') => {
        const bad = {persnr:'00022',employee:'Max Beispiel',email:'max@example.invalid',document:'00022.pdf',status:'Fehler',
          error_code:issue.ErrorCode,error_title:issue.ErrorTitle,
          error_action:issue.ErrorAction,error:issue.Error};
        const second = {...bad,persnr:'00023',employee:'Anna Beispiel'};
        if(outcome==='partial') Object.assign(second,{status:'Dry-Run',error:'',error_code:'',error_title:'',error_action:''});
        if(outcome==='success') Object.assign(bad,{status:'Dry-Run',error:''});
        const rows = outcome==='success' ? [bad] : [bad,second];
        applyShippingState({revision:++window.fixtureRevision,company:{id:'test'},rows,
          metrics:{total:rows.length,errors:outcome==='failed'?2:outcome==='partial'?1:0},
          status:{operation_id:'fixture'+window.fixtureRevision,dry_run:true,running:false,
            finished:outcome!=='failed',failed:outcome==='failed',outcome,
            prepared:outcome==='failed'?0:1,errors:outcome==='failed'?2:outcome==='partial'?1:0,processed:rows.length,
            message:outcome==='failed'?'0 Mitarbeiter-PDFs vorbereitet · 2 Fehler. Ursachen unten prüfen.':'Vorbereitung beendet.'}});
      };
      window.fixtureRevision = 0;
      showFixture();
    }, birthDateIssue);
    for (const width of [760,1180,1440]) {
      await page.setViewportSize({width,height:1100});
      await page.evaluate(() => showFixture());
      assert.equal(await page.locator('[data-shipping-live="title"]').innerText(), 'Vorbereitung fehlgeschlagen');
      assert.equal(await page.locator('[data-shipping-live="count"]').innerText(), '2/2');
      assert.ok(await page.locator('.shipping-live-progress').evaluate(el => el.classList.contains('is-failed') && !el.classList.contains('is-complete')));
      const panel = page.locator('[data-shipping="issues"]');
      assert.match(await panel.innerText(), /Geburtsdatum.*2 betroffen/s);
      assert.ok((await panel.innerText()).includes(birthDateIssue.ErrorAction));
      assert.equal(await panel.evaluate(el => el.scrollWidth <= el.clientWidth + 1), true);
      assert.equal(await page.locator('.shipping-issue-row').count(), 2);
      assert.equal(await page.locator('.mailing-table-scroll').evaluate(el => el.clientHeight >= el.querySelector('table').getBoundingClientRect().height - 1), true);
      assert.equal(await page.locator('.shipping-issue-row td').first().evaluate(el => getComputedStyle(el).whiteSpace), 'normal');
      await page.evaluate(() => showFixture('partial'));
      assert.ok(await page.locator('.shipping-live-progress').evaluate(el => el.classList.contains('is-warning') && !el.classList.contains('is-complete')));
    }
    await page.evaluate(() => showFixture());
    await page.locator('.page-mailing').screenshot({path:'/private/tmp/lohnmail-shipping-errors.png'});
    // User-controlled values remain text; the latest final row replaces generic live errors.
    await page.evaluate(() => {
      const row = latestShippingState.rows[0];
      row.employee='<img src=x onerror="window.injected=true">'; row.error='<script>window.injected=true</script>';
      shippingLiveProgress.selected[row.persnr]={}; shippingLiveProgress.processed[row.persnr]={status:'Fehler',error:'generic'};
      renderShippingRows();
    });
    assert.equal(await page.evaluate(() => !!window.injected), false);
    assert.equal(await page.locator('[data-shipping="issues"] img').count(), 0);
    assert.match(await page.locator('.shipping-issue-row').first().innerText(), /<script>/);
    await page.evaluate(() => showFixture('success'));
    assert.equal(await page.locator('[data-shipping="issues"]').isVisible(), false);
    assert.ok(await page.locator('.shipping-live-progress').evaluate(el => el.classList.contains('is-complete')));
    assert.deepEqual(errors, []);
    console.log('Shipping failures, partial success, recovery, escaping and layouts 760/1180/1440 passed');
  } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exitCode=1;});
