#!/usr/bin/env bash
# GPU pretraining for the chase brains (Kaggle notebook training/kaggle_gpu_pretrain.ipynb, or any Linux
# machine with an NVIDIA GPU): fetches Godot, exports cities from the real game, then trains cops and
# runner in the GPU copy of the chase (training/gpu_world/) for HOURS hours.
# The result (checkpoint.pt, cop_brain.json, runner_brain.json, progress.csv, summary.md) lands in OUT and
# continues in the real game with the GitHub chase training (it carries over like any checkpoint).
#
#   bash training/gpu_pretrain.sh HOURS [CHASES] [CITIES] [OUT] [WORLD]
# Environment: GODOT=path (skip the download), DEVICE=cuda|cpu, STEPS=64
set -euo pipefail
HOURS=${1:-10}
CHASES=${2:-4096}
CITIES=${3:-96}
OUT=${4:-/kaggle/working/out}
WORLD=${5:-/kaggle/working/world}
DEVICE=${DEVICE:-cuda}
STEPS=${STEPS:-64}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
GODOT_URL=https://github.com/godotengine/godot/releases/download/4.7-stable/Godot_v4.7-stable_linux.x86_64.zip

if [ -z "${GODOT:-}" ]; then
  GODOT="$(dirname "$OUT")/godot/godot"
  if [ ! -x "$GODOT" ]; then
    mkdir -p "$(dirname "$GODOT")"
    curl -fsSL -o /tmp/godot.zip "$GODOT_URL"
    unzip -q -o /tmp/godot.zip -d "$(dirname "$GODOT")"
    mv "$(dirname "$GODOT")"/Godot_v4.7-stable_linux.x86_64 "$GODOT"
    chmod +x "$GODOT"
  fi
fi
echo "== Godot: $("$GODOT" --version)"

if [ ! -f "$ROOT/.godot/global_script_class_cache.cfg" ]; then
  echo "== importing the project"
  "$GODOT" --headless --import --path "$ROOT" >/dev/null 2>&1 || "$GODOT" --headless --editor --quit --path "$ROOT" >/dev/null 2>&1
fi

if [ ! -f "$WORLD/city_$((CITIES - 1)).solid" ]; then
  echo "== exporting $CITIES cities"
  mkdir -p "$WORLD"
  PER=$(( (CITIES + 3) / 4 ))
  for i in 0 1 2 3; do
    FIRST=$(( i * PER ))
    COUNT=$(( CITIES - FIRST < PER ? CITIES - FIRST : PER ))
    [ "$COUNT" -gt 0 ] && "$GODOT" --headless --path "$ROOT" --script res://tools/export_gpu_world.gd -- \
      --out="$WORLD" --cities="$COUNT" --first="$FIRST" --seed=50000 > "$WORLD/export_$i.log" 2>&1 &
  done
  wait
  grep -h "GPU_WORLD" "$WORLD"/export_*.log | tail -3
fi

START="--init $ROOT/resources/ai/cop_brain.json"
if [ -f "$ROOT/training/seeds/chase_seed.pt" ]; then
  START="--resume $ROOT/training/seeds/chase_seed.pt"
fi
mkdir -p "$OUT"
echo "== training $HOURS h on $DEVICE with $CHASES chases at once ($START)"
python3 "$ROOT/training/train_chase.py" --gpu-world "$WORLD" --gpu-matches "$CHASES" --device "$DEVICE" \
  --steps-force "$STEPS" --hours "$HOURS" --out "$OUT" --line gpu --threads 4 --snapshot-minutes 30 $START
cat "$OUT/summary.md"
