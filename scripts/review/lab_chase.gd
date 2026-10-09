class_name LabChase
extends Node
## Lab police director, step 1: spawns cops on the roads around you, keeps them in play at
## 115 km/h by moving stragglers back ahead of you, and escalates with chase time.

const POLICE_SCENE_PATH: String = "res://scenes/review/lab_police_car.tscn"
const SPAWN_NEAR: float = 110.0
const SPAWN_FAR: float = 280.0
const RECYCLE_DISTANCE: float = 420.0
## Catch-up boost starts building at CATCH_UP_START metres behind and is full by CATCH_UP_FULL.
const CATCH_UP_START: float = 25.0
const CATCH_UP_FULL: float = 85.0

## Minute-zero cop top speed (m/s); escalation multiplies it. Your cruise is 32 m/s (115 km/h).
var base_top_speed: float = 34.0
## Speed multiplier for cops more than CATCH_UP_DISTANCE behind you.
var catch_up_boost: float = 1.3

var active: bool = false
## Off when cops were only added by hand (P): they chase, but nothing spawns or escalates.
var auto_spawn: bool = false
var elapsed: float = 0.0
var graph: RoadGraph
var player: LabVehicle
var astar := AStar2D.new()
var cops: Array[LabVehicle] = []
var _drivers: Dictionary = {}
const BRAIN_PATH: String = "res://resources/ai/cop_brain.json"
## Learned cop brain from training (scripts/ai/policy_net.gd). B in the lab switches cops to it.
var brain: PolicyNet
var use_brain: bool = false
var nav: RoadNav
var _spawn_clock: float = 0.0
var _rng := RandomNumberGenerator.new()


func setup(road_graph: RoadGraph, car: LabVehicle) -> void:
	stop()
	graph = road_graph
	player = car
	elapsed = 0.0
	nav = RoadNav.new(graph)
	astar.clear()
	for node: int in graph.node_count():
		if graph.degree(node) > 0:
			astar.add_point(node, graph.positions[node])
	for id: int in graph.alive_edges():
		astar.connect_points(graph.edge_a[id], graph.edge_b[id])


func toggle() -> void:
	if active and auto_spawn:
		stop()
	else:
		start()


func start() -> void:
	if graph == null:
		return
	active = true
	auto_spawn = true
	_rng.randomize()
	for index: int in 2:
		_spawn(true)
	_spawn_clock = 0.5


func stop() -> void:
	active = false
	auto_spawn = false
	for cop: LabVehicle in cops:
		if is_instance_valid(cop):
			cop.queue_free()
	cops.clear()
	_drivers.clear()


# --- escalation (by chase time only) -------------------------------------------

func minute() -> float:
	return elapsed / 60.0


func cop_count() -> int:
	return mini(2 + int(minute() * 0.8), 10)


func speed_scale() -> float:
	return minf(0.97 + 0.025 * minute(), 1.3)


func lateness() -> float:
	return minf(0.9 + 0.08 * minute(), 1.8)


func top_speed() -> float:
	return base_top_speed * speed_scale()


func _physics_process(delta: float) -> void:
	if not active or not is_instance_valid(player):
		return
	if auto_spawn:
		elapsed += delta
	_spawn_clock -= delta
	var here := Vector2(player.global_position.x, player.global_position.z)
	var heading := Vector2(-player.global_basis.z.x, -player.global_basis.z.z).normalized()
	for cop: LabVehicle in cops.duplicate():
		var at := Vector2(cop.global_position.x, cop.global_position.z)
		var distance: float = at.distance_to(here)
		if distance > RECYCLE_DISTANCE or cop.global_position.y < -5.0:
			_remove(cop)
			continue
		var behind: bool = heading.dot(at - here) < 0.0
		var lag: float = clampf((distance - CATCH_UP_START) / (CATCH_UP_FULL - CATCH_UP_START), 0.0, 1.0) if behind else 0.0
		cop.tuning.maximum_speed_mps = top_speed() * lerpf(1.0, catch_up_boost, lag)
		var scripted := _drivers[cop] as LabCopDriver
		if scripted != null:
			scripted.lateness = lateness()
	if auto_spawn and cops.size() < cop_count() and _spawn_clock <= 0.0:
		_spawn(false)
		_spawn_clock = 1.2


## Closest road junction to a point, preferring the end of the road that lies ahead.
func node_near(at: Vector2, heading: Vector2) -> int:
	var found: Dictionary = graph.closest_road_point(at, 400.0)
	if found.is_empty():
		return -1
	var id: int = found["edge"]
	var a: int = graph.edge_a[id]
	var b: int = graph.edge_b[id]
	if heading != Vector2.ZERO:
		return a if heading.dot(graph.positions[a] - at) > heading.dot(graph.positions[b] - at) else b
	return a if graph.positions[a].distance_to(at) < graph.positions[b].distance_to(at) else b


