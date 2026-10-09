#!/usr/bin/env bash
# Opens the city generator lab: drive the red car around a generated city and tune it live.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
lowcar_engine="${LOWCAR_GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
exec "$lowcar_engine" --path "$project_dir" res://scenes/review/city_lab.tscn "$@"
