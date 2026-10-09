extends SceneTree
## Real main-scene pursuit, cornering, capture, escapes, escalation, and reset.
var failures: Array[String] = []
var checks: int = 0
var game: Node
var car: ArcadeVehicle
var director: Node
var session: Node

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	game = (load("res://scenes/main/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await process_frame
	session = root.get_node("RunSession")
	car = game.get_node("Vehicles/PlayerCar") as ArcadeVehicle
	car.get_node("PlayerInput").set_physics_process(false)
	director = game.get_node("ChaseDirector")
	director.tuning = director.tuning.duplicate() as ChaseTuning
	check(director.active_police.is_empty(), "Title contains no active patrols")
	game.start_run(142857)
	await frames(170)
	check(director.active_police.is_empty(), "Opening grace allows the player to get moving")
	await frames(95)
	check(director.active_police.size() == 2, "Director spawns the first two physical patrols")
	var unit: Node3D = director.active_police[0]
	var before: float = unit.global_position.distance_to(car.global_position)
	var pursuing_position: Vector3 = unit.global_position
	session.toggle_pause()
	await create_timer(0.05, true).timeout
	check(unit.global_position == pursuing_position, "Pause freezes a patrol while its AI is actively pursuing")
	session.toggle_pause()
	await frames(60)
	check(unit.global_position.distance_to(car.global_position) < before - 5.0, "Police AI closes the gap on a stopped player")
	check(unit.collision_layer == 4 and unit.collision_mask == 15, "Patrols physically collide with world, player, and each other")
	await frames(330)
	check(session.phase == session.Phase.ENDED and session.end_reason == "CAUGHT", "Actual pursuing police fill the meter and catch a stationary player")
	check(is_zero_approx(unit.forward_speed), "Result state stops police movement")
	game.restart_run()
	await frames(8)
	check(director.active_police.is_empty() and session.capture_progress == 0.0 and session.pursuit_tier == 1, "Restart clears patrols, heat, and capture progress")
	# Route around a real occupied block, including two 90-degree bends.
	director.set_physics_process(false)
	car.reset_vehicle(Vector3(64, 0.1, -55))
	await frames(8)
	unit = spawn_test_unit(Vector3(0, 0.1, 38), 0)
	var stayed_on_streets: bool = true
	var reached: bool = false
	for index: int in range(1100):
		await physics_frame
		var at: Vector3 = unit.global_position
		stayed_on_streets = stayed_on_streets and at.distance_to(ChaseRoads.project(at)) < 10.5
		if unit.global_position.distance_to(car.global_position) < 8.0:
			reached = true
			break
	print("CORNER_REPLAY: reached=%s at=%s route=%s" % [reached, unit.global_position, unit.route])
	check(reached and stayed_on_streets, "Police follow street corners around buildings and reach another street")
	# A local setup exercises the genuine capture detector and launcher escape.
	unit.reset_vehicle(Vector3(69, 0.1, -55))
	unit.controls_enabled = false
	unit.set_physics_process(false)
	director.tuning.start_grace_seconds = 9999.0
	director.set_physics_process(true)
	await frames(60)
	check(session.capture_progress > 0.2 and session.phase == session.Phase.DRIVING, "Nearby grounded police give a visible escape window before arrest")
	var time_before: float = session.elapsed_s
	var capture_before: float = session.capture_progress
	var unit_before: Vector3 = unit.global_position
	session.toggle_pause()
	await create_timer(0.05, true).timeout
	check(session.elapsed_s == time_before and session.capture_progress == capture_before and unit.global_position == unit_before, "Pause freezes police, run time, and capture together")
	session.toggle_pause()
	(car.get_node("Attachments/GroundPunch") as LauncherAttachment).try_activate()
	await frames(75)
	check(car.global_position.y > 2.0 and session.capture_progress == 0.0, "Ground Punch actually breaks capture and drains the arrest meter")
	# Boost release must escape an arrest without a special police-only exception.
	game.restart_run()
	await frames(8)
	unit = spawn_test_unit(Vector3(9.5, 0.1, 8), 1)
	unit.set_physics_process(false)
	car.set_driver_command(0, 0, false, true)
	await frames(70)
	check(session.capture_progress > 0.2 and session.phase == session.Phase.DRIVING, "Charging from a pin keeps the arrest timer running")
	car.set_driver_command(1, 0, false, false)
	await frames(45)
	check(car.forward_speed > 30.0 and session.capture_progress == 0.0 and session.phase == session.Phase.DRIVING, "Releasing boost outruns nearby cops and clears capture")
	# A hard patrol impact slows the hero and can pin it; wall crashes remain terminal.
	car.reset_vehicle(Vector3(4.5, 0.1, 8))
	unit.reset_vehicle(Vector3(4.5, 0.1, -7))
	car.forward_speed = 24.0
	car.velocity = Vector3(0, 0, -24)
	car.set_driver_command(1, 0, false)
	await frames(40)
	check(session.phase == session.Phase.DRIVING and car.forward_speed < 15.0, "A hard police collision produces a physical pin instead of an instant wall-crash loss")
	# Capture needs line of sight, not just a distance threshold through a wall.
	car.reset_vehicle(Vector3(4.5, 0.1, 8))
	unit.reset_vehicle(Vector3(9.5, 0.1, 8))
	var wall := StaticBody3D.new()
	wall.collision_layer = 1
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(0.4, 4, 8)
	collision.shape = shape
	wall.add_child(collision)
	wall.position = Vector3(7, 2, 8)
	game.add_child(wall)
	await frames(90)
	check(session.capture_progress == 0.0, "Police cannot arrest through world geometry")
	wall.queue_free()
	await frames(2)
	game.restart_run()
	await frames(8)
	director.tuning.start_grace_seconds = 0.0
	session.elapsed_s = 61.0
	car.set_driver_command(1, 0, false)
	await frames(250)
	check(session.pursuit_tier == 3 and director.active_police.size() == 4, "Elapsed time escalates to four real patrols at pursuit three")
	check(director.active_police[0].tuning.maximum_speed_mps > 34.0, "Escalation strengthens actual patrol speed")
	# Exercise the top tier and bounded reinforcements while the hero is out of capture range.
	director.tuning.capture_radius_m = 0.0
	session.elapsed_s = 999.0
	await frames(350)
	check(director.active_police.size() <= 7 and session.pursuit_tier == 6 and director.desired_count() == 7, "Endless pursuit caps active actors and reaches maximum heat")
	game.return_to_title()
	await frames(3)
	check(get_nodes_in_group("police").is_empty() and session.active_police_count == 0, "Returning to title removes patrols and sirens")
	game.queue_free()
	await process_frame
	await process_frame
	if failures.is_empty():
		print("LOWCAR_POLICE_PASS: %d gameplay checks" % checks)
		quit(0)
	else:
		for failure: String in failures:
			printerr("LOWCAR_POLICE_FAIL: " + failure)
		quit(1)

func spawn_test_unit(at: Vector3, id: int) -> Node3D:
	var unit: Node3D = director.police_scene.instantiate()
	game.get_node("Vehicles").add_child(unit)
	unit.reset_vehicle(at)
	unit.configure(car, id, 1, director.tuning)
	director.active_police.append(unit)
	return unit

func frames(count: int) -> void:
	for index: int in range(count):
		await physics_frame
	await process_frame

func check(condition: bool, message: String) -> void:
	checks += 1
	if condition:
		print("PASS: " + message)
	else:
		failures.append(message)
