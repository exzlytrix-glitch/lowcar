extends SceneTree
func _initialize() -> void:
	root.unfocusable = true
	root.mode = Window.MODE_MINIMIZED
	call_deferred("run")
func run() -> void:
	var garage := (load("res://scenes/review/car_animation_garage.tscn") as PackedScene).instantiate()
	root.add_child(garage)
	await process_frame
	garage.set_process(false)
	for child: Node in garage.get_children():
		if child is CanvasLayer:
			child.visible = false
	garage.select_clip("explode")
	var chase: Node3D = garage.vehicle.get_node("ChaseCamera")
	chase.reset_view()
	chase.camera.current = true
	await physics_frame
	for frame: int in [7, 12, 36]:
		garage.apply_preview(frame)
		await process_frame
		RenderingServer.force_draw(false)
		root.get_texture().get_image().save_png("res://../../work/car_death_frames/chase_explode_%02d.png" % frame)
	garage.queue_free()
	await process_frame
	await process_frame
	print("LOWCAR_DEATH_CHASE_CAPTURE_PASS")
	quit()
