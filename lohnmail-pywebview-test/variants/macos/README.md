# macOS

This folder owns macOS-only packaging and App Store configuration. It builds
from the canonical source; it is not a separate product copy.

Local preview:

```bash
./variants/macos/build-local.sh
```

TestFlight and App Store package:

```bash
./variants/macos/build-appstore.sh
```

Developer ID signed website DMG:

```bash
./variants/macos/build-website.sh
```

Set `NOTARY_PROFILE` to a `notarytool` Keychain profile to submit, wait for,
and staple Apple notarization as part of the website build.

The same signed App Store package is used first in TestFlight and later for an
App Store release. The local ad-hoc preview is never uploaded.

## macOS icon (white background, 2026-09-13)

The only packaging sources are `assets/LohnMail-white.png` (1024×1024)
and `assets/LohnMail.icns`. `BUILD-MACOS.sh` pins both SHA-256 hashes and is
shared by website, local, and App Store builds. Regenerate ICNS with
`zsh variants/macos/build-icon.sh`, then review it before updating its hash.
The ICNS includes 512pt @2x (1024×1024).

The PNG was prepared with built-in imagegen from the approved white-background
preview. Final prompt: preserve the approved green LM and ring; use a flat white
full-bleed square background, no shadow, tile outline or transparency, centered
logo with white margins. The original transparent
`web/assets/brand/lohnmail-app-icon-previous.png` remains the UI/Dock logo.
Do not use the legacy `web/assets/brand/LohnMail.icns` for macOS packaging.

| Surface | Asset | Background |
| --- | --- | --- |
| Finder / application launcher / bundle | `variants/macos/assets/LohnMail.icns` | White |
| Dock while running (source and frozen) | `web/assets/brand/lohnmail-app-icon-previous.png` | Transparent |
| In-app branding | Existing web PNG/SVG | Unchanged |

`MACOS_DOCK_ICON_PATH` and `_set_macos_dock_icon()` apply only a runtime Dock
override after pywebview initializes AppKit. The signed bundle is not modified.
Before startup and after exit, macOS may display the white bundle icon in Dock.
There is no separate menu-bar status/tray icon in the current application.

Changing these source assets does not update an installed app or an existing
signed DMG. A new distribution must be rebuilt, signed and notarized separately.
