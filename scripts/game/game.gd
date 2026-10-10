class_name LowcarGame
extends Node3D
## The game: hideout → breakout → chase → wreck → news report → back to the hideout, in a new city each
## time. The world is the endless city (WorldStreamer), the cops are the lab's (LabChase; learned brains
## when present, wreckable as in training), the car is the lab car (LabVehicle).
## Options after `--`: --seed=N (first city), --autoplay (the AI runner drives and runs loop on their own),
## --capture=DIR (autoplay one run, save screenshots of each part, then quit), --run-seconds=N (testing:
## each chase ends itself after N seconds).

enum State { LOADING, HIDEOUT, BREAKOUT, CHASE, WRECKED, REPORT }

const SETTINGS_PATH: String = "res://resources/citygen/city_lab_settings.tres"

@onready var player: LabVehicle = $PlayerCar
@onready var world_environment: WorldEnvironment = $Environment
var state: State = State.LOADING
var settings: CityGenSettings
var profile: GameProfile
var streamer: WorldStreamer
var chase: LabChase
var hideout: Hideout
var score: RunScore
var breakout: Breakout
var menu: HideoutMenu
var hud: ChaseHud
var report: NewsReport
var broadcast: LabBroadcast
## The menu and cutscene camera (the chase uses the car's own camera).
var camera: Camera3D
var _base_tuning: VehicleTuning
var _loading: CanvasLayer
var _pause: CanvasLayer
var _ai: RunnerBrainDriver
var _autoplay: bool = false
var _capture_dir: String = ""
var _first_seed: int = -1
## Testing: a chase ends itself after this many seconds (0 = never).
var _run_limit: float = 0.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	player.process_mode = Node.PROCESS_MODE_PAUSABLE
	for argument: String in OS.get_cmdline_user_args():
		if argument.begins_with("--seed="):
			_first_seed = int(argument.trim_prefix("--seed="))
		elif argument == "--autoplay":
			_autoplay = true
		elif argument.begins_with("--capture="):
			_capture_dir = argument.trim_prefix("--capture=")
			_autoplay = true
			if _run_limit <= 0.0:
				_run_limit = 30.0
		elif argument.begins_with("--run-seconds="):
			_run_limit = float(argument.trim_prefix("--run-seconds="))
	settings = _load_settings()
	profile = GameProfile.load_profile()
	_base_tuning = player.tuning
	player.takes_damage = true
	player.mass = 1.6
	player.chamfer_collider()
	player.destroyed.connect(_on_wrecked)
	# No jumping, as in the lab.
	(player.get_node("Attachments/GroundPunch") as LauncherAttachment).definition = null
	# Police light bars only flash while a run is "driving".
	RunSession.phase = RunSession.Phase.DRIVING
	camera = Camera3D.new()
	camera.name = "ShowCamera"
	add_child(camera)
	chase = LabChase.new()
	chase.name = "Chase"
	chase.process_mode = Node.PROCESS_MODE_PAUSABLE
	chase.cops_take_damage = true
	add_child(chase)
	chase.cop_wrecked.connect(_on_cop_wrecked)
	score = RunScore.new()
	score.name = "Score"
	add_child(score)
	score.scored.connect(_on_scored)
	breakout = Breakout.new()
	breakout.name = "Breakout"
	breakout.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(breakout)
	breakout.spotted.connect(_on_spotted)
	breakout.finished.connect(_start_chase)
	menu = HideoutMenu.new()
	menu.profile = profile
	menu.visible = false
	add_child(menu)
	menu.start_requested.connect(_start_breakout)
	hud = ChaseHud.new()
	hud.player = player
	hud.chase = chase
	hud.score = score
	hud.visible = false
	add_child(hud)
	report = NewsReport.new()
	add_child(report)
	report.done.connect(_back_to_hideout)
	_build_loading()
	_build_pause()
	if not _capture_dir.is_empty():
		DirAccess.make_dir_recursive_absolute(_capture_dir)
	await _new_world(_first_seed if _first_seed >= 0 else randi_range(1, 999999))
	_enter_hideout()


func _process(_delta: float) -> void:
	if streamer == null or state == State.LOADING:
		return
	if state == State.HIDEOUT or (state == State.BREAKOUT and not player.visible):
		streamer.update(hideout.center)
	else:
		var going := Vector2(player.velocity.x, player.velocity.z)
		streamer.update(Vector2(player.global_position.x, player.global_position.z), going if going.length() > 3.0 else Vector2.ZERO)


func _physics_process(delta: float) -> void:
	if state == State.CHASE and not get_tree().paused:
		score.tick(delta, chase.cops)
		if _run_limit > 0.0 and score.seconds > _run_limit:
			player.apply_damage(10000.0, "test")


