extends SceneTree
## Uses the existing garage and native renderer without touching the running game.
const FOLDER := "res://../../work/car_death_frames"
func _initialize() -> void:
	root.unfocusable = true
	root.mode = Window.MODE_MINIMIZED
	call_deferred("run")
func run() -> void:
	var garage: Node = (load("res://scenes/review/car_animation_garage.tscn") as PackedScene).instantiate()
	root.add_child(garage)
	await process_frame
	garage.set_process(false)
	for child: Node in garage.get_children():
		if child is CanvasLayer:
			child.visible = false
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(FOLDER))
	var metadata: Array = []
	for clip: String in ["crash_front", "crash_left", "crash_right", "explode"]:
		garage.select_clip(clip)
		garage.camera.h_offset = 0.0
		for frame: int in range(int(garage.source.clips[clip].frames) + 1):
			garage.clock = frame / 12.0
			garage.apply_preview(frame)
			await process_frame
			RenderingServer.force_draw(false)
			root.get_texture().get_image().save_png(FOLDER + "/%s_%02d.png" % [clip, frame])
			metadata.append({"clip": clip, "frame": frame, "state": garage.presentation.crash_effects.snapshot()})
	var file := FileAccess.open(FOLDER + "/frames.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(metadata, "  "))
	print("LOWCAR_CAR_DEATH_CAPTURE_PASS: ", metadata.size(), " native frames; four distinct clips")
	garage.queue_free()
	await process_frame
	await process_frame
	quit()
