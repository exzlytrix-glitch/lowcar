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
from torch.distributions import Bernoulli, Categorical, Normal

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
# Brain outputs per side, in the order the game reads them (scripts/ai/chase_agent.gd):
# smooth controls (gauss), on/off (bern) and pick-one (cat). The last pick is the navigation choice,
# which only counts on decisions where the car is choosing (flag 3 from the arena).
HEADS = {
    "cop": [("gauss", 2), ("bern", 2), ("cat", 5)],               # steer, throttle | handbrake, burst | route
    "runner": [("gauss", 2), ("bern", 1), ("cat", 5), ("cat", 5)],  # steer, throttle | handbrake | boost | route
}
ACTION_NAMES = {"cop": ["steer", "throttle", "handbrake", "burst", "route"],
                "runner": ["steer", "throttle", "handbrake", "boost", "route"]}
COP_ROUTES = ["chase", "ahead", "far", "left", "right"]
RUNNER_ROUTES = ["gps", "straight", "left", "right", "back"]
# Starting odds for new outputs: route option 0 (chase / GPS) about 75% of the time, the rest explored
# (and boost "none" likewise), so carried-over brains keep driving well while they try the new choices.
ROUTE_PRIOR = 2.5


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
    p.add_argument("--minibatches", type=int, default=4)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--gae-lambda", type=float, default=0.95)
    p.add_argument("--clip", type=float, default=0.2)
    p.add_argument("--ent", type=float, default=0.0, help="exploration bonus for steering and throttle")
    p.add_argument("--ent-discrete", type=float, default=0.005,
                   help="exploration bonus for on/off and pick outputs (route, boost, burst, handbrake), so the "
                        "route choice does not collapse to 'chase directly' before cut-offs are discovered")
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
    p.add_argument("--genome", default="", help="this line's settings (genome.json from the last merge); "
                                                 "missing = the line's starting settings")
    p.add_argument("--exam-dir", default="", help="fixed opponents for the end-of-run exam (from the last merge)")
    p.add_argument("--exam-minutes", type=float, default=0.0, help="minutes at the end spent on the exam")
    p.add_argument("--route-prior", type=float, default=ROUTE_PRIOR,
                   help="starting preference for route option 0 and no boost in new or carried-over brains")
    p.add_argument("--export-only", action="store_true",
                   help="just write the game brains from --resume (carried over to the current format) and stop")
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
    """The in-game brain: observations in, one value per output head out (see HEADS)."""

    def __init__(self, obs_dim, heads, hidden):
        super().__init__()
        self.heads = [tuple(h) for h in heads]
        self.n_gauss = sum(size for kind, size in self.heads if kind == "gauss")
        width = sum(size for _, size in self.heads)
        self.net = nn.Sequential(
            layer_init(nn.Linear(obs_dim, hidden)), nn.Tanh(),
            layer_init(nn.Linear(hidden, hidden)), nn.Tanh(),
            layer_init(nn.Linear(hidden, width), std=0.01))
        self.logstd = nn.Parameter(torch.full((1, self.n_gauss), -0.5))
        self.last_cat = max(i for i, (kind, _) in enumerate(self.heads) if kind == "cat")
        with torch.no_grad():
            at = 0
            for i, (kind, size) in enumerate(self.heads):
                if kind == "bern":
                    self.net[4].bias[at:at + size] = -1.5  # handbrake / burst start mostly off
                elif kind == "cat":
                    self.net[4].bias[at] = ROUTE_PRIOR  # boost "none" / route option 0 start most likely
                at += size

    def evaluate(self, x, actions=None, nav_mask=None):
        """Samples actions (actions=None) or scores given ones. Returns (actions in game order, log-prob,
        (smooth entropy, on/off + pick entropy)); the navigation pick only counts where nav_mask is 1."""
        raw = self.net(x)
        outs, logp, smooth, discrete = [], 0.0, 0.0, 0.0
        at, col = 0, 0
        for i, (kind, size) in enumerate(self.heads):
            part = raw[:, at:at + size]
            at += size
            if kind == "gauss":
                dist = Normal(part, torch.exp(self.logstd.expand_as(part)))
                act = dist.sample() if actions is None else actions[:, col:col + size]
                lp, ent = dist.log_prob(act).sum(1), dist.entropy().sum(1)
                col += size
            elif kind == "bern":
                dist = Bernoulli(logits=part)
                act = dist.sample() if actions is None else actions[:, col:col + size]
                lp, ent = dist.log_prob(act).sum(1), dist.entropy().sum(1)
                col += size
            else:
                dist = Categorical(logits=part)
                pick = dist.sample() if actions is None else actions[:, col].long()
                lp, ent = dist.log_prob(pick), dist.entropy()
                act = pick.float().unsqueeze(1)
                col += 1
                if i == self.last_cat and nav_mask is not None:
                    lp, ent = lp * nav_mask, ent * nav_mask
            outs.append(act)
            logp = logp + lp
            if kind == "gauss":
                smooth = smooth + ent
            else:
                discrete = discrete + ent
        return torch.cat(outs, 1), logp, (smooth, discrete)


