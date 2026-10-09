extends Node3D
## City lab: generate a city, drive the red car around it, and tune the generator live. No police.
## M map · T tuning panel · R back onto a road · G regenerate · N new seed · F find car on map
## Optional: -- --capture=/folder writes map, chase and aerial screenshots, then quits.

const POLICE_SCENE_PATH: String = "res://scenes/review/lab_police_car.tscn"
const SETTINGS_PATH: String = "res://resources/citygen/city_lab_settings.tres"
const HANDLING_PATH: String = "res://resources/citygen/lab_car_handling.tres"
const CAR_TUNABLES: Array[Array] = [
	["steer_low_speed", "Steering, low speed", 0.5, 6.0, 0.05],
	["steer_top_speed", "Steering at 115 km/h", 0.5, 6.0, 0.05],
	["steer_boost_speed", "Steering while boosting", 0.3, 5.0, 0.05],
	["steer_response", "Steering response", 1.0, 30.0, 0.5],
	["grip", "Grip", 2.0, 40.0, 0.5],
	["air_steer", "Air steering", 0.0, 1.0, 0.05],
	["drift_grip", "Drift grip", 0.5, 10.0, 0.1],
	["drift_steer_boost", "Drift steering boost", 1.0, 3.0, 0.05],
	["drift_max_angle", "Drift max angle", 15.0, 80.0, 1.0],
	["drift_speed_loss", "Drift speed loss", 0.0, 15.0, 0.25],
	["drift_exit_kick", "Drift exit kick (m/s)", 0.0, 15.0, 0.25],
	["drift_min_speed", "Drift min speed (m/s)", 5.0, 25.0, 0.5],
	["wall_glance_keep", "Speed kept on wall scrape", 0.0, 1.0, 0.01],
	["wall_head_on_keep", "Speed kept head-on", 0.0, 1.0, 0.01],
	["wall_align", "Turn along wall on scrape", 0.0, 1.0, 0.05],
]
const TUNABLES: Array[Array] = [
	["city_radius", "City radius (m)", 250.0, 2000.0, 10.0],
	["edge_wobble", "Edge wobble", 0.0, 0.45, 0.01],
	["district_count", "Districts", 1.0, 24.0, 1.0],
	["arterial_count", "Arterial spokes", 2.0, 12.0, 1.0],
	["old_town_weight", "Old town weight", 0.0, 3.0, 0.05],
	["grid_weight", "Grid weight", 0.0, 3.0, 0.05],
	["residential_weight", "Residential weight", 0.0, 3.0, 0.05],
	["industrial_weight", "Industrial weight", 0.0, 3.0, 0.05],
	["block_scale", "Block size", 0.5, 2.5, 0.05],
	["curviness", "Curviness", 0.0, 3.0, 0.05],
	["branch_chance", "Side-street chance", 0.0, 1.0, 0.01],
	["through_chance", "Streets continue through", 0.0, 1.0, 0.01],
	["dead_end_chance", "Dead-end chance", 0.0, 0.5, 0.005],
	["min_road_spacing", "Min road spacing (m)", 10.0, 80.0, 1.0],
	["min_junction_angle", "Min junction angle", 15.0, 70.0, 1.0],
	["snap_radius", "Snap radius (m)", 2.0, 30.0, 0.5],
	["arterial_width", "Arterial width (m)", 8.0, 30.0, 0.5],
	["street_width", "Street width (m)", 6.0, 20.0, 0.5],
	["lane_width", "Old-town lane width (m)", 5.0, 14.0, 0.5],
	["sidewalk_width", "Sidewalk width (m)", 1.0, 8.0, 0.1],
	["corner_radius", "Corner radius (m)", 0.0, 14.0, 0.25],
	["curb_height", "Curb height (m)", 0.05, 0.4, 0.01],
	["park_chance", "Park chance", 0.0, 0.5, 0.01],
	["building_fill", "Building fill", 0.0, 1.0, 0.01],
	["tree_spacing", "Street tree spacing (m)", 4.0, 40.0, 0.5],
	["detail_distance", "Full-detail distance (m)", 60.0, 600.0, 5.0],
	["view_distance", "View distance (m)", 150.0, 1500.0, 10.0],
]

