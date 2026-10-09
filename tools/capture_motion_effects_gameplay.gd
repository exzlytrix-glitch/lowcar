extends SceneTree
## Render actual driving, launcher, and contact events from the normal chase camera.
const FOLDER := "res://../../work/car_effects_gameplay_frames"
func _initialize() -> void:
	call_deferred("capture")

func capture() -> void:
	root.size = Vector2i(1280,800)
	root.msaa_3d = Viewport.MSAA_4X
	var game := (load("res://scenes/main/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await process_frame
	game.start_run(142857)
	var player := game.get_node("Vehicles/PlayerCar") as ArcadeVehicle
	player.get_node("PlayerInput").set_physics_process(false)
	for step: int in range(15):
		await physics_frame
	player.set_driver_command(1,0,false)
	var presentation := player.get_node("Presentation") as CarPresentation
	var polish: bool = "--capture-polish" in OS.get_cmdline_user_args()
	var folder: String = "res://../../work/car_animation_polish_frames" if polish else FOLDER
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(folder))
	var metadata: Array = []
	for index: int in range(120 if polish else 84):
		if polish:
			match index:
				12: player.set_driver_command(1,-0.55,false)
				20: player.set_driver_command(1,0.55,false)
				28: player.set_driver_command(1,0,false)
				32: player.set_driver_command(-1,0,false)
				38: player.set_driver_command(1,0,false)
				79: player.set_driver_command(1,0.4,true)
				85: player.set_driver_command(1,-0.4,false)
				91: player.set_driver_command(1,0,false)
		if index == (48 if polish else 30):
			(player.get_node("Attachments/GroundPunch") as LauncherAttachment).try_activate()
		for step: int in range(5):
			await physics_frame
		await process_frame
		RenderingServer.force_draw(false)
		root.get_texture().get_image().save_png(folder + "/frame_%03d.png" % index)
		var state: Dictionary = presentation.accents.snapshot()
		metadata.append({"index":index,"clip":presentation.current_clip,"speed":player.forward_speed,
			"height":player.position.y,"wind_streaks":state.wind_streaks,"dust_puffs":state.dust_puffs,
			"body_height":presentation.chassis.scale.y,"body_roll":presentation.chassis.rotation_degrees.z,
			"trunk_degrees":presentation.trunk.rotation_degrees.x,"run_phase":root.get_node("RunSession").phase,
			"left_tire_height":presentation.wheels.get_node("FrontLeft").scale.y,
			"right_tire_height":presentation.wheels.get_node("FrontRight").scale.y})
	var file := FileAccess.open(folder+"/frames.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(metadata,"  "))
	print("LOWCAR_EFFECTS_GAMEPLAY_CAPTURE: %d actual driving frames" % metadata.size())
	quit()