def to_game(actions, n_gauss):
    """Smooth controls are clipped to -1..1; on/off and picks go as they are."""
    out = np.array(actions, np.float32)
    out[:, :n_gauss] = np.clip(out[:, :n_gauss], -1.0, 1.0)
    return out


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


# Per-line settings ("genome") that population-based training tunes: the merge copies strong lines over
# weak ones and nudges these by x0.8 / x1.2 (DeepMind's Capture the Flag and soccer agents did the same).
# Per side: learning rate, gamma (how far ahead it plans: 0.99 is ~10 s at 10 decisions/s, 0.995 ~20 s),
# exploration bonus for on/off and pick outputs. Shared: decisions per slot per update (batch size).
DEFAULT_SIDE = {"lr": 2.5e-4, "gamma": 0.995, "ent_discrete": 0.005}
DEFAULT_STEPS = 768


def initial_genome(line):
    """Line 0 gets the recommended defaults, other lines a spread around them."""
    if str(line) == "0" or not str(line).isdigit():
        return {"cop": dict(DEFAULT_SIDE), "runner": dict(DEFAULT_SIDE), "steps": DEFAULT_STEPS}
    pick = np.random.default_rng(1000 + int(line))

    def side():
        return {"lr": float(2.5e-4 * pick.choice([0.6, 0.8, 1.0, 1.25])),
                "gamma": float(pick.choice([0.99, 0.993, 0.995, 0.997])),
                "ent_discrete": float(0.005 * pick.choice([0.6, 1.0, 1.5]))}

    return {"cop": side(), "runner": side(), "steps": int(pick.choice([512, 768, 1024]))}


class ValueNorm:
    """Running mean and spread of the critic's targets; the critic predicts normalised values. When the
    statistics move, the critic's last layer is rescaled so its predictions stay the same (PopArt), so
    reward scales that drift (the closing-in hint fading out) do not upset it."""

    def __init__(self):
        self.mean, self.var, self.count = 0.0, 1.0, 1e-4

    def std(self):
        return float(np.sqrt(self.var + 1e-8))

    def update(self, targets, layer):
        x = np.asarray(targets, np.float64)
        if len(x) == 0:
            return
        old_mean, old_std = self.mean, self.std()
        batch_mean, batch_var, batch_count = x.mean(), x.var(), len(x)
        delta = batch_mean - self.mean
        total = self.count + batch_count
        self.mean += delta * batch_count / total
        self.var = (self.var * self.count + batch_var * batch_count + delta ** 2 * self.count * batch_count / total) / total
        self.count = total
        new_std = self.std()
        with torch.no_grad():
            layer.weight.mul_(old_std / new_std)
            layer.bias.mul_(old_std).add_(old_mean - self.mean).div_(new_std)

    def denorm(self, value):
        return value * self.std() + self.mean

    def norm(self, value):
        return (value - self.mean) / self.std()

    def state(self):
        return {"mean": self.mean, "var": self.var, "count": self.count}

    def load(self, state):
        self.mean, self.var, self.count = state["mean"], state["var"], state["count"]


