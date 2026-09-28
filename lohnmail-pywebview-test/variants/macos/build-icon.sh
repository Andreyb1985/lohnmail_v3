#!/bin/zsh
# Convert the approved macOS PNG into every standard ICNS representation.
set -euo pipefail
cd "${0:A:h}"
ICON_WORK="$(mktemp -d -t lohnmail-icon)"
mkdir "$ICON_WORK/LohnMail.iconset"
for size in 16 32 128 256 512; do
  sips -z "$size" "$size" assets/LohnMail-white.png \
    --out "$ICON_WORK/LohnMail.iconset/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" assets/LohnMail-white.png \
    --out "$ICON_WORK/LohnMail.iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICON_WORK/LohnMail.iconset" -o assets/LohnMail.icns
echo "Created variants/macos/assets/LohnMail.icns (including 512pt @2x)."
echo "Temporary iconset retained at $ICON_WORK for inspection."
