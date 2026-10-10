"""Replays a Godot trace (tools/gpu_parity_trace.gd) in the GPU world's car physics and reports how
far the two drift apart. Same city, same start, same controls every decision.

  python3 training/gpu_world/parity.py --world DIR --trace FILE [--plot out.png]
"""

import argparse
import json
import math
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gpu_world.city import Cities  # noqa: E402
from gpu_world.physics import Cars, load_specs, wrap_angle  # noqa: E402


def replay(world, trace_path, city_index=None):
    with open(trace_path) as handle:
        trace = json.load(handle)
    data, specs, lab = load_specs(os.path.join(world, "cars.json"))
    cities = Cities(world, limit=None)
    if city_index is None:
        city_index = next(i for i, m in enumerate(cities.meta) if m["seed"] == trace["city_seed"])
    roles = trace["roles"]
    kind = torch.tensor([0 if r == "runner" else 1 for r in roles])
    cars = Cars(len(roles), specs, kind, lab)
    cars.city = torch.full((len(roles),), city_index, dtype=torch.long)
    frames = [np.array(f) for f in trace["frames"]]
    for i, f in enumerate(frames):
        s = f[0]
        cars.x[i], cars.z[i], cars.yaw[i], cars.vx[i], cars.vz[i], cars.fwd[i] = s[0], s[1], s[2], s[3], s[4], s[5]
    if len(roles) > 1:
        cars.max_speed[1] = trace.get("cop_top_speed", cars.max_speed[1])
    controls = trace["controls"]
    dt = 1.0 / data["physics_hz"]
    total = len(frames[0])
    pairs = torch.tensor([[0, 1]]) if len(roles) > 1 else torch.zeros(0, 2, dtype=torch.long)
    out = np.zeros((len(roles), total, 7))
    command = torch.zeros(len(roles), 4)
    for frame in range(total - 1):
        if frame % 6 == 0:
            command = torch.tensor([controls[i][frame // 6] for i in range(len(roles))], dtype=torch.float32)
        _, before = cars.step(command[:, 0], command[:, 1], command[:, 2] > 0.5, command[:, 3] > 0.5,
                              torch.ones(len(roles), dtype=torch.bool), cities, dt)
        if len(roles) > 1:
            cars.crashes(pairs, before, frame)
        for i in range(len(roles)):
            out[i, frame + 1] = [cars.x[i], cars.z[i], cars.yaw[i], cars.vx[i], cars.vz[i], cars.fwd[i], cars.health[i]]
    return trace, frames, out


def report(trace, frames, out):
    lines = [f"scenario {trace['scenario']} ({len(trace['roles'])} car(s), {len(frames[0]) / 60:.0f} s)"]
    for i, role in enumerate(trace["roles"]):
        godot = frames[i]
        mine = out[i]
        for seconds in (0.5, 1, 2, 5, 10, 20):
            f = min(int(seconds * 60), len(godot) - 1)
            pos = math.hypot(godot[f][0] - mine[f][0], godot[f][1] - mine[f][1])
            yaw = abs(float(wrap_angle(torch.tensor(godot[f][2] - mine[f][2]))))
            lines.append(f"  {role} t={seconds:>4}s  position off {pos:6.2f} m  heading off {math.degrees(yaw):5.1f} deg  "
                         f"speed godot {godot[f][5]:5.1f} gpu {mine[f][5]:5.1f}  health godot {godot[f][7]:5.1f} gpu {mine[f][6]:5.1f}")
        gd = [f for f in range(1, len(godot)) if godot[f][7] < godot[f - 1][7] - 1e-3]
        gp = [f for f in range(1, len(mine)) if mine[f][6] < mine[f - 1][6] - 1e-3]
        lines.append(f"  {role} damage events: godot at {[round(f / 60, 2) for f in gd][:8]}  gpu at {[round(f / 60, 2) for f in gp][:8]}")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--world", required=True)
    p.add_argument("--trace", nargs="+", required=True)
    p.add_argument("--horizon", type=int, default=60, help="frames per resynced segment (0 = one long replay)")
    args = p.parse_args()
    for path in args.trace:
        if args.horizon <= 0:
            print(report(*replay(args.world, path)))
        else:
            print(os.path.basename(path))
            print(summarize(segment_errors(args.world, path, args.horizon), args.horizon))


STATE = ["x", "z", "yaw", "vx", "vz", "fwd", "drifting", "health", "boost_phase", "slip", "spin", "steer",
         "grip_return", "drift_time", "stagger", "wall_contact", "boost_charge", "boost_power", "boost_duration",
         "boost_elapsed", "max_speed"]


def segment_errors(world, trace_path, horizon=60, stride=30):
    """Restarts the GPU car from Godot's exact state every `stride` frames, replays `horizon` frames of the
    same controls and measures the error at the end. Segments are labelled by what happened in Godot:
    'crash' (cars hit), 'wall' (a wall contact) or 'free'."""
    with open(trace_path) as handle:
        trace = json.load(handle)
    data, specs, lab = load_specs(os.path.join(world, "cars.json"))
    cities = Cities(world)
    city_index = next(i for i, m in enumerate(cities.meta) if m["seed"] == trace["city_seed"])
    roles = trace["roles"]
    kind = torch.tensor([0 if r == "runner" else 1 for r in roles])
    frames = [np.array(f) for f in trace["frames"]]
    controls = trace["controls"]
    dt = 1.0 / data["physics_hz"]
    pairs = torch.tensor([[0, 1]]) if len(roles) > 1 else torch.zeros(0, 2, dtype=torch.long)
    results = {"free": [], "wall": [], "crash": []}
    total = len(frames[0])
    for start in range(0, total - horizon, stride):
        start -= start % 6
        cars = Cars(len(roles), specs, kind, lab)
        cars.city = torch.full((len(roles),), city_index, dtype=torch.long)
        for i in range(len(roles)):
            for k, name in enumerate(STATE):
                getattr(cars, name)[i] = float(frames[i][start][k])
        command = None
        for frame in range(start, start + horizon):
            if frame % 6 == 0:
                command = torch.tensor([controls[i][frame // 6] for i in range(len(roles))], dtype=torch.float32)
            _, before = cars.step(command[:, 0], command[:, 1], command[:, 2] > 0.5, command[:, 3] > 0.5,
                                  torch.ones(len(roles), dtype=torch.bool), cities, dt)
            if len(roles) > 1:
                cars.crashes(pairs, before, frame)
        for i in range(len(roles)):
            g0, g1 = frames[i][start], frames[i][start + horizon]
            seg = frames[i][start:start + horizon + 1]
            spun = np.abs(seg[:, 10]).max() > 0.3 if len(roles) > 1 else False
            label = "crash" if spun else ("wall" if seg[:, 15].max() > 0.5 else "free")
            pos = math.hypot(g1[0] - float(cars.x[i]), g1[1] - float(cars.z[i]))
            yaw = abs(math.degrees(float(wrap_angle(torch.tensor(g1[2] - float(cars.yaw[i]))))))
            speed = abs(g1[5] - float(cars.fwd[i]))
            dmg_g, dmg_p = g0[7] - g1[7], float(frames[i][start][7] - cars.health[i])
            results[label].append((pos, yaw, speed, dmg_g, dmg_p))
    return results


def summarize(results, horizon):
    lines = []
    for label, rows in results.items():
        if not rows:
            continue
        a = np.array(rows)
        lines.append(f"  {label:5s} {len(a):4d} segments of {horizon / 60:.1f}s: position off median {np.median(a[:, 0]):5.2f} m "
                     f"(90% {np.percentile(a[:, 0], 90):5.2f}), heading median {np.median(a[:, 1]):5.1f} deg "
                     f"(90% {np.percentile(a[:, 1], 90):5.1f}), speed median {np.median(a[:, 2]):4.1f} m/s, "
                     f"damage godot {a[:, 3].sum():6.1f} gpu {a[:, 4].sum():6.1f}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
