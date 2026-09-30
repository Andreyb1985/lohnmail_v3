"""Execute the real UI state renderer with delayed/duplicate bridge events."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_shipping_renderer_orders_runs_and_displays_intermediate_progress():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the actual JavaScript renderer")
    source = Path(__file__).resolve().parents[1] / "web" / "app.js"
    script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync(process.argv[1], 'utf8');
const nodes = new Map();
function node(selector) {
  if (!nodes.has(selector)) nodes.set(selector, {style:{}, hidden:true,
    classList:{toggle(){}}, textContent:''});
  return nodes.get(selector);
}
const c = {shippingRevision:-1, shippingTerminalState:null, shippingLiveProgress:{phase:'idle'},
  latestShippingState:null, document:{querySelector:node, querySelectorAll:()=>[]},
  workflowStateMatchesActiveCompany:s=>s.company.id === 'test',
  setText:(s,t)=>node(s).textContent=String(t),
  selectedShippingRows:()=>[{persnr:'1',email:'test@example.invalid'}],
  shippingRows:()=>[{persnr:'1',email:'test@example.invalid'}]};
for (const name of ['syncShippingSelectionDefaults','updateShippingFilterControls',
  'renderShippingRows','updateCompactWorkflowTrackers','updateDashboardPipeline',
  'updateWarningCenter','updateReportsScreen']) c[name]=()=>{};
vm.createContext(c);
for (const name of ['resetShippingLiveProgress','syncShippingLiveProgress',
    'updateShippingLiveProgressPanel','applyShippingState']) {
  const start=source.indexOf('  function '+name+'(');
  const end=source.indexOf('\n  function ',start+1);
  vm.runInContext(source.slice(start,end),c);
}
function event(revision, id, mode, current, options={}) {
  return {revision,company:{id:'test'},rows:[],metrics:{total:70,queued:70,exported:70},
    status:{operation_id:id, running:true,dry_run:mode,
      live_progress:{phase:mode?'preparing':'sending',current,total:70,
        sent:mode?0:current,prepared:mode?current:0,errors:0,
        operation:'Synthetic progress',persnr:'1',email:'test@example.invalid'}, ...options}};
}
function apply(e){c.applyShippingState(e);}
function text(s){return node(s).textContent;}
const prepared=event(2,'prepare',true,70,{running:false,finished:true});
apply(prepared);
// Do not rely on a click resetting the company-wide terminal guard.
apply(event(3,'send',false,0));
assert.equal(c.latestShippingState.status.operation_id,'send');
assert.equal(text('[data-shipping-live="count"]'),'0/70');
apply(event(4,'send',false,21));
assert.equal(text('[data-shipping-live="count"]'),'21/70');
assert.equal(node('[data-shipping-live="bar"]').style.width,'30%');
assert.equal(text('[data-shipping="sent-count"]'),'21');
assert.equal(text('[data-shipping="queued-count"]'),'49');
assert.equal(node('[data-shipping-live]').hidden,false);
assert.ok(text('[data-shipping-live="current"]').includes('test@example.invalid'));
apply(prepared); // delayed previous preparation result
apply(event(3,'send',false,0)); // delayed start Promise
apply(event(4,'send',false,21)); // duplicate signal
assert.equal(text('[data-shipping-live="count"]'),'21/70');
const finished=event(6,'send',false,70,{running:false,finished:true});
finished.metrics={total:70,sent:70,queued:0,exported:0,errors:0};
apply(finished);
apply(event(5,'send',false,69));
assert.equal(text('[data-shipping-live="count"]'),'70/70');
assert.equal(c.latestShippingState.status.finished,true);
// A fresh operation is allowed even after success or failure in the same company.
apply(event(7,'prepare-again',true,0));
assert.equal(text('[data-shipping-live="count"]'),'0/70');
apply(event(8,'send-again',false,5));
const failed=event(9,'send-again',false,5,{running:false,failed:true,message:'Synthetic failure'});
failed.metrics={total:70,sent:5,errors:0};
apply(failed);
assert.equal(text('[data-shipping-live="count"]'),'5/70');
assert.equal(text('[data-shipping-live="title"]'),'Versand abgebrochen');
apply(event(10,'third-run',false,1));
assert.equal(text('[data-shipping-live="count"]'),'1/70');
// Wrong company must not poison the global revision watermark.
const other=event(100,'other-run',false,1); other.company.id='other'; apply(other);
apply(event(11,'third-run',false,2));
assert.equal(text('[data-shipping-live="count"]'),'2/70');
// Terminal before any progress/start response (very fast worker).
const fast=event(13,'fast-run',false,70,{running:false,finished:true});
fast.metrics=finished.metrics; apply(fast); apply(event(12,'fast-run',false,0));
assert.equal(text('[data-shipping-live="count"]'),'70/70');
assert.equal(text('[data-shipping-live="current"]'),'70 E-Mails gesendet');
console.log('Shipping event order and visible counters passed');
'''
    result = subprocess.run([node, "-e", script, str(source)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
