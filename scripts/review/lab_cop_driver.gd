class_name LabCopDriver
extends Node
## Scripted police driver for the city lab. It presses the same controls a player does (throttle,
## steer, handbrake), so cops slide, drift, overshoot corners and crash under the same physics as
## the red car.
##
## Attacks: a cop close to you asks the chase for an attack slot, shows a "!" while it winds up,
## then commits to the move for a moment without dodging anything (that is where cops end up in
## each other) and swings wide to recover. Moves: rear ram, side slam, PIT (clip the rear corner
## to spin you), brake check (get ahead in your lane and stand on the brakes), and charge (any cop
## facing you floors it into you; against a slow or stopped car every nearby cop does, backing up
## and charging again, because stopping should be deadly).

const SIGHT_RANGE: float = 70.0
const TAIL_GAP: float = 10.0
## Speed a cop is willing to carry into a 90° corner; it drifts through instead of braking down.
const CORNER_SPEED: float = 21.0
const FULL_LOCK_ANGLE: float = 0.5

var chase: LabChase
var car: LabVehicle
var target: LabVehicle
## Above 1.0 the cop brakes later than its car really can, so it overshoots corners more.
var lateness: float = 1.0
var mode: String = "route"
var route := PackedVector2Array()
var _route_index: int = 0
var _route_clock: float = 0.0
var _sight_clock: float = 0.0
var _sees_target: bool = false
var _stuck_clock: float = 0.0
var _reverse_left: float = 0.0
var _reverse_steer: float = 0.0
var _last_steer: float = 0.0

enum Phase { NONE, WINDUP, COMMIT, RECOVER }
const ATTACK_RANGE: float = 32.0
## Below this speed (m/s) you count as stopped: no attack-slot limit, quick repeat charges.
const STOPPED_SPEED: float = 4.0
const SLOW_SPEED: float = 8.0
## True while ramming: the chase lets the cop exceed its normal top speed.
var burst: bool = false
var phase: Phase = Phase.NONE
var attack: String = ""
var _phase_left: float = 0.0
var _cooldown: float = 0.0
var _side: float = 1.0
var _warning: Label3D


func _ready() -> void:
	_cooldown = randf_range(1.0, 3.0)
	_warning = Label3D.new()
	_warning.text = "!"
	_warning.font_size = 160
	_warning.pixel_size = 0.012
	_warning.outline_size = 36
	_warning.modulate = Color("#FFD400")
	_warning.outline_modulate = Color("#24394B")
	_warning.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_warning.no_depth_test = true
	_warning.position = Vector3(0.0, 3.4, 0.0)
	_warning.visible = false
	car.add_child.call_deferred(_warning)
	car.bumped.connect(_on_bumped)


func _exit_tree() -> void:
	if chase != null:
		chase.release_attack(self)

func _physics_process(delta: float) -> void:
	if car == null:
		return
	if not chase.active or not is_instance_valid(target) or not car.controls_enabled:
		car.set_driver_command(0.0, 0.0, true)
		return
	var here: Vector2 = _flat(car.global_position)
	var goal: Vector2 = _flat(target.global_position)
	var distance: float = here.distance_to(goal)
	_sight_clock -= delta
	if _sight_clock <= 0.0:
		_sight_clock = 0.2 + randf() * 0.05
		_sees_target = distance < SIGHT_RANGE and _clear_line()
	_update_attack(delta, distance)
	if _reverse_left > 0.0:
		_reverse_left -= delta
		car.set_driver_command(-1.0, _reverse_steer, false)
		return
	var target_velocity: Vector2 = _flat(target.velocity)
	var aim: Vector2
	var desired: float
	if phase == Phase.RECOVER and target_velocity.length() < SLOW_SPEED and distance < 16.0:
		# Back straight up for a run-up, then charge the stopped car again.
		car.set_driver_command(-1.0, 0.0, false)
		return
	if phase == Phase.WINDUP or phase == Phase.COMMIT:
		var plan: Array = _attack_plan(here, goal, target_velocity)
		aim = plan[0]
		desired = plan[1]
	elif _sees_target and target_velocity.length() < SLOW_SPEED:
		# You are slow or stopped: close in hard instead of matching your speed.
		mode = "direct"
		aim = goal
		desired = car.tuning.maximum_speed_mps
	elif _sees_target:
		mode = "direct"
		if distance < TAIL_GAP * 2.0:
			# Close but no attack slot yet: hang off your rear quarter, ready to go.
			var ahead: Vector2 = _flat(-target.global_basis.z).normalized()
			var right: Vector2 = _flat(target.global_basis.x).normalized()
			aim = goal - ahead * (TAIL_GAP + 4.0) + right * _side * 3.5
			desired = target_velocity.length() + clampf((distance - TAIL_GAP - 4.0) * 0.8, -6.0, 6.0)
		else:
			var lead: float = clampf(distance / maxf(absf(car.forward_speed) + 5.0, 10.0), 0.15, 0.9)
			aim = goal + target_velocity * lead
			desired = car.tuning.maximum_speed_mps
	else:
		mode = "route"
		_route_clock -= delta
		if _route_clock <= 0.0 or route.is_empty():
			_route_clock = 0.45 + randf() * 0.15
			_plan_route(here, goal + target_velocity * 1.2)
		aim = _route_aim(here)
		desired = _route_speed(here)
	_drive(here, aim, desired, delta)


