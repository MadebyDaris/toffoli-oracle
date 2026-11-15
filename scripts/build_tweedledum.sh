#!/usr/bin/env bash
# Build tweedledum 1.2.0 (unreleased GitHub main) from source, with our binding fixes, into a Python env.
#
#   scripts/build_tweedledum.sh [path/to/python]      default: ~/.conda/envs/tweedledum-dev/bin/python
#
# Why this exists:
#   - PyPI's tweedledum 1.1.1 has wheels only up to Python 3.10; its sdist no longer builds
#     (invalid [project] table for modern setuptools, bundled pybind11 2.6).
#   - GitHub main (1.2.0, nanobind) builds on 3.14, but 9 of 18 API calls in
#     sandbox/tweedledum/00_smoke_api.py fail; patches/tweedledum-1.2.0-nanobind-bindings.patch fixes them.
#   - The Python must ship its C headers (Python.h). Fedora's system python3 does not unless
#     python3-devel is installed; conda's Python always does.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
python="${1:-$HOME/.conda/envs/tweedledum-dev/bin/python}"
commit=3d765c3
src="$root/build/tweedledum-src"

[ -x "$python" ] || { echo "no python at $python (create it: conda create -n tweedledum-dev -c conda-forge python=3.14 pip)"; exit 1; }
"$python" -c 'import sysconfig, os, sys; h = os.path.join(sysconfig.get_paths()["include"], "Python.h"); sys.exit(0 if os.path.exists(h) else f"{h} missing: this Python has no C headers (Fedora: sudo dnf install python3-devel, or use a conda Python)")'
[ -d "$root/third_party/tweedledum/.git" ] || "$root/scripts/fetch_third_party.sh"

rm -rf "$src"
git clone --quiet "$root/third_party/tweedledum" "$src"
git -C "$src" checkout --quiet "$commit"
git -C "$src" apply "$root/patches/tweedledum-1.2.0-nanobind-bindings.patch"

PYTHONNOUSERSITE=1 "$python" -m pip install --force-reinstall --no-deps "$src"
PYTHONNOUSERSITE=1 "$python" "$root/sandbox/tweedledum/00_smoke_api.py"
