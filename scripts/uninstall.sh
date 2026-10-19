#!/usr/bin/env bash
set -euo pipefail
rm -f -- "$HOME/.local/bin/elgin-smart-local" "$HOME/.local/share/applications/io.github.elgin.SmartLocal.desktop" "$HOME/.local/share/icons/hicolor/scalable/apps/io.github.elgin.SmartLocal.svg"
rm -rf -- "$HOME/.local/lib/elgin-smart-local"
printf '%s\n' 'Aplicativo removido. Projeto, credenciais originais e presets foram preservados.'
