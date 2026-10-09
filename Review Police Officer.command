#!/bin/zsh
project_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
exec /Applications/Godot.app/Contents/MacOS/Godot --path "$project_dir" res://scenes/review/police_officer_review.tscn
