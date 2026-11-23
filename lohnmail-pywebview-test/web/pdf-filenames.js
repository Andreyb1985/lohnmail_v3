(function(){
  'use strict';
  var api, state={}, draft={mode:'standard'}, filename='', generation=0, request=0, busy=false, knownCompany;
  var $=function(id){return document.getElementById('pdf-rule-'+id);};
  function call(method,args){
    return new Promise(function(resolve,reject){
      if(!api || typeof api[method]!=='function') return reject(new Error('Verbindung zur Anwendung fehlt.'));
      try { api[method].apply(api,(args||[]).concat(function(raw){
        try {resolve(typeof raw==='string'?JSON.parse(raw):raw);} catch(e){reject(e);}
      })); } catch(e){reject(e);}
    });
  }
  function status(text){ $('status').textContent=text||''; }
  function payload(){return JSON.stringify({company_id:state.company_id,rule:draft,filename:filename});}
  function render(){
    $('company').textContent=state.company_id?'Gilt nur für: '+state.company_name:'Bitte ein Unternehmen auswählen';
    $('fields').disabled=busy||!!state.busy||!state.company_id;
    document.querySelectorAll('[name="pdf-rule-mode"]').forEach(function(el){el.checked=el.value===draft.mode;});
    $('custom').hidden=draft.mode!=='custom';
    $('content').hidden=draft.mode!=='content';
    $('note').textContent=draft.mode==='content'?
      'Quelle: PDF-Inhalt. Keine Zuordnung über Dateinamen. Gesamt-PDF bleibt unverändert.':
      'Quelle: Dateiname. Standardnamen bleiben auch mit eigenem Format gültig. Gesamt-PDF bleibt unverändert.';
    $('example').textContent=filename||'Noch keine Beispieldatei ausgewählt';
    $('separator').value=draft.separator||'_';
    $('parts').replaceChildren();
    if(filename && draft.mode==='custom'){
      var parts=filename.slice(0,-4).split(draft.separator||'_');
      parts.forEach(function(part,index){
        if(index){var sep=document.createElement('span');sep.textContent=draft.separator;$('parts').appendChild(sep);}
        var button=document.createElement('button');button.type='button';button.textContent=part||'(leer)';
        button.setAttribute('aria-pressed',String(draft.index===index));
        button.setAttribute('aria-label','Teil '+(index+1)+': '+part);
        button.onclick=function(){draft.index=index;draft.parts=parts.length;changed();preview();};
        $('parts').appendChild(button);
      });
      var ext=document.createElement('span');ext.textContent='.pdf';$('parts').appendChild(ext);
    }
    $('structure').textContent=draft.parts && Number.isInteger(draft.index)?
      'Regel: Teil '+(draft.index+1)+' von '+draft.parts+'. Monat, Jahr und Namen dürfen sich ändern; Anzahl und Reihenfolge der Teile bleiben gleich.':
      'Monat, Jahr und Namen dürfen sich ändern. Bitte den Teil mit der Personalnummer wählen.';
    var valid=draft.mode==='standard'||draft.mode==='content'||(Number.isInteger(draft.index)&&draft.parts>=2);
    $('save').disabled=!valid;
    $('test').disabled=!valid;
  }
  function changed(){
    request++; $('results').hidden=true; status('Noch nicht gespeichert.');
    $('preview').className='pdf-rule-preview';
    $('preview').textContent='Bitte Zuordnung prüfen.'; render();
  }
  async function preview(){
    if(!filename || !Number.isInteger(draft.index)) return;
    var token=++request, companyGeneration=generation;
    $('preview').textContent='Excel-Zuordnung wird geprüft …';
    try {
      var result=await call('previewPdfFilename',[payload()]);
      if(token!==request||companyGeneration!==generation)return;
      if(!result.ok){$('preview').textContent=result.message;$('preview').className='pdf-rule-preview problem';return;}
      var m=result.match;
      $('preview').className='pdf-rule-preview '+(m.matched?'success':'problem');
      $('preview').textContent=m.matched?'Zuordnung erkannt\n'+m.persnr+' → '+(m.employee||'Mitarbeiter ohne Namen')+'\nIn der Excel-Liste gefunden.':
        (m.persnr?m.persnr+' — ':'')+m.reason;
    }catch(e){if(token===request) $('preview').textContent='Excel-Zuordnung konnte nicht geprüft werden. Bitte erneut versuchen.';}
  }
  async function reload(){
    var token=++generation; request++;
    state={}; filename=''; draft={mode:'standard'}; busy=true;
    $('results').hidden=true; $('preview').textContent='Bitte ein PDF auswählen und die Personalnummer markieren.';render();
    try{
      var result=await call('getPdfFilenameState');
      if(token!==generation)return;
      state=result;draft=Object.assign({},result.rule||{mode:'standard'});status(result.message);
    }catch(e){if(token===generation)status('PDF-Einstellungen konnten nicht geladen werden.');}
    finally{if(token===generation){busy=false;render();}}
  }
  async function action(method,args,handler){
    if(busy)return;
    var token=generation;busy=true;render();status('Bitte warten …');
    try{
      var result=await call(method,args);
      if(token!==generation)return;
      if(result.cancelled){status('Abgebrochen. Einstellungen unverändert.');return;}
      if(!result.ok){status(result.message||'Vorgang fehlgeschlagen.');return;}
      handler(result);
    }catch(e){if(token===generation)status('Vorgang konnte nicht abgeschlossen werden. Bitte erneut versuchen.');}
    finally{if(token===generation){busy=false;render();}}
  }
  function attach(bridge){
    api=bridge;
    document.querySelectorAll('[name="pdf-rule-mode"]').forEach(function(el){el.onchange=function(){
      draft=el.value==='custom'?{mode:'custom',separator:'_'}:{mode:el.value};changed();
    };});
    $('separator').onchange=function(){draft={mode:'custom',separator:this.value};changed();};
    $('choose').onclick=function(){action('choosePdfFilenameExample',[],function(result){
      if(result.company_id!==state.company_id)return;
      filename=result.filename;draft={mode:'custom',separator:$('separator').value};changed();
    });};
    $('test').onclick=function(){action('choosePdfFilenameFolder',[payload()],function(result){
      $('results').hidden=false;
      $('counts').textContent=result.matched+' von '+result.total+' Dateien zugeordnet · '+result.problems+' problematisch'+(result.truncated?' · Erste 500 Dateien angezeigt':'');
      $('rows').replaceChildren();
      result.rows.forEach(function(row){
        var tr=document.createElement('tr');tr.dataset.problem=String(!row.matched);
        [row.file,row.persnr||'—',row.matched?(row.employee||'Mitarbeiter gefunden'):row.reason].forEach(function(text){var td=document.createElement('td');td.textContent=text;tr.appendChild(td);});
        $('rows').appendChild(tr);
      });
      status('Ordner geprüft. Keine Dateien verändert. Zum Übernehmen bitte speichern.');
    });};
    $('save').onclick=function(){action('savePdfFilenameRule',[payload()],function(result){
      state.rule=Object.assign({},draft);status(result.message);
    });};
    $('cancel').onclick=reload;
    $('reset').onclick=function(){draft={mode:'standard'};changed();status('Standardformat ausgewählt. Zum Übernehmen für diese Firma speichern.');};
    reload();
  }
  window.LohnMailPdfFilenames={attach:attach,companyChanged:function(id){
    if(knownCompany===id)return;knownCompany=id;if(api)reload();
  }};
})();