## Cops arrive ahead of you and from side streets, out of sight; a fresh chase starts with two behind.
func _spawn(behind: bool) -> void:
	var here := Vector2(player.global_position.x, player.global_position.z)
	var heading := Vector2(-player.global_basis.z.x, -player.global_basis.z.z).normalized()
	var near: float = 70.0 if behind else SPAWN_NEAR
	var far: float = 120.0 if behind else SPAWN_FAR
	var edges: PackedInt32Array = graph.edges_in(Rect2(here, Vector2.ZERO).grow(far))
	if edges.is_empty():
		return
	for attempt: int in 40:
		var id: int = edges[_rng.randi() % edges.size()]
		if graph.edge_alive[id] == 0:
			continue
		var a: Vector2 = graph.positions[graph.edge_a[id]]
		var b: Vector2 = graph.positions[graph.edge_b[id]]
		var point: Vector2 = a.lerp(b, _rng.randf_range(0.2, 0.8))
		var distance: float = point.distance_to(here)
		if distance < near or distance > far:
			continue
		var side: float = heading.dot((point - here).normalized())
		if (behind and side > -0.3) or (not behind and side < 0.1):
			continue
		var crowded: bool = false
		for other: LabVehicle in cops:
			if Vector2(other.global_position.x, other.global_position.z).distance_to(point) < 25.0:
				crowded = true
				break
		if crowded:
			continue
		# On your road a cop faces your way and cruises, so it is on your tail as you catch it;
		# on a side street it faces toward your line, ready to pull out.
		var dir: Vector2 = (b - a).normalized()
		var start_speed: float = 22.0
		if absf(dir.dot(heading)) > 0.5:
			if dir.dot(heading) < 0.0:
				dir = -dir
		else:
			if dir.dot(here + heading * distance - point) < 0.0:
				dir = -dir
			start_speed = 12.0
		_add_cop(point, dir, start_speed)
		return


## One chasing cop on the road about 40 m behind you, already facing your way at your speed.
## Works with or without a running chase.
func add_cop_behind() -> void:
	if graph == null or not is_instance_valid(player):
		return
	var forward := Vector2(-player.global_basis.z.x, -player.global_basis.z.z).normalized()
	var here := Vector2(player.global_position.x, player.global_position.z)
	var found: Dictionary = graph.closest_road_point(here - forward * 40.0, 200.0)
	if found.is_empty():
		return
	var id: int = found["edge"]
	var point: Vector2 = found["point"]
	var dir: Vector2 = (graph.positions[graph.edge_b[id]] - graph.positions[graph.edge_a[id]]).normalized()
	if dir.dot(forward) < 0.0:
		dir = -dir
	active = true
	_add_cop(point, dir, maxf(player.forward_speed, 10.0))


func _add_cop(point: Vector2, dir: Vector2, start_speed: float) -> void:
	var cop := (load(POLICE_SCENE_PATH) as PackedScene).instantiate() as LabVehicle
	cop.tuning = cop.tuning.duplicate() as VehicleTuning
	cop.tuning.maximum_speed_mps = top_speed()
	var handling := CarHandling.new()
	handling.steer_low_speed = 2.6
	handling.steer_top_speed = 2.1
	handling.grip = 11.0
	handling.steer_response = 9.0
	cop.handling = handling
	cop.add_to_group("police")
	var driver: Node = _make_driver(cop)
	cop.add_child(driver)
	get_parent().add_child(cop)
	cop.chamfer_collider()
	cop.reset_vehicle(Vector3(point.x, 0.2, point.y))
	cop.rotation.y = atan2(-dir.x, -dir.y)
	cop.forward_speed = start_speed
	cop.velocity = Vector3(dir.x, 0.0, dir.y) * start_speed
	cop.reset_physics_interpolation()
	cop.controls_enabled = true
	cops.append(cop)
	_drivers[cop] = driver


func _make_driver(cop: LabVehicle) -> Node:
	if use_brain and brain != null:
		var learned := BrainCopDriver.new()
		learned.name = "Driver"
		learned.net = brain
		learned.chase = self
		learned.car = cop
		learned.target = player
		return learned
	var driver := LabCopDriver.new()
	driver.name = "Driver"
	driver.chase = self
	driver.car = cop
	driver.target = player
	driver.lateness = lateness()
	return driver


## Switches every cop (current and future) between the scripted driver and the learned brain.
func set_brain(enabled: bool) -> void:
	if enabled and brain == null:
		brain = PolicyNet.load_file(BRAIN_PATH)
	use_brain = enabled and brain != null
	for cop: LabVehicle in cops:
		var old: Node = _drivers[cop]
		cop.remove_child(old)
		old.queue_free()
		var driver: Node = _make_driver(cop)
		cop.add_child(driver)
		_drivers[cop] = driver


func driver_label() -> String:
	if use_brain and brain != null:
		return "learned brain (%s, %s decisions of training)" % [brain.meta.get("stage", "?"), _thousands(int(brain.meta.get("steps", 0)))]
	return "scripted driver"


func _thousands(value: int) -> String:
	return "%.1fM" % (value / 1.0e6) if value >= 1000000 else "%dk" % (value / 1000)


func _remove(cop: LabVehicle) -> void:
	cops.erase(cop)
	_drivers.erase(cop)
	cop.queue_free()
