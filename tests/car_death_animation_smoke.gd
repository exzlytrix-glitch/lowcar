extends SceneTree
var failures: Array[String] = []
var checks: int = 0
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var floor_body := StaticBody3D.new()
	floor_body.collision_layer = 1
	var floor_collision := CollisionShape3D.new()
	var floor_shape := BoxShape3D.new()
	floor_shape.size = Vector3(80,.2,80)
	floor_collision.shape = floor_shape
	floor_collision.position.y = -.1
	floor_body.add_child(floor_collision)
	root.add_child(floor_body)
	var vehicle := (load("res://scenes/vehicles/player_car.tscn") as PackedScene).instantiate() as ArcadeVehicle
	root.add_child(vehicle)
	vehicle.get_node("PlayerInput").set_physics_process(false)
	vehicle.get_node("ChaseCamera").set_process(false)
	vehicle.tuning = vehicle.tuning.duplicate()
	vehicle.tuning.road_grip = 0.0
	var presentation := vehicle.get_node("Presentation") as CarPresentation
	vehicle.crashed.connect(func(_reason: String) -> void: vehicle.stop_vehicle())
	var collider := (vehicle.get_node("Collision") as CollisionShape3D).shape as BoxShape3D
	var dimensions: Vector3 = collider.size
	for clip: String in ["crash_front", "crash_left", "crash_right"]:
		var wall := StaticBody3D.new()
		wall.collision_layer = 1
		var collision := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = Vector3(20,5,1) if clip == "crash_front" else Vector3(1,5,20)
		collision.shape = shape
		wall.add_child(collision)
		wall.position = Vector3(0,2.5,-5) if clip == "crash_front" else Vector3(-4 if clip == "crash_left" else 4,2.5,0)
		root.add_child(wall)
		vehicle.reset_vehicle(Vector3(0,.05,0))
		presentation.reset_pose(7)
		vehicle.controls_enabled = true
		vehicle.velocity = Vector3(0,0,-26) if clip == "crash_front" else Vector3(-26 if clip == "crash_left" else 26,0,0)
		vehicle.forward_speed = 26 if clip == "crash_front" else 0
		for frame: int in range(40):
			await physics_frame
		await process_frame
		check(presentation.current_clip == clip, "Actual wall normal selects " + clip)
		presentation.set_process(false)
		presentation.preview_frame(20)
		var damage: Vector3 = presentation.crash_effects.damage
		check(damage.z > .7 if clip == "crash_front" else (damage.x > .7 and damage.y == 0 if clip == "crash_left" else damage.y > .7 and damage.x == 0), "Damage remains on the struck region: " + clip)
		check(collider.size == dimensions and vehicle.scale == Vector3.ONE, "Damage preserves the collider: " + clip)
		var held: Transform3D = presentation.chassis.transform
		presentation._process(.01)
		check(presentation.chassis.transform == held, "Crash drawing holds between samples: " + clip)
		wall.queue_free()
		await process_frame
		presentation.set_process(true)
	vehicle.set_physics_process(false)
	presentation.set_process(false)
	vehicle.reset_vehicle(Vector3(0,.05,0))
	presentation.reset_pose(8)
	presentation.play_explosion()
	check(presentation.current_clip == "explode" and not vehicle._terminal_collision, "Standalone explosion starts without a collision")
	presentation.preview_frame(5)
	check(presentation.crash_effects.snapshot().intact_visible, "Pressure swell keeps the recognizable car intact")
	presentation.preview_frame(6)
	var peak: Dictionary = presentation.crash_effects.snapshot()
	check(peak.parts_visible and peak.intact_visible and peak.flash and peak.pieces == 4 and peak.flames > 0, "Blast releases four wheels while preserving the red body and showing held flame drawings")
	presentation.preview_frame(16)
	check(presentation.crash_effects.snapshot().flames > 0 and not presentation.crash_effects.snapshot().flash, "Orange flame tail follows the single flash drawing")
	var pieces: Array[Node3D] = presentation.crash_effects._pieces
	var flying: Transform3D = pieces[0].transform
	presentation.preview_frame(30)
	presentation.preview_frame(16)
	check(pieces[0].transform.is_equal_approx(flying), "Explosion scrubs deterministically in either direction")
	presentation.preview_frame(36)
	check(not presentation.crash_effects.snapshot().flash and presentation.crash_effects.snapshot().flames == 0 and presentation.chassis.scale.y < .65, "Blast effects expire while the flattened red wreck remains")
	var grounded: bool = true
	for piece: Node3D in pieces:
		for point: Vector3 in presentation.crash_effects._ground_points[piece.name]:
			grounded = grounded and (piece.transform * point).y >= -0.001
	check(grounded and not presentation.launcher_foot.visible, "Every debris piece stays above the road and the intact attachment disappears")
	presentation.reset_pose(9)
	var reset: Dictionary = presentation.crash_effects.snapshot()
	check(reset.intact_visible and not reset.parts_visible and reset.damage == Vector3.ZERO and presentation.chassis.scale == Vector3.ONE, "Restart restores every intact part and clears damage")
	vehicle.queue_free()
	floor_body.queue_free()
	await process_frame
	await process_frame
	for failure: String in failures:
		printerr("LOWCAR_DEATH_FAIL: ", failure)
	print("LOWCAR_DEATH_%s: %d checks" % ["PASS" if failures.is_empty() else "FAIL", checks])
	quit(0 if failures.is_empty() else 1)
func check(condition: bool, description: String) -> void:
	checks += 1
	if condition:
		print("PASS: ", description)
	else:
		failures.append(description)
