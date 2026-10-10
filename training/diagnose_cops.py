"""Where do the cops' rewards come from? Runs a cop brain against a runner brain in the GPU world and
breaks every active cop's reward down by the route option it was on (chase, ahead, far, left, right):
time share, distance and speed, the raw reward parts, and what they are worth under a set of weights.
Answers "would a passive cop score better than an aggressive one under these rewards?".

  python3 training/diagnose_cops.py --world DIR --cop COP.json --runner RUNNER.json [--matches 256]
      [--decisions 1300] [--weights 0.05,3,0,-0.015,-0.004,-1.25,0.02,-0.02]
"""

import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gpu_world.brain import GameBrain  # noqa: E402
from gpu_world.chase import GpuChase  # noqa: E402

PARTS = ["team runner dmg", "runner wrecked", "metres closed", "own wall dmg", "own car-hit dmg", "own wreck",
         "dmg it dealt", "dmg to cops"]
ROUTES = ["chase", "ahead", "far", "left", "right"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--world", required=True)
    p.add_argument("--cop", required=True)
    p.add_argument("--runner", required=True)
    p.add_argument("--matches", type=int, default=256)
    p.add_argument("--decisions", type=int, default=1300)
    p.add_argument("--seed", type=int, default=5)
    p.add_argument("--weights", action="append", default=[],
                   help="name=w0,...,w7 (cop reward weights to price the parts with); repeatable")
    p.add_argument("--json", default="", help="also write the results here")
    args = p.parse_args()
    torch.manual_seed(args.seed)
    env = GpuChase(args.world, matches=args.matches, device="cpu", seed=args.seed)
    cop, runner = GameBrain(args.cop), GameBrain(args.runner)
    is_runner = torch.as_tensor(env.is_runner)
    runner_of = torch.as_tensor(env.match_of) * env.slots_per_match
    obs, _, _, flags, _ = env.reset()
    n_parts = len(PARTS)
    by_route = np.zeros((len(ROUTES), n_parts))
    steps_route = np.zeros(len(ROUTES))
    dist_route = np.zeros(len(ROUTES))
    speed_route = np.zeros(len(ROUTES))
    reversing = np.zeros(len(ROUTES))
    totals = np.zeros(n_parts)
    cop_steps = 0
    chases = wrecked_runners = 0
    gen = torch.Generator().manual_seed(args.seed)
    for _ in range(args.decisions):
        o = torch.as_tensor(obs)
        actions = torch.zeros(env.num_slots, 5)
        actions[~is_runner] = cop.decide(o[~is_runner], gen)
        actions[is_runner] = runner.decide(o[is_runner], gen)
        obs, _, parts, flags, stats = env.step(actions.numpy())
        chases += stats[0]
        wrecked_runners += stats[1]
        active = (flags[:, 1] > 0.5) & ~env.is_runner
        option = env.option.cpu().numpy()
        cars = env.cars
        dx = (cars.x - cars.x[runner_of]).cpu().numpy()
        dz = (cars.z - cars.z[runner_of]).cpu().numpy()
        dist = np.hypot(dx, dz)
        speed = np.hypot(cars.vx.cpu().numpy(), cars.vz.cpu().numpy())
        fwd = cars.fwd.cpu().numpy()
        for r in range(len(ROUTES)):
            m = active & (option == r)
            if not m.any():
                continue
            by_route[r] += parts[m].sum(0)
            steps_route[r] += m.sum()
            dist_route[r] += dist[m].sum()
            speed_route[r] += speed[m].sum()
            reversing[r] += (fwd[m] < -0.5).sum()
        totals += parts[active].sum(0)
        cop_steps += active.sum()
    weights = {"v1 (team reward, hint faded)": [0.05, 3.0, 0.0, -0.015, -0.004, -1.25, 0.02, -0.02],
               "v2 (team reward doubled)": [0.1, 3.0, 0.0, -0.015, -0.004, -1.25, 0.02, -0.02],
               "v3 (own hits, permanent hint)": [0.02, 3.0, 0.005, -0.015, -0.004, -1.25, 0.12, -0.02]}
    for entry in args.weights:
        name, values = entry.split("=")
        weights[name] = [float(v) for v in values.split(",")]
    per_min = 600.0  # decisions per minute (10 a second)
    result = {"cop": args.cop, "runner": args.runner, "chases_ended": int(chases),
              "runner_wreck_share": wrecked_runners / max(chases, 1),
              "cop_minutes": cop_steps / per_min, "routes": {}, "totals_per_cop_minute": {}}
    print(f"cop {os.path.basename(os.path.dirname(args.cop)) or args.cop} vs runner "
          f"{os.path.basename(os.path.dirname(args.runner)) or args.runner}: {int(chases)} chases ended, runner wrecked in "
          f"{100 * result['runner_wreck_share']:.1f}%, {cop_steps / per_min:.0f} cop-minutes")
    for k, name in enumerate(PARTS):
        result["totals_per_cop_minute"][name] = round(totals[k] / cop_steps * per_min, 3)
    own_share = totals[6] / max(totals[0], 1e-6)
    print(f"  per cop-minute: team runner dmg {totals[0] / cop_steps * per_min:.2f} HP, dealt itself "
          f"{totals[6] / cop_steps * per_min:.2f} HP ({100 * own_share:.0f}% of the team reward it receives), walls "
          f"{totals[3] / cop_steps * per_min:.2f} HP, wrecks {totals[5] / cop_steps * per_min:.3f}")
    header = f"  {'route':6} {'time':>6} {'dist m':>7} {'km/h':>6} {'rev%':>5} " + \
             " ".join(f"{n[:10]:>10}" for n in PARTS) + "   " + "  ".join(f"{w[:2]}/min" for w in weights)
    print(header)
    for r, route in enumerate(ROUTES):
        s = max(steps_route[r], 1)
        rates = by_route[r] / s * per_min
        values = {w: float(np.dot(rates, weights[w])) for w in weights}
        result["routes"][route] = {"time_share": steps_route[r] / max(cop_steps, 1), "dist": dist_route[r] / s,
                                   "kmh": speed_route[r] / s * 3.6, "reversing": reversing[r] / s,
                                   "parts_per_min": dict(zip(PARTS, rates.round(4).tolist())),
                                   "reward_per_min": values}
        print(f"  {route:6} {100 * steps_route[r] / max(cop_steps, 1):5.1f}% {dist_route[r] / s:7.1f} "
              f"{speed_route[r] / s * 3.6:6.1f} {100 * reversing[r] / s:5.1f} " +
              " ".join(f"{v:10.3f}" for v in rates) + "   " + "  ".join(f"{values[w]:+7.3f}" for w in weights))
    overall = totals / max(cop_steps, 1) * per_min
    print("  overall reward per cop-minute: " + ", ".join(f"{w}: {np.dot(overall, weights[w]):+.3f}" for w in weights))
    result["reward_per_min"] = {w: float(np.dot(overall, weights[w])) for w in weights}
    if args.json:
        with open(args.json, "w") as handle:
            json.dump(result, handle, indent=1)


if __name__ == "__main__":
    main()