class Learner:
    """Everything one side learns with: actor, critic, optimiser and the input/return scaling."""

    def __init__(self, role, obs_dim, priv_dim, act_dim, args):
        self.role, self.obs_dim, self.priv_dim, self.act_dim = role, obs_dim, priv_dim, act_dim
        self.actor = Actor(obs_dim, HEADS[role], args.actor_hidden)
        self.critic = Critic(obs_dim + priv_dim, args.critic_hidden)
        self.optimizer = torch.optim.Adam(list(self.actor.parameters()) + list(self.critic.parameters()),
                                          lr=args.lr, eps=1e-5)
        self.obs_rms, self.priv_rms, self.ret_rms = RunningMeanStd((obs_dim,)), RunningMeanStd((priv_dim,)), RunningMeanStd(())
        self.value_norm = ValueNorm()
        self.gamma, self.ent_discrete = args.gamma, args.ent_discrete
        self.weights = np.array(WEIGHTS[role], np.float64)
        if role == "runner":
            for part, weight in RUNNER_STYLES[args.runner_style].items():
                self.weights[part] = weight
        self.steps = 0

    def value_input(self, obs_n, priv_n):
        return torch.cat([obs_n, priv_n], dim=-1)

    def value(self, obs_n, priv_n):
        return self.value_norm.denorm(self.critic(self.value_input(obs_n, priv_n)))

    def use_genome(self, side):
        for group in self.optimizer.param_groups:
            group["lr"] = side["lr"]
        self.gamma, self.ent_discrete = side["gamma"], side["ent_discrete"]

    def state(self):
        return {"actor": self.actor.state_dict(), "critic": self.critic.state_dict(),
                "optimizer": self.optimizer.state_dict(), "obs_rms": self.obs_rms.state(),
                "priv_rms": self.priv_rms.state(), "ret_rms": self.ret_rms.state(), "steps": self.steps,
                "value_norm": self.value_norm.state()}

    def load(self, state):
        """Loads a checkpoint; one from before the current senses/outputs is carried over (upgrade())."""
        old_obs = state["actor"]["net.0.weight"].shape[1]
        if old_obs == self.obs_dim and "logstd" in state["actor"] and \
                state["actor"]["net.4.weight"].shape[0] == self.actor.net[4].out_features:
            self.actor.load_state_dict(state["actor"])
            self.critic.load_state_dict(state["critic"])
            self.optimizer.load_state_dict(state["optimizer"])
            self.obs_rms.load(state["obs_rms"])
        else:
            transplant(self.actor, state["actor"], self.role)
            critic = state["critic"]
            with torch.no_grad():
                for key, value in critic.items():
                    target = dict(self.critic.named_parameters())[key]
                    if key == "net.0.weight":
                        target.zero_()
                        target[:, :old_obs] = value[:, :old_obs]
                        target[:, self.obs_dim:] = value[:, old_obs:]
                    else:
                        target.copy_(value)
            self.obs_rms.load(state["obs_rms"])
            self.obs_rms.mean = np.concatenate([self.obs_rms.mean, np.zeros(self.obs_dim - old_obs)])
            self.obs_rms.var = np.concatenate([self.obs_rms.var, np.ones(self.obs_dim - old_obs)])
            print(f"{self.role}: carried over a brain with {old_obs} senses into {self.obs_dim} senses and new outputs")
        self.priv_rms.load(state["priv_rms"])
        self.ret_rms.load(state["ret_rms"])
        self.steps = state["steps"]
        if "value_norm" in state:
            self.value_norm.load(state["value_norm"])

    def snapshot_data(self, name):
        return {"role": self.role, "name": name, "obs_dim": self.obs_dim, "act_dim": self.act_dim,
                "heads": HEADS[self.role],
                "hidden": self.actor.net[0].out_features, "actor": copy.deepcopy(self.actor.state_dict()),
                "obs_mean": self.obs_rms.mean.copy(), "obs_var": self.obs_rms.var.copy(), "steps": self.steps}


