# LohnMail v2 — AI Context

## Project goal

We are redesigning LohnMail as a professional HR/Payroll desktop product.

Current UI direction:

- PySide6 + QWebEngineView
- HTML/CSS/JS frontend inside desktop window
- Python core remains unchanged
- Existing business logic must not be rewritten

## Important rule

Do not change core business logic.

Do not rewrite:
- PDF processing
- Excel processing
- mail sending
- report generation
- encryption
- license logic

Only work on UI unless explicitly requested.

## Previous attempts

QWidget/QSS and QML/Qt Quick were rejected because visual fidelity was not good enough.

The selected approach is:

PySide6 desktop window
→ QWebEngineView
→ web/index.html
→ web/styles.css
→ web/app.js
→ ui_web/bridge.py for future JS ↔ Python communication

## Current visual status

Dashboard: visually acceptable as WebEngine base.
Verarbeitung: visually acceptable as WebEngine base.
Prüfung: in progress. Detail panel bottom alignment still needs polish.

## Current files

WebEngine UI:
- ui_web/app.py
- ui_web/bridge.py
- web/index.html
- web/styles.css
- web/app.js
- web/assets/icons/

Design documentation:
- design/FROZEN_SCREENS.md
- design/DESIGN_SYSTEM.md
- design/previews/

Fallback:
Old QWidget UI can still be launched with:

LOHNMAIL_UI=widgets python main.py

## Current task

Continue only with WebEngine UI.

Next task:
1. Fix Prüfung layout bottom alignment.
2. Make table and Detailansicht align vertically.
3. Keep Detailansicht internal scroll.
4. Do not touch core.
5. After Prüfung is approved, build Versand screen in WebEngine style.

## Visual rules

- Keep sidebar/topbar/footer consistent across screens.
- Use local SVG icons only.
- No emoji icons.
- No PySide Widget UI work.
- No QML work.
- Do not add new product features.
- This phase is design implementation only.