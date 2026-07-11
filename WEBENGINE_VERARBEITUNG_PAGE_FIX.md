# WebEngine Verarbeitung Page Fix

Fix for a blank Verarbeitung screen.

## Cause
`page-processing` was accidentally nested inside `page-dashboard` in `web/index.html`.
When Dashboard was hidden, the Verarbeitung page was hidden with its parent.

## Fix
Closed the Dashboard page section before the Verarbeitung page section, so both pages are sibling `.page` elements inside `.content`.

No business logic changes.
