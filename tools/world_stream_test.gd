extends SceneTree
## Drives a camera through the endless city (WorldStreamer) at chase speed on a slowly curving line and
## reports how streaming keeps up: frame times (mean, 99th percentile, worst, frames over 25 ms), cells
## built and dropped, and frames where a cell within view distance was still missing.
##   godot --path . --script res://tools/world_stream_test.gd -- --seconds=60 --speed=45 --seed=7

var _streamer: WorldStreamer
var _camera: Camera3D
var _focus := Vector2(240.0, 0.0)
var _heading: float = 0.4
var _speed: float = 45.0
var _seconds: float = 60.0
var _elapsed: float = 0.0
var _frames := PackedFloat32Array()
var _last_usec: int = 0
var _missing_frames: int = 0
var _built: int = 0
var _dropped: int = 0
var _view: float = 600.0


func _initialize() -> void:
	var settings := CityGenSettings.new()
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with("--seconds="):
			_seconds = float(argument.trim_prefix("--seconds="))
		elif argument.begins_with("--speed="):
			_speed = float(argument.trim_prefix("--speed="))
		elif argument.begins_with("--seed="):
			settings.city_seed = int(argument.trim_prefix("--seed="))
	_view = settings.view_distance
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	var scene := Node3D.new()
	root.add_child(scene)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-50.0, 30.0, 0.0)
	light.shadow_enabled = true
	scene.add_child(light)
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color("#BFE3F2")
	environment.environment.fog_enabled = true
	environment.environment.fog_mode = Environment.FOG_MODE_DEPTH
	environment.environment.fog_depth_begin = _view * 0.35
	environment.environment.fog_depth_end = _view
	scene.add_child(environment)
	_camera = Camera3D.new()
	_camera.far = _view + 80.0
	scene.add_child(_camera)
	_camera.current = true
	_streamer = WorldStreamer.new()
	scene.add_child(_streamer)
	_streamer.setup(settings)
	var started: int = Time.get_ticks_msec()
	_streamer.load_around(_focus)
	print("STREAM_TEST start: %d cells in %d ms" % [_streamer.cells.size(), Time.get_ticks_msec() - started])
	_built = _streamer.cells.size()
	_last_usec = Time.get_ticks_usec()


func _process(delta: float) -> bool:
	var now: int = Time.get_ticks_usec()
	if _elapsed > 1.0:
		_frames.append((now - _last_usec) / 1000.0)
		if (now - _last_usec) / 1000.0 > 25.0:
			print("SPIKE %.1f ms at %.1f s" % [(now - _last_usec) / 1000.0, _elapsed])
	_last_usec = now
	_elapsed += delta
	_heading += 0.06 * delta
	var dir := Vector2.from_angle(_heading)
	_focus += dir * _speed * delta
	var known: Dictionary = _streamer.cells.duplicate()
	_streamer.update(_focus, dir)
	for cell: Vector2i in _streamer.cells:
		if not known.has(cell):
			_built += 1
	for cell: Vector2i in known:
		if not _streamer.cells.has(cell):
			_dropped += 1
	if _missing_near():
		_missing_frames += 1
	_camera.position = Vector3(_focus.x - dir.x * 9.0, 3.2, _focus.y - dir.y * 9.0)
	_camera.look_at(Vector3(_focus.x + dir.x * 20.0, 1.0, _focus.y + dir.y * 20.0), Vector3.UP)
	if _elapsed < _seconds:
		return false
	_report()
	return true


func _missing_near() -> bool:
	var center: Vector2i = _streamer.world.cell_of(_focus)
	for j: int in range(center.y - 2, center.y + 3):
		for i: int in range(center.x - 2, center.x + 3):
			var cell := Vector2i(i, j)
			var area := Rect2(Vector2(cell) * WorldGen.CELL, Vector2.ONE * WorldGen.CELL)
			var nearest := Vector2(clampf(_focus.x, area.position.x, area.end.x), clampf(_focus.y, area.position.y, area.end.y))
			if nearest.distance_to(_focus) < _view and not _streamer.cells.has(cell):
				return true
	return false


func _report() -> void:
	var sorted: PackedFloat32Array = _frames.duplicate()
	sorted.sort()
	var total: float = 0.0
	var slow: int = 0
	for value: float in sorted:
		total += value
		if value > 25.0:
			slow += 1
	var count: int = sorted.size()
	print("STREAM_TEST drove %.1f km at %d km/h: %d frames, mean %.1f ms, p99 %.1f ms, worst %.1f ms, %d frames over 25 ms" % [
		_elapsed * _speed / 1000.0, int(_speed * 3.6), count, total / maxf(count, 1), sorted[int(count * 0.99)],
		sorted[count - 1], slow])
	print("STREAM_TEST cells built %d, dropped %d, loaded now %d, junctions %d, frames with a missing cell in view range %d" % [
		_built, _dropped, _streamer.cells.size(), _streamer.nav.astar.get_point_count(), _missing_frames])
	_streamer.clear()