class Snapshot:
    """A frozen past version of one side, used as an opponent."""

    def __init__(self, data, obs_dim, imported=False):
        self.role, self.name, self.imported = data["role"], data["name"], imported
        self.actor = Actor(obs_dim, HEADS[self.role], data["hidden"])
        mean, var = np.asarray(data["obs_mean"]), np.asarray(data["obs_var"])
        heads = [tuple(h) for h in data.get("heads", [])]
        if data["obs_dim"] == obs_dim and heads == list(HEADS[self.role]):
            self.actor.load_state_dict(data["actor"])
        else:
            transplant(self.actor, data["actor"], self.role)
            mean = np.concatenate([mean, np.zeros(obs_dim - len(mean))])
            var = np.concatenate([var, np.ones(obs_dim - len(var))])
        self.actor.eval()
        self.rms = RunningMeanStd((obs_dim,))
        self.rms.mean, self.rms.var = mean, var
        self.data = data
        self.uid = -1
        self.learner_win = 0.5  # how often the current learner beats this version (moving average)
        self.games = 0

    @torch.no_grad()
    def act(self, raw_obs):
        return self.actor.evaluate(torch.from_numpy(self.rms.normalize(raw_obs)))[0].numpy()


def transplant(actor, old, role):
    """Carries an older brain into the current shape so nothing it learned is lost: its senses keep their
    weights (new senses start at zero influence), wider layers get new units that start silent, its
    steering and throttle carry over, its old "above zero means on" outputs become on/off odds that
    match (a Gaussian with mean m and spread s is on with odds about sigmoid(1.7 m / s)), and new
    choices start at their default (no boost, route option 0 about half the time).
    `old` is an actor state dict (keys net.0.weight ... logstd) or a list of (w, b) layers."""
    if isinstance(old, dict):
        layers = [(old[f"net.{k}.weight"].detach().numpy(), old[f"net.{k}.bias"].detach().numpy()) for k in (0, 2, 4)]
        logstd = old["logstd"].detach().numpy().reshape(-1) if "logstd" in old else None
    else:
        layers, logstd = old, None
    (w0, b0), (w1, b1), (w2, b2) = layers
    hidden, old_in = w0.shape
    spread = np.exp(logstd) if logstd is not None else np.full(w2.shape[0], 0.6)
    net = actor.net
    with torch.no_grad():
        net[0].weight[hidden:, :].mul_(0.5)
        net[0].weight[:hidden, :] = 0.0
        net[0].weight[:hidden, :old_in] = torch.from_numpy(w0)
        net[0].bias[:hidden] = torch.from_numpy(b0)
        net[2].weight[hidden:, :].mul_(0.5)
        net[2].weight[:hidden, :] = 0.0
        net[2].weight[:hidden, :hidden] = torch.from_numpy(w1)
        net[2].bias[:hidden] = torch.from_numpy(b1)
        weight, bias = net[4].weight, net[4].bias
        if w2.shape[0] == weight.shape[0]:
            # Already has today's outputs (only the senses grew): copy them as they are.
            weight.zero_()
            weight[:, :hidden] = torch.from_numpy(w2)
            bias.copy_(torch.from_numpy(b2))
            if logstd is not None:
                actor.logstd[0, :] = torch.from_numpy(logstd[:actor.logstd.shape[1]])
            return
        weight.zero_()
        bias.zero_()

        def put(row, source, scale=1.0, shift=0.0):
            weight[row, :hidden] = torch.from_numpy(w2[source] * scale)
            bias[row] = float(b2[source] * scale + shift)

        put(0, 0)
        put(1, 1)
        put(2, 2, 1.7 / spread[2])
        has_special = w2.shape[0] > 3
        if role == "cop":
            if has_special:
                put(3, 3, 1.7 / spread[3])
            else:
                bias[3] = -1.5
            bias[4] = ROUTE_PRIOR
        else:
            bias[3] = ROUTE_PRIOR
            for row in range(4, 8):
                if has_special:
                    put(row, 3, 1.7 / spread[3], -np.log(4.0))
                else:
                    bias[row] = -1.5
            bias[8] = ROUTE_PRIOR
        actor.logstd[0, :] = torch.from_numpy(logstd[:2]) if logstd is not None else -1.0