func _unhandled_input(event: InputEvent) -> void:
	var key := event as InputEventKey
	if key == null or not key.pressed or key.echo:
		return
	if state == State.CHASE and key.physical_keycode == KEY_ESCAPE:
		_set_paused(not get_tree().paused)
		get_viewport().set_input_as_handled()
	elif state == State.CHASE and get_tree().paused and key.physical_keycode == KEY_Q:
		_set_paused(false)
		player.apply_damage(10000.0, "gave up")
		get_viewport().set_input_as_handled()


# --- the flow -----------------------------------------------------------------------

## A new city: its hideout lot is found first, then the cells around it are built behind the loading card.
func _new_world(seed_value: int) -> void:
	state = State.LOADING
	_loading.visible = true
	menu.visible = false
	hud.visible = false
	await get_tree().process_frame
	await get_tree().process_frame
	chase.stop()
	if is_instance_valid(broadcast):
		broadcast.queue_free()
	if streamer != null:
		streamer.clear()
		remove_child(streamer)
		streamer.queue_free()
	if hideout != null:
		remove_child(hideout)
		hideout.queue_free()
	var started: int = Time.get_ticks_msec()
	var spot: Dictionary = {}
	for attempt: int in 8:
		settings.city_seed = seed_value + attempt * 7919
		streamer = WorldStreamer.new()
		streamer.name = "World"
		streamer.process_mode = Node.PROCESS_MODE_PAUSABLE
		add_child(streamer)
		streamer.setup(settings)
		spot = Hideout.find_spot(streamer, settings)
		if not spot.is_empty():
			break
		remove_child(streamer)
		streamer.queue_free()
	streamer.clear_areas = [Hideout.clear_area(spot)]
	streamer.load_around(spot["center"])
	hideout = Hideout.new()
	hideout.name = "Hideout"
	add_child(hideout)
	hideout.setup(spot, settings)
	chase.setup(streamer.graph, player, streamer.nav)
	if ResourceLoader.exists(LabChase.CHASE_BRAIN_PATH) or ResourceLoader.exists(LabChase.BRAIN_PATH):
		chase.set_brain(true)
	_apply_view()
	print("GAME city %d ready: %d cells in %d ms, cops: %s" % [settings.city_seed, streamer.cells.size(),
		Time.get_ticks_msec() - started, chase.driver_label()])
	_loading.visible = false


func _enter_hideout() -> void:
	state = State.HIDEOUT
	player.stop_vehicle()
	player.visible = false
	player.process_mode = Node.PROCESS_MODE_DISABLED
	hideout.reset_display()
	hideout.menu_camera(camera)
	camera.current = true
	menu.show_menu()
	if not _capture_dir.is_empty():
		_snap_later("1_hideout", 2.0)
	if _autoplay:
		await get_tree().create_timer(3.0).timeout
		if state == State.HIDEOUT:
			_start_breakout()


func _start_breakout() -> void:
	if state != State.HIDEOUT:
		return
	state = State.BREAKOUT
	menu.hide_menu()
	profile.apply(player, _base_tuning)
	player.get_node("Presentation").reset_pose(settings.city_seed)
	breakout.hideout = hideout
	breakout.car = player
	breakout.chase = chase
	breakout.camera = camera
	breakout.play()
	if not _capture_dir.is_empty():
		for shot: Array in [["2_breakout_inside", 0.9], ["3_breakout_rolling", 2.6], ["4_breakout_street", 4.6], ["5_breakout_spotted", 7.2]]:
			_snap_later(shot[0], shot[1])


func _on_spotted() -> void:
	broadcast = LabBroadcast.new()
	broadcast.name = "Broadcast"
	broadcast.chase = chase
	broadcast.player = player
	broadcast.generator = streamer.world
	add_child(broadcast)
	broadcast.announce("BREAKING: police spot the red muscle car leaving a hideout — pursuit underway")
	hud.visible = true


func _start_chase() -> void:
	state = State.CHASE
	player.controls_enabled = true
	var chase_camera: Node = player.get_node("ChaseCamera")
	chase_camera.reset_view()
	(chase_camera.get_node("SpringArm3D/Camera3D") as Camera3D).current = true
	chase.start(false)
	score.start(player)
	hud.visible = true
	if _autoplay:
		var net: PolicyNet = PolicyNet.load_file(RunnerBrainDriver.BRAIN_PATH)
		if net != null:
			_ai = RunnerBrainDriver.new()
			_ai.name = "AIRunner"
			_ai.net = net
			_ai.chase = chase
			_ai.car = player
			player.add_child(_ai)
	if not _capture_dir.is_empty():
		_snap_later("6_chase", 4.0)
		_snap_later("7_chase_later", 18.0)


