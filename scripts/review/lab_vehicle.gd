class_name LabVehicle
extends ArcadeVehicle
## The city lab's car: same body, input and visuals as the game car, driven by the CarHandling
## experiment (sharp steering, a real drift, wall scrapes that keep speed). The main game still
## drives ArcadeVehicle unchanged. The lab never ends a run, so walls never emit crashed.

const WALL_DRAG: float = 4.0
## Health lost per hit: walls scale with how hard you hit them; cop contact only chips a little.
const WALL_DAMAGE_PER_MPS: float = 1.1
const WALL_DAMAGE_MAX: float = 40.0
const COP_DAMAGE_MIN: float = 2.0
const COP_DAMAGE_MAX: float = 6.0

signal damaged(amount: float, source: String)
signal destroyed

@export var handling: CarHandling
@export var max_health: float = 100.0
var health: float = 100.0
var takes_damage: bool = false
var drifting: bool = false
var drift_time: float = 0.0
var slip_angle: float = 0.0
var _steer: float = 0.0
var _grip_return: float = 1.0
var _wall_contact: bool = false


func _physics_process(delta: float) -> void:
	if tuning == null or handling == null:
		super._physics_process(delta)
		return
	var drive_input: float = throttle if controls_enabled else 0.0
	_update_drift(delta, absf(forward_speed))
	var handbrake_braking: bool = handbrake_active and not drifting
	boost.tick(delta, boost_held, controls_enabled, drive_input < -0.1 or handbrake_braking, tuning)
	var target_speed: float = drive_input * (tuning.maximum_speed_mps if drive_input >= 0.0 else tuning.reverse_speed_mps)
	var rate: float = tuning.acceleration_mps2
	if is_zero_approx(drive_input):
		rate = tuning.coasting_drag_mps2
	elif signf(drive_input) != signf(forward_speed) and absf(forward_speed) > 0.5:
		rate = tuning.braking_mps2
	if handbrake_braking and controls_enabled:
		target_speed *= 0.7
	if boost.phase == ChargeBoost.Phase.CHARGING:
		target_speed *= boost.charge_speed_multiplier(tuning)
		rate = maxf(rate, 10.0)
	elif boost.phase == ChargeBoost.Phase.BOOSTING:
		target_speed = boost.speed_limit(tuning)
		if boost.fired_this_tick:
			forward_speed = maxf(forward_speed, target_speed)
			var kick: Vector3 = -global_basis.z * forward_speed
			velocity.x = kick.x
			velocity.z = kick.z
			boost_released.emit(boost.power)
	elif forward_speed > tuning.maximum_speed_mps:
		rate = maxf(rate, 14.0)
	forward_speed = move_toward(forward_speed, target_speed, rate * delta)
	if drifting:
		forward_speed = move_toward(forward_speed, 0.0, handling.drift_speed_loss * delta)
	_steer_toward(delta)
	if controls_enabled and absf(forward_speed) > 0.2:
		var yaw: float = _yaw_rate(absf(forward_speed))
		if drifting:
			yaw *= handling.drift_steer_boost
		if not is_on_floor():
			yaw *= handling.air_steer
		rotation.y -= _steer * yaw * signf(forward_speed) * delta
	var desired: Vector3 = -global_basis.z * forward_speed
	var grip: float = _current_grip(delta)
	velocity.x = lerpf(velocity.x, desired.x, minf(grip * delta, 1.0))
	velocity.z = lerpf(velocity.z, desired.z, minf(grip * delta, 1.0))
	_limit_slip(desired)
	var was_grounded: bool = is_on_floor()
	if not was_grounded:
		velocity.y -= tuning.gravity_mps2 * delta
	elif velocity.y <= 0.0:
		velocity.y = -0.5
	var before_move: Vector3 = velocity
	move_and_slide()
	if not was_grounded and is_on_floor():
		landed.emit(absf(before_move.y))
	_resolve_walls(before_move)


func reset_vehicle(at: Vector3) -> void:
	super.reset_vehicle(at)
	drifting = false
	drift_time = 0.0
	slip_angle = 0.0
	_steer = 0.0
	_grip_return = 1.0
	_wall_contact = false
	health = max_health


## Swaps the box collider for the same box with its bottom edges chamfered, so curb lips and other
## small edges push the car up instead of catching a square corner (which reads as a wall hit).
func chamfer_collider(chamfer: float = 0.3) -> void:
	for child: Node in get_children():
		var holder := child as CollisionShape3D
		if holder == null or not (holder.shape is BoxShape3D):
			continue
		var half: Vector3 = (holder.shape as BoxShape3D).size * 0.5
		var points := PackedVector3Array()
		for x: float in [-half.x, half.x]:
			for z: float in [-half.z, half.z]:
				points.append(Vector3(x, half.y, z))
				points.append(Vector3(x, -half.y + chamfer, z))
				points.append(Vector3(x - signf(x) * chamfer, -half.y, z - signf(z) * chamfer))
		var shape := ConvexPolygonShape3D.new()
		shape.points = points
		holder.shape = shape


func apply_damage(amount: float, source: String) -> void:
	if not takes_damage or health <= 0.0 or amount <= 0.0:
		return
	health = maxf(0.0, health - amount)
	damaged.emit(amount, source)
	if health <= 0.0:
		destroyed.emit()


