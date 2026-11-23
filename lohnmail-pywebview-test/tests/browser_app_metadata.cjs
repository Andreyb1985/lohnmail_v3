// Real UI + Promise-based pywebview adapter; network and backend are mocked.
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROME_EXECUTABLE});
  try {
    for (const scenario of [
      {name:'mac-website', version:'2.2.0', build:'2026102203', supported:true, manual:true},
      {name:'mac-store', version:'2.2.0', build:'2026101902', supported:false},
      {name:'windows-source', version:'2.2.0', build:'2026.10.20.2', supported:true},
      {name:'future-release', version:'9.8.7', build:'2030010109', supported:true},
      {name:'without-updater', version:'2.2.0', build:'2026102203', supported:true, noUpdater:true},
      {name:'unavailable', invalid:true, supported:false},
    ]) {
      const page = await browser.newPage({viewport:{width:1440,height:1000}});
      const errors=[];
      page.on('pageerror', e => errors.push(e.message));
      await page.route('**/*', r => r.abort());
      const root=path.resolve(__dirname,'../web');
      await page.setContent(fs.readFileSync(path.join(root,'index.html'),'utf8').replace(/<script[\s\S]*?<\/script>/g,'').replace(/<link[^>]+>/g,''));
      await page.addStyleTag({content:fs.readFileSync(path.join(root,'styles.css'),'utf8')});
      await page.evaluate(s => {
        window.pywebview={api:{
          // Delayed identity must win over an earlier updater response.
          getAppInfo: () => new Promise(resolve => setTimeout(() => resolve(JSON.stringify(
            s.invalid ? {ok:false,message:'unavailable'} : {version:s.version,build:s.build})),50)),
          getUpdateState: async () => JSON.stringify({supported:s.supported,manual_download:!!s.manual,
            auto_check:false,installed_version:'1.0.0',installed_build:'1',status:'idle'}),
        }};
        if (s.noUpdater) delete window.pywebview.api.getUpdateState;
      },scenario);
      await page.addScriptTag({content:fs.readFileSync(path.join(root,'app.js'),'utf8')});
      await page.evaluate(() => window.dispatchEvent(new Event('DOMContentLoaded')));
      if (scenario.invalid) {
        await page.waitForTimeout(100);
        assert.equal(await page.locator('[data-app-version="sidebar"]').textContent(),'Enterprise Edition');
        assert.equal(await page.locator('[data-app-version="about"]').textContent(),'—');
      } else {
        await page.waitForFunction(v => document.querySelector('[data-app-version="sidebar"]').textContent === 'v'+v+' Enterprise Edition',scenario.version);
        assert.equal(await page.title(),`LohnMail ${scenario.version} — Enterprise Edition`);
        assert.equal(await page.locator('[data-app-version="about"]').textContent(),`v${scenario.version} (Build ${scenario.build})`);
        assert.equal(await page.locator('[data-update="installed-version"]').textContent(),'v'+scenario.version);
        assert.equal(await page.locator('[data-update="installed-build"]').textContent(),'Build '+scenario.build);
        await page.evaluate(() => window.lohnmailApplyUpdateState({status:'available',installed_version:'0.1',installed_build:'1',available_version:'10.0.0'}));
        assert.equal(await page.locator('[data-update="installed-version"]').textContent(),'v'+scenario.version);
        assert.equal(await page.locator('[data-update="release-version"]').textContent(),'Version 10.0.0');
        if (!scenario.supported) assert.equal(await page.locator('[data-settings-panel="updates"]').isHidden(),true);
        if (scenario.name==='mac-website') {
          await page.evaluate(() => {
            document.querySelectorAll('.page').forEach(n=>n.classList.toggle('active',n.dataset.page==='Über LohnMail'));
          });
          await page.screenshot({path:'/private/tmp/lohnmail-version-unified.png'});
        }
      }
      assert.deepEqual(errors,[]);
      console.log(scenario.name+': PASS');
      await page.close();
    }
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
