extends Node3D
## An isolated animation review stage with authored playback and real physics drops.
const CAPTURE_DIR := "res://../../work/car_animation_frames"
const SOURCE_PATH := "res://resources/animation/car_clips.json"
const SEQUENCE: Array[String] = ["drive", "turn_left_a", "turn_right_b", "brake", "launch", "air_rise", "air_hang", "air_drop", "land_hard_b", "recover"]
var vehicle: ArcadeVehicle
var presentation: CarPresentation
var camera: Camera3D
var title: Label
var description: Label
var status: Label
var picker: OptionButton
var frame_slider: HSlider
var pause_button: Button
var source: Dictionary
var names: Array[String] = []
var selected: String = "air_drop"
var playing: bool = true
var autoplay: bool = false
var physics_demo: bool = false
var effects_demo: bool = false
var _effects_phase: String = ""
var sequence_index: int = 0
var clock: float = 0.0
var _capture: bool = false
var _stage: Node3D
var _crash_wall: MeshInstance3D

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_window().size = Vector2i(1280,800)
	get_viewport().msaa_3d = Viewport.MSAA_4X
	get_window().title = "Lowcar — Animation Garage"
	source = JSON.parse_string(FileAccess.get_file_as_string(SOURCE_PATH))
	for clip: String in source.clips.keys():
		if clip != "RESET":
			names.append(clip)
	build_stage()
	build_ui()
	vehicle = (load("res://scenes/vehicles/player_car.tscn") as PackedScene).instantiate() as ArcadeVehicle
	add_child(vehicle)
	vehicle.get_node("PlayerInput").set_physics_process(false)
	vehicle.get_node("ChaseCamera").set_process(false)
	camera.make_current()
	vehicle.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	vehicle.set_physics_process(false)
	presentation = vehicle.get_node("Presentation") as CarPresentation
	presentation.set_process(false)
	select_clip("crash_front" if "--death-review" in OS.get_cmdline_user_args() else "air_drop")
	_capture = "--capture-animation" in OS.get_cmdline_user_args() or "--capture-physics" in OS.get_cmdline_user_args() or "--capture-effects" in OS.get_cmdline_user_args()
	if _capture:
		call_deferred("capture_effects" if "--capture-effects" in OS.get_cmdline_user_args() else ("capture_physics" if "--capture-physics" in OS.get_cmdline_user_args() else "capture_sequence"))

func build_stage() -> void:
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color("b9dce8")
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color("e3f0ff")
	environment.environment.ambient_light_energy = 0.35
	environment.environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -32, 0)
	sun.light_color = Color("fff0d7")
	sun.light_energy = 0.85
	sun.shadow_enabled = true
	add_child(sun)
	_stage = Node3D.new()
	add_child(_stage)
	add_box("Stage", Vector3(0,-0.12,0), Vector3(18,0.24,18), Color("e9e0ce"))
	add_box("Road", Vector3(0,0.002,0), Vector3(7,0.004,18), Color("727e89"))
	for z: float in [-7.0,-4.0,4.0,7.0]:
		add_box("Lane_mark",Vector3(0,0.004,z),Vector3(0.12,0.008,1.1),Color("f6eedb"))
	for side: float in [-1.0,1.0]:
		add_box("Curb",Vector3(side*3.65,0.045,0),Vector3(0.3,0.09,18),Color("fff1da"))
	for item: Array in [[Vector3(-6,1.3,-6),Vector3(3,2.6,3),Color("92b9ac")],[Vector3(5.5,2.2,-7),Vector3(3,4.4,2),Color("eabc84")],[Vector3(-6.5,2.5,4),Vector3(2,5,2),Color("89a9c8")]]:
		add_box("Backdrop",item[0],item[1],item[2])
	add_box("Crash_review_wall",Vector3(0,.225,-3),Vector3(8,.45,.38),Color("8aa7ae"))
	_crash_wall = _stage.get_node("Crash_review_wall") as MeshInstance3D
	_crash_wall.visible = false
	var floor_body := StaticBody3D.new()
	floor_body.collision_layer = 1
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(1000,0.2,1000)
	collision.shape = shape
	collision.position.y = -0.1
	floor_body.add_child(collision)
	add_child(floor_body)
	camera = Camera3D.new()
	camera.position = Vector3(6.8,4.1,7.6)
	camera.h_offset = 0.0
	camera.look_at_from_position(camera.position, Vector3(0,0.9,0))
	camera.fov = 42
	camera.current = true
	add_child(camera)

