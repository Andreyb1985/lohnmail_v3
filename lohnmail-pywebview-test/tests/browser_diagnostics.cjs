// Synthetic browser check; never starts the app or contacts any server.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHROME_EXECUTABLE ? {executablePath:process.env.CHROME_EXECUTABLE} : {})});
  try {
    const page = await browser.newPage();
    const errors=[]; page.on('pageerror',error=>errors.push(error.message));
    // Serve only local static assets from memory; all external requests blocked.
    await page.route('**/*', route=>{
      const url=new URL(route.request().url());
      const asset=path.resolve(root,'web',decodeURIComponent(url.pathname).replace(/^\//,''));
      if(url.origin==='http://lohnmail.test' && asset.startsWith(path.join(root,'web/assets')+path.sep) && fs.existsSync(asset)) {
        const ext=path.extname(asset), types={'.svg':'image/svg+xml','.png':'image/png','.woff2':'font/woff2'};
        return route.fulfill({body:fs.readFileSync(asset),contentType:types[ext]||'application/octet-stream'});
      }
      return route.abort();
    });
    const html=fs.readFileSync(path.join(root,'web/index.html'),'utf8').replace(/<script[\s\S]*?<\/script>/g,'').replace(/<link[^>]+>/g,'');
    await page.setContent(html.replace('<head>','<head><base href="http://lohnmail.test/">'));
    for (const file of ['styles.css','diagnostics.css']) await page.addStyleTag({content:fs.readFileSync(path.join(root,'web',file),'utf8')});
    await page.addScriptTag({content:fs.readFileSync(path.join(root,'web/diagnostics.js'),'utf8')});
    await page.evaluate(() => {
      document.querySelectorAll('.page').forEach(el=>el.classList.toggle('active',el.dataset.page==='Einstellungen'));
      document.querySelectorAll('[data-settings-panel]').forEach(el=>el.classList.toggle('active',el.dataset.settingsPanel==='advanced'));
      document.querySelectorAll('[data-settings-tab]').forEach(el=>el.classList.toggle('active',el.dataset.settingsTab==='advanced'));
      document.querySelector('.page-breadcrumb strong').textContent='Einstellungen';
      document.querySelector('.page-breadcrumb > span').textContent='Konfiguration und lokale Defaults';
      document.querySelectorAll('.nav-item').forEach(el=>el.classList.toggle('active',el.textContent.trim()==='Einstellungen'));
      const report={schema:1,id:'11111111-2222-3333-4444-555555555555',operation_id:'12345678-1234-1234-1234-123456789012',
        occurred_at:new Date().toISOString(),version:'2.0.3',build:'2026.09.03.1',platform:'win32',stage:'send',company:{id:'example',name:'Beispielunternehmen'},code:'NETWORK_DNS',frames:[{module:'core/mailer.py',line:42}],events:[]};
      const state={automatic:false,storage_ok:true,pending:0,last_send:'',reports:[]};
      window.sentIds=[];
      let changed;
      window.diagnosticFixture={state,report,render:()=>changed(JSON.stringify(state))};
      const api={getDiagnosticsState:cb=>cb(JSON.stringify(state)),setDiagnosticsConsent:(value,cb)=>{state.automatic=value;cb(JSON.stringify(state));},
        diagnosticsStateChanged:{connect:handler=>{changed=handler;}},
        sendDiagnosticReport:(id,cb)=>{window.sentIds.push(id);cb(JSON.stringify({ok:true,message:'Bericht zur Übermittlung freigegeben.'}));},
        exportDiagnosticReport:cb=>cb(JSON.stringify({ok:true,message:'Exportiert.'}))};
      window.LohnMailDiagnostics.attach(api);
    });
    const layout=async()=>{
      const issues=await page.locator('.diagnostics-card').evaluateAll(cards=>cards.flatMap(card=>{
        const bounds=card.getBoundingClientRect();
        return (card.scrollWidth>card.clientWidth+1?['card overflow']:[]).concat(Array.from(card.querySelectorAll('button,input,select,h2,h3,p,label,summary')).filter(el=>el.getClientRects().length && !el.closest('details:not([open]) p')).flatMap(el=>{
          const b=el.getBoundingClientRect();return b.left<bounds.left-1||b.right>bounds.right+1? [el.id||el.tagName]:[];
        }));
      }));
      assert.deepEqual(issues,[]);
    };
    for (const width of [760,1180,1440]) {
      await page.setViewportSize({width,height:1000});
      assert.equal(await page.locator('#diagnostics-empty').isVisible(),true);
      assert.equal(await page.locator('#diagnostics-report-controls').isVisible(),false);
      assert.equal(await page.locator('#diagnostics-status').isVisible(),false);
      assert.equal(await page.locator('#diagnostics-auto').evaluate(el=>getComputedStyle(el).appearance),'none');
      await page.waitForFunction(()=>getComputedStyle(document.getElementById('diagnostics-send')).backgroundColor==='rgb(0, 131, 87)',null,{timeout:3000});
      await layout();
    }
    await page.locator('.page-settings').screenshot({path:'/private/tmp/lohnmail-diagnostics-settings-empty.png'});
    await page.evaluate(()=>{const f=window.diagnosticFixture;f.state.reports=[{report:f.report,sent:false}];f.render();});
    assert.equal(await page.locator('#diagnostics-report-picker').isVisible(),false);
    assert.equal(await page.locator('#diagnostics-report-title').innerText(),'E-Mail-Server nicht gefunden');
    for (const width of [760,1180,1440]) {
      await page.setViewportSize({width,height:850});
      const checkbox=page.locator('#diagnostics-auto'); assert.equal(await checkbox.isChecked(),false);
      await page.locator('#diagnostics-send').click();
      await page.locator('dialog[open]').waitFor();
      assert.equal(await page.locator('dialog').getByText('Unternehmen:',{exact:false}).count(),1);
      assert.equal((await page.evaluate(()=>window.sentIds)).length,0);
      const bounds=await page.locator('dialog').boundingBox(); assert.ok(bounds.x>=0 && bounds.x+bounds.width<=width);
      await page.locator('dialog').getByRole('button',{name:'Abbrechen',exact:true}).click();
      await layout();
    }
    await page.evaluate(()=>{const f=window.diagnosticFixture;f.state.reports.push({report:{...f.report,id:'22222222-2222-3333-4444-555555555555',code:'SMTP_AUTH',company:{id:'two',name:'Beispielunternehmen mit einem sehr langen Namen '.repeat(5)}},sent:true});f.render();});
    await page.locator('#diagnostics-report').selectOption('22222222-2222-3333-4444-555555555555');
    await page.evaluate(()=>window.diagnosticFixture.render());
    assert.equal(await page.locator('#diagnostics-report').inputValue(),'22222222-2222-3333-4444-555555555555');
    assert.ok((await page.locator('#diagnostics-report-meta').innerText()).includes('Übermittelt'));
    for(const width of [760,1180,1440]){await page.setViewportSize({width,height:1000});await layout();}
    await page.locator('#diagnostics-report').selectOption('11111111-2222-3333-4444-555555555555');
    await page.locator('.page-settings').screenshot({path:'/private/tmp/lohnmail-diagnostics-settings-reports.png'});
    await page.setViewportSize({width:760,height:1000});
    await page.locator('.page-settings').screenshot({path:'/private/tmp/lohnmail-diagnostics-settings-narrow.png'});
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('#diagnostics-export').click();
    assert.equal(await page.locator('#diagnostics-status').innerText(),'Exportiert.');
    assert.equal((await page.evaluate(()=>window.sentIds)).length,0);
    await page.locator('.diagnostics-privacy summary').click();
    assert.ok((await page.locator('.diagnostics-privacy').innerText()).includes('Lizenzschlüssel und Computer-ID'));
    await layout();
    await page.locator('.diagnostics-privacy summary').click();
    await page.locator('#diagnostics-send').click();
    await page.getByRole('button',{name:'Diesen Bericht senden',exact:true}).click();
    assert.equal((await page.evaluate(()=>window.sentIds)).length,1);
    assert.equal(await page.locator('#diagnostics-auto').isChecked(),false);
    await page.getByRole('button',{name:'Abbrechen',exact:true}).click();
    await page.locator('#diagnostics-auto').check();
    assert.equal(await page.locator('#diagnostics-auto').isChecked(),true);
    await page.locator('#diagnostics-auto').uncheck();
    await page.evaluate(()=>window.LohnMailDiagnostics.showError({message:'Verbindung fehlgeschlagen. '.repeat(40)+'ENDE_DER_MELDUNG'}));
    await page.locator('dialog[open]').waitFor();
    assert.equal(await page.locator('dialog h2').innerText(),'SMTP-Server nicht gefunden');
    assert.equal(await page.locator('dialog pre, dialog details').count(),0);
    assert.equal(await page.locator('dialog button').count(),1);
    assert.equal(await page.getByRole('button',{name:'OK',exact:true}).count(),1);
    assert.ok((await page.locator('dialog').boundingBox()).width <= 540);
    await page.screenshot({path:process.env.DIAGNOSTICS_SCREENSHOT || '/private/tmp/lohnmail-diagnostics-ui.png'});
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('dialog[open]').count(),0);
    await page.locator('#diagnostics-details').click();
    assert.equal(await page.locator('dialog pre').count(),1);
    await page.getByRole('button',{name:'Details kopieren'}).click();
    await page.keyboard.press('Escape');
    assert.deepEqual(errors,[]);
    console.log('PASS: 760/1180/1440 layouts, empty/single/multiple reports, long text, selection preserved, preview/cancel, single manual send, consent independent, compact error, explicit details/copy, Escape; no external network.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
