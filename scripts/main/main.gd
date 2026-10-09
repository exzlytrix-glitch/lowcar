extends Node3D
## Boot, run lifecycle, and scene wiring. Gameplay systems stay in their own scenes.

@onready var world: CityStreamer = $World
@onready var player: ArcadeVehicle = $Vehicles/PlayerCar
@onready var launcher: LauncherAttachment = $Vehicles/PlayerCar/Attachments/GroundPunch
@onready var ui: LowcarUI = $GameUI
var _previous_position: Vector3
const START_POSITION := Vector3(4.5, 0.1, 8.0)


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	ui.start_requested.connect(start_run)
	ui.restart_requested.connect(restart_run)
	ui.resume_requested.connect(RunSession.toggle_pause)
	ui.menu_requested.connect(return_to_title)
	player.crashed.connect(RunSession.end_run)
	RunSession.phase_changed.connect(_on_phase_changed)
	player.reset_vehicle(START_POSITION)
	player.get_node("ChaseCamera").reset_view()
	_previous_position = player.global_position
	RunSession.return_to_menu()


func _physics_process(delta: float) -> void:
	if RunSession.phase != RunSession.Phase.DRIVING:
		_previous_position = player.global_position
		return
	var displacement: Vector3 = player.global_position - _previous_position
	displacement.y = 0.0
	RunSession.advance(delta, displacement.length())
	_previous_position = player.global_position


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		RunSession.toggle_pause()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("restart") and RunSession.phase != RunSession.Phase.MENU:
		restart_run()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("toggle_debug"):
		ui.debug_visible = not ui.debug_visible
		get_viewport().set_input_as_handled()


func start_run(seed_value: int = -1) -> void:
	var next_seed: int = seed_value if seed_value >= 0 else randi_range(1, 2147483646)
	world.reset(next_seed)
	player.reset_vehicle(START_POSITION)
	launcher.reset_attachment()
	player.get_node("Presentation").reset_pose(next_seed)
	player.get_node("ChaseCamera").reset_view()
	_previous_position = player.global_position
	RunSession.begin_run(next_seed)


func restart_run() -> void:
	start_run(RunSession.city_seed)


func return_to_title() -> void:
	RunSession.return_to_menu()
	world.reset(RunSession.city_seed)
	player.reset_vehicle(START_POSITION)
	launcher.reset_attachment()
	player.get_node("Presentation").reset_pose(RunSession.city_seed)
	player.get_node("ChaseCamera").reset_view()


func _on_phase_changed(phase: RunSession.Phase) -> void:
	player.controls_enabled = phase == RunSession.Phase.DRIVING
	if phase == RunSession.Phase.ENDED or phase == RunSession.Phase.MENU:
		player.stop_vehicle()

