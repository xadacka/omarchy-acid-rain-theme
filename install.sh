#!/usr/bin/env bash
# Installs the Acid Rain theme. Safe to re-run.
set -euo pipefail

THEME_URL="https://github.com/xadacka/omarchy-acid-rain-theme.git"

omarchy theme install "$THEME_URL"   # also applies it (calls omarchy theme set)

cat <<'MSG'

Done. Acid Rain is applied.

Keyboard RGB: Razer Shortcut Lights and the OpenRGB theme-set hook both read
this theme's colors.toml automatically -- nothing more to configure.
Cycle wallpapers with:  omarchy theme bg next
MSG
