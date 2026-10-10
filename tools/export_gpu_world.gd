extends SceneTree
## Exports what the GPU training world (training/gpu_world/) needs from the real game, so it never keeps
## its own copy of the numbers:
##   cars.json        runner and cop tuning, handling and crash constants, exactly as chase training uses
##   city_<k>.json    a generated city's road graph and collision-grid size
##   city_<k>.solid   its collision grid: one byte per cell, 1 where a car body (0.7 m up) would hit something
## Cities are generated exactly like the chase arena's (same settings, radius), from seeds base+k.
##
## godot --headless --path . --script res://tools/export_gpu_world.gd -- --out=DIR --cities=8 --seed=1000
##   [--radius=450] [--cell=1.0] [--first=0] [--world]
## --world: pieces of the game's endless city (WorldGen 2 × 2 cells, as the arena's --world-cities).

var out_dir: String = "user://gpu_world"
var cities: int = 8
var first: int = 0
var base_seed: int = 1000
var radius: float = 450.0
var cell: float = 1.0
var world_cities: bool = false


func _initialize() -> void:
	for argument: String in OS.get_cmdline_user_args():
		var value: String = argument.get_slice("=", 1)
		match argument.get_slice("=", 0):
			"--out":
				out_dir = value
			"--cities":
				cities = int(value)
			"--first":
				first = int(value)
			"--seed":
				base_seed = int(value)
			"--radius":
				radius = float(value)
			"--cell":
				cell = float(value)
			"--world":
				world_cities = true
	DirAccess.make_dir_recursive_absolute(out_dir)
	call_deferred("run")


func run() -> void:
	_write_json(out_dir.path_join("cars.json"), _cars())
	for k: int in range(first, first + cities):
		var started: int = Time.get_ticks_msec()
		await _export_city(k)
		print("GPU_WORLD city %d exported in %d ms" % [k, Time.get_ticks_msec() - started])
	quit()


func _export_city(k: int) -> void:
	var settings := CityGenSettings.new()
	settings.city_seed = base_seed + k
	settings.city_radius = radius
	var generator := RoadGenerator.new()
	var graph: RoadGraph
	var half: float = radius
	var extent: float = radius + 80.0
	if world_cities:
		var world_gen := WorldGen.new()
		world_gen.setup(settings)
		var rng := RandomNumberGenerator.new()
		rng.seed = settings.city_seed
		graph = world_gen.training_city(2, rng)
		generator = world_gen
		half = WorldGen.CELL
		extent = WorldGen.training_extent(2)
		settings.city_radius = extent * 1.42
		settings.ring_road = false
	else:
		graph = generator.generate(settings)
	var blocks: Array[CityBlocks.Block] = CityBlocks.build(graph, generator, settings)
	var world := Node3D.new()
	root.add_child(world)
	var city := CityBuilder.new()
	city.collision_only = true
	world.add_child(city)
	city.build(settings, graph, generator, blocks)
	await physics_frame
	await physics_frame
	var size: int = int(ceil(extent * 2.0 / cell))
	var space: PhysicsDirectSpaceState3D = world.get_world_3d().direct_space_state
	var query := PhysicsPointQueryParameters3D.new()
	query.collision_mask = 1
	var solid := PackedByteArray()
	solid.resize(size * size)
	for row: int in size:
		var z: float = -extent + (row + 0.5) * cell
		for col: int in size:
			query.position = Vector3(-extent + (col + 0.5) * cell, 0.7, z)
			if not space.intersect_point(query, 1).is_empty():
				solid[row * size + col] = 1
	var file := FileAccess.open(out_dir.path_join("city_%d.solid" % k), FileAccess.WRITE)
	file.store_buffer(solid)
	file.close()
	var nodes: Array = []
	for node: int in graph.node_count():
		nodes.append([snappedf(graph.positions[node].x, 0.001), snappedf(graph.positions[node].y, 0.001)])
	var edges: Array = []
	for id: int in graph.alive_edges():
		edges.append([graph.edge_a[id], graph.edge_b[id], snappedf(graph.edge_width[id], 0.01)])
	_write_json(out_dir.path_join("city_%d.json" % k), {"seed": settings.city_seed, "radius": half,
		"extent": extent, "cell": cell, "size": size, "nodes": nodes, "edges": edges,
		"buildings": city.building_count})
	world.queue_free()
	await process_frame


