"""Trains learned cops against a learned runner: self-play PPO (MAPPO-style) in the chase arena.

Two brains learn at the same time. The cop brain is shared by every cop in every squad (1-5 cops,
changing mid-chase); the runner brain drives a car with the player's advantages. Each new trick one
side finds is a problem the other side has to solve, like OpenAI's hide-and-seek.

Rewards only score winning, not tactics: cops score for damage on the runner and for wrecking it,
the runner for staying alive and in one piece (plus a little for wrecking cops, like the game's chaos
score). Small extras keep driving sane: wall hits cost a little, and early on cops get a hint for
closing in, which fades out (--approach-fade-steps) so they are left with winning only.

Each brain is an actor (what runs in the game, small enough for GDScript) and a critic that sees extra
facts the actor does not, such as where the runner really is (centralised training, decentralised
play). A pool of past versions of both sides (plus versions from other training lines) plays some
chases, so neither side forgets how to beat old tricks.

Outputs in --out:
  checkpoint.pt      full training state for resuming
  cop_brain.json     cop actor for the game (scripts/ai/policy_net.gd)
  runner_brain.json  runner actor (lab autopilot)
  league/            snapshots of past versions (opponents for later training)
  scores.json        recent win rates, for picking the best training line
  progress.csv, summary.md

Local smoke test:
  python3 training/train_chase.py --godot /Applications/Godot.app/Contents/MacOS/Godot --project . \\
      --out /tmp/chase --procs 2 --matches 4 --minutes 5 --init resources/ai/cop_brain.json
"""

import argparse
import copy
import csv
import glob
import json
import os
import time
from collections import deque

import numpy as np
import torch
import torch.nn as nn
from torch.distributions.normal import Normal

from chase_env import ChaseWorlds

ROLES = ("cop", "runner")
# Weights for the reward parts each slot reports (meanings at the top of scripts/ai/chase_match.gd).
WEIGHTS = {
    # runner damage (team), runner wrecked (team), metres closed (fades out), own wall damage,
    # own damage from car hits, own wreck, damage it dealt to the runner, damage it dealt to other cops
    "cop": [0.05, 3.0, 0.02, -0.01, -0.004, -1.0, 0.02, -0.02],
    # alive, damage taken, wrecked, damage dealt to cops, cops wrecked, speed, wall damage, survived
    "runner": [0.02, -0.05, -3.0, 0.01, 0.4, 0.0, 0.0, 0.0],
}
APPROACH_PART = 2
# Runner personalities: each training line gives its runner one, so the cops (and the league of past
# versions) face different kinds of drivers. Changes to the runner weights above, by part index.
RUNNER_STYLES = {
    "balanced": {},
    "aggressive": {3: 0.04, 4: 1.6},     # goes looking for cops to wreck
    "speedy": {5: 0.002},                 # rewarded for keeping its speed up, like the real game
    "careful": {1: -0.08, 6: -0.03},      # hates every scratch
}
ACTION_NAMES = {"cop": ["steer", "throttle", "handbrake", "burst"],
                "runner": ["steer", "throttle", "handbrake", "boost"]}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--godot", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--line", default="0", help="name of this training line (parallel jobs)")
    p.add_argument("--runner-style", default="balanced", choices=sorted(RUNNER_STYLES))
    p.add_argument("--hours", type=float, default=0.0)
    p.add_argument("--minutes", type=float, default=0.0)
    p.add_argument("--procs", type=int, default=3)
    p.add_argument("--matches", type=int, default=6, help="chases per Godot process")
    p.add_argument("--steps", type=int, default=256, help="decisions per slot per update")
    p.add_argument("--lr", type=float, default=2.5e-4)
    p.add_argument("--epochs", type=int, default=4)
    p.add_argument("--minibatches", type=int, default=8)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--gae-lambda", type=float, default=0.95)
    p.add_argument("--clip", type=float, default=0.2)
    p.add_argument("--ent", type=float, default=0.001)
    p.add_argument("--vf", type=float, default=0.5)
    p.add_argument("--max-grad", type=float, default=0.5)
    p.add_argument("--actor-hidden", type=int, default=128)
    p.add_argument("--critic-hidden", type=int, default=256)
    p.add_argument("--city-steps", type=int, default=3000)
    p.add_argument("--radius", type=float, default=450.0)
    p.add_argument("--past-share", type=float, default=0.2,
                   help="share of chases where one side is a past version (each side)")
    p.add_argument("--pool-size", type=int, default=40)
    p.add_argument("--snapshot-minutes", type=float, default=20.0)
    p.add_argument("--approach-fade-steps", type=float, default=30e6,
                   help="cop decisions over which the closing-in hint fades to zero")
    p.add_argument("--save-minutes", type=float, default=10.0)
    p.add_argument("--resume", default="")
    p.add_argument("--init", default="", help="driving-school brain (cop_brain.json or checkpoint.pt) to start both from")
    p.add_argument("--critic-warmup", type=int, default=6, help="updates that train only critics after --init")
    p.add_argument("--league-in", default="", help="folder of snapshots from earlier rounds / other lines")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--threads", type=int, default=1)
    return p.parse_args()


