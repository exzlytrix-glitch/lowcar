"""Combines one round of parallel chase-training lines (the GitHub Actions matrix jobs in
.github/workflows/train-chase.yml) into the next round's starting point.

* Judging: every line ends its run with an exam against the same fixed opponents (scripted autopilot,
  a fixed anchor from an early round, recent champions). Cops and runners are ranked separately on it,
  and get Elo ratings (Bradley-Terry fit over all exam games, scripted opponent = 1000). Lines without an
  exam fall back to their training win rates.
* Population-based training, per side: the weakest quarter of cops are replaced by copies of the
  strongest quarter's cops (same for runners), and the copy's settings (learning rate, gamma,
  exploration, batch size) are nudged by x0.8 or x1.2, so good settings spread and keep being tuned.
* The league of past versions gets each line's newest snapshots, so every line also trains against
  what the other lines learned; the next exam panel keeps the anchor and adds this round's champions.
* The best cop and runner brains are picked for the game, and progress against the fixed opponents is
  kept across rounds.

Usage: python3 training/league_merge.py --lines DIR --out DIR [--prev DIR] [--round N]
"""

import argparse
import glob
import json
import math
import os
import random
import re
import shutil

KEEP_PER_LINE = 2
POOL_PER_ROLE = 40
PANEL_CHAMPIONS = 3
STEP_CHOICES = [512, 768, 1024]
ROLES = ("cop", "runner")


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


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path) as handle:
        return json.load(handle)


def strength(line, role):
    exam = line.get("exam")
    if exam and exam.get(f"{role}_score") is not None and any(v["games"] for v in exam[role].values()):
        return exam[f"{role}_score"]
    return line["scores"].get("kill_vs_past" if role == "cop" else "survive_vs_past", 0.0)


def nudge(side):
    out = dict(side)
    out["lr"] = min(max(side["lr"] * random.choice([0.8, 1.2]), 5e-5), 1e-3)
    out["ent_discrete"] = min(max(side["ent_discrete"] * random.choice([0.8, 1.2]), 1e-4), 0.05)
    horizon = (1.0 - side["gamma"]) * random.choice([0.8, 1.2])
    out["gamma"] = round(min(max(1.0 - horizon, 0.98), 0.998), 5)
    return out


def nudge_steps(steps):
    index = STEP_CHOICES.index(steps) if steps in STEP_CHOICES else 1
    return STEP_CHOICES[min(max(index + random.choice([-1, 0, 1]), 0), len(STEP_CHOICES) - 1)]


def bradley_terry(results, fixed):
    """Ratings from (a, b, wins of a, games) results, with `fixed` held at 0. A small pull toward 0 keeps
    ratings finite when someone won or lost everything. Returns Elo-style numbers (fixed = 1000)."""
    names = {a for a, _, _, _ in results} | {b for _, b, _, _ in results}
    rating = {n: 0.0 for n in names}
    played = {n: 0.0 for n in names}
    for a, b, _, g in results:
        played[a] += g
        played[b] += g
    for _ in range(4000):
        grad = {n: -0.05 * rating[n] for n in names}
        for a, b, w, g in results:
            if g <= 0:
                continue
            p = 1.0 / (1.0 + math.exp(rating[b] - rating[a]))
            grad[a] += w - g * p
            grad[b] -= w - g * p
        for n in names:
            if n != fixed:
                rating[n] += 0.5 * grad[n] / max(played[n], 1.0)
    return {n: round(1000.0 + rating[n] * 400.0 / math.log(10.0)) for n in names}


def newest_snapshot(folder, role):
    own = sorted(glob.glob(os.path.join(folder, "league", f"{role}_*.pt")), key=snapshot_order)
    return own[-1] if own else None


