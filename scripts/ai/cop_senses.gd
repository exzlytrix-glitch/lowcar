class_name CopSenses
extends RefCounted
## What a learned cop sees: a fixed list of OBS_DIM numbers, rebuilt every decision (10 per second).
## Training and the in-game driver both build it here, so a trained brain sees the same thing in both.
##
##  8  own car: forward speed, sideways slide, spin rate, slip angle, steering, drifting, grounded, top speed
## 18  wall distance in 18 directions (buildings and kerbs)
## 10  car distance in 10 directions (you and other cops)
## 12  the road ahead: 6 points along the route, 5 m to 65 m ahead, in the car's own frame
##  5  the goal: position, velocity and distance
##  8  the two nearest other cars: position and velocity relative to this one
## Actions are [steer, throttle, handbrake], each -1..1 (handbrake on above 0).

const WALL_RAYS: PackedFloat32Array = [-90.0, -67.5, -45.0, -30.0, -20.0, -10.0, -4.0, 0.0, 4.0, 10.0, 20.0, 30.0,
	45.0, 67.5, 90.0, 135.0, 180.0, -135.0]
const CAR_RAYS: PackedFloat32Array = [-60.0, -30.0, -12.0, 0.0, 12.0, 30.0, 60.0, 150.0, 180.0, -150.0]
const RAY_RANGE: float = 60.0
const PATH_AHEAD: PackedFloat32Array = [5.0, 12.0, 20.0, 30.0, 45.0, 65.0]
const OBS_DIM: int = 61
const ACT_DIM: int = 3
const WALL_MASK: int = 1
const CAR_MASK: int = 2 | 4

var car: LabVehicle
var _last_yaw: float = 0.0
var _has_yaw: bool = false


func reset() -> void:
	_has_yaw = false


func observe(route: RouteTrack, progress: float, goal: Vector2, goal_velocity: Vector2, cars: Array, dt: float) -> PackedFloat32Array:
	var obs := PackedFloat32Array()
	obs.resize(OBS_DIM)
	var forward := Vector2(-car.global_basis.z.x, -car.global_basis.z.z).normalized()
	var right := Vector2(car.global_basis.x.x, car.global_basis.x.z).normalized()
	var here := Vector2(car.global_position.x, car.global_position.z)
	var velocity := Vector2(car.velocity.x, car.velocity.z)
	var yaw_rate: float = 0.0
	if _has_yaw:
		yaw_rate = angle_difference(_last_yaw, car.rotation.y) / maxf(dt, 0.001)
	_last_yaw = car.rotation.y
	_has_yaw = true
	var i: int = 0
	obs[0] = velocity.dot(forward) / 40.0
	obs[1] = velocity.dot(right) / 20.0
	obs[2] = clampf(yaw_rate / 3.0, -2.0, 2.0)
	obs[3] = clampf(car.slip_angle, -1.5, 1.5)
	obs[4] = car._steer
	obs[5] = 1.0 if car.drifting else 0.0
	obs[6] = 1.0 if car.is_on_floor() else 0.0
	obs[7] = car.tuning.maximum_speed_mps / 40.0
	i = 8
	var space: PhysicsDirectSpaceState3D = car.get_world_3d().direct_space_state
	var exclude: Array[RID] = [car.get_rid()]
	for degrees: float in WALL_RAYS:
		obs[i] = _ray(space, car.global_position + Vector3.UP * 0.7, forward, right, degrees, WALL_MASK, exclude)
		i += 1
	for degrees: float in CAR_RAYS:
		obs[i] = _ray(space, car.global_position + Vector3.UP * 0.8, forward, right, degrees, CAR_MASK, exclude)
		i += 1
	for ahead: float in PATH_AHEAD:
		var local: Vector2 = _local(route.point_at(progress + ahead) - here, forward, right) / RAY_RANGE
		obs[i] = clampf(local.x, -2.0, 2.0)
		obs[i + 1] = clampf(local.y, -2.0, 2.0)
		i += 2
	var to_goal: Vector2 = _local(goal - here, forward, right)
	var goal_motion: Vector2 = _local(goal_velocity, forward, right)
	obs[i] = clampf(to_goal.x / 100.0, -2.0, 2.0)
	obs[i + 1] = clampf(to_goal.y / 100.0, -2.0, 2.0)
	obs[i + 2] = clampf(goal_motion.x / 40.0, -2.0, 2.0)
	obs[i + 3] = clampf(goal_motion.y / 40.0, -2.0, 2.0)
	obs[i + 4] = clampf(here.distance_to(goal) / 150.0, 0.0, 2.0)
	i += 5
	var nearest: Array = _nearest_two(cars, here)
	for slot: int in 2:
		if slot < nearest.size():
			var other: CharacterBody3D = nearest[slot]
			var offset: Vector2 = _local(Vector2(other.global_position.x, other.global_position.z) - here, forward, right) / 50.0
			var closing: Vector2 = _local(Vector2(other.velocity.x, other.velocity.z) - velocity, forward, right) / 40.0
			obs[i] = clampf(offset.x, -2.0, 2.0)
			obs[i + 1] = clampf(offset.y, -2.0, 2.0)
			obs[i + 2] = clampf(closing.x, -2.0, 2.0)
			obs[i + 3] = clampf(closing.y, -2.0, 2.0)
		else:
			obs[i + 1] = 2.0
		i += 4
	return obs


## Applies one cop's slice of an action array: [steer, throttle, handbrake].
static func apply(target: ArcadeVehicle, actions: PackedFloat32Array, offset: int) -> void:
	target.set_driver_command(clampf(actions[offset + 1], -1.0, 1.0), clampf(actions[offset], -1.0, 1.0), actions[offset + 2] > 0.0)


func _local(v: Vector2, forward: Vector2, right: Vector2) -> Vector2:
	return Vector2(v.dot(right), v.dot(forward))


func _ray(space: PhysicsDirectSpaceState3D, origin: Vector3, forward: Vector2, right: Vector2, degrees: float,
		mask: int, exclude: Array[RID]) -> float:
	var radians: float = deg_to_rad(degrees)
	var dir: Vector2 = forward * cos(radians) + right * sin(radians)
	var query := PhysicsRayQueryParameters3D.create(origin, origin + Vector3(dir.x, 0.0, dir.y) * RAY_RANGE, mask, exclude)
	var hit: Dictionary = space.intersect_ray(query)
	return 1.0 if hit.is_empty() else origin.distance_to(hit["position"]) / RAY_RANGE


func _nearest_two(cars: Array, here: Vector2) -> Array:
	var first: CharacterBody3D = null
	var second: CharacterBody3D = null
	var first_gap: float = INF
	var second_gap: float = INF
	for other: CharacterBody3D in cars:
		if other == car or not is_instance_valid(other):
			continue
		var gap: float = Vector2(other.global_position.x, other.global_position.z).distance_squared_to(here)
		if gap < first_gap:
			second = first
			second_gap = first_gap
			first = other
			first_gap = gap
		elif gap < second_gap:
			second = other
			second_gap = gap
	var result: Array = []
	if first != null:
		result.append(first)
	if second != null:
		result.append(second)
	return result
