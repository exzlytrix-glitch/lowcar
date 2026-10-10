"""The chase arena on the GPU: thousands of chases at once, mirroring the Godot training world
(scripts/ai/chase_match.gd, chase_agent.gd, chase_senses.gd, chase_nav.gd, chase_intel.gd, cop_senses.gd,
standoff_rule.gd, cop_burst.gd, runner_boost.gd) and speaking its exact protocol: same observation layout
(cop 176 / runner 165), privileged facts, reward parts, flags, stats and actions, so train_chase.py can
train on it unchanged and the brains load straight back into Godot.

Slot 0 of every chase is the runner, slots 1-5 its cops. Physics: training/gpu_world/physics.py.
"""

import math
import os

import numpy as np
import torch

from .city import Cities
from .physics import BOOSTING, CHARGING, READY, Cars, load_specs, wrap_angle
from .roads import Roads

SLOTS, COPS = 6, 5
OBS_DIM, COP_OBS, RUNNER_OBS = 176, 176, 165
PRIV_DIM, COMP_DIM, FLAG_DIM, ACT_DIM, STATS_DIM = 12, 8, 5, 5, 27
DECISION_FRAMES = 6
OPTIONS, NAV_DECISIONS = 5, 10
SPAWN_TRIES = 48


class GpuChase:
    def __init__(self, world, matches=256, device="cpu", seed=1, city_limit=None, torch_out=False):
        """torch_out: step()/reset() return tensors on `device` (for a trainer on the same GPU) instead of
        numpy arrays."""
        self.device = torch.device(device)
        self.torch_out = torch_out
        self.data, specs, self.lab = load_specs(os.path.join(world, "cars.json"))
        self.c = self.data["chase"]
        self.cities = Cities(world, device=self.device, limit=city_limit)
        self.roads = Roads(self.cities, device=self.device)
        self.gen = torch.Generator(device=self.device)
        self.gen.manual_seed(seed)
        self.M, self.N = matches, matches * SLOTS
        self.dt = 1.0 / self.data["physics_hz"]
        dev = self.device
        slot = torch.arange(self.N, device=dev) % SLOTS
        self.slot = slot
        self.match_index = torch.arange(self.N, device=dev) // SLOTS
        self.cars = Cars(self.N, specs, (slot > 0).long(), self.lab, device=dev)
        self.city_of_match = torch.randint(0, self.cities.count, (self.M,), device=dev, generator=self.gen)
        self.cars.city = self.city_of_match[self.match_index]
        self.frame = 0
        # protocol attributes (same as training/chase_env.py)
        self.num_slots, self.num_matches, self.slots_per_match = self.N, self.M, SLOTS
        self.obs_dim, self.cop_obs, self.runner_obs = OBS_DIM, COP_OBS, RUNNER_OBS
        self.priv_dim, self.comp_dim, self.flag_dim = PRIV_DIM, COMP_DIM, FLAG_DIM
        self.act_dim, self.stats_dim = ACT_DIM, STATS_DIM
        self.is_runner = (slot == 0).cpu().numpy()
        self.match_of = self.match_index.cpu().numpy()
        # pairs of cars inside each chase (15 per chase)
        local = torch.tensor([(i, j) for i in range(SLOTS) for j in range(i + 1, SLOTS)], device=dev)
        self.pairs = (local[None, :, :] + (torch.arange(self.M, device=dev) * SLOTS)[:, None, None]).reshape(-1, 2)
        self.pair_runner = (self.pairs[:, 0] % SLOTS) == 0
        f = lambda *shape: torch.zeros(*shape, device=dev)
        # per chase
        self.minute, self.elapsed, self.target_cops = f(self.M), f(self.M), torch.ones(self.M, device=dev, dtype=torch.long)
        self.reinforce_clock, self.abort = f(self.M), torch.zeros(self.M, dtype=torch.bool, device=dev)
        self.known = torch.ones(self.M, dtype=torch.bool, device=dev)
        self.last_pos, self.last_vel, self.last_fwd, self.age = f(self.M, 2), f(self.M, 2), f(self.M, 2), f(self.M)
        self.standoff_for = f(self.M)
        # per slot
        self.active = torch.zeros(self.N, dtype=torch.bool, device=dev)
        self.respawn_wait, self.last_gap = f(self.N), f(self.N)
        self.accum = f(self.N, COMP_DIM)
        self.stats = torch.zeros(STATS_DIM, device=dev, dtype=torch.float64)
        self.option = torch.zeros(self.N, dtype=torch.long, device=dev)
        self.nav_countdown = torch.zeros(self.N, dtype=torch.long, device=dev)
        self.nav_open = torch.zeros(self.N, dtype=torch.bool, device=dev)
        self.frozen = f(self.N, 2)
        self.goal = f(self.N, 2)
        self.drive_len = f(self.N, OPTIONS)
        self.burst_left, self.burst_wait, self.burst_cooldown = f(self.N), f(self.N), torch.full((self.N,), 4.5, device=dev)
        self.burst_count, self.burst_seen = torch.zeros(self.N, dtype=torch.long, device=dev), torch.zeros(self.N, dtype=torch.long, device=dev)
        self.charge_left = f(self.N)
        self.delay = torch.zeros(self.N, dtype=torch.long, device=dev)
        self.orders_due = torch.full((self.N, 3), -1, dtype=torch.long, device=dev)
        self.orders = f(self.N, 3, 5)
        self.command = f(self.N, 4)  # throttle, steer, handbrake, hold boost (as delivered)
        self.last_yaw, self.has_yaw = f(self.N), torch.zeros(self.N, dtype=torch.bool, device=dev)
        self.sees = torch.zeros(self.N, dtype=torch.bool, device=dev)
        self._park(torch.ones(self.N, dtype=torch.bool, device=dev))
        self._restart(torch.ones(self.M, dtype=torch.bool, device=dev))
        self._first = self._decide(first=True)

    # --- protocol -----------------------------------------------------------------------------

    def reset(self):
        return self._first

    def step(self, actions):
        a = actions.to(self.device).float() if torch.is_tensor(actions) else torch.as_tensor(np.asarray(actions, np.float32), device=self.device)
        self._act(a)
        for _ in range(DECISION_FRAMES):
            self._physics_frame()
        return self._decide()

    def close(self):
        pass

    def change_cities(self, fraction=0.25):
        """Moves a share of chases to other cities (they end without blame at the next decision)."""
        move = torch.rand(self.M, device=self.device, generator=self.gen) < fraction
        self.city_of_match = torch.where(move, torch.randint(0, self.cities.count, (self.M,), device=self.device, generator=self.gen), self.city_of_match)
        self.abort |= move

    # --- helpers ------------------------------------------------------------------------------

    def _rand(self, *shape):
        return torch.rand(*shape, device=self.device, generator=self.gen)

    def _m(self, per_match):
        return per_match[self.match_index]

    def _forward(self, yaw=None):
        yaw = self.cars.yaw if yaw is None else yaw
        return -torch.sin(yaw), -torch.cos(yaw)

    def _cop_top_speed(self):
        return self.c["base_top_speed"] * torch.clamp(0.97 + 0.025 * self.minute, max=1.3)

    def _park(self, mask):
        car = self.cars
        idx = torch.arange(self.N, device=self.device)
        car.x = torch.where(mask, 5000.0 + (idx // SLOTS).float() * 30.0, car.x)
        car.z = torch.where(mask, 5000.0 + (idx % SLOTS).float() * 30.0, car.z)
        for name in ("vx", "vz", "fwd", "spin", "stagger", "steer", "drifting"):
            setattr(car, name, torch.where(mask, 0.0, getattr(car, name)))
        self.active = self.active & ~mask
        self.command = torch.where(mask[:, None], 0.0, self.command)
        self.orders_due = torch.where(mask[:, None], -1, self.orders_due)

    def _place(self, mask, x, z, dx, dz, speed):
        car = self.cars
        car.x, car.z = torch.where(mask, x, car.x), torch.where(mask, z, car.z)
        car.yaw = torch.where(mask, torch.atan2(-dx, -dz), car.yaw)
        car.fwd = torch.where(mask, speed, car.fwd)
        car.vx, car.vz = torch.where(mask, dx * speed, car.vx), torch.where(mask, dz * speed, car.vz)
        for name in ("spin", "stagger", "steer", "drifting", "drift_time", "slip", "wall_contact", "boost_charge",
                     "boost_power", "boost_duration", "boost_elapsed", "boost_fired"):
            setattr(car, name, torch.where(mask, 0.0, getattr(car, name)))
        car.grip_return = torch.where(mask, 1.0, car.grip_return)
        car.boost_phase = torch.where(mask, READY, car.boost_phase)
        car.health = torch.where(mask, car.c_max_health, car.health)
        car.prev_x, car.prev_z, car.prev_yaw = car.x.clone(), car.z.clone(), car.yaw.clone()
        self.command = torch.where(mask[:, None], 0.0, self.command)
        self.orders_due = torch.where(mask[:, None], -1, self.orders_due)
        self.option = torch.where(mask, 0, self.option)
        self.nav_countdown = torch.where(mask, 0, self.nav_countdown)
        self.has_yaw = self.has_yaw & ~mask
        self.burst_left, self.burst_wait = torch.where(mask, 0.0, self.burst_left), torch.where(mask, 0.0, self.burst_wait)
        self.charge_left = torch.where(mask, 0.0, self.charge_left)
        self.accum = torch.where(mask[:, None], 0.0, self.accum)

    def _random_road_spot(self, city, min_length=12.0, t_range=(0.25, 0.75), tries=20):
        """RoadNav.random_road_spot for each entry of `city`: point on a random road and its direction
        (all tries at once, the first road long enough wins)."""
        n = city.shape[0]
        count = self.roads.edge_count[city][:, None]
        e = (self._rand(n, tries) * count).long().clamp(max=count - 1)
        c = city[:, None].expand(n, tries).reshape(-1)
        a, b = self.roads.edge_nodes(c, e.reshape(-1))
        pa, pb = self.roads.node_xy(c, a).reshape(n, tries, 2), self.roads.node_xy(c, b).reshape(n, tries, 2)
        seg = pb - pa
        length = torch.linalg.norm(seg, dim=2)
        ok = length >= min_length
        first = ok.float().argmax(1)
        rows = torch.arange(n, device=self.device)
        pa, seg, length = pa[rows, first], seg[rows, first], length[rows, first]
        t = t_range[0] + self._rand(n) * (t_range[1] - t_range[0])
        p = pa + seg * t[:, None]
        d = seg / length.clamp(min=1e-3)[:, None]
        d = torch.where((self._rand(n) < 0.5)[:, None], -d, d)
        return p[:, 0], p[:, 1], d[:, 0], d[:, 1]

    def _pick_goals(self, mask):
        """A random junction more than 300 m away for each chase's runner where `mask` (12 tries at once;
        like the game, the last try is kept when none is far enough)."""
        rows = torch.arange(self.M, device=self.device) * SLOTS
        city = self.city_of_match
        here = torch.stack([self.cars.x[rows], self.cars.z[rows]], 1)
        node = (self._rand(self.M, 12) * self.roads.node_count[city][:, None]).long()
        p = self.roads.node_xy(city[:, None].expand(-1, 12).reshape(-1), node.reshape(-1)).reshape(self.M, 12, 2)
        far = torch.linalg.norm(p - here[:, None, :], dim=2) > 300.0
        pick = torch.where(far.any(1), far.float().argmax(1), 11)
        goal = p[torch.arange(self.M, device=self.device), pick]
        self.goal[rows] = torch.where(mask[:, None], goal, self.goal[rows])

    # --- chase lifecycle (ChaseMatch.restart / _spawn_cop / _reinforce) ------------------------

    def _restart(self, matches):
        if not bool(matches.any()):  # one check per decision; most decisions start no new chase
            return
        dev = self.device
        m = matches
        self.abort = self.abort & ~m
        self.elapsed = torch.where(m, 0.0, self.elapsed)
        self.minute = torch.where(m, self._rand(self.M) * self.c.get("start_minute_max", 15.0), self.minute)
        odds = torch.tensor(self.c["squad_odds"], device=dev)
        squad = torch.searchsorted(odds.cumsum(0), self._rand(self.M)).clamp(max=COPS - 1) + 1
        self.target_cops = torch.where(m, squad, self.target_cops)
        self.reinforce_clock = torch.where(m, 20.0 + self._rand(self.M) * 20.0, self.reinforce_clock)
        self.standoff_for = torch.where(m, 0.0, self.standoff_for)
        # every new chase gets a random city (instead of swapping the whole arena's city)
        self.city_of_match = torch.where(m, torch.randint(0, self.cities.count, (self.M,), device=dev, generator=self.gen), self.city_of_match)
        self.cars.city = self.city_of_match[self.match_index]
        slots_of = self._m(m)
        self._park(slots_of & (self.slot > 0))
        self.respawn_wait = torch.where(slots_of, 0.0, self.respawn_wait)
        runner = slots_of & (self.slot == 0)
        x, z, dx, dz = self._random_road_spot(self.city_of_match)
        speed = torch.where(self._rand(self.M) < self.c["runner_standing_start"], 0.0, 15.0 + self._rand(self.M) * 15.0)
        spread = lambda v: torch.zeros(self.N, device=dev).index_copy(0, torch.arange(self.M, device=dev) * SLOTS, v)
        self._place(runner, spread(x), spread(z), spread(dx), spread(dz), spread(speed))
        self.active = self.active | runner
        self._pick_goals(m)
        self._refresh_intel(m)
        # first cops: one behind, the rest behind or ahead
        for count in range(COPS):
            behind = (count == 0) | (self._rand(self.M) < 0.3)
            self._spawn(m & (self.target_cops > count), behind)
        self.accum = torch.where(slots_of[:, None], 0.0, self.accum)

    def _free_slot(self):
        """First inactive cop slot per chase (-1 if none), as a global slot index."""
        free = (~self.active).reshape(self.M, SLOTS).clone()
        free[:, 0] = False
        has = free.any(1)
        first = free.float().argmax(1)
        return torch.where(has, torch.arange(self.M, device=self.device) * SLOTS + first, -1)

    def _spawn(self, want, behind):
        """Spawns one cop in each chase where `want`, out of sight like the lab chase. All candidate spots
        are drawn at once; the first that fits wins (the first 32 also have to be behind / ahead)."""
        dev, M, K = self.device, self.M, SPAWN_TRIES
        slot = self._free_slot()
        want = want & (slot >= 0)
        rows = torch.arange(M, device=dev)
        r = rows * SLOTS
        city = self.city_of_match
        here = torch.stack([self.cars.x[r], self.cars.z[r]], 1)
        hx, hz = self._forward(self.cars.yaw[r])
        near = torch.where(behind, 40.0, 110.0)
        far = torch.where(behind, 110.0, 280.0)
        count = self.roads.edge_count[city][:, None]
        e = (self._rand(M, K) * count).long().clamp(max=count - 1)
        c = city[:, None].expand(M, K).reshape(-1)
        a, b = self.roads.edge_nodes(c, e.reshape(-1))
        pa, pb = self.roads.node_xy(c, a).reshape(M, K, 2), self.roads.node_xy(c, b).reshape(M, K, 2)
        p = pa + (pb - pa) * (0.2 + self._rand(M, K) * 0.6)[:, :, None]
        off = p - here[:, None, :]
        dist = torch.linalg.norm(off, dim=2)
        side = (hx[:, None] * off[:, :, 0] + hz[:, None] * off[:, :, 1]) / dist.clamp(min=1e-3)
        ok = (dist >= near[:, None]) & (dist <= far[:, None])
        facing = torch.where(behind[:, None], side <= -0.3, side >= 0.1)
        ok = ok & (facing | (torch.arange(K, device=dev) >= 32)[None, :])
        cops = torch.stack([self.cars.x, self.cars.z], 1).reshape(M, SLOTS, 2)[:, 1:]
        cop_active = self.active.reshape(M, SLOTS)[:, 1:]
        crowded = ((torch.linalg.norm(cops[:, None, :, :] - p[:, :, None, :], dim=3) < 25.0) & cop_active[:, None, :]).any(2)
        ok = ok & ~crowded
        first = ok.float().argmax(1)
        final = want & ok.any(1)
        p, pa, pb, dist = p[rows, first], pa[rows, first], pb[rows, first], dist[rows, first]
        d = (pb - pa) / torch.linalg.norm(pb - pa, dim=1).clamp(min=1e-3)[:, None]
        along = d[:, 0] * hx + d[:, 1] * hz
        parallel = along.abs() > 0.5
        d = torch.where((parallel & (along < 0.0))[:, None], -d, d)
        line = here + torch.stack([hx, hz], 1) * dist[:, None] - p
        d = torch.where((~parallel & ((d * line).sum(1) < 0.0))[:, None], -d, d)
        speed = torch.where(parallel, 22.0, 12.0)
        speed = torch.where(self._rand(M) < self.c["cop_parked_start"], 0.0, speed)
        # write into the chosen slots (chases without a spawn write nothing: their target index is the
        # runner row, which a spawn never uses, and the mask there stays False)
        target = torch.where(final, slot, r)
        mask = torch.zeros(self.N, dtype=torch.bool, device=dev).index_put((target,), final, accumulate=True)
        full = lambda v: torch.zeros(self.N, device=dev).index_put((target,), torch.where(final, v, 0.0), accumulate=True)
        self._place(mask, full(p[:, 0]), full(p[:, 1]), full(d[:, 0]), full(d[:, 1]), full(speed))
        self.cars.max_speed = torch.where(mask, self._m(self._cop_top_speed()), self.cars.max_speed)
        self.active = self.active | mask
        minute = self._m(self.minute)
        self.burst_cooldown = torch.where(mask, 4.5 + (2.0 - 4.5) * (minute / 12.0).clamp(0.0, 1.0), self.burst_cooldown)
        lo, hi = self.c["cop_delay_frames"]
        self.delay = torch.where(mask, (lo + self._rand(self.N) * (hi - lo + 1)).long().clamp(max=hi), self.delay)
        self.last_gap = torch.where(mask, full(dist), self.last_gap)
        self.burst_seen = torch.where(mask, self.burst_count, self.burst_seen)

    def _reinforce(self, running):
        self.reinforce_clock = torch.where(running, self.reinforce_clock - 0.1, self.reinforce_clock)
        tick = running & (self.reinforce_clock <= 0.0)
        self.reinforce_clock = torch.where(tick, 20.0 + self._rand(self.M) * 20.0, self.reinforce_clock)
        grow = tick & (self._rand(self.M) < self.c.get("reinforce_chance", 0.5))
        self.target_cops = torch.where(grow, (self.target_cops + 1).clamp(max=COPS), self.target_cops)
        cops = self.active.reshape(self.M, SLOTS)[:, 1:].sum(1)
        slot = self._free_slot()
        ready = slot >= 0
        wait = self.respawn_wait[slot.clamp(min=0)]
        want = running & (cops < self.target_cops) & ready & (wait <= 0.0)
        self._spawn(want, self._rand(self.M) < 0.35)

    # --- intel (ChaseIntel) --------------------------------------------------------------------

    def _refresh_intel(self, m):
        r = torch.arange(self.M, device=self.device) * SLOTS
        pos = torch.stack([self.cars.x[r], self.cars.z[r]], 1)
        vel = torch.stack([self.cars.vx[r], self.cars.vz[r]], 1)
        fx, fz = self._forward(self.cars.yaw[r])
        fwd = torch.stack([fx, fz], 1)
        self.known = torch.where(m, True, self.known)
        self.age = torch.where(m, 0.0, self.age)
        self.last_pos = torch.where(m[:, None], pos, self.last_pos)
        self.last_vel = torch.where(m[:, None], vel, self.last_vel)
        self.last_fwd = torch.where(m[:, None], fwd, self.last_fwd)

    def _update_intel(self, dt):
        car = self.cars
        rx, rz = self._m(car.x[::SLOTS]), self._m(car.z[::SLOTS])
        gap = torch.sqrt((car.x - rx) ** 2 + (car.z - rz) ** 2)
        cop = self.active & (self.slot > 0)
        check = cop & (gap >= self.c["always_see"]) & (gap <= self.c["sight_range"])
        dx, dz = (rx - car.x) / gap.clamp(min=1e-3), (rz - car.z) / gap.clamp(min=1e-3)
        clear = self.cities.raycast(car.city, car.x, car.z, dx, dz, gap.clamp(max=self.c["sight_range"]))
        sees = cop & ((gap < self.c["always_see"]) | (check & (clear >= gap - 0.5)))
        self.sees = sees
        anyone = sees.reshape(self.M, SLOTS).any(1)
        self.age = self.age + dt
        refresh = anyone | (self.age >= self.c["ping_seconds"])
        self._refresh_intel(refresh)
        self.known = torch.where(refresh, True, torch.zeros_like(self.known))

    def _believed(self):
        return self.last_pos + self.last_vel * self.age.clamp(max=self.c["lead_seconds"])[:, None]

    # --- physics frame (ChaseMatch.physics_tick + car physics + crashes) -----------------------

    def _physics_frame(self):
        car = self.cars
        self.frame += 1
        # delayed orders arrive
        due = (self.orders_due >= 0) & (self.orders_due <= self.frame)
        last = torch.where(due, torch.arange(3, device=self.device)[None, :], -1).max(1).values
        has = last >= 0
        pick = self.orders.gather(1, last.clamp(min=0)[:, None, None].expand(-1, 1, 5)).squeeze(1)
        self.command[:, :3] = torch.where(has[:, None], pick[:, :3], self.command[:, :3])
        self._try_fire((due & (self.orders[:, :, 4] > 0.5)).any(1))
        self.orders_due = torch.where(due, -1, self.orders_due)
        # standoff rule
        self._standoff()
        enabled = self.active
        wall, before = car.step(self.command[:, 0], self.command[:, 1], self.command[:, 2] > 0.5, self.command[:, 3] > 0.5,
                                enabled, self.cities, self.dt)
        self.stats[17] += (car.boost_fired * (self.slot == 0) * enabled).sum()
        both = self.active[self.pairs[:, 0]] & self.active[self.pairs[:, 1]]
        _, per_pair = car.crashes(self.pairs, before, self.frame, mask=both)
        self._credit(wall, self.pairs, per_pair)

    def _credit(self, wall, pairs, per_pair):
        acc, st = self.accum, self.stats
        runner = self.slot == 0
        cop = (self.slot > 0) & self.active
        # walls
        rw = torch.where(runner & self.active, wall, 0.0)
        acc[:, 1] += rw
        acc[:, 6] += rw
        cw = torch.where(cop, wall, 0.0)
        acc[:, 3] += cw
        team = rw.reshape(self.M, SLOTS)[:, 0]
        st[3] += rw.sum()
        st[5] += rw.sum()
        st[6] += cw.sum()
        if pairs.numel():
            a, b = pairs[:, 0], pairs[:, 1]
            ha, hb = per_pair[:, 0], per_pair[:, 1]
            with_runner = (a % SLOTS) == 0
            # runner (a) hit by cop (b)
            rd = torch.where(with_runner, ha, 0.0)
            acc[:, 1].index_add_(0, a, rd)
            acc[:, 6].index_add_(0, b, rd)
            team = team.index_add(0, a // SLOTS, rd)
            st[3] += rd.sum()
            st[4] += rd.sum()
            st[15] += (rd > 0).sum()
            st[24] += ((rd > 0) & (self.burst_left[b] > 0.0)).sum()
            # cop (b) hit by runner (a): the cop's damage from car hits, the runner's damage dealt to cops
            cd = torch.where(with_runner, hb, 0.0)
            acc[:, 4].index_add_(0, b, cd)
            acc[:, 3].index_add_(0, a, cd)
            st[25] += ((cd > 0) & (self.cars.boost_phase[a] == BOOSTING)).sum()
            # cop-cop: each one's damage is friendly fire dealt by the other
            fa, fb = torch.where(with_runner, 0.0, ha), torch.where(with_runner, 0.0, hb)
            acc[:, 4].index_add_(0, a, fa)
            acc[:, 4].index_add_(0, b, fb)
            acc[:, 7].index_add_(0, b, fa)
            acc[:, 7].index_add_(0, a, fb)
            st[8] += (fa + fb).sum()
        acc[:, 0] += torch.where(cop, self._m(team), 0.0)

    def _standoff(self):
        car = self.cars
        rx, rz = car.x[::SLOTS], car.z[::SLOTS]
        speed = torch.sqrt(car.vx[::SLOTS] ** 2 + car.vz[::SLOTS] ** 2)
        gap = torch.sqrt((car.x - self._m(rx)) ** 2 + (car.z - self._m(rz)) ** 2).reshape(self.M, SLOTS)
        near = (gap < self.c["standoff_range"]) & self.active.reshape(self.M, SLOTS)
        near[:, 0] = False
        stand = (speed < self.c["standoff_speed"]) & near.any(1) & self.active[::SLOTS]
        self.standoff_for = torch.where(stand, self.standoff_for + self.dt, 0.0)
        hurt = stand & (self.standoff_for >= self.c["standoff_grace"])
        r = torch.arange(self.M, device=self.device) * SLOTS
        damage = torch.where(hurt, torch.minimum(torch.full_like(speed, self.c["standoff_damage"] * self.dt), car.health[r]), 0.0)
        car.health[r] = (car.health[r] - damage).clamp(min=0.0)
        self.accum[r, 1] += damage
        share = damage / near.sum(1).clamp(min=1)
        credit = torch.where(near, share[:, None], 0.0).reshape(-1)
        self.accum[:, 6] += credit
        cops = (self.slot > 0) & self.active
        self.accum[:, 0] += torch.where(cops, self._m(damage), 0.0)
        self.stats[3] += damage.sum()
        self.stats[26] += damage.sum()

    def _try_fire(self, fire):
        ok = fire & (self.burst_left <= 0.0) & (self.burst_wait <= 0.0)
        self.burst_left = torch.where(ok, self.c["burst_duration"], self.burst_left)
        self.burst_wait = torch.where(ok, self.burst_cooldown, self.burst_wait)
        self.burst_count = self.burst_count + ok.long()

    # --- actions (ChaseAgent.apply + ChaseMatch.act) -----------------------------------------

    def _act(self, a):
        car = self.cars
        dt = DECISION_FRAMES * self.dt
        act = self.active
        runner = (self.slot == 0) & act
        cop = (self.slot > 0) & act
        steer, throttle = a[:, 0].clamp(-1, 1), a[:, 1].clamp(-1, 1)
        handbrake = a[:, 2] > 0.5
        choose = act & self.nav_open
        new_option = a[:, 4].round().long().clamp(0, OPTIONS - 1)
        self.option = torch.where(choose, new_option, self.option)
        targets = self._targets_cache
        picked = targets.gather(1, self.option[:, None, None].expand(-1, 1, 2)).squeeze(1)
        self.frozen = torch.where((choose & (self.slot == 0))[:, None], picked, self.frozen)
        # runner boost (RunnerBoost.hold)
        choice = a[:, 3].round().long()
        charging = car.boost_phase == CHARGING
        charges = torch.tensor(self.c["boost_charges"], device=self.device)
        cancelled = (self.charge_left > 0.0) & ~charging
        self.charge_left = torch.where(cancelled, 0.0, self.charge_left)
        running = self.charge_left > 0.0
        self.charge_left = torch.where(running, self.charge_left - dt, self.charge_left)
        hold = running & (self.charge_left > 0.0)
        start = (~running) & (~cancelled) & (choice >= 1) & (car.boost_phase == READY)
        self.charge_left = torch.where(start, charges[(choice - 1).clamp(0, 3)], self.charge_left)
        hold = (hold | start) & runner
        # cop burst recharge runs on (CopBurst.advance: the recharge only counts once the burst is over);
        # the order to fire travels with the delayed controls
        waiting = cop & (self.burst_left <= 0.0)
        self.burst_left = torch.where(cop, (self.burst_left - dt).clamp(min=0.0), self.burst_left)
        self.burst_wait = torch.where(waiting, (self.burst_wait - dt).clamp(min=0.0), self.burst_wait)
        fire = cop & (a[:, 3] > 0.5)
        order = torch.stack([throttle, steer, handbrake.float(), hold.float(), fire.float()], 1)
        now = act & (self.delay <= 0)
        self.command[:, :3] = torch.where(now[:, None], order[:, :3], self.command[:, :3])
        self.command[:, 3] = torch.where(runner, hold.float(), self.command[:, 3])
        self._try_fire(now & fire)
        later = act & (self.delay > 0)
        free = (self.orders_due < 0).float().argmax(1)
        put = later[:, None] & (torch.arange(3, device=self.device)[None, :] == free[:, None])
        self.orders_due = torch.where(put, (self.frame + self.delay)[:, None], self.orders_due)
        self.orders = torch.where(put[:, :, None], order[:, None, :], self.orders)
        # stats
        st = self.stats
        st[18] += (runner & (car.boost_phase == CHARGING)).sum()
        st[20] += (runner & (car.drifting > 0.5)).sum()
        st[22] += (runner & handbrake).sum()
        st[16] += torch.where(cop, self.burst_count - self.burst_seen, 0).sum()
        self.burst_seen = self.burst_count.clone()
        st[19] += (cop & (car.drifting > 0.5)).sum()
        st[21] += (cop & handbrake).sum()
        st[23] += (cop & (car.fwd < -1.0)).sum()
        # cop top speed: difficulty, catch-up when behind, burst
        rx, rz = self._m(car.x[::SLOTS]), self._m(car.z[::SLOTS])
        hx, hz = self._forward(self._m(car.yaw[::SLOTS]))
        ox, oz = car.x - rx, car.z - rz
        distance = torch.sqrt(ox ** 2 + oz ** 2)
        behind = (hx * ox + hz * oz) < 0.0
        lag = torch.where(behind, ((distance - self.c["catch_up_start"]) / (self.c["catch_up_full"] - self.c["catch_up_start"])).clamp(0.0, 1.0), 0.0)
        top = self._m(self._cop_top_speed()) * (1.0 + (self.c["catch_up_boost"] - 1.0) * lag)
        top = torch.where(self.burst_left > 0.0, top * self.c["burst_speed_gain"], top)
        car.max_speed = torch.where(cop, top, car.max_speed)

    # --- decision (ChaseMatch.decide) ---------------------------------------------------------

    def _decide(self, first=False):
        dt = DECISION_FRAMES * self.dt
        car = self.cars
        dev = self.device
        if not first:
            self.elapsed = self.elapsed + dt
            if "start_minute_max" in self.c:  # exports from before the chase minute ran on lack this
                self.minute = self.minute + dt / 60.0
        parts = self.accum.clone()
        self.accum.zero_()
        flags = torch.zeros(self.N, FLAG_DIM, device=dev)
        rx, rz = self._m(car.x[::SLOTS]), self._m(car.z[::SLOTS])
        gap = torch.sqrt((car.x - rx) ** 2 + (car.z - rz) ** 2)
        cop = (self.slot > 0) & self.active
        idle = (self.slot > 0) & ~self.active
        self.respawn_wait = torch.where(idle, self.respawn_wait - dt, self.respawn_wait)
        if not first:
            parts[:, 2] = torch.where(cop, (self.last_gap - gap).clamp(-10.0, 10.0), parts[:, 2])
            self.last_gap = torch.where(cop, gap, self.last_gap)
            wrecked = cop & (car.health <= 0.0)
            gone = cop & (wrecked | (gap > self.c["recycle_distance"]))
            parts[:, 5] += wrecked.float()
            runner_rows = torch.arange(self.M, device=dev) * SLOTS
            parts[runner_rows, 4] += wrecked.reshape(self.M, SLOTS).sum(1).float()
            self.stats[7] += wrecked.sum()
            flags[:, 4] = wrecked.float()
            flags[:, 0] = gone.float()
            self._park(gone)
            self.respawn_wait = torch.where(gone, 3.0 + self._rand(self.N) * 5.0, self.respawn_wait)
            r = runner_rows
            speed = torch.sqrt(car.vx[r] ** 2 + car.vz[r] ** 2)
            parts[r, 5] = speed
            self.stats[9] += speed.sum()
            self.stats[10] += float(self.M)
            dead = car.health[r] <= 0.0
            parts[r, 2] += dead.float()
            cops_now = (self.slot > 0) & self.active
            parts[:, 1] += torch.where(cops_now, self._m(dead).float(), 0.0)
            self.stats[1] += dead.sum()
            alive = ~dead
            parts[r, 0] += alive.float()
            timeout = alive & ~self.abort & (self.elapsed >= self.c["match_seconds"])
            parts[r, 7] += timeout.float()
            self.stats[2] += timeout.sum()
            ended = dead | (alive & self.abort) | timeout
            truncated = alive & (self.abort | timeout)
            self.stats[0] += ended.sum()
            self.stats[13] += torch.where(ended, self.elapsed, 0.0).sum()
            end_slots = self._m(ended) & self.active
            flags[:, 0] = torch.where(end_slots, 1.0, flags[:, 0])
            flags[:, 2] = torch.where(end_slots, self._m(truncated).float(), 0.0)
            self._restart(ended)
            self._reinforce(~ended)
        self._update_intel(dt)
        self.stats[12] += self.known.sum()
        obs, priv = self._observe(dt)
        flags[:, 1] = self.active.float()
        flags[:, 3] = (self.active & self.nav_open).float()
        stats = self.stats.cpu().numpy().copy()
        self.stats.zero_()
        if self.torch_out:
            return obs, priv, parts, flags, stats
        return (obs.cpu().numpy(), priv.cpu().numpy(), parts.cpu().numpy(), flags.cpu().numpy(), stats)

    # --- observations (ChaseAgent + ChaseSenses + CopSenses + ChaseNav) -----------------------

    def _observe(self, dt):
        car, dev, R = self.cars, self.device, self.roads
        N, M = self.N, self.M
        obs = torch.zeros(N, OBS_DIM, device=dev)
        priv = torch.zeros(N, PRIV_DIM, device=dev)
        act = self.active
        runner = (self.slot == 0) & act
        cop = (self.slot > 0) & act
        city = car.city
        fx, fz = self._forward()
        rx_, rz_ = car.x.clone(), car.z.clone()
        hx, hz = fx, fz
        right_x, right_z = -fz, fx
        here = torch.stack([car.x, car.z], 1)

        def local(vx, vz):
            return vx * right_x + vz * right_z, vx * fx + vz * fz

        # navigation ticks (ChaseNav.tick) and the runner's GPS / finished escape routes
        rr = torch.arange(M, device=dev) * SLOTS
        reached_goal = runner & (torch.linalg.norm(here - self.goal, dim=1) < 40.0)
        self._pick_goals(reached_goal[::SLOTS])
        done_escape = runner & (self.option != 0) & (torch.linalg.norm(here - self.frozen, dim=1) < 25.0)
        self.option = torch.where(done_escape, 0, self.option)
        self.nav_open = self.nav_countdown <= 0
        self.nav_countdown = torch.where(self.nav_open, NAV_DECISIONS, self.nav_countdown) - 1

        # targets per slot (5 options), cops around the believed runner, runner around itself
        believed = self._believed()
        speed_known = torch.linalg.norm(self.last_vel, dim=1) > 3.0
        rh = torch.where(speed_known[:, None], self.last_vel / torch.linalg.norm(self.last_vel, dim=1).clamp(min=1e-3)[:, None], self.last_fwd)
        cop_targets, cop_valid = self._cop_options(believed, rh)
        run_targets, run_valid = self._runner_options(rr)
        targets = torch.where((self.slot == 0)[:, None, None], run_targets[self.match_index], cop_targets[self.match_index])
        valid = torch.where((self.slot == 0)[:, None], run_valid[self.match_index], cop_valid[self.match_index])
        self._targets_cache = targets
        # where each car is driving now
        current = targets.gather(1, self.option[:, None, None].expand(-1, 1, 2)).squeeze(1)
        current = torch.where(((self.slot == 0) & (self.option != 0))[:, None], self.frozen, current)
        # road distances to every option, only when choosing
        measure = act & self.nav_open
        if True:
            for k in range(OPTIONS):
                back = (self.slot == 0) & (k == 4)
                length = R.route_length(city, car.x, car.z, torch.where(back, -hx, hx), torch.where(back, -hz, hz),
                                        targets[:, k, 0], targets[:, k, 1])
                self.drive_len[:, k] = torch.where(measure, length, self.drive_len[:, k])
        # route toward the current target (fresh each decision, so progress is 0)
        back = (self.slot == 0) & (self.option == 4)
        pts, cnt = R.route(city, car.x, car.z, torch.where(back, -hx, hx), torch.where(back, -hz, hz), current[:, 0], current[:, 1])
        ahead = torch.tensor(self.c["path_ahead"] + [self.c["goal_ahead"]], device=dev)
        along = R.points_along(pts, cnt, ahead)

        # --- school senses (61) ---
        yaw_rate = torch.where(self.has_yaw, wrap_angle(car.yaw - self.last_yaw) / dt, 0.0)
        self.last_yaw, self.has_yaw = car.yaw.clone(), self.has_yaw | act
        vf_r, vf_f = local(car.vx, car.vz)
        obs[:, 0] = vf_f / 40.0
        obs[:, 1] = vf_r / 20.0
        obs[:, 2] = (yaw_rate / 3.0).clamp(-2.0, 2.0)
        obs[:, 3] = car.slip.clamp(-1.5, 1.5)
        obs[:, 4] = car.steer
        obs[:, 5] = car.drifting
        obs[:, 6] = 1.0
        obs[:, 7] = car.max_speed / 40.0
        rng = self.c["ray_range"]
        rads = torch.tensor([math.radians(d) for d in self.c["wall_rays"]], device=dev)
        rdx = fx[:, None] * torch.cos(rads) + right_x[:, None] * torch.sin(rads)
        rdz = fz[:, None] * torch.cos(rads) + right_z[:, None] * torch.sin(rads)
        k_rays = len(self.c["wall_rays"])
        hits = self.cities.raycast(city[:, None].expand(-1, k_rays).reshape(-1), car.x[:, None].expand(-1, k_rays).reshape(-1),
                                   car.z[:, None].expand(-1, k_rays).reshape(-1), rdx.reshape(-1), rdz.reshape(-1), rng)
        obs[:, 8:8 + k_rays] = hits.reshape(N, k_rays) / rng
        obs[:, 26:36] = self._car_rays(fx, fz, right_x, right_z) / rng
        for k in range(6):
            lx, lz = local(along[:, k, 0] - car.x, along[:, k, 1] - car.z)
            obs[:, 36 + 2 * k] = (lx / rng).clamp(-2.0, 2.0)
            obs[:, 37 + 2 * k] = (lz / rng).clamp(-2.0, 2.0)
        gx, gz = local(along[:, 6, 0] - car.x, along[:, 6, 1] - car.z)
        obs[:, 48] = (gx / 100.0).clamp(-2.0, 2.0)
        obs[:, 49] = (gz / 100.0).clamp(-2.0, 2.0)
        obs[:, 52] = (torch.sqrt((along[:, 6, 0] - car.x) ** 2 + (along[:, 6, 1] - car.z) ** 2) / 150.0).clamp(0.0, 2.0)
        others = self._match_view()  # (N, 6) distances to the cars of the same chase, inf if not there
        near2 = others.topk(2, dim=1, largest=False)
        for k in range(2):
            j = near2.indices[:, k] + self.match_index * SLOTS
            ok = torch.isfinite(near2.values[:, k])
            ox, oz = local(car.x[j] - car.x, car.z[j] - car.z)
            cx, cz = local(car.vx[j] - car.vx, car.vz[j] - car.vz)
            base = 53 + 4 * k
            obs[:, base] = torch.where(ok, (ox / 50.0).clamp(-2.0, 2.0), 0.0)
            obs[:, base + 1] = torch.where(ok, (oz / 50.0).clamp(-2.0, 2.0), 2.0)
            obs[:, base + 2] = torch.where(ok, (cx / 40.0).clamp(-2.0, 2.0), 0.0)
            obs[:, base + 3] = torch.where(ok, (cz / 40.0).clamp(-2.0, 2.0), 0.0)

        # --- navigation features (31) and junction features (13), for both roles ---
        nav = torch.zeros(N, 31, device=dev)
        for k in range(OPTIONS):
            ox, oz = local(targets[:, k, 0] - car.x, targets[:, k, 1] - car.z)
            nav[:, 5 * k] = (ox / 100.0).clamp(-3.0, 3.0)
            nav[:, 5 * k + 1] = (oz / 100.0).clamp(-3.0, 3.0)
            nav[:, 5 * k + 2] = (self.drive_len[:, k] / 300.0).clamp(0.0, 3.0)
            nav[:, 5 * k + 4] = valid[:, k].float()
        # other side's distance to each option: the runner (believed) for cops, cops within 160 m for the runner
        bel = believed[self.match_index]
        cop_dist = torch.linalg.norm(targets - bel[:, None, :], dim=2)
        cars_xy = here.reshape(M, SLOTS, 2)
        cop_xy = cars_xy[:, 1:][self.match_index]
        cop_ok = act.reshape(M, SLOTS)[:, 1:][self.match_index] & (torch.linalg.norm(cop_xy - here[:, None, :], dim=2) <= self.c["runner_sense"])
        d_run = torch.linalg.norm(targets[:, :, None, :] - cop_xy[:, None, :, :], dim=3)
        d_run = torch.where(cop_ok[:, None, :], d_run, 900.0).min(2).values
        other = torch.where((self.slot == 0)[:, None], d_run, cop_dist)
        nav[:, 3:25:5] = (other / 300.0).clamp(0.0, 3.0)
        nav[torch.arange(N, device=dev), 25 + self.option] = 1.0
        nav[:, 30] = self.nav_open.float()
        junction = self._junction_features(city, car.x, car.z, fx, fz)

        # --- cop block ---
        seen_x, seen_z = local(self.last_pos[self.match_index, 0] - car.x, self.last_pos[self.match_index, 1] - car.z)
        mot_x, mot_z = local(self.last_vel[self.match_index, 0], self.last_vel[self.match_index, 1])
        fac_x, fac_z = local(self.last_fwd[self.match_index, 0], self.last_fwd[self.match_index, 1])
        cb = torch.zeros(N, 13, device=dev)
        cb[:, 0], cb[:, 1] = (seen_x / 100.0).clamp(-3, 3), (seen_z / 100.0).clamp(-3, 3)
        cb[:, 2], cb[:, 3] = (mot_x / 40.0).clamp(-2, 2), (mot_z / 40.0).clamp(-2, 2)
        cb[:, 4], cb[:, 5] = fac_x, fac_z
        cb[:, 6] = (torch.linalg.norm(self.last_vel, dim=1) / 40.0).clamp(0, 2)[self.match_index]
        cb[:, 7] = (torch.sqrt(seen_x ** 2 + seen_z ** 2) / 150.0).clamp(0, 3)
        cb[:, 8] = self.sees.float()
        cb[:, 9] = self.known.float()[self.match_index]
        cb[:, 10] = (self.age / self.c["ping_seconds"]).clamp(0, 1)[self.match_index]
        rh_ = car.health[::SLOTS] / car.c_max_health[::SLOTS]
        cb[:, 11] = rh_[self.match_index]
        boost_state = torch.where(car.boost_phase[::SLOTS] == BOOSTING, 1.0, torch.where(car.boost_phase[::SLOTS] == CHARGING, 0.5, 0.0))
        cb[:, 12] = torch.where(self.known, boost_state, 0.0)[self.match_index]
        # teammates (nearest 4 other cops)
        mate_d = others.clone()
        mate_d[:, 0] = float("inf")
        mate_d = torch.where((torch.arange(SLOTS, device=dev)[None, :] == self.slot[:, None]), float("inf"), mate_d)
        order = mate_d.argsort(1)[:, :4]
        mates = torch.zeros(N, 32, device=dev)
        team_opts = torch.zeros(N, 20, device=dev)
        for k in range(4):
            j = order[:, k] + self.match_index * SLOTS
            ok = torch.isfinite(mate_d.gather(1, order[:, k:k + 1]).squeeze(1))
            ox, oz = local(car.x[j] - car.x, car.z[j] - car.z)
            vx, vz = local(car.vx[j], car.vz[j])
            jx, jz = self._forward(car.yaw[j])
            hx2, hz2 = local(jx, jz)
            extra = (torch.linalg.norm(here[j] - bel, dim=1) / 150.0).clamp(0, 3)
            row = torch.stack([(ox / 100).clamp(-2, 2), (oz / 100).clamp(-2, 2), (vx / 40).clamp(-2, 2), (vz / 40).clamp(-2, 2),
                               hx2, hz2, extra, torch.ones_like(extra)], 1)
            mates[:, 8 * k:8 * k + 8] = torch.where(ok[:, None], row, 0.0)
            team_opts[torch.arange(N, device=dev), 5 * k + self.option[j]] = torch.where(ok, 1.0, 0.0)
        team_size = act.reshape(M, SLOTS)[:, 1:].sum(1)[self.match_index]
        my_gap = torch.linalg.norm(here - bel, dim=1)
        mates_bel = torch.linalg.norm(cop_xy - bel[:, None, :], dim=2)
        mate_ok = act.reshape(M, SLOTS)[:, 1:][self.match_index] & (torch.arange(1, SLOTS, device=dev)[None, :] != self.slot[:, None])
        rank = ((mates_bel < my_gap[:, None]) & mate_ok).sum(1).clamp(max=4).float() / 4.0
        ctx = torch.stack([team_size.clamp(max=5).float() / 5.0, car.health / car.c_max_health,
                           self._burst_readiness(), (self.burst_left > 0.0).float()], 1)
        cop_obs = torch.cat([obs[:, :61], cb, mates, ctx, nav, junction, team_opts,
                             rank[:, None], (self.delay.float() / self.data["physics_hz"] / 0.25)[:, None]], 1)

        # --- runner block ---
        rd = torch.linalg.norm(cop_xy - here[:, None, :], dim=2)
        rd = torch.where(cop_ok, rd, float("inf"))
        rorder = rd.argsort(1)
        rb = torch.zeros(N, 54, device=dev)
        for k in range(5):
            j = rorder[:, k] + 1 + self.match_index * SLOTS
            dist = rd.gather(1, rorder[:, k:k + 1]).squeeze(1)
            ok = torch.isfinite(dist)
            ox, oz = local(car.x[j] - car.x, car.z[j] - car.z)
            vx, vz = local(car.vx[j], car.vz[j])
            jx, jz = self._forward(car.yaw[j])
            hx2, hz2 = local(jx, jz)
            row = torch.stack([(ox / 100).clamp(-2, 2), (oz / 100).clamp(-2, 2), (vx / 40).clamp(-2, 2), (vz / 40).clamp(-2, 2),
                               hx2, hz2, dist.clamp(max=1e6) / 150.0, (self.burst_left[j] > 0).float(), torch.ones_like(dist)], 1)
            rb[:, 9 * k:9 * k + 9] = torch.where(ok[:, None], row, 0.0)
        near_count = torch.isfinite(rd).sum(1)
        ratio = (car.boost_charge / car.c_boost_max_charge.clamp(min=0.01)).clamp(0, 1)
        rctx = torch.stack([car.health / car.c_max_health, (car.boost_phase == CHARGING).float(), ratio,
                            (car.boost_phase == BOOSTING).float(), near_count.clamp(max=5).float() / 5.0,
                            self.known.float()[self.match_index]], 1)
        runner_obs = torch.cat([obs[:, :61], rb, rctx, nav, junction, torch.zeros(N, OBS_DIM - RUNNER_OBS, device=dev)], 1)
        out = torch.where((self.slot == 0)[:, None], runner_obs, cop_obs)
        out = torch.where(act[:, None], out, 0.0)

        # --- privileged facts ---
        time_left = (1.0 - (self.elapsed / self.c["match_seconds"]).clamp(0, 1))[self.match_index]
        rgap = torch.linalg.norm(cop_xy - torch.stack([rx_[::SLOTS], rz_[::SLOTS]], 1)[self.match_index][:, None, :], dim=2)
        rgap = torch.where(act.reshape(M, SLOTS)[:, 1:][self.match_index], rgap, float("inf"))
        sorted_gap = rgap.sort(1).values
        cops_n = act.reshape(M, SLOTS)[:, 1:].sum(1)[self.match_index].float()
        pending = (self.target_cops[self.match_index].float() - cops_n).clamp(min=0) / 5.0
        cop_speed = torch.sqrt(car.vx ** 2 + car.vz ** 2).reshape(M, SLOTS)[:, 1:]
        cop_speed = torch.where(act.reshape(M, SLOTS)[:, 1:], cop_speed, 0.0).sum(1)[self.match_index] / cops_n.clamp(min=1)
        any_burst = ((self.burst_left > 0) & act).reshape(M, SLOTS)[:, 1:].any(1)[self.match_index].float()
        g0 = torch.where(torch.isfinite(sorted_gap[:, 0]), (sorted_gap[:, 0] / 150).clamp(0, 3), 3.0)
        g1 = torch.where(torch.isfinite(sorted_gap[:, 1]), (sorted_gap[:, 1] / 150).clamp(0, 3), 3.0)
        near50 = (rgap < 50.0).sum(1).float()
        rpriv = torch.stack([time_left, cops_n / 5, g0, g1, self.known.float()[self.match_index],
                             (self.age / self.c["ping_seconds"]).clamp(0, 1)[self.match_index], rh_[self.match_index],
                             near50 / 5, cop_speed / 40, (self.minute / 15)[self.match_index], pending, any_burst], 1)
        tx, tz = local(self._m(rx_[::SLOTS]) - car.x, self._m(rz_[::SLOTS]) - car.z)
        mvx, mvz = local(self._m(car.vx[::SLOTS]), self._m(car.vz[::SLOTS]))
        best = torch.where(torch.isfinite(sorted_gap[:, 0]), sorted_gap[:, 0], 999.0)
        cpriv = torch.stack([(tx / 100).clamp(-3, 3), (tz / 100).clamp(-3, 3), mvx / 40, mvz / 40,
                             (torch.sqrt(tx ** 2 + tz ** 2) / 150).clamp(0, 3), rh_[self.match_index],
                             self.known.float()[self.match_index], time_left, (best / 150).clamp(0, 3), cops_n / 5,
                             boost_state[self.match_index], pending], 1)
        priv = torch.where((self.slot == 0)[:, None], rpriv, cpriv)
        priv = torch.where(act[:, None], priv, 0.0)
        self.stats[11] += cops_n[::SLOTS].sum()
        self.stats[14] += torch.where(act & (self.slot > 0), torch.sqrt(car.vx ** 2 + car.vz ** 2), 0.0).sum()
        return out, priv

    def _burst_readiness(self):
        ready = 1.0 - (self.burst_wait / self.burst_cooldown.clamp(min=0.01)).clamp(0, 1)
        return torch.where(self.burst_left > 0.0, 0.0, ready)

    def _match_view(self):
        """Distance from every car to each car of its chase (N, 6); inf for itself and inactive cars."""
        car = self.cars
        xy = torch.stack([car.x, car.z], 1).reshape(self.M, SLOTS, 2)[self.match_index]
        d = torch.linalg.norm(xy - torch.stack([car.x, car.z], 1)[:, None, :], dim=2)
        ok = self.active.reshape(self.M, SLOTS)[self.match_index] & (torch.arange(SLOTS, device=self.device)[None, :] != self.slot[:, None])
        return torch.where(ok, d, float("inf"))

    def _car_rays(self, fx, fz, rx, rz):
        """CopSenses car rays: distance along each of 10 rays to the other cars of the chase (boxes)."""
        car = self.cars
        rng = self.c["ray_range"]
        xy = torch.stack([car.x, car.z], 1).reshape(self.M, SLOTS, 2)[self.match_index]
        yaw = car.yaw.reshape(self.M, SLOTS)[self.match_index]
        hw = (car.c_width * 0.5).reshape(self.M, SLOTS)[self.match_index]
        hl = (car.c_length * 0.5).reshape(self.M, SLOTS)[self.match_index]
        ok = self.active.reshape(self.M, SLOTS)[self.match_index] & (torch.arange(SLOTS, device=self.device)[None, :] != self.slot[:, None])
        bfx, bfz = -torch.sin(yaw), -torch.cos(yaw)
        brx, brz = -bfz, bfx
        out = torch.full((self.N, len(self.c["car_rays"])), rng, device=self.device)
        ox = car.x[:, None] - xy[:, :, 0]
        oz = car.z[:, None] - xy[:, :, 1]
        lo_r, lo_f = ox * brx + oz * brz, ox * bfx + oz * bfz
        for k, deg in enumerate(self.c["car_rays"]):
            rad = math.radians(deg)
            dx, dz = fx * math.cos(rad) + rx * math.sin(rad), fz * math.cos(rad) + rz * math.sin(rad)
            ld_r = dx[:, None] * brx + dz[:, None] * brz
            ld_f = dx[:, None] * bfx + dz[:, None] * bfz
            inv_r = 1.0 / torch.where(ld_r.abs() < 1e-6, torch.full_like(ld_r, 1e-6), ld_r)
            inv_f = 1.0 / torch.where(ld_f.abs() < 1e-6, torch.full_like(ld_f, 1e-6), ld_f)
            t1, t2 = (-hw - lo_r) * inv_r, (hw - lo_r) * inv_r
            t3, t4 = (-hl - lo_f) * inv_f, (hl - lo_f) * inv_f
            tmin = torch.maximum(torch.minimum(t1, t2), torch.minimum(t3, t4))
            tmax = torch.minimum(torch.maximum(t1, t2), torch.maximum(t3, t4))
            hit = ok & (tmax >= tmin) & (tmin >= 0.0) & (tmin <= rng)
            out[:, k] = torch.where(hit, tmin, rng).min(1).values
        return out

    def _junction_features(self, city, x, z, fx, fz):
        R = self.roads
        node, came, distance = R.next_junction(city, x, z, fx, fz)
        turns, _, _, _, valid = R.exits(city, node, came)
        out = torch.zeros(self.N, 13, device=self.device)
        out[:, 0] = (distance / 100.0).clamp(0.0, 3.0)
        for k in range(4):
            ok = valid[:, k]
            out[:, 1 + 3 * k] = torch.where(ok, torch.sin(turns[:, k]), 0.0)
            out[:, 2 + 3 * k] = torch.where(ok, torch.cos(turns[:, k]), 0.0)
            out[:, 3 + 3 * k] = ok.float()
        return out

    def _sides(self, city, node, came):
        """Straightest, leftmost and rightmost exits of a junction: (end node, first neighbour, length, ok)."""
        R = self.roads
        turns, ends, lengths, firsts, valid = R.exits(city, node, came)
        absturn = torch.where(valid, turns.abs(), 9.0)
        straight_k = absturn.argmin(1)
        straight_ok = absturn.gather(1, straight_k[:, None]).squeeze(1) < 0.6
        left_ok = valid[:, 0] & (turns[:, 0] < -0.5)
        last = valid.sum(1) - 1
        right_turn = turns.gather(1, last.clamp(min=0)[:, None]).squeeze(1)
        right_ok = (last >= 0) & (right_turn > 0.5)
        pick = lambda t, k: t.gather(1, k[:, None]).squeeze(1)
        return ((pick(ends, straight_k), straight_ok),
                (ends[:, 0], firsts[:, 0], lengths[:, 0], left_ok),
                (pick(ends, last.clamp(min=0)), pick(firsts, last.clamp(min=0)), pick(lengths, last.clamp(min=0)), right_ok))

    def _along_exit(self, city, node, first, end, length, metres):
        R = self.roads
        start, nxt, far = R.node_xy(city, node), R.node_xy(city, first), R.node_xy(city, end)
        seg = torch.linalg.norm(nxt - start, dim=1)
        direct = start + (nxt - start) / seg.clamp(min=1e-3)[:, None] * metres
        return torch.where((seg >= metres)[:, None], direct, torch.where((length <= metres)[:, None], far, nxt))

    def _cop_options(self, believed, heading):
        """ChaseNav.update_cop_targets for each chase."""
        city = self.city_of_match
        R = self.roads
        node, came, _ = R.next_junction(city, believed[:, 0], believed[:, 1], heading[:, 0], heading[:, 1])
        at = R.node_xy(city, node)
        (s_end, s_ok), (l_end, l_first, l_len, l_ok), (r_end, r_first, r_len, r_ok) = self._sides(city, node, came)
        targets = torch.stack([believed, at, torch.where(s_ok[:, None], R.node_xy(city, s_end), at),
                               torch.where(l_ok[:, None], self._along_exit(city, node, l_first, l_end, l_len, self.c["exit_cover"]), at),
                               torch.where(r_ok[:, None], self._along_exit(city, node, r_first, r_end, r_len, self.c["exit_cover"]), at)], 1)
        valid = torch.stack([torch.ones_like(s_ok), torch.ones_like(s_ok), s_ok, l_ok, r_ok], 1)
        return targets, valid

    def _runner_options(self, rows):
        """ChaseNav.update_runner_targets for each chase's runner."""
        car, R = self.cars, self.roads
        city = self.city_of_match
        x, z = car.x[rows], car.z[rows]
        fx, fz = self._forward(car.yaw[rows])
        goal = self.goal[rows]
        behind, _, _ = R.next_junction(city, x, z, -fx, -fz)
        node, came, _ = R.next_junction(city, x, z, fx, fz)
        at = R.node_xy(city, node)
        (s_end, s_ok), (l_end, _, _, l_ok), (r_end, _, _, r_ok) = self._sides(city, node, came)
        targets = torch.stack([goal, torch.where(s_ok[:, None], R.node_xy(city, s_end), at),
                               torch.where(l_ok[:, None], R.node_xy(city, l_end), at),
                               torch.where(r_ok[:, None], R.node_xy(city, r_end), at), R.node_xy(city, behind)], 1)
        valid = torch.stack([torch.ones_like(s_ok), s_ok, l_ok, r_ok, torch.ones_like(s_ok)], 1)
        return targets, valid
