#!/bin/zsh
set -euo pipefail

PROJECT_ROOT="${0:A:h:h:h}"
cd "$PROJECT_ROOT"
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-/private/tmp/lohnmail-pyinstaller-cache}"
exec ./BUILD-MACOS.sh