def warm_start(learner, path):
    """Starts a side from the driving-school brain (cop_brain.json or its checkpoint.pt)."""
    if path.endswith(".json"):
        with open(path) as handle:
            data = json.load(handle)
        layers = [(np.array(l["w"], np.float32), np.array(l["b"], np.float32)) for l in data["layers"]]
        mean, var = np.array(data["obs_mean"]), np.array(data["obs_std"]) ** 2
    else:
        state = torch.load(path, weights_only=False)
        brain = state["brain"]
        layers = [(brain[f"actor_mean.{k}.weight"].numpy(), brain[f"actor_mean.{k}.bias"].numpy()) for k in (0, 2, 4)]
        mean, var = np.array(state["obs_rms"]["mean"]), np.array(state["obs_rms"]["var"])
    transplant(learner.actor, layers, learner.role)
    old_in = layers[0][0].shape[1]
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
                 "obs_clip": 10.0, "layers": layers, "action_names": ACTION_NAMES[learner.role],
                 "heads": [{"kind": kind, "size": size} for kind, size in HEADS[learner.role]]})
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
    global ROUTE_PRIOR
    args = parse_args()
    ROUTE_PRIOR = args.route_prior
    budget = args.hours * 3600 + args.minutes * 60
    if budget <= 0 and not args.export_only:
        raise SystemExit("give --hours or --minutes")
    os.makedirs(os.path.join(args.out, "league"), exist_ok=True)
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    started = time.time()
    if args.export_only:
        export_only(args)
        return

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
            if data["obs_dim"] <= dims[data["role"]]:
                league.add(Snapshot(data, dims[data["role"]],
                                    imported=not path.startswith(os.path.join(args.out, "league"))))
    print(f"league: {len(league.pool['cop'])} past cop versions, {len(league.pool['runner'])} past runners")
    genome = initial_genome(args.line)
    if args.genome and os.path.exists(args.genome):
        with open(args.genome) as handle:
            genome = json.load(handle)
    for role in ROLES:
        learners[role].use_genome(genome[role])
    with open(os.path.join(args.out, "genome.json"), "w") as handle:
        json.dump(genome, handle, indent=1)
    print(f"settings: {json.dumps(genome)}")
    exam_panel = load_exam_panel(args, dims, league)

    T, lam = int(genome.get("steps", args.steps)), args.gae_lambda
    bufs = {}
    for role in ROLES:
        n, d = len(slots[role]), dims[role]
        bufs[role] = {"obs": torch.zeros((T, n, d)), "priv": torch.zeros((T, n, env.priv_dim)),
                      "act": torch.zeros((T, n, A)), "nav": torch.zeros((T, n)), "gone": torch.zeros((T, n)),
                      "logp": torch.zeros((T, n)), "val": torch.zeros((T, n)),
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
               "approach_hint", "cop_bursts_min", "burst_hits", "runner_boosts_min", "runner_charging_pct",
               "boost_rams", "cop_drift_pct", "runner_drift_pct", "cop_handbrake_pct", "runner_handbrake_pct",
               "cop_reverse_pct"] + [f"cop_route_{name}" for name in COP_ROUTES] + \
              [f"runner_route_{name}" for name in RUNNER_ROUTES]
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as handle:
            old_rows = list(csv.DictReader(handle))
        if old_rows and list(old_rows[0].keys()) != columns:
            with open(csv_path, "w", newline="") as handle:  # an older line's log: rewrite with the new columns
                rewriter = csv.DictWriter(handle, columns, extrasaction="ignore")
                rewriter.writeheader()
                rewriter.writerows(old_rows)
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
        if exam:
            scores["exam_cop"], scores["exam_runner"] = exam["cop_score"], exam["runner_score"]
        with open(os.path.join(args.out, "scores.json"), "w") as handle:
            json.dump(scores, handle, indent=1)
        write_summary(args, history, final, league)

    def snapshot():
        for role in ROLES:
            name = f"{role}_line{args.line}_u{updates}"
            data = learners[role].snapshot_data(name)
            torch.save(data, os.path.join(args.out, "league", name + ".pt"))
            league.add(Snapshot(data, dims[role]))
        own = sorted(glob.glob(os.path.join(args.out, "league", "*.pt")), key=os.path.getmtime)
        for path in own[:-24]:
            os.remove(path)

    exam_seconds = args.exam_minutes * 60 if exam_panel else 0.0
    exam = None
    try:
        while time.time() - started < budget - exam_seconds:
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
                    nav = torch.from_numpy(flags[idx, 3].astype(np.float32))
                    with torch.no_grad():
                        act, logp, _ = learner.actor.evaluate(o_n, None, nav)
                        b["logp"][t] = logp
                        b["val"][t] = learner.value(o_n, p_n)
                    act_np = act.numpy().copy()
                    for snap_index in np.unique(ctrl[active[idx] & (ctrl != League.CURRENT)]):
                        rows = np.nonzero(active[idx] & (ctrl == snap_index))[0]
                        act_np[rows] = league.by_uid[snap_index].act(o_raw[rows])
                    b["obs"][t], b["priv"][t], b["act"][t], b["nav"][t] = o_n, p_n, act, nav
                    b["valid"][t] = torch.from_numpy(valid.astype(np.float32))
                    actions[idx] = to_game(act_np, learner.actor.n_gauss)
                next_obs, next_priv, parts, next_flags, stats = env.step(actions)
                stats_sum += stats
                done_all = next_flags[:, 0] > 0.5
                trunc_all = next_flags[:, 2] > 0.5
                for role in ROLES:
                    learner, b, idx = learners[role], bufs[role], slots[role]
                    gamma = learner.gamma
                    valid = b["valid"][t].numpy() > 0.5
                    reward = parts[idx].astype(np.float64) @ weights[role]
                    b["gone"][t] = torch.from_numpy((next_flags[idx, 4] > 0.5).astype(np.float32))
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
                gamma = learner.gamma
                with torch.no_grad():
                    o_n = torch.from_numpy(learner.obs_rms.normalize(raw_obs[idx, :dims[role]]))
                    p_n = torch.from_numpy(learner.priv_rms.normalize(raw_priv[idx]))
                    last_value = learner.value(o_n, p_n)
                if role == "cop":
                    share_team_future(b, match_of["cop"], last_value, valid_last, gamma)
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
                   "approach_hint": round(fade, 3),
                   "cop_bursts_min": round(s[16] / cop_min, 2), "burst_hits": int(s[24]),
                   "runner_boosts_min": round(s[17] / runner_min, 2),
                   "runner_charging_pct": round(s[18] / max(s[10], 1) * 100, 1), "boost_rams": int(s[25]),
                   "cop_drift_pct": round(s[19] / max(s[11], 1) * 100, 1),
                   "runner_drift_pct": round(s[20] / max(s[10], 1) * 100, 1),
                   "cop_handbrake_pct": round(s[21] / max(s[11], 1) * 100, 1),
                   "runner_handbrake_pct": round(s[22] / max(s[10], 1) * 100, 1),
                   "cop_reverse_pct": round(s[23] / max(s[11], 1) * 100, 1)}
            for role, names in (("cop", COP_ROUTES), ("runner", RUNNER_ROUTES)):
                b = bufs[role]
                chosen = (b["valid"] * b["nav"]).reshape(-1) > 0.5
                picks = b["act"].reshape(-1, A)[chosen][:, -1].long()
                counts = torch.bincount(picks, minlength=len(names)).float() if len(picks) else torch.zeros(len(names))
                for k, name in enumerate(names):
                    row[f"{role}_route_{name}"] = round(float(counts[k] / max(counts.sum(), 1.0)) * 100, 1)
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
        if exam_panel:
            save()
            exam = run_exam(env, learners, dims, slots, exam_panel, raw_obs, raw_priv, flags,
                            budget - (time.time() - started))
            with open(os.path.join(args.out, "exam.json"), "w") as handle:
                json.dump(exam, handle, indent=1)
            print(f"exam: cops {exam['cop_score']:.2f}, runner {exam['runner_score']:.2f}")
    finally:
        if updates > 0:
            snapshot()
        save(final=True)
        csv_file.close()
        env.close()


