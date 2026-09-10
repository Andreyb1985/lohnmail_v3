# LohnMail Microsoft Store package

The Store artifact is produced by `.github/workflows/build-windows-store.yml`
on `windows-latest`. It packages the existing pywebview/PyInstaller application
as an x64 full-trust MSIX. It does not introduce PySide6 or a second desktop app.

## Partner Center identity

After reserving **LohnMail** in Partner Center, copy the exact values from
**Product management → Product identity** into these GitHub Actions variables:

- `MSIX_IDENTITY_NAME` → Package/Identity/Name
- `MSIX_PUBLISHER` → Package/Identity/Publisher
- `MSIX_PUBLISHER_DISPLAY_NAME` → Package/Properties/PublisherDisplayName
- `MSIX_APPLICATION_ID` → Package/Applications/Application/Id
- `LOHNMAIL_STORE_URI` → optional Store product URI after publication

The fallback identity is only for CI packaging and test installation. A package
using fallback values cannot be submitted under the reserved Store identity.

No production signing secret is required for the Partner Center upload. CI
creates a temporary self-signed certificate only for its install/upgrade test;
the certificate and private key are deleted before artifacts are uploaded.

## Output

`dist/store/` contains:

- `LohnMail_<four-part-version>_x64.msix`
- `LohnMail_<four-part-version>_x64.msix.sha256`
- `AppxManifest.xml`
- `build_info.json`

The GitHub artifact is named `LohnMail-Windows-Store-<version>`.

Package version comes from `ui_web/version.py`: `APP_VERSION=2.1.0` becomes
`2.1.0.0`. A tag such as `v2.1.0` must match `APP_VERSION` exactly.
