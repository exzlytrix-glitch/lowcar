extends SceneTree
## Records how real Godot cars move under scripted controls, so the GPU training world
## (training/gpu_world/) can replay exactly the same controls and be compared frame by frame.
## The city is generated from --city-seed exactly like tools/export_gpu_world.gd does.
##
## Scenarios: runner / cop   one car, random controls (steering, throttle, handbrake drifts, boosts, walls)
##            rear            a faster cop drives into the runner from behind
##            angle           a faster cop comes in at an angle from behind and to the side
## godot --headless --fixed-fps 60 --path . --script res://tools/gpu_parity_trace.gd -- --out=FILE
##   --scenario=runner --city-seed=1000 --seconds=30 --input-seed=1
## Output JSON: start states, per-decision controls per car, per-frame states per car
## ([x, z, yaw, vx, vz, forward_speed, drifting, health, boost_phase, slip, spin, steer, grip_return,
##   drift_time, stagger, wall_contact, boost_charge, boost_power, boost_duration, boost_elapsed, max_speed]).

var out_path: String = "user://trace.json"
var scenario: String = "runner"
var city_seed: int = 1000
var radius: float = 450.0
var seconds: float = 30.0
var input_seed: int = 1
var _rng := RandomNumberGenerator.new()


func _initialize() -> void:
	for argument: String in OS.get_cmdline_user_args():
		var value: String = argument.get_slice("=", 1)
		match argument.get_slice("=", 0):
			"--out":
				out_path = value
			"--scenario":
				scenario = value
			"--city-seed":
				city_seed = int(value)
			"--radius":
				radius = float(value)
			"--seconds":
				seconds = float(value)
			"--input-seed":
				input_seed = int(value)
	_rng.seed = input_seed
	call_deferred("run")


func run() -> void:
	var settings := CityGenSettings.new()
	settings.city_seed = city_seed
	settings.city_radius = radius
	var generator := RoadGenerator.new()
	var graph: RoadGraph = generator.generate(settings)
	var blocks: Array[CityBlocks.Block] = CityBlocks.build(graph, generator, settings)
	var world := Node3D.new()
	root.add_child(world)
	var city := CityBuilder.new()
	city.collision_only = true
	world.add_child(city)
	city.build(settings, graph, generator, blocks)
	var nav := RoadNav.new(graph)
	var maker := ChaseMatch.new()
	maker.layer = 2
	var cars: Array[LabVehicle] = []
	var roles: Array[String] = []
	roles.append("cop" if scenario == "cop" else "runner")
	if scenario == "rear" or scenario == "angle":
		roles.append("cop")
	for role: String in roles:
		var car: LabVehicle = maker._make_car(role == "runner")
		world.add_child(car)
		car.chamfer_collider()
		cars.append(car)
	await physics_frame
	var spot: Dictionary = _straight_spot(nav, graph)
	var point: Vector2 = spot["point"]
	var dir: Vector2 = spot["dir"]
	_place(cars[0], point, dir, 20.0)
	if scenario == "rear":
		_place(cars[1], point - dir * 25.0, dir, 30.0)
		cars[1].tuning.maximum_speed_mps = 44.0
	elif scenario == "angle":
		var side := Vector2(-dir.y, dir.x)
		_place(cars[1], point - dir * 18.0 + side * 3.5, (dir - side * 0.35).normalized(), 32.0)
		cars[1].tuning.maximum_speed_mps = 44.0
	var starts: Array = []
	for car: LabVehicle in cars:
		starts.append(_state(car))
	var controls: Array = []
	var frames: Array = []
	for car: LabVehicle in cars:
		controls.append([])
		frames.append([])
	var plans: Array = []
	for car: LabVehicle in cars:
		plans.append({"left": 0, "throttle": 1.0, "steer": 0.0, "handbrake": false, "boost": 0})
	var total: int = int(seconds * Engine.physics_ticks_per_second)
	for frame: int in total:
		await physics_frame
		for index: int in cars.size():
			frames[index].append(_state(cars[index]))
		if frame % 6 == 0:
			for index: int in cars.size():
				var command: Array = _next_command(plans[index], index)
				controls[index].append(command)
				cars[index].set_driver_command(command[0], command[1], command[2] > 0.5, command[3] > 0.5)
	var file := FileAccess.open(out_path, FileAccess.WRITE)
	file.store_string(JSON.stringify({"scenario": scenario, "city_seed": city_seed, "radius": radius,
		"roles": roles, "start": starts, "controls": controls, "frames": frames,
		"cop_top_speed": cars[cars.size() - 1].tuning.maximum_speed_mps}))
	file.close()
	print("PARITY_TRACE %s: %d frames, %d cars -> %s" % [scenario, total, cars.size(), out_path])
	quit()


