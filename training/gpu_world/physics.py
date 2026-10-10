"""Batched car physics for the GPU training world: a line-by-line port of the game's car
(scripts/review/lab_vehicle.gd on top of scripts/vehicles/arcade_vehicle.gd and charge_boost.gd),
running thousands of cars at once as PyTorch tensors (CPU or CUDA).

Coordinates are the game's ground plane: x and z (here "y" of 2D vectors = world z). Yaw is Godot's
rotation.y; forward = (-sin yaw, -cos yaw), right = (cos yaw, -sin yaw).

What is approximated (checked against the real game by training/gpu_world/parity.py):
* the car body is three circles along its length (rounded box) moving in 2D;
* city collision uses a signed distance field rasterised from the real city (training/gpu_world/city.py);
* move_and_slide becomes "move, push out of walls, slide along them";
* cars that touch are separated half each way, then the game's crash formula runs.
Heights, curbs, jumps and airborne steering are left out (jumping is off in the lab).
"""

import json
import math

import torch

READY, CHARGING, BOOSTING = 0, 1, 2


def move_toward(value, target, step):
    return torch.where((target - value).abs() <= step, target, value + torch.sign(target - value) * step)


def lerp(a, b, t):
    return a + (b - a) * t


def wrap_angle(a):
    return torch.remainder(a + math.pi, 2.0 * math.pi) - math.pi


class CarSpec:
    """Per-car constants (runner or cop), from cars.json exported by tools/export_gpu_world.gd."""

    def __init__(self, data, role, lab, device):
        t, h = data[role]["tuning"], data[role]["handling"]
        self.values = {
            "max_speed": t["maximum_speed_mps"], "reverse": t["reverse_speed_mps"], "accel": t["acceleration_mps2"],
            "braking": t["braking_mps2"], "coast": t["coasting_drag_mps2"], "handbrake_grip": t["handbrake_grip"],
            "boost_max_charge": t["boost_max_charge_seconds"], "boost_min_speed": t["boost_min_speed_mps"],
            "boost_max_speed": t["boost_max_speed_mps"], "boost_min_duration": t["boost_min_duration_seconds"],
            "boost_max_duration": t["boost_max_duration_seconds"],
            "steer_low": h["steer_low_speed"], "steer_top": h["steer_top_speed"], "steer_boost": h["steer_boost_speed"],
            "steer_response": h["steer_response"], "grip": h["grip"], "drift_grip": h["drift_grip"],
            "drift_steer_boost": h["drift_steer_boost"], "drift_max_angle": math.radians(h["drift_max_angle"]),
            "drift_speed_loss": h["drift_speed_loss"], "drift_exit_kick": h["drift_exit_kick"],
            "drift_min_speed": h["drift_min_speed"], "wall_glance_keep": h["wall_glance_keep"],
            "wall_head_on_keep": h["wall_head_on_keep"], "wall_align": h["wall_align"],
            "mass": data[role]["mass"], "max_health": data[role]["max_health"],
            "width": data[role]["box"][0], "length": data[role]["box"][1]}


