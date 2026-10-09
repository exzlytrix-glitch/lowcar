extends SceneTree
## Verifies actual physics/events plus held poses, independent wheel pivots, and lifecycle.
var failures: Array[String] = []
var checks: int = 0
var vehicle: ArcadeVehicle
var presentation: CarPresentation
var floor_body: StaticBody3D

func _initialize() -> void:
	call_deferred("run")

func run() -> void:
	var library := load("res://resources/animation/car_animation_pack.tres") as AnimationLibrary
	check(library != null and library.get_animation_list().size() == 34, "All 34 authored clips load")
	var valid: bool = true
	for clip: StringName in library.get_animation_list():
		var anim: Animation = library.get_animation(clip)
		valid = valid and anim.get_track_count() == (8 if String(clip) in CarCrashEffects.DEATH_CLIPS else 7) and is_equal_approx(anim.step, 1.0 / 12.0)
		for track: int in range(anim.get_track_count()):
			valid = valid and anim.track_get_interpolation_type(track) == Animation.INTERPOLATION_NEAREST
			for key: int in range(anim.track_get_key_count(track)):
				var value: Vector3 = anim.track_get_key_value(track, key)
				valid = valid and value.is_finite()
				if String(anim.track_get_path(track)).ends_with(":scale"):
					valid = valid and value.x > 0.0 and value.y > 0.0 and value.z > 0.0
	check(valid, "Every clip has finite, positive, stepped 12 FPS tracks")
	floor_body = StaticBody3D.new()
	floor_body.collision_layer = 1
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(1000, 0.2, 1000)
	collision.shape = shape
	collision.position.y = -0.1
	floor_body.add_child(collision)
	root.add_child(floor_body)
	vehicle = (load("res://scenes/vehicles/player_car.tscn") as PackedScene).instantiate() as ArcadeVehicle
	root.add_child(vehicle)
	vehicle.get_node("PlayerInput").set_physics_process(false)
	vehicle.get_node("ChaseCamera").set_process(false)
	presentation = vehicle.get_node("Presentation") as CarPresentation
	await settle(303)
	var collider: BoxShape3D = (vehicle.get_node("Collision") as CollisionShape3D).shape
	var original_size: Vector3 = collider.size
	check(presentation.trunk.get_child_count() > 0, "Trunk lid is a separate hinged mesh")
	check(presentation.wheels.get_child_count() == 4 and presentation.wheels.get_node("FrontLeft/FrontLeftSteer/FrontLeftSpin") != null, "Four independent suspension, steering, and spin pivots import")
	# Pose sampling at multiple render rates, without controller/event interference.
	presentation.set_process(false)
	for fps: int in [30, 60, 120]:
		presentation.preview_clip("drive")
		var before: int = presentation.pose_sample_count
		for index: int in range(fps):
			presentation._process(1.0 / fps)
		check(presentation.pose_sample_count - before == 12, "Exactly 12 body samples at %d render FPS" % fps)
	presentation.preview_clip("turn_left_a")
	vehicle.forward_speed = 12.0
	presentation._process(1.0 / 12.0)
	var held: Vector3 = presentation.chassis.rotation
	var spin := presentation.wheels.get_node("FrontLeft/FrontLeftSteer/FrontLeftSpin") as Node3D
	var before_spin: float = spin.rotation.x
	presentation._process(0.02)
	presentation._process(0.02)
	check(held.is_equal_approx(presentation.chassis.rotation) and not is_equal_approx(before_spin, spin.rotation.x), "Body holds its pose while wheel spin continues between samples")
	check(collider.size == original_size and vehicle.scale == Vector3.ONE, "Visual squash leaves the physical collider and vehicle scale intact")
	# Playback switches carry the previous silhouette through held transition poses.
	presentation.reset_pose(333)
	vehicle.set_physics_process(false)
	vehicle.forward_speed = 12.0
	vehicle.set_driver_command(1.0,-0.8,false)
	for sample: int in range(12):
		presentation._process(1.0/12.0)
	var turn_rotation: Vector3 = presentation.chassis.rotation
	var front_left := presentation.wheels.get_node("FrontLeft") as Node3D
	var front_right := presentation.wheels.get_node("FrontRight") as Node3D
	check(turn_rotation.z < deg_to_rad(-5.0) and front_right.scale.y < front_left.scale.y, "A loaded left turn compresses the outside tires")
	var planted: bool = true
	for wheel: Node3D in presentation.wheels.get_children():
		planted = planted and absf(wheel.position.y - presentation._wheel_rest[wheel.name].y * wheel.scale.y) < 0.0001
	check(planted, "Loaded tire centers preserve their road contact height")
	vehicle.set_driver_command(1.0,0.0,false)
	presentation._process(0.001)
	check(presentation.current_clip == "recover" and presentation.chassis.rotation.is_equal_approx(turn_rotation), "Releasing steering carries the bank instead of snapping through neutral")
	var recover_pose: Vector3 = presentation.chassis.rotation
	presentation._process(0.02)
	check(presentation.chassis.rotation.is_equal_approx(recover_pose), "Transition poses stay held between 12 FPS samples")
	presentation._process(1.0/12.0)
	check(absf(presentation.chassis.rotation.z) < absf(turn_rotation.z) and absf(presentation.chassis.rotation.z) > 0.001, "The first recovery step unloads weight without erasing the bank")
	for sample: int in range(8):
		presentation._process(1.0/12.0)
	check(absf(presentation.chassis.rotation.z) < 0.01, "Turn recovery settles completely into driving")
	vehicle.set_driver_command(1.0,-0.8,false)
	for sample: int in range(10):
		presentation._process(1.0/12.0)
	turn_rotation = presentation.chassis.rotation
	vehicle.set_driver_command(1.0,0.8,false)
	presentation._process(0.001)
	check(presentation.current_clip.begins_with("turn_right_") and presentation.chassis.rotation.is_equal_approx(turn_rotation), "Opposite steering responds immediately while preserving the outgoing pose")
	for sample: int in range(3):
		presentation._process(1.0/12.0)
	check(presentation.chassis.rotation.z > deg_to_rad(4.0), "An opposite turn crosses into its new bank within three held poses")
	for fps: int in [30,60,120]:
		presentation.reset_pose(334)
		var before_switches: int = presentation.pose_sample_count
		for frame: int in range(fps):
			vehicle.set_driver_command(1.0,-0.8 if int(frame*6/fps)%2 == 0 else 0.8,false)
			presentation._process(1.0/fps)
		check(presentation.pose_sample_count-before_switches == 12, "Rapid maneuvers preserve 12 pose samples at %d render FPS" % fps)
	# Opposing throttle loads the travel-facing axle in either direction.
	for direction: float in [1.0,-1.0]:
		presentation.reset_pose(335)
		vehicle.forward_speed = 20.0*direction
		vehicle.set_driver_command(-direction,0.0,false)
		for sample: int in range(12):
			presentation._process(1.0/12.0)
		check(presentation.current_clip == "brake" and presentation.chassis.rotation.x*direction < deg_to_rad(-1.0), "Held %s braking keeps its directional weight load" % ("forward" if direction > 0 else "reverse"))
	vehicle.set_physics_process(true)
	presentation.set_process(true)
	await settle(404)
	# Repeated identical turns: stable style during a turn, slight change between turns.
	var turn_clips: Array[String] = []
	var gains: Array[float] = []
	for attempt: int in range(6):
		vehicle.forward_speed = 12.0
		vehicle.set_driver_command(1.0, -0.75, false)
		await frames(3)
		turn_clips.append(presentation.current_clip)
		gains.append(presentation.turn_gain)
		var serial: int = presentation.turn_serial
		var gain: float = presentation.turn_gain
		await frames(45)
		check(presentation.turn_serial == serial and presentation.turn_gain == gain, "Turn %d keeps one style without per-frame random jitter" % (attempt + 1))
		vehicle.set_driver_command(0.0, 0.0, false)
		await frames(40)
	var unique: Dictionary = {}
	var no_repeat: bool = true
	for index: int in range(turn_clips.size()):
		unique[turn_clips[index]] = true
		if index > 0:
			no_repeat = no_repeat and turn_clips[index] != turn_clips[index - 1]
	check(unique.size() >= 2 and no_repeat, "Repeated turns use bounded variants with no immediate repeat")
	check(gains.min() >= 0.965 and gains.max() <= 1.035 and gains.min() < gains.max(), "Turn exaggeration varies subtly within the intended range")
	await settle(404)
	vehicle.forward_speed = 12.0
	vehicle.set_driver_command(1.0, -0.75, false)
	await frames(3)
	check(presentation.current_clip == turn_clips[0] and is_equal_approx(presentation.turn_gain, gains[0]), "Restart seed reproduces the first turn style")
	# Controls remain reactive during authored turn anticipation and sustained braking.
	vehicle.set_driver_command(1.0, 0.75, false)
	await frames(3)
	check(presentation.current_clip.begins_with("turn_right_"), "Opposite steering interrupts turn-in promptly")
	vehicle.set_driver_command(1.0, 0.75, true)
	await frames(55)
	check(presentation.current_clip == "handbrake_right" and absf(presentation.chassis.rotation.y) > 0.04, "Held handbrake preserves the slide yaw instead of losing it to a normal turn")
	await settle(450)
	vehicle.forward_speed = 30.0
	vehicle.set_driver_command(-1.0,0.0,false)
	await frames(40)
	var braking_clip: String = presentation.current_clip
	var braking_time: float = presentation.animation.current_animation_position
	await frames(4)
	check(braking_clip == "brake" and presentation.current_clip == "brake" and presentation.animation.current_animation_position >= braking_time, "Sustained braking holds its final pose without repeating the impact")
	vehicle.set_driver_command(0.0,0.0,false)
	await frames(3)
	check(presentation.current_clip == "recover", "Brake release triggers a controlled recovery")
	# Full real launch, with physics-determined rise, hang, drop, and floor contact.
	await settle(505)
	var launcher := vehicle.get_node("Attachments/GroundPunch") as LauncherAttachment
	check(launcher.try_activate(), "Ground Punch activates the authored launch")
	await frames(2)
	check(presentation.current_clip == "launch", "Launch anticipation plays immediately")
	var saw_rise: bool = false
	var saw_hang: bool = false
	var saw_drop: bool = false
	var open_before_contact: bool = false
	var minimum_height: float = 1.0
	for index: int in range(180):
		await frames(1)
		saw_rise = saw_rise or presentation.current_clip == "air_rise"
		saw_hang = saw_hang or presentation.current_clip == "air_hang"
		saw_drop = saw_drop or presentation.current_clip == "air_drop"
		open_before_contact = open_before_contact or (not vehicle.is_on_floor() and vehicle.position.y > 0.5 and presentation.trunk.rotation.x < deg_to_rad(-10.0))
		if presentation.current_clip.begins_with("land_"):
			minimum_height = minf(minimum_height, presentation.chassis.scale.y)
	check(saw_rise and saw_hang and saw_drop, "Real jump traverses rise, apex hang, and falling clips")
	check(open_before_contact, "Trunk opens during the fall before floor contact")
	check(presentation.last_landing_category == "hard" and minimum_height < 0.6, "Full jump produces a clearly flattened hard landing")
	await frames(80)
	check(absf(presentation.trunk.rotation.x) < 0.01 and absf(presentation.chassis.scale.y - 1.0) < 0.02, "Trunk slams shut and body returns to neutral after recovery")
	# A steering request can follow the rebound before the quiet landing tail ends.
	await settle(550)
	vehicle.position.y = 12.0
	vehicle.forward_speed = 12.0
	vehicle.set_driver_command(1.0,0.7,false)
	vehicle.reset_physics_interpolation()
	var contact_index: int = -1
	var steer_index: int = -1
	var closed_on_contact: bool = false
	for index: int in range(160):
		await frames(1)
		if contact_index < 0 and presentation.current_clip.begins_with("land_hard_"):
			contact_index = index
			closed_on_contact = absf(presentation.trunk.rotation.x) < deg_to_rad(1.0) and presentation.chassis.scale.y < 0.6
		if contact_index >= 0 and presentation.current_clip.begins_with("turn_right_"):
			steer_index = index
			break
	check(closed_on_contact, "A real hard landing slams the trunk closed on the contact squash")
	check(steer_index-contact_index >= 25 and steer_index-contact_index <= 40, "New steering follows the main landing rebound before the recovery tail ends")
	# Three actual drops exercise severity selection instead of calling the event directly.
	var minimums: Array[float] = []
	var categories: Array[String] = []
	for height: float in [1.2, 4.0, 12.0]:
		await settle(606)
		vehicle.position.y = height
		vehicle.velocity = Vector3.ZERO
		vehicle.reset_physics_interpolation()
		var minimum: float = 1.0
		for index: int in range(130):
			await frames(1)
			if presentation.current_clip.begins_with("land_"):
				minimum = minf(minimum, presentation.chassis.scale.y)
		minimums.append(minimum)
		categories.append(presentation.last_landing_category)
	check(categories == ["soft", "medium", "hard"], "Real 1.2 m, 4 m, and 12 m drops select soft, medium, and hard impacts")
	check(minimums[0] > minimums[1] and minimums[1] > minimums[2], "Squash increases with actual drop severity")
	print("DROP_EVIDENCE: categories=%s minimum_body_heights=%s" % [categories, minimums])
	# Pause an actual falling trunk, then resume and reset.
	await settle(707)
	vehicle.position.y = 9.0
	vehicle.velocity.y = -8.0
	vehicle.reset_physics_interpolation()
	await frames(10)
	paused = true
	var pause_snapshot: Dictionary = presentation.snapshot()
	var paused_position: Vector3 = vehicle.position
	await create_timer(0.15, true).timeout
	check(presentation.snapshot() == pause_snapshot and vehicle.position == paused_position, "Pause freezes clip time, body, trunk, and physics together")
	paused = false
	await frames(8)
	check(presentation.snapshot() != pause_snapshot, "Resume continues the interrupted animation")
	await settle(808)
	presentation.preview_clip("land_hard_a")
	presentation.preview_frame(1)
	check(presentation.chassis.scale.y < 0.6, "Review scene can inspect the held squash pose")
	presentation.reset_pose(808)
	check(presentation.chassis.scale.is_equal_approx(Vector3.ONE) and presentation.trunk.rotation == Vector3.ZERO and presentation.turn_serial == 0, "Reset clears deformation, trunk, and variation state")
	# A physical wall collision triggers crash; the terminal pose survives disabled driving.
	var wall := StaticBody3D.new()
	wall.collision_layer = 4
	var wall_collision := CollisionShape3D.new()
	var wall_shape := BoxShape3D.new()
	wall_shape.size = Vector3(20, 5, 1)
	wall_collision.shape = wall_shape
	wall.add_child(wall_collision)
	wall.position = Vector3(0, 2.5, -6)
	root.add_child(wall)
	vehicle.forward_speed = 25.0
	vehicle.set_driver_command(1, 0, false)
	var crash_seen: bool = false
	for index: int in range(30):
		await frames(1)
		crash_seen = crash_seen or presentation.current_clip.begins_with("crash_")
	check(crash_seen, "Actual wall impact triggers the crash animation")
	vehicle.stop_vehicle()
	await frames(90)
	check(presentation.current_clip == "crash_front" and presentation.crash_effects.damage.z > 0.7, "Crash holds its settled damaged pose after controls are disabled")
	check(collider.size == original_size, "All landings and crashes preserve physical collision dimensions")
	vehicle.queue_free()
	floor_body.queue_free()
	wall.queue_free()
	await process_frame
	# Review controls use the same native clips and actual physics actor.
	var garage := (load("res://scenes/review/car_animation_garage.tscn") as PackedScene).instantiate()
	root.add_child(garage)
	await process_frame
	garage.select_clip("land_hard_a")
	garage.toggle_play()
	garage.frame_slider.value = 1
	check(garage.presentation.chassis.scale.y < 0.6 and not garage.playing, "Garage timeline scrubs a paused impact pose")
	garage.physics_drop()
	await frames(20)
	check(garage.camera.position.y > 10.0 and garage.presentation.current_clip == "air_drop", "Garage follows an actual high drop and plays its falling clip")
	garage.select_clip("drive")
	check(is_equal_approx(garage.camera.position.y,4.1) and garage.vehicle.position.y == 0.0, "Returning from a physics demo restores the clip-review camera")
	garage.physics_launch()
	await frames(15)
	check(garage.vehicle.position.y > 0.5 and garage.presentation.current_clip == "launch", "Garage launch waits for real floor contact before activating")
	garage.toggle_play()
	var garage_pause: Dictionary = garage.presentation.snapshot()
	await create_timer(0.1,true).timeout
	check(paused and garage.presentation.snapshot() == garage_pause, "Garage pause button freezes the real physics demo")
	garage.toggle_play()
	await frames(10)
	check(not paused and garage.presentation.snapshot() != garage_pause, "Garage play button resumes the real physics demo")
	var next_event := InputEventKey.new()
	next_event.keycode = KEY_RIGHT
	next_event.pressed = true
	garage._input(next_event)
	check(not garage.physics_demo and garage.selected == "accelerate" and is_equal_approx(garage.camera.position.y,4.1), "Garage keyboard navigation exits physics and selects the next clip")
	garage.queue_free()
	await process_frame
	if failures.is_empty():
		print("LOWCAR_ANIMATION_PASS: %d checks" % checks)
		quit(0)
	else:
		for failure: String in failures:
			printerr("LOWCAR_ANIMATION_FAIL: " + failure)
		quit(1)

func settle(seed_value: int) -> void:
	vehicle.reset_vehicle(Vector3(0, 0.1, 0))
	vehicle.controls_enabled = true
	(vehicle.get_node("Attachments/GroundPunch") as LauncherAttachment).reset_attachment()
	presentation.reset_pose(seed_value)
	await frames(15)

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