def layer_init(layer, std=np.sqrt(2), bias=0.0):
    nn.init.orthogonal_(layer.weight, std)
    nn.init.constant_(layer.bias, bias)
    return layer


class Actor(nn.Module):
    def __init__(self, obs_dim, act_dim, hidden):
        super().__init__()
        self.net = nn.Sequential(
            layer_init(nn.Linear(obs_dim, hidden)), nn.Tanh(),
            layer_init(nn.Linear(hidden, hidden)), nn.Tanh(),
            layer_init(nn.Linear(hidden, act_dim), std=0.01))
        self.logstd = nn.Parameter(torch.full((1, act_dim), -0.5))
        with torch.no_grad():
            self.net[4].bias[3] = -1.0  # burst / boost starts mostly off

    def dist(self, x):
        mean = self.net(x)
        return Normal(mean, torch.exp(self.logstd.expand_as(mean)))


class Critic(nn.Module):
    def __init__(self, in_dim, hidden):
        super().__init__()
        self.net = nn.Sequential(
            layer_init(nn.Linear(in_dim, hidden)), nn.Tanh(),
            layer_init(nn.Linear(hidden, hidden)), nn.Tanh(),
            layer_init(nn.Linear(hidden, 1), std=1.0))

    def forward(self, x):
        return self.net(x).flatten()


class RunningMeanStd:
    def __init__(self, shape=()):
        self.mean = np.zeros(shape, np.float64)
        self.var = np.ones(shape, np.float64)
        self.count = 1e-4

    def update(self, x):
        if len(x) == 0:
            return
        batch_mean, batch_var, batch_count = x.mean(0), x.var(0), x.shape[0]
        delta = batch_mean - self.mean
        total = self.count + batch_count
        self.mean = self.mean + delta * batch_count / total
        m2 = self.var * self.count + batch_var * batch_count + delta ** 2 * self.count * batch_count / total
        self.var = m2 / total
        self.count = total

    def normalize(self, x):
        return np.clip((x - self.mean) / np.sqrt(self.var + 1e-8), -10.0, 10.0).astype(np.float32)

    def state(self):
        return {"mean": self.mean.tolist(), "var": self.var.tolist(), "count": self.count}

    def load(self, state):
        self.mean = np.array(state["mean"], np.float64)
        self.var = np.array(state["var"], np.float64)
        self.count = state["count"]


