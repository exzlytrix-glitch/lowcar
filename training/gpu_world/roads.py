"""Road queries for the GPU training world, batched, mirroring scripts/ai/road_nav.gd and route_track.gd:
nearest road, the junction ahead (bends skipped), its exits left to right, routes and route lengths.
Routes use precomputed next-hop and distance tables (the same shortest paths A* finds in Godot).
All tensors are stacked over cities, padded to the largest city."""

import math

import numpy as np
import torch
from scipy.spatial import cKDTree

MAX_DEGREE = 8
BEND_STEPS = 16
ROUTE_HOPS = 12
LOOKUP_CELL = 2.0


class Roads:
    def __init__(self, cities, device="cpu", dtype=torch.float32):
        self.device, self.dtype = device, dtype
        graphs = cities.graphs
        self.count = len(graphs)
        nn = max(len(g["nodes"]) for g in graphs)
        ne = max(len(g["edges"]) for g in graphs)
        self.max_nodes = nn
        pos = np.zeros((self.count, nn, 2), np.float32)
        degree = np.zeros((self.count, nn), np.int64)
        neighbors = np.full((self.count, nn, MAX_DEGREE), -1, np.int64)
        edge_a = np.zeros((self.count, ne), np.int64)
        edge_b = np.zeros((self.count, ne), np.int64)
        edge_len = np.zeros((self.count, ne), np.float32)
        edge_count = np.zeros(self.count, np.int64)
        next_hop = np.zeros((self.count, nn, nn), np.int16)
        dist = np.full((self.count, nn, nn), 1e6, np.float32)
        node_count = np.zeros(self.count, np.int64)
        extent = cities.meta[0]["extent"]
        side = int(math.ceil(extent * 2.0 / LOOKUP_CELL))
        lookup = np.zeros((self.count, side, side), np.int32)
        for c, g in enumerate(graphs):
            n = len(g["nodes"])
            node_count[c] = n
            pos[c, :n] = g["nodes"]
            degree[c, :n] = g["degree"]
            fill = np.zeros(n, np.int64)
            for a, b in g["edges"]:
                neighbors[c, a, fill[a]] = b
                fill[a] += 1
                neighbors[c, b, fill[b]] = a
                fill[b] += 1
            m = len(g["edges"])
            edge_count[c] = m
            edge_a[c, :m], edge_b[c, :m] = g["edges"][:, 0], g["edges"][:, 1]
            edge_len[c, :m] = g["length"]
            pred = g["pred"]
            # next hop from s toward t is the predecessor of s on the shortest path from t.
            hop = pred.T.copy()
            hop[hop < 0] = np.arange(n)[:, None].repeat(n, 1)[hop < 0]
            next_hop[c, :n, :n] = hop.astype(np.int16)
            d = g["dist"].astype(np.float32)
            d[~np.isfinite(d)] = 1e6
            dist[c, :n, :n] = d
            # Nearest road segment for every 2 m cell: sample points along roads, nearest sample wins.
            samples, owners = [], []
            for e, (a, b) in enumerate(g["edges"]):
                pa, pb = g["nodes"][a], g["nodes"][b]
                k = max(2, int(np.linalg.norm(pb - pa) / 1.0) + 1)
                t = np.linspace(0.0, 1.0, k)[:, None]
                samples.append(pa + (pb - pa) * t)
                owners.append(np.full(k, e))
            tree = cKDTree(np.concatenate(samples))
            owner = np.concatenate(owners)
            centers = (np.arange(side) + 0.5) * LOOKUP_CELL - extent
            gx, gz = np.meshgrid(centers, centers)
            _, idx = tree.query(np.stack([gx.ravel(), gz.ravel()], 1))
            lookup[c] = owner[idx].reshape(side, side)
        t = lambda a, dt=None: torch.as_tensor(a, device=device, dtype=dt)
        self.pos = t(pos, dtype)
        self.degree = t(degree)
        self.neighbors = t(neighbors)
        self.edge_a, self.edge_b, self.edge_len = t(edge_a), t(edge_b), t(edge_len, dtype)
        self.edge_count, self.node_count = t(edge_count), t(node_count)
        self.next_hop = t(next_hop.astype(np.int64))
        self.dist = t(dist, dtype)
        self.lookup = t(lookup.astype(np.int64))
        self.lookup_side, self.extent = side, extent

    # --- basic queries -----------------------------------------------------------------------

    def node_xy(self, city, node):
        flat = self.pos.reshape(-1, 2)
        return flat[city * self.max_nodes + node.clamp(min=0)]

    def nearest_edge(self, city, x, z):
        s = self.lookup_side
        col = ((x + self.extent) / LOOKUP_CELL).long().clamp(0, s - 1)
        row = ((z + self.extent) / LOOKUP_CELL).long().clamp(0, s - 1)
        return self.lookup.reshape(-1)[city * s * s + row * s + col]

    def edge_nodes(self, city, edge):
        ne = self.edge_a.shape[1]
        return self.edge_a.reshape(-1)[city * ne + edge], self.edge_b.reshape(-1)[city * ne + edge]

    def node_ahead(self, city, x, z, hx, hz):
        """RoadNav.node_near: the end of the nearest road that lies ahead (or the nearer end, heading 0)."""
        a, b = self.edge_nodes(city, self.nearest_edge(city, x, z))
        pa, pb = self.node_xy(city, a), self.node_xy(city, b)
        ahead_a = hx * (pa[:, 0] - x) + hz * (pa[:, 1] - z)
        ahead_b = hx * (pb[:, 0] - x) + hz * (pb[:, 1] - z)
        no_heading = (hx == 0.0) & (hz == 0.0)
        near_a = ((pa[:, 0] - x) ** 2 + (pa[:, 1] - z) ** 2) < ((pb[:, 0] - x) ** 2 + (pb[:, 1] - z) ** 2)
        return torch.where(no_heading, torch.where(near_a, a, b), torch.where(ahead_a > ahead_b, a, b))

    def neighbor(self, city, node, k):
        return self.neighbors.reshape(-1, MAX_DEGREE)[city * self.max_nodes + node.clamp(min=0), k]

    def node_degree(self, city, node):
        return self.degree.reshape(-1)[city * self.max_nodes + node.clamp(min=0)]

    def road_distance(self, city, a, b):
        nn = self.max_nodes
        return self.dist.reshape(-1)[city * nn * nn + a.clamp(min=0) * nn + b.clamp(min=0)]

    def hop(self, city, a, b):
        nn = self.max_nodes
        return self.next_hop.reshape(-1)[city * nn * nn + a.clamp(min=0) * nn + b.clamp(min=0)]

    # --- junctions ---------------------------------------------------------------------------

    def through_bends(self, city, node, came_from, distance):
        """Follows a road through bend nodes (exactly two roads) to the next real junction or dead end.
        Returns (junction, the node before it, distance)."""
        for _ in range(BEND_STEPS):
            bend = self.node_degree(city, node) == 2
            if not bool(bend.any()):
                break
            first = self.neighbor(city, node, 0)
            onward = torch.where(first == came_from, self.neighbor(city, node, 1), first)
            step = torch.linalg.norm(self.node_xy(city, onward) - self.node_xy(city, node), dim=1)
            distance = torch.where(bend, distance + step, distance)
            came_from = torch.where(bend, node, came_from)
            node = torch.where(bend, onward, node)
        return node, came_from, distance

    def next_junction(self, city, x, z, hx, hz):
        """RoadNav.next_junction: (junction, node before it, distance along the road)."""
        a, b = self.edge_nodes(city, self.nearest_edge(city, x, z))
        pa, pb = self.node_xy(city, a), self.node_xy(city, b)
        pick_a = (hx * (pa[:, 0] - x) + hz * (pa[:, 1] - z)) > (hx * (pb[:, 0] - x) + hz * (pb[:, 1] - z))
        node = torch.where(pick_a, a, b)
        other = torch.where(pick_a, b, a)
        start = torch.where(pick_a[:, None], pa, pb)
        distance = torch.sqrt((start[:, 0] - x) ** 2 + (start[:, 1] - z) ** 2)
        return self.through_bends(city, node, other, distance)

    def exits(self, city, node, came_from):
        """RoadNav.exits: up to MAX_DEGREE roads leaving `node` except the one from `came_from`, sorted
        left to right. Returns turn (radians, negative = left), far junction, length, first neighbour
        and a validity mask, each (N, MAX_DEGREE). All neighbours are followed at once."""
        n = city.shape[0]
        p = self.node_xy(city, node)
        q = self.node_xy(city, came_from)
        ix, iz = p[:, 0] - q[:, 0], p[:, 1] - q[:, 1]
        il = torch.sqrt(ix ** 2 + iz ** 2).clamp(min=1e-6)
        ix, iz = (ix / il)[:, None], (iz / il)[:, None]
        nb = self.neighbors.reshape(-1, MAX_DEGREE)[city * self.max_nodes + node.clamp(min=0)]
        valid = (nb >= 0) & (nb != came_from[:, None])
        cities = city[:, None].expand(n, MAX_DEGREE).reshape(-1)
        r = self.node_xy(cities, nb.reshape(-1)).reshape(n, MAX_DEGREE, 2)
        ox, oz = r[:, :, 0] - p[:, None, 0], r[:, :, 1] - p[:, None, 1]
        seg = torch.sqrt(ox ** 2 + oz ** 2).clamp(min=1e-6)
        ox, oz = ox / seg, oz / seg
        turns = torch.where(valid, torch.atan2(ix * oz - iz * ox, ix * ox + iz * oz), 9.0)
        end, _, length = self.through_bends(cities, nb.reshape(-1).clamp(min=0),
                                            node[:, None].expand(n, MAX_DEGREE).reshape(-1), seg.reshape(-1))
        ends = torch.where(valid, end.reshape(n, MAX_DEGREE), 0)
        lengths = torch.where(valid, length.reshape(n, MAX_DEGREE), 0.0)
        firsts = torch.where(valid, nb, 0)
        order = turns.argsort(1)
        gather = lambda t: t.gather(1, order)
        return gather(turns), gather(ends), gather(lengths), gather(firsts), gather(valid)

    # --- routes ------------------------------------------------------------------------------

    def route(self, city, x, z, hx, hz, tx, tz):
        """Route polyline like RoadNav.route: the car's position, junctions along the shortest path from the
        road end ahead to the target's nearest junction, then the target. Returns points (N, H+2, 2) and
        how many are real (N)."""
        n = city.shape[0]
        start = self.node_ahead(city, x, z, hx, hz)
        finish = self.node_ahead(city, tx, tz, torch.zeros_like(tx), torch.zeros_like(tz))
        points = torch.zeros((n, ROUTE_HOPS + 2, 2), device=self.device, dtype=self.dtype)
        points[:, 0, 0], points[:, 0, 1] = x, z
        count = torch.ones(n, device=self.device, dtype=torch.long)
        node = start
        done = torch.zeros(n, device=self.device, dtype=torch.bool)
        for k in range(ROUTE_HOPS):
            xy = self.node_xy(city, node)
            points[:, k + 1] = torch.where(done[:, None], points[:, k], xy)
            count = count + (~done).long()
            done = done | (node == finish)
            node = torch.where(done, node, self.hop(city, node, finish))
        last = (count).clamp(max=ROUTE_HOPS + 1)
        idx = torch.arange(ROUTE_HOPS + 2, device=self.device)[None, :]
        target = torch.stack([tx, tz], 1)[:, None, :].expand(-1, ROUTE_HOPS + 2, -1)
        points = torch.where((idx >= last[:, None])[:, :, None], target, points)
        return points, last + 1

    def route_length(self, city, x, z, hx, hz, tx, tz):
        """Length of RoadNav.route without building it: car -> start junction -> (road distance) ->
        target's junction -> target."""
        start = self.node_ahead(city, x, z, hx, hz)
        finish = self.node_ahead(city, tx, tz, torch.zeros_like(tx), torch.zeros_like(tz))
        ps, pf = self.node_xy(city, start), self.node_xy(city, finish)
        return (torch.sqrt((ps[:, 0] - x) ** 2 + (ps[:, 1] - z) ** 2) + self.road_distance(city, start, finish)
                + torch.sqrt((pf[:, 0] - tx) ** 2 + (pf[:, 1] - tz) ** 2))

    @staticmethod
    def points_along(points, count, distances):
        """Points at the given distances along each polyline (RouteTrack.point_at from its start).
        points (N, K, 2), count (N), distances (D) -> (N, D, 2)."""
        seg = points[:, 1:] - points[:, :-1]
        length = torch.linalg.norm(seg, dim=2)
        k = torch.arange(points.shape[1] - 1, device=points.device)[None, :]
        length = torch.where(k < (count[:, None] - 1), length, torch.zeros_like(length))
        cum = torch.cat([torch.zeros_like(length[:, :1]), length.cumsum(1)], 1)
        total = cum[:, -1:]
        d = torch.minimum(distances[None, :].expand(points.shape[0], -1), total)
        idx = torch.searchsorted(cum.contiguous(), d.contiguous(), right=True).clamp(1, points.shape[1] - 1) - 1
        start = points.gather(1, idx[:, :, None].expand(-1, -1, 2))
        step = seg.gather(1, idx.clamp(max=seg.shape[1] - 1)[:, :, None].expand(-1, -1, 2))
        span = length.gather(1, idx.clamp(max=seg.shape[1] - 1)).clamp(min=1e-3)
        frac = ((d - cum.gather(1, idx)) / span).clamp(0.0, 1.0)
        return start + step * frac[:, :, None]
