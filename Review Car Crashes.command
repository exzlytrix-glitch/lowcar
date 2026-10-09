#!/bin/zsh
project_dir="$(cd -- "$(dirname -- "$0")" && pwd)"
exec "$project_dir/tools/animation_garage.sh" -- --death-review