func add_box(label: String, at: Vector3, size: Vector3, color: Color) -> void:
	var mesh := MeshInstance3D.new()
	mesh.name = label
	var box := BoxMesh.new()
	box.size = size
	mesh.mesh = box
	var material := StandardMaterial3D.new()
	material.albedo_color = color.srgb_to_linear()
	material.roughness = 0.9
	mesh.material_override = material
	mesh.position = at
	_stage.add_child(mesh)

func build_ui() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := MarginContainer.new()
	panel.position = Vector2(28,24)
	panel.add_theme_constant_override("margin_left",16)
	panel.add_theme_constant_override("margin_top",12)
	panel.add_theme_constant_override("margin_right",16)
	panel.add_theme_constant_override("margin_bottom",12)
	var background := StyleBoxFlat.new()
	background.bg_color = Color(0.08,0.14,0.2,0.9)
	background.corner_radius_top_left = 10
	background.corner_radius_top_right = 10
	background.corner_radius_bottom_left = 10
	background.corner_radius_bottom_right = 10
	var container := PanelContainer.new()
	container.position = Vector2(855,20)
	container.add_theme_stylebox_override("panel",background)
	layer.add_child(container)
	panel.position = Vector2.ZERO
	container.add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation",8)
	panel.add_child(column)
	title = Label.new()
	title.text = "LOWCAR / ANIMATION GARAGE"
	title.add_theme_font_size_override("font_size",18)
	column.add_child(title)
	description = Label.new()
	description.custom_minimum_size.x = 355
	description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	description.add_theme_font_size_override("font_size",16)
	column.add_child(description)
	picker = OptionButton.new()
	for clip: String in names:
		picker.add_item(clip.replace("_", " ").capitalize())
	picker.item_selected.connect(func(index: int) -> void: select_clip(names[index]))
	column.add_child(picker)
	var row := HBoxContainer.new()
	column.add_child(row)
	button(row,"← Previous",func() -> void: step_clip(-1))
	pause_button = button(row,"Pause",toggle_play)
	button(row,"Next →",func() -> void: step_clip(1))
	button(row,"Chase sequence",start_sequence)
	var physics_row := HBoxContainer.new()
	column.add_child(physics_row)
	button(physics_row,"Real launch [L]",func() -> void: physics_launch())
	button(physics_row,"Real 12 m drop [D]",func() -> void: physics_drop())
	var effects_row := HBoxContainer.new()
	column.add_child(effects_row)
	button(effects_row,"Wind + impact review [V]",start_effects_review)
	var death_row := HBoxContainer.new()
	column.add_child(death_row)
	for entry: Array in [["Front", "crash_front"], ["Left", "crash_left"], ["Right", "crash_right"], ["Explode", "explode"]]:
		var death_clip: String = entry[1]
		button(death_row, entry[0], func() -> void: select_clip(death_clip))
	frame_slider = HSlider.new()
	frame_slider.step = 1
	frame_slider.value_changed.connect(func(value: float) -> void:
		if not playing and not physics_demo:
			if effects_demo:
				seek_effects_review(int(value))
				return
			clock = value / 12.0
			apply_preview(int(value))
	)
	column.add_child(frame_slider)
	status = Label.new()
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.custom_minimum_size.x = 355
	status.add_theme_color_override("font_color",Color("ffcf72"))
	column.add_child(status)
	var hint := Label.new()
	hint.text = "← → clips / Space pause / C sequence
Drag timeline while paused to inspect"
	hint.add_theme_font_size_override("font_size",14)
	column.add_child(hint)

func button(parent: Node, text: String, action: Callable) -> Button:
	var result := Button.new()
	result.text = text
	result.pressed.connect(action)
	parent.add_child(result)
	return result

