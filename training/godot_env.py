"""Runs several headless Godot training worlds (scenes/training/train_env.tscn) and steps all of
their cops together as one batch. Each world is a separate Godot process with its own random city;
the wire format is described at the top of scripts/ai/train_env.gd."""

import json
import os
import socket
import struct
import subprocess

import numpy as np


class GodotCops:
    def __init__(self, godot, project, procs=3, agents=16, seed=1, repeat=6, city_steps=3000,
                 radius=450.0, log_dir=None, connect_timeout=600):
        self.procs = []
        self.socks = []
        self.agents = agents
        servers = []
        for index in range(procs):
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            server.settimeout(connect_timeout)
            port = server.getsockname()[1]
            args = [godot, "--headless", "--fixed-fps", "60", "--path", project,
                    "res://scenes/training/train_env.tscn", "--",
                    f"--port={port}", f"--agents={agents}", f"--seed={seed * 1000 + index}",
                    f"--repeat={repeat}", f"--city-steps={city_steps}", f"--radius={radius}"]
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
        self.obs_dim = hello[0]["obs_dim"]
        self.act_dim = hello[0]["act_dim"]
        self.info_dim = hello[0]["info_dim"]
        self.num_envs = procs * agents
        self._first = [self._recv_packet(sock) for sock in self.socks]

    def reset(self):
        return np.concatenate([packet[0] for packet in self._first])

    def step(self, actions):
        chunks = np.asarray(actions, dtype="<f4").reshape(len(self.socks), self.agents * self.act_dim)
        for sock, chunk in zip(self.socks, chunks):
            sock.sendall(chunk.tobytes())
        packets = [self._recv_packet(sock) for sock in self.socks]
        return tuple(np.concatenate([packet[k] for packet in packets]) for k in range(4))

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

    def _recv_packet(self, sock):
        size = struct.unpack("<i", self._recv_exact(sock, 4))[0]
        data = np.frombuffer(self._recv_exact(sock, size), dtype="<f4")
        a, d, i = self.agents, self.obs_dim, self.info_dim
        obs = data[: a * d].reshape(a, d)
        reward = data[a * d: a * d + a]
        done = data[a * d + a: a * d + 2 * a]
        info = data[a * d + 2 * a: a * d + 2 * a + a * i].reshape(a, i)
        return obs, reward, done, info

    @staticmethod
    def _recv_exact(sock, size):
        chunks = []
        remaining = size
        while remaining > 0:
            chunk = sock.recv(remaining)
            if not chunk:
                raise ConnectionError("Godot training world closed the connection")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    @staticmethod
    def _readline(sock):
        line = bytearray()
        while True:
            byte = sock.recv(1)
            if not byte:
                raise ConnectionError("Godot training world closed before saying hello")
            if byte == b"\n":
                return line.decode("utf-8")
            line += byte
