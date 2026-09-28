"""Browser geometry regression using shipped CSS and the real log renderer.

Requires agent-browser on PATH. Opens static files only, never starts Python
backend, licensing or mail. Optional --source points at unpacked MSIX payload.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--browser', default='agent-browser')
    parser.add_argument('--executable')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    source = (args.source / 'web/app.js').read_text(encoding='utf-8')
    start = source.index('  function renderProcessingLog(){')
    end = source.index('\n  function ', start+1)
    renderer = source[start:end]
    commands = [args.browser, '--session', 'lohnmail-log-regression']

    def run(*items):
        # A browser daemon can inherit stdout handles on Windows. Do not wait
        # for pipe EOF from its descendants; wait for the CLI itself, bounded.
        subprocess.run(commands+list(items), check=True, timeout=90)
        return ''

    launch = ['--allow-file-access']
    if args.executable:
        launch += ['--executable-path', args.executable]
    try:
        print(run(*launch, 'open', (args.source.resolve() / 'web/index.html').as_uri()))
        print(run('set', 'viewport', '1366', '768'))
        script = '''(() => {
          const article=document.querySelector('.operation-log');
          document.body.replaceChildren(article);
          document.body.style.cssText='margin:0;padding:24px;background:#f5f8fb';
          let processingActivityLog=[];
          const escapeHtml=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
          RENDERER
          const results=[];
          const box=el=>el.getBoundingClientRect();
          const check=(ok,message)=>{if(!ok)throw Error(message)};
          for(const width of [280,360,640,960,1280]) {
            article.style.width=width+'px';
            for(const populated of [false,true]) {
              // Normal rows retain desktop columns; tiny widths stress only the empty state.
              if(populated && width<640) continue;
              processingActivityLog=populated ? [{time:'12:34:56',level:'error',title:'Testfehler',detail:'Synthetische Meldung mit langem Dateipfad /Demonstration/Unternehmen/Ergebnisse/Pruefbericht.xlsx'}] : [];
              renderProcessingLog();
              const row=article.querySelector('.log-list>div'), b=row.querySelector('b'), em=row.querySelector('em');
              const rb=box(row), bb=box(b), eb=box(em);
              if(!populated){
                check(bb.width>100,'Empty title still squeezed at '+width);
                check(bb.height<=parseFloat(getComputedStyle(b).lineHeight)*2+.5,'Empty title wraps vertically');
                check(eb.top>=bb.bottom-1,'Empty title/detail overlap');
                check(row.scrollWidth<=row.clientWidth+1,'Empty row overflows');
              } else if(width>=640) {
                check(eb.left>=bb.right-1,'Normal columns overlap');
                check(row.scrollWidth<=row.clientWidth+1,'Normal row overflows');
              }
              results.push({width,populated,titleWidth:bb.width,rowHeight:rb.height,columns:getComputedStyle(row).gridTemplateColumns});
            }
          }
          article.style.width='900px'; processingActivityLog=[];renderProcessingLog();
          return results;
        })()'''.replace('RENDERER',renderer)
        print(run('eval', script))
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True,exist_ok=True)
            print(run('screenshot', str(args.screenshot.resolve())))
    finally:
        run('close')


if __name__ == '__main__':
    main()
