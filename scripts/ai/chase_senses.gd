class_name ChaseSenses
extends RefCounted
## What a cop or the runner sees in a chase (learned cops vs a learned runner). Both start with the
## driving-school senses (CopSenses, 61 numbers) so a school-trained brain carries over, then add the
## chase. Training and the game build it here, so a brain sees the same thing in both.
##
## Cop (154): school senses, with the road route to the navigation target it chose, then
## 13  the runner as the team knows it: last seen position, velocity and heading, speed, distance,
##     whether this cop sees it, whether anyone does, how long ago it was seen, its health, boosting
## 32  up to 4 teammates, nearest first: position, velocity, heading, their distance to the runner, present
##  4  team size, own health, burst ready, bursting
## 31  navigation options (scripts/ai/chase_nav.gd)
## 13  the next junction on its own road: distance, then up to 4 exits left to right (turn sin/cos, present)
## 20  the 4 teammate slots' current navigation choices (one-hot each, same order as the teammates above)
##  1  this cop's rank by distance to the runner within the squad (0 = closest, /4)
##  1  its reaction delay (seconds / 0.25): how late its controls land, so it can plan for it
##
## Runner (165): school senses, with the road route to the navigation target it chose, then
## 54  up to 6 cops within 160 m, nearest first: position, velocity, heading, distance, bursting, present
##  6  own health, boost charging, charge, boosting, cops nearby, spotted by the cops right now
## 31  navigation options
## 13  the next junction on its own road
##
## Brain answers are handled by ChaseAgent (scripts/ai/chase_agent.gd).

const COP_OBS: int = 176
const RUNNER_OBS: int = 165
const OBS_DIM: int = 176
const ACT_DIM: int = 5
const JUNCTION_FEATURES: int = 13
const TEAM_SLOTS: int = 4
const COP_SLOTS: int = 6
const RUNNER_SENSE: float = 160.0
const GOAL_AHEAD: float = 80.0

var car: LabVehicle
var school := CopSenses.new()
var _here := Vector2.ZERO
var _forward := Vector2(0.0, -1.0)
var _right := Vector2(1.0, 0.0)


func setup(vehicle: LabVehicle, car_mask: int) -> void:
	car = vehicle
	school.car = vehicle
	school.car_mask = car_mask


func reset() -> void:
	school.reset()


func observe_cop(route: RouteTrack, progress: float, cars: Array, dt: float, intel: ChaseIntel, sees: bool,
		runner: LabVehicle, team: Array, team_size: int, burst: CopBurst, nav: RoadNav,
		navigation: PackedFloat32Array, team_options: Dictionary, delay_seconds: float) -> PackedFloat32Array:
	var obs: PackedFloat32Array = _school(route, progress, cars, dt)
	var i: int = CopSenses.OBS_DIM
	var seen: Vector2 = _local(intel.last_position - _here)
	var motion: Vector2 = _local(intel.last_velocity)
	var facing: Vector2 = _local(intel.last_forward)
	obs[i] = clampf(seen.x / 100.0, -3.0, 3.0)
	obs[i + 1] = clampf(seen.y / 100.0, -3.0, 3.0)
	obs[i + 2] = clampf(motion.x / 40.0, -2.0, 2.0)
	obs[i + 3] = clampf(motion.y / 40.0, -2.0, 2.0)
	obs[i + 4] = facing.x
	obs[i + 5] = facing.y
	obs[i + 6] = clampf(intel.last_velocity.length() / 40.0, 0.0, 2.0)
	obs[i + 7] = clampf(seen.length() / 150.0, 0.0, 3.0)
	obs[i + 8] = 1.0 if sees else 0.0
	obs[i + 9] = 1.0 if intel.known else 0.0
	obs[i + 10] = clampf(intel.age / ChaseIntel.PING_SECONDS, 0.0, 1.0)
	obs[i + 11] = runner.health / maxf(runner.max_health, 1.0)
	obs[i + 12] = _boost_state(runner) if intel.known else 0.0
	i += 13
	var believed: Vector2 = intel.believed_position()
	var mates: Array = _nearest(team, TEAM_SLOTS, INF)
	var my_gap: float = _here.distance_to(believed)
	var rank: int = 0
	for mate: LabVehicle in team:
		if Vector2(mate.global_position.x, mate.global_position.z).distance_to(believed) < my_gap:
			rank += 1
	for slot: int in TEAM_SLOTS:
		if slot < mates.size():
			var mate: LabVehicle = mates[slot]
			var at := Vector2(mate.global_position.x, mate.global_position.z)
			_put_car(obs, i, mate, clampf(at.distance_to(believed) / 150.0, 0.0, 3.0))
		i += 8
	obs[i] = minf(team_size, 5) / 5.0
	obs[i + 1] = car.health / maxf(car.max_health, 1.0)
	obs[i + 2] = burst.readiness()
	obs[i + 3] = 1.0 if burst.active() else 0.0
	var at: int = _append_roads(obs, i + 4, nav, navigation)
	for slot: int in mini(mates.size(), TEAM_SLOTS):
		obs[at + slot * ChaseNav.OPTIONS + clampi(int(team_options.get(mates[slot], 0)), 0, ChaseNav.OPTIONS - 1)] = 1.0
	at += TEAM_SLOTS * ChaseNav.OPTIONS
	obs[at] = minf(rank, 4) / 4.0
	obs[at + 1] = delay_seconds / 0.25
	return obs


