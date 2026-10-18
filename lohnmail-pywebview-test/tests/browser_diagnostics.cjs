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
    await page.route('**/*', route=>route.abort());
    const html=fs.readFileSync(path.join(root,'web/index.html'),'utf8').replace(/<script[\s\S]*?<\/script>/g,'').replace(/<link[^>]+>/g,'');
    await page.setContent(html);
    for (const file of ['styles.css','diagnostics.css']) await page.addStyleTag({content:fs.readFileSync(path.join(root,'web',file),'utf8')});
    await page.addScriptTag({content:fs.readFileSync(path.join(root,'web/diagnostics.js'),'utf8')});
    await page.evaluate(() => {
      document.querySelectorAll('.page').forEach(el=>el.classList.toggle('active',el.dataset.page==='Einstellungen'));
      document.querySelectorAll('[data-settings-panel]').forEach(el=>el.classList.toggle('active',el.dataset.settingsPanel==='advanced'));
      const report={schema:1,id:'11111111-2222-3333-4444-555555555555',operation_id:'12345678-1234-1234-1234-123456789012',
        occurred_at:new Date().toISOString(),version:'2.0.3',build:'2026.09.03.1',platform:'win32',stage:'send',company:{id:'example',name:'Beispielunternehmen'},code:'NETWORK_DNS',frames:[{module:'core/mailer.py',line:42}],events:[]};
      const state={automatic:false,storage_ok:true,pending:0,last_send:'',reports:[{report,sent:false}]};
      window.sentIds=[];
      const api={getDiagnosticsState:cb=>cb(JSON.stringify(state)),setDiagnosticsConsent:(value,cb)=>{state.automatic=value;cb(JSON.stringify(state));},
        sendDiagnosticReport:(id,cb)=>{window.sentIds.push(id);cb(JSON.stringify({ok:true,message:'Bericht zur Übermittlung freigegeben.'}));},
        exportDiagnosticReport:cb=>cb(JSON.stringify({ok:true,message:'Exportiert.'}))};
      window.LohnMailDiagnostics.attach(api);
    });
    for (const width of [1180,1440]) {
      await page.setViewportSize({width,height:850});
      const checkbox=page.locator('#diagnostics-auto'); assert.equal(await checkbox.isChecked(),false);
      await page.locator('#diagnostics-send').click();
      await page.locator('dialog[open]').waitFor();
      assert.equal(await page.locator('dialog').getByText('Unternehmen:',{exact:false}).count(),1);
      assert.equal((await page.evaluate(()=>window.sentIds)).length,0);
      const bounds=await page.locator('dialog').boundingBox(); assert.ok(bounds.x>=0 && bounds.x+bounds.width<=width);
      await page.locator('dialog').getByRole('button',{name:'Abbrechen',exact:true}).click();
    }
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
    console.log('PASS: 1180/1440 layouts, preview/cancel, single manual send, consent independent, compact error, explicit details/copy, Escape; no network.');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
