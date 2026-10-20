#!/usr/bin/env python3
"""Install the prebuilt bundle locally. No pip, compilation, or credential copy."""
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys

base = Path(__file__).resolve().parent
if platform.machine() != 'x86_64' or sys.version_info[:2] != (3, 12):
    raise SystemExit('Este pacote requer Linux x86-64 com Python 3.12 (Pop!_OS 24.04).')
home = Path.home()
dest = home / '.local/lib/elgin-smart-local'
dest.mkdir(parents=True, exist_ok=True)
dest.chmod(0o700)
# Only release files are copied. Existing devices.json/presets are untouched.
shutil.copytree(base / 'app', dest, dirs_exist_ok=True)
exe = home / '.local/bin/elgin-smart-local'
exe.parent.mkdir(parents=True, exist_ok=True)
exe.write_text('#!/bin/sh\nexport ELGIN_HOME=' + shlex.quote(str(dest)) + '\nexec ' + shlex.quote(str(dest / 'elgin-smart-local')) + ' "$@"\n')
exe.chmod(0o755)
icon = home / '.local/share/icons/hicolor/scalable/apps/io.github.elgin.SmartLocal.svg'
icon.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(base / 'io.github.elgin.SmartLocal.svg', icon)
desktop = home / '.local/share/applications/io.github.elgin.SmartLocal.desktop'
desktop.parent.mkdir(parents=True, exist_ok=True)
escaped = str(exe).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
desktop.write_text((base / 'io.github.elgin.SmartLocal.desktop').read_text().replace('Exec=/usr/bin/elgin-smart-local', f'Exec="{escaped}"'))
config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'elgin-smart-local'
config.mkdir(parents=True, exist_ok=True)
config.chmod(0o700)
example = config / 'devices.example.json'
if not example.exists():
    shutil.copy2(base / 'app/devices.example.json', example)
shutil.copy2(base / 'uninstall.sh', dest / 'uninstall.sh')
if shutil.which('update-desktop-database'):
    subprocess.run(['update-desktop-database', str(desktop.parent)], check=False)
print(f'Instalado. Configure {config / "devices.json"} e abra Elgin Smart Local pelo launcher.')