class Cars:
    """State of N cars. `specs` is a list of CarSpec and `kind` a length-N tensor of indexes into it."""

    FIELDS = ["x", "z", "yaw", "vx", "vz", "fwd", "steer", "drifting", "drift_time", "grip_return", "spin",
              "stagger", "health", "wall_contact", "boost_phase", "boost_charge", "boost_power", "boost_duration",
              "boost_elapsed", "boost_fired", "slip", "max_speed", "prev_x", "prev_z", "prev_yaw"]

    def __init__(self, n, specs, kind, lab, device="cpu", dtype=torch.float32):
        self.n, self.device, self.dtype = n, device, dtype
        self.lab = lab
        self.kind = kind.to(device)
        for name in self.FIELDS:
            setattr(self, name, torch.zeros(n, device=device, dtype=dtype))
        # Per-car constants gathered from the specs.
        for key in specs[0].values:
            table = torch.tensor([s.values[key] for s in specs], device=device, dtype=dtype)
            setattr(self, "c_" + key, table[self.kind])
        self.max_speed = self.c_max_speed.clone()
        self.health = self.c_max_health.clone()
        self.radius = self.c_width * 0.5
        self.offset = (self.c_length * 0.5 - self.radius).clamp(min=0.0)
        self.pair_cooldown = None

    # --- game car step -------------------------------------------------------------------------

    def step(self, throttle, steering, handbrake, hold_boost, enabled, city, dt, cars_per_group=None):
        """One physics frame (dt = 1/60). Controls are tensors of length N; handbrake/hold_boost/enabled bool.
        Returns per-car wall damage and the crash events (for rewards)."""
        self.prev_x, self.prev_z, self.prev_yaw = self.x.clone(), self.z.clone(), self.yaw.clone()
        hb = handbrake & enabled
        drive = torch.where(enabled, throttle, torch.zeros_like(throttle))
        speed_abs = self.fwd.abs()
        self._update_drift(dt, speed_abs, hb, steering, enabled)
        handbrake_braking = hb & (self.drifting < 0.5)
        self._boost_tick(dt, hold_boost, enabled, (drive < -0.1) | handbrake_braking)

        target = drive * torch.where(drive >= 0.0, self.max_speed, self.c_reverse)
        rate = self.c_accel.clone()
        zero = drive == 0.0
        rate = torch.where(zero, self.c_coast, rate)
        opposing = (~zero) & (torch.sign(drive) != torch.sign(self.fwd)) & (self.fwd.abs() > 0.5)
        rate = torch.where(opposing, self.c_braking, rate)
        target = torch.where(handbrake_braking, target * 0.7, target)
        charging = self.boost_phase == CHARGING
        boosting = self.boost_phase == BOOSTING
        ratio = (self.boost_charge / self.c_boost_max_charge.clamp(min=0.01)).clamp(0.0, 1.0)
        target = torch.where(charging, target * lerp(0.72, 0.36, ratio), target)
        rate = torch.where(charging, rate.clamp(min=10.0), rate)
        limit = lerp(self.c_boost_min_speed, self.c_boost_max_speed, self.boost_power)
        target = torch.where(boosting, limit, target)
        fired = boosting & (self.boost_fired > 0.5)
        self.fwd = torch.where(fired, torch.maximum(self.fwd, limit), self.fwd)
        fx, fz = -torch.sin(self.yaw), -torch.cos(self.yaw)
        self.vx = torch.where(fired, fx * self.fwd, self.vx)
        self.vz = torch.where(fired, fz * self.fwd, self.vz)
        over = (~charging) & (~boosting) & (self.fwd > self.max_speed)
        rate = torch.where(over, rate.clamp(min=14.0), rate)
        self.fwd = move_toward(self.fwd, target, rate * dt)
        drifting = self.drifting > 0.5
        self.fwd = torch.where(drifting, move_toward(self.fwd, torch.zeros_like(self.fwd), self.c_drift_speed_loss * dt), self.fwd)

        self._steer_toward(dt, steering, enabled)
        turning = enabled & (self.fwd.abs() > 0.2)
        yaw_rate = self._yaw_rate(self.fwd.abs())
        yaw_rate = torch.where(drifting, yaw_rate * self.c_drift_steer_boost, yaw_rate)
        yaw_rate = torch.where(self.stagger > 0.0, yaw_rate * 0.4, yaw_rate)
        self.yaw = torch.where(turning, self.yaw - self.steer * yaw_rate * torch.sign(self.fwd) * dt, self.yaw)
        spinning = self.spin.abs() > 0.01
        self.yaw = torch.where(spinning, self.yaw + self.spin * dt, self.yaw)
        self.spin = torch.where(spinning, self.spin * math.exp(-self.lab["spin_decay"] * dt), self.spin)
        self.stagger = (self.stagger - dt).clamp(min=0.0)

        fx, fz = -torch.sin(self.yaw), -torch.cos(self.yaw)
        dx, dz = fx * self.fwd, fz * self.fwd
        grip = self._current_grip(dt, hb)
        grip = torch.where(self.stagger > 0.0, torch.minimum(grip, self.c_drift_grip * 1.2), grip)
        blend = (grip * dt).clamp(max=1.0)
        self.vx = lerp(self.vx, dx, blend)
        self.vz = lerp(self.vz, dz, blend)
        self._limit_slip(dx, dz)

        before_x, before_z = self.vx.clone(), self.vz.clone()
        self.x = self.x + self.vx * dt
        self.z = self.z + self.vz * dt
        hit, nx, nz = city.push_out(self)
        return self._resolve_walls(dt, hit, nx, nz, before_x, before_z), (before_x, before_z)

    def _update_drift(self, dt, speed, handbrake, steering, enabled):
        drifting = self.drifting > 0.5
        start = (~drifting) & enabled & handbrake & (speed >= self.c_drift_min_speed) & (steering.abs() > 0.2)
        self.drift_time = torch.where(drifting, self.drift_time + dt, torch.where(start, 0.0, self.drift_time))
        stop = drifting & ((~handbrake) | (~enabled) | (speed < self.c_drift_min_speed * 0.6))
        kick = stop & (self.drift_time > 0.6) & enabled
        self.fwd = torch.where(kick, self.fwd + self.c_drift_exit_kick * torch.sign(self.fwd), self.fwd)
        self.grip_return = torch.where(stop, torch.zeros_like(self.grip_return), self.grip_return)
        self.drifting = torch.where(start, 1.0, torch.where(stop, 0.0, self.drifting))

    def _boost_tick(self, dt, held, enabled, braking):
        self.boost_fired = torch.zeros_like(self.boost_fired)
        clear = (~enabled) | braking
        boosting = self.boost_phase == BOOSTING
        # Boosting: holding again starts a new charge; otherwise the boost runs out.
        restart = boosting & held & ~clear
        run = boosting & ~held & ~clear
        self.boost_elapsed = torch.where(run, self.boost_elapsed + dt, self.boost_elapsed)
        finished = run & (self.boost_duration - self.boost_elapsed <= 0.0)
        self.boost_phase = torch.where(finished, READY, self.boost_phase)
        self.boost_power = torch.where(finished, 0.0, self.boost_power)
        self.boost_phase = torch.where(restart, CHARGING, self.boost_phase)
        for name in ("boost_charge", "boost_power", "boost_duration", "boost_elapsed"):
            setattr(self, name, torch.where(restart, 0.0, getattr(self, name)))
        active = ~clear & ~run
        start = active & (self.boost_phase == READY) & held
        self.boost_phase = torch.where(start, CHARGING, self.boost_phase)
        charging = active & (self.boost_phase == CHARGING)
        keep = charging & held
        self.boost_charge = torch.where(keep, torch.minimum(self.boost_charge + dt, self.c_boost_max_charge), self.boost_charge)
        release = charging & ~held
        fire = release & (self.boost_charge >= 0.12)
        fizzle = release & (self.boost_charge < 0.12)
        ratio = (self.boost_charge / self.c_boost_max_charge.clamp(min=0.01)).clamp(0.0, 1.0)
        power = ratio * ratio * (3.0 - 2.0 * ratio)
        self.boost_power = torch.where(fire, power, self.boost_power)
        self.boost_duration = torch.where(fire, lerp(self.c_boost_min_duration, self.c_boost_max_duration, power), self.boost_duration)
        self.boost_elapsed = torch.where(fire, 0.0, self.boost_elapsed)
        self.boost_phase = torch.where(fire, BOOSTING, torch.where(fizzle, READY, self.boost_phase))
        self.boost_charge = torch.where(fire | fizzle, 0.0, self.boost_charge)
        self.boost_fired = fire.to(self.dtype)
        for name in ("boost_charge", "boost_power", "boost_duration", "boost_elapsed"):
            setattr(self, name, torch.where(clear, 0.0, getattr(self, name)))
        self.boost_phase = torch.where(clear, READY, self.boost_phase)

    def _steer_toward(self, dt, steering, enabled):
        target = torch.where(enabled, steering, torch.zeros_like(steering))
        response = self.c_steer_response.clone()
        faster = (target.abs() < self.steer.abs()) | (torch.sign(target) != torch.sign(self.steer))
        response = torch.where(faster, response * 1.8, response)
        self.steer = move_toward(self.steer, target, response * dt)

    def _yaw_rate(self, speed):
        top = self.max_speed
        low = self.c_steer_low * (speed / 6.0).clamp(0.0, 1.0)
        mid = lerp(self.c_steer_low, self.c_steer_top, (speed - 14.0) / (top - 14.0).clamp(min=0.01))
        boosted = ((speed - top) / (self.c_boost_max_speed - top).clamp(min=0.01)).clamp(0.0, 1.0)
        high = lerp(self.c_steer_top, self.c_steer_boost, boosted)
        return torch.where(speed <= 14.0, low, torch.where(speed <= top, mid, high))

    def _current_grip(self, dt, handbrake):
        drifting = self.drifting > 0.5
        self.grip_return = torch.where(drifting, self.grip_return, move_toward(self.grip_return, torch.ones_like(self.grip_return), torch.full_like(self.grip_return, dt / 0.3)))
        base = torch.where(handbrake, self.c_handbrake_grip, self.c_grip)
        return torch.where(drifting, self.c_drift_grip, lerp(self.c_drift_grip, base, self.grip_return))

    def _limit_slip(self, dx, dz):
        travel = torch.sqrt(self.vx ** 2 + self.vz ** 2)
        heading = torch.sqrt(dx ** 2 + dz ** 2)
        ok = (travel >= 2.0) & (heading >= 2.0)
        slip = torch.atan2(dx * self.vz - dz * self.vx, dx * self.vx + dz * self.vz)
        cap = torch.where(self.stagger > 0.0, torch.full_like(slip, math.radians(80.0)),
                          torch.where(self.drifting > 0.5, self.c_drift_max_angle, torch.full_like(slip, math.radians(25.0))))
        over = ok & (slip.abs() > cap)
        turn = -(slip - torch.sign(slip) * cap)
        c, s = torch.cos(turn), torch.sin(turn)
        rx, rz = self.vx * c - self.vz * s, self.vx * s + self.vz * c
        self.vx = torch.where(over, rx, self.vx)
        self.vz = torch.where(over, rz, self.vz)
        self.slip = torch.where(ok, torch.where(over, torch.sign(slip) * cap, slip), torch.zeros_like(slip))

    def _resolve_walls(self, dt, hit, nx, nz, bx, bz):
        """The game's wall rule: glancing hits keep speed and align the car along the wall, head-on hits
        lose speed; a hit costs speed once, grinding afterwards only drags. Returns wall damage per car."""
        flat = torch.sqrt(bx ** 2 + bz ** 2)
        impact = (-(bx * nx + bz * nz)).clamp(min=0.0)
        worst = (impact / flat.clamp(min=1.0)).clamp(0.0, 1.0)
        fresh = hit & ((self.wall_contact < 0.5) | (worst > 0.6))
        keep = lerp(self.c_wall_glance_keep, self.c_wall_head_on_keep, worst ** 1.5)
        self.fwd = torch.where(fresh, self.fwd * keep, self.fwd)
        damage = torch.where(fresh & (impact > 5.0),
                             ((impact - 5.0) * self.lab["wall_damage_per_mps"]).clamp(max=self.lab["wall_damage_max"]),
                             torch.zeros_like(impact))
        grind = hit & ~fresh
        self.fwd = torch.where(grind, move_toward(self.fwd, torch.zeros_like(self.fwd), torch.full_like(self.fwd, self.lab["wall_drag"] * dt)), self.fwd)
        self.wall_contact = hit.to(self.dtype)
        align = hit & (worst < 0.6) & (self.c_wall_align > 0.0)
        ax, az = -nz, nx
        flip = (ax * bx + az * bz) < 0.0
        ax, az = torch.where(flip, -ax, ax), torch.where(flip, -az, az)
        along_yaw = torch.atan2(-ax, -az)
        along_yaw = torch.where(self.fwd < 0.0, along_yaw + math.pi, along_yaw)
        new_yaw = self.yaw + wrap_angle(along_yaw - self.yaw) * self.c_wall_align
        self.yaw = torch.where(align, new_yaw, self.yaw)
        self.health = (self.health - damage).clamp(min=0.0)
        return damage

    # --- car to car ----------------------------------------------------------------------------

    def circles(self, previous=False):
        """Centres of each car's three body circles: (N, 3) x and z (this frame, or last frame's pose)."""
        x, z, yaw = (self.prev_x, self.prev_z, self.prev_yaw) if previous else (self.x, self.z, self.yaw)
        fx, fz = -torch.sin(yaw), -torch.cos(yaw)
        k = torch.tensor([-1.0, 0.0, 1.0], device=self.device, dtype=self.dtype)
        return (x[:, None] + fx[:, None] * self.offset[:, None] * k,
                z[:, None] + fz[:, None] * self.offset[:, None] * k)

    def crashes(self, pairs, before, frame, mask=None):
        """Touching pairs (P, 2 index tensor) are separated and run the game's crash formula
        (LabVehicle.crash / take_hit). Returns car-hit damage per car and per pair (for credit)."""
        n = self.n
        damage = torch.zeros(n, device=self.device, dtype=self.dtype)
        if pairs.numel() == 0:
            return damage, torch.zeros(0, 2, device=self.device, dtype=self.dtype)
        a, b = pairs[:, 0], pairs[:, 1]
        cx, cz = self.circles()
        ox, oz = self.circles(previous=True)
        reach = self.radius[a] + self.radius[b]

        def closest(axs, azs, bxs, bzs):
            dx = axs[a][:, :, None] - bxs[b][:, None, :]
            dz = azs[a][:, :, None] - bzs[b][:, None, :]
            dist = torch.sqrt(dx ** 2 + dz ** 2).reshape(len(a), 9)
            best = dist.argmin(1)
            i, j = best // 3, best % 3
            return (dist.gather(1, best[:, None]).squeeze(1),
                    axs[a].gather(1, i[:, None]).squeeze(1), azs[a].gather(1, i[:, None]).squeeze(1),
                    bxs[b].gather(1, j[:, None]).squeeze(1), bzs[b].gather(1, j[:, None]).squeeze(1))

        # Godot moves cars one after another, so a car runs into where the other one was a frame ago
        # (it has not moved yet this frame): a pair touches if either car's new pose meets the other's
        # old pose, not only when both new poses overlap.
        gap, ax_, az_, bx_, bz_ = closest(cx, cz, cx, cz)
        for candidate in (closest(cx, cz, ox, oz), closest(ox, oz, cx, cz)):
            better = candidate[0] < gap
            gap, ax_, az_, bx_, bz_ = (torch.where(better, c, g) for c, g in zip(candidate, (gap, ax_, az_, bx_, bz_)))
        touching = gap < reach
        if mask is not None:
            touching = touching & mask
        nx, nz = (ax_ - bx_) / gap.clamp(min=1e-4), (az_ - bz_) / gap.clamp(min=1e-4)
        now_gap = closest(cx, cz, cx, cz)[0]
        push = ((reach - now_gap) * 0.5).clamp(min=0.0) * touching
        self.x.index_add_(0, a, nx * push)
        self.z.index_add_(0, a, nz * push)
        self.x.index_add_(0, b, -nx * push)
        self.z.index_add_(0, b, -nz * push)
        # Godot's physics reports a box-on-box contact at a corner of the touching faces, not the middle, so
        # even a straight rear-end hit spins both cars (about half the car's width of lever). Put the contact
        # point there, on the side the cars are offset to (a random side when they are dead in line).
        tx, tz = -nz, nx
        side = torch.sign((self.x[a] - self.x[b]) * tx + (self.z[a] - self.z[b]) * tz)
        side = torch.where(side == 0.0, torch.where(torch.rand_like(side) < 0.5, -1.0, 1.0), side)
        corner = torch.minimum(self.radius[a], self.radius[b]) * side
        px = (ax_ + bx_) * 0.5 + tx * corner
        pz = (az_ + bz_) * 0.5 + tz * corner
        bvx, bvz = before
        closing = -((bvx[a] - bvx[b]) * nx + (bvz[a] - bvz[b]) * nz)
        if self.pair_cooldown is None or self.pair_cooldown.shape[0] != len(a):
            self.pair_cooldown = torch.full((len(a),), -1000, device=self.device, dtype=torch.long)
        ready = (frame - self.pair_cooldown) >= self.lab["pair_cooldown_frames"]
        crash = touching & ready & (closing >= 1.0)
        self.pair_cooldown = torch.where(crash, torch.full_like(self.pair_cooldown, frame), self.pair_cooldown)
        mass_a = self._effective_mass(a, -nx, -nz)
        mass_b = self._effective_mass(b, nx, nz)
        strength = closing * self.lab["crash_push"] * crash
        hard = (closing - self.lab["car_damage_threshold"]).clamp(min=0.0) * crash
        total = mass_a + mass_b
        hit_a = self._take_hit(a, nx * strength * mass_b / total, nz * strength * mass_b / total, px, pz, hard * mass_b, crash)
        hit_b = self._take_hit(b, -nx * strength * mass_a / total, -nz * strength * mass_a / total, px, pz, hard * mass_a, crash)
        damage.index_add_(0, a, hit_a)
        damage.index_add_(0, b, hit_b)
        return damage, torch.stack([hit_a, hit_b], 1)

    def _effective_mass(self, idx, tx, tz):
        weight = self.c_mass[idx].clone()
        fx, fz = -torch.sin(self.yaw[idx]), -torch.cos(self.yaw[idx])
        nose = (self.boost_phase[idx] == BOOSTING) & ((fx * tx + fz * tz) > 0.5)
        weight = torch.where(nose, weight * self.lab["boost_mass"], weight)
        return torch.where(self.stagger[idx] > 0.0, weight * 0.7, weight)

    def _take_hit(self, idx, cx, cz, px, pz, force, crash):
        cx, cz = cx * crash, cz * crash
        self.vx.index_add_(0, idx, cx)
        self.vz.index_add_(0, idx, cz)
        fx, fz = -torch.sin(self.yaw[idx]), -torch.cos(self.yaw[idx])
        self.fwd.index_add_(0, idx, cx * fx + cz * fz)
        strength = torch.sqrt(cx ** 2 + cz ** 2)
        stagger = torch.where(strength > 4.0, (strength / 20.0).clamp(0.25, 0.9), torch.zeros_like(strength))
        self.stagger.scatter_reduce_(0, idx, stagger, "amax", include_self=True)
        lx, lz = px - self.x[idx], pz - self.z[idx]
        spin = (lz * cx - lx * cz) * self.lab["spin_gain"]
        self.spin.index_add_(0, idx, spin)
        self.spin.clamp_(-6.0, 6.0)
        damage = torch.where(force > 0.0, (force * self.lab["car_damage_per_hit"]).clamp(max=self.lab["car_damage_max"]),
                             torch.zeros_like(force))
        self.health.index_add_(0, idx, -damage)
        self.health.clamp_(min=0.0)
        return damage


def load_specs(path, device="cpu"):
    with open(path) as handle:
        data = json.load(handle)
    lab = data["lab_vehicle"]
    return data, [CarSpec(data, "runner", lab, device), CarSpec(data, "cop", lab, device)], lab
