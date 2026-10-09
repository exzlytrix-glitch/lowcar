class_name ArcadeVehicle
extends CharacterBody3D
## Responsive blockout controller. Replace handling here without coupling it to the car mesh.

signal crashed(reason: String)
signal landed(vertical_speed_mps: float)
signal boost_released(power: float)

@export var tuning: VehicleTuning
var controls_enabled: bool = false
var forward_speed: float = 0.0
var steering: float = 0.0
var throttle: float = 0.0
var handbrake_active: bool = false
var boost_held: bool = false
var boost := ChargeBoost.new()
var _terminal_collision: bool = false
var crash_local_normal: Vector3 = Vector3.BACK


func _physics_process(delta: float) -> void:
	if tuning == null:
		return
	var drive_input: float = throttle if controls_enabled else 0.0
	boost.tick(delta,boost_held,controls_enabled,drive_input < -0.1 or handbrake_active,tuning)
	var target_speed: float = drive_input * (tuning.maximum_speed_mps if drive_input >= 0.0 else tuning.reverse_speed_mps)
	var rate: float = tuning.acceleration_mps2
	if is_zero_approx(drive_input):
		rate = tuning.coasting_drag_mps2
	elif signf(drive_input) != signf(forward_speed) and absf(forward_speed) > 0.5:
		rate = tuning.braking_mps2
	if handbrake_active and controls_enabled:
		target_speed *= 0.7
	if boost.phase == ChargeBoost.Phase.CHARGING:
		target_speed *= boost.charge_speed_multiplier(tuning)
		rate = maxf(rate,10.0)
	elif boost.phase == ChargeBoost.Phase.BOOSTING:
		target_speed = boost.speed_limit(tuning)
		if boost.fired_this_tick:
			forward_speed = maxf(forward_speed,target_speed)
			var kick: Vector3 = -global_basis.z*forward_speed
			velocity.x = kick.x
			velocity.z = kick.z
			boost_released.emit(boost.power)
	elif forward_speed > tuning.maximum_speed_mps:
		rate = maxf(rate,14.0)
	forward_speed = move_toward(forward_speed, target_speed, rate * delta)
	if controls_enabled and absf(forward_speed) > 0.2:
		var steering_factor: float = clampf(absf(forward_speed) / 12.0, 0.0, 1.0)
		rotation.y -= steering * tuning.steering_radians_per_second * steering_factor * signf(forward_speed) * delta
	var desired: Vector3 = -global_basis.z * forward_speed
	var grip: float = tuning.handbrake_grip if handbrake_active else tuning.road_grip
	velocity.x = lerpf(velocity.x, desired.x, minf(grip * delta, 1.0))
	velocity.z = lerpf(velocity.z, desired.z, minf(grip * delta, 1.0))
	var was_grounded: bool = is_on_floor()
	if not was_grounded:
		velocity.y -= tuning.gravity_mps2 * delta
	elif velocity.y <= 0.0:
		velocity.y = -0.5
	var before_move: Vector3 = velocity
	move_and_slide()
	if not was_grounded and is_on_floor():
		landed.emit(absf(before_move.y))
	for index: int in range(get_slide_collision_count()):
		var collision: KinematicCollision3D = get_slide_collision(index)
		if absf(collision.get_normal().y) < 0.5:
			var impact: float = maxf(-before_move.dot(collision.get_normal()), 0.0)
			# Patrol contact starts a pin/capture, while a hard wall impact still ends the run.
			var hit_police: bool = collision.get_collider() is Node and collision.get_collider().is_in_group("police")
			if impact >= tuning.terminal_impact_speed_mps and controls_enabled and not _terminal_collision and not hit_police:
				_terminal_collision = true
				crash_local_normal = global_basis.inverse() * collision.get_normal()
				crashed.emit("CRASHED")
			if impact > 1.0:
				forward_speed *= 0.35


func set_driver_command(acceleration: float, turn: float, handbrake: bool, charge_boost: bool = false) -> void:
	throttle = clampf(acceleration, -1.0, 1.0)
	steering = clampf(turn, -1.0, 1.0)
	handbrake_active = handbrake
	boost_held = charge_boost


func reset_vehicle(at: Vector3) -> void:
	global_position = at
	rotation = Vector3.ZERO
	velocity = Vector3.ZERO
	forward_speed = 0.0
	_terminal_collision = false
	crash_local_normal = Vector3.BACK
	boost.clear()
	set_driver_command(0.0, 0.0, false)
	reset_physics_interpolation()


func stop_vehicle() -> void:
	controls_enabled = false
	forward_speed = 0.0
	velocity = Vector3.ZERO
	boost.clear()
	set_driver_command(0.0, 0.0, false)
