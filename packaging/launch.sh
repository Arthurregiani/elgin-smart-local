#!/bin/sh
set -eu
# Works in /usr/bin and in an extracted .deb used for validation.
app_root=$(CDPATH= cd -- "$(dirname -- "$0")/../lib/elgin-smart-local" && pwd)
export ELGIN_HOME="$app_root"
exec "$app_root/elgin-smart-local" "$@"
