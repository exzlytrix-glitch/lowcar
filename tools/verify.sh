#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "$0")/.." && pwd)"
lowcar_engine="${LOWCAR_GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
verification_log="$(mktemp -t lowcar-verification)"
trap 'rm -f "$verification_log"' EXIT
"$lowcar_engine" --headless --editor --path "$project_dir" --quit 2>&1 | tee "$verification_log"
"$lowcar_engine" --headless --fixed-fps 60 --path "$project_dir" --script res://tests/scaffold_smoke.gd 2>&1 | tee -a "$verification_log"
"$lowcar_engine" --headless --fixed-fps 60 --path "$project_dir" --script res://tests/city_building_smoke.gd 2>&1 | tee -a "$verification_log"
"$lowcar_engine" --headless --fixed-fps 60 --path "$project_dir" --script res://tests/car_animation_smoke.gd 2>&1 | tee -a "$verification_log"
"$lowcar_engine" --headless --fixed-fps 60 --path "$project_dir" --script res://tests/car_death_animation_smoke.gd 2>&1 | tee -a "$verification_log"
"$lowcar_engine" --headless --fixed-fps 60 --path "$project_dir" --script res://tests/car_motion_effects_smoke.gd 2>&1 | tee -a "$verification_log"
"$lowcar_engine" --headless --fixed-fps 60 --path "$project_dir" --script res://tests/charge_boost_smoke.gd 2>&1 | tee -a "$verification_log"
"$lowcar_engine" --headless --fixed-fps 60 --path "$project_dir" --script res://tests/police_chase_smoke.gd 2>&1 | tee -a "$verification_log"
# Godot can return zero after a script error in a node outside the test runner.
if rg -q '(^|[[:space:]])(SCRIPT ERROR:|ERROR:)' "$verification_log"; then
    echo "LOWCAR_VERIFY_FAILED: engine reported errors" >&2
    exit 1
fi
