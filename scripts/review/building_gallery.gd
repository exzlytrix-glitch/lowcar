extends Node3D
## Dedicated native-Godot art review; the gameplay city remains independently tunable.
@export var asset_dir := "res://assets/models/buildings/style_trial/"
@export var ids: Array[String] = ["corner_market", "terrace_apartments", "redline_garage"]
@export var titles: Array[String] = ["CORNER MARKET", "TERRACE APARTMENTS", "REDLINE AUTO"]
@export var notes: Array[String] = [
	"Coral plaster / chamfered entrance / striped awnings / recessed windows",
	"Mint plaster / staggered balconies / coral stair tower / rooftop pergola",
	"Butter yellow / triple sawtooth roof / two open service bays / blue clerestories"
]
@export var scene_folder := "res://scenes/buildings/"
@export var lineup_spacing := 19.0
@export var lineup_size := 38.0
@export var lineup_heading := "THREE STREET PERSONALITIES"
var buildings: Array[Node3D] = []
var camera: Camera3D
var car: Node3D
var ui: CanvasLayer
var heading: Label
var detail: Label
var view_label: Label
var selection := -1
var mode := "orbit"
var yaw := -0.62
var pitch := 0.46
var zoom := 1.0
var dragging := false
var manifest: Dictionary

func _ready() -> void:
	get_window().size = Vector2i(1600, 1000)
	get_window().title = "Lowcar — Building Gallery"
	get_viewport().msaa_3d = Viewport.MSAA_4X
	RenderingServer.directional_shadow_atlas_set_size(4096, false)
	manifest = JSON.parse_string(FileAccess.get_file_as_string(asset_dir + "manifest.json"))
	build_stage()
	for id in ids:
		var building := (load(scene_folder + id + ".tscn") as PackedScene).instantiate() as Node3D
		add_child(building)
		buildings.append(building)
	car = (load("res://scenes/vehicles/red_muscle_car.tscn") as PackedScene).instantiate() as Node3D
	add_child(car)
	build_ui()
	select_building(-1)
	if "--capture-batch" in OS.get_cmdline_user_args():
		call_deferred("capture_lineup")
	elif "--capture-buildings" in OS.get_cmdline_user_args():
		call_deferred("capture_previews")

func mat(hex: String) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(hex).srgb_to_linear()
	material.roughness = 0.9
	return material

func stage_box(label: String, at: Vector3, size: Vector3, color: String) -> void:
	var object := MeshInstance3D.new()
	object.name = label
	var mesh := BoxMesh.new()
	mesh.size = size
	object.mesh = mesh
	object.material_override = mat(color)
	object.position = at
	object.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(object)

func build_stage() -> void:
	var world := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("b9dce8")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("e3f0ff")
	env.ambient_light_energy = 0.40
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	world.environment = env
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-47, -38, 0)
	sun.light_color = Color("fff1db")
	sun.light_energy = 0.55
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 90.0
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_ORTHOGONAL
	sun.directional_shadow_pancake_size = 0.0
	sun.shadow_bias = 0.08
	sun.shadow_normal_bias = 0.7
	sun.shadow_reverse_cull_face = true
	add_child(sun)
	stage_box("Pavement", Vector3(0, -0.17, 0), Vector3(100, 0.3, 38), "d9d4c4")
	stage_box("Street", Vector3(0, -0.05, 10.8), Vector3(100, 0.10, 8.0), "75838a")
	stage_box("Near_curb", Vector3(0, 0.05, 6.77), Vector3(100, 0.2, 0.3), "f5e7cd")
	stage_box("Far_curb", Vector3(0, 0.05, 14.87), Vector3(100, 0.2, 0.3), "f5e7cd")
	for x in range(-46, 47, 6):
		stage_box("Lane_mark", Vector3(x, 0.009, 10.8), Vector3(2.8, 0.014, 0.14), "f5e7cd")
	for x in range(-45, 46, 3):
		stage_box("Paving_joint", Vector3(x, -0.011, 5.9), Vector3(0.018, 0.01, 1.65), "c2bdaF")
	stage_box("Rear_green_strip", Vector3(0, -0.004, -8.0), Vector3(100, 0.04, 3.0), "a3b993")
	camera = Camera3D.new()
	camera.near = 0.1
	camera.far = 120.0
	add_child(camera)
	camera.make_current()

func label(text_value: String, size: int, color: String) -> Label:
	var item := Label.new()
	item.text = text_value
	item.add_theme_font_size_override("font_size", size)
	item.add_theme_color_override("font_color", Color(color))
	return item

func build_ui() -> void:
	ui = CanvasLayer.new()
	add_child(ui)
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ui.add_child(root)
	var top := VBoxContainer.new()
	top.position = Vector2(30, 24)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(top)
	top.add_child(label("LOWCAR   /   BUILDING STUDIES", 17, "2a4656"))
	heading = label("THREE STREET PERSONALITIES", 32, "1c3443")
	top.add_child(heading)
	detail = label("", 16, "365367")
	top.add_child(detail)
	var bottom := VBoxContainer.new()
	bottom.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	bottom.offset_left = 30
	bottom.offset_top = -118
	root.add_child(bottom)
	var buttons := HBoxContainer.new()
	buttons.add_theme_constant_override("separation", 8)
	bottom.add_child(buttons)
	for index in range(-1, ids.size()):
		var button := Button.new()
		button.focus_mode = Control.FOCUS_NONE
		button.text = "0  /  ALL " + str(ids.size()) if index == -1 else str(index+1) + "  /  " + titles[index]
		button.add_theme_font_size_override("font_size", 15)
		button.custom_minimum_size = Vector2(175 if index < 1 else 227, 40)
		button.pressed.connect(select_building.bind(index))
		buttons.add_child(button)
	view_label = label("", 15, "263f50")
	bottom.add_child(view_label)
	bottom.add_child(label("Drag to orbit  /  wheel to zoom  /  G street view  /  I overview  /  B rear  /  Tab hide controls", 15, "365367"))

