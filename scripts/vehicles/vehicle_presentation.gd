class_name CarPresentation
extends Node3D
## Smooth travel and wheel rotation; authored body poses held at twelve samples/second.

@export var pose_rate_hz: float = 12.0
@onready var vehicle: ArcadeVehicle = get_parent() as ArcadeVehicle
@onready var chassis: Node3D = $Model/Lowcar_Red_Muscle/Chassis
@onready var trunk: Node3D = $Model/Lowcar_Red_Muscle/Chassis/TrunkHinge
@onready var wheels: Node3D = $Model/Lowcar_Red_Muscle/Wheels
@onready var launcher_foot: Node3D = $LauncherFoot
@onready var pose: Node3D = $Pose
@onready var tire_pose: Node3D = $Pose/Tires
@onready var trunk_pose: Node3D = $Pose/Trunk
@onready var foot_pose: Node3D = $Pose/Foot
@onready var crash_pose: Node3D = $Pose/Crash
@onready var animation: AnimationPlayer = $AnimationPlayer
@onready var accents: CarMotionAccents = $MotionAccents

var current_clip: String = ""
var pose_sample_count: int = 0
var turn_serial: int = 0
var last_landing_speed: float = 0.0
var last_landing_category: String = ""
var turn_gain: float = 1.0
var jump_roll: float = 0.0
var _pose_clock: float = 0.0
var _exclusive_clock: float = 0.0
var _exclusive_kind: String = ""
var _rng := RandomNumberGenerator.new()
var _last_variants: Dictionary = {}
var _wheel_rest: Dictionary = {}
var _turn_direction: int = 0
var _turn_handbrake: bool = false
var _was_grounded: bool = false
var _has_grounded: bool = false
var _previous_throttle: float = 0.0
var _was_braking: bool = false
var _landing_gain: float = 1.0
var _trunk_bias: float = 0.0
var _preview_mode: bool = false
var _crashed: bool = false
var _first_pose_pending: bool = false
var _rendered_pose: Dictionary = {}
var _transition_from: Dictionary = {}
var _transition_elapsed: float = 0.0
var _transition_duration: float = 0.0
var boost_exhaust: BoostExhaust
var crash_effects: CarCrashEffects


func _ready() -> void:
	set_as_top_level(true)
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	global_transform = vehicle.global_transform
	animation.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	for wheel: Node3D in wheels.get_children():
		_wheel_rest[wheel.name] = wheel.position
	var launcher := vehicle.get_node("Attachments/GroundPunch") as LauncherAttachment
	launcher.activated.connect(_on_launch)
	vehicle.landed.connect(_on_land)
	vehicle.crashed.connect(_on_crash)
	vehicle.boost_released.connect(_on_boost_release)
	crash_effects = CarCrashEffects.new()
	crash_effects.name = "CrashEffects"
	add_child(crash_effects)
	crash_effects.setup($Model, chassis, wheels)
	boost_exhaust = BoostExhaust.new()
	chassis.add_child(boost_exhaust)
	reset_pose(1)


func _process(delta: float) -> void:
	global_transform = vehicle.get_global_transform_interpolated()
	_exclusive_clock = maxf(0.0, _exclusive_clock - delta)
	if not _preview_mode:
		_select_clip()
	for wheel: Node3D in wheels.get_children():
		var front: bool = wheel.name.begins_with("Front")
		var radius: float = 0.445 if front else 0.48
		var spin := wheel.get_node(String(wheel.name) + "Steer/" + String(wheel.name) + "Spin") as Node3D
		spin.rotation.x = fmod(spin.rotation.x - vehicle.forward_speed * delta / radius, TAU)
		(wheel.get_node(String(wheel.name) + "Steer") as Node3D).rotation.y = -vehicle.steering * 0.32 if front else 0.0
	accents.tick(delta,global_transform,vehicle.forward_speed,vehicle.steering,vehicle.is_on_floor(),vehicle.controls_enabled and not _crashed)
	_pose_clock += delta
	var quantum: float = 1.0 / maxf(pose_rate_hz, 1.0)
	var steps: int = int(floor((_pose_clock + 0.000001) / quantum))
	if steps > 0:
		_pose_clock -= steps * quantum
		_transition_elapsed += steps * quantum
		animation.advance(steps * quantum)
		_apply_pose()
		pose_sample_count += steps
		_first_pose_pending = false
	elif _first_pose_pending:
		_apply_pose()
		_first_pose_pending = false
	boost_exhaust.tick(delta,vehicle.boost,vehicle.tuning,vehicle.controls_enabled and not _crashed,vehicle.is_on_floor())


