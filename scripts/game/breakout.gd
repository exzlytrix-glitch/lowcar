class_name Breakout
extends Node
## The breakout cutscene (the user's idea): the stand turns the car to the door, it rolls out of the
## hideout onto the street, sirens grow as a cruiser comes down the street, it spots you, the news goes
## live, and the car is yours. Enter or Space skips straight to the hand-over.

## The cruiser has seen you: time for the LIVE banner.
signal spotted
## Hand the car to the player and start the chase.
signal finished

const COP_DISTANCE: float = 95.0
const COP_SPEED: float = 24.0

var hideout: Hideout
var car: LabVehicle
var chase: LabChase
## The cutscene camera (the game's; the menu uses it too).
var camera: Camera3D
var running: bool = false
var _driver: ScriptedDriver
var _away: float = 1.0
var _clock: float = 0.0
var _step: int = 0
var _cop: LabVehicle
var _camera_target := Vector3.ZERO
var _camera_from := Vector3.ZERO
var _camera_to := Vector3.ZERO
var _camera_move: float = 0.0
var _camera_moved: float = 0.0
var _track_car: bool = false
## The spotted shot: riding just ahead of the car, looking back past it at the cruiser.
var _front_track: bool = false
var _front_blend: float = 0.0


func play() -> void:
	running = true
	_clock = 0.0
	_step = 0
	_away = 1.0 if randf() < 0.5 else -1.0
	hideout.show_inside(false)
	hideout.turn_to_door(1.4)
	camera.projection = Camera3D.PROJECTION_PERSPECTIVE
	camera.h_offset = 0.0
	camera.fov = 55.0
	camera.near = 0.1
	camera.current = true
	# Inside the garage, low by the back corner, looking past the stand at the open door.
	_cut(hideout.to_global(Vector3(4.6, 1.3, 3.6)), hideout.to_global(Vector3(0.0, 0.8, -2.0)))


func _unhandled_input(event: InputEvent) -> void:
	if not running:
		return
	var key := event as InputEventKey
	if key != null and key.pressed and not key.echo and key.physical_keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE, KEY_ESCAPE]:
		get_viewport().set_input_as_handled()
		_skip()


func _process(delta: float) -> void:
	if not running:
		return
	_clock += delta
	_update_camera(delta)
	match _step:
		0:
			if _clock >= 1.5:
				_step = 1
				car.process_mode = Node.PROCESS_MODE_PAUSABLE
				car.visible = true
				hideout.put_car_on_stand(car)
				car.controls_enabled = true
				_driver = ScriptedDriver.new()
				_driver.name = "BreakoutDriver"
				_driver.car = car
				_driver.path = hideout.route_out(_away)
				car.add_child(_driver)
				_track_car = true
		1:
			if _clock >= 3.3:
				_step = 2
				# Across the street, a little up the road the car will take: it pulls out toward us.
				var across: Vector2 = hideout.street_point + hideout.facing * (hideout.street_width * 0.5 + 5.0) + hideout.street_dir * _away * 14.0
				_cut(Vector3(across.x, 2.2, across.y), car.global_position)
				_spawn_cop()
		2:
			var along: Vector2 = hideout.street_dir * _away
			var travelled: float = (Vector2(car.global_position.x, car.global_position.z) - hideout.street_point).dot(along)
			if _clock >= 6.0 or travelled > 14.0:
				_step = 3
				spotted.emit()
				_track_car = false
				_front_track = true
				_front_blend = 0.0
				_camera_from = camera.global_position
		3:
			if _clock >= 8.2:
				_finish()


func _spawn_cop() -> void:
	if is_instance_valid(_cop):
		return
	var along: Vector2 = hideout.street_dir * _away
	var wanted: Vector2 = hideout.street_point - along * COP_DISTANCE
	var found: Dictionary = chase.graph.closest_road_point(wanted, 120.0)
	if found.is_empty():
		return
	var id: int = found["edge"]
	var point: Vector2 = found["point"]
	var dir: Vector2 = (chase.graph.positions[chase.graph.edge_b[id]] - chase.graph.positions[chase.graph.edge_a[id]]).normalized()
	if dir.dot(hideout.street_point - point) < 0.0:
		dir = -dir
	_cop = chase.spawn_cop(point, dir, COP_SPEED)


func _skip() -> void:
	car.process_mode = Node.PROCESS_MODE_PAUSABLE
	car.visible = true
	if _step < 1:
		hideout.put_car_on_stand(car)
	var along: Vector2 = hideout.street_dir * _away
	var lane: Vector2 = hideout.street_point - hideout.facing * (hideout.street_width * 0.2) + along * 8.0
	car.reset_vehicle(Vector3(lane.x, 0.2, lane.y))
	car.rotation.y = atan2(-along.x, -along.y)
	car.forward_speed = 14.0
	car.velocity = Vector3(along.x, 0.0, along.y) * 14.0
	car.reset_physics_interpolation()
	_spawn_cop()
	if _step < 3:
		spotted.emit()
	_finish()


func _finish() -> void:
	running = false
	_track_car = false
	_front_track = false
	if is_instance_valid(_driver):
		_driver.queue_free()
	_driver = null
	hideout.spin_display(false)
	finished.emit()


# --- camera ---------------------------------------------------------------------

func _cut(at: Vector3, look: Vector3) -> void:
	_camera_move = 0.0
	camera.global_position = at
	_camera_target = look
	camera.look_at(look, Vector3.UP)


func _glide(to: Vector3, look: Vector3, seconds: float) -> void:
	_camera_from = camera.global_position
	_camera_to = to
	_camera_move = seconds
	_camera_moved = 0.0
	_camera_target = look
	_track_car = false


func _update_camera(delta: float) -> void:
	if _front_track and is_instance_valid(car):
		# Locked 12 m ahead of the car (it is accelerating, so a lagging camera gets overtaken),
		# blending in from the previous shot over 0.7 s.
		_front_blend = minf(_front_blend + delta / 0.7, 1.0)
		var blend: float = smoothstep(0.0, 1.0, _front_blend)
		var along: Vector2 = hideout.street_dir * _away
		var at: Vector3 = car.get_global_transform_interpolated().origin
		var side: Vector2 = hideout.facing * 3.4
		var wanted := Vector3(at.x + along.x * 12.0 + side.x, 1.9, at.z + along.y * 12.0 + side.y)
		camera.global_position = _camera_from.lerp(wanted, blend)
		var behind := Vector3(at.x - along.x * 22.0, 1.0, at.z - along.y * 22.0)
		camera.look_at(_camera_target.lerp(behind, blend), Vector3.UP)
		return
	if _camera_move > 0.0:
		_camera_moved = minf(_camera_moved + delta, _camera_move)
		var t: float = smoothstep(0.0, 1.0, _camera_moved / _camera_move)
		camera.global_position = _camera_from.lerp(_camera_to, t)
	var look: Vector3 = _camera_target
	if _track_car and is_instance_valid(car):
		look = car.get_global_transform_interpolated().origin + Vector3.UP * 0.8
		_camera_target = _camera_target.lerp(look, minf(delta * 6.0, 1.0))
		look = _camera_target
	if not camera.global_position.is_equal_approx(look):
		camera.look_at(look, Vector3.UP)