@onready var player: LabVehicle = $PlayerCar
@onready var world_environment: WorldEnvironment = $Environment
var settings: CityGenSettings
var handling: CarHandling
var generator: RoadGenerator
var graph: RoadGraph
var blocks: Array[CityBlocks.Block] = []
var city: CityBuilder
var stats: String = ""
var _hud: Label
var _overlay: Label
var _map: CityMapView
var _panel: PanelContainer
var _controls: Dictionary = {}
var _seed_box: SpinBox
var _ring_box: CheckBox
var _busy: bool = false
var _hud_clock: float = 0.0
var _capture_dir: String = ""
var _police: Array[LabVehicle] = []
var chase: LabChase
var recorder: LabRecorder
var _layer: CanvasLayer
var _health_bar: ProgressBar
var _health_fill := StyleBoxFlat.new()
var _wrecked: bool = false
var _start_chase_on_load: bool = false


func _ready() -> void:
	settings = _load_settings()
	handling = _load_handling()
	player.handling = handling
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with("--capture="):
			_capture_dir = argument.trim_prefix("--capture=")
		elif argument == "--chase":
			_start_chase_on_load = true
		elif argument.begins_with("--seed="):
			settings.city_seed = int(argument.trim_prefix("--seed="))
	chase = LabChase.new()
	chase.name = "Chase"
	add_child(chase)
	player.takes_damage = true
	player.chamfer_collider()
	player.destroyed.connect(_on_wrecked)
	_build_ui()
	recorder = LabRecorder.new()
	recorder.name = "Recorder"
	recorder.chase = chase
	recorder.player = player
	recorder.map = _map
	recorder.layer = _layer
	add_child(recorder)
	# The reused police light bar only flashes while a run is "driving".
	RunSession.phase = RunSession.Phase.DRIVING
	player.controls_enabled = false
	_map.player = player
	_map.teleport_requested.connect(_on_map_teleport)
	await regenerate()
	if _start_chase_on_load:
		chase.start()
	if not _capture_dir.is_empty():
		await _capture()
		get_tree().quit()


func _process(delta: float) -> void:
	_hud_clock -= delta
	if _hud_clock > 0.0 or _hud == null:
		return
	_hud_clock = 0.2
	var speed: float = Vector2(player.velocity.x, player.velocity.z).length() * 3.6
	var district: String = ""
	if generator != null:
		district = RoadGenerator.STYLE_NAMES[generator.style_at(Vector2(player.global_position.x, player.global_position.z))]
	var drift: String = "  ·  DRIFT %d°" % int(absf(rad_to_deg(player.slip_angle))) if player.drifting else ""
	var chase_line: String = "Enter: start a chase  ·  P: one cop behind you"
	if chase.active and not chase.auto_spawn:
		chase_line = "%d hand-placed cops chasing  ·  Enter: start the full chase  ·  C: clear" % chase.cops.size()
	elif chase.active:
		var seconds: int = int(chase.elapsed)
		chase_line = "CHASE %d:%02d  ·  minute %.1f  ·  %d cops  ·  cop top speed %d km/h  ·  Enter to stop" % [
			seconds / 60, seconds % 60, chase.minute(), chase.cops.size(), int(chase.top_speed() * 3.6)]
	if recorder.recording:
		chase_line += "\n● REC %.1f s  ·  press 1 to stop and review the cops" % recorder.recorded_seconds()
	elif not recorder.replaying:
		chase_line += "\n1: record the chase  ·  2: watch the last recording"
	_hud.text = "CITY LAB  ·  seed %d  ·  %s\n%d km/h  ·  %d fps  ·  %s%s\n%s\nWASD drive · Shift boost · Space jump · Ctrl + steer drift\nM map · T tune · R back on road · G regenerate · N new seed · P cop behind · C clear cops" % [
		settings.city_seed, stats, int(speed), Engine.get_frames_per_second(), district, drift, chase_line]
	_health_bar.value = player.health
	_health_fill.bg_color = Color("#7BC67E") if player.health > 60.0 else (Color("#F2C46B") if player.health > 30.0 else Color("#E2574C"))


