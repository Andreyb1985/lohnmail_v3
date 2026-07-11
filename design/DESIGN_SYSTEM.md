# LohnMail v2.0 — Design System

Status: **Frozen foundation**  
Scope: PySide6/Tauri-compatible B2B desktop UI

## Product Personality

LohnMail v2.0 should feel like a serious commercial B2B payroll/HR tool: clean, trustworthy, precise and calm.

Reference qualities:
- DATEV seriousness;
- Lexware business clarity;
- Outlook productivity;
- Linear visual hierarchy;
- Apple/macOS desktop polish.

## Color Tokens

### Primary
- Primary Green: `#16A34A`
- Primary Hover: `#15803D`
- Primary Pressed: `#166534`

### Semantic
- Success: `#16A34A`
- Warning: `#F59E0B`
- Error: `#EF4444`
- Info: `#2563EB`
- Neutral: `#64748B`

### Light Theme
- App Background: `#F8FAFC`
- Surface: `#FFFFFF`
- Surface Muted: `#F1F5F9`
- Border: `#E2E8F0`
- Text Primary: `#0F172A`
- Text Secondary: `#475569`
- Text Muted: `#64748B`

### Dark Theme Preparation
Dark mode remains part of the design system but implementation should happen after the light theme is stable.

Suggested dark tokens:
- App Background: `#0F172A`
- Surface: `#111827`
- Surface Muted: `#1E293B`
- Border: `#334155`
- Text Primary: `#F8FAFC`
- Text Secondary: `#CBD5E1`

## Typography

Primary font stack:
- Inter;
- SF Pro Display;
- Segoe UI;
- system sans-serif.

Sizes:
- Page Title: 24 px / Semibold
- Section Title: 16 px / Semibold
- Card Title: 14 px / Semibold
- Body: 13 px / Regular
- Caption: 12 px / Regular
- KPI Number: 28 px / Semibold

## Spacing

Base unit: 8 px.

Approved spacing scale:
- 4
- 8
- 12
- 16
- 20
- 24
- 32
- 40
- 48

Rules:
- card padding: 20–24 px;
- page margin: 24–32 px;
- row gap: 12–16 px;
- card gap: 16–24 px.

## Radius

- Small controls: 8 px
- Inputs/buttons: 10 px
- Cards: 14 px
- Dialogs: 16 px

## Borders and Shadows

Cards use subtle borders and very soft shadow only when needed.

Default card:
- border: 1 px `#E2E8F0`
- background: `#FFFFFF`
- radius: 14 px

Avoid heavy shadows. LohnMail should feel precise and business-like, not decorative.

## Components

### Sidebar
- fixed width approx. 240 px;
- active item: light green background + green left indicator;
- icons: outline, 20–22 px;
- groups separated by spacing, not heavy dividers.

### Top Bar
- height approx. 72 px;
- contains search/status/user controls;
- clean border bottom;
- no heavy gradients.

### Footer
- compact status bar;
- shows version/system/license/service state;
- must not steal visual focus.

### Cards
- used for KPIs, summaries, detail panels and settings groups;
- always have title hierarchy;
- avoid overfilled cards.

### Tables
- row height 44–48 px;
- sticky-style header visually;
- selected row uses very light green/blue tint;
- status badges instead of raw status text;
- actions are right-aligned.

### Buttons
- one primary button per action cluster;
- secondary buttons are neutral outline;
- destructive buttons use red and require confirmation;
- icon left, text right.

### Inputs
- height 40 px;
- radius 10 px;
- label above or context title;
- validation inline.

### Badges
- small rounded pills;
- use semantic color;
- concise labels only.

### Empty States
Every data-heavy screen needs an empty state with:
- short explanation;
- one recommended action;
- no technical jargon.

### Loading States
Use skeletons/progress where possible. Avoid freezing the UI without feedback.

### Error States
Errors must include:
- plain-language title;
- technical details expandable/copyable;
- next action if available.

## Responsive / Adaptive Rules

Desktop first, but must adapt to smaller screens:
- initial window size must never exceed available screen geometry;
- content pages must be scrollable;
- right panels can shrink but not force the window off-screen;
- tables should scroll horizontally when needed;
- minimum usable width target: 1180 px;
- comfortable width target: 1440–1600 px.

## Implementation Rules

1. Do not hardcode repeated colors in page files. Use theme/tokens.
2. Build pages from reusable LM components.
3. Do not change core logic while implementing visual changes.
4. Keep existing behavior available unless explicitly removed from scope.
5. Screens must follow the approved previews in `design/previews/`.
