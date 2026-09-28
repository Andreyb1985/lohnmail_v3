#!/bin/zsh
set -euo pipefail

cd "${0:A:h}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv-macos"
APP_VERSION="2.0.3"
APP_BUILD="202609048"
ICON_SOURCE="variants/macos/assets/LohnMail-white.png"
ICON_FILE="variants/macos/assets/LohnMail.icns"
EXPECTED_ICON_SOURCE_SHA256="763b210e2cc8d76b22d0b3f6cc3ccaaf92c606b0f8f9b7e2681b5a2c579a6ac4"
EXPECTED_ICON_FILE_SHA256="0dda034b1d99ade7e2cb24daad219e1b4ab69c01f05f8da62518556934d57198"

# macOS uses the white-background variant approved on 2026-09-13.
# The transparent UI logo and Windows artwork remain unchanged.
# Stop the build if either the source or generated ICNS is accidentally replaced.
[[ "$(shasum -a 256 "$ICON_SOURCE" | awk '{print $1}')" == "$EXPECTED_ICON_SOURCE_SHA256" ]] || {
  echo "ERROR: The approved macOS icon source has changed: $ICON_SOURCE" >&2
  exit 1
}
[[ "$(shasum -a 256 "$ICON_FILE" | awk '{print $1}')" == "$EXPECTED_ICON_FILE_SHA256" ]] || {
  echo "ERROR: The approved macOS ICNS has changed: $ICON_FILE" >&2
  exit 1
}

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r requirements-build-macos.txt

"$VENV_DIR/bin/python" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name LohnMail \
  --icon "$ICON_FILE" \
  --osx-bundle-identifier "lohnmail" \
  --collect-all webview \
  --add-data "web:web" \
  --add-data "settings_template.json:." \
  --add-data "/etc/ssl/cert.pem:certs" \
  main.py

# Keep platform-specific and archived icon variants out of the macOS bundle.
# The bundle icon is Contents/Resources/LohnMail.icns; the web UI uses only
# lohnmail-app-icon-previous.png (and lohnmail-logo.svg references that PNG).
BRAND_RESOURCES="dist/LohnMail.app/Contents/Resources/web/assets/brand"
rm -f \
  "$BRAND_RESOURCES/LohnMail.icns" \
  "$BRAND_RESOURCES/LohnMail.ico" \
  "$BRAND_RESOURCES/lohnmail-app-icon.png" \
  "$BRAND_RESOURCES/lohnmail-windows-icon.png"
rm -rf "$BRAND_RESOURCES/old"

PLIST="dist/LohnMail.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $APP_VERSION" "$PLIST"
if ! /usr/libexec/PlistBuddy -c "Set :CFBundleVersion $APP_BUILD" "$PLIST" 2>/dev/null; then
  /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $APP_BUILD" "$PLIST"
fi
/usr/libexec/PlistBuddy -c "Add :CFBundleSupportedPlatforms array" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :CFBundleSupportedPlatforms:0 string MacOSX" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 13.0" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :LSApplicationCategoryType string public.app-category.business" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :ITSAppUsesNonExemptEncryption bool false" "$PLIST" 2>/dev/null || true

# Re-apply a local ad-hoc signature after editing Info.plist. Distribution
# signing and notarization are deliberately separate from this test build.
codesign --force --deep --sign - "dist/LohnMail.app"

echo
echo "macOS-Testbuild fertig: dist/LohnMail.app"
