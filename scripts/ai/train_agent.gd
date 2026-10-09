class_name TrainAgent
extends RefCounted
## One learning cop in the training city. Each decision it scores what the last action did, ends and
## restarts its episode when needed, and returns what it sees next.
## Stage "school": drive a long random route through the city as fast and as cleanly as possible.

const INFO_DIM: int = 4
const EPISODE_STEPS: int = 900
## Stuck this long costs points every decision (so it learns to back out); this long ends the episode.
const STUCK_SECONDS: float = 2.0
const STUCK_GIVE_UP: float = 8.0
const STUCK_COST: float = 0.05
const OFF_ROUTE: float = 30.0
const LOOSE_OFFSET: float = 12.0
const PROGRESS_REWARD: float = 0.1
const STEP_COST: float = 0.005
const WALL_DAMAGE_COST: float = 0.08
const COP_DAMAGE_COST: float = 0.1
const GRIND_COST: float = 0.02
const FAIL_COST: float = 1.0
const ROUTE_BONUS: float = 2.0

var car: LabVehicle
var senses := CopSenses.new()
var route := RouteTrack.new()
var nav: RoadNav
var rng: RandomNumberGenerator
var progress: float = 0.0
var steps: int = 0
## Set when the world changes under the cop (new city): its episode is cut at the next decision.
var forced_end: bool = false
var _stuck: float = 0.0
var _wall_damage: float = 0.0
var _cop_damage: float = 0.0


func _init(vehicle: LabVehicle, road_nav: RoadNav, random: RandomNumberGenerator) -> void:
	car = vehicle
	nav = road_nav
	rng = random
	senses.car = car
	car.damaged.connect(_on_damaged)


func reset() -> void:
	var spot: Dictionary = nav.random_road_spot(rng)
	var point: Vector2 = spot.get("point", Vector2.ZERO)
	var dir: Vector2 = spot.get("dir", Vector2(0.0, -1.0))
	var speed: float = rng.randf_range(0.0, 15.0)
	car.reset_vehicle(Vector3(point.x, 0.25, point.y))
	car.rotation.y = atan2(-dir.x, -dir.y)
	car.forward_speed = speed
	car.velocity = Vector3(dir.x, 0.0, dir.y) * speed
	car.reset_physics_interpolation()
	car.controls_enabled = true
	senses.reset()
	_new_route()
	steps = 0
	_stuck = 0.0
	_wall_damage = 0.0
	_cop_damage = 0.0


## Scores the last decision and returns {"obs", "reward", "done", "info"}. After an episode ends the
## cop has already been restarted, so "obs" is the first view of its next episode.
func step(dt: float, cars: Array) -> Dictionary:
	var here := Vector2(car.global_position.x, car.global_position.z)
	var speed: float = Vector2(car.velocity.x, car.velocity.z).length()
	var now: float = route.project(here)
	var moved: float = clampf(now - progress, -10.0, 15.0)
	progress = now
	var reward: float = PROGRESS_REWARD * moved - STEP_COST
	reward -= _wall_damage * WALL_DAMAGE_COST + _cop_damage * COP_DAMAGE_COST
	if car._wall_contact:
		reward -= GRIND_COST
	if route.offset > LOOSE_OFFSET:
		reward -= 0.001 * (route.offset - LOOSE_OFFSET)
	var info := PackedFloat32Array([moved, speed, _wall_damage, _cop_damage])
	_wall_damage = 0.0
	_cop_damage = 0.0
	steps += 1
	_stuck = _stuck + dt if speed < 1.5 else 0.0
	if _stuck > STUCK_SECONDS:
		reward -= STUCK_COST
	var done: bool = false
	if _stuck > STUCK_GIVE_UP or route.offset > OFF_ROUTE or car.global_position.y < -3.0:
		reward -= FAIL_COST
		done = true
	elif progress >= route.length() - 15.0:
		reward += ROUTE_BONUS
		_new_route()
	elif steps >= EPISODE_STEPS or forced_end:
		done = true
	forced_end = false
	if done:
		reset()
	var goal: Vector2 = route.point_at(progress + 80.0)
	var obs: PackedFloat32Array = senses.observe(route, progress, goal, Vector2.ZERO, cars, dt)
	return {"obs": obs, "reward": reward, "done": done, "info": info}


func _new_route() -> void:
	var here := Vector2(car.global_position.x, car.global_position.z)
	var heading := Vector2(-car.global_basis.z.x, -car.global_basis.z.z).normalized()
	var destination: Vector2 = here
	for attempt: int in 12:
		var node: int = nav.random_node(rng)
		if node >= 0:
			destination = nav.graph.positions[node]
			if destination.distance_to(here) > 350.0:
				break
	route.setup(nav.route(here, heading, destination))
	progress = route.project(here)


func _on_damaged(amount: float, source: String) -> void:
	if source == "cop":
		_cop_damage += amount
	else:
		_wall_damage += amount