func _on_scored(label: String, points: int) -> void:
	hud.callout(label, points)
	if is_instance_valid(broadcast) and label == "COP WRECKED":
		broadcast.announce(["Another cruiser out of action!", "Unit down! The suspect leaves a wreck behind!",
			"That cruiser won't be chasing anyone tonight"].pick_random())


func _on_cop_wrecked(cop: LabVehicle) -> void:
	WreckSmoke.attach(cop)
	score.cop_wrecked()


func _on_wrecked() -> void:
	if state != State.CHASE:
		return
	state = State.WRECKED
	score.stop()
	player.controls_enabled = false
	player.get_node("Presentation").play_explosion()
	if is_instance_valid(_ai):
		_ai.queue_free()
	_ai = null
	if is_instance_valid(broadcast):
		broadcast.wrecked(int(score.seconds))
	Engine.time_scale = 0.35
	await get_tree().create_timer(0.7, true, false, true).timeout
	Engine.time_scale = 1.0
	await get_tree().create_timer(1.6).timeout
	var record: bool = profile.add_run(score.total(), score.seconds, score.cops_wrecked)
	hud.visible = false
	state = State.REPORT
	report.show_report(score, record, profile.bank)
	if not _capture_dir.is_empty():
		await get_tree().create_timer(1.5).timeout
		await _snap("8_report")
		get_tree().quit()
	elif _autoplay:
		await get_tree().create_timer(5.0).timeout
		report.close()


func _back_to_hideout() -> void:
	chase.stop()
	await _new_world(randi_range(1, 999999))
	_enter_hideout()


func _set_paused(paused: bool) -> void:
	get_tree().paused = paused
	_pause.visible = paused


# --- setup and screens --------------------------------------------------------------

func _load_settings() -> CityGenSettings:
	if ResourceLoader.exists(SETTINGS_PATH):
		var saved: Resource = load(SETTINGS_PATH)
		if saved is CityGenSettings:
			return saved.duplicate() as CityGenSettings
	return CityGenSettings.new()


func _apply_view() -> void:
	var chase_camera: Camera3D = player.get_node("ChaseCamera/SpringArm3D/Camera3D")
	chase_camera.near = 0.4
	chase_camera.far = settings.view_distance + 80.0
	var environment: Environment = world_environment.environment
	environment.fog_enabled = true
	environment.fog_mode = Environment.FOG_MODE_DEPTH
	environment.fog_depth_begin = settings.view_distance * 0.35
	environment.fog_depth_end = settings.view_distance
	environment.fog_depth_curve = 1.4


func _build_loading() -> void:
	_loading = CanvasLayer.new()
	_loading.layer = 20
	add_child(_loading)
	var back := ColorRect.new()
	back.color = NewsStyle.NAVY
	back.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_loading.add_child(back)
	var column := VBoxContainer.new()
	column.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	column.offset_left = -300
	column.offset_right = 300
	column.offset_top = -60
	column.alignment = BoxContainer.ALIGNMENT_CENTER
	_loading.add_child(column)
	var bug := NewsStyle.panel(NewsStyle.RED, 0, 14)
	bug.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	bug.add_child(NewsStyle.label("L24  ·  LOWCAR NEWS", 26))
	column.add_child(bug)
	var text := NewsStyle.label("Searching the city for the suspect…", 22, NewsStyle.CREAM, false)
	text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(text)


func _build_pause() -> void:
	_pause = CanvasLayer.new()
	_pause.layer = 15
	_pause.visible = false
	add_child(_pause)
	var back := ColorRect.new()
	back.color = Color(0.04, 0.06, 0.09, 0.5)
	back.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_pause.add_child(back)
	var card := NewsStyle.panel(NewsStyle.INK, 10, 24)
	card.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	card.offset_left = -220
	card.offset_right = 220
	card.offset_top = -70
	card.offset_bottom = 70
	_pause.add_child(card)
	var column := VBoxContainer.new()
	column.alignment = BoxContainer.ALIGNMENT_CENTER
	card.add_child(column)
	var title := NewsStyle.label("WE'LL BE RIGHT BACK", 28, NewsStyle.AMBER)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(title)
	var hint := NewsStyle.label("Esc: back to the chase  ·  Q: give up", 18, NewsStyle.CREAM, false)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(hint)


func _snap_later(label: String, seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout
	await _snap(label)


func _snap(label: String) -> void:
	await get_tree().process_frame
	# Draw the frame now: macOS skips drawing while the window is covered, and the capture would wait.
	RenderingServer.force_draw(false)
	var image: Image = get_viewport().get_texture().get_image()
	image.save_png(_capture_dir.path_join(label + ".png"))
	print("GAME captured ", label)
