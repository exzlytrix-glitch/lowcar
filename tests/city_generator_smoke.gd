extends SceneTree
## City generator lab: deterministic layouts, planar roads, sane junctions, buildings off the road,
## and the real car driving on generated streets.
var failures: Array[String] = []


func _initialize() -> void:
	call_deferred("run")


func check(condition: bool, description: String) -> void:
	if condition:
		print("PASS: ", description)
	else:
		failures.append(description)
		printerr("CITY_GENERATOR_FAIL: ", description)


func run() -> void:
	var settings := CityGenSettings.new()
	for seed_value: int in [7, 21, 4242]:
		settings.city_seed = seed_value
		var generator := RoadGenerator.new()
		var graph: RoadGraph = generator.generate(settings)
		var again: RoadGraph = RoadGenerator.new().generate(settings)
		check(_signature(graph) == _signature(again), "seed %d builds the same roads every time" % seed_value)
		var crossings: int = 0
		var sharp: int = 0
		var edges: PackedInt32Array = graph.alive_edges()
		for id: int in edges:
			var a: int = graph.edge_a[id]
			var b: int = graph.edge_b[id]
			if graph.crosses(graph.positions[a], graph.positions[b], a, b):
				crossings += 1
		for node: int in graph.node_count():
			var list: Array = graph.node_edges[node]
			for i: int in list.size():
				for j: int in range(i + 1, list.size()):
					var gap: float = absf(angle_difference(graph.direction_from(node, list[i]), graph.direction_from(node, list[j])))
					if gap < deg_to_rad(settings.min_junction_angle - 1.0):
						sharp += 1
		check(edges.size() > 500, "seed %d grows a real network (%d road pieces)" % [seed_value, edges.size()])
		check(crossings == 0, "seed %d: every crossing is a junction (%d unjoined)" % [seed_value, crossings])
		check(sharp <= edges.size() / 100, "seed %d: junction angles respect the minimum (%d sharp)" % [seed_value, sharp])
		var blocks: Array[CityBlocks.Block] = CityBlocks.build(graph, generator, settings)
		check(blocks.size() > 60, "seed %d: roads enclose real blocks (%d)" % [seed_value, blocks.size()])
		var styles: Dictionary = {}
		for block: CityBlocks.Block in blocks:
			styles[block.style] = true
		check(styles.size() >= 2, "seed %d: more than one district street pattern" % seed_value)

	var lab: Node3D = (load("res://scenes/review/city_lab.tscn") as PackedScene).instantiate()
	root.add_child(lab)
	while lab.get("city") == null or lab.get("_busy"):
		await process_frame
	var city: CityBuilder = lab.get("city")
	var lab_graph: RoadGraph = lab.get("graph")
	check(city.building_count > 300, "the lab fills blocks with kit buildings (%d)" % city.building_count)
	var on_road: int = 0
	for footprint: PackedVector2Array in city.footprints:
		for corner: Vector2 in footprint:
			var near: Dictionary = lab_graph.closest_road_point(corner, 20.0)
			if not near.is_empty() and corner.distance_to(near["point"]) < lab_graph.edge_width[int(near["edge"])] * 0.5:
				on_road += 1
				break
	check(on_road == 0, "no building sits on a road (%d overlapping)" % on_road)
	var car: ArcadeVehicle = lab.get("player")
	var start: Vector3 = car.global_position
	Input.action_press("accelerate")
	for frame: int in 180:
		await physics_frame
	Input.action_release("accelerate")
	var travelled: float = Vector2(car.global_position.x - start.x, car.global_position.z - start.z).length()
	check(travelled > 30.0, "the car drives along a generated street (%.1f m)" % travelled)
	check(car.global_position.y > -0.5, "the car stays on the generated ground")
	await _check_handling(lab, car as LabVehicle)
	if failures.is_empty():
		print("CITY_GENERATOR_OK")
	quit(1 if not failures.is_empty() else 0)


## Open ground outside the city: sharp steering at cruise, a held drift, and a glancing wall scrape.
func _check_handling(lab: Node3D, car: LabVehicle) -> void:
	var settings: CityGenSettings = lab.get("settings")
	var open := Vector3(settings.city_radius + 500.0, 0.2, 0.0)
	Input.action_press("accelerate")
	_launch(car, open, 0.0, 32.0)
	Input.action_press("steer_right")
	for frame: int in 30:
		await physics_frame
	Input.action_release("steer_right")
	var turned: float = absf(angle_difference(0.0, car.rotation.y))
	check(turned > 0.85, "half a second of full steering at 115 km/h turns %.0f° (old car about 47°)" % rad_to_deg(turned))
	_launch(car, open, 0.0, 30.0)
	Input.action_press("steer_left")
	Input.action_press("handbrake")
	var widest: float = 0.0
	for frame: int in 60:
		await physics_frame
		widest = maxf(widest, absf(car.slip_angle))
	var drifting: bool = car.drifting
	var drift_speed: float = car.forward_speed
	Input.action_release("handbrake")
	Input.action_release("steer_left")
	check(drifting and widest > deg_to_rad(15.0), "handbrake + steer holds a drift (%.0f° slide)" % rad_to_deg(widest))
	check(drift_speed > 20.0, "a one-second drift keeps speed (%.1f m/s)" % drift_speed)
	var wall := StaticBody3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(1.0, 4.0, 300.0)
	var collision := CollisionShape3D.new()
	collision.shape = shape
	wall.add_child(collision)
	lab.add_child(wall)
	wall.global_position = open + Vector3(6.0, 2.0, -120.0)
	await physics_frame
	# Heading 15° toward the wall at 115 km/h.
	_launch(car, open, -deg_to_rad(15.0), 32.0)
	var scraped: bool = false
	for frame: int in 60:
		await physics_frame
		scraped = scraped or car.get_slide_collision_count() > 0
	Input.action_release("accelerate")
	check(scraped and car.forward_speed > 22.0, "a 15° wall scrape keeps speed (%.1f m/s)" % car.forward_speed)
	wall.queue_free()


func _launch(car: LabVehicle, at: Vector3, yaw: float, speed: float) -> void:
	car.reset_vehicle(at)
	car.rotation.y = yaw
	car.forward_speed = speed
	var forward: Vector3 = -car.global_basis.z * speed
	car.velocity = Vector3(forward.x, 0.0, forward.z)


func _signature(graph: RoadGraph) -> String:
	var total := Vector2.ZERO
	for id: int in graph.alive_edges():
		total += graph.positions[graph.edge_a[id]] + graph.positions[graph.edge_b[id]]
	return "%d:%.3f:%.3f" % [graph.alive_edges().size(), total.x, total.y]
