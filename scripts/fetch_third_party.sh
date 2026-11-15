#!/usr/bin/env bash
# Clone the LSI / tweedledum sources into third_party/ at the commits the sandbox was tested with.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$root/third_party"
cd "$root/third_party"

fetch() { # name url commit
  [ -d "$1" ] || git clone --quiet "$2" "$1"
  if ! git -C "$1" checkout --quiet "$3" 2>/dev/null; then
    git -C "$1" fetch --quiet --unshallow 2>/dev/null || git -C "$1" fetch --quiet
    git -C "$1" checkout --quiet "$3"
  fi
  echo "$1 @ $(git -C "$1" log -1 --format='%h %cs %s')"
}

fetch mockturtle  https://github.com/lsils/mockturtle.git    434c1ac  # active, used unmodified by opt/
fetch caterpillar https://github.com/gmeuli/caterpillar.git  4c6f766  # dormant since Nov 2020, reference only
fetch tweedledum  https://github.com/boschmitt/tweedledum.git 3d765c3 # source for reading; Python wheel comes from PyPI