# Sizes the arena reports in its hello (scripts/ai/chase_senses.gd, chase_match.gd); only used by --export-only.
GAME_DIMS = {"cop": 176, "runner": 165}
GAME_PRIV, GAME_ACT = 12, 5


def export_only(args):
    state = torch.load(args.resume, weights_only=False)
    for role in ROLES:
        learner = Learner(role, GAME_DIMS[role], GAME_PRIV, GAME_ACT, args)
        learner.load(state["learners"][role])
        export_brain(os.path.join(args.out, f"{role}_brain.json"), learner,
                     {"line": args.line, "trained_hours": round(state.get("trained_seconds", 0.0) / 3600, 3)})
    print(f"wrote cop_brain.json and runner_brain.json to {args.out}")


SCRIPTED = "scripted"


def load_exam_panel(args, dims, league):
    """The fixed opponents every line is examined against this round: the scripted autopilot (never
    changes, so it shows progress across rounds) plus the past versions the last merge chose (or, before
    any merge made a panel, the newest imported league versions, which every line shares)."""
    if args.exam_minutes <= 0:
        return None
    panel = {"cop": [(SCRIPTED, None)], "runner": [(SCRIPTED, None)]}
    files = sorted(glob.glob(os.path.join(args.exam_dir, "*.pt"))) if args.exam_dir else []
    if files:
        for path in files:
            data = torch.load(path, weights_only=False)
            if data["obs_dim"] <= dims[data["role"]]:
                name = os.path.splitext(os.path.basename(path))[0]
                panel[data["role"]].append((name, Snapshot(data, dims[data["role"]], imported=True)))
    else:
        for role in ROLES:
            imported = [s for s in league.pool[role] if s.imported]
            for snap in imported[-2:]:
                panel[role].append((snap.name, snap))
    print("exam panel: " + "; ".join(f"{role}: " + ", ".join(n for n, _ in panel[role]) for role in ROLES))
    return panel


