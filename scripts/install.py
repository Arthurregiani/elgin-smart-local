"""User-local installation, no sudo, no service, no copied credentials."""
from pathlib import Path
import os,shlex,shutil,subprocess
base=Path(__file__).resolve().parents[1]
home=Path.home();dest=home/'.local/lib/elgin-smart-local'
dest.mkdir(parents=True,exist_ok=True);dest.chmod(0o700)
shutil.copy2(base/'native/target/release/elgin-smart-local',dest/'elgin-smart-local')
shutil.copytree(base/'bridge',dest/'bridge',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
for name in ('.venv','devices.json'):
 p=dest/name
 if p.is_symlink():p.unlink()
 if not p.exists():p.symlink_to(base/name,target_is_directory=name=='.venv')
exe=home/'.local/bin/elgin-smart-local';exe.parent.mkdir(parents=True,exist_ok=True)
exe.write_text('#!/bin/sh\nexport ELGIN_HOME='+shlex.quote(str(dest))+'\nexec '+shlex.quote(str(dest/'elgin-smart-local'))+' "$@"\n');exe.chmod(0o755)
icon=home/'.local/share/icons/hicolor/scalable/apps/io.github.elgin.SmartLocal.svg';icon.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base/'assets/io.github.elgin.SmartLocal.svg',icon)
desktop=home/'.local/share/applications/io.github.elgin.SmartLocal.desktop';desktop.parent.mkdir(parents=True,exist_ok=True)
escaped=str(exe).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')
desktop.write_text(f'''[Desktop Entry]
Type=Application
Name=Elgin Smart Local
Comment=Brilho, saturação e cor pela rede local
Exec="{escaped}"
Icon=io.github.elgin.SmartLocal
Terminal=false
Categories=Utility;
Keywords=Elgin;Tuya;Lâmpadas;Iluminação;RGB;COSMIC;
StartupNotify=true
StartupWMClass=io.github.elgin.SmartLocal
''')
for program,args in [('update-desktop-database',[str(desktop.parent)]),('gtk-update-icon-cache',['-f','-t',str(icon.parents[2])])]:
 if shutil.which(program):subprocess.run([program,*args],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print(f'Instalado: {exe}\nLauncher: {desktop}')
