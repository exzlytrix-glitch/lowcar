class_name LabRecorder
extends Node
## Rough chase recorder for the city lab. 1 starts and stops recording; then pick any cop that was in
## the chase and watch how it drove, from behind it or overhead, with every recorded car as a ghost.
## 2 reopens the last recording.

const POLICE_MODEL: String = "res://assets/models/vehicles/police_cruiser/police_cruiser.glb"
const PLAYER_MODEL: String = "res://scenes/vehicles/red_muscle_car.tscn"
const RATE: float = 60.0
const MODE_NAMES: PackedStringArray = ["route", "direct", "brain", "windup", "ram", "slam", "pit", "brake", "recover", "charge", "burst"]


class Track:
	var label: String = ""
	var first_frame: int = 0
	var origins := PackedVector3Array()
	var rotations := PackedVector4Array()
	var modes := PackedByteArray()
	var speeds := PackedFloat32Array()
	var closest: float = INF

	func frame_count() -> int:
		return origins.size()


## The replay viewer was closed (the game puts its own screens back).
signal replay_closed

var chase: LabChase
var player: LabVehicle
var map: CityMapView
var layer: CanvasLayer
var recording: bool = false
var replaying: bool = false
var frame: int = 0
var player_track: Track
var cop_tracks: Array[Track] = []
var _by_cop: Dictionary = {}
var _ghosts: Array[Node3D] = []
var _player_ghost: Node3D
var _camera: Camera3D
var _previous_camera: Camera3D
var _selected: int = 0
var _time: float = 0.0
var _playing: bool = true
var _speed: float = 1.0
var _overhead: bool = false
var _panel: PanelContainer
var _list: ItemList
var _info: Label
var _timeline: HSlider


func toggle_recording() -> void:
	if replaying:
		return
	if not recording:
		recording = true
		frame = 0
		player_track = Track.new()
		player_track.label = "You"
		cop_tracks.clear()
		_by_cop.clear()
		return
	recording = false
	open_replay()


## Ends a recording without opening the replay (the game: watching stops the chase, so it waits).
func stop_recording() -> void:
	recording = false


func has_recording() -> bool:
	return player_track != null and not cop_tracks.is_empty()


func recorded_seconds() -> float:
	return frame / RATE


func open_replay() -> void:
	if replaying or player_track == null or cop_tracks.is_empty():
		return
	replaying = true
	chase.stop()
	player.controls_enabled = false
	player.visible = false
	_player_ghost = (load(PLAYER_MODEL) as PackedScene).instantiate() as Node3D
	add_child(_player_ghost)
	var police: PackedScene = load(POLICE_MODEL) as PackedScene
	for track: Track in cop_tracks:
		var ghost := police.instantiate() as Node3D
		add_child(ghost)
		_ghosts.append(ghost)
	_previous_camera = get_viewport().get_camera_3d()
	_camera = Camera3D.new()
	_camera.near = 0.4
	_camera.far = 900.0
	add_child(_camera)
	_camera.current = true
	_build_panel()
	map.show_player_marker = false
	_select(0)


func close_replay() -> void:
	if not replaying:
		return
	replaying = false
	for ghost: Node3D in _ghosts:
		ghost.queue_free()
	_ghosts.clear()
	_player_ghost.queue_free()
	_camera.queue_free()
	if is_instance_valid(_previous_camera):
		_previous_camera.current = true
	_panel.queue_free()
	_info.queue_free()
	map.overlay_lines.clear()
	map.overlay_markers.clear()
	map.show_player_marker = true
	player.visible = true
	player.controls_enabled = true
	replay_closed.emit()


func _physics_process(_delta: float) -> void:
	if not recording:
		return
	_record(player_track, player, 0)
	for cop: LabVehicle in chase.cops:
		var id: int = cop.get_instance_id()
		if not _by_cop.has(id):
			var track := Track.new()
			track.label = "Cop %d" % (cop_tracks.size() + 1)
			track.first_frame = frame
			cop_tracks.append(track)
			_by_cop[id] = track
		var driver: Node = cop.get_node_or_null("Driver")
		var mode: String = String(driver.get("mode")) if driver != null else ""
		var cop_track: Track = _by_cop[id]
		_record(cop_track, cop, maxi(0, MODE_NAMES.find(mode)))
		cop_track.closest = minf(cop_track.closest, cop.global_position.distance_to(player.global_position))
	frame += 1