# --- attacks -----------------------------------------------------------------

func _update_attack(delta: float, distance: float) -> void:
	_cooldown -= delta
	if phase != Phase.NONE:
		_phase_left -= delta
		if _phase_left <= 0.0:
			_next_phase()
		return
	if not _sees_target or _cooldown > 0.0 or distance > ATTACK_RANGE:
		return
	var kind: String = _choose_attack()
	if kind.is_empty():
		return
	var stopped: bool = _flat(target.velocity).length() < STOPPED_SPEED
	if not chase.claim_attack(self, stopped):
		return
	attack = kind
	phase = Phase.WINDUP
	_phase_left = chase.windup_time()
	mode = "windup"
	_warning.visible = true


func _next_phase() -> void:
	match phase:
		Phase.WINDUP:
			phase = Phase.COMMIT
			_phase_left = chase.commit_time()
			mode = attack
			burst = attack == "ram" or (attack == "charge" and _flat(target.velocity).length() < SLOW_SPEED)
			_warning.visible = false
		Phase.COMMIT:
			_end_attack()
		Phase.RECOVER:
			phase = Phase.NONE
			mode = "direct"


func _end_attack() -> void:
	phase = Phase.RECOVER
	_phase_left = randf_range(0.8, 1.4)
	mode = "recover"
	burst = false
	_warning.visible = false
	_cooldown = 1.0 if _flat(target.velocity).length() < SLOW_SPEED else chase.attack_cooldown()
	chase.release_attack(self)


func _on_bumped(other: LabVehicle, _strength: float) -> void:
	if phase == Phase.COMMIT and other == target:
		_end_attack()


## Picks the move that fits where this cop is relative to you right now.
func _choose_attack() -> String:
	var t_forward: Vector2 = _flat(-target.global_basis.z).normalized()
	var t_right: Vector2 = _flat(target.global_basis.x).normalized()
	var offset: Vector2 = _flat(car.global_position) - _flat(target.global_position)
	var along: float = offset.dot(t_forward)
	var lateral: float = offset.dot(t_right)
	var cop_forward: Vector2 = _flat(-car.global_basis.z).normalized()
	var aligned: float = cop_forward.dot(t_forward)
	var facing: float = cop_forward.dot(-offset.normalized())
	_side = 1.0 if lateral >= 0.0 else -1.0
	# Pointed at you and close: charge. Any direction on a slow car; on a moving car only from the
	# side (a T-bone), never head-on into your nose at combined top speeds.
	if facing > 0.8 and offset.length() < 30.0:
		if _flat(target.velocity).length() < SLOW_SPEED or absf(aligned) < 0.5:
			return "charge"
	if aligned < 0.5:
		return ""
	if along < -4.0 and along > -28.0 and absf(lateral) < 3.0:
		return "ram"
	if along > -7.0 and along < 2.0 and absf(lateral) > 1.8 and absf(lateral) < 8.0:
		return "pit" if along < -2.5 else "slam"
	if along > 6.0 and along < 35.0 and absf(lateral) < 3.0 and aligned > 0.7:
		return "brake"
	return ""


## [aim point, desired speed] for the current attack phase.
func _attack_plan(here: Vector2, goal: Vector2, target_velocity: Vector2) -> Array:
	var t_forward: Vector2 = _flat(-target.global_basis.z).normalized()
	var t_right: Vector2 = _flat(target.global_basis.x).normalized()
	var speed: float = target_velocity.length()
	var winding: bool = phase == Phase.WINDUP
	match attack:
		"ram":
			if winding:
				return [goal - t_forward * 9.0, speed - 1.0]
			return [goal + target_velocity * 0.15, speed + 15.0]
		"slam":
			if winding:
				return [goal + t_right * _side * 5.5, speed]
			return [goal - t_right * _side * 2.0 + t_forward * 1.0, speed + 4.0]
		"pit":
			if winding:
				return [goal - t_forward * 3.5 + t_right * _side * 2.5, speed + 1.0]
			return [goal - t_forward * 1.8 - t_right * _side * 2.5, speed + 6.0]
		"charge":
			if winding:
				return [goal, 6.0]
			return [goal + target_velocity * 0.2, car.tuning.maximum_speed_mps]
		"brake":
			var ahead: float = (here - goal).dot(t_forward)
			if winding:
				return [goal + t_forward * maxf(ahead, 8.0), speed + 2.0]
			return [goal + t_forward * maxf(ahead, 8.0), 0.0]
	return [goal, speed]


