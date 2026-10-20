#!/usr/bin/env python3
"""Build credential-free amd64 packages from an explicit allowlist."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/release'
VERSION = tomllib.loads((ROOT / 'native/Cargo.toml').read_text())['package']['version']
STEM = f'elgin-smart-local-{VERSION}-popos24.04-amd64'

def run(args, **kw):
    return subprocess.run(args, cwd=ROOT, check=True, **kw)

def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def tree(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

def licenses(dest, env):
    metadata = json.loads(subprocess.check_output(['cargo', 'metadata', '--locked', '--format-version=1', '--manifest-path', 'native/Cargo.toml'], cwd=ROOT, env=env))
    lines = ['# Third-party Rust dependencies', '', 'The following dependency notices accompany the compiled application.', 'Python distribution metadata and licenses are included in app/python/*.dist-info.', '']
    for pkg in sorted(metadata['packages'], key=lambda p: (p['name'], p['version'])):
        if pkg['name'] == 'elgin-smart-local':
            continue
        name = f'{pkg["name"]}-{pkg["version"]}'
        lines.append(f'- {name}: {pkg.get("license") or "See included license file"}')
        source = pkg.get('source')
        if source and source.startswith('git+'):
            lines.append(f'  Source: {source[4:]}')
        elif source and source.startswith('registry+'):
            lines.append(f'  Source: https://crates.io/crates/{pkg["name"]}/{pkg["version"]}')
        root = Path(pkg['manifest_path']).parent
        candidates = list(root.glob('LICENSE*')) + list(root.glob('COPYING*')) + list(root.glob('NOTICE*'))
        if not candidates and source and source.startswith('git+'):
            for parent in root.parents:
                candidates = list(parent.glob('LICENSE*')) + list(parent.glob('COPYING*'))
                if candidates or (parent / '.git').exists():break
        if pkg.get('license_file'):
            candidates.append(root / pkg['license_file'])
        for path in set(candidates):
            if path.is_file():
                copy(path, dest / 'licenses' / name / path.name)
            elif path.is_dir():
                for f in path.rglob('*'):
                    if f.is_file():copy(f, dest / 'licenses' / name / path.name / f.relative_to(path))
    (dest / 'THIRD_PARTY_NOTICES.md').write_text('\n'.join(lines) + '\n')

def main():
    if platform.machine() != 'x86_64':raise SystemExit('Build requires x86-64.')
    OUT.mkdir(parents=True, exist_ok=True)
    stage = OUT / 'stage'
    if stage.exists():shutil.rmtree(stage)
    stage.mkdir()
    env = os.environ.copy()
    env['CARGO_TARGET_DIR'] = str(OUT / 'cargo-target')
    env['CARGO_BUILD_JOBS'] = '4'
    env['RUSTFLAGS'] = f'--remap-path-prefix={Path.home()}=/build/user --remap-path-prefix={ROOT}=/usr/src/elgin-smart-local'
    run(['cargo', 'build', '--locked', '--release', '--manifest-path', 'native/Cargo.toml'], env=env)
    bundle = stage / STEM
    app = bundle / 'app'
    app.mkdir(parents=True)
    copy(OUT / 'cargo-target/release/elgin-smart-local', app / 'elgin-smart-local')
    tree(ROOT / 'bridge', app / 'bridge')
    copy(ROOT / 'devices.example.json', app / 'devices.example.json')
    wheel_dir = OUT / 'wheels'
    wheel_dir.mkdir(exist_ok=True)
    # A release downloads only official binary distributions; never copies the user's venv.
    python = ROOT / '.venv/bin/python'
    run([str(python), '-m', 'pip', 'download', '--require-hashes', '--only-binary=:all:', '--dest', str(wheel_dir), '-r', 'packaging/requirements-python.lock'])
    run([str(python), '-m', 'pip', 'install', '--no-compile', '--no-index', '--require-hashes', '--find-links', str(wheel_dir), '--target', str(app / 'python'), '-r', 'packaging/requirements-python.lock'])
    # Console entry points are unused and contain the build interpreter path.
    shutil.rmtree(app / 'python/bin', ignore_errors=True)
    for f in (app / 'python').rglob('direct_url.json'):f.unlink()
    licenses(app, env)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    manifest = {'version': VERSION, 'source_commit': commit, 'architecture': 'amd64', 'python': '3.12', 'target': 'Pop!_OS 24.04', 'runtime': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in wheel_dir.glob('*.whl')}}
    (app / 'BUILD-INFO.json').write_text(json.dumps(manifest, indent=2) + '\n')
    copy(ROOT / 'packaging/install-user.py', bundle / 'install.py')
    copy(ROOT / 'packaging/install-user.sh', bundle / 'install.sh')
    copy(ROOT / 'scripts/uninstall.sh', bundle / 'uninstall.sh')
    copy(ROOT / 'packaging/io.github.elgin.SmartLocal.desktop', bundle / 'io.github.elgin.SmartLocal.desktop')
    copy(ROOT / 'assets/io.github.elgin.SmartLocal.svg', bundle / 'io.github.elgin.SmartLocal.svg')
    copy(ROOT / 'README.md', bundle / 'README.md')
    copy(ROOT / 'docs/INSTALL.md', bundle / 'INSTALL.md')
    for f in bundle.rglob('*'):
        f.chmod(0o755 if f.is_dir() or f.name in ('elgin-smart-local', 'install.sh', 'uninstall.sh') else 0o644)
    bundle.chmod(0o755)
    archive = OUT / f'{STEM}.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(bundle, arcname=STEM)
    debroot = stage / 'deb'
    tree(app, debroot / 'usr/lib/elgin-smart-local')
    copy(ROOT / 'packaging/launch.sh', debroot / 'usr/bin/elgin-smart-local')
    (debroot / 'usr/bin/elgin-smart-local').chmod(0o755)
    copy(ROOT / 'packaging/io.github.elgin.SmartLocal.desktop', debroot / 'usr/share/applications/io.github.elgin.SmartLocal.desktop')
    copy(ROOT / 'assets/io.github.elgin.SmartLocal.svg', debroot / 'usr/share/icons/hicolor/scalable/apps/io.github.elgin.SmartLocal.svg')
    docdir = debroot / 'usr/share/doc/elgin-smart-local'
    for name in ('README.md', 'docs/INSTALL.md', 'devices.example.json'):
        copy(ROOT / name, docdir / Path(name).name)
    copy(app / 'THIRD_PARTY_NOTICES.md', docdir / 'copyright')
    (debroot / 'DEBIAN').mkdir()
    size = sum(f.stat().st_size for f in debroot.rglob('*') if f.is_file()) // 1024
    (debroot / 'DEBIAN/control').write_text(f'''Package: elgin-smart-local
Version: {VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Arthurregiani <84139073+Arthurregiani@users.noreply.github.com>
Depends: python3 (>= 3.12), python3 (<< 3.13), libc6 (>= 2.39), libgcc-s1, libxkbcommon0, libwayland-client0, libfontconfig1, libx11-6
Installed-Size: {size}
Homepage: https://github.com/Arthurregiani/elgin-smart-local
Description: Native COSMIC application for local Elgin lighting control
 Controls brightness, saturation, hue and white temperature via TinyTuya LAN.
 Includes its Python dependencies. No daemon, browser or credentials bundled.
''')
    # No maintainer scripts: installation does not start processes or touch user configuration.
    for f in [debroot, *debroot.rglob('*')]:
        f.chmod(0o755 if f.is_dir() or f.name == 'elgin-smart-local' else 0o644)
    deb = OUT / f'elgin-smart-local_{VERSION}_amd64.deb'
    run(['dpkg-deb', '--root-owner-group', '--build', str(debroot), str(deb)])
    sums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in (archive, deb))
    (OUT / 'SHA256SUMS').write_text(sums)
    print(f'Release assets: {archive}\n{deb}\n{OUT / "SHA256SUMS"}')

if __name__ == '__main__':main()
