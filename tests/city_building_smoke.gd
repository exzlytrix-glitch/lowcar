extends SceneTree
## Actual imported geometry, road clearance, seeded coverage, and garage collisions.
var failures: Array[String] = []

func _initialize() -> void:
	call_deferred("run")

func check(condition: bool, description: String) -> void:
	if condition:
		print("PASS: ", description)
	else:
		failures.append(description)
		printerr("CITY_BUILDINGS_FAIL: ", description)

func run() -> void:
	var game := (load("res://scenes/main/main.tscn") as PackedScene).instantiate()
	root.add_child(game)
	await process_frame
	game.start_run(142857)
	await physics_frame
	await physics_frame
	var buildings := get_nodes_in_group("city_buildings")
	var initial_count := buildings.size()
	var kit_count := CityBuildingKit.catalog().size()
	var coverage_ids: Dictionary = {}
	for building: Node3D in buildings:
		coverage_ids[building.get_meta("building_id")] = true
	# The growing catalog eventually exceeds the starting neighborhood's distinct
	# slots. Build adjacent rows through the real placement path until all are seen.
	var coverage_chunks: Array[CityChunk] = []
	var coverage_row := 3
	while coverage_ids.size() < kit_count and coverage_row <= kit_count:
		for x: int in range(-2, 3):
			var chunk := CityChunk.new()
			root.add_child(chunk)
			chunk.build(Vector2i(x, coverage_row), 142857)
			coverage_chunks.append(chunk)
			for placed: Node3D in chunk.get_children():
				if placed.is_in_group("city_buildings"):
					buildings.append(placed)
					coverage_ids[placed.get_meta("building_id")] = true
			if coverage_ids.size() == kit_count:
				break
		coverage_row += 1
	if not coverage_chunks.is_empty():
		await physics_frame
		await physics_frame
	var ids: Dictionary = {}
	var contained := true
	var grounded := true
	var collidable := true
	var actual_bounds_match := true
	for building: Node3D in buildings:
		ids[building.get_meta("building_id")] = true
		var actual := AABB()
		var first := true
		for visual: MeshInstance3D in building.find_children("*", "MeshInstance3D", true, false):
			var bounds: AABB = visual.global_transform * visual.mesh.get_aabb()
			actual = bounds if first else actual.merge(bounds)
			first = false
		var expected: AABB = building.global_transform * (building.get_meta("local_bounds") as AABB)
		actual_bounds_match = actual_bounds_match and actual.position.distance_to(expected.position) < .005 and actual.end.distance_to(expected.end) < .005
		var chunk := building.get_parent() as CityChunk
		var signs: Vector2i = building.get_meta("plot_signs")
		var local := AABB(actual.position - chunk.global_position, actual.size)
		var xmin := 10.5 if signs.x > 0 else -31.5
		var xmax := 31.5 if signs.x > 0 else -10.5
		var zmin := 10.5 if signs.y > 0 else -31.5
		var zmax := 31.5 if signs.y > 0 else -10.5
		contained = contained and local.position.x >= xmin and local.end.x <= xmax and local.position.z >= zmin and local.end.z <= zmax
		grounded = grounded and absf(actual.position.y - .26) < .005 and building.scale.is_equal_approx(Vector3.ONE)
		collidable = collidable and not building.find_children("*", "CollisionShape3D", true, false).is_empty()
	check(initial_count == 100 and ids.size() == kit_count, "All %d finished models are placed across the initial neighborhood and adjacent blocks" % kit_count)
	check(actual_bounds_match and contained, "Imported balconies, awnings and roof geometry stay inside their plots")
	check(grounded, "Buildings retain authored scale and sit on the sidewalk")
	check(collidable, "Every placed building has world collision")
	var space := (game as Node3D).get_world_3d().direct_space_state
	var clear_streets := true
	for axis: Vector3 in [Vector3.RIGHT, Vector3.FORWARD]:
		var query := PhysicsRayQueryParameters3D.create(axis * -150 + Vector3.UP, axis * 150 + Vector3.UP, 1)
		clear_streets = clear_streets and space.intersect_ray(query).is_empty()
	check(clear_streets, "Both main driving streets remain clear of building collision")
	var garage: Node3D
	for building: Node3D in buildings:
		if building.get_meta("building_id") == "redline_garage":
			garage = building
			break
	var bays: Array[bool] = []
	for x: float in [-4.6, 0.0, 4.6]:
		var query := PhysicsRayQueryParameters3D.create(garage.to_global(Vector3(x, 1.5, 6.7)), garage.to_global(Vector3(x, 1.5, 0)), 1)
		bays.append(not space.intersect_ray(query).is_empty())
	check(bays == [false, false, true], "Garage collision preserves two open bays and the closed shutter")
	var duplex: Node3D
	for building: Node3D in buildings:
		if building.get_meta("building_id") == "courtyard_duplex":
			duplex = building
			break
	if duplex != null:
		var courtyard := PhysicsRayQueryParameters3D.create(duplex.to_global(Vector3(2.1, 1.4, 6.7)), duplex.to_global(Vector3(2.1, 1.4, 0)), 1)
		var rear_wing := PhysicsRayQueryParameters3D.create(duplex.to_global(Vector3(2.1, 1.4, 0)), duplex.to_global(Vector3(2.1, 1.4, -1.5)), 1)
		check(space.intersect_ray(courtyard).is_empty() and not space.intersect_ray(rear_wing).is_empty(), "Duplex courtyard stays open while its rear wing remains solid")
	var before := layout(game.get_node("World") as CityStreamer)
	game.restart_run()
	await physics_frame
	check(layout(game.get_node("World") as CityStreamer) == before, "Restart recreates the same model selection, positions and rotations")
	game.start_run(73819)
	await physics_frame
	check(layout(game.get_node("World") as CityStreamer) != before, "A different city seed changes the building arrangement")
	for chunk: CityChunk in coverage_chunks:
		chunk.queue_free()
	game.queue_free()
	await process_frame
	print("CITY_BUILDINGS_CHECKS: 9 checks; ", failures.size(), " failures")
	quit(0 if failures.is_empty() else 1)

func layout(world: CityStreamer) -> Array:
	var result: Array = []
	for chunk: CityChunk in world.active_chunks.values():
		for building: Node3D in chunk.get_children():
			if building.is_in_group("city_buildings"):
				result.append([chunk.grid_coordinate, building.get_meta("building_id"), building.position, building.rotation])
	return result