func _select_clip() -> void:
	var grounded: bool = vehicle.is_on_floor()
	if grounded:
		_has_grounded = true
	if _exclusive_clock > 0.0 and (_exclusive_kind.begins_with("land_") or _exclusive_kind.begins_with("crash_") or _exclusive_kind == "launch"):
		# Let the impact read first, then respond to new driving before its quiet tail ends.
		var impact_read_time: float = 4.0 / pose_rate_hz if last_landing_category == "soft" else 6.0 / pose_rate_hz
		var driving_request: bool = absf(vehicle.forward_speed) > 3.0 and (absf(vehicle.steering) > 0.22 or vehicle.handbrake_active or vehicle.throttle * vehicle.forward_speed < -2.0)
		if _exclusive_kind.begins_with("land_") and animation.current_animation_position >= impact_read_time and driving_request:
			_exclusive_clock = 0.0
		else:
			_was_grounded = grounded
			return
	if _crashed:
		# Hold the authored wreck after the clip finishes; restart restores the intact car.
		return
	if not vehicle.controls_enabled:
		_play("idle")
		_previous_throttle = 0.0
		_was_grounded = grounded
		return
	if not grounded and _has_grounded:
		if _was_grounded:
			_choose_jump_style()
		if vehicle.velocity.y > 2.5:
			_play("air_rise")
		elif vehicle.velocity.y < -2.5:
			_play("air_drop")
		else:
			_play("air_hang")
		_turn_direction = 0
		_was_grounded = false
		return
	_was_grounded = grounded
	var moving: bool = absf(vehicle.forward_speed) > 3.0
	var direction: int = int(signf(vehicle.steering)) if moving and absf(vehicle.steering) > (0.12 if _turn_direction != 0 else 0.22) else 0
	if direction != 0:
		var handbrake: bool = vehicle.handbrake_active
		var side: String = "left" if direction < 0 else "right"
		if direction != _turn_direction or handbrake != _turn_handbrake:
			_turn_direction = direction
			_turn_handbrake = handbrake
			turn_serial += 1
			turn_gain = _rng.randf_range(0.965, 1.035)
			var clip: String = "handbrake_" + side if handbrake else _variant("turn_" + side, 3)
			_play(clip, true)
		elif not handbrake and animation.current_animation_position >= animation.current_animation_length - 0.001:
			_play("turn_" + side + "_hold")
		_previous_throttle = vehicle.throttle
		return
	if _turn_direction != 0:
		_turn_direction = 0
		_play("recover", true)
		_previous_throttle = vehicle.throttle
		return
	var braking: bool = vehicle.handbrake_active or (absf(vehicle.throttle) > 0.1 and signf(vehicle.throttle) != signf(vehicle.forward_speed) and absf(vehicle.forward_speed) > 2.0)
	if braking:
		if not _was_braking:
			_play("brake", true)
	elif _was_braking:
		_play("recover", true)
	elif absf(vehicle.throttle) > 0.15 and absf(_previous_throttle) < 0.15:
		_play("accelerate", true)
	elif current_clip in ["accelerate", "brake", "recover"] and animation.current_animation_position < animation.current_animation_length - 0.001:
		pass
	else:
		_play("drive" if moving else "idle")
	_was_braking = braking
	_previous_throttle = vehicle.throttle


func _play(clip: String, exclusive: bool = false) -> void:
	if current_clip == clip:
		return
	var previous_clip: String = current_clip
	_transition_from = _rendered_pose.duplicate()
	_transition_elapsed = 0.0
	_transition_duration = _transition_time(clip, previous_clip)
	current_clip = clip
	animation.play("car/" + clip, 0.0)
	animation.advance(0.0)
	_first_pose_pending = true
	if exclusive:
		_exclusive_clock = animation.current_animation_length
		_exclusive_kind = clip


func _transition_time(clip: String, previous: String) -> float:
	if _preview_mode or _rendered_pose.is_empty() or clip == "RESET" or clip == "launch" or clip == "explode" or clip.begins_with("land_") or clip.begins_with("crash_"):
		return 0.0
	if clip == "recover":
		return 3.0 / maxf(pose_rate_hz, 1.0)
	if clip.begins_with("turn_") and not (previous.begins_with("turn_") or previous.begins_with("handbrake_")):
		return 1.0 / maxf(pose_rate_hz, 1.0)
	return 2.0 / maxf(pose_rate_hz, 1.0)


