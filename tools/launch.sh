#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
lowcar_engine="${LOWCAR_GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
exec "$lowcar_engine" --editor --path "$project_dir" "$@"