func _record(track: Track, car: Node3D, mode: int) -> void:
	var rotation: Quaternion = car.global_basis.get_rotation_quaternion()
	track.origins.append(car.global_position)
	track.rotations.append(Vector4(rotation.x, rotation.y, rotation.z, rotation.w))
	track.modes.append(mode)
	var velocity: Vector3 = (car as CharacterBody3D).velocity
	track.speeds.append(Vector2(velocity.x, velocity.z).length())


func _process(delta: float) -> void:
	if not replaying:
		return
	var end: float = (player_track.frame_count() - 1) / RATE
	if _playing:
		_time = minf(_time + delta * _speed, end)
	var at: float = _time * RATE
	_place(_player_ghost, player_track, at)
	for index: int in cop_tracks.size():
		_place(_ghosts[index], cop_tracks[index], at)
	var track: Track = cop_tracks[_selected]
	var ghost: Node3D = _ghosts[_selected]
	if ghost.visible:
		_follow(ghost, delta)
	_timeline.set_value_no_signal(_time)
	_update_info(track, at)
	_update_map(at)


## Sets a ghost to the recording at a fractional frame; hidden outside the time that car existed.
func _place(ghost: Node3D, track: Track, at: float) -> void:
	var local: float = at - track.first_frame
	if local < 0.0 or local > track.frame_count() - 1:
		ghost.visible = false
		return
	ghost.visible = true
	var index: int = int(local)
	var next: int = mini(index + 1, track.frame_count() - 1)
	var blend: float = local - index
	var a: Vector4 = track.rotations[index]
	var b: Vector4 = track.rotations[next]
	var rotation: Quaternion = Quaternion(a.x, a.y, a.z, a.w).slerp(Quaternion(b.x, b.y, b.z, b.w), blend)
	ghost.global_transform = Transform3D(Basis(rotation), track.origins[index].lerp(track.origins[next], blend))


func _follow(ghost: Node3D, delta: float) -> void:
	var forward: Vector3 = -ghost.global_basis.z
	forward.y = 0.0
	forward = forward.normalized()
	var focus: Vector3 = ghost.global_position
	var position: Vector3
	var look: Vector3
	if _overhead:
		var you: Vector3 = _player_ghost.global_position if _player_ghost.visible else focus
		var gap: float = focus.distance_to(you)
		var middle: Vector3 = focus.lerp(you, 0.5) if gap < 220.0 else focus
		position = middle + Vector3(0.0, 45.0 + minf(gap, 220.0) * 0.7, 0.01)
		look = middle
	else:
		position = focus - forward * 11.0 + Vector3.UP * 4.0
		look = focus + forward * 10.0 + Vector3.UP * 1.0
	_camera.global_position = _camera.global_position.lerp(position, 1.0 - exp(-7.0 * delta))
	_camera.look_at(look, Vector3.UP)


func _update_info(track: Track, at: float) -> void:
	var local: int = clampi(int(at) - track.first_frame, 0, track.frame_count() - 1)
	var state: String = "not in the chase at this moment"
	if at >= track.first_frame and at <= track.first_frame + track.frame_count() - 1:
		var you: Vector3 = player_track.origins[clampi(int(at), 0, player_track.frame_count() - 1)]
		state = "%s mode  ·  %d km/h  ·  %d m from you (you %d km/h)" % [MODE_NAMES[track.modes[local]],
			int(track.speeds[local] * 3.6), int(track.origins[local].distance_to(you)),
			int(player_track.speeds[clampi(int(at), 0, player_track.frame_count() - 1)] * 3.6)]
	_info.text = "REPLAY  %s  ·  %s / %s  ·  %s  ·  %sx\n%s\nSpace pause · ←/→ skip 2 s · [ ] speed · ↑/↓ other cop · V overhead/behind · M map · Esc exit" % [
		track.label, _clock(_time), _clock((player_track.frame_count() - 1) / RATE), "playing" if _playing else "paused", str(_speed), state]


