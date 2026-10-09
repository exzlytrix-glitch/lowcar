#!/bin/zsh
project_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
exec /Applications/Godot.app/Contents/MacOS/Godot --path "$project_dir" res://scenes/review/street_stuff_review.tscn
