class_name CityBuildingKit
extends RefCounted
## Shared model library, authored bounds, and seeded selection for streamed blocks.

const ASSET_DIRECTORY := "res://assets/models/buildings/"
const STUDY_BODIES := {
	"corner_market": Vector3(10.8, 9.65, 9.5),
	"terrace_apartments": Vector3(9.2, 12.75, 9.0)
}
static var _catalog: Array[Dictionary] = []
static var _order: Array[Dictionary] = []
static var _order_seed := -1
static var _study_shapes: Dictionary = {}


static func catalog() -> Array[Dictionary]:
	if not _catalog.is_empty():
		return _catalog
	var directories := DirAccess.get_directories_at(ASSET_DIRECTORY)
	directories.sort()
	for folder: String in directories:
		var directory := ASSET_DIRECTORY + folder + "/"
		if not FileAccess.file_exists(directory + "manifest.json"):
			continue
		var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(directory + "manifest.json"))
		for entry: Dictionary in manifest.models:
			var low: Array = entry.blender_bounds_m.min
			var high: Array = entry.blender_bounds_m.max
			var minimum := Vector3(low[0], low[2], -high[1])
			var maximum := Vector3(high[0], high[2], -low[1])
			var path: String = entry.get("scene", "res://scenes/buildings/" + String(entry.id) + ".tscn")
			_catalog.append({"id": entry.id, "scene": load(path) as PackedScene,
				"bounds": AABB(minimum, maximum - minimum)})
	return _catalog


static func choose(coordinate: Vector2i, x_sign: int, z_sign: int, seed_value: int) -> Dictionary:
	if _order_seed != seed_value:
		_order = catalog().duplicate()
		var rng := RandomNumberGenerator.new()
		rng.seed = seed_value
		for i: int in range(_order.size() - 1, 0, -1):
			var other := rng.randi_range(0, i)
			var entry := _order[i]
			_order[i] = _order[other]
			_order[other] = entry
		_order_seed = seed_value
	# Neighboring rows advance through the shuffled kit as the city streams.
	# Revisiting a chunk keeps the same layout.
	var lot_x := coordinate.x * 2 + (1 if x_sign > 0 else 0)
	var lot_z := coordinate.y * 2 + (1 if z_sign > 0 else 0)
	return _order[posmod(lot_x + lot_z * 7, _order.size())]


static func instantiate(entry: Dictionary) -> Node3D:
	var building := (entry.scene as PackedScene).instantiate() as Node3D
	building.set_meta("building_id", entry.id)
	building.set_meta("local_bounds", entry.bounds)
	building.add_to_group("city_buildings")
	if STUDY_BODIES.has(entry.id):
		var size: Vector3 = STUDY_BODIES[entry.id]
		if not _study_shapes.has(entry.id):
			var shape := BoxShape3D.new()
			shape.size = size
			_study_shapes[entry.id] = shape
		_add_body(building, _study_shapes[entry.id], Vector3(0, size.y * 0.5, 0))
	elif entry.id == "redline_garage":
		var visual := building.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
		if not _study_shapes.has(entry.id):
			_study_shapes[entry.id] = visual.mesh.create_trimesh_shape()
		# Collide with the real static mesh; an enclosing box would seal the bays.
		_add_body(visual, _study_shapes[entry.id], Vector3.ZERO)
	return building


static func _add_body(parent: Node3D, shape: Shape3D, at: Vector3) -> void:
	var body := StaticBody3D.new()
	body.name = "BuildingBody"
	body.collision_layer = 1
	body.collision_mask = 0
	parent.add_child(body)
	var collision := CollisionShape3D.new()
	collision.position = at
	collision.shape = shape
	body.add_child(collision)