func _cars() -> Dictionary:
	var maker := ChaseMatch.new()
	var data: Dictionary = {"physics_hz": Engine.physics_ticks_per_second}
	for role: String in ["runner", "cop"]:
		var car: LabVehicle = maker._make_car(role == "runner")
		var holder := car.get_child(0) as CollisionShape3D
		data[role] = {"tuning": _script_vars(car.tuning), "handling": _script_vars(car.handling),
			"mass": car.mass, "max_health": car.max_health,
			"box": [(holder.shape as BoxShape3D).size.x, (holder.shape as BoxShape3D).size.z]}
		car.free()
	data["lab_vehicle"] = {"wall_drag": LabVehicle.WALL_DRAG, "wall_damage_per_mps": LabVehicle.WALL_DAMAGE_PER_MPS,
		"wall_damage_max": LabVehicle.WALL_DAMAGE_MAX, "crash_push": LabVehicle.CRASH_PUSH,
		"spin_gain": LabVehicle.SPIN_GAIN, "spin_decay": LabVehicle.SPIN_DECAY, "boost_mass": LabVehicle.BOOST_MASS,
		"car_damage_per_hit": LabVehicle.CAR_DAMAGE_PER_HIT, "car_damage_max": LabVehicle.CAR_DAMAGE_MAX,
		"car_damage_threshold": LabVehicle.CAR_DAMAGE_THRESHOLD, "pair_cooldown_frames": LabVehicle.PAIR_COOLDOWN_FRAMES,
		"chamfer": 0.3}
	data["chase"] = {"match_seconds": ChaseMatch.MATCH_SECONDS, "base_top_speed": ChaseMatch.BASE_TOP_SPEED,
		"catch_up_start": ChaseMatch.CATCH_UP_START, "catch_up_full": ChaseMatch.CATCH_UP_FULL,
		"catch_up_boost": ChaseMatch.CATCH_UP_BOOST, "recycle_distance": ChaseMatch.RECYCLE_DISTANCE,
		"runner_standing_start": ChaseMatch.RUNNER_STANDING_START, "cop_parked_start": ChaseMatch.COP_PARKED_START,
		"cop_delay_frames": [ChaseMatch.COP_DELAY_FRAMES.x, ChaseMatch.COP_DELAY_FRAMES.y],
		"squad_odds": Array(ChaseMatch.SQUAD_ODDS), "burst_duration": CopBurst.DURATION,
		"burst_speed_gain": CopBurst.SPEED_GAIN, "boost_charges": Array(RunnerBoost.CHARGES),
		"sight_range": ChaseIntel.SIGHT_RANGE, "always_see": ChaseIntel.ALWAYS_SEE,
		"ping_seconds": ChaseIntel.PING_SECONDS, "lead_seconds": ChaseIntel.LEAD_SECONDS,
		"standoff_speed": StandoffRule.SPEED, "standoff_range": StandoffRule.RANGE,
		"standoff_damage": StandoffRule.DAMAGE_PER_SECOND, "standoff_grace": StandoffRule.GRACE,
		"ray_range": CopSenses.RAY_RANGE, "wall_rays": Array(CopSenses.WALL_RAYS), "car_rays": Array(CopSenses.CAR_RAYS),
		"path_ahead": Array(CopSenses.PATH_AHEAD), "goal_ahead": ChaseSenses.GOAL_AHEAD,
		"runner_sense": ChaseSenses.RUNNER_SENSE, "cop_obs": ChaseSenses.COP_OBS, "runner_obs": ChaseSenses.RUNNER_OBS,
		"nav_options": ChaseNav.OPTIONS, "nav_decisions": ChaseNav.DECISIONS, "exit_cover": ChaseNav.EXIT_COVER}
	return data


func _script_vars(object: Object) -> Dictionary:
	var result: Dictionary = {}
	for property: Dictionary in object.get_property_list():
		if property["usage"] & PROPERTY_USAGE_SCRIPT_VARIABLE:
			result[property["name"]] = object.get(property["name"])
	return result


func _write_json(path: String, data: Dictionary) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(data))
	file.close()