def run_exam(env, learners, dims, slots, panel, raw_obs, raw_priv, flags, seconds):
    """Plays this line's current cops against every runner on the panel and its current runner against
    every cop on the panel, spreading chases evenly, for `seconds`. Brains act as in the game (sampled).
    Chases already running when the exam starts are not counted."""
    tests = [("cop", name, opp) for name, opp in panel["runner"]] + [("runner", name, opp) for name, opp in panel["cop"]]
    wins, games, pending = np.zeros(len(tests)), np.zeros(len(tests)), np.zeros(len(tests))
    assign = [-1] * env.num_matches
    started = time.time()
    while time.time() - started < seconds:
        actions = np.zeros((env.num_slots, env.act_dim), np.float32)
        active = flags[:, 1] > 0.5
        for role in ROLES:
            idx = slots[role]
            o_raw = raw_obs[idx, :dims[role]]
            learner = learners[role]
            with torch.no_grad():
                mine = learner.actor.evaluate(torch.from_numpy(learner.obs_rms.normalize(o_raw)))[0].numpy()
            out = mine.copy()
            for row, slot in enumerate(idx):
                test = assign[env.match_of[slot]]
                if test < 0 or tests[test][0] == role or not active[slot]:
                    continue
                opponent = tests[test][2]
                if opponent is None:
                    out[row] = 0.0
                    out[row, -1] = -1.0  # the arena drives this slot with its scripted autopilot
                else:
                    out[row] = opponent.act(o_raw[row:row + 1])[0]
            actions[idx] = to_game(out, learner.actor.n_gauss)
        raw_obs, raw_priv, parts, next_flags, _ = env.step(actions)
        for slot in slots["runner"][next_flags[slots["runner"], 0] > 0.5]:
            m = env.match_of[slot]
            test = assign[m]
            wrecked, survived = parts[slot, 2] > 0.5, parts[slot, 7] > 0.5
            if test >= 0:
                pending[test] -= 1
                if wrecked or survived:
                    games[test] += 1
                    wins[test] += float(wrecked if tests[test][0] == "cop" else survived)
            choice = int(np.argmin(games + pending))
            assign[m] = choice
            pending[choice] += 1
        flags = next_flags
    result = {"cop": {}, "runner": {}, "minutes": round((time.time() - started) / 60, 1)}
    for k, (role, name, _) in enumerate(tests):
        result[role][name] = {"wins": int(wins[k]), "games": int(games[k])}
    for role in ROLES:
        rates = [v["wins"] / v["games"] for v in result[role].values() if v["games"] > 0]
        result[f"{role}_score"] = float(np.mean(rates)) if rates else 0.0
        scripted = result[role].get(SCRIPTED, {"wins": 0, "games": 0})
        result[f"{role}_vs_scripted"] = scripted["wins"] / scripted["games"] if scripted["games"] else 0.0
    return result