def main():
    args = parse_args()
    random.seed(args.seed * 1000 + args.round)
    lines = []
    for folder in sorted(glob.glob(os.path.join(args.lines, "*"))):
        scores = read_json(os.path.join(folder, "scores.json"))
        if scores is None or not os.path.exists(os.path.join(folder, "checkpoint.pt")):
            continue
        lines.append({"folder": folder, "line": str(scores["line"]), "scores": scores,
                      "exam": read_json(os.path.join(folder, "exam.json")),
                      "genome": read_json(os.path.join(folder, "genome.json"))})
    if not lines:
        raise SystemExit("no finished training lines found")
    lines.sort(key=lambda line: int(line["line"]) if line["line"].isdigit() else 0)
    by_name = {line["line"]: line for line in lines}

    # Elo from the exam: line cops vs panel runners, line runners vs panel cops.
    elo = {}
    for role in ROLES:
        results = []
        for line in lines:
            exam = line.get("exam") or {}
            for opponent, record in exam.get(role, {}).items():
                results.append((f"line {line['line']}", f"panel {opponent}", record["wins"], record["games"]))
        elo[role] = bradley_terry(results, "panel scripted") if results else {}
        for line in lines:
            line[f"{role}_elo"] = elo[role].get(f"line {line['line']}")
            line[f"{role}_strength"] = strength(line, role)

    # Population-based training, per side.
    quarter = len(lines) // 4
    replaced = {role: {} for role in ROLES}
    for role in ROLES:
        ranked = sorted(lines, key=lambda line: line[f"{role}_strength"], reverse=True)
        if quarter:
            for line in ranked[len(ranked) - quarter:]:
                replaced[role][line["line"]] = random.choice(ranked[:quarter])["line"]
    os.makedirs(os.path.join(args.out, "lines"), exist_ok=True)
    surgery = any(replaced[role] for role in ROLES)
    if surgery:
        import torch  # only needed when a side is copied between checkpoints
    for line in lines:
        target = os.path.join(args.out, "lines", f"line_{line['line']}")
        os.makedirs(target, exist_ok=True)
        genome = json.loads(json.dumps(line["genome"])) if line["genome"] else None
        own = os.path.join(line["folder"], "checkpoint.pt")
        donors = {role: replaced[role].get(line["line"]) for role in ROLES}
        if any(donors.values()):
            state = torch.load(own, weights_only=False)
            for role in ROLES:
                donor = donors[role]
                if donor is None:
                    continue
                donor_line = by_name[donor]
                donor_state = torch.load(os.path.join(donor_line["folder"], "checkpoint.pt"), weights_only=False)
                state["learners"][role] = donor_state["learners"][role]
                if genome and donor_line["genome"]:
                    genome[role] = nudge(donor_line["genome"][role])
                    if role == "cop":
                        genome["steps"] = nudge_steps(donor_line["genome"].get("steps", 768))
            torch.save(state, os.path.join(target, "checkpoint.pt"))
        else:
            shutil.copy(own, os.path.join(target, "checkpoint.pt"))
        line["next_genome"] = genome
        if genome:
            with open(os.path.join(target, "genome.json"), "w") as handle:
                json.dump(genome, handle, indent=1)
        for name in ("progress.csv", "summary.md", "scores.json", "exam.json"):
            path = os.path.join(line["folder"], name)
            if os.path.exists(path):
                shutil.copy(path, os.path.join(target, name))

    # League pool.
    league_out = os.path.join(args.out, "league")
    os.makedirs(league_out, exist_ok=True)
    if args.prev and os.path.isdir(os.path.join(args.prev, "league")):
        for path in glob.glob(os.path.join(args.prev, "league", "*.pt")):
            shutil.copy(path, os.path.join(league_out, os.path.basename(path)))
    for line in lines:
        for role in ROLES:
            own = sorted(glob.glob(os.path.join(line["folder"], "league", f"{role}_*.pt")), key=snapshot_order)
            for path in own[-KEEP_PER_LINE:]:
                shutil.copy(path, os.path.join(league_out, f"r{args.round}_{os.path.basename(path)}"))
    for role in ROLES:
        pool = sorted(glob.glob(os.path.join(league_out, f"*{role}_line*.pt")), key=snapshot_order)
        for path in pool[:-POOL_PER_ROLE]:
            os.remove(path)

    # Best brains and next exam panel: keep the anchor (fixed forever), add this round's champion,
    # keep the newest PANEL_CHAMPIONS champions.
    best = {role: max(lines, key=lambda line: line[f"{role}_strength"]) for role in ROLES}
    shutil.copy(os.path.join(best["cop"]["folder"], "cop_brain.json"), os.path.join(args.out, "cop_brain.json"))
    shutil.copy(os.path.join(best["runner"]["folder"], "runner_brain.json"), os.path.join(args.out, "runner_brain.json"))
    panel_out = os.path.join(args.out, "exam")
    os.makedirs(panel_out, exist_ok=True)
    previous_panel = glob.glob(os.path.join(args.prev, "exam", "*.pt")) if args.prev else []
    for role in ROLES:
        anchors = [p for p in previous_panel if os.path.basename(p).startswith(f"anchor_{role}_")]
        champions = sorted([p for p in previous_panel if os.path.basename(p).startswith(f"champ_{role}_")],
                           key=lambda p: int(re.search(r"_r(\d+)\.pt$", p).group(1)))
        newest = newest_snapshot(best[role]["folder"], role)
        if newest:
            if not anchors:
                shutil.copy(newest, os.path.join(panel_out, f"anchor_{role}_r{args.round}.pt"))
            shutil.copy(newest, os.path.join(panel_out, f"champ_{role}_r{args.round}.pt"))
        for path in anchors + champions[-(PANEL_CHAMPIONS - 1):]:
            shutil.copy(path, os.path.join(panel_out, os.path.basename(path)))

    # Progress across rounds against the fixed opponents.
    history = (read_json(os.path.join(args.prev, "round.json"), {}) or {}).get("history", []) if args.prev else []

    def vs(line, role, prefix):
        exam = line.get("exam") or {}
        for name, record in exam.get(role, {}).items():
            if name.startswith(prefix) and record["games"]:
                return round(record["wins"] / record["games"], 3)
        return None

    history.append({"round": args.round,
                    "cop_vs_scripted": vs(best["cop"], "cop", "scripted"),
                    "runner_vs_scripted": vs(best["runner"], "runner", "scripted"),
                    "cop_vs_anchor": vs(best["cop"], "cop", "anchor_"),
                    "runner_vs_anchor": vs(best["runner"], "runner", "anchor_"),
                    "best_cop_elo": best["cop"].get("cop_elo"), "best_runner_elo": best["runner"].get("runner_elo")})
    with open(os.path.join(args.out, "round.json"), "w") as handle:
        json.dump({"round": args.round, "best_cop_line": best["cop"]["line"], "best_runner_line": best["runner"]["line"],
                   "replaced": replaced, "elo": elo, "history": history,
                   "lines": [{k: v for k, v in l.items() if k not in ("folder", "next_genome")} for l in lines]}, handle, indent=1)

    def pct(value):
        return "–" if value is None else f"{value:.0%}"

    hours = max(l["scores"].get("trained_hours", 0.0) for l in lines)
    report = [f"# Chase training, round {args.round}", "",
              f"{len(lines)} lines trained in parallel (up to {hours} h each in total so far). Lines are judged on an "
              "exam against fixed opponents; Elo: the scripted opponent is 1000, +200 means winning about 3 of 4.", "",
              f"**Best cops:** line {best['cop']['line']} (exam {pct(best['cop']['cop_strength'])}, Elo {best['cop'].get('cop_elo')}). "
              f"**Best runner:** line {best['runner']['line']} ({best['runner']['scores'].get('runner_style', '?')}, "
              f"exam {pct(best['runner']['runner_strength'])}, Elo {best['runner'].get('runner_elo')}). "
              "Their brains are cop_brain.json and runner_brain.json.", "",
              "## Progress against fixed opponents (best line each round)", "",
              "| round | cops wreck scripted runner | runner survives scripted cops | cops wreck anchor runner | runner survives anchor cops | cop Elo | runner Elo |",
              "|---|---|---|---|---|---|---|"]
    for h in history:
        report.append(f"| {h['round']} | {pct(h['cop_vs_scripted'])} | {pct(h['runner_vs_scripted'])} | {pct(h['cop_vs_anchor'])} | "
                      f"{pct(h['runner_vs_anchor'])} | {h['best_cop_elo'] or '–'} | {h['best_runner_elo'] or '–'} |")
    report += ["", "## Lines", "",
               "| line | runner style | cop exam | cop Elo | runner exam | runner Elo | next round's cop settings (lr / gamma / steps) | next round |",
               "|---|---|---|---|---|---|---|---|"]
    for line in lines:
        genome = line.get("next_genome") or {}
        cop_side = genome.get("cop", {})
        notes = [f"{role} copied from line {replaced[role][line['line']]}" for role in ROLES if line["line"] in replaced[role]]
        report.append(f"| {line['line']} | {line['scores'].get('runner_style', '?')} | {pct(line['cop_strength'])} | "
                      f"{line.get('cop_elo') or '–'} | {pct(line['runner_strength'])} | {line.get('runner_elo') or '–'} | "
                      f"{cop_side.get('lr', 0):.1e} / {cop_side.get('gamma', '–')} / {genome.get('steps', '–')} | "
                      f"{', '.join(notes) or 'continues'} |")
    counts = {role: len(glob.glob(os.path.join(league_out, f"*{role}_line*.pt"))) for role in ROLES}
    report += ["", f"League for next round: {counts['cop']} past cop versions, {counts['runner']} past runners. "
               f"Next exam panel: {', '.join(sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(panel_out, '*.pt'))))} "
               "plus the scripted opponent."]
    best_summary = os.path.join(best["cop"]["folder"], "summary.md")
    if os.path.exists(best_summary):
        with open(best_summary) as handle:
            report += ["", "---", "", handle.read()]
    with open(os.path.join(args.out, "summary.md"), "w") as handle:
        handle.write("\n".join(report) + "\n")
    print("\n".join(report[:12 + len(history)]))


if __name__ == "__main__":
    main()
