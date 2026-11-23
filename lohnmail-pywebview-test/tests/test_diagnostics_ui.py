"""Execute the real diagnostics UI with a synthetic DOM and mocked bridge."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_errors_are_compact_but_explicit_reports_keep_preview_and_consent():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for diagnostics renderer")
    source = Path(__file__).resolve().parents[1] / "web/diagnostics.js"
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const nodes=new Map();
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.handlers={};this.value='';this.open=false;this.isConnected=true;}
 set textContent(value){this.text=String(value);this.children=[];}
 get textContent(){return (this.text||'')+this.children.map(c=>c.textContent).join(' ');}
 get options(){return this.children;}
 appendChild(child){this.children.push(child);return child;}
 replaceChildren(){this.children=[];this.text='';}
 setAttribute(k,v){this[k]=v;}
 removeAttribute(k){delete this[k];}
 addEventListener(k,v){this.handlers[k]=v;}
 focus(){document.activeElement=this;}
 showModal(){this.open=true;}
 close(){this.open=false;this.handlers.close?.();}
}
const document={body:new Element('body'),activeElement:new Element('button'),querySelector:()=>({value:'smtp'}),
 createElement:tag=>new Element(tag),getElementById:id=>{
   if(!nodes.has(id))nodes.set(id,new Element(id==='diagnostics-report'?'select':'button'));
   return nodes.get(id);
 }};
const report={id:'synthetic-report',code:'NETWORK_DNS',stage:'mail_test',occurred_at:new Date().toISOString(),
 company:{id:'example',name:'Example'},frames:[],events:[]};
let state={reports:[{report,sent:false}],automatic:false,pending:0},sent=0,copied='',opened=0;
const c={window:{lohnmailOpenMailSettings:()=>opened++},document,console,Date,setTimeout:()=>0,clearTimeout(){},setInterval:()=>0,clearInterval(){},
 navigator:{clipboard:{writeText:async text=>{copied=text;}}}};
vm.createContext(c);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),c);
const api=c.window.LohnMailDiagnostics;
api.attach({getDiagnosticsState:cb=>cb(JSON.stringify(state)),
 sendDiagnosticReport:(id,cb)=>{sent++;cb(JSON.stringify({message:'queued'}));}});
const dialog=()=>document.body.children.find(n=>n.tag==='dialog');
const all=(tag,n=dialog())=>n.children.flatMap(c=>[...(c.tag===tag?[c]:[]),...all(tag,c)]);
(async()=>{
 await api.showError({message:'PRIVATE LONG ERROR '.repeat(100)});
 assert.equal(all('h2')[0].textContent,'SMTP-Server nicht gefunden');
 assert.equal(all('button').length,2);assert.equal(all('button')[1].textContent,'OK');
 assert.equal(document.activeElement,all('button')[1]);
 assert.ok(all('p')[0].textContent.includes('SMTP-Serveradresse'));
 assert.equal(all('details').length,0);assert.equal(all('pre').length,0);
 assert.ok(!dialog().textContent.includes('synthetic-report'));
 assert.ok(!dialog().textContent.includes('PRIVATE'));
 assert.ok(dialog().className.includes('diagnostics-error-dialog'));
 all('button')[0].onclick();assert.equal(dialog().open,false);assert.equal(opened,1);assert.equal(sent,0);
 await api.showError({code:'NETWORK_DNS',stage:'license'});
 assert.equal(all('h2')[0].textContent,'Server nicht gefunden');assert.equal(all('button').length,1);
 await api.showError({code:'NETWORK_TIMEOUT',stage:'send'});
 assert.equal(all('h2')[0].textContent,'SMTP-Server antwortet nicht');assert.equal(all('button').length,2);
 await api.showError({code:'SMTP_AUTH'});
 assert.equal(all('h2')[0].textContent,'Anmeldung am Mailserver fehlgeschlagen');
 await api.showError({code:'UNKNOWN',message:'technical details'});
 assert.equal(all('h2')[0].textContent,'Vorgang fehlgeschlagen');
 assert.equal(all('button').length,1);
 await api.showError('invalid JSON');assert.equal(all('h2')[0].textContent,'Vorgang fehlgeschlagen');
 state={...state,reports:[]};await api.showError({message:'no report available'});
 assert.equal(all('h2')[0].textContent,'Vorgang fehlgeschlagen');assert.equal(sent,0);
 assert.equal(nodes.get('diagnostics-empty').hidden,false);
 assert.equal(nodes.get('diagnostics-report-controls').hidden,true);
 assert.equal(nodes.get('diagnostics-details').disabled,true);
 assert.equal(nodes.get('diagnostics-pending').textContent,'Keine ausstehenden Berichte');
 assert.equal(nodes.get('diagnostics-status').hidden,true);
 state={...state,reports:[{report,sent:false}]};await api.showError({});
 assert.equal(nodes.get('diagnostics-empty').hidden,true);
 assert.equal(nodes.get('diagnostics-report-controls').hidden,false);
 assert.equal(nodes.get('diagnostics-report-picker').hidden,true);
 assert.equal(nodes.get('diagnostics-report-title').textContent,'E-Mail-Server nicht gefunden');
 assert.ok(nodes.get('diagnostics-report-meta').textContent.includes('Lokal gespeichert'));
 const second={...report,id:'second-report',code:'SMTP_AUTH',company:{id:'two',name:'<b>Example Two</b>'}};
 state={...state,pending:1,reports:[{report,sent:false},{report:second,sent:true}]};await api.showError({});
 assert.equal(nodes.get('diagnostics-report-picker').hidden,false);
 nodes.get('diagnostics-report').value=second.id;nodes.get('diagnostics-report').onchange();
 assert.equal(nodes.get('diagnostics-report-title').textContent,'Anmeldung am Mailserver fehlgeschlagen');
 assert.ok(nodes.get('diagnostics-report-meta').textContent.includes('<b>Example Two</b>'));
 assert.equal(nodes.get('diagnostics-report-meta').children.length,0); // text, never HTML
 await api.showError({}); // polling must preserve selection and selected report details
 assert.equal(nodes.get('diagnostics-report').value,second.id);
 assert.ok(nodes.get('diagnostics-report-meta').textContent.includes('Übermittelt'));
 assert.equal(nodes.get('diagnostics-pending').textContent,'Ausstehende Berichte: 1');
 state={...state,automatic:true,storage_ok:false,last_send:'Übertragung fehlgeschlagen'};await api.showError({});
 assert.ok(nodes.get('diagnostics-consent-caption').textContent.includes('Eingeschaltet'));
 assert.ok(nodes.get('diagnostics-status').textContent.includes('nicht gespeichert'));
 assert.equal(nodes.get('diagnostics-status').hidden,false);
 state={...state,automatic:false,storage_ok:true,pending:0,last_send:'',reports:[{report,sent:false}]};await api.showError({});
 // Detailed metadata is still accessible only by explicit settings action.
 nodes.get('diagnostics-details').onclick();
 assert.equal(all('h2')[0].textContent,'Fehlerdetails');
 assert.equal(all('pre').length,1);assert.ok(!dialog().className.includes('diagnostics-error-dialog'));
 await all('button').find(b=>b.textContent==='Details kopieren').onclick();
 assert.equal(JSON.parse(copied).id,report.id);
 await nodes.get('diagnostics-send').onclick();
 assert.equal(all('h2')[0].textContent,'Diagnosebericht senden?');
 assert.ok(dialog().textContent.includes('Lizenzschlüssel und Computer-ID'));
 assert.equal(sent,0);assert.equal(nodes.get('diagnostics-auto').checked,false);
 await all('button').find(b=>b.textContent==='Diesen Bericht senden').onclick();
 assert.equal(sent,1);assert.equal(nodes.get('diagnostics-auto').checked,false);
 console.log('PASS compact errors, safe fallbacks, focus, explicit details and unchanged consent');
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    result = subprocess.run([node, "-e", script, str(source)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_diagnostics_settings_reuse_product_controls_and_keep_disclosures():
    root = Path(__file__).resolve().parents[1] / "web"
    html = (root / "index.html").read_text()
    css = (root / "diagnostics.css").read_text()
    assert 'class="settings-toggle-list diagnostics-consent"' in html
    assert 'id="diagnostics-auto" type="checkbox" role="switch"' in html
    assert 'class="primary" id="diagnostics-send"' in html
    assert 'class="secondary-action" id="diagnostics-export"' in html
    assert 'id="diagnostics-empty" hidden' in html
    assert 'id="diagnostics-report-controls" hidden' in html
    assert '<details class="diagnostics-privacy">' in html
    for disclosure in ["Lizenzschlüssel und Computer-ID", "aller Unternehmen", "Server: 30 Tage",
                       "standardmäßig ausgeschaltet", "nicht zurückgerufen"]:
        assert disclosure in html
    assert '.diagnostics-card [hidden]' in css
    assert '.diagnostics-card button, .diagnostics-dialog button' not in css
