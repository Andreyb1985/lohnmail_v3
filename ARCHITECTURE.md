# LohnMail v2 UI Architecture

Status: Sprint 1 / Build Preview 1.

## Entry point
`main.py` imports `ui.main_window.MainWindow`.

## UI shell
`ui.main_window.MainWindow` inherits legacy `app_gui.MainWindow` methods but does not call its legacy constructor. This preserves the existing worker flow, dialogs and business integration while replacing the visual shell.

## Folder structure
```text
ui/
  main_window.py
  layout/
    sidebar.py
    topbar.py
    footer.py
  pages/
    dashboard_page.py
    processing_page.py
    validation_page.py
    simple_page.py
  widgets/
    card.py
    badge.py
  theme/
    tokens.py
    stylesheet.py
```

## Current integration
Connected to existing logic:
- PDF input selection
- Excel selection
- Company combo/settings
- Check job
- Send job + send preview
- Selected send
- Table rendering/filtering
- Audit/missing/send report menu actions
- Legacy settings/help/support dialogs

## Migration rule
No business logic in `core` is changed in Sprint 1. The legacy `app_gui.py` remains as a reference and rollback layer.

## Build Preview 2

Additional real pages were added to the v2 shell:

- `ui/pages/mailing_page.py`
- `ui/pages/reports_page.py`
- `ui/pages/company_page.py`
- `ui/pages/license_page.py`
- `ui/pages/settings_page.py`
- `ui/pages/help_page.py`
- `ui/pages/about_page.py`

The shell no longer uses placeholder `SimplePage` for the approved main navigation. Existing legacy dialogs remain connected through the inherited `app_gui.MainWindow` methods.

### Integration rule

For this preview the existing dialogs remain the source of truth for settings, companies, e-mail templates, period/password configuration and help/support. The new pages act as commercial-grade entry points and will be deep-integrated screen by screen in later previews.
