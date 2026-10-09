extends SceneTree
## Capture the normal camera during a real pin and an input-driven boost escape.
func _initialize() -> void:
	root.unfocusable = true
	root.mode = Window.MODE_MINIMIZED
	call_deferred("run")

func run() -> void:
	root.size = Vector2i(1280, 800)
	root.msaa_3d = Viewport.MSAA_4X
	var game: Node = (load("res://scenes/main/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await process_frame
	game.start_run(142857)
	var car := game.get_node("Vehicles/PlayerCar") as ArcadeVehicle
	var session: Node = root.get_node("RunSession")
	var director: Node = game.get_node("ChaseDirector")
	var folder: String = "res://assets/previews"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(folder))
	var pinned: bool = false
	for index: int in range(900):
		await physics_frame
		if session.capture_progress > 0.2:
			pinned = true
			break
	if not pinned:
		printerr("LOWCAR_CHASE_CAPTURE_FAIL: patrols did not catch up")
		quit(1)
		return
	await save_frame(folder + "/police_pin.png")
	Input.action_press("charge_boost")
	for index: int in range(65):
		await physics_frame
	Input.action_release("charge_boost")
	Input.action_press("accelerate")
	for index: int in range(18):
		await physics_frame
	await save_frame(folder + "/police_escape.png")
	if session.phase != session.Phase.DRIVING or car.forward_speed < 30.0:
		printerr("LOWCAR_CHASE_CAPTURE_FAIL: boost escape did not succeed")
		quit(1)
		return
	print("LOWCAR_CHASE_CAPTURE_PASS: pin=%.2f; escape_speed=%.1f; patrols=%d; phase=%d" % [session.capture_progress, car.forward_speed, director.active_police.size(), session.phase])
	Input.action_release("accelerate")
	game.queue_free()
	await process_frame
	await process_frame
	quit()

func save_frame(path: String) -> void:
	await process_frame
	RenderingServer.force_draw(false)
	root.get_texture().get_image().save_png(path)
