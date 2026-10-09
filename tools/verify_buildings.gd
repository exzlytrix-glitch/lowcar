extends SceneTree
## Checks imported geometry, units, materials, and the actual service-bay openings.
const ASSET_DIR := "res://assets/models/buildings/style_trial/"
var failures := 0
var checks := 0

func _initialize() -> void:
	call_deferred("verify")

func check(condition: bool, description: String) -> void:
	checks += 1
	if condition:
		print("PASS ", description)
	else:
		failures += 1
		push_error("FAIL " + description)

func verify() -> void:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ASSET_DIR + "manifest.json"))
	check(manifest.models.size() == 3, "three distinct building models")
	check(manifest.units == "meters" and manifest.godot_front == "+Z", "shared meter scale and street direction")
	var hashes: Array[String] = []
	for entry: Dictionary in manifest.models:
		var id: String = entry.id
		var glb_path := ASSET_DIR + id + ".glb"
		var hash := FileAccess.get_sha256(glb_path)
		check(hash == entry.sha256, id + " export hash matches manifest")
		check(not hashes.has(hash), id + " is distinct geometry")
		hashes.append(hash)
		check(FileAccess.file_exists(ASSET_DIR + entry.source), id + " editable Blender source exists")
		var resource := load("res://scenes/buildings/" + id + ".tscn") as PackedScene
		check(resource != null, id + " reusable Godot scene loads")
		if resource == null:
			continue
		var instance := resource.instantiate() as Node3D
		root.add_child(instance)
		var meshes := instance.find_children("*", "MeshInstance3D", true, false)
		check(meshes.size() == 1, id + " static pieces merge into one runtime mesh")
		var bounds := AABB()
		var first := true
		var triangles := 0
		var material_count := 0
		var faces := PackedVector3Array()
		for node: MeshInstance3D in meshes:
			var mesh_bounds: AABB = node.global_transform * node.mesh.get_aabb()
			bounds = mesh_bounds if first else bounds.merge(mesh_bounds)
			first = false
			for surface in range(node.mesh.get_surface_count()):
				var arrays := node.mesh.surface_get_arrays(surface)
				var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
				triangles += indices.size() / 3
				var material := node.mesh.surface_get_material(surface) as StandardMaterial3D
				check(material != null and material.transparency == BaseMaterial3D.TRANSPARENCY_DISABLED and material.albedo_texture == null,
					id + " surface " + str(surface) + " opaque, texture-free material")
				material_count += 1
			for vertex: Vector3 in node.mesh.get_faces():
				faces.append(node.global_transform * vertex)
		check(triangles == int(entry.triangles), id + " imported triangle count matches export")
		check(triangles < 12000, id + " stays below 12k triangles")
		check(material_count == entry.materials.size(), id + " material slots survive import")
		var source_min: Array = entry.blender_bounds_m.min
		var source_max: Array = entry.blender_bounds_m.max
		var expected_min := Vector3(source_min[0], source_min[2], -source_max[1])
		var expected_max := Vector3(source_max[0], source_max[2], -source_min[1])
		check(bounds.position.distance_to(expected_min) < 0.003 and bounds.end.distance_to(expected_max) < 0.003,
			id + " import keeps authored bounds and axis conversion")
		check(absf(bounds.position.y) < 0.001, id + " rests at ground zero")
		if id == "redline_garage":
			check(not bay_obstructed(faces, -4.6), "garage bay 01 has an actual open entrance")
			check(not bay_obstructed(faces, 0.0), "garage bay 02 has an actual open entrance")
			check(bay_obstructed(faces, 4.6), "garage bay 03 has a physical closed shutter")
		print("BUILDING_GEOMETRY ", id, " ", triangles, " triangles / ", material_count, " surfaces / ", bounds.size)
		instance.free()
	print("BUILDING_CHECKS ", checks, " checks; ", failures, " failures")
	quit(0 if failures == 0 else 1)

func bay_obstructed(faces: PackedVector3Array, x: float) -> bool:
	var start := Vector3(x, 1.5, 7.0)
	var end := Vector3(x, 1.5, 0.0)
	for i in range(0, faces.size(), 3):
		if Geometry3D.segment_intersects_triangle(start, end, faces[i], faces[i+1], faces[i+2]) != null:
			return true
	return false