class Learner:
    """Everything one side learns with: actor, critic, optimiser and the input/return scaling."""

    def __init__(self, role, obs_dim, priv_dim, act_dim, args):
        self.role, self.obs_dim, self.priv_dim, self.act_dim = role, obs_dim, priv_dim, act_dim
        self.actor = Actor(obs_dim, act_dim, args.actor_hidden)
        self.critic = Critic(obs_dim + priv_dim, args.critic_hidden)
        self.optimizer = torch.optim.Adam(list(self.actor.parameters()) + list(self.critic.parameters()),
                                          lr=args.lr, eps=1e-5)
        self.obs_rms, self.priv_rms, self.ret_rms = RunningMeanStd((obs_dim,)), RunningMeanStd((priv_dim,)), RunningMeanStd(())
        self.weights = np.array(WEIGHTS[role], np.float64)
        if role == "runner":
            for part, weight in RUNNER_STYLES[args.runner_style].items():
                self.weights[part] = weight
        self.steps = 0

    def value_input(self, obs_n, priv_n):
        return torch.cat([obs_n, priv_n], dim=-1)

    def state(self):
        return {"actor": self.actor.state_dict(), "critic": self.critic.state_dict(),
                "optimizer": self.optimizer.state_dict(), "obs_rms": self.obs_rms.state(),
                "priv_rms": self.priv_rms.state(), "ret_rms": self.ret_rms.state(), "steps": self.steps}

    def load(self, state):
        self.actor.load_state_dict(state["actor"])
        self.critic.load_state_dict(state["critic"])
        self.optimizer.load_state_dict(state["optimizer"])
        self.obs_rms.load(state["obs_rms"])
        self.priv_rms.load(state["priv_rms"])
        self.ret_rms.load(state["ret_rms"])
        self.steps = state["steps"]

    def snapshot_data(self, name):
        return {"role": self.role, "name": name, "obs_dim": self.obs_dim, "act_dim": self.act_dim,
                "hidden": self.actor.net[0].out_features, "actor": copy.deepcopy(self.actor.state_dict()),
                "obs_mean": self.obs_rms.mean.copy(), "obs_var": self.obs_rms.var.copy(), "steps": self.steps}


class Snapshot:
    """A frozen past version of one side, used as an opponent."""

    def __init__(self, data, imported=False):
        self.role, self.name, self.imported = data["role"], data["name"], imported
        self.actor = Actor(data["obs_dim"], data["act_dim"], data["hidden"])
        self.actor.load_state_dict(data["actor"])
        self.actor.eval()
        self.rms = RunningMeanStd((data["obs_dim"],))
        self.rms.mean, self.rms.var = np.asarray(data["obs_mean"]), np.asarray(data["obs_var"])
        self.data = data
        self.uid = -1
        self.learner_win = 0.5  # how often the current learner beats this version (moving average)
        self.games = 0

    @torch.no_grad()
    def act(self, raw_obs):
        return self.actor.dist(torch.from_numpy(self.rms.normalize(raw_obs))).sample().numpy()


def warm_start(learner, path):
    """Starts a side from the driving-school brain: its 61 inputs and 3 controls keep their weights and
    the network is widened so it behaves exactly like the school driver at first (new inputs, units
    and the burst/boost control start at zero influence)."""
    if path.endswith(".json"):
        with open(path) as handle:
            data = json.load(handle)
        layers = [(np.array(l["w"], np.float32), np.array(l["b"], np.float32)) for l in data["layers"]]
        mean, std = np.array(data["obs_mean"]), np.array(data["obs_std"])
        var = std ** 2
    else:
        state = torch.load(path, weights_only=False)
        brain = state["brain"]
        layers = [(brain[f"actor_mean.{k}.weight"].numpy(), brain[f"actor_mean.{k}.bias"].numpy()) for k in (0, 2, 4)]
        mean, var = np.array(state["obs_rms"]["mean"]), np.array(state["obs_rms"]["var"])
    old_in = layers[0][0].shape[1]
    net = learner.actor.net
    with torch.no_grad():
        for index, linear in enumerate([net[0], net[2], net[4]]):
            w, b = layers[index]
            rows, cols = w.shape
            if index < 2:
                linear.weight[rows:, :].mul_(0.5)  # new units: small random weights
            else:
                linear.weight.zero_()  # outputs listen only to the school units at first
                linear.bias.zero_()
                linear.bias[3] = -1.0
            linear.weight[:rows, :] = 0.0
            linear.weight[:rows, :cols] = torch.from_numpy(w)
            linear.bias[:rows] = torch.from_numpy(b)
        learner.actor.logstd[:] = -1.0
        learner.actor.logstd[0, 3] = -0.5
    learner.obs_rms.mean[:old_in] = mean
    learner.obs_rms.var[:old_in] = var
    learner.obs_rms.count = 1e4


