"""Trains the learned cop driver with PPO (clipped policy gradients, the CleanRL-style recipe).

One shared brain drives every cop in every training world. The actor (what runs in the game) is
small on purpose so it stays cheap in plain GDScript; the critic (training only) is bigger.

Outputs in --out:
  checkpoint.pt   full training state, for resuming (also across 6-hour GitHub Actions jobs)
  cop_brain.json  the actor + observation scaling, loaded by the game (scripts/ai/policy_net.gd)
  progress.csv    one row per update
  summary.md      readable report (also shown on the GitHub Actions run page)

Example (local smoke test):
  python3 training/train.py --godot /Applications/Godot.app/Contents/MacOS/Godot --project . \\
      --out /tmp/cops --procs 1 --agents 16 --minutes 3
"""

import argparse
import csv
import json
import os
import time
from collections import deque

import numpy as np
import torch
import torch.nn as nn
from torch.distributions.normal import Normal

from godot_env import GodotCops


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--godot", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--stage", default="school")
    p.add_argument("--hours", type=float, default=0.0)
    p.add_argument("--minutes", type=float, default=0.0)
    p.add_argument("--procs", type=int, default=3)
    p.add_argument("--agents", type=int, default=16)
    p.add_argument("--steps", type=int, default=256, help="decisions per cop per update")
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--epochs", type=int, default=4)
    p.add_argument("--minibatches", type=int, default=8)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--gae-lambda", type=float, default=0.95)
    p.add_argument("--clip", type=float, default=0.2)
    p.add_argument("--ent", type=float, default=0.0)
    p.add_argument("--vf", type=float, default=0.5)
    p.add_argument("--max-grad", type=float, default=0.5)
    p.add_argument("--actor-hidden", type=int, default=64)
    p.add_argument("--critic-hidden", type=int, default=256)
    p.add_argument("--city-steps", type=int, default=3000)
    p.add_argument("--radius", type=float, default=450.0)
    p.add_argument("--save-minutes", type=float, default=10.0)
    p.add_argument("--resume", default="")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--threads", type=int, default=1)
    return p.parse_args()


def layer_init(layer, std=np.sqrt(2), bias=0.0):
    nn.init.orthogonal_(layer.weight, std)
    nn.init.constant_(layer.bias, bias)
    return layer


class Brain(nn.Module):
    def __init__(self, obs_dim, act_dim, actor_hidden, critic_hidden):
        super().__init__()
        self.critic = nn.Sequential(
            layer_init(nn.Linear(obs_dim, critic_hidden)), nn.Tanh(),
            layer_init(nn.Linear(critic_hidden, critic_hidden)), nn.Tanh(),
            layer_init(nn.Linear(critic_hidden, 1), std=1.0))
        self.actor_mean = nn.Sequential(
            layer_init(nn.Linear(obs_dim, actor_hidden)), nn.Tanh(),
            layer_init(nn.Linear(actor_hidden, actor_hidden)), nn.Tanh(),
            layer_init(nn.Linear(actor_hidden, act_dim), std=0.01))
        self.actor_logstd = nn.Parameter(torch.full((1, act_dim), -0.5))

    def value(self, x):
        return self.critic(x)

    def act(self, x, action=None):
        mean = self.actor_mean(x)
        std = torch.exp(self.actor_logstd.expand_as(mean))
        dist = Normal(mean, std)
        if action is None:
            action = dist.sample()
        return action, dist.log_prob(action).sum(1), dist.entropy().sum(1), self.critic(x)


class RunningMeanStd:
    def __init__(self, shape=()):
        self.mean = np.zeros(shape, np.float64)
        self.var = np.ones(shape, np.float64)
        self.count = 1e-4

    def update(self, x):
        batch_mean, batch_var, batch_count = x.mean(0), x.var(0), x.shape[0]
        delta = batch_mean - self.mean
        total = self.count + batch_count
        self.mean = self.mean + delta * batch_count / total
        m2 = self.var * self.count + batch_var * batch_count + delta ** 2 * self.count * batch_count / total
        self.var = m2 / total
        self.count = total

    def state(self):
        return {"mean": self.mean.tolist(), "var": self.var.tolist(), "count": self.count}

    def load(self, state):
        self.mean = np.array(state["mean"], np.float64)
        self.var = np.array(state["var"], np.float64)
        self.count = state["count"]


def export_brain(path, brain, obs_rms, meta):
    layers = []
    linear = [m for m in brain.actor_mean if isinstance(m, nn.Linear)]
    for index, layer in enumerate(linear):
        layers.append({
            "w": layer.weight.detach().cpu().numpy().astype(float).round(6).tolist(),
            "b": layer.bias.detach().cpu().numpy().astype(float).round(6).tolist(),
            "act": "tanh" if index < len(linear) - 1 else "none"})
    data = dict(meta)
    data.update({
        "obs_mean": obs_rms.mean.astype(float).round(6).tolist(),
        "obs_std": np.sqrt(obs_rms.var + 1e-8).astype(float).round(6).tolist(),
        "obs_clip": 10.0,
        "layers": layers,
        "action_names": ["steer", "throttle", "handbrake"]})
    with open(path + ".tmp", "w") as handle:
        json.dump(data, handle)
    os.replace(path + ".tmp", path)


