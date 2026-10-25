#!/usr/bin/env bash
# Copy google_kit into a project:  scripts/vendor.sh ../health-sync
# The project commits the copy (src/google_kit/), so its Docker build needs no access to this private repo.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
dst=${1:?project directory}/src/google_kit
[ -d "${1}/src" ] || { echo "no src/ in $1" >&2; exit 1; }
rm -rf "$dst"; mkdir -p "$dst"
cp "$here"/src/google_kit/*.py "$dst"/
printf 'Vendored copy of ExiosV/google-kit %s. Do not edit here: change google-kit and rerun scripts/vendor.sh.\n' \
  "$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$here/src/google_kit/__init__.py")" > "$dst/VENDORED.txt"
echo "vendored $(cat "$dst/VENDORED.txt")"