## Controls change every 0.3-2 s: mostly throttle with wandering steering, sometimes braking, coasting,
## handbrake drifts or a held boost charge. Crash scenarios drive straight.
func _next_command(plan: Dictionary, index: int) -> Array:
	if scenario == "rear" or scenario == "angle":
		return [1.0, 0.0, 0.0, 0.0]
	plan["left"] -= 1
	if plan["left"] <= 0:
		plan["left"] = _rng.randi_range(3, 20)
		var roll: float = _rng.randf()
		plan["throttle"] = 1.0 if roll < 0.7 else (0.5 if roll < 0.8 else (0.0 if roll < 0.9 else -1.0))
		plan["steer"] = _rng.randf_range(-1.0, 1.0) if _rng.randf() < 0.7 else 0.0
		plan["handbrake"] = _rng.randf() < 0.15
		plan["boost"] = _rng.randi_range(5, 25) if _rng.randf() < 0.12 and index == 0 else 0
	var hold: bool = plan["boost"] > 0
	if hold:
		plan["boost"] -= 1
	return [plan["throttle"], plan["steer"], 1.0 if plan["handbrake"] else 0.0, 1.0 if hold else 0.0]


func _straight_spot(nav: RoadNav, graph: RoadGraph) -> Dictionary:
	var spot: Dictionary = {}
	for attempt: int in 200:
		spot = nav.random_road_spot(_rng)
		if spot.is_empty():
			continue
		var found: Dictionary = graph.closest_road_point(spot["point"], 5.0)
		if not found.is_empty() and graph.edge_length(found["edge"]) > 70.0:
			return spot
	return spot


func _place(car: LabVehicle, point: Vector2, dir: Vector2, speed: float) -> void:
	car.reset_vehicle(Vector3(point.x, 0.0, point.y))
	car.rotation.y = atan2(-dir.x, -dir.y)
	car.forward_speed = speed
	car.velocity = Vector3(dir.x, 0.0, dir.y) * speed
	car.reset_physics_interpolation()
	car.controls_enabled = true


func _state(car: LabVehicle) -> Array:
	return [snappedf(car.global_position.x, 0.0001), snappedf(car.global_position.z, 0.0001),
		snappedf(car.rotation.y, 0.00001), snappedf(car.velocity.x, 0.0001), snappedf(car.velocity.z, 0.0001),
		snappedf(car.forward_speed, 0.0001), 1 if car.drifting else 0, snappedf(car.health, 0.001),
		car.boost.phase, snappedf(car.slip_angle, 0.0001), snappedf(car.spin, 0.0001), snappedf(car._steer, 0.00001),
		snappedf(car._grip_return, 0.00001), snappedf(car.drift_time, 0.0001), snappedf(car.stagger, 0.0001),
		1 if car._wall_contact else 0, snappedf(car.boost.charge_seconds, 0.0001), snappedf(car.boost.power, 0.0001),
		snappedf(car.boost.duration, 0.0001), snappedf(car.boost.elapsed, 0.0001), car.tuning.maximum_speed_mps]
