"""Runs an exported game brain (cop_brain.json / runner_brain.json) in PyTorch exactly like
scripts/ai/policy_net.gd decide(): normalised inputs, tanh layers, smooth outputs used as they are,
on/off and pick outputs rolled with the brain's own odds. Used to compare how the same brain plays
in Godot and in the GPU world."""

import json

import torch


class GameBrain:
    def __init__(self, path, device="cpu"):
        with open(path) as handle:
            data = json.load(handle)
        self.obs_dim = int(data["obs_dim"])
        self.mean = torch.tensor(data["obs_mean"], device=device)
        self.std = torch.tensor(data["obs_std"], device=device)
        self.clip = float(data.get("obs_clip", 10.0))
        self.layers = [(torch.tensor(l["w"], device=device), torch.tensor(l["b"], device=device), l["act"] == "tanh")
                       for l in data["layers"]]
        self.heads = [(h["kind"], int(h["size"])) for h in data.get("heads", [])]

    @torch.no_grad()
    def decide(self, obs, generator=None):
        x = ((obs[:, :self.obs_dim] - self.mean) / self.std).clamp(-self.clip, self.clip)
        for w, b, tanh in self.layers:
            x = x @ w.T + b
            if tanh:
                x = torch.tanh(x)
        outs, at = [], 0
        for kind, size in self.heads:
            part = x[:, at:at + size]
            at += size
            if kind == "gauss":
                outs.append(part.clamp(-1.0, 1.0))
            elif kind == "bern":
                outs.append((torch.rand(part.shape, device=x.device, generator=generator) < torch.sigmoid(part)).float())
            else:
                pick = torch.multinomial(torch.softmax(part, 1), 1, generator=generator).float()
                outs.append(pick)
        return torch.cat(outs, 1)
