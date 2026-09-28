#!/bin/zsh
set -euo pipefail
cd "${0:A:h}/../.."
# Independent output: never overwrites the local, website or App Store app.
DEST="dist/windows-ui-demo-20260924"
WORK="build/windows-ui-demo-20260924"
[[ ! -e "$DEST/LohnMail Windows UI Demo.app" ]] || {
  echo 'Demo app already exists. Preserve it before rebuilding.' >&2
  exit 1
}
mkdir -p "$WORK"
export PYINSTALLER_CONFIG_DIR="$PWD/$WORK/cache"
.venv-macos/bin/python -m PyInstaller --noconfirm --clean --windowed \
  --name 'LohnMail Windows UI Demo' \
  --distpath "$DEST" --workpath "$WORK/work" --specpath "$WORK" \
  --paths "$PWD" --icon "$PWD/variants/macos/assets/LohnMail.icns" \
  --osx-bundle-identifier de.lohnmail.windows-ui-demo \
  --collect-all webview --add-data "$PWD/web:web" \
  --add-data "$PWD/settings_template.json:." --add-data '/etc/ssl/cert.pem:certs' \
  "$PWD/variants/macos/windows_ui_demo.py"
APP="$DEST/LohnMail Windows UI Demo.app"
/usr/libexec/PlistBuddy -c 'Set :CFBundleShortVersionString 2.0.3' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Set :CFBundleVersion 2026092402' "$APP/Contents/Info.plist" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c 'Add :CFBundleVersion string 2026092402' "$APP/Contents/Info.plist"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
echo "Demo app: $APP"
