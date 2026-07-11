# WebEngine Prüfung Detail Panel Fix

Fixes the right `Detailansicht` panel layout:

- closes the missing `.detail-scroll` wrapper in `web/index.html`;
- prevents horizontal overflow inside the details panel;
- fixes panel width/min-width/max-width;
- adds proper `min-width: 0` and ellipsis handling;
- makes preview table fit inside the panel;
- changes detail action buttons to a safe vertical stack on narrow panel widths.

Business logic was not changed.