def main():
    args = parse_args()
    budget = args.hours * 3600 + args.minutes * 60
    if budget <= 0:
        raise SystemExit("give --hours or --minutes")
    os.makedirs(args.out, exist_ok=True)
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    started = time.time()

    env = GodotCops(args.godot, args.project, procs=args.procs, agents=args.agents, seed=args.seed,
                    city_steps=args.city_steps, radius=args.radius, log_dir=os.path.join(args.out, "logs"))
    n, d, a = env.num_envs, env.obs_dim, env.act_dim
    brain = Brain(d, a, args.actor_hidden, args.critic_hidden)
    optimizer = torch.optim.Adam(brain.parameters(), lr=args.lr, eps=1e-5)
    obs_rms, ret_rms = RunningMeanStd((d,)), RunningMeanStd(())
    global_step, updates, prior_seconds = 0, 0, 0.0
    if args.resume and os.path.exists(args.resume):
        state = torch.load(args.resume, weights_only=False)
        brain.load_state_dict(state["brain"])
        optimizer.load_state_dict(state["optimizer"])
        obs_rms.load(state["obs_rms"])
        ret_rms.load(state["ret_rms"])
        global_step, updates = state["global_step"], state["updates"]
        prior_seconds = state.get("trained_seconds", 0.0)
        print(f"resumed from {args.resume}: {global_step} steps, {prior_seconds / 3600:.2f} h trained")

    def normalize(x):
        return np.clip((x - obs_rms.mean) / np.sqrt(obs_rms.var + 1e-8), -10.0, 10.0).astype(np.float32)

    obs_buf = torch.zeros((args.steps, n, d))
    act_buf = torch.zeros((args.steps, n, a))
    logp_buf = torch.zeros((args.steps, n))
    rew_buf = torch.zeros((args.steps, n))
    done_buf = torch.zeros((args.steps, n))
    val_buf = torch.zeros((args.steps, n))

    raw_obs = env.reset()
    obs_rms.update(raw_obs)
    next_done = np.zeros(n, np.float32)
    discounted = np.zeros(n, np.float64)
    episode_return = np.zeros(n, np.float64)
    finished = deque(maxlen=200)
    csv_path = os.path.join(args.out, "progress.csv")
    new_csv = not os.path.exists(csv_path)
    csv_file = open(csv_path, "a", newline="")
    writer = csv.writer(csv_file)
    if new_csv:
        writer.writerow(["hours", "steps", "sps", "episode_return", "speed_kmh", "progress_mps",
                         "wall_damage_per_min", "cop_damage_per_min", "episodes"])
    history = []
    last_save = time.time()
    meta = {"stage": args.stage, "obs_dim": d, "act_dim": a}

    def save(final=False):
        trained = prior_seconds + time.time() - started
        torch.save({"brain": brain.state_dict(), "optimizer": optimizer.state_dict(),
                    "obs_rms": obs_rms.state(), "ret_rms": ret_rms.state(), "global_step": global_step,
                    "updates": updates, "trained_seconds": trained, "args": vars(args)},
                   os.path.join(args.out, "checkpoint.pt"))
        export_brain(os.path.join(args.out, "cop_brain.json"), brain, obs_rms,
                     dict(meta, steps=global_step, trained_hours=round(trained / 3600, 3)))
        write_summary(args, history, final)

    try:
        while time.time() - started < budget:
            frac = max(0.05, 1.0 - (time.time() - started) / budget)
            optimizer.param_groups[0]["lr"] = frac * args.lr
            update_start = time.time()
            info_sum = np.zeros(env.info_dim)
            for step in range(args.steps):
                obs_t = torch.from_numpy(normalize(raw_obs))
                obs_buf[step] = obs_t
                done_buf[step] = torch.from_numpy(next_done)
                with torch.no_grad():
                    action, logp, _, value = brain.act(obs_t)
                act_buf[step] = action
                logp_buf[step] = logp
                val_buf[step] = value.flatten()
                raw_obs, reward, done, info = env.step(np.clip(action.numpy(), -1.0, 1.0))
                obs_rms.update(raw_obs)
                episode_return += reward
                discounted = discounted * args.gamma + reward
                ret_rms.update(discounted)
                rew_buf[step] = torch.from_numpy((reward / np.sqrt(ret_rms.var + 1e-8)).astype(np.float32))
                for index in np.nonzero(done > 0.5)[0]:
                    finished.append(episode_return[index])
                    episode_return[index] = 0.0
                    discounted[index] = 0.0
                next_done = (done > 0.5).astype(np.float32)
                info_sum += info.sum(0)
            global_step += args.steps * n

            with torch.no_grad():
                next_value = brain.value(torch.from_numpy(normalize(raw_obs))).flatten()
                advantages = torch.zeros_like(rew_buf)
                last = 0.0
                for t in reversed(range(args.steps)):
                    if t == args.steps - 1:
                        nonterminal = 1.0 - torch.from_numpy(next_done)
                        next_values = next_value
                    else:
                        nonterminal = 1.0 - done_buf[t + 1]
                        next_values = val_buf[t + 1]
                    delta = rew_buf[t] + args.gamma * next_values * nonterminal - val_buf[t]
                    last = delta + args.gamma * args.gae_lambda * nonterminal * last
                    advantages[t] = last
                returns = advantages + val_buf

            b_obs, b_act = obs_buf.reshape(-1, d), act_buf.reshape(-1, a)
            b_logp, b_adv = logp_buf.reshape(-1), advantages.reshape(-1)
            b_ret, b_val = returns.reshape(-1), val_buf.reshape(-1)
            batch = b_obs.shape[0]
            mini = batch // args.minibatches
            for _ in range(args.epochs):
                order = torch.randperm(batch)
                for start in range(0, batch, mini):
                    idx = order[start:start + mini]
                    _, new_logp, entropy, new_value = brain.act(b_obs[idx], b_act[idx])
                    ratio = (new_logp - b_logp[idx]).exp()
                    adv = b_adv[idx]
                    adv = (adv - adv.mean()) / (adv.std() + 1e-8)
                    pg_loss = torch.max(-adv * ratio, -adv * ratio.clamp(1 - args.clip, 1 + args.clip)).mean()
                    new_value = new_value.flatten()
                    clipped = b_val[idx] + (new_value - b_val[idx]).clamp(-args.clip, args.clip)
                    v_loss = 0.5 * torch.max((new_value - b_ret[idx]) ** 2, (clipped - b_ret[idx]) ** 2).mean()
                    loss = pg_loss - args.ent * entropy.mean() + args.vf * v_loss
                    optimizer.zero_grad()
                    loss.backward()
                    nn.utils.clip_grad_norm_(brain.parameters(), args.max_grad)
                    optimizer.step()
            updates += 1

            samples = args.steps * n
            minutes = samples * 0.1 / 60.0
            row = {
                "hours": round((prior_seconds + time.time() - started) / 3600, 3),
                "steps": global_step,
                "sps": round(samples / (time.time() - update_start)),
                "episode_return": round(float(np.mean(finished)), 3) if finished else 0.0,
                "speed_kmh": round(info_sum[1] / samples * 3.6, 1),
                "progress_mps": round(info_sum[0] / samples / 0.1, 2),
                "wall_damage_per_min": round(info_sum[2] / minutes, 2),
                "cop_damage_per_min": round(info_sum[3] / minutes, 2),
                "episodes": len(finished)}
            writer.writerow(list(row.values()))
            csv_file.flush()
            history.append(row)
            print(" ".join(f"{k}={v}" for k, v in row.items()), flush=True)
            if time.time() - last_save > args.save_minutes * 60:
                save()
                last_save = time.time()
    finally:
        save(final=True)
        csv_file.close()
        env.close()