func _unhandled_input(event: InputEvent) -> void:
	var key := event as InputEventKey
	if key == null or not key.pressed or key.echo:
		return
	if recorder.replaying and key.physical_keycode != KEY_M:
		return
	match key.physical_keycode:
		KEY_1:
			recorder.toggle_recording()
		KEY_2:
			recorder.open_replay()
		KEY_M:
			_map.visible = not _map.visible
		KEY_T:
			_panel.visible = not _panel.visible
		KEY_R:
			var forward: Vector3 = -player.global_basis.z
			_place_on_road(Vector2(player.global_position.x, player.global_position.z), Vector2(forward.x, forward.z))
		KEY_G:
			regenerate()
		KEY_N:
			_new_seed()
		KEY_F:
			if _map.visible:
				_map.center_on_player()
		KEY_L:
			_map.show_graph = not _map.show_graph
		KEY_ENTER, KEY_KP_ENTER:
			chase.toggle()
		KEY_P:
			chase.add_cop_behind()
		KEY_C:
			_clear_police()
			chase.stop()
		_:
			return
	get_viewport().set_input_as_handled()


func regenerate() -> void:
	if _busy:
		return
	_busy = true
	player.controls_enabled = false
	_overlay.text = "Generating city %d…" % settings.city_seed
	_overlay.visible = true
	await get_tree().process_frame
	await get_tree().process_frame
	_clear_police()
	if city != null:
		remove_child(city)
		city.queue_free()
	var started: int = Time.get_ticks_msec()
	generator = RoadGenerator.new()
	graph = generator.generate(settings)
	var roads_done: int = Time.get_ticks_msec()
	blocks = CityBlocks.build(graph, generator, settings)
	var blocks_done: int = Time.get_ticks_msec()
	city = CityBuilder.new()
	city.name = "City"
	add_child(city)
	city.build(settings, graph, generator, blocks)
	var finished: int = Time.get_ticks_msec()
	var length: float = 0.0
	for id: int in graph.alive_edges():
		length += graph.edge_length(id)
	stats = "%.1f km of road · %d blocks · %d buildings · %d trees · built in %.1fs" % [
		length / 1000.0, blocks.size(), city.building_count, city.tree_count, (finished - started) / 1000.0]
	print("CITY_LAB seed=%d roads=%dms blocks=%dms build=%dms %s" % [settings.city_seed,
		roads_done - started, blocks_done - roads_done, finished - blocks_done, stats])
	_map.set_city(graph, generator, blocks, city.footprints, city.footprint_styles, settings.city_radius)
	chase.setup(graph, player)
	_apply_view()
	_place_at_start()
	_overlay.visible = false
	player.controls_enabled = true
	_busy = false


func _new_seed() -> void:
	settings.city_seed = randi_range(1, 999999)
	_seed_box.set_value_no_signal(settings.city_seed)
	regenerate()


func _apply_view() -> void:
	var camera: Camera3D = player.get_node("ChaseCamera/SpringArm3D/Camera3D")
	camera.near = 0.4
	camera.far = settings.view_distance + 80.0
	var environment: Environment = world_environment.environment
	environment.fog_enabled = true
	environment.fog_mode = Environment.FOG_MODE_DEPTH
	environment.fog_depth_begin = settings.view_distance * 0.35
	environment.fog_depth_end = settings.view_distance
	environment.fog_depth_curve = 1.4


## Start on the arterial nearest the centre, pointing along it.
func _place_at_start() -> void:
	var best: int = -1
	var best_distance: float = INF
	for id: int in graph.alive_edges():
		if graph.edge_kind[id] != RoadGraph.Kind.ARTERIAL or graph.edge_length(id) < 20.0:
			continue
		var middle: Vector2 = (graph.positions[graph.edge_a[id]] + graph.positions[graph.edge_b[id]]) * 0.5
		var distance: float = middle.length()
		if distance > 60.0 and distance < best_distance:
			best_distance = distance
			best = id
	if best < 0:
		_place_on_road(Vector2.ZERO, Vector2.ZERO)
		return
	var a: Vector2 = graph.positions[graph.edge_a[best]]
	var b: Vector2 = graph.positions[graph.edge_b[best]]
	_place_on_road((a + b) * 0.5, (b - a) if b.length() > a.length() else (a - b))


