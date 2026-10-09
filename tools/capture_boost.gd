extends SceneTree
## Native chase-camera replay: cruise, real ten-second charge, release, and recovery.
const FOLDER := "res://../../work/car_boost_frames"

func _initialize() -> void:
	call_deferred("capture")

func capture() -> void:
	root.size = Vector2i(1280,800)
	root.msaa_3d = Viewport.MSAA_4X
	var game := (load("res://scenes/main/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await process_frame
	game.start_run(142857)
	var car := game.get_node("Vehicles/PlayerCar") as ArcadeVehicle
	var presentation := car.get_node("Presentation") as CarPresentation
	car.get_node("PlayerInput").set_physics_process(false)
	for frame: int in range(15):
		await physics_frame
	car.set_driver_command(1,0,false,false)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(FOLDER))
	var metadata: Array = []
	for index: int in range(216):
		if index == 24:
			car.set_driver_command(1,0,false,true)
		if index == 145:
			car.set_driver_command(1,0,false,false)
		for step: int in range(5):
			await physics_frame
		await process_frame
		RenderingServer.force_draw(false)
		root.get_texture().get_image().save_png(FOLDER+"/frame_%03d.png" % index)
		metadata.append({"index":index,"phase":car.boost.phase,"charge":car.boost.charge_seconds,
			"power":car.boost.power,"remaining":car.boost.remaining,"speed":car.forward_speed,
			"fire_length":presentation.boost_exhaust.flame_length,"body_height":presentation.chassis.scale.y,
			"run_phase":root.get_node("RunSession").phase})
	var file := FileAccess.open(FOLDER+"/frames.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(metadata,"  "))
	print("LOWCAR_BOOST_CAPTURE: %d native frames" % metadata.size())
	quit()