def export_brain(path, learner, meta):
    linear = [m for m in learner.actor.net if isinstance(m, nn.Linear)]
    layers = []
    for index, layer in enumerate(linear):
        layers.append({"w": layer.weight.detach().numpy().astype(float).round(6).tolist(),
                       "b": layer.bias.detach().numpy().astype(float).round(6).tolist(),
                       "act": "tanh" if index < len(linear) - 1 else "none"})
    data = dict(meta)
    data.update({"stage": "chase", "role": learner.role, "obs_dim": learner.obs_dim, "act_dim": learner.act_dim,
                 "steps": learner.steps,
                 "obs_mean": learner.obs_rms.mean.astype(float).round(6).tolist(),
                 "obs_std": np.sqrt(learner.obs_rms.var + 1e-8).astype(float).round(6).tolist(),
                 "obs_clip": 10.0, "layers": layers, "action_names": ACTION_NAMES[learner.role]})
    with open(path + ".tmp", "w") as handle:
        json.dump(data, handle)
    os.replace(path + ".tmp", path)


class League:
    """Past versions of both sides, and who plays which chase. Most chases are current cops vs the
    current runner; in --past-share of them the runner is a past version, in as many the cops are.
    Past versions the learner struggles against are picked more often."""

    CURRENT = -1

    def __init__(self, args, rng):
        self.args, self.rng = args, rng
        self.pool = {role: [] for role in ROLES}
        self.by_uid = {}  # also keeps versions dropped from the pool while a chase still uses them
        self._next_uid = 0

    def add(self, snapshot):
        snapshot.uid = self._next_uid
        self._next_uid += 1
        self.by_uid[snapshot.uid] = snapshot
        pool = self.pool[snapshot.role]
        pool.append(snapshot)
        while len(pool) > self.args.pool_size:
            own = [s for s in pool if not s.imported]
            pool.remove(own[0] if len(own) > len(pool) // 2 else pool[0])

    def forget_unused(self, in_use):
        keep = {s.uid for role in ROLES for s in self.pool[role]} | set(in_use)
        self.by_uid = {uid: s for uid, s in self.by_uid.items() if uid in keep}

    def pick(self):
        """(runner, cops) controllers for a new chase: CURRENT or the uid of a past version."""
        roll = self.rng.random()
        share = self.args.past_share
        if roll < share and self.pool["runner"]:
            return self._choose("runner"), self.CURRENT
        if roll < 2 * share and self.pool["cop"]:
            return self.CURRENT, self._choose("cop")
        return self.CURRENT, self.CURRENT

    def _choose(self, role):
        pool = self.pool[role]
        weights = np.array([(1.0 - s.learner_win) ** 1.5 + 0.1 for s in pool])
        return pool[int(self.rng.choice(len(pool), p=weights / weights.sum()))].uid

    def record(self, uid, learner_won):
        snap = self.by_uid.get(uid)
        if snap is not None:
            snap.games += 1
            snap.learner_win = 0.95 * snap.learner_win + 0.05 * float(learner_won)


def main():
    args = parse_args()
    budget = args.hours * 3600 + args.minutes * 60
    if budget <= 0:
        raise SystemExit("give --hours or --minutes")
    os.makedirs(os.path.join(args.out, "league"), exist_ok=True)
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    started = time.time()

    env = ChaseWorlds(args.godot, args.project, procs=args.procs, matches=args.matches, seed=args.seed,
                      city_steps=args.city_steps, radius=args.radius, log_dir=os.path.join(args.out, "logs"))
    S, A, M = env.num_slots, env.act_dim, env.num_matches
    dims = {"cop": env.cop_obs, "runner": env.runner_obs}
    slots = {"cop": np.nonzero(~env.is_runner)[0], "runner": np.nonzero(env.is_runner)[0]}
    match_of = {role: env.match_of[slots[role]] for role in ROLES}
    learners = {role: Learner(role, dims[role], env.priv_dim, A, args) for role in ROLES}
    league = League(args, rng)
    updates, prior_seconds, warmup_left = 0, 0.0, 0
    if args.resume and os.path.exists(args.resume):
        state = torch.load(args.resume, weights_only=False)
        for role in ROLES:
            learners[role].load(state["learners"][role])
        updates, prior_seconds = state["updates"], state.get("trained_seconds", 0.0)
        print(f"resumed from {args.resume}: {updates} updates, {prior_seconds / 3600:.2f} h trained")
    elif args.init:
        for role in ROLES:
            warm_start(learners[role], args.init)
        warmup_left = args.critic_warmup
        print(f"both sides start from the driving-school brain {args.init}")
    for pattern in ([os.path.join(args.league_in, "*.pt")] if args.league_in else []) + \
                   [os.path.join(args.out, "league", "*.pt")]:
        for path in sorted(glob.glob(pattern), key=os.path.getmtime):
            try:
                data = torch.load(path, weights_only=False)
            except Exception as error:  # a damaged file should not stop training
                print(f"skipping snapshot {path}: {error}")
                continue
            if data["obs_dim"] == dims[data["role"]]:
                league.add(Snapshot(data, imported=not path.startswith(os.path.join(args.out, "league"))))
    print(f"league: {len(league.pool['cop'])} past cop versions, {len(league.pool['runner'])} past runners")

    T, gamma, lam = args.steps, args.gamma, args.gae_lambda
    bufs = {}
    for role in ROLES:
        n, d = len(slots[role]), dims[role]
        bufs[role] = {"obs": torch.zeros((T, n, d)), "priv": torch.zeros((T, n, env.priv_dim)),
                      "act": torch.zeros((T, n, A)), "logp": torch.zeros((T, n)), "val": torch.zeros((T, n)),
                      "rew": torch.zeros((T, n)), "done": torch.zeros((T, n)), "valid": torch.zeros((T, n))}

    raw_obs, raw_priv, _, flags, _ = env.reset()
    controllers = [league.pick() for _ in range(M)]  # per chase: (runner, cops)
    discounted = {role: np.zeros(len(slots[role])) for role in ROLES}
    episode_return = {role: np.zeros(len(slots[role])) for role in ROLES}
    finished = {role: deque(maxlen=300) for role in ROLES}
    outcomes = {"current": deque(maxlen=300), "vs_past_runner": deque(maxlen=300), "vs_past_cops": deque(maxlen=300)}
    csv_path = os.path.join(args.out, "progress.csv")
    columns = ["hours", "updates", "cop_steps", "runner_steps", "sps", "kill_rate", "kill_vs_past", "survive_vs_past",
               "match_s", "runner_kmh", "runner_dmg_cops_min", "runner_dmg_walls_min", "cop_kmh", "cop_wall_dmg_min",
               "cop_wrecks_min", "cop_on_cop_min", "cops_per_chase", "known_pct", "cop_return", "runner_return",
               "approach_hint"]
    new_csv = not os.path.exists(csv_path)
    csv_file = open(csv_path, "a", newline="")
    writer = csv.writer(csv_file)
    if new_csv:
        writer.writerow(columns)
    history = []
    last_save = last_snapshot = time.time()

    def controller_of(role):
        side = 0 if role == "runner" else 1
        return np.array([controllers[m][side] for m in match_of[role]])

    def save(final=False):
        trained = prior_seconds + time.time() - started
        torch.save({"learners": {role: learners[role].state() for role in ROLES}, "updates": updates,
                    "trained_seconds": trained, "args": vars(args)}, os.path.join(args.out, "checkpoint.pt"))
        meta = {"line": args.line, "runner_style": args.runner_style, "trained_hours": round(trained / 3600, 3)}
        export_brain(os.path.join(args.out, "cop_brain.json"), learners["cop"], meta)
        export_brain(os.path.join(args.out, "runner_brain.json"), learners["runner"], meta)
        recent = history[-30:]
        scores = {"line": args.line, "runner_style": args.runner_style, "updates": updates,
                  "trained_hours": round(trained / 3600, 3)}
        for key in ("kill_rate", "kill_vs_past", "survive_vs_past", "cop_return", "runner_return"):
            scores[key] = float(np.mean([row[key] for row in recent])) if recent else 0.0
        with open(os.path.join(args.out, "scores.json"), "w") as handle:
            json.dump(scores, handle, indent=1)
        write_summary(args, history, final, league)

    def snapshot():
        for role in ROLES:
            name = f"{role}_line{args.line}_u{updates}"
            data = learners[role].snapshot_data(name)
            torch.save(data, os.path.join(args.out, "league", name + ".pt"))
            league.add(Snapshot(data))
        own = sorted(glob.glob(os.path.join(args.out, "league", "*.pt")), key=os.path.getmtime)
        for path in own[:-24]:
            os.remove(path)

    try:
        while time.time() - started < budget:
            update_start = time.time()
            stats_sum = np.zeros(env.stats_dim)
            fade = max(0.0, 1.0 - learners["cop"].steps / max(args.approach_fade_steps, 1.0))
            weights = {role: learners[role].weights.copy() for role in ROLES}
            weights["cop"][APPROACH_PART] *= fade
            for t in range(T):
                actions = np.zeros((S, A), np.float32)
                active = flags[:, 1] > 0.5
                for role in ROLES:
                    learner, b, idx = learners[role], bufs[role], slots[role]
                    o_raw = raw_obs[idx, :dims[role]]
                    ctrl = controller_of(role)
                    valid = active[idx] & (ctrl == League.CURRENT)
                    o_n = torch.from_numpy(learner.obs_rms.normalize(o_raw))
                    p_n = torch.from_numpy(learner.priv_rms.normalize(raw_priv[idx]))
                    with torch.no_grad():
                        dist = learner.actor.dist(o_n)
                        act = dist.sample()
                        b["logp"][t] = dist.log_prob(act).sum(1)
                        b["val"][t] = learner.critic(learner.value_input(o_n, p_n))
                    act_np = act.numpy()
                    for snap_index in np.unique(ctrl[active[idx] & (ctrl != League.CURRENT)]):
                        rows = np.nonzero(active[idx] & (ctrl == snap_index))[0]
                        act_np[rows] = league.by_uid[snap_index].act(o_raw[rows])
                    b["obs"][t], b["priv"][t], b["act"][t] = o_n, p_n, act
                    b["valid"][t] = torch.from_numpy(valid.astype(np.float32))
                    actions[idx] = np.clip(act_np, -1.0, 1.0)
                next_obs, next_priv, parts, next_flags, stats = env.step(actions)
                stats_sum += stats
                done_all = next_flags[:, 0] > 0.5
                trunc_all = next_flags[:, 2] > 0.5
                for role in ROLES:
                    learner, b, idx = learners[role], bufs[role], slots[role]
                    valid = b["valid"][t].numpy() > 0.5
                    reward = parts[idx].astype(np.float64) @ weights[role]
                    done = done_all[idx]
                    episode_return[role][valid] += reward[valid]
                    discounted[role] = np.where(valid, discounted[role] * gamma + reward, discounted[role])
                    learner.ret_rms.update(discounted[role][valid])
                    scaled = reward / np.sqrt(learner.ret_rms.var + 1e-8)
                    bootstrap = valid & trunc_all[idx]
                    scaled[bootstrap] += gamma * b["val"][t].numpy()[bootstrap]
                    b["rew"][t] = torch.from_numpy((scaled * valid).astype(np.float32))
                    b["done"][t] = torch.from_numpy(done.astype(np.float32))
                    for k in np.nonzero(done)[0]:
                        if valid[k]:
                            finished[role].append(episode_return[role][k])
                        episode_return[role][k] = 0.0
                        discounted[role][k] = 0.0
                    new_active = next_flags[idx, 1] > 0.5
                    learner.obs_rms.update(next_obs[idx][new_active, :dims[role]].astype(np.float64))
                    learner.priv_rms.update(next_priv[idx][new_active].astype(np.float64))
                for slot in slots["runner"][done_all[slots["runner"]]]:
                    m = env.match_of[slot]
                    wrecked, survived = parts[slot, 2] > 0.5, parts[slot, 7] > 0.5
                    if wrecked or survived:
                        runner_ctrl, cop_ctrl = controllers[m]
                        if runner_ctrl == League.CURRENT and cop_ctrl == League.CURRENT:
                            outcomes["current"].append(float(wrecked))
                        elif runner_ctrl != League.CURRENT:
                            outcomes["vs_past_runner"].append(float(wrecked))
                            league.record(runner_ctrl, wrecked)
                        else:
                            outcomes["vs_past_cops"].append(float(survived))
                            league.record(cop_ctrl, survived)
                    controllers[m] = league.pick()
                raw_obs, raw_priv, flags = next_obs, next_priv, next_flags

            # Advantages (GAE), skipping slots that were idle or played by a past version.
            active = flags[:, 1] > 0.5
            for role in ROLES:
                learner, b, idx = learners[role], bufs[role], slots[role]
                valid_last = torch.from_numpy((active[idx] & (controller_of(role) == League.CURRENT)).astype(np.float32))
                with torch.no_grad():
                    o_n = torch.from_numpy(learner.obs_rms.normalize(raw_obs[idx, :dims[role]]))
                    p_n = torch.from_numpy(learner.priv_rms.normalize(raw_priv[idx]))
                    last_value = learner.critic(learner.value_input(o_n, p_n))
                adv = torch.zeros_like(b["rew"])
                running = torch.zeros(len(idx))
                for t in reversed(range(T)):
                    next_value, next_valid = (last_value, valid_last) if t == T - 1 else (b["val"][t + 1], b["valid"][t + 1])
                    nonterminal = (1.0 - b["done"][t]) * next_valid
                    delta = b["rew"][t] + gamma * next_value * nonterminal - b["val"][t]
                    running = (delta + gamma * lam * nonterminal * running) * b["valid"][t]
                    adv[t] = running
                b["adv"] = adv
                b["ret"] = adv + b["val"]

            for role in ROLES:
                train_side(learners[role], bufs[role], args, train_actor=warmup_left <= 0)
            warmup_left -= 1
            updates += 1

            samples = {role: int(bufs[role]["valid"].sum().item()) for role in ROLES}
            for role in ROLES:
                learners[role].steps += samples[role]
            s = stats_sum
            runner_min = max(s[10] * 0.1 / 60, 1e-6)
            cop_min = max(s[11] * 0.1 / 60, 1e-6)

            def rate(name):
                return round(float(np.mean(outcomes[name])), 3) if outcomes[name] else 0.0

            row = {"hours": round((prior_seconds + time.time() - started) / 3600, 3), "updates": updates,
                   "cop_steps": learners["cop"].steps, "runner_steps": learners["runner"].steps,
                   "sps": round((s[10] + s[11]) / (time.time() - update_start)),
                   "kill_rate": rate("current"), "kill_vs_past": rate("vs_past_runner"),
                   "survive_vs_past": rate("vs_past_cops"),
                   "match_s": round(s[13] / max(s[0], 1), 1), "runner_kmh": round(s[9] / max(s[10], 1) * 3.6, 1),
                   "runner_dmg_cops_min": round(s[4] / runner_min, 2), "runner_dmg_walls_min": round(s[5] / runner_min, 2),
                   "cop_kmh": round(s[14] / max(s[11], 1) * 3.6, 1), "cop_wall_dmg_min": round(s[6] / cop_min, 2),
                   "cop_wrecks_min": round(s[7] / cop_min, 3), "cop_on_cop_min": round(s[8] / cop_min, 2),
                   "cops_per_chase": round(s[11] / max(s[10], 1), 2), "known_pct": round(s[12] / max(s[10], 1) * 100, 1),
                   "cop_return": round(float(np.mean(finished["cop"])), 3) if finished["cop"] else 0.0,
                   "runner_return": round(float(np.mean(finished["runner"])), 3) if finished["runner"] else 0.0,
                   "approach_hint": round(fade, 3)}
            writer.writerow([row[c] for c in columns])
            csv_file.flush()
            history.append(row)
            print(" ".join(f"{k}={v}" for k, v in row.items()), flush=True)
            if time.time() - last_snapshot > args.snapshot_minutes * 60:
                snapshot()
                league.forget_unused([uid for pair in controllers for uid in pair])
                last_snapshot = time.time()
            if time.time() - last_save > args.save_minutes * 60:
                save()
                last_save = time.time()
    finally:
        if updates > 0:
            snapshot()
        save(final=True)
        csv_file.close()
        env.close()


def train_side(learner, b, args, train_actor=True):
    mask = b["valid"].reshape(-1) > 0.5
    count = int(mask.sum().item())
    if count < 64:
        return
    d, p, a = learner.obs_dim, learner.priv_dim, learner.act_dim
    obs, priv = b["obs"].reshape(-1, d)[mask], b["priv"].reshape(-1, p)[mask]
    act, logp_old = b["act"].reshape(-1, a)[mask], b["logp"].reshape(-1)[mask]
    adv_all, ret, val_old = b["adv"].reshape(-1)[mask], b["ret"].reshape(-1)[mask], b["val"].reshape(-1)[mask]
    value_in = learner.value_input(obs, priv)
    pieces = max(1, min(args.minibatches, count // 64))
    for _ in range(args.epochs):
        for idx in torch.randperm(count).tensor_split(pieces):
            new_value = learner.critic(value_in[idx])
            clipped = val_old[idx] + (new_value - val_old[idx]).clamp(-args.clip, args.clip)
            v_loss = 0.5 * torch.max((new_value - ret[idx]) ** 2, (clipped - ret[idx]) ** 2).mean()
            loss = args.vf * v_loss
            if train_actor:
                dist = learner.actor.dist(obs[idx])
                ratio = (dist.log_prob(act[idx]).sum(1) - logp_old[idx]).exp()
                adv = adv_all[idx]
                adv = (adv - adv.mean()) / (adv.std() + 1e-8)
                pg_loss = torch.max(-adv * ratio, -adv * ratio.clamp(1 - args.clip, 1 + args.clip)).mean()
                loss = loss + pg_loss - args.ent * dist.entropy().sum(1).mean()
            learner.optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(list(learner.actor.parameters()) + list(learner.critic.parameters()), args.max_grad)
            learner.optimizer.step()


def write_summary(args, history, final, league):
    lines = [f"# Chase training (cops vs runner), line {args.line}, {args.runner_style} runner", ""]
    if not history:
        lines.append("No updates finished yet.")
    else:
        first, last = history[0], history[-1]
        lines += [
            f"{'Finished' if final else 'In progress'}: {last['hours']} h of training in total, "
            f"{last['cop_steps']:,} cop decisions and {last['runner_steps']:,} runner decisions learned from.",
            "",
            "| | first update | latest |",
            "|---|---|---|",
            f"| Cops wreck the runner (current vs current) | {first['kill_rate']} | {last['kill_rate']} |",
            f"| Cops wreck past runners | {first['kill_vs_past']} | {last['kill_vs_past']} |",
            f"| Runner survives past cops | {first['survive_vs_past']} | {last['survive_vs_past']} |",
            f"| Average chase length (s, max 120) | {first['match_s']} | {last['match_s']} |",
            f"| Runner speed (km/h) | {first['runner_kmh']} | {last['runner_kmh']} |",
            f"| Runner damage from cops per minute | {first['runner_dmg_cops_min']} | {last['runner_dmg_cops_min']} |",
            f"| Runner damage from walls per minute | {first['runner_dmg_walls_min']} | {last['runner_dmg_walls_min']} |",
            f"| Cop speed (km/h) | {first['cop_kmh']} | {last['cop_kmh']} |",
            f"| Cop wall damage per cop-minute | {first['cop_wall_dmg_min']} | {last['cop_wall_dmg_min']} |",
            f"| Cop wrecks per cop-minute | {first['cop_wrecks_min']} | {last['cop_wrecks_min']} |",
            f"| Cop-on-cop damage per cop-minute | {first['cop_on_cop_min']} | {last['cop_on_cop_min']} |",
            f"| Cops in a chase (average) | {first['cops_per_chase']} | {last['cops_per_chase']} |",
            f"| Cops know where the runner is (%) | {first['known_pct']} | {last['known_pct']} |",
            f"| Decisions per second | {first['sps']} | {last['sps']} |",
            "",
            f"Past versions in the league: {len(league.pool['cop'])} cop, {len(league.pool['runner'])} runner.",
            "",
            "Every 10th update:",
            "",
            "| hours | cops wreck runner | vs past runners | runner survives past cops | chase s | runner dmg/min | cop wall dmg/min |",
            "|---|---|---|---|---|---|---|"]
        for row in history[::10] + ([history[-1]] if len(history) % 10 != 1 else []):
            lines.append(f"| {row['hours']} | {row['kill_rate']} | {row['kill_vs_past']} | {row['survive_vs_past']} | "
                         f"{row['match_s']} | {row['runner_dmg_cops_min']} | {row['cop_wall_dmg_min']} |")
    with open(os.path.join(args.out, "summary.md"), "w") as handle:
        handle.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