func _apply_pose() -> void:
	var body_scale: Vector3 = pose.scale
	var body_rotation: Vector3 = pose.rotation
	var tire_scale: Vector3 = tire_pose.scale
	var tire_offset: Vector3 = tire_pose.position
	var lid_rotation: Vector3 = trunk_pose.rotation
	var is_turn: bool = current_clip.begins_with("turn_") or current_clip.begins_with("handbrake_")
	if is_turn and not _preview_mode:
		var strength: float = absf(vehicle.steering) * clampf(absf(vehicle.forward_speed) / 10.0, 0.0, 1.0) * turn_gain
		body_rotation *= strength
		body_scale = Vector3.ONE + (body_scale - Vector3.ONE) * strength
	if current_clip.begins_with("land_") and not _preview_mode:
		body_scale = Vector3.ONE + (body_scale - Vector3.ONE) * _landing_gain
	if current_clip.begins_with("air_") and not _preview_mode:
		body_rotation.z += jump_roll - deg_to_rad(vehicle.steering * 1.2)
		if current_clip == "air_drop":
			var fall_load: float = clampf(-vehicle.velocity.y / 24.0, 0.0, 1.0)
			body_rotation.x += deg_to_rad(lerpf(1.5, -1.8, fall_load))
			lid_rotation.x = deg_to_rad(lerpf(-10.0, -20.0, fall_load)) + (lid_rotation.x + deg_to_rad(16.0)) * 0.35 + _trunk_bias
	if current_clip in ["accelerate", "brake"] and not _preview_mode:
		var travel_sign: float = signf(vehicle.forward_speed) if absf(vehicle.forward_speed) > 0.4 else signf(vehicle.throttle)
		body_rotation.x *= travel_sign
	if not _preview_mode and not _crashed and not current_clip.begins_with("land_"):
		if vehicle.boost.phase == ChargeBoost.Phase.CHARGING:
			var charge: float = vehicle.boost.charge_ratio(vehicle.tuning)
			var rumble: float = sin(vehicle.boost.charge_seconds*21.0)*charge*0.008
			body_scale *= Vector3(1.0+charge*0.045,1.0-charge*0.09+rumble,1.0)
			body_rotation.x -= deg_to_rad(1.0+charge*2.0)
		elif vehicle.boost.phase == ChargeBoost.Phase.BOOSTING and vehicle.is_on_floor():
			var kick_weight: float = maxf(0.0,1.0-vehicle.boost.elapsed/0.35)
			body_scale *= Vector3(1.0-kick_weight*0.025,1.0+kick_weight*0.085,1.0+kick_weight*0.035)
			body_rotation.x += deg_to_rad(1.0+kick_weight*3.0)*lerpf(0.65,1.0,vehicle.boost.power)
	var target: Dictionary = {"scale": body_scale, "rotation": body_rotation, "offset": pose.position,
		"tire_scale": tire_scale, "tire_offset": tire_offset, "trunk": lid_rotation, "foot": foot_pose.position}
	if not _preview_mode and _transition_duration > 0.0 and _transition_elapsed < _transition_duration:
		var weight: float = clampf(_transition_elapsed / _transition_duration, 0.0, 1.0)
		weight = 1.0 - pow(1.0 - weight, 3.0)
		for property: String in target:
			target[property] = (_transition_from[property] as Vector3).lerp(target[property], weight)
	_rendered_pose = target
	body_scale = target.scale
	body_rotation = target.rotation
	tire_scale = target.tire_scale
	tire_offset = target.tire_offset
	chassis.scale = body_scale
	chassis.rotation = body_rotation
	# Squash stays planted at ground level; banking pivots around the body center.
	var pivot: Vector3 = Vector3(0.0, 0.78, 0.0) * body_scale
	chassis.position = pivot - Basis.from_euler(body_rotation) * pivot + target.offset
	if not _preview_mode and vehicle.is_on_floor() and vehicle.boost.phase == ChargeBoost.Phase.BOOSTING:
		var left_pipe: Vector3 = chassis.transform*Vector3(-0.76,0.363,2.55)
		var right_pipe: Vector3 = chassis.transform*Vector3(0.76,0.363,2.55)
		chassis.position.y += maxf(0.0,0.21*body_scale.y-minf(left_pipe.y,right_pipe.y))
	lid_rotation = target.trunk
	trunk.rotation = Vector3(clampf(lid_rotation.x, deg_to_rad(-24.0), deg_to_rad(3.0)), 0.0, 0.0)
	for wheel: Node3D in wheels.get_children():
		var rest: Vector3 = _wheel_rest[wheel.name]
		# Outside / rear tires visibly take weight; their contact patch stays on the road.
		var bank_load: float = clampf(-rest.x * body_rotation.z * 0.7, -0.10, 0.10)
		var pitch_load: float = clampf(rest.z * body_rotation.x * 0.45, -0.075, 0.075)
		var load: float = bank_load + pitch_load
		var wheel_scale: Vector3 = tire_scale
		wheel_scale.y = maxf(0.3, tire_scale.y - load)
		wheel_scale.x += maxf(load, 0.0) * 0.24
		wheel.scale = wheel_scale
		wheel.position = Vector3(rest.x * body_scale.x, rest.y * wheel_scale.y + tire_offset.y, rest.z * body_scale.z)
	launcher_foot.position = target.foot
	crash_effects.apply(current_clip, animation.current_animation_position, crash_pose.position)
	launcher_foot.visible = current_clip != "explode" or animation.current_animation_position < 0.5


