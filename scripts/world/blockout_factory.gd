class_name BlockoutFactory
extends RefCounted
## Shared simple street surfaces and low-poly street trees.

static var _materials: Dictionary = {}


static func material(color: Color) -> StandardMaterial3D:
	if _materials.has(color):
		return _materials[color] as StandardMaterial3D
	var result := StandardMaterial3D.new()
	result.albedo_color = color.srgb_to_linear()
	result.roughness = 0.82
	_materials[color] = result
	return result


static func box(parent: Node3D, label: String, size: Vector3, at: Vector3, color: Color, solid: bool = false) -> Node3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	var visual := MeshInstance3D.new()
	visual.mesh = mesh
	visual.material_override = material(color)
	if solid:
		var body := StaticBody3D.new()
		body.name = label
		body.position = at
		body.collision_layer = 1
		body.collision_mask = 0
		parent.add_child(body)
		var shape := BoxShape3D.new()
		shape.size = size
		var collision := CollisionShape3D.new()
		collision.shape = shape
		body.add_child(collision)
		body.add_child(visual)
		return body
	visual.name = label
	visual.position = at
	parent.add_child(visual)
	return visual


static func tree(parent: Node3D, at: Vector3, color: Color) -> void:
	var tree_root := Node3D.new()
	tree_root.name = "StreetTree"
	tree_root.position = at
	parent.add_child(tree_root)
	var trunk_mesh := CylinderMesh.new()
	trunk_mesh.top_radius = 0.18
	trunk_mesh.bottom_radius = 0.27
	trunk_mesh.height = 2.6
	trunk_mesh.radial_segments = 6
	var trunk := MeshInstance3D.new()
	trunk.mesh = trunk_mesh
	trunk.material_override = material(Color("#856952"))
	trunk.position.y = 1.3
	tree_root.add_child(trunk)
	var leaves_mesh := SphereMesh.new()
	leaves_mesh.radius = 1.6
	leaves_mesh.height = 2.7
	leaves_mesh.radial_segments = 8
	leaves_mesh.rings = 3
	var leaves := MeshInstance3D.new()
	leaves.mesh = leaves_mesh
	leaves.material_override = material(color)
	leaves.position.y = 3.1
	tree_root.add_child(leaves)
