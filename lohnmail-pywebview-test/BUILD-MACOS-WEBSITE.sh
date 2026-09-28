#!/bin/zsh
set -euo pipefail

cd "${0:A:h}"

DEVELOPER_ID_APPLICATION="${DEVELOPER_ID_APPLICATION:-797F3A74ADBF45BC347ECAA1184C12F802B70414}"
NOTARY_PROFILE="${NOTARY_PROFILE:-}"
APP_SOURCE="dist/LohnMail.app"
OUTPUT_DIR="dist/website"
APP_PATH="$OUTPUT_DIR/LohnMail.app"
DMG_STAGE="$OUTPUT_DIR/dmg-root"

./BUILD-MACOS.sh

APP_VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP_SOURCE/Contents/Info.plist")"
APP_BUILD="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$APP_SOURCE/Contents/Info.plist")"
ARCH="$(lipo -archs "$APP_SOURCE/Contents/MacOS/LohnMail" | tr ' ' '-')"
DMG_PATH="$OUTPUT_DIR/LohnMail-${APP_VERSION}-${APP_BUILD}-macOS-${ARCH}.dmg"

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR" "$DMG_STAGE"
ditto "$APP_SOURCE" "$APP_PATH"

# Website distribution does not use an App Store provisioning profile or sandbox.
rm -f "$APP_PATH/Contents/embedded.provisionprofile"
/usr/libexec/PlistBuddy -c "Add :LohnMailDistributionChannel string website" "$APP_PATH/Contents/Info.plist" 2>/dev/null || \
  /usr/libexec/PlistBuddy -c "Set :LohnMailDistributionChannel website" "$APP_PATH/Contents/Info.plist"
xattr -cr "$APP_PATH" 2>/dev/null || true
find "$APP_PATH" -name '._*' -type f -delete

# Sign every bundled executable before sealing the outer application bundle.
while IFS= read -r -d '' binary; do
  if file -b "$binary" | grep -q 'Mach-O'; then
    codesign \
      --force \
      --timestamp \
      --options runtime \
      --sign "$DEVELOPER_ID_APPLICATION" \
      "$binary"
  fi
done < <(find "$APP_PATH/Contents" -type f -print0)

codesign \
  --force \
  --timestamp \
  --options runtime \
  --sign "$DEVELOPER_ID_APPLICATION" \
  "$APP_PATH"

codesign --verify --deep --strict --verbose=2 "$APP_PATH"

ditto "$APP_PATH" "$DMG_STAGE/LohnMail.app"
ln -s /Applications "$DMG_STAGE/Applications"
hdiutil create \
  -volname "LohnMail" \
  -srcfolder "$DMG_STAGE" \
  -format UDZO \
  -ov \
  "$DMG_PATH"
codesign --force --timestamp --sign "$DEVELOPER_ID_APPLICATION" "$DMG_PATH"
codesign --verify --verbose=2 "$DMG_PATH"
hdiutil verify "$DMG_PATH"

rm -rf "$DMG_STAGE"

if [[ -n "$NOTARY_PROFILE" ]]; then
  xcrun notarytool submit "$DMG_PATH" --keychain-profile "$NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG_PATH"
  xcrun stapler validate "$DMG_PATH"
  spctl -a -vv --type open --context context:primary-signature "$DMG_PATH"
else
  echo
  echo "Signed DMG created, but not notarized: $DMG_PATH"
  echo "Set NOTARY_PROFILE to a notarytool Keychain profile and run this script again."
fi

echo
echo "Website artifact: $DMG_PATH"
