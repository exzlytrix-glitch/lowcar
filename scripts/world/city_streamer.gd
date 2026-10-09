class_name CityStreamer
extends Node3D
## Keeps a bounded square of seeded blocks around the car.

@export var focus_path: NodePath
@export_range(1, 4) var active_radius: int = 2
@export var city_seed: int = 142857

var active_chunks: Dictionary = {}
var _focus: Node3D
var _center := Vector2i(2147483647, 2147483647)
var _pending: Array[Vector2i] = []


func _ready() -> void:
	_focus = get_node_or_null(focus_path) as Node3D
	reset(city_seed)


func _process(_delta: float) -> void:
	if is_instance_valid(_focus):
		var next_center := coordinate_for(_focus.global_position)
		if next_center != _center:
			_queue_neighborhood(next_center)
	if not _pending.is_empty():
		_add_chunk(_pending.pop_front())


func reset(seed_value: int) -> void:
	city_seed = seed_value
	for chunk: CityChunk in active_chunks.values():
		remove_child(chunk)
		chunk.queue_free()
	active_chunks.clear()
	_pending.clear()
	_center = Vector2i.ZERO
	for x: int in range(-active_radius, active_radius + 1):
		for z: int in range(-active_radius, active_radius + 1):
			_add_chunk(Vector2i(x, z))


func coordinate_for(at: Vector3) -> Vector2i:
	return Vector2i(floori((at.x + 32.0) / CityChunk.CHUNK_SIZE), floori((at.z + 32.0) / CityChunk.CHUNK_SIZE))


func _queue_neighborhood(center: Vector2i) -> void:
	_center = center
	_pending.clear()
	for coordinate: Vector2i in active_chunks.keys():
		if absi(coordinate.x - center.x) > active_radius or absi(coordinate.y - center.y) > active_radius:
			var chunk: CityChunk = active_chunks[coordinate]
			remove_child(chunk)
			chunk.queue_free()
			active_chunks.erase(coordinate)
	for x: int in range(center.x - active_radius, center.x + active_radius + 1):
		for z: int in range(center.y - active_radius, center.y + active_radius + 1):
			var coordinate := Vector2i(x, z)
			if not active_chunks.has(coordinate):
				_pending.append(coordinate)


func _add_chunk(coordinate: Vector2i) -> void:
	if active_chunks.has(coordinate):
		return
	var chunk := CityChunk.new()
	chunk.name = "Block_%d_%d" % [coordinate.x, coordinate.y]
	add_child(chunk)
	chunk.build(coordinate, city_seed)
	active_chunks[coordinate] = chunk