## Handbrake + steering above drift speed starts a drift; releasing it snaps grip back with a speed kick.
func _update_drift(delta: float, speed: float) -> void:
	if not drifting:
		if controls_enabled and handbrake_active and is_on_floor() and speed >= handling.drift_min_speed and absf(steering) > 0.2:
			drifting = true
			drift_time = 0.0
		return
	drift_time += delta
	if not handbrake_active or not controls_enabled or speed < handling.drift_min_speed * 0.6:
		drifting = false
		_grip_return = 0.0
		if drift_time > 0.6 and controls_enabled:
			forward_speed += handling.drift_exit_kick * signf(forward_speed)


## Keyboard steering eases in, so taps make small corrections; letting go or counter-steering is faster.
func _steer_toward(delta: float) -> void:
	var target: float = steering if controls_enabled else 0.0
	var response: float = handling.steer_response
	if absf(target) < absf(_steer) or signf(target) != signf(_steer):
		response *= 1.8
	_steer = move_toward(_steer, target, response * delta)


func _yaw_rate(speed: float) -> float:
	var top: float = tuning.maximum_speed_mps
	if speed <= 14.0:
		return handling.steer_low_speed * clampf(speed / 6.0, 0.0, 1.0)
	if speed <= top:
		return lerpf(handling.steer_low_speed, handling.steer_top_speed, (speed - 14.0) / maxf(top - 14.0, 0.01))
	var boosted: float = clampf((speed - top) / maxf(tuning.boost_max_speed_mps - top, 0.01), 0.0, 1.0)
	return lerpf(handling.steer_top_speed, handling.steer_boost_speed, boosted)


func _current_grip(delta: float) -> float:
	if drifting:
		return handling.drift_grip
	_grip_return = move_toward(_grip_return, 1.0, delta / 0.3)
	var base: float = tuning.handbrake_grip if handbrake_active else handling.grip
	return lerpf(handling.drift_grip, base, _grip_return)


## Caps how sideways the car can travel, so a held drift turns the path at the steering rate.
func _limit_slip(desired: Vector3) -> void:
	var travel := Vector2(velocity.x, velocity.z)
	var heading := Vector2(desired.x, desired.z)
	if travel.length() < 2.0 or heading.length() < 2.0:
		slip_angle = 0.0
		return
	slip_angle = heading.angle_to(travel)
	var cap: float = deg_to_rad(handling.drift_max_angle if drifting else 25.0)
	if absf(slip_angle) > cap:
		travel = travel.rotated(-(slip_angle - signf(slip_angle) * cap))
		velocity.x = travel.x
		velocity.z = travel.y
		slip_angle = signf(slip_angle) * cap


## Glancing hits keep most of the speed and turn the car along the wall; head-on hits still stop it.
## The hit costs speed once; grinding along the wall afterwards only drags a little.
func _resolve_walls(before_move: Vector3) -> void:
	var flat_speed: float = Vector2(before_move.x, before_move.z).length()
	var worst: float = -1.0
	var worst_normal := Vector3.ZERO
	var worst_impact: float = 0.0
	var hit_police: bool = false
	for index: int in range(get_slide_collision_count()):
		var collision: KinematicCollision3D = get_slide_collision(index)
		var normal: Vector3 = collision.get_normal()
		if absf(normal.y) >= 0.5:
			continue
		var impact: float = maxf(-before_move.dot(normal), 0.0)
		var ratio: float = clampf(impact / maxf(flat_speed, 1.0), 0.0, 1.0)
		if ratio > worst:
			worst = ratio
			worst_normal = normal
			worst_impact = impact
			var collider: Object = collision.get_collider()
			hit_police = collider is Node and (collider as Node).is_in_group("police")
	if worst < 0.0:
		# The engine can stop the car on a wall without reporting the contact that frame;
		# catch that from the speed the move actually lost.
		var lost := Vector3(before_move.x - velocity.x, 0.0, before_move.z - velocity.z)
		if lost.length() < 4.0 or flat_speed < 1.0:
			_wall_contact = false
			return
		worst_normal = -lost.normalized()
		worst_impact = lost.length()
		worst = clampf(worst_impact / flat_speed, 0.0, 1.0)
	if not _wall_contact or worst > 0.6:
		forward_speed *= lerpf(handling.wall_glance_keep, handling.wall_head_on_keep, pow(worst, 1.5))
		if hit_police:
			apply_damage(clampf(worst_impact * 0.25, COP_DAMAGE_MIN, COP_DAMAGE_MAX), "cop")
		elif worst_impact > 5.0:
			apply_damage(minf((worst_impact - 5.0) * WALL_DAMAGE_PER_MPS, WALL_DAMAGE_MAX), "crash")
	else:
		forward_speed = move_toward(forward_speed, 0.0, WALL_DRAG * get_physics_process_delta_time())
	_wall_contact = true
	if worst < 0.6 and handling.wall_align > 0.0:
		var along := Vector3(-worst_normal.z, 0.0, worst_normal.x)
		if along.dot(Vector3(before_move.x, 0.0, before_move.z)) < 0.0:
			along = -along
		var along_yaw: float = atan2(-along.x, -along.z)
		if forward_speed < 0.0:
			along_yaw += PI
		rotation.y = lerp_angle(rotation.y, along_yaw, handling.wall_align)
