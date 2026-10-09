class_name ChaseSenses
extends RefCounted
## What a cop or the runner sees in a chase (learned cops vs a learned runner). Both start with the
## driving-school senses (CopSenses, 61 numbers) so a school-trained brain carries over, then add the
## chase. Training and the game build it here, so a brain sees the same thing in both.
##
## Cop (110): school senses, with the road route toward where the team thinks the runner is, then
## 13  the runner as the team knows it: last seen position, velocity and heading, speed, distance,
##     whether this cop sees it, whether anyone does, how long ago it was seen, its health, boosting
## 32  up to 4 teammates, nearest first: position, velocity, heading, their distance to the runner, present
##  4  team size, own health, burst ready, bursting
##
## Runner (121): school senses, with a route to a random destination it is free to ignore, then
## 54  up to 6 cops within 160 m, nearest first: position, velocity, heading, distance, bursting, present
##  6  own health, boost charging, charge, boosting, cops nearby, spotted by the cops right now
##
## Actions: [steer, throttle, handbrake, special], special = fire burst (cop) or hold boost (runner).

const COP_OBS: int = 110
const RUNNER_OBS: int = 121
const OBS_DIM: int = 121
const ACT_DIM: int = 4
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
		runner: LabVehicle, team: Array, team_size: int, burst: CopBurst) -> PackedFloat32Array:
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
	return obs


func observe_runner(route: RouteTrack, progress: float, cars: Array, dt: float, cops: Array, bursting: Array,
		intel: ChaseIntel) -> PackedFloat32Array:
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
	return obs


## Applies one car's slice of an action array: [steer, throttle, handbrake, special]. For the runner
## the special holds the charge boost; a cop's burst is handled by its CopBurst instead.
static func apply(target: ArcadeVehicle, actions: PackedFloat32Array, offset: int, hold_boost: bool) -> void:
	target.set_driver_command(clampf(actions[offset + 1], -1.0, 1.0), clampf(actions[offset], -1.0, 1.0),
		actions[offset + 2] > 0.0, hold_boost and actions[offset + 3] > 0.0)


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
