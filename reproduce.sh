#!/bin/sh
# A bounded sequence of single-worker child processes; no two run concurrently.
set -eu
OUT=${1:?Usage: sh reproduce.sh OUTPUT_DIRECTORY}
exec python reproduce.py "$OUT"
