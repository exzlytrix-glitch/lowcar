extends SceneTree
var failures: Array[String] = []
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var scene: PackedScene = load("res://scenes/chase/police_vehicle.tscn")
	var unit: Node3D = scene.instantiate()
	root.add_child(unit)
	unit.set_physics_process(false)
	await process_frame
	var presentation: Node3D = unit.get_node("Presentation")
	var model: Node3D = presentation.get_node("Model/Belle_Rive_Police_Cruiser")
	var meshes := model.find_children("*", "MeshInstance3D", true, false)
	var bounds := AABB()
	var first := true
	for item in meshes:
		var mesh := item as MeshInstance3D
		var local_bounds: AABB = (model.global_transform.affine_inverse() * mesh.global_transform) * mesh.get_aabb()
		bounds = local_bounds if first else bounds.merge(local_bounds)
		first = false
		for surface in mesh.mesh.get_surface_count():
			check(mesh.get_active_material(surface) != null, "Every imported surface keeps its material")
	check(meshes.size() == 7, "Seven runtime meshes: body, four wheels, two lenses")
	check(bounds.size.x > 2.1 and bounds.size.x < 2.5 and bounds.size.z > 4.9 and bounds.size.z < 5.3, "Ordinary full-size sedan dimensions")
	check(absf(bounds.position.y) < 0.015 and bounds.end.y < 1.95, "Tires meet the road and roof stays normal height")
	unit.forward_speed = 10.0
	unit.steering = 0.65
	presentation._process(0.12)
	for name: String in ["FrontLeft", "FrontRight", "RearLeft", "RearRight"]:
		var wheel: Node3D = model.get_node("Wheels/" + name)
		var steer: Node3D = wheel.get_node(name + "Steer")
		var spin: Node3D = steer.get_node(name + "Spin")
		check(absf(spin.rotation.x) > 0.1, "Authored wheel rotates: " + name)
		check(absf(steer.rotation.y) > 0.1 if name.begins_with("Front") else is_zero_approx(steer.rotation.y), "Front-only visual steering: " + name)
	var second: Node3D = scene.instantiate()
	root.add_child(second)
	second.set_physics_process(false)
	await process_frame
	check(presentation._red != second.get_node("Presentation")._red, "Patrol lightbar materials are isolated between cars")
	check(presentation._red != presentation._blue, "Red and blue lenses flash independently")
	print("CRUISER_BOUNDS: ", bounds)
	unit.queue_free()
	second.queue_free()
	await process_frame
	await process_frame
	if failures.is_empty():
		print("LOWCAR_CRUISER_PASS: imported geometry, materials, wheel rig, instance-safe lights")
		quit(0)
	else:
		for failure: String in failures:
			printerr("LOWCAR_CRUISER_FAIL: " + failure)
		quit(1)
func check(condition: bool, description: String) -> void:
	if not condition:
		failures.append(description)
