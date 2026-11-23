// Real Python filename/settings bridge, synthetic files, no SMTP or external network.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const {spawn}=require('node:child_process'), readline=require('node:readline');
const root=path.resolve(__dirname,'..');
const python=spawn(process.env.LOHNMAIL_TEST_PYTHON||path.join(root,'../.venv/bin/python'),
  [path.join(__dirname,'pdf_rules_browser_backend.py')],{cwd:root,stdio:['pipe','pipe','inherit']});
let sequence=0;const pending=new Map();
readline.createInterface({input:python.stdout}).on('line',line=>{
  const value=JSON.parse(line), p=pending.get(value.id);if(!p)return;
  pending.delete(value.id);clearTimeout(p.timeout);
  value.error?p.reject(new Error(value.error)):p.resolve(value.result);
});
const rpc=(method,args=[])=>new Promise((resolve,reject)=>{
  const id=++sequence,timeout=setTimeout(()=>{pending.delete(id);reject(new Error('Python bridge timeout'));},10000);
  pending.set(id,{resolve,reject,timeout});python.stdin.write(JSON.stringify({id,method,args})+'\n');
});
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.CHROME_EXECUTABLE?{executablePath:process.env.CHROME_EXECUTABLE}:{})});
  try{
    const page=await browser.newPage();const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.route('**/*',route=>{
      const url=new URL(route.request().url()), asset=path.resolve(root,'web',decodeURIComponent(url.pathname).replace(/^\//,''));
      if(url.origin==='http://lohnmail.test'&&asset.startsWith(path.join(root,'web/assets')+path.sep)&&fs.existsSync(asset)){
        const types={'.svg':'image/svg+xml','.png':'image/png','.woff2':'font/woff2'};
        return route.fulfill({body:fs.readFileSync(asset),contentType:types[path.extname(asset)]||'application/octet-stream'});
      }
      return route.abort();
    });
    await page.exposeFunction('testPdfRpc',rpc);
    const html=fs.readFileSync(path.join(root,'web/index.html'),'utf8').replace(/<script[\s\S]*?<\/script>/g,'').replace(/<link[^>]+>/g,'');
    await page.setContent(html.replace('<head>','<head><base href="http://lohnmail.test/">'));
    for(const file of ['styles.css','pdf-filenames.css'])await page.addStyleTag({content:fs.readFileSync(path.join(root,'web',file),'utf8')});
    await page.addScriptTag({content:fs.readFileSync(path.join(root,'web/pdf-filenames.js'),'utf8')});
    const attach=()=>page.evaluate(()=>{
      const api={};
      ['getPdfFilenameState','choosePdfFilenameExample','choosePdfFilenameFolder','previewPdfFilename','savePdfFilenameRule'].forEach(method=>{
        api[method]=(...args)=>{const cb=args.pop();window.testPdfRpc(method,args).then(value=>cb(JSON.stringify(value)));};
      });
      window.LohnMailPdfFilenames.attach(api);
    });
    await page.evaluate(()=>{
      document.querySelectorAll('.page').forEach(el=>el.classList.toggle('active',el.dataset.page==='Einstellungen'));
      document.querySelectorAll('[data-settings-panel]').forEach(el=>el.classList.toggle('active',el.dataset.settingsPanel==='pdf-files'));
      document.querySelectorAll('[data-settings-tab]').forEach(el=>el.classList.toggle('active',el.dataset.settingsTab==='pdf-files'));
      document.querySelector('.page-breadcrumb strong').textContent='Einstellungen';
      document.querySelector('.page-breadcrumb > span').textContent='Konfiguration und lokale Defaults';
      document.querySelectorAll('[data-company-switch="name"]').forEach(el=>el.textContent='Musterfirma GmbH');
      document.querySelectorAll('[data-company-switch="status"]').forEach(el=>el.textContent='musterfirma · Excel bereit');
      document.querySelector('.side-version').textContent='v2.2.0 Enterprise Edition';
      document.querySelectorAll('[data-company-switch="initials"]').forEach(el=>el.textContent='MF');
      document.querySelectorAll('.nav-item').forEach(el=>el.classList.toggle('active',el.textContent.trim()==='Einstellungen'));
    });
    await attach();
    await page.waitForFunction(()=>!document.getElementById('pdf-rule-fields').disabled);
    assert.equal(await page.locator('[name="pdf-rule-mode"][value="standard"]').isChecked(),true);
    await page.locator('[name="pdf-rule-mode"][value="custom"]').check();
    await page.locator('#pdf-rule-choose').click();
    await page.getByRole('button',{name:'Teil 4: 00022',exact:true}).click();
    await page.waitForFunction(()=>document.getElementById('pdf-rule-preview').textContent.includes('Max Mustermann'));
    const out=process.env.LOHNMAIL_SCREENSHOTS||'/private/tmp/lohnmail-pdf-filenames';
    fs.mkdirSync(out,{recursive:true});
    for(const width of [760,1180,1586]){
      await page.setViewportSize({width,height:1450});
      const issues=await page.locator('.pdf-rule-card').evaluate(card=>{
        const bounds=card.getBoundingClientRect();
        return [...card.querySelectorAll('button,input,select,p,h2,h3,label')].filter(el=>el.getClientRects().length).filter(el=>{
          const r=el.getBoundingClientRect();return r.left<bounds.left-1||r.right>bounds.right+1;
        }).map(el=>el.id||el.tagName);
      });assert.deepEqual(issues,[]);
      await page.evaluate(()=>document.querySelectorAll('*').forEach(el=>{if(el.scrollTop)el.scrollTop=0;}));
      await page.evaluate(()=>Promise.all(document.getAnimations().map(animation=>animation.finished.catch(()=>{}))));
      await page.screenshot({path:path.join(out,`pdf-dateien-${width}.png`)});
    }
    await page.locator('#pdf-rule-test').click();
    await page.waitForFunction(()=>document.getElementById('pdf-rule-counts').textContent.includes('3 von 5'));
    assert.equal(await page.locator('#pdf-rule-rows tr').count(),5);
    assert.equal(await page.locator('#pdf-rule-rows tr[data-problem="true"]').count(),2);
    await page.setViewportSize({width:1586,height:1750});
    await page.evaluate(()=>document.querySelectorAll('*').forEach(el=>{if(el.scrollTop)el.scrollTop=0;}));
    await page.screenshot({path:path.join(out,'ordner-pruefung.png')});
    await page.locator('#pdf-rule-save').click();
    await page.waitForFunction(()=>document.getElementById('pdf-rule-status').textContent.includes('gespeichert.'));
    assert.deepEqual((await rpc('getPdfFilenameState')).rule,{mode:'custom',separator:'_',index:3,parts:6});
    await rpc('switchCompany',['b']);
    await page.evaluate(()=>window.LohnMailPdfFilenames.companyChanged('b'));
    await page.waitForFunction(()=>document.getElementById('pdf-rule-company').textContent.includes('Beispielunternehmen'));
    assert.equal(await page.locator('[name="pdf-rule-mode"][value="standard"]').isChecked(),true);
    await rpc('switchCompany',['a']);await rpc('restart');
    await page.evaluate(()=>window.LohnMailPdfFilenames.companyChanged('a'));
    await page.waitForFunction(()=>document.querySelector('[name="pdf-rule-mode"][value="custom"]').checked);
    await page.locator('#pdf-rule-reset').click();await page.locator('#pdf-rule-cancel').click();
    await page.waitForFunction(()=>document.querySelector('[name="pdf-rule-mode"][value="custom"]').checked);
    await page.locator('#pdf-rule-reset').click();await page.locator('#pdf-rule-save').click();
    await page.waitForFunction(()=>document.getElementById('pdf-rule-status').textContent.includes('gespeichert.'));
    await rpc('restart');assert.deepEqual((await rpc('getPdfFilenameState')).rule,{mode:'standard'});
    await page.locator('[name="pdf-rule-mode"][value="content"]').check();
    assert.equal(await page.locator('#pdf-rule-custom').isVisible(),false);
    assert.equal(await page.locator('#pdf-rule-content').isVisible(),true);
    await page.locator('#pdf-rule-test').click();
    await page.waitForFunction(()=>document.getElementById('pdf-rule-counts').textContent.includes('3 von 5'));
    assert.equal(await page.locator('#pdf-rule-rows tr[data-problem="true"]').count(),2);
    for(const width of [760,1180,1586]){
      await page.setViewportSize({width,height:1450});
      await page.evaluate(()=>document.querySelectorAll('*').forEach(el=>{if(el.scrollTop)el.scrollTop=0;}));
      await page.evaluate(()=>Promise.all(document.getAnimations().map(a=>a.finished.catch(()=>{}))));
      const overflow=await page.locator('.pdf-rule-modes').evaluate(el=>el.scrollWidth>el.clientWidth+1);
      assert.equal(overflow,false);
      await page.screenshot({path:path.join(out,`pdf-inhalt-${width}.png`)});
    }
    await page.locator('#pdf-rule-save').click();
    await page.waitForFunction(()=>document.getElementById('pdf-rule-status').textContent.includes('gespeichert.'));
    await rpc('restart');assert.deepEqual((await rpc('getPdfFilenameState')).rule,{mode:'content'});
    await rpc('switchCompany',['b']);await page.evaluate(()=>window.LohnMailPdfFilenames.companyChanged('b'));
    await page.waitForFunction(()=>document.querySelector('[name="pdf-rule-mode"][value="standard"]').checked);
    await rpc('switchCompany',['a']);await page.evaluate(()=>window.LohnMailPdfFilenames.companyChanged('a'));
    await page.waitForFunction(()=>document.querySelector('[name="pdf-rule-mode"][value="content"]').checked);
    await page.locator('#pdf-rule-reset').click();await page.locator('#pdf-rule-save').click();
    await page.waitForFunction(()=>document.getElementById('pdf-rule-status').textContent.includes('gespeichert.'));
    await rpc('restart');assert.deepEqual((await rpc('getPdfFilenameState')).rule,{mode:'standard'});
    assert.deepEqual(errors,[]);
    console.log('PASS: real Python bridge; filename + PDF content modes, Excel preview, folder problems, save, company isolation, cancel/reset/restart; 760/1180/1586 layouts; no external network/mail.');
  }finally{await browser.close();python.stdin.end();}
})().catch(error=>{console.error(error);python.kill();process.exitCode=1;});