func _place_on_road(at: Vector2, heading: Vector2) -> void:
	if graph == null:
		return
	var found: Dictionary = graph.closest_road_point(at, settings.city_radius * 3.0)
	if found.is_empty():
		return
	var id: int = found["edge"]
	var point: Vector2 = found["point"]
	var dir: Vector2 = (graph.positions[graph.edge_b[id]] - graph.positions[graph.edge_a[id]]).normalized()
	if heading != Vector2.ZERO and dir.dot(heading) < 0.0:
		dir = -dir
	player.reset_vehicle(Vector3(point.x, 0.2, point.y))
	player.rotation.y = atan2(-dir.x, -dir.y)
	player.reset_physics_interpolation()
	player.controls_enabled = not _busy
	if _wrecked:
		_wrecked = false
		_overlay.visible = false
	(player.get_node("Attachments/GroundPunch") as LauncherAttachment).reset_attachment()
	player.get_node("Presentation").reset_pose(settings.city_seed)
	player.get_node("ChaseCamera").reset_view()


## Parks a cruiser on the road about 45 m ahead, facing you. No driving yet.
func _park_police_ahead() -> void:
	if graph == null:
		return
	var forward: Vector3 = -player.global_basis.z
	var ahead := Vector2(player.global_position.x + forward.x * 45.0, player.global_position.z + forward.z * 45.0)
	var found: Dictionary = graph.closest_road_point(ahead, 200.0)
	if found.is_empty():
		return
	var point: Vector2 = found["point"]
	var id: int = found["edge"]
	var dir: Vector2 = (graph.positions[graph.edge_b[id]] - graph.positions[graph.edge_a[id]]).normalized()
	var to_player := Vector2(player.global_position.x, player.global_position.z) - point
	if dir.dot(to_player) < 0.0:
		dir = -dir
	var cop := (load(POLICE_SCENE_PATH) as PackedScene).instantiate() as LabVehicle
	cop.handling = CarHandling.new()
	cop.add_to_group("police")
	add_child(cop)
	cop.chamfer_collider()
	cop.reset_vehicle(Vector3(point.x, 0.2, point.y))
	cop.rotation.y = atan2(-dir.x, -dir.y)
	cop.reset_physics_interpolation()
	_police.append(cop)


func _on_wrecked() -> void:
	_wrecked = true
	player.get_node("Presentation").play_explosion()
	_overlay.text = "WRECKED — press R to get back on the road"
	_overlay.visible = true


func _clear_police() -> void:
	for cop: LabVehicle in _police:
		if is_instance_valid(cop):
			cop.queue_free()
	_police.clear()


func _on_map_teleport(world: Vector2) -> void:
	_place_on_road(world, Vector2.ZERO)


# --- settings ----------------------------------------------------------------

func _load_settings() -> CityGenSettings:
	if ResourceLoader.exists(SETTINGS_PATH):
		var saved: Resource = load(SETTINGS_PATH)
		if saved is CityGenSettings:
			return saved.duplicate() as CityGenSettings
	return CityGenSettings.new()


func _load_handling() -> CarHandling:
	if ResourceLoader.exists(HANDLING_PATH):
		var saved: Resource = load(HANDLING_PATH)
		if saved is CarHandling:
			return saved.duplicate() as CarHandling
	return CarHandling.new()


func _save_settings() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SETTINGS_PATH.get_base_dir()))
	var error: Error = ResourceSaver.save(settings, SETTINGS_PATH)
	if error == OK:
		error = ResourceSaver.save(handling, HANDLING_PATH)
	_overlay.text = "Settings saved" if error == OK else "Save failed (%d)" % error
	_overlay.visible = true
	await get_tree().create_timer(1.2).timeout
	if not _busy:
		_overlay.visible = false


func _reset_settings() -> void:
	var seed_value: int = settings.city_seed
	settings = CityGenSettings.new()
	settings.city_seed = seed_value
	handling = CarHandling.new()
	player.handling = handling
	_refresh_controls()


func _refresh_controls() -> void:
	_seed_box.set_value_no_signal(settings.city_seed)
	_ring_box.set_pressed_no_signal(settings.ring_road)
	for key: String in _controls:
		var target: Object = handling if key.begins_with("car.") else settings
		var property: String = key.trim_prefix("car.")
		var slider: HSlider = _controls[key][0]
		slider.set_value_no_signal(float(target.get(property)))
		(_controls[key][1] as Label).text = _format(float(target.get(property)), slider.step)


# --- interface ---------------------------------------------------------------

