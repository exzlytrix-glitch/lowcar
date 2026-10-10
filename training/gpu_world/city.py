"""Cities for the GPU training world, loaded from what tools/export_gpu_world.gd wrote.

Collision: the exported grid says which 1 m cells a car body would hit. It becomes a signed distance
field (metres to the nearest wall, negative inside), sampled smoothly, with its gradient as the wall
normal. Cars are pushed out of walls along it (CharacterBody move_and_slide), and raycasts march along it.
Roads: the road graph, plus all-pairs road distances and next-hop tables for routes (instead of A*).
"""

import glob
import json
import os

import numpy as np
import torch
from scipy.ndimage import distance_transform_edt
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import shortest_path


class Cities:
    def __init__(self, folder, device="cpu", limit=None, dtype=torch.float32):
        paths = sorted(glob.glob(os.path.join(folder, "city_*.json")),
                       key=lambda p: int(os.path.basename(p)[5:-5]))[:limit]
        if not paths:
            raise FileNotFoundError(f"no exported cities in {folder}")
        self.device, self.dtype = device, dtype
        fields, normals, self.meta, self.graphs = [], [], [], []
        for path in paths:
            with open(path) as handle:
                meta = json.load(handle)
            size = meta["size"]
            solid = np.fromfile(path[:-5] + ".solid", dtype=np.uint8).reshape(size, size).astype(bool)
            solid = np.pad(solid, 1, constant_values=False)  # past the city is open grass, as in Godot
            cell = meta["cell"]
            outside = distance_transform_edt(~solid) * cell
            inside = distance_transform_edt(solid) * cell
            sdf = np.where(solid, -(inside - 0.5 * cell), outside - 0.5 * cell).astype(np.float32)
            gz, gx = np.gradient(sdf, cell)
            norm = np.sqrt(gx ** 2 + gz ** 2) + 1e-6
            fields.append(sdf)
            normals.append(np.stack([gx / norm, gz / norm]).astype(np.float32))
            meta["origin"] = -meta["extent"] - cell  # world coordinate of the padded grid's edge
            meta["grid"] = size + 2
            self.meta.append(meta)
            self.graphs.append(self._roads(meta))
        self.count = len(paths)
        self.cell = self.meta[0]["cell"]
        self.grid = self.meta[0]["grid"]
        self.origin = self.meta[0]["origin"]
        self.sdf = torch.from_numpy(np.stack(fields)).to(device)          # (C, G, G)
        self.normal = torch.from_numpy(np.stack(normals)).to(device)      # (C, 2, G, G)
        self._flat = [self.sdf.reshape(-1).contiguous(), self.normal[:, 0].reshape(-1).contiguous(),
                      self.normal[:, 1].reshape(-1).contiguous()]

    # --- collision ---------------------------------------------------------------------------

    def sample(self, city, x, z, normals=True):
        """Signed distance to walls and wall normal (nx, nz) at world points, bilinear. `city` per point.
        Outside the grid there is nothing to hit (open land around the city)."""
        g = self.grid
        u_raw = (x - self.origin) / self.cell - 0.5
        v_raw = (z - self.origin) / self.cell - 0.5
        outside = (u_raw < 0.0) | (v_raw < 0.0) | (u_raw > g - 1.001) | (v_raw > g - 1.001)
        u = u_raw.clamp(0.0, g - 1.001)
        v = v_raw.clamp(0.0, g - 1.001)
        c0, r0 = u.floor().long(), v.floor().long()
        fu, fv = u - c0, v - r0
        base = city * g * g
        out = []
        for field in (self._flat if normals else self._flat[:1]):
            def at(r, c):
                return field[base + r * g + c]
            top = at(r0, c0) * (1 - fu) + at(r0, c0 + 1) * fu
            bottom = at(r0 + 1, c0) * (1 - fu) + at(r0 + 1, c0 + 1) * fu
            out.append(top * (1 - fv) + bottom * fv)
        out[0] = torch.where(outside, torch.clamp(out[0], min=60.0), out[0])
        return out if normals else (out[0], None, None)

    def push_out(self, cars, iterations=2):
        """Moves cars out of walls (each car is three circles) and slides their velocity along the wall.
        Returns (hit, nx, nz): whether a car touched a wall this frame and the wall's normal."""
        hit = torch.zeros(cars.n, dtype=torch.bool, device=cars.device)
        hx = torch.zeros(cars.n, device=cars.device, dtype=cars.dtype)
        hz = torch.zeros_like(hx)
        for _ in range(iterations):
            cx, cz = cars.circles()
            city = cars.city[:, None].expand_as(cx)
            dist, nx, nz = self.sample(city.reshape(-1), cx.reshape(-1), cz.reshape(-1))
            depth = (cars.radius[:, None] - dist.reshape(cx.shape))
            worst, k = depth.max(1)
            nx = nx.reshape(cx.shape).gather(1, k[:, None]).squeeze(1)
            nz = nz.reshape(cx.shape).gather(1, k[:, None]).squeeze(1)
            touching = worst > 0.0
            push = worst.clamp(min=0.0)
            cars.x = cars.x + nx * push
            cars.z = cars.z + nz * push
            into = (cars.vx * nx + cars.vz * nz).clamp(max=0.0) * touching
            cars.vx = cars.vx - into * nx
            cars.vz = cars.vz - into * nz
            hx = torch.where(touching & ~hit, nx, hx)
            hz = torch.where(touching & ~hit, nz, hz)
            hit = hit | touching
        return hit, hx, hz

    def raycast(self, city, ox, oz, dx, dz, reach, steps=24):
        """Distance along each ray (unit direction) to the first wall, capped at `reach`: sphere tracing."""
        travelled = torch.zeros_like(ox)
        limit = torch.as_tensor(reach, device=ox.device, dtype=ox.dtype).expand_as(ox)
        for _ in range(steps):
            dist, _, _ = self.sample(city, ox + dx * travelled, oz + dz * travelled, normals=False)
            travelled = torch.minimum(travelled + dist.clamp(min=0.05), limit)
        dist, _, _ = self.sample(city, ox + dx * travelled, oz + dz * travelled, normals=False)
        return torch.where(dist < 0.3, travelled, limit)

    # --- roads -------------------------------------------------------------------------------

    def _roads(self, meta):
        nodes = np.array(meta["nodes"], np.float64).reshape(-1, 2)
        edges = np.array(meta["edges"], np.float64).reshape(-1, 3)
        a, b = edges[:, 0].astype(int), edges[:, 1].astype(int)
        length = np.linalg.norm(nodes[a] - nodes[b], axis=1)
        n = len(nodes)
        graph = csr_matrix((np.concatenate([length, length]), (np.concatenate([a, b]), np.concatenate([b, a]))), shape=(n, n))
        dist, pred = shortest_path(graph, directed=False, return_predecessors=True)
        return {"nodes": nodes, "edges": np.stack([a, b], 1), "length": length, "dist": dist, "pred": pred,
                "degree": np.bincount(np.concatenate([a, b]), minlength=n)}