func select_clip(clip: String) -> void:
	effects_demo = false
	physics_demo = false
	autoplay = false
	vehicle.set_physics_process(false)
	presentation.set_process(false)
	get_tree().paused = false
	camera.position = Vector3(6.8,4.1,7.6)
	camera.look_at(Vector3(0,0.9,0))
	presentation.accents.clear()
	selected = clip
	clock = 0.0
	playing = true
	pause_button.text = "Pause"
	presentation.preview_clip(clip)
	picker.select(names.find(clip))
	frame_slider.max_value = source.clips[clip].frames
	description.text = source.clips[clip].description
	_crash_wall.visible = clip.begins_with("crash_") and clip in CarCrashEffects.DEATH_CLIPS
	_crash_wall.position = Vector3(0,.225,-2.58)
	_crash_wall.rotation = Vector3.ZERO
	if clip in ["crash_left", "crash_right"]:
		_crash_wall.position = Vector3(-1.33 if clip == "crash_left" else 1.33,.225,0)
		_crash_wall.rotation.y = PI * .5
		camera.position = Vector3(-5.7 if clip == "crash_left" else 5.7,6.1,7.6)
		camera.look_at(Vector3(0,.9,0))
	if clip == "crash_front":
		camera.position = Vector3(5.8,5.2,-5.2)
		camera.look_at(Vector3(0,.85,0))
	if clip == "explode":
		camera.position = Vector3(8.3,6.1,10.3)
		camera.look_at(Vector3(0,1.4,0))
	if clip in CarCrashEffects.DEATH_CLIPS:
		camera.h_offset = 0.8
	apply_preview(0)

func step_clip(direction: int) -> void:
	select_clip(names[posmod(names.find(selected) + direction, names.size())])

func _process(delta: float) -> void:
	if _capture:
		return
	if effects_demo:
		if playing:
			step_effects_review(delta)
		return
	if physics_demo:
		status.text = "LIVE PHYSICS  /  %s  /  trunk %.0f°  /  body height %.0f%%" % [presentation.current_clip, rad_to_deg(presentation.trunk.rotation.x), presentation.chassis.scale.y * 100]
		update_physics_camera()
		return
	if playing:
		clock += delta
		var duration: float = source.clips[selected].frames / 12.0
		if clock >= duration:
			if autoplay:
				sequence_index = (sequence_index + 1) % SEQUENCE.size()
				var next: String = SEQUENCE[sequence_index]
				select_clip(next)
				autoplay = true
			else:
				clock = fmod(clock,duration)
		apply_preview(int(floor(clock * 12.0)))

func apply_preview(frame: int) -> void:
	presentation.preview_frame(frame)
	var height: float = 0.0
	if selected == "air_rise": height = 1.15
	if selected == "air_hang": height = 1.65
	if selected == "air_drop": height = lerpf(1.65,0.35,frame / float(source.clips[selected].frames))
	if selected == "launch": height = maxf(0.0,(frame - 1) * 0.15)
	var approach: float = maxf(0, 2 - frame) * .38
	var offset: Vector3 = Vector3.ZERO
	if selected == "crash_front": offset.z = approach
	if selected == "crash_left": offset.x = approach
	if selected == "crash_right": offset.x = -approach
	vehicle.position = Vector3(0,height,0) + offset
	presentation.global_transform = vehicle.global_transform
	for wheel: Node3D in presentation.wheels.get_children():
		(wheel.get_node(String(wheel.name) + "Steer/" + String(wheel.name) + "Spin") as Node3D).rotation.x = -clock * 7 if selected in ["drive","accelerate","brake"] or selected.begins_with("turn_") or selected.begins_with("handbrake_") else -clock * 2.5
		(wheel.get_node(String(wheel.name) + "Steer") as Node3D).rotation.y = 0.22 if selected.begins_with("turn_left") else (-0.22 if selected.begins_with("turn_right") else 0.0)
	frame_slider.set_value_no_signal(frame)
	status.text = "12 FPS HELD POSES  /  frame %02d
trunk %.0f°  /  body height %.0f%%" % [frame,rad_to_deg(presentation.trunk.rotation.x),presentation.chassis.scale.y*100]

func start_sequence() -> void:
	sequence_index = 0
	select_clip(SEQUENCE[0])
	autoplay = true