func _build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	_layer = layer
	_map = CityMapView.new()
	_map.visible = false
	layer.add_child(_map)
	_hud = Label.new()
	_hud.position = Vector2(14, 10)
	_hud.add_theme_font_size_override("font_size", 15)
	_hud.add_theme_color_override("font_color", Color("#24394B"))
	_hud.add_theme_color_override("font_outline_color", Color("#F7F1E6"))
	_hud.add_theme_constant_override("outline_size", 5)
	layer.add_child(_hud)
	_health_bar = ProgressBar.new()
	_health_bar.position = Vector2(14, 168)
	_health_bar.size = Vector2(260, 18)
	_health_bar.max_value = player.max_health
	_health_bar.value = player.health
	_health_bar.show_percentage = false
	_health_fill.bg_color = Color("#7BC67E")
	_health_fill.set_corner_radius_all(4)
	var health_back := StyleBoxFlat.new()
	health_back.bg_color = Color(0.14, 0.22, 0.29, 0.55)
	health_back.set_corner_radius_all(4)
	_health_bar.add_theme_stylebox_override("fill", _health_fill)
	_health_bar.add_theme_stylebox_override("background", health_back)
	layer.add_child(_health_bar)
	_overlay = Label.new()
	_overlay.set_anchors_preset(Control.PRESET_CENTER)
	_overlay.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_overlay.add_theme_font_size_override("font_size", 28)
	_overlay.add_theme_color_override("font_color", Color("#24394B"))
	_overlay.add_theme_color_override("font_outline_color", Color("#F7F1E6"))
	_overlay.add_theme_constant_override("outline_size", 8)
	_overlay.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_overlay.grow_vertical = Control.GROW_DIRECTION_BOTH
	layer.add_child(_overlay)
	_build_panel(layer)


func _build_panel(layer: CanvasLayer) -> void:
	_panel = PanelContainer.new()
	_panel.visible = false
	_panel.anchor_left = 1.0
	_panel.anchor_right = 1.0
	_panel.anchor_bottom = 1.0
	_panel.offset_left = -390.0
	_panel.offset_top = 8.0
	_panel.offset_right = -8.0
	_panel.offset_bottom = -8.0
	layer.add_child(_panel)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_panel.add_child(scroll)
	var list := VBoxContainer.new()
	list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(list)
	var title := Label.new()
	title.text = "City generator  (T to close)"
	title.add_theme_font_size_override("font_size", 17)
	list.add_child(title)
	var seed_row := HBoxContainer.new()
	var seed_label := Label.new()
	seed_label.text = "Seed"
	seed_label.custom_minimum_size.x = 150.0
	seed_row.add_child(seed_label)
	_seed_box = SpinBox.new()
	_seed_box.min_value = 1
	_seed_box.max_value = 999999
	_seed_box.value = settings.city_seed
	_seed_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_seed_box.value_changed.connect(func(value: float) -> void: settings.city_seed = int(value))
	seed_row.add_child(_seed_box)
	list.add_child(seed_row)
	_ring_box = CheckBox.new()
	_ring_box.text = "Ring road around the city"
	_ring_box.button_pressed = settings.ring_road
	_ring_box.toggled.connect(func(on: bool) -> void: settings.ring_road = on)
	list.add_child(_ring_box)
	var chase_title := Label.new()
	chase_title.text = "Chase (Enter starts / stops)"
	chase_title.add_theme_font_size_override("font_size", 16)
	list.add_child(chase_title)
	list.add_child(_minute_row())
	list.add_child(_value_row("Cop top speed at minute 0 (km/h)", 80.0, 200.0, 1.0, chase.base_top_speed * 3.6,
		func(value: float) -> void: chase.base_top_speed = value / 3.6))
	list.add_child(_value_row("Cop catch-up boost when behind", 1.0, 1.8, 0.05, chase.catch_up_boost,
		func(value: float) -> void: chase.catch_up_boost = value))
	var car_title := Label.new()
	car_title.text = "Car handling (live, no regenerate needed)"
	car_title.add_theme_font_size_override("font_size", 16)
	list.add_child(car_title)
	for tunable: Array in CAR_TUNABLES:
		list.add_child(_slider_row(tunable, true))
	var city_title := Label.new()
	city_title.text = "City (press G to rebuild)"
	city_title.add_theme_font_size_override("font_size", 16)
	list.add_child(city_title)
	for tunable: Array in TUNABLES:
		list.add_child(_slider_row(tunable, false))
	var buttons := HFlowContainer.new()
	list.add_child(buttons)
	_button(buttons, "Regenerate (G)", func() -> void: regenerate())
	_button(buttons, "New seed (N)", func() -> void: _new_seed())
	_button(buttons, "Save settings", func() -> void: _save_settings())
	_button(buttons, "Reset defaults", func() -> void: _reset_settings())


