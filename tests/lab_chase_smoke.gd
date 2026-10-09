extends SceneTree
## City lab chase, step 1: cops route through the generated streets and reach you, numbers grow
## with chase time, and crashes cost health.
var failures: Array[String] = []


func _initialize() -> void:
	call_deferred("run")


func check(condition: bool, description: String) -> void:
	if condition:
		print("PASS: ", description)
	else:
		failures.append(description)
		printerr("LAB_CHASE_FAIL: ", description)


func run() -> void:
	var lab: Node3D = (load("res://scenes/review/city_lab.tscn") as PackedScene).instantiate()
	root.add_child(lab)
	while lab.get("city") == null or lab.get("_busy"):
		await process_frame
	var chase: LabChase = lab.get("chase")
	var car: LabVehicle = lab.get("player")
	chase.start()
	check(chase.cops.size() == 2, "a chase starts with two cops (%d)" % chase.cops.size())
	var start_gap: float = _nearest(chase, car)
	var closest: float = start_gap
	var moving_frames: int = 0
	var frames: int = 0
	for frame: int in 60 * 25:
		await physics_frame
		frames += 1
		for cop: LabVehicle in chase.cops:
			if Vector2(cop.velocity.x, cop.velocity.z).length() > 8.0:
				moving_frames += 1
				break
		closest = minf(closest, _nearest(chase, car))
		if closest < 22.0:
			break
	check(closest < 22.0, "cops drive the streets from %.0f m away and reach you (%.0f m in %.1f s)" % [start_gap, closest, frames / 60.0])
	check(moving_frames > frames / 2, "cops spend the approach actually driving, not stuck")
	var fallen: bool = false
	for cop: LabVehicle in chase.cops:
		fallen = fallen or cop.global_position.y < -1.0
	check(not fallen, "cops stay on the ground")
	chase.elapsed = 5.0 * 60.0
	for frame: int in 60 * 8:
		await physics_frame
	check(chase.cops.size() >= 5, "minute 5 brings more cops (%d)" % chase.cops.size())
	check(chase.top_speed() > 33.0, "cops get faster with time (%.0f km/h)" % (chase.top_speed() * 3.6))
	chase.stop()
	check(chase.cops.is_empty(), "stopping the chase clears the cops")

	# Head-on into a wall at cruise speed: a good amount of damage, not a wreck.
	var wall := StaticBody3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(30.0, 4.0, 1.0)
	var collision := CollisionShape3D.new()
	collision.shape = shape
	wall.add_child(collision)
	lab.add_child(wall)
	var open := Vector3((lab.get("settings") as CityGenSettings).city_radius + 500.0, 0.2, 0.0)
	wall.global_position = open + Vector3(0.0, 2.0, -20.0)
	car.reset_vehicle(open)
	car.forward_speed = 32.0
	car.velocity = Vector3(0.0, 0.0, -32.0)
	Input.action_press("accelerate")
	for frame: int in 60:
		await physics_frame
	Input.action_release("accelerate")
	check(car.health < 80.0 and car.health > 50.0, "a head-on crash at 115 km/h costs a good amount (%.0f left)" % car.health)
	if failures.is_empty():
		print("LAB_CHASE_OK")
	quit(1 if not failures.is_empty() else 0)


func _nearest(chase: LabChase, car: LabVehicle) -> float:
	var best: float = INF
	for cop: LabVehicle in chase.cops:
		best = minf(best, cop.global_position.distance_to(car.global_position))
	return best
