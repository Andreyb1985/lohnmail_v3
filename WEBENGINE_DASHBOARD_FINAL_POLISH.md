# WebEngine Dashboard Final Polish

This build finalizes the visual proof-of-concept for the WebEngine Dashboard.

Scope:
- HTML/CSS visual layer only.
- No business logic changes.
- No core changes.

Changes:
- tightened vertical density so the dashboard fits standard desktop heights better;
- reduced KPI height and internal padding;
- refined topbar/search/pills sizes;
- adjusted sidebar spacing and navigation density;
- improved card row heights;
- improved Processing Overview contrast and spacing;
- kept local SVG icon system in `web/assets/icons/`;
- preserved Widgets fallback mode.

Fallback launch:

```bash
LOHNMAIL_UI=widgets python main.py
```
