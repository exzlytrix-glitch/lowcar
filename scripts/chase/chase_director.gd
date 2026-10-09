class_name ChaseDirector
extends Node
## Owns bounded police spawning, escalation, and a visible, escapable arrest timer.
signal spawn_requested(tier: int, desired_count: int)
@export var tuning: ChaseTuning
@export var police_scene: PackedScene
@export var player_path: NodePath = NodePath("../Vehicles/PlayerCar")
@export var world_path: NodePath = NodePath("../World")
var active_police: Array[PoliceVehicle] = []
var nearest_distance: float = INF
var notice: String = ""
var notice_remaining: float = 0.0
var _last_tier: int = 1
var _spawn_clock: float = 0.0
var _serial: int = 0
var _rng := RandomNumberGenerator.new()
var _player: ArcadeVehicle
var _world: CityStreamer

func _ready() -> void:
	_player = get_node(player_path) as ArcadeVehicle
	_world = get_node(world_path) as CityStreamer
	RunSession.run_started.connect(_on_run_started)
	RunSession.phase_changed.connect(_on_phase_changed)

func _physics_process(delta: float) -> void:
	if RunSession.phase != RunSession.Phase.DRIVING or tuning == null:
		return
	notice_remaining = maxf(0.0, notice_remaining - delta)
	var tier: int = mini(tuning.maximum_tier, 1 + int(RunSession.elapsed_s / maxf(tuning.seconds_per_tier, 1.0)))
	if tier != _last_tier:
		_last_tier = tier
		RunSession.set_pursuit_tier(tier)
		for unit: PoliceVehicle in active_police:
			unit.set_pursuit_tier(tier, tuning)
		announce("BACKUP INBOUND / PURSUIT %d" % tier)
		_request_budget()
	_prune_units()
	_spawn_clock -= delta
	if RunSession.elapsed_s >= tuning.start_grace_seconds and _spawn_clock <= 0.0 and active_police.size() < desired_count():
		_spawn_unit()
		_spawn_clock = tuning.spawn_interval_seconds
	RunSession.active_police_count = active_police.size()
	_update_capture(delta)

func desired_count() -> int:
	return mini(tuning.maximum_police, tuning.initial_police_budget + (_last_tier - 1) * tuning.additional_police_per_tier)

func announce(message: String) -> void:
	notice = message
	notice_remaining = 3.2

func report_capture() -> void:
	RunSession.end_run("CAUGHT")

func _on_run_started(seed_value: int) -> void:
	_clear_units()
	_rng.seed = seed_value
	_serial = 0
	_last_tier = 1
	_spawn_clock = 0.0
	nearest_distance = INF
	announce("GO! / PATROLS INBOUND")
	_request_budget()

func _on_phase_changed(phase: RunSession.Phase) -> void:
	if phase == RunSession.Phase.MENU:
		_clear_units()
		RunSession.active_police_count = 0
		RunSession.capture_progress = 0.0
	elif phase == RunSession.Phase.ENDED:
		for unit: PoliceVehicle in active_police:
			unit.stop_vehicle()
			unit.silence()

func _clear_units() -> void:
	for unit: PoliceVehicle in active_police:
		if is_instance_valid(unit):
			unit.get_parent().remove_child(unit)
			unit.queue_free()
	active_police.clear()

func _request_budget() -> void:
	spawn_requested.emit(_last_tier, desired_count())

func _spawn_unit() -> void:
	var shape := BoxShape3D.new()
	shape.size = Vector3(2.4, 1.5, 5.0)
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = shape
	query.collision_mask = 15
	var space: PhysicsDirectSpaceState3D = _player.get_world_3d().direct_space_state
	for attempt: int in range(18):
		var behind: Vector3 = _player.global_basis.z
		behind.y = 0.0
		var distance: float = _rng.randf_range(43.0, 76.0)
		var at: Vector3 = _player.global_position + behind * distance
		# Later cars enter through side streets; never materialize beside the player.
		if _last_tier >= 2 and _serial % 3 != 0:
			var angle: float = (_serial % 2 * 2 - 1) * PI * 0.5
			at = _player.global_position + behind.rotated(Vector3.UP, angle) * distance
		if attempt > 5:
			at = _player.global_position + Vector3(cos(attempt * 1.7), 0, sin(attempt * 1.7)) * distance
		at = ChaseRoads.project(at)
		if at.distance_to(_player.global_position) < 38.0 or not _world.active_chunks.has(_world.coordinate_for(at)):
			continue
		query.transform = Transform3D(Basis.IDENTITY, at + Vector3.UP * 1.0)
		if not space.intersect_shape(query, 1).is_empty():
			continue
		var unit := police_scene.instantiate() as PoliceVehicle
		unit.name = "Patrol_%d" % _serial
		_player.get_parent().add_child(unit)
		unit.reset_vehicle(at)
		unit.configure(_player, _serial, _last_tier, tuning)
		active_police.append(unit)
		_serial += 1
		return

func _prune_units() -> void:
	for index: int in range(active_police.size() - 1, -1, -1):
		var unit: PoliceVehicle = active_police[index]
		if not is_instance_valid(unit):
			active_police.remove_at(index)
			continue
		var distance: float = unit.global_position.distance_to(_player.global_position)
		if distance > tuning.recycle_distance_m or unit.global_position.y < -5.0:
			active_police.remove_at(index)
			unit.get_parent().remove_child(unit)
			unit.queue_free()

func _update_capture(delta: float) -> void:
	nearest_distance = INF
	var nearby: int = 0
	for unit: PoliceVehicle in active_police:
		var distance: float = unit.global_position.distance_to(_player.global_position)
		nearest_distance = minf(nearest_distance, distance)
		if distance < tuning.capture_radius_m and _player.is_on_floor() and _has_clear_sight(unit):
			nearby += 1
	var speed: float = Vector2(_player.velocity.x, _player.velocity.z).length()
	if nearby > 0 and speed < tuning.capture_max_speed_mps:
		var rate: float = (1.0 + minf(nearby - 1, 2) * 0.25) / tuning.capture_seconds
		RunSession.capture_progress = minf(1.0, RunSession.capture_progress + delta * rate)
	else:
		RunSession.capture_progress = maxf(0.0, RunSession.capture_progress - delta / tuning.capture_decay_seconds)
	if RunSession.capture_progress >= 1.0:
		report_capture()

func _has_clear_sight(unit: PoliceVehicle) -> bool:
	var ray := PhysicsRayQueryParameters3D.create(unit.global_position + Vector3.UP, _player.global_position + Vector3.UP, 1)
	return _player.get_world_3d().direct_space_state.intersect_ray(ray).is_empty()
