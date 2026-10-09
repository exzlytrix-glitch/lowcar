extends SceneTree
## Exercises the actual scene lifecycle, driving, launcher, pause, restart, and streaming.

var _failures: Array[String] = []


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	var packed := load("res://scenes/main/main.tscn") as PackedScene
	if packed == null:
		printerr("LOWCAR_SMOKE_FAIL: main scene could not load")
		quit(1)
		return
	var game := packed.instantiate()
	packed = null
	root.add_child(game)
	await process_frame
	await process_frame
	var session := root.get_node("RunSession")
	var vehicle := game.get_node("Vehicles/PlayerCar") as ArcadeVehicle
	var launcher := vehicle.get_node("Attachments/GroundPunch") as LauncherAttachment
	var world: Node = game.get_node("World")
	_check(session.phase == session.Phase.MENU, "Startup reaches the title state")
	_check(world.active_chunks.size() == 25, "Initial city loads the configured block neighborhood")
	_check(AudioServer.bus_count == 4, "Master, SFX, Music, and UI audio buses load")
	game.start_run(142857)
	await _frames(8)
	_check(vehicle.is_on_floor(), "Car settles on the generated road")
	Input.action_press("accelerate")
	await _frames(60)
	_check(vehicle.forward_speed > 8.0, "Driving accelerates the car")
	_check(session.distance_m > 3.0, "Run distance tracks actual movement")
	Input.action_press("attachment_primary")
	await _frames(2)
	Input.action_release("attachment_primary")
	await _frames(25)
	_check(vehicle.global_position.y > 3.0, "Launcher produces real vertical movement")
	_check(not launcher.try_activate(), "Launcher cannot retrigger while airborne")
	var before_pause: Vector3 = vehicle.global_position
	var time_before_pause: float = session.elapsed_s
	session.toggle_pause()
	await create_timer(0.1, true).timeout
	_check(vehicle.global_position.is_equal_approx(before_pause), "Pause stops vehicle physics")
	_check(is_equal_approx(session.elapsed_s, time_before_pause), "Pause stops run time")
	session.toggle_pause()
	Input.action_release("accelerate")
	game.restart_run()
	await _frames(8)
	_check(session.city_seed == 142857, "Restart preserves the city seed")
	_check(session.distance_m < 0.1, "Restart clears run distance")
	_check(launcher.cooldown_remaining <= 0.0, "Restart resets attachment cooldown")
	_check(vehicle.global_position.distance_to(Vector3(4.5, 0.0, 8.0)) < 0.3, "Restart restores the car spawn")
	var double_click := InputEventMouseButton.new()
	double_click.position = Vector2(850.0, 350.0)
	double_click.global_position = double_click.position
	double_click.button_index = MOUSE_BUTTON_LEFT
	double_click.pressed = true
	double_click.double_click = true
	Input.parse_input_event(double_click)
	await _frames(12)
	_check(vehicle.global_position.y > 1.0, "Double-click mouse input reaches the launcher")
	double_click.pressed = false
	double_click.double_click = false
	Input.parse_input_event(double_click)
	game.restart_run()
	await _frames(8)
	var camera := vehicle.get_node("ChaseCamera") as Node3D
	vehicle.global_position = Vector3(4.5, 0.1, -390.0)
	vehicle.reset_physics_interpolation()
	camera.reset_view()
	await _frames(30)
	var coordinate: Vector2i = world.coordinate_for(vehicle.global_position)
	_check(world.active_chunks.has(coordinate), "Streaming supplies the car's current block")
	_check(world.active_chunks.size() == 25, "Streaming remains bounded after crossing multiple blocks")
	session.end_run("CAUGHT")
	_check(session.phase == session.Phase.ENDED, "Capture hook ends the run")
	game.restart_run()
	await _frames(8)
	_check(session.phase == session.Phase.DRIVING, "Restart exits the result state")
	vehicle.forward_speed = 24.0
	load("res://tests/city_smoke_support.gd").approach_building(world, vehicle)
	Input.action_press("accelerate")
	await _frames(35)
	Input.action_release("accelerate")
	_check(session.phase == session.Phase.ENDED and session.end_reason == "CRASHED", "Actual building collision ends the run")
	_check(not game.get_node("GameUI")._result.visible, "The result overlay leaves the crash drawing visible")
	await _frames(100)
	_check(game.get_node("GameUI")._result.visible, "The result overlay appears after the crash finishes")
	game.return_to_title()
	_check(session.phase == session.Phase.MENU, "Return-to-title restores the menu state")
	_check(not vehicle.controls_enabled, "Title state disables driving")
	Input.action_release("accelerate")
	Input.action_release("attachment_primary")
	paused = false
	game.queue_free()
	await process_frame
	await process_frame
	if _failures.is_empty():
		print("LOWCAR_SMOKE_PASS: startup, input driving, launch, pause, restart, streaming, capture hook, title")
		quit(0)
	else:
		for failure: String in _failures:
			printerr("LOWCAR_SMOKE_FAIL: " + failure)
		quit(1)


func _frames(count: int) -> void:
	for _index: int in range(count):
		await physics_frame
	await process_frame


func _check(condition: bool, message: String) -> void:
	if condition:
		print("PASS: " + message)
	else:
		_failures.append(message)
