#!/bin/sh
# Build the standalone IPS with the repository's patch generator.
set -eu

root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if [ "$#" -eq 0 ]; then
    set -- --help
fi
exec "${PYTHON:-python3}" -B "$root/tools/build_patch.py" "$@"