func toggle_play() -> void:
	playing = not playing
	pause_button.text = "Play" if not playing else "Pause"
	if physics_demo:
		get_tree().paused = not playing

func physics_launch() -> void:
	start_physics(0.1)
	# Wait for actual floor contact; the reset's initial settle is not a jump.
	var attempts: int = 0
	while not vehicle.is_on_floor() and physics_demo and attempts < 30:
		await get_tree().physics_frame
		await get_tree().process_frame
		if not get_tree().paused:
			attempts += 1
	if physics_demo and vehicle.is_on_floor():
		(vehicle.get_node("Attachments/GroundPunch") as LauncherAttachment).try_activate()

func physics_drop() -> void:
	start_physics(12.0)
	# Establish that this demo starts in a real airborne state, bypassing menu-spawn settling.
	presentation._has_grounded = true

func update_physics_camera() -> void:
	camera.position.y = 4.1 + vehicle.position.y
	camera.look_at(vehicle.position + Vector3(0,0.9,0))

func start_physics(height: float) -> void:
	effects_demo = false
	get_tree().paused = false
	physics_demo = true
	autoplay = false
	playing = true
	pause_button.text = "Pause"
	vehicle.reset_vehicle(Vector3(0,height,0))
	vehicle.controls_enabled = true
	presentation.reset_pose(12345)
	(vehicle.get_node("Attachments/GroundPunch") as LauncherAttachment).reset_attachment()
	vehicle.set_physics_process(true)
	presentation.set_process(true)
	description.text = "Actual controller, gravity, floor contact, and animation events."

func _input(event: InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo:
		return
	match event.keycode:
		KEY_LEFT: step_clip(-1)
		KEY_RIGHT: step_clip(1)
		KEY_SPACE: toggle_play()
		KEY_C: start_sequence()
		KEY_L: physics_launch()
		KEY_D: physics_drop()
		KEY_V: start_effects_review()
		_: return
	get_viewport().set_input_as_handled()

func capture_sequence() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(CAPTURE_DIR))
	var count: int = 0
	var frames_meta: Array = []
	for clip: String in SEQUENCE:
		select_clip(clip)
		var frame_count: int = source.clips[clip].frames
		for frame: int in range(frame_count):
			clock = frame / 12.0
			apply_preview(frame)
			await get_tree().process_frame
			RenderingServer.force_draw(false)
			var path: String = CAPTURE_DIR + "/frame_%03d.png" % count
			get_viewport().get_texture().get_image().save_png(path)
			frames_meta.append({"index":count,"clip":clip,"frame":frame,"scale_y":presentation.chassis.scale.y,"trunk_degrees":rad_to_deg(presentation.trunk.rotation.x)})
			count += 1
	var meta := FileAccess.open(CAPTURE_DIR + "/frames.json",FileAccess.WRITE)
	meta.store_string(JSON.stringify(frames_meta,"  "))
	print("LOWCAR_NATIVE_CAPTURE: %d frames" % count)
	get_tree().quit()


func capture_physics() -> void:
	var folder: String = "res://../../work/car_physics_frames"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(folder))
	start_physics(0.1)
	for index: int in range(15):
		await get_tree().physics_frame
	(vehicle.get_node("Attachments/GroundPunch") as LauncherAttachment).try_activate()
	var frames_meta: Array = []
	for index: int in range(48):
		for step: int in range(5):
			await get_tree().physics_frame
		await get_tree().process_frame
		update_physics_camera()
		status.text = "LIVE PHYSICS / %s\ntrunk %.0f° / body height %.0f%%" % [presentation.current_clip,rad_to_deg(presentation.trunk.rotation.x),presentation.chassis.scale.y*100]
		RenderingServer.force_draw(false)
		get_viewport().get_texture().get_image().save_png(folder + "/frame_%03d.png" % index)
		frames_meta.append({"index":index,"clip":presentation.current_clip,"height_m":vehicle.position.y,"scale_y":presentation.chassis.scale.y,"trunk_degrees":rad_to_deg(presentation.trunk.rotation.x)})
	var meta := FileAccess.open(folder + "/frames.json",FileAccess.WRITE)
	meta.store_string(JSON.stringify(frames_meta,"  "))
	print("LOWCAR_NATIVE_PHYSICS_CAPTURE: %d frames" % frames_meta.size())
	get_tree().quit()


