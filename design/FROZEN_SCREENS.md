# LohnMail v2.0 — Frozen Screens

Status: **Frozen / Approved**  
Scope: **Design and UX for existing LohnMail functionality only**  
Date: 2026-06-30

This document freezes the approved screen direction for LohnMail v2.0. During implementation, these screens should be treated as the visual and structural reference. No new product features should be added to v2.0 unless they already exist in the current application logic.

## Frozen Screen List

| # | Screen | Status | Preview file |
|---|---|---|---|
| 01 | Dashboard | Frozen | `design/previews/01_dashboard.png` |
| 02 | Verarbeitung | Frozen | `design/previews/02_verarbeitung.png` |
| 03 | Prüfung | Frozen | `design/previews/03_pruefung.png` |
| 04 | Versand | Frozen | `design/previews/04_versand.png` |
| 05 | Berichte | Frozen | `design/previews/05_berichte.png` |
| 06 | Unternehmen | Frozen | `design/previews/06_unternehmen.png` |
| 07 | Lizenzen | Frozen | `design/previews/07_lizenzen.png` |
| 08 | Einstellungen | Frozen | `design/previews/08_einstellungen.png` |
| 09 | Hilfe | Frozen | `design/previews/09_hilfe.png` |
| 10 | Über LohnMail | Frozen | `design/previews/10_ueber_lohnmail.png` |

## Implementation Rule

v2.0 is a design and UX modernization of the existing product. It must not become a feature expansion.

Allowed:
- reorganize UI;
- improve layout, hierarchy, navigation, spacing, typography and component consistency;
- connect existing logic to the new UI;
- add placeholder UI only where the existing application already exposes related logic;
- improve responsiveness and scroll behavior.

Not allowed for v2.0:
- new business logic;
- new backend services;
- new PDF/Excel/Mail algorithms;
- new product modules beyond the approved navigation;
- expanding scope with features planned for v2.1.

## Global Shell

All screens use the same application shell:

- left sidebar with the approved navigation;
- top bar with search/status/user area;
- page header with title and short description;
- card-based content layout;
- fixed footer/status bar;
- adaptive window sizing and scrollable page content.

## Navigation

Approved sidebar order:

1. Dashboard
2. Verarbeitung
3. Prüfung
4. Versand
5. Berichte
6. Unternehmen
7. Lizenzen
8. Einstellungen
9. Hilfe
10. Über LohnMail

## Screen Notes

### Dashboard
Purpose: overview of system, recent activity and current processing status.

Core blocks:
- KPI cards;
- license and SMTP status;
- recent activity;
- quick actions;
- processing overview.

### Verarbeitung
Purpose: import and process payroll documents.

Core blocks:
- workflow header;
- PDF input;
- Excel input;
- status overview;
- progress area;
- operation journal;
- existing processing actions.

### Prüfung
Purpose: validate employees, PersNr, e-mail mapping and detected issues.

Core blocks:
- KPI cards for critical errors, warnings, hints and checked employees;
- filter tabs;
- validation table;
- right details panel;
- export action.

### Versand
Purpose: prepare, preview and send/export payroll e-mails.

Core blocks:
- sending KPI cards;
- queue tabs;
- recipient table;
- preview/details panel;
- send/export actions.

### Berichte
Purpose: show processing, sending and audit reports.

Core blocks:
- report KPI cards;
- date/status filters;
- chart area;
- report table;
- report details panel;
- export/download actions.

### Unternehmen
Purpose: manage company, sender and communication settings.

Core blocks:
- company profile;
- contact person;
- sender details;
- SMTP/Outlook settings;
- e-mail settings summary;
- save/reset actions.

### Lizenzen
Purpose: manage license status and activation information.

Core blocks:
- license KPI cards;
- license key area;
- activation/deactivation actions;
- licensed users/features;
- support area.

### Einstellungen
Purpose: configure application preferences.

Core blocks:
- settings category tabs;
- general preferences;
- program behavior;
- update settings;
- system info;
- cache/import/export/danger zone.

### Hilfe
Purpose: documentation and support entry point.

Core blocks:
- help search;
- frequent topics;
- knowledge base;
- quick links;
- support contact.

### Über LohnMail
Purpose: product, version, legal and component information.

Core blocks:
- product hero;
- version/build/license information;
- technology components;
- product description;
- legal links;
- contact/support.

## Frozen Definition

A screen is considered implemented only when:

- layout matches the approved preview at the same application width;
- reusable components are used instead of one-off styling;
- page content adapts to smaller screens via scroll/resize behavior;
- colors, spacing and typography follow the design system;
- existing business logic remains functional;
- no unapproved new features are introduced.