func select_building(index: int) -> void:
	selection = clampi(index, -1, ids.size()-1)
	yaw = -0.62
	pitch = 0.46
	zoom = 1.0
	mode = "orbit"
	for i in range(ids.size()):
		buildings[i].visible = selection == -1 or selection == i
		buildings[i].position = Vector3((i-(ids.size()-1)*0.5)*lineup_spacing, 0, 0) if selection == -1 else Vector3.ZERO
	car.position = Vector3(0, 0.025, 9.0)
	car.rotation.y = -PI/2 if selection == -1 else 0.0
	heading.text = lineup_heading if selection == -1 else titles[selection]
	if selection == -1:
		detail.text = str(ids.size()) + " original models  /  red muscle car shown at game scale"
	else:
		var count := int(manifest.models[selection].triangles)
		detail.text = notes[selection] + "  /  " + String.num_int64(count) + " triangles"
	update_camera()

func set_view(value: String) -> void:
	mode = value
	if value == "rear":
		yaw = 2.5
		pitch = 0.40
		zoom = 1.0
	elif value == "orbit":
		yaw = -0.62
		pitch = 0.46
		zoom = 1.0
	update_camera()

func update_camera() -> void:
	if mode == "street":
		camera.projection = Camera3D.PROJECTION_PERSPECTIVE
		camera.fov = 62.0
		var street_target := Vector3(0, 3.9, -0.5)
		camera.look_at_from_position(street_target + Vector3(3.6, -0.4, 19.3) * zoom, street_target)
		view_label.text = "STREET VIEW   /   camera behind the red muscle car"
		return
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	var tallest := 0.0
	for entry: Dictionary in manifest.models:
		tallest = maxf(tallest, float(entry.blender_bounds_m.max[2]))
	var model_height := tallest if selection == -1 else float(manifest.models[selection].blender_bounds_m.max[2])
	var target_height := model_height * (0.34 if selection == -1 else 0.43)
	var target := Vector3(0, target_height, 0)
	var distance := 63.0 if selection == -1 else 32.0
	camera.size = (lineup_size if selection == -1 else maxf(18.5, model_height*1.25+3.0)) * zoom
	var offset := Vector3(sin(yaw)*cos(pitch), sin(pitch), cos(yaw)*cos(pitch))*distance
	camera.look_at_from_position(target+offset, target)
	view_label.text = ("REAR VIEW" if mode == "rear" else "OVERVIEW") + "   /   real Godot models and materials"

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_0: select_building(-1)
			KEY_1: select_building(0)
			KEY_2: select_building(1)
			KEY_3: select_building(2)
			KEY_4:
				if ids.size() > 3: select_building(3)
			KEY_G: set_view("street")
			KEY_I, KEY_F: set_view("orbit")
			KEY_B: set_view("rear")
			KEY_TAB: ui.visible = not ui.visible
			KEY_LEFT:
				yaw -= 0.17
				mode = "orbit"
				update_camera()
			KEY_RIGHT:
				yaw += 0.17
				mode = "orbit"
				update_camera()
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			dragging = event.pressed
		elif event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
			zoom = clampf(zoom * (0.92 if event.button_index == MOUSE_BUTTON_WHEEL_UP else 1.08), 0.50, 1.75)
			update_camera()
	if event is InputEventMouseMotion and dragging:
		mode = "orbit"
		yaw -= event.relative.x * 0.006
		pitch = clampf(pitch + event.relative.y * 0.004, 0.10, 1.1)
		update_camera()

func save_capture(filename: String) -> void:
	for frame in range(8):
		await get_tree().process_frame
	RenderingServer.force_draw(false)
	var picture := get_viewport().get_texture().get_image()
	var error := picture.save_png(asset_dir + "previews/" + filename + ".png")
	if error != OK:
		push_error("Building preview could not be saved: " + filename)
		get_tree().quit(1)
	print("BUILDING_CAPTURED ", filename)

func capture_previews() -> void:
	ui.visible = false
	select_building(-1)
	await save_capture("lineup")
	for i in range(ids.size()):
		select_building(i)
		await save_capture(ids[i])
		set_view("rear")
		await save_capture(ids[i]+"_rear")
		set_view("street")
		await save_capture(ids[i]+"_street")
	select_building(-1)
	ui.visible = true
	await save_capture("gallery_controls")
	print("BUILDING_PREVIEWS_OK")
	get_tree().quit()

func capture_lineup() -> void:
	ui.visible = false
	select_building(-1)
	await save_capture("lineup")
	print("BUILDING_BATCH_PREVIEW_OK")
	get_tree().quit()