func start_effects_review() -> void:
	select_clip("drive")
	effects_demo = true
	frame_slider.max_value = 80
	_effects_phase = ""
	clock = 0.0
	description.text = "Speed builds airflow; a hard landing throws a low dust ring and cloud clusters."
	step_effects_review(0.0)


func step_effects_review(delta: float) -> void:
	clock += delta
	if clock >= 6.75:
		clock = fmod(clock,6.75)
		_effects_phase = ""
		presentation.accents.clear(12345)
	var clip: String = "drive"
	var local_time: float = clock
	var height: float = 0.0
	var speed: float = lerpf(10.0,32.0,clampf(clock/1.8,0,1))
	if clock >= 2.5 and clock < 3.0:
		clip = "launch"
		local_time = clock-2.5
		height = maxf(0,(local_time*12-1)*0.15)
	elif clock >= 3.0 and clock < 3.67:
		clip = "air_rise"
		local_time = clock-3.0
		height = lerpf(0.75,1.65,local_time/0.67)
	elif clock >= 3.67 and clock < 4.17:
		clip = "air_hang"
		local_time = clock-3.67
		height = 1.65
	elif clock >= 4.17 and clock < 4.84:
		clip = "air_drop"
		local_time = clock-4.17
		height = lerpf(1.65,0,local_time/0.67)
	elif clock >= 4.84 and clock < 5.76:
		clip = "land_hard_b"
		local_time = clock-4.84
		speed = 0.0
	elif clock >= 5.76:
		clip = "idle"
		local_time = clock-5.76
		speed = 0.0
	vehicle.position = Vector3(0,height,0)
	presentation.global_transform = vehicle.global_transform
	if clip != _effects_phase:
		_effects_phase = clip
		presentation.preview_clip(clip)
		picker.select(names.find(clip))
		if clip == "launch":
			presentation.accents.burst(vehicle.global_transform,false,0.6)
		elif clip == "land_hard_b":
			presentation.accents.burst(vehicle.global_transform,true,1.1)
	var frame: int = int(floor(local_time*12.0))
	if source.clips[clip].loop:
		frame = frame % int(source.clips[clip].frames)
	else:
		frame = mini(frame,int(source.clips[clip].frames))
	presentation.preview_frame(frame)
	for wheel: Node3D in presentation.wheels.get_children():
		(wheel.get_node(String(wheel.name)+"Steer/"+String(wheel.name)+"Spin") as Node3D).rotation.x = -clock*speed/0.46
	presentation.accents.tick(delta,vehicle.global_transform,speed,0.0,height < 0.01,true)
	frame_slider.set_value_no_signal(floor(clock*12.0))
	var effects: Dictionary = presentation.accents.snapshot()
	status.text = "WIND + IMPACT / %s\n%.0f km/h / %d air streaks / %d dust lobes" % [clip,speed*3.6,effects.wind_streaks,effects.dust_puffs]


func seek_effects_review(frame: int) -> void:
	presentation.accents.clear(12345)
	_effects_phase = ""
	clock = 0.0
	step_effects_review(0.0)
	for step: int in range(clampi(frame,0,80)):
		step_effects_review(1.0/12.0)


func capture_effects() -> void:
	var folder: String = "res://../../work/car_effects_frames"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(folder))
	start_effects_review()
	var metadata: Array = []
	for index: int in range(81):
		step_effects_review(1.0/12.0)
		await get_tree().process_frame
		RenderingServer.force_draw(false)
		get_viewport().get_texture().get_image().save_png(folder + "/frame_%03d.png" % index)
		var state: Dictionary = presentation.accents.snapshot()
		metadata.append({"index":index,"clip":_effects_phase,"wind_streaks":state.wind_streaks,"dust_puffs":state.dust_puffs})
	var file := FileAccess.open(folder+"/frames.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(metadata,"  "))
	print("LOWCAR_EFFECTS_CAPTURE: %d native frames" % metadata.size())
	get_tree().quit()
