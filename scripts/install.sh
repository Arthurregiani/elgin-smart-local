#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import tinytuya; assert tinytuya.__version__ == "1.20.0"' 2>/dev/null; then
  .venv/bin/python -m pip install 'tinytuya==1.20.0'
fi
cargo build --release --locked --manifest-path native/Cargo.toml
python3 scripts/install.py
