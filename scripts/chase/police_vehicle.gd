class_name PoliceVehicle
extends ArcadeVehicle
## A street-following driver with physical collisions, corner braking, and stuck recovery.
var target: ArcadeVehicle
var unit_id: int = 0
var pursuit_tier: int = 1
var route: Array[Vector3] = []
var _route_clock: float = 0.0
var _stuck_clock: float = 0.0
var _reverse_remaining: float = 0.0
var _reverse_turn: float = 0.0

func _ready() -> void:
	tuning = tuning.duplicate() as VehicleTuning
	add_to_group("police")

func configure(player: ArcadeVehicle, serial: int, tier: int, chase: ChaseTuning) -> void:
	target = player
	unit_id = serial
	set_pursuit_tier(tier, chase)
	controls_enabled = true
	_update_route()
	if not route.is_empty():
		var direction: Vector3 = route[0] - global_position
		if direction.length() > 0.2:
			rotation.y = atan2(-direction.x, -direction.z)
	forward_speed = 8.0
	reset_physics_interpolation()

func set_pursuit_tier(tier: int, chase: ChaseTuning) -> void:
	pursuit_tier = tier
	tuning.maximum_speed_mps = chase.patrol_speed_mps + (tier - 1) * chase.speed_per_tier_mps
	tuning.acceleration_mps2 = 12.0 + minf(tier, 6) * 1.0

func _physics_process(delta: float) -> void:
	if RunSession.phase != RunSession.Phase.DRIVING or not is_instance_valid(target):
		return
	_route_clock -= delta
	if _route_clock <= 0.0:
		_update_route()
		_route_clock = 0.8 + (unit_id % 3) * 0.12
	_drive(delta)
	super._physics_process(delta)

func _update_route() -> void:
	var lead: float = 0.25 + minf(pursuit_tier - 1, 5) * 0.14
	if unit_id % 2 == 1:
		lead += 0.35
	var predicted: Vector3 = target.global_position + Vector3(target.velocity.x, 0, target.velocity.z) * lead
	route = ChaseRoads.route(global_position, predicted, -global_basis.z, unit_id % 2 == 0)
	if predicted.distance_to(ChaseRoads.project(predicted)) < 8.0 and _clear_to(predicted):
		route[-1] = Vector3(predicted.x, 0.1, predicted.z)

func _drive(delta: float) -> void:
	var distance_to_player: float = global_position.distance_to(target.global_position)
	if _reverse_remaining > 0.0:
		_reverse_remaining -= delta
		set_driver_command(-0.65, _reverse_turn, false)
		return
	var actual_speed: float = Vector2(get_real_velocity().x, get_real_velocity().z).length()
	if distance_to_player > 8.0 and controls_enabled and throttle > 0.05 and actual_speed < 1.3:
		_stuck_clock += delta
	else:
		_stuck_clock = 0.0
	if _stuck_clock > 1.4:
		_reverse_remaining = 1.1
		_reverse_turn = 0.75 if unit_id % 2 == 0 else -0.75
		_stuck_clock = 0.0
		return
	while route.size() > 1 and _flat_distance(global_position, route[0]) < 5.0:
		route.pop_front()
	if route.is_empty():
		set_driver_command(0, 0, false)
		return
	var aim: Vector3 = route[0]
	var corner_distance: float = _flat_distance(global_position, aim)
	var offset: Vector3 = aim - global_position
	offset.y = 0.0
	if offset.length() < 0.4:
		set_driver_command(0, 0, true)
		return
	var angle: float = (-global_basis.z).signed_angle_to(offset.normalized(), Vector3.UP)
	var turn: float = clampf(-angle / 0.55, -1.0, 1.0)
	var desired: float = tuning.maximum_speed_mps
	desired *= lerpf(1.0, 0.22, clampf(absf(angle) / 1.0, 0.0, 1.0))
	if route.size() > 1:
		var next: Vector3 = (route[1] - aim).normalized()
		if absf(offset.normalized().dot(next)) < 0.8:
			desired = minf(desired, sqrt(8.0 * 8.0 + 2.0 * 12.0 * maxf(0.0, corner_distance - 5.0)))
	elif distance_to_player < 12.0 and target.velocity.length() < 4.0:
		desired = minf(desired, maxf(0.0, (distance_to_player - 4.5) * 2.5))
	var ray := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP, global_position + Vector3.UP - global_basis.z * 7.0, 5, [get_rid()])
	var hit: Dictionary = get_world_3d().direct_space_state.intersect_ray(ray)
	if not hit.is_empty():
		var obstruction_distance: float = global_position.distance_to(hit.position as Vector3)
		desired = minf(desired, maxf(3.0, obstruction_distance * 1.5))
		if hit.collider is PoliceVehicle:
			turn += 0.45 if unit_id % 2 == 0 else -0.45
	var gas: float = desired / tuning.maximum_speed_mps
	if forward_speed > desired + 2.0:
		gas = -0.4
	set_driver_command(gas, clampf(turn, -1.0, 1.0), false)

func _clear_to(at: Vector3) -> bool:
	var query := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP, Vector3(at.x, global_position.y + 1.0, at.z), 1)
	return get_world_3d().direct_space_state.intersect_ray(query).is_empty()

func _flat_distance(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()

func silence() -> void:
	get_node("Presentation").silence()
