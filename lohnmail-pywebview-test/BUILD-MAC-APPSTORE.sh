#!/bin/zsh
set -euo pipefail

cd "${0:A:h}"

PROFILE_SOURCE="${PROFILE_SOURCE:-/Users/strelok/Downloads/lohnmailmacos.provisionprofile}"
APP_SIGN_IDENTITY="${APP_SIGN_IDENTITY:-F82AE7A8106A68344616535F3D16D9CBB320B6BF}"
INSTALLER_SIGN_IDENTITY="${INSTALLER_SIGN_IDENTITY:-3rd Party Mac Developer Installer: Andrii Bakanov (VUF387578P)}"
APP_PATH="dist/LohnMail.app"
LOCAL_APP_PATH="dist/LohnMail-Local-Test.app"
PKG_PATH="dist/LohnMail-2.0.3-macOS-AppStore.pkg"
ENTITLEMENTS="macos-app-store.entitlements"

if [[ ! -f "$PROFILE_SOURCE" ]]; then
  echo "Provisioning profile not found: $PROFILE_SOURCE" >&2
  exit 1
fi

if [[ ! -f "$ENTITLEMENTS" ]]; then
  echo "Entitlements file not found: $ENTITLEMENTS" >&2
  exit 1
fi

./BUILD-MACOS.sh
rm -rf "$LOCAL_APP_PATH"
ditto "$APP_PATH" "$LOCAL_APP_PATH"
cp "$PROFILE_SOURCE" "$APP_PATH/Contents/embedded.provisionprofile"

# Downloads and Finder can attach quarantine/provenance attributes. They are
# forbidden on files inside apps submitted to TestFlight or the Mac App Store.
xattr -cr "$APP_PATH" 2>/dev/null || true

# Finder/Archive can leave AppleDouble metadata files in generated bundles;
# they are not application resources and must not enter the App Store payload.
find "$APP_PATH" -name '._*' -type f -delete

# Sign nested Mach-O files before sealing the outer application bundle.
while IFS= read -r binary; do
  codesign --force --timestamp --sign "$APP_SIGN_IDENTITY" "$binary"
done < <(find "$APP_PATH/Contents" -type f -print0 | xargs -0 file | awk -F: '/Mach-O/{print $1}')

codesign \
  --force \
  --timestamp \
  --options runtime \
  --entitlements "$ENTITLEMENTS" \
  --sign "$APP_SIGN_IDENTITY" \
  "$APP_PATH"

codesign --verify --deep --strict --verbose=2 "$APP_PATH"

productbuild \
  --component "$APP_PATH" /Applications \
  --sign "$INSTALLER_SIGN_IDENTITY" \
  "$PKG_PATH"

pkgutil --check-signature "$PKG_PATH"

echo
echo "App Store package created: $PKG_PATH"