func _slider_row(tunable: Array, car: bool) -> Control:
	var property: String = tunable[0]
	var row := VBoxContainer.new()
	var top := HBoxContainer.new()
	var name_label := Label.new()
	name_label.text = tunable[1]
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(name_label)
	var value_label := Label.new()
	top.add_child(value_label)
	row.add_child(top)
	var slider := HSlider.new()
	slider.min_value = tunable[2]
	slider.max_value = tunable[3]
	slider.step = tunable[4]
	slider.value = float((handling if car else settings).get(property))
	value_label.text = _format(slider.value, slider.step)
	slider.value_changed.connect(func(value: float) -> void:
		var target: Object = handling if car else settings
		var current: Variant = target.get(property)
		target.set(property, int(value) if current is int else value)
		value_label.text = _format(value, slider.step))
	row.add_child(slider)
	_controls[("car." if car else "") + property] = [slider, value_label]
	return row


func _value_row(text: String, low: float, high: float, step: float, value: float, apply: Callable) -> Control:
	var row := VBoxContainer.new()
	var top := HBoxContainer.new()
	var name_label := Label.new()
	name_label.text = text
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(name_label)
	var value_label := Label.new()
	value_label.text = _format(value, step)
	top.add_child(value_label)
	row.add_child(top)
	var slider := HSlider.new()
	slider.min_value = low
	slider.max_value = high
	slider.step = step
	slider.value = value
	slider.value_changed.connect(func(changed: float) -> void:
		apply.call(changed)
		value_label.text = _format(changed, step))
	row.add_child(slider)
	return row


## Jumps the chase clock to any minute so escalation can be tested without driving that long.
func _minute_row() -> Control:
	var row := VBoxContainer.new()
	var top := HBoxContainer.new()
	var name_label := Label.new()
	name_label.text = "Jump chase to minute"
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(name_label)
	var value_label := Label.new()
	value_label.text = "0.0"
	top.add_child(value_label)
	row.add_child(top)
	var slider := HSlider.new()
	slider.min_value = 0.0
	slider.max_value = 20.0
	slider.step = 0.5
	slider.value_changed.connect(func(value: float) -> void:
		chase.elapsed = value * 60.0
		value_label.text = "%.1f" % value)
	row.add_child(slider)
	return row


func _button(parent: Control, text: String, action: Callable) -> void:
	var button := Button.new()
	button.text = text
	button.pressed.connect(action)
	parent.add_child(button)


func _format(value: float, step: float) -> String:
	if step >= 1.0:
		return str(int(value))
	return "%.2f" % value


# --- screenshots for review ----------------------------------------------------

func _capture() -> void:
	DirAccess.make_dir_recursive_absolute(_capture_dir)
	await _snap("chase_start")
	Input.action_press("accelerate")
	await get_tree().create_timer(3.0).timeout
	await _snap("chase_driving")
	Input.action_release("accelerate")
	_map.visible = true
	_map.fit()
	await _snap("map")
	_map.center_on_player()
	_map._zoom = 2.2
	await _snap("map_zoom")
	_map.visible = false
	var aerial := Camera3D.new()
	add_child(aerial)
	aerial.near = 1.0
	aerial.far = settings.view_distance + 200.0
	var focus: Vector3 = player.global_position
	aerial.look_at_from_position(focus + Vector3(70.0, 85.0, 70.0), focus, Vector3.UP)
	aerial.current = true
	await _snap("aerial")
	aerial.look_at_from_position(focus + Vector3(-30.0, 6.0, -30.0), focus + Vector3(30.0, 4.0, 30.0), Vector3.UP)
	await _snap("street")
	world_environment.environment.fog_enabled = false
	aerial.look_at_from_position(Vector3(0.0, settings.city_radius * 0.9, settings.city_radius * 1.1), Vector3.ZERO, Vector3.UP)
	aerial.near = 4.0
	aerial.far = settings.city_radius * 4.0
	await _snap("overview")
	world_environment.environment.fog_enabled = true


func _snap(label: String) -> void:
	for frame: int in 6:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image: Image = get_viewport().get_texture().get_image()
	image.save_png(_capture_dir.path_join(label + ".png"))
	print("CITY_LAB captured ", label)
