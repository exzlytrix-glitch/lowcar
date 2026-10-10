#!/usr/bin/env bash
# Plays Lowcar: the hideout garage, the breakout, the chase through the endless city, the news report.
# Extra options go after --, e.g. tools/play.sh -- --seed=7, or -- --autoplay to watch the AI runner.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
lowcar_engine="${LOWCAR_GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
exec "$lowcar_engine" --path "$project_dir" res://scenes/game/game.tscn "$@"
