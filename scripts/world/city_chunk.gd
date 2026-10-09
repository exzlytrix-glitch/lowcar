class_name CityChunk
extends Node3D
## Deterministic streets populated with the finished Lowcar building kit.

const CHUNK_SIZE: float = 64.0

var grid_coordinate: Vector2i
var city_seed: int


func build(coordinate: Vector2i, seed_value: int) -> void:
	grid_coordinate = coordinate
	city_seed = seed_value
	position = Vector3(coordinate.x * CHUNK_SIZE, 0.0, coordinate.y * CHUNK_SIZE)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash("%d:%d:%d" % [city_seed, coordinate.x, coordinate.y])
	var road := BlockoutFactory.box(self, "Road", Vector3(64.0, 0.2, 64.0), Vector3(0.0, -0.1, 0.0), Color("#67717A"), true)
	for visual: MeshInstance3D in road.find_children("*", "MeshInstance3D", true, false):
		visual.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for x_sign: int in [-1, 1]:
		for z_sign: int in [-1, 1]:
			var center := Vector3(x_sign * 21.0, 0.13, z_sign * 21.0)
			BlockoutFactory.box(self, "Sidewalk", Vector3(22.0, 0.26, 22.0), center, Color("#CFCEC3"))
			var occupied := _build_building(rng, x_sign, z_sign)
			var tree_at := Vector3(x_sign * 12.3, 0.26, z_sign * 12.3)
			if not occupied.intersects(AABB(tree_at - Vector3(1.7, 0, 1.7), Vector3(3.4, 5.0, 3.4))):
				BlockoutFactory.tree(self, tree_at, Color("#709568"))
	_build_markings()


func _build_building(rng: RandomNumberGenerator, x_sign: int, z_sign: int) -> AABB:
	var entry := CityBuildingKit.choose(grid_coordinate, x_sign, z_sign, city_seed)
	var along_z := rng.randi_range(0, 1) == 0
	var angle: float = (PI if z_sign > 0 else 0.0) if along_z else (-PI * 0.5 if x_sign > 0 else PI * 0.5)
	var bounds: AABB = Transform3D(Basis(Vector3.UP, angle), Vector3.ZERO) * (entry.bounds as AABB)
	var at := Vector3(x_sign * 21.0 + rng.randf_range(-1.0, 1.0), 0.26, z_sign * 21.0 + rng.randf_range(-1.0, 1.0))
	if along_z:
		at.z = 11.75 - bounds.position.z if z_sign > 0 else -11.75 - bounds.end.z
	else:
		at.x = 11.75 - bounds.position.x if x_sign > 0 else -11.75 - bounds.end.x
	var plot_min := Vector3(10.75 if x_sign > 0 else -31.25, 0, 10.75 if z_sign > 0 else -31.25)
	var plot_max := Vector3(31.25 if x_sign > 0 else -10.75, 0, 31.25 if z_sign > 0 else -10.75)
	at.x = clampf(at.x, plot_min.x - bounds.position.x, plot_max.x - bounds.end.x)
	at.z = clampf(at.z, plot_min.z - bounds.position.z, plot_max.z - bounds.end.z)
	var building := CityBuildingKit.instantiate(entry)
	building.name = "Building_%s_%d_%d" % [entry.id, x_sign, z_sign]
	building.position = at
	building.rotation.y = angle
	building.set_meta("plot_signs", Vector2i(x_sign, z_sign))
	add_child(building)
	return AABB(bounds.position + at, bounds.size)


func _build_markings() -> void:
	var paint := Color("#F7F1E6")
	for at: float in [-28.0, -20.0, 20.0, 28.0]:
		BlockoutFactory.box(self, "LaneMark", Vector3(0.16, 0.015, 3.5), Vector3(0.0, 0.018, at), paint)
		BlockoutFactory.box(self, "LaneMark", Vector3(3.5, 0.015, 0.16), Vector3(at, 0.018, 0.0), paint)
	for offset: float in [-6.0, -3.0, 0.0, 3.0, 6.0]:
		for side: int in [-1, 1]:
			BlockoutFactory.box(self, "Crosswalk", Vector3(1.5, 0.015, 2.7), Vector3(offset, 0.02, side * 8.4), paint)
			BlockoutFactory.box(self, "Crosswalk", Vector3(2.7, 0.015, 1.5), Vector3(side * 8.4, 0.02, offset), paint)
