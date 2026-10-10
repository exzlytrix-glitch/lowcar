class_name ChaseAgent
extends RefCounted
## One learned car's plumbing, shared by chase training (ChaseMatch) and the game (the lab's brain
## drivers), so a brain sees and acts exactly the same in both: senses, road route, navigation choice,
## burst or boost. Each decision: observe_cop()/observe_runner() builds the brain's input, the brain
## answers, apply() drives the car until the next decision.
##
## Brain answer (wire order): [steer, throttle, handbrake 0/1, special, navigation option 0-4]
##   special: cop = fire burst 0/1; runner = boost charge 0 none, 1-4 short to long (RunnerBoost)
## A reaction delay (delay_frames, physics frames) makes the controls land late, like a human's
## reaction time; call physics_tick() every physics frame so delayed orders arrive.

const COP_REPLAN: float = 0.5
const RUNNER_REPLAN: float = 2.0
const GOAL_REACHED: float = 40.0
## The runner's chosen escape target counts as reached this close.
const ESCAPE_REACHED: float = 25.0

var car: LabVehicle
var is_runner: bool = false
var nav: RoadNav
var rng: RandomNumberGenerator
var senses := ChaseSenses.new()
var route := RouteTrack.new()
var navigation := ChaseNav.new()
var burst := CopBurst.new()
var boost := RunnerBoost.new()
var progress: float = 0.0
## The runner's GPS destination (navigation option 0).
var goal := Vector2.ZERO
var _replan: float = 0.0
var _dt: float = 0.1
var _throttle: float = 0.0
var _steer: float = 0.0
var _handbrake: bool = false
var _hold: bool = false
## Physics frames between a decision and its controls landing (0 = instant).
var delay_frames: int = 0
## Orders still on their way: [frames left, throttle, steer, handbrake, hold boost, fire burst].
var _orders: Array = []


func setup(vehicle: LabVehicle, runner: bool, road_nav: RoadNav, car_mask: int, random: RandomNumberGenerator) -> void:
	car = vehicle
	is_runner = runner
	rng = random
	senses.setup(vehicle, car_mask)
	navigation.setup(road_nav, runner)
	set_nav(road_nav)


func set_nav(road_nav: RoadNav) -> void:
	nav = road_nav
	navigation.nav = road_nav


## New chase or new spawn.
func reset() -> void:
	senses.reset()
	route.points = PackedVector2Array()
	progress = 0.0
	_replan = 0.0
	navigation.reset()
	burst.reset()
	boost.reset()
	_hold = false
	_orders.clear()
	_throttle = 0.0
	_steer = 0.0
	_handbrake = false
	if is_runner:
		_pick_goal()


## `team_options` maps each teammate car to its current navigation option.
func observe_cop(dt: float, cars: Array, intel: ChaseIntel, sees: bool, runner: LabVehicle, team: Array,
		team_size: int, team_options: Dictionary) -> PackedFloat32Array:
	_dt = dt
	var believed: Vector2 = intel.believed_position()
	var heading: Vector2 = intel.last_velocity.normalized() if intel.last_velocity.length() > 3.0 else intel.last_forward
	navigation.tick()
	navigation.update_cop_targets(believed, heading)
	navigation.measure(_here(), _forward())
	_follow_route(dt, COP_REPLAN)
	var options: PackedFloat32Array = navigation.features(_here(), _forward(), [believed])
	return senses.observe_cop(route, progress, cars, dt, intel, sees, runner, team, team_size, burst, nav, options,
		team_options, delay_frames / float(Engine.physics_ticks_per_second))


func observe_runner(dt: float, cars: Array, cops: Array, bursting: Array, intel: ChaseIntel) -> PackedFloat32Array:
	_dt = dt
	var here: Vector2 = _here()
	if here.distance_to(goal) < GOAL_REACHED:
		_pick_goal()
	if navigation.option != 0 and here.distance_to(navigation.target()) < ESCAPE_REACHED:
		navigation.option = 0  # escape route done: back on the GPS route
		_replan = 0.0
	navigation.tick()
	navigation.update_runner_targets(here, _forward(), goal)
	navigation.measure(here, _forward())
	_follow_route(dt, RUNNER_REPLAN)
	var near: Array = []
	for cop: LabVehicle in cops:
		var at := Vector2(cop.global_position.x, cop.global_position.z)
		if at.distance_to(here) <= ChaseSenses.RUNNER_SENSE:
			near.append(at)
	var options: PackedFloat32Array = navigation.features(here, _forward(), near)
	return senses.observe_runner(route, progress, cars, dt, cops, bursting, intel, nav, options)


## Drives the car with one slot of a brain answer (starting at `offset`).
func apply(actions: PackedFloat32Array, offset: int) -> void:
	var steer: float = clampf(actions[offset], -1.0, 1.0)
	var throttle: float = clampf(actions[offset + 1], -1.0, 1.0)
	var handbrake: bool = actions[offset + 2] > 0.5
	if navigation.open:
		var before: int = navigation.option
		navigation.choose(int(round(actions[offset + 4])))
		if navigation.option != before:
			_replan = 0.0
	var hold: bool = false
	var fire: bool = false
	if is_runner:
		hold = boost.hold(_dt, int(round(actions[offset + 3])), car)
	else:
		burst.advance(_dt)
		fire = actions[offset + 3] > 0.5
	var order: Array = [delay_frames, throttle, steer, handbrake, hold, fire]
	if delay_frames <= 0:
		_carry_out(order)
	else:
		_orders.append(order)


## Delivers delayed orders whose time has come. Call once per physics frame.
func physics_tick() -> void:
	while not _orders.is_empty():
		var order: Array = _orders[0]
		order[0] -= 1
		if order[0] > 0:
			break
		_orders.pop_front()
		_carry_out(order)
	for index: int in range(1, _orders.size()):
		_orders[index][0] -= 1


func _carry_out(order: Array) -> void:
	_throttle = order[1]
	_steer = order[2]
	_handbrake = order[3]
	_hold = order[4]
	if order[5]:
		burst.try_fire()
	reapply()


## Sends the last controls again (the lab's runner does this every frame to win over keyboard input).
func reapply() -> void:
	car.set_driver_command(_throttle, _steer, _handbrake, _hold)


func _follow_route(dt: float, every: float) -> void:
	var here: Vector2 = _here()
	_replan -= dt
	if _replan <= 0.0 or route.points.is_empty():
		_replan = every
		var facing: Vector2 = -_forward() if is_runner and navigation.option == 4 else _forward()
		route.setup(nav.route(here, facing, navigation.target()))
	progress = route.project(here)


func _pick_goal() -> void:
	var here: Vector2 = _here()
	goal = here
	for attempt: int in 12:
		var node: int = nav.random_node(rng)
		if node >= 0:
			goal = nav.graph.positions[node]
			if goal.distance_to(here) > 300.0:
				return


func _here() -> Vector2:
	return Vector2(car.global_position.x, car.global_position.z)


func _forward() -> Vector2:
	return Vector2(-car.global_basis.z.x, -car.global_basis.z.z).normalized()