def share_team_future(b, match_of_slot, last_value, valid_last, gamma):
    """A cop that wrecks (say, blocking the runner) leaves before the chase is decided, so on its own it
    never sees the team's later result. Give its last step the team's expected future instead of nothing:
    gamma times the average value of its teammates still in that chase one step later (the
    "posthumous credit" problem from Unity's MA-POCA). Its own wreck penalty still applies."""
    T = b["rew"].shape[0]
    matches = int(match_of_slot.max()) + 1
    for t in range(T):
        gone = (b["gone"][t] * b["valid"][t]).numpy() > 0.5
        if not gone.any():
            continue
        values = (last_value if t == T - 1 else b["val"][t + 1]).numpy()
        alive = (valid_last if t == T - 1 else b["valid"][t + 1]).numpy() > 0.5
        alive = alive & ~gone
        totals = np.bincount(match_of_slot, weights=values * alive, minlength=matches)
        counts = np.bincount(match_of_slot, weights=alive.astype(np.float64), minlength=matches)
        team = np.where(counts > 0, totals / np.maximum(counts, 1), 0.0)
        bonus = np.where(gone, gamma * team[match_of_slot], 0.0)
        b["rew"][t] += torch.from_numpy(bonus.astype(np.float32))


def train_side(learner, b, args, train_actor=True):
    mask = b["valid"].reshape(-1) > 0.5
    count = int(mask.sum().item())
    if count < 64:
        return
    d, p, a = learner.obs_dim, learner.priv_dim, learner.act_dim
    obs, priv = b["obs"].reshape(-1, d)[mask], b["priv"].reshape(-1, p)[mask]
    act, logp_old = b["act"].reshape(-1, a)[mask], b["logp"].reshape(-1)[mask]
    nav = b["nav"].reshape(-1)[mask]
    adv_all, ret, val_old = b["adv"].reshape(-1)[mask], b["ret"].reshape(-1)[mask], b["val"].reshape(-1)[mask]
    value_in = learner.value_input(obs, priv)
    learner.value_norm.update(ret.numpy(), learner.critic.net[4])
    target = torch.from_numpy(learner.value_norm.norm(ret.numpy()).astype(np.float32))
    pieces = max(1, min(args.minibatches, count // 64))
    for _ in range(args.epochs):
        for idx in torch.randperm(count).tensor_split(pieces):
            # Plain squared error on normalised targets: value clipping hurt in every setting Andrychowicz et
            # al. ("What Matters in On-Policy RL") tried; value normalisation helped in the MAPPO paper.
            v_loss = 0.5 * ((learner.critic(value_in[idx]) - target[idx]) ** 2).mean()
            loss = args.vf * v_loss
            if train_actor:
                _, new_logp, entropy = learner.actor.evaluate(obs[idx], act[idx], nav[idx])
                ratio = (new_logp - logp_old[idx]).exp()
                adv = adv_all[idx]
                adv = (adv - adv.mean()) / (adv.std() + 1e-8)
                pg_loss = torch.max(-adv * ratio, -adv * ratio.clamp(1 - args.clip, 1 + args.clip)).mean()
                loss = loss + pg_loss - args.ent * entropy[0].mean() - learner.ent_discrete * entropy[1].mean()
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
            "Abilities and controls (latest): "
            f"cop bursts {last.get('cop_bursts_min', 0)}/min ({last.get('burst_hits', 0)} landed hits last update), "
            f"runner boosts {last.get('runner_boosts_min', 0)}/min ({last.get('boost_rams', 0)} boost rams), "
            f"drifting cops {last.get('cop_drift_pct', 0)}% / runner {last.get('runner_drift_pct', 0)}%.",
            "",
            "Route choices (latest, % of choices): cops " + ", ".join(
                f"{name} {last.get('cop_route_' + name, 0)}" for name in COP_ROUTES) +
            "; runner " + ", ".join(f"{name} {last.get('runner_route_' + name, 0)}" for name in RUNNER_ROUTES) + ".",
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