func observe_runner(route: RouteTrack, progress: float, cars: Array, dt: float, cops: Array, bursting: Array,
		intel: ChaseIntel, nav: RoadNav, navigation: PackedFloat32Array) -> PackedFloat32Array:
	var obs: PackedFloat32Array = _school(route, progress, cars, dt)
	var i: int = CopSenses.OBS_DIM
	var near: Array = _nearest(cops, COP_SLOTS, RUNNER_SENSE)
	for slot: int in COP_SLOTS:
		if slot < near.size():
			var cop: LabVehicle = near[slot]
			var gap: float = Vector2(cop.global_position.x, cop.global_position.z).distance_to(_here)
			_put_car(obs, i, cop, gap / 150.0)
			obs[i + 8] = obs[i + 7]
			obs[i + 7] = 1.0 if bursting[cops.find(cop)] else 0.0
		i += 9
	obs[i] = car.health / maxf(car.max_health, 1.0)
	obs[i + 1] = 1.0 if car.boost.phase == ChargeBoost.Phase.CHARGING else 0.0
	obs[i + 2] = car.boost.charge_ratio(car.tuning)
	obs[i + 3] = 1.0 if car.boost.phase == ChargeBoost.Phase.BOOSTING else 0.0
	obs[i + 4] = minf(near.size(), 5) / 5.0
	obs[i + 5] = 1.0 if intel.known else 0.0
	_append_roads(obs, i + 6, nav, navigation)
	return obs


## Navigation options, then the next junction on this car's road: its distance and up to 4 exits.
## Returns the index after what it wrote.
func _append_roads(obs: PackedFloat32Array, i: int, nav: RoadNav, navigation: PackedFloat32Array) -> int:
	for k: int in navigation.size():
		obs[i + k] = navigation[k]
	i += navigation.size()
	var next: Dictionary = nav.next_junction(_here, _forward)
	if next.is_empty():
		obs[i] = 3.0
		return i + JUNCTION_FEATURES
	obs[i] = clampf(float(next["distance"]) / 100.0, 0.0, 3.0)
	var ways: Array = nav.exits(next["node"], next["edge"])
	for slot: int in mini(ways.size(), 4):
		var turn: float = ways[slot]["turn"]
		obs[i + 1 + slot * 3] = sin(turn)
		obs[i + 2 + slot * 3] = cos(turn)
		obs[i + 3 + slot * 3] = 1.0
	return i + JUNCTION_FEATURES


func _school(route: RouteTrack, progress: float, cars: Array, dt: float) -> PackedFloat32Array:
	var goal: Vector2 = route.point_at(progress + GOAL_AHEAD)
	var obs: PackedFloat32Array = school.observe(route, progress, goal, Vector2.ZERO, cars, dt)
	obs.resize(OBS_DIM)
	_here = Vector2(car.global_position.x, car.global_position.z)
	_forward = Vector2(-car.global_basis.z.x, -car.global_basis.z.z).normalized()
	_right = Vector2(car.global_basis.x.x, car.global_basis.x.z).normalized()
	return obs


## Position, velocity and heading of another car in this car's frame, then `extra`, then "present".
func _put_car(obs: PackedFloat32Array, i: int, other: LabVehicle, extra: float) -> void:
	var offset: Vector2 = _local(Vector2(other.global_position.x, other.global_position.z) - _here)
	var motion: Vector2 = _local(Vector2(other.velocity.x, other.velocity.z))
	var facing: Vector2 = _local(Vector2(-other.global_basis.z.x, -other.global_basis.z.z).normalized())
	obs[i] = clampf(offset.x / 100.0, -2.0, 2.0)
	obs[i + 1] = clampf(offset.y / 100.0, -2.0, 2.0)
	obs[i + 2] = clampf(motion.x / 40.0, -2.0, 2.0)
	obs[i + 3] = clampf(motion.y / 40.0, -2.0, 2.0)
	obs[i + 4] = facing.x
	obs[i + 5] = facing.y
	obs[i + 6] = extra
	obs[i + 7] = 1.0


func _nearest(cars: Array, count: int, within: float) -> Array:
	var ranked: Array = []
	for other: LabVehicle in cars:
		if other == car or not is_instance_valid(other):
			continue
		var gap: float = Vector2(other.global_position.x, other.global_position.z).distance_to(_here)
		if gap <= within:
			ranked.append([gap, other])
	ranked.sort_custom(func(a: Array, b: Array) -> bool: return a[0] < b[0])
	var result: Array = []
	for entry: Array in ranked.slice(0, count):
		result.append(entry[1])
	return result


func _local(v: Vector2) -> Vector2:
	return Vector2(v.dot(_right), v.dot(_forward))


static func _boost_state(vehicle: LabVehicle) -> float:
	match vehicle.boost.phase:
		ChargeBoost.Phase.BOOSTING:
			return 1.0
		ChargeBoost.Phase.CHARGING:
			return 0.5
	return 0.0
