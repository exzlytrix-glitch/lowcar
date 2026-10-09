"""Combines one round of parallel chase-training lines (the GitHub Actions matrix jobs in
.github/workflows/train-chase.yml) into the next round's starting point:

  * every line's checkpoint carries on, except the weakest quarter, which restart from a copy of one of
    the strongest (population-based training: bad lines stop wasting compute)
  * the league of past versions gets each line's newest snapshots, so next round every line also
    trains against what the other lines learned
  * the best cop brain and best runner brain are picked for the game

"Strongest" is judged against the league (past versions from all lines), not against the line's own
current partner, so lines that only got good at beating each other do not win.

Usage: python3 training/league_merge.py --lines DIR --out DIR [--prev DIR] [--round N]
  --lines  folder holding one sub-folder per finished line (the line-* artifacts)
  --prev   the previous round's folder (its league is kept)
"""

import argparse
import glob
import json
import os
import random
import re
import shutil

KEEP_PER_LINE = 2
POOL_PER_ROLE = 40


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--lines", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--prev", default="")
    p.add_argument("--round", type=int, default=1)
    p.add_argument("--seed", type=int, default=1)
    return p.parse_args()


def snapshot_order(path):
    """(round, update) from names like r3_cop_line2_u512.pt; files without a round are round 0."""
    name = os.path.basename(path)
    found_round = re.match(r"r(\d+)_", name)
    found_update = re.search(r"_u(\d+)\.pt$", name)
    return (int(found_round.group(1)) if found_round else 0, int(found_update.group(1)) if found_update else 0)


def main():
    args = parse_args()
    random.seed(args.seed + args.round)
    lines = []
    for folder in sorted(glob.glob(os.path.join(args.lines, "*"))):
        score_file = os.path.join(folder, "scores.json")
        if os.path.exists(score_file) and os.path.exists(os.path.join(folder, "checkpoint.pt")):
            with open(score_file) as handle:
                lines.append({"folder": folder, **json.load(handle)})
    if not lines:
        raise SystemExit("no finished training lines found")
    lines.sort(key=lambda line: int(line["line"]) if str(line["line"]).isdigit() else 0)
    for line in lines:
        line["strength"] = line.get("kill_vs_past", 0.0) + line.get("survive_vs_past", 0.0)

    os.makedirs(os.path.join(args.out, "lines"), exist_ok=True)
    league_out = os.path.join(args.out, "league")
    os.makedirs(league_out, exist_ok=True)

    ranked = sorted(lines, key=lambda line: line["strength"], reverse=True)
    quarter = len(lines) // 4
    top, bottom = ranked[:quarter], ranked[len(ranked) - quarter:] if quarter else []
    copies = {}
    for line in bottom:
        donor = random.choice(top)
        copies[line["line"]] = donor["line"]
    for line in lines:
        target = os.path.join(args.out, "lines", f"line_{line['line']}")
        os.makedirs(target, exist_ok=True)
        source = next(l for l in lines if l["line"] == copies.get(line["line"], line["line"]))
        shutil.copy(os.path.join(source["folder"], "checkpoint.pt"), os.path.join(target, "checkpoint.pt"))
        for name in ("progress.csv", "summary.md", "scores.json"):
            path = os.path.join(line["folder"], name)
            if os.path.exists(path):
                shutil.copy(path, os.path.join(target, name))

    if args.prev and os.path.isdir(os.path.join(args.prev, "league")):
        for path in glob.glob(os.path.join(args.prev, "league", "*.pt")):
            shutil.copy(path, os.path.join(league_out, os.path.basename(path)))
    for line in lines:
        for role in ("cop", "runner"):
            own = sorted(glob.glob(os.path.join(line["folder"], "league", f"{role}_*.pt")), key=snapshot_order)
            for path in own[-KEEP_PER_LINE:]:
                shutil.copy(path, os.path.join(league_out, f"r{args.round}_{os.path.basename(path)}"))
    for role in ("cop", "runner"):
        pool = sorted(glob.glob(os.path.join(league_out, f"*{role}_line*.pt")), key=snapshot_order)
        for path in pool[:-POOL_PER_ROLE]:
            os.remove(path)

    best_cop = max(lines, key=lambda line: line.get("kill_vs_past", 0.0))
    best_runner = max(lines, key=lambda line: line.get("survive_vs_past", 0.0))
    shutil.copy(os.path.join(best_cop["folder"], "cop_brain.json"), os.path.join(args.out, "cop_brain.json"))
    shutil.copy(os.path.join(best_runner["folder"], "runner_brain.json"), os.path.join(args.out, "runner_brain.json"))
    with open(os.path.join(args.out, "round.json"), "w") as handle:
        json.dump({"round": args.round, "lines": [l["line"] for l in lines], "best_cop_line": best_cop["line"],
                   "best_runner_line": best_runner["line"], "restarted_from": copies,
                   "scores": [{k: v for k, v in l.items() if k != "folder"} for l in lines]}, handle, indent=1)

    hours = max(l.get("trained_hours", 0.0) for l in lines)
    report = [f"# Chase training, round {args.round}", "",
              f"{len(lines)} lines trained in parallel (up to {hours} h each in total so far).", "",
              f"Best cops: line {best_cop['line']} (wreck past runners {best_cop.get('kill_vs_past', 0):.0%}). "
              f"Best runner: line {best_runner['line']} ({best_runner.get('runner_style', '?')}, survives past cops "
              f"{best_runner.get('survive_vs_past', 0):.0%}). Their brains are cop_brain.json and runner_brain.json.", "",
              "| line | runner style | cops wreck past runners | runner survives past cops | cops vs own runner | next round |",
              "|---|---|---|---|---|---|"]
    for line in lines:
        note = f"restarts from line {copies[line['line']]}" if line["line"] in copies else "continues"
        report.append(f"| {line['line']} | {line.get('runner_style', '?')} | {line.get('kill_vs_past', 0):.0%} | "
                      f"{line.get('survive_vs_past', 0):.0%} | {line.get('kill_rate', 0):.0%} | {note} |")
    league_counts = {role: len(glob.glob(os.path.join(league_out, f"*{role}_line*.pt"))) for role in ("cop", "runner")}
    report += ["", f"League for next round: {league_counts['cop']} past cop versions, {league_counts['runner']} past runners."]
    best_summary = os.path.join(best_cop["folder"], "summary.md")
    if os.path.exists(best_summary):
        with open(best_summary) as handle:
            report += ["", "---", "", handle.read()]
    with open(os.path.join(args.out, "summary.md"), "w") as handle:
        handle.write("\n".join(report) + "\n")
    print("\n".join(report[:8 + len(lines)]))


if __name__ == "__main__":
    main()