func _variant(prefix: String, count: int) -> String:
	var choice: int = _rng.randi_range(0, count - 1)
	if choice == int(_last_variants.get(prefix, -1)):
		choice = (choice + 1 + _rng.randi_range(0, count - 2)) % count
	_last_variants[prefix] = choice
	return prefix + "_" + String.chr(97 + choice)


func _choose_jump_style() -> void:
	jump_roll = deg_to_rad(_rng.randf_range(-0.9, 0.9))
	_trunk_bias = deg_to_rad(_rng.randf_range(-1.2, 1.2))


func _on_launch() -> void:
	if _preview_mode or _crashed:
		return
	_choose_jump_style()
	_play("launch", true)
	accents.burst(vehicle.global_transform, false, 0.6)


func _on_boost_release(_power: float) -> void:
	if _preview_mode or _crashed:
		return
	boost_exhaust.ignite(_power,vehicle.is_on_floor())
	if vehicle.is_on_floor() and not current_clip.begins_with("land_"):
		_play("accelerate", true)


func _on_land(speed: float) -> void:
	if _preview_mode or _crashed or speed < 4.0 or not vehicle.controls_enabled:
		return
	last_landing_speed = speed
	last_landing_category = "soft" if speed < 9.0 else ("medium" if speed < 17.0 else "hard")
	_landing_gain = _rng.randf_range(0.985, 1.015)
	_play(_variant("land_" + last_landing_category, 2 if last_landing_category == "soft" else 3), true)
	# Contact is a fresh held drawing, rather than one more render of the falling car.
	_apply_pose()
	_first_pose_pending = false
	_turn_direction = 0
	accents.burst(vehicle.global_transform, true, clampf(speed / 24.0, 0.3, 1.2))


func _on_crash(_reason: String) -> void:
	if _preview_mode:
		return
	_crashed = true
	var normal: Vector3 = vehicle.crash_local_normal
	var clip: String = "crash_front"
	if absf(normal.x) > absf(normal.z):
		clip = "crash_left" if normal.x > 0.0 else "crash_right"
	_play(clip, true)
	# Physics has already reached the wall: begin at the contact drawing, not the lead-in.
	animation.seek(2.0 / pose_rate_hz, true)
	_apply_pose()
	_first_pose_pending = false
	accents.burst(vehicle.global_transform, true, 1.2)


func play_explosion() -> void:
	# Explicit visual trigger, independent of collision. No random explosion gameplay rule.
	_crashed = true
	vehicle.stop_vehicle()
	_play("explode", true)
	_apply_pose()


func reset_pose(seed_value: int = 1) -> void:
	_rng.seed = seed_value
	_last_variants.clear()
	_pose_clock = 0.0
	_exclusive_clock = 0.0
	_exclusive_kind = ""
	_previous_throttle = 0.0
	_was_braking = false
	_turn_direction = 0
	_turn_handbrake = false
	_has_grounded = false
	_was_grounded = false
	_crashed = false
	_preview_mode = false
	turn_serial = 0
	pose_sample_count = 0
	turn_gain = 1.0
	jump_roll = 0.0
	_landing_gain = 1.0
	_trunk_bias = 0.0
	_rendered_pose.clear()
	_transition_from.clear()
	_transition_elapsed = 0.0
	_transition_duration = 0.0
	last_landing_category = ""
	last_landing_speed = 0.0
	current_clip = ""
	crash_pose.position = Vector3.ZERO
	crash_effects.clear()
	_play("RESET")
	_apply_pose()
	for wheel: Node3D in wheels.get_children():
		(wheel.get_node(String(wheel.name) + "Steer/" + String(wheel.name) + "Spin") as Node3D).rotation = Vector3.ZERO
		(wheel.get_node(String(wheel.name) + "Steer") as Node3D).rotation = Vector3.ZERO
	accents.clear(seed_value)
	boost_exhaust.clear()
	global_transform = vehicle.global_transform


func preview_clip(clip: String) -> void:
	crash_effects.clear()
	crash_pose.position = Vector3.ZERO
	_preview_mode = true
	_exclusive_clock = 0.0
	current_clip = ""
	_play(clip)
	_apply_pose()


func preview_frame(frame: int) -> void:
	animation.seek(frame / pose_rate_hz, true)
	_apply_pose()


func snapshot() -> Dictionary:
	return {"clip": current_clip, "body_scale": chassis.scale, "body_rotation": chassis.rotation, "trunk_angle": trunk.rotation.x,
		"clip_time": animation.current_animation_position, "samples": pose_sample_count,
		"turn_serial": turn_serial, "turn_gain": turn_gain, "jump_roll": jump_roll,
		"landing_speed": last_landing_speed, "landing_category": last_landing_category}