func _update_map(at: float) -> void:
	map.overlay_lines.clear()
	map.overlay_markers.clear()
	map.overlay_lines.append([_path(player_track), Color("#D94B3D"), 3.0])
	for index: int in cop_tracks.size():
		if index != _selected:
			map.overlay_lines.append([_path(cop_tracks[index]), Color(0.25, 0.35, 0.55, 0.45), 1.5])
	map.overlay_lines.append([_path(cop_tracks[_selected]), Color("#2F6FE0"), 3.0])
	if _player_ghost.visible:
		map.overlay_markers.append([Vector2(_player_ghost.global_position.x, _player_ghost.global_position.z), Color("#D94B3D")])
	for index: int in cop_tracks.size():
		if _ghosts[index].visible:
			var color: Color = Color("#2F6FE0") if index == _selected else Color(0.25, 0.35, 0.55)
			map.overlay_markers.append([Vector2(_ghosts[index].global_position.x, _ghosts[index].global_position.z), color])


func _path(track: Track) -> PackedVector2Array:
	var points := PackedVector2Array()
	for index: int in range(0, track.frame_count(), 10):
		points.append(Vector2(track.origins[index].x, track.origins[index].z))
	return points


func _select(index: int) -> void:
	_selected = clampi(index, 0, cop_tracks.size() - 1)
	_list.select(_selected)
	_time = cop_tracks[_selected].first_frame / RATE
	_playing = true
	_camera.global_position = cop_tracks[_selected].origins[0] + Vector3(0.0, 6.0, 12.0)


func _unhandled_input(event: InputEvent) -> void:
	if not replaying:
		return
	var key := event as InputEventKey
	if key == null or not key.pressed:
		return
	match key.physical_keycode:
		KEY_SPACE:
			_playing = not _playing
		KEY_LEFT:
			_time = maxf(0.0, _time - 2.0)
		KEY_RIGHT:
			_time += 2.0
		KEY_BRACKETLEFT:
			_speed = maxf(0.25, _speed * 0.5)
		KEY_BRACKETRIGHT:
			_speed = minf(4.0, _speed * 2.0)
		KEY_UP:
			_select(_selected - 1)
		KEY_DOWN:
			_select(_selected + 1)
		KEY_V:
			_overhead = not _overhead
		KEY_ESCAPE:
			close_replay()
		_:
			return
	get_viewport().set_input_as_handled()


func _build_panel() -> void:
	_panel = PanelContainer.new()
	_panel.position = Vector2(14, 250)
	_panel.custom_minimum_size = Vector2(300, 0)
	layer.add_child(_panel)
	var column := VBoxContainer.new()
	_panel.add_child(column)
	var title := Label.new()
	title.text = "Recorded cops (click to watch)"
	column.add_child(title)
	_list = ItemList.new()
	_list.custom_minimum_size = Vector2(300, 220)
	_list.focus_mode = Control.FOCUS_NONE
	for track: Track in cop_tracks:
		_list.add_item("%s  ·  in chase %s  ·  closest %d m" % [track.label, _clock(track.frame_count() / RATE), int(track.closest)])
	_list.item_selected.connect(func(index: int) -> void: _select(index))
	column.add_child(_list)
	_timeline = HSlider.new()
	_timeline.min_value = 0.0
	_timeline.max_value = (player_track.frame_count() - 1) / RATE
	_timeline.step = 0.01
	_timeline.focus_mode = Control.FOCUS_NONE
	_timeline.value_changed.connect(func(value: float) -> void: _time = value)
	column.add_child(_timeline)
	_info = Label.new()
	_info.anchor_top = 1.0
	_info.anchor_bottom = 1.0
	_info.offset_left = 14.0
	_info.offset_top = -118.0
	_info.add_theme_font_size_override("font_size", 15)
	_info.add_theme_color_override("font_color", Color("#24394B"))
	_info.add_theme_color_override("font_outline_color", Color("#F7F1E6"))
	_info.add_theme_constant_override("outline_size", 5)
	layer.add_child(_info)


func _clock(seconds: float) -> String:
	return "%d:%04.1f" % [int(seconds) / 60, fmod(seconds, 60.0)]
