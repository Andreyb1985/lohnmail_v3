# LohnMail v2 Design System

Status: v2.0.0-alpha foundation.

## Visual direction
Professional B2B payroll desktop application inspired by DATEV, Lexware, Outlook, Linear and macOS applications.

## Tokens
- Primary: #0E7A56
- Accent: #1D4ED8
- Success: #16A34A
- Warning: #D97706
- Error: #DC2626
- Background: #F6F8FA
- Surface: #FFFFFF
- Border: #E5E7EB
- Text: #111827
- Muted: #6B7280

## Components implemented
- Sidebar
- TopBar
- Footer
- LMCard
- LMBadge
- Dashboard page
- Processing page
- Validation page
- Simple placeholder pages for Reports, Company, License, Settings, Help and About

## Rules
- All new UI must use components from `ui/widgets` and tokens from `ui/theme`.
- Existing business logic remains in `core` and legacy helper classes until migrated.
- `app_gui.py` remains available as rollback/reference during migration.

## Build Preview 2 UI Status

The following Frozen Design areas now have concrete PySide6 page implementations:

- Versand
- Berichte
- Unternehmen
- Lizenzen
- Einstellungen
- Hilfe
- Über LohnMail

Visual direction remains unchanged: DATEV/Lexware/Outlook inspired B2B SaaS desktop UI with green primary actions, rounded cards, calm typography and clear workflow grouping.