def write_summary(args, history, final):
    lines = [f"# Cop training: stage `{args.stage}`", ""]
    if not history:
        lines.append("No updates finished yet.")
    else:
        first, last = history[0], history[-1]
        lines += [
            f"{'Finished' if final else 'In progress'}: {last['steps']:,} decisions, {last['hours']} h of training in total.",
            "",
            "| | first update | latest |",
            "|---|---|---|",
            f"| Average episode score | {first['episode_return']} | {last['episode_return']} |",
            f"| Average speed (km/h) | {first['speed_kmh']} | {last['speed_kmh']} |",
            f"| Progress along route (m/s) | {first['progress_mps']} | {last['progress_mps']} |",
            f"| Wall damage per cop-minute | {first['wall_damage_per_min']} | {last['wall_damage_per_min']} |",
            f"| Cop-on-cop damage per cop-minute | {first['cop_damage_per_min']} | {last['cop_damage_per_min']} |",
            f"| Decisions per second | {first['sps']} | {last['sps']} |",
            "",
            "Higher score, speed and progress are better; lower damage is better.",
            "",
            "Every 10th update:",
            "",
            "| hours | decisions | score | km/h | progress m/s | wall dmg/min |",
            "|---|---|---|---|---|---|"]
        for row in history[::10] + ([history[-1]] if len(history) % 10 != 1 else []):
            lines.append(f"| {row['hours']} | {row['steps']:,} | {row['episode_return']} | {row['speed_kmh']} | "
                         f"{row['progress_mps']} | {row['wall_damage_per_min']} |")
    with open(os.path.join(args.out, "summary.md"), "w") as handle:
        handle.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