func _drive(here: Vector2, aim: Vector2, desired: float, delta: float) -> void:
	var forward: Vector2 = _flat(-car.global_basis.z).normalized()
	var to_aim: Vector2 = aim - here
	if to_aim.length() < 0.5:
		to_aim = forward
	var angle: float = forward.angle_to(to_aim)
	var speed: float = car.forward_speed
	var cap: float = car.tuning.maximum_speed_mps
	# Point the nose first: the sharper the turn needed right now, the slower it wants to go.
	desired = minf(desired, lerpf(cap, CORNER_SPEED * 0.8, clampf((absf(angle) - 0.3) / 1.2, 0.0, 1.0)))
	var steer: float = clampf(angle / FULL_LOCK_ANGLE, -1.0, 1.0)
	var throttle: float
	if absf(angle) > 2.0 and absf(speed) < 6.0:
		# Target is behind: three-point turn.
		throttle = -1.0
		steer = -signf(angle)
	elif speed > desired + 1.5:
		throttle = -1.0
	else:
		throttle = clampf(desired / cap, 0.2, 1.0)
	var drift: bool = absf(angle) > 0.6 and speed > 16.0
	car.set_driver_command(throttle, steer, drift)
	_last_steer = steer
	_check_stuck(throttle, delta)


func _check_stuck(throttle: float, delta: float) -> void:
	if throttle > 0.3 and _flat(car.get_real_velocity()).length() < 2.0:
		_stuck_clock += delta
	else:
		_stuck_clock = 0.0
	if _stuck_clock > 1.0:
		_stuck_clock = 0.0
		_reverse_left = 1.0
		_reverse_steer = -signf(_last_steer) if absf(_last_steer) > 0.1 else (1.0 if randf() < 0.5 else -1.0)
		_route_clock = 0.0


func _plan_route(here: Vector2, goal: Vector2) -> void:
	var start: int = chase.node_near(here, _flat(-car.global_basis.z))
	var finish: int = chase.node_near(goal, Vector2.ZERO)
	route = PackedVector2Array()
	_route_index = 0
	if start < 0 or finish < 0:
		route.append(goal)
		return
	for id: int in chase.astar.get_id_path(start, finish):
		route.append(chase.graph.positions[id])
	route.append(goal)


## Aims at the next route point, moving on once it is close; the reach grows with speed.
func _route_aim(here: Vector2) -> Vector2:
	var reach: float = clampf(absf(car.forward_speed) * 0.45, 7.0, 20.0)
	while _route_index < route.size() - 1 and here.distance_to(route[_route_index]) < reach:
		_route_index += 1
	return route[_route_index] if not route.is_empty() else here


## Fastest speed that still makes the next few corners, braking from where it is now.
func _route_speed(here: Vector2) -> float:
	var cap: float = car.tuning.maximum_speed_mps
	var desired: float = cap
	var braking: float = car.tuning.braking_mps2 * 0.6 * lateness
	var travelled: float = here.distance_to(route[_route_index]) if not route.is_empty() else 0.0
	var previous: Vector2 = here
	for index: int in range(_route_index, mini(_route_index + 4, route.size() - 1)):
		var corner: Vector2 = route[index]
		var after: Vector2 = route[index + 1]
		var turn: float = absf((corner - previous).angle_to(after - corner))
		var corner_speed: float = lerpf(cap, CORNER_SPEED, clampf((turn - 0.2) / 1.2, 0.0, 1.0))
		desired = minf(desired, sqrt(corner_speed * corner_speed + 2.0 * braking * travelled))
		travelled += corner.distance_to(after)
		previous = corner
	return desired


## Straight-at-you only when a whole car width fits: centre line plus both sides.
func _clear_line() -> bool:
	var from: Vector3 = car.global_position + Vector3.UP * 1.2
	var to: Vector3 = target.global_position + Vector3.UP * 1.2
	var side: Vector3 = (to - from).cross(Vector3.UP).normalized() * 1.3
	var space: PhysicsDirectSpaceState3D = car.get_world_3d().direct_space_state
	for offset: Vector3 in [Vector3.ZERO, side, -side]:
		if not space.intersect_ray(PhysicsRayQueryParameters3D.create(from + offset, to + offset, 1)).is_empty():
			return false
	return true


func _flat(v: Vector3) -> Vector2:
	return Vector2(v.x, v.z)
