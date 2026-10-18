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
 state={...state,reports:[{report,sent:false}]};await api.showError({});
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
