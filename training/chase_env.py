"""Runs several headless Godot chase arenas (scenes/training/chase_arena.tscn) and steps all their
slots together. Each arena is a separate Godot process with its own random city and several chases;
slot 0 of every chase is the runner, slots 1-5 its cops. Wire format: scripts/ai/chase_arena.gd."""

import json
import os
import socket
import struct
import subprocess

import numpy as np


class ChaseWorlds:
    def __init__(self, godot, project, procs=3, matches=6, seed=1, repeat=6, city_steps=3000,
                 radius=450.0, log_dir=None, connect_timeout=600, world_cities=False):
        self.procs = []
        self.socks = []
        servers = []
        for index in range(procs):
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            server.settimeout(connect_timeout)
            port = server.getsockname()[1]
            args = [godot, "--headless", "--fixed-fps", "60", "--path", project,
                    "res://scenes/training/chase_arena.tscn", "--",
                    f"--port={port}", f"--matches={matches}", f"--seed={seed * 1000 + index}",
                    f"--repeat={repeat}", f"--city-steps={city_steps}", f"--radius={radius}"]
            if world_cities:
                args.append("--world-cities")
            log = subprocess.DEVNULL
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                log = open(os.path.join(log_dir, f"godot_{index}.log"), "w")
            self.procs.append(subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT))
            servers.append(server)
        for server in servers:
            conn, _ = server.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            server.close()
            self.socks.append(conn)
        hello = [json.loads(self._readline(sock)) for sock in self.socks]
        h = hello[0]
        self.slots_per_proc = h["slots"]
        self.slots_per_match = h["slots_per_match"]
        self.obs_dim, self.cop_obs, self.runner_obs = h["obs_dim"], h["cop_obs"], h["runner_obs"]
        self.priv_dim, self.comp_dim, self.flag_dim = h["priv_dim"], h["comp_dim"], h["flag_dim"]
        self.act_dim, self.stats_dim = h["act_dim"], h["stats_dim"]
        self.num_slots = procs * self.slots_per_proc
        self.num_matches = self.num_slots // self.slots_per_match
        slot = np.arange(self.num_slots)
        self.is_runner = slot % self.slots_per_match == 0
        self.match_of = slot // self.slots_per_match
        self._first = [self._recv_packet(sock) for sock in self.socks]

    def reset(self):
        return self._merge(self._first)

    def step(self, actions):
        chunks = np.asarray(actions, dtype="<f4").reshape(len(self.socks), self.slots_per_proc * self.act_dim)
        for sock, chunk in zip(self.socks, chunks):
            sock.sendall(chunk.tobytes())
        return self._merge([self._recv_packet(sock) for sock in self.socks])

    def close(self):
        for sock in self.socks:
            try:
                sock.close()
            except OSError:
                pass
        for proc in self.procs:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    @staticmethod
    def _merge(packets):
        """(obs, priv, parts, flags) stacked over all slots, plus stats summed over the arenas."""
        merged = tuple(np.concatenate([packet[k] for packet in packets]) for k in range(4))
        return merged + (np.sum([packet[4] for packet in packets], axis=0),)

    def _recv_packet(self, sock):
        size = struct.unpack("<i", self._recv_exact(sock, 4))[0]
        data = np.frombuffer(self._recv_exact(sock, size), dtype="<f4")
        s = self.slots_per_proc
        out, at = [], 0
        for width in (self.obs_dim, self.priv_dim, self.comp_dim, self.flag_dim):
            out.append(data[at: at + s * width].reshape(s, width))
            at += s * width
        out.append(data[at: at + self.stats_dim].astype(np.float64))
        return out

    @staticmethod
    def _recv_exact(sock, size):
        chunks = []
        remaining = size
        while remaining > 0:
            chunk = sock.recv(remaining)
            if not chunk:
                raise ConnectionError("Godot chase arena closed the connection")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    @staticmethod
    def _readline(sock):
        line = bytearray()
        while True:
            byte = sock.recv(1)
            if not byte:
                raise ConnectionError("Godot chase arena closed before saying hello")
            if byte == b"\n":
                return line.decode("utf-8")
            line += byte
