class_name WorldStreamer
extends Node3D
## The endless city around a moving point (the player's car). Cells of the infinite layout (WorldGen)
## within load_distance are built one at a time on a worker thread (roads, blocks, then the 3D city with
## CellBuilder) and added when ready; cells beyond unload_distance are dropped. A cell is the same every
## time it loads, because everything in it depends only on the world seed and the cell.
##
## `graph` is one live road graph of every loaded cell (main-road junctions shared between cells are one
## junction) and `nav` routes over it, so cops can drive the whole loaded area. Node and road ids stay
## valid while their cell is loaded. One flat ground and floor follow the focus everywhere.

signal cells_changed

const GROUND := Color("#7B848E")
const GROUND_SIZE: float = 6000.0
## The ground and floor jump to the focus once it is this far from their centre (they are uniform, so
## the jump can't be seen).
const GROUND_RECENTER: float = 600.0
## Main-thread time per frame for adding and freeing the pieces of arriving and dropped cells: a whole
## cell at once is a visible hitch (tens of ms), a few pieces a frame are not. Cells come and go far
## away in the fog, so filling them in over a few frames can't be seen.
const FRAME_BUDGET_USEC: int = 2000

var settings: CityGenSettings
var load_distance: float = 760.0
var unload_distance: float = 1150.0
var graph := RoadGraph.new()
var nav: RoadNav
## WorldGen for questions on the main thread (style_at for the HUD, links); the worker has its own.
var world := WorldGen.new()
## Cell → {"node", "pairs", "keys", "fresh", "blocks", "footprints", "styles", "polygon"}.
var cells: Dictionary = {}
var last_build_ms: float = 0.0

static var _buildings_ready: bool = false
var _worker := WorldGen.new()
var _worker_roads: Dictionary = {}
var _task: int = -1
var _task_cell := Vector2i.ZERO
var _result: Dictionary = {}
var _key_nodes: Dictionary = {}
var _key_refs: Dictionary = {}
var _pairs: Dictionary = {}
var _ground: MeshInstance3D
var _floor: StaticBody3D
var _focus := Vector2.ZERO
var _heading := Vector2.ZERO
## [parent, child] pieces of arrived cells still to add (collision first), and nodes of dropped cells
## still to free (children before their parents).
var _adding: Array = []
var _freeing: Array[Node] = []


func setup(config: CityGenSettings) -> void:
	settings = config
	world.setup(config)
	_worker.setup(config)
	nav = RoadNav.new(graph)
	_prepare_buildings()
	# Same material and vertex colour as the city's own ground (CityBuilder), so they match exactly.
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	material.roughness = 0.92
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var half: float = GROUND_SIZE * 0.5
	for corner: Vector2 in [Vector2(-1, -1), Vector2(1, 1), Vector2(1, -1), Vector2(-1, -1), Vector2(-1, 1), Vector2(1, 1)]:
		surface.set_color(GROUND)
		surface.set_normal(Vector3.UP)
		surface.add_vertex(Vector3(corner.x * half, 0.0, corner.y * half))
	_ground = MeshInstance3D.new()
	_ground.name = "Ground"
	_ground.mesh = surface.commit()
	_ground.material_override = material
	_ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_ground)
	_floor = StaticBody3D.new()
	_floor.name = "Floor"
	_floor.collision_layer = 1
	_floor.collision_mask = 0
	var shape := BoxShape3D.new()
	shape.size = Vector3(GROUND_SIZE, 1.0, GROUND_SIZE)
	var collision := CollisionShape3D.new()
	collision.shape = shape
	collision.position.y = -0.5
	_floor.add_child(collision)
	add_child(_floor)


## Everything about the buildings that is made once and kept (the catalogs, each model's distant stand-in
## box, special collision shapes) is made here on the main thread. Making a stand-in reads the model's
## mesh back from the renderer, which only the main thread can answer: on the worker it would wait for
## the main thread, and the main thread waiting for the worker (quitting, a new world) would hang.
static func _prepare_buildings() -> void:
	if _buildings_ready:
		return
	_buildings_ready = true
	var started: int = Time.get_ticks_msec()
	var entries: Array[Dictionary] = CityBuildingKit.catalog().duplicate()
	var kit: Script = CityBuildingKit
	for info: Dictionary in kit.get_script_method_list():
		if info["name"] == "small_catalog":
			entries.append_array(kit.call("small_catalog"))
	for entry: Dictionary in entries:
		CityBuilder._stand_in_mesh(entry)
	print("WORLD prepared %d building models in %d ms" % [entries.size(), Time.get_ticks_msec() - started])


## Builds every cell near `at` right away (on this thread): the start of a run, behind a loading screen.
func load_around(at: Vector2) -> void:
	_focus = at
	_recenter_ground(true)
	for cell: Vector2i in _wanted():
		if not cells.has(cell):
			_attach(_make_cell(cell))
	_work(-1)
	cells_changed.emit()


## Call every frame with the focus (the car) and where it is heading: finishes and starts background
## builds (nearest cells first, ahead of the car before behind it) and drops one far cell.
func update(at: Vector2, heading: Vector2 = Vector2.ZERO) -> void:
	_focus = at
	_heading = heading
	_recenter_ground(false)
	if _task >= 0 and WorkerThreadPool.is_task_completed(_task):
		WorkerThreadPool.wait_for_task_completion(_task)
		_task = -1
		_attach(_result)
		_result = {}
		cells_changed.emit()
	if _task < 0:
		var next: Variant = _next_cell()
		if next != null:
			_task_cell = next
			_task = WorkerThreadPool.add_task(_run_task.bind(_task_cell), false, "World cell")
	for cell: Vector2i in cells:
		if _cell_distance(cell) > unload_distance:
			_detach(cell)
			cells_changed.emit()
			break
	_work(FRAME_BUDGET_USEC)


## Adds and frees queued cell pieces for up to `budget` microseconds (-1: all of them).
func _work(budget: int) -> void:
	var started: int = Time.get_ticks_usec()
	while not _freeing.is_empty() and (budget < 0 or Time.get_ticks_usec() - started < budget):
		var node: Node = _freeing.pop_back()
		if is_instance_valid(node):
			node.free()
	while not _adding.is_empty() and (budget < 0 or Time.get_ticks_usec() - started < budget):
		var piece: Array = _adding.pop_front()
		if is_instance_valid(piece[0]):
			(piece[0] as Node).add_child(piece[1])
		else:
			(piece[1] as Node).free()


## Waits for a running build and drops every cell (before a new world or leaving the scene).
func clear() -> void:
	if _task >= 0:
		WorkerThreadPool.wait_for_task_completion(_task)
		_task = -1
		if not _result.is_empty():
			_free_result(_result)
		_result = {}
	for cell: Vector2i in cells.keys():
		_detach(cell)
	_work(-1)
	graph = RoadGraph.new()
	nav = RoadNav.new(graph)
	_key_nodes.clear()
	_key_refs.clear()
	_pairs.clear()
	_worker_roads.clear()


func _exit_tree() -> void:
	if _task >= 0:
		WorkerThreadPool.wait_for_task_completion(_task)
		_task = -1
		if not _result.is_empty():
			_free_result(_result)
		_result = {}
	for piece: Array in _adding:
		(piece[1] as Node).free()
	_adding.clear()


## A finished build that never joined the scene: its pieces are off the tree, so free them too.
func _free_result(result: Dictionary) -> void:
	for piece: Array in result["pieces"]:
		(piece[1] as Node).free()
	(result["node"] as Node).free()


func is_loading() -> bool:
	return _task >= 0 or _next_cell() != null


func all_blocks() -> Array[CityBlocks.Block]:
	var result: Array[CityBlocks.Block] = []
	for cell: Vector2i in cells:
		result.append_array(cells[cell]["blocks"])
	return result


func all_footprints() -> Array[PackedVector2Array]:
	var result: Array[PackedVector2Array] = []
	for cell: Vector2i in cells:
		result.append_array(cells[cell]["footprints"])
	return result


func all_footprint_styles() -> PackedInt32Array:
	var result := PackedInt32Array()
	for cell: Vector2i in cells:
		result.append_array(cells[cell]["styles"])
	return result


## Outline around the loaded cells (for the map's road-coloured land).
func outline() -> PackedVector2Array:
	var points := PackedVector2Array()
	for cell: Vector2i in cells:
		points.append_array(cells[cell]["polygon"])
	return Geometry2D.convex_hull(points) if points.size() >= 3 else points


# --- which cells -------------------------------------------------------------------

func _cell_distance(cell: Vector2i) -> float:
	var low := Vector2(cell) * WorldGen.CELL
	var area := Rect2(low, Vector2.ONE * WorldGen.CELL)
	var nearest := Vector2(clampf(_focus.x, area.position.x, area.end.x), clampf(_focus.y, area.position.y, area.end.y))
	return nearest.distance_to(_focus)


func _wanted() -> Array[Vector2i]:
	var result: Array[Vector2i] = []
	var reach: int = int(ceil(load_distance / WorldGen.CELL)) + 1
	var center: Vector2i = world.cell_of(_focus)
	for j: int in range(center.y - reach, center.y + reach + 1):
		for i: int in range(center.x - reach, center.x + reach + 1):
			var cell := Vector2i(i, j)
			if _cell_distance(cell) <= load_distance:
				result.append(cell)
	return result


func _next_cell() -> Variant:
	var best: Variant = null
	var best_score: float = INF
	for cell: Vector2i in _wanted():
		if cells.has(cell) or (_task >= 0 and cell == _task_cell):
			continue
		var score: float = _cell_distance(cell)
		if _heading != Vector2.ZERO:
			var middle := (Vector2(cell) + Vector2.ONE * 0.5) * WorldGen.CELL
			score -= _heading.normalized().dot((middle - _focus).normalized()) * 250.0
		if score < best_score:
			best_score = score
			best = cell
	return best


# --- building a cell (worker thread) ------------------------------------------------------

func _run_task(cell: Vector2i) -> void:
	_result = _make_cell(cell)


## Roads, blocks and the 3D city of one cell, outside the scene tree. Uses only the worker's own
## WorldGen and cache, so it is safe on the worker thread (one build at a time).
func _make_cell(cell: Vector2i) -> Dictionary:
	var started: int = Time.get_ticks_usec()
	var roads: Dictionary = _roads(cell)
	var cell_settings := settings.duplicate() as CityGenSettings
	cell_settings.city_seed = hash([settings.city_seed, cell.x, cell.y]) & 0x7fffffff
	cell_settings.city_radius = WorldGen.CELL
	cell_settings.ring_road = false
	var road_graph: RoadGraph = roads["graph"]
	var blocks: Array[CityBlocks.Block] = CityBlocks.build(road_graph, _worker, cell_settings)
	var builder := CellBuilder.new()
	builder.name = "Cell_%d_%d" % [cell.x, cell.y]
	builder.owned = roads["owned"]
	builder.trim_extra = _trim_extra(cell, roads)
	builder.build(cell_settings, road_graph, _worker, blocks)
	# Take the pieces off the tiles so the main thread can add them a few at a time, collision first.
	var solid: Array = []
	var rest: Array = []
	for tile_root: Node in builder.get_children():
		for child: Node in tile_root.get_children():
			tile_root.remove_child(child)
			(solid if child is StaticBody3D else rest).append([tile_root, child])
	return {"cell": cell, "roads": roads, "node": builder, "pieces": solid + rest, "blocks": blocks,
		"footprints": builder.footprints, "styles": builder.footprint_styles,
		"ms": (Time.get_ticks_usec() - started) / 1000.0}


func _roads(cell: Vector2i) -> Dictionary:
	if not _worker_roads.has(cell):
		if _worker_roads.size() > 96:
			_worker_roads.clear()
		var roads: Dictionary = _worker.cell_roads(cell.x, cell.y)
		var by_key: Dictionary = {}
		var keys: Array[String] = roads["keys"]
		for node: int in keys.size():
			if keys[node] != "":
				by_key[keys[node]] = node
		roads["by_key"] = by_key
		_worker_roads[cell] = roads
	return _worker_roads[cell]


## For paint trimming: roads that neighbouring cells add at this cell's main-road junctions. Corners
## always join four main roads; a gate on a road this cell paints may also have the neighbour's street.
func _trim_extra(cell: Vector2i, roads: Dictionary) -> Dictionary:
	var road_graph: RoadGraph = roads["graph"]
	var keys: Array[String] = roads["keys"]
	var below_key: String = "h%d:%d:" % [cell.x, cell.y]
	var left_key: String = "v%d:%d:" % [cell.x, cell.y]
	var extra: Dictionary = {}
	for node: int in keys.size():
		var key: String = keys[node]
		if key == "":
			continue
		if key.begins_with("c"):
			var parts: PackedStringArray = key.substr(1).split(":")
			var i: int = int(parts[0])
			var j: int = int(parts[1])
			var widest: float = 0.0
			for road: Dictionary in [_worker.link(i, j, true), _worker.link(i - 1, j, true), _worker.link(i, j, false), _worker.link(i, j - 1, false)]:
				widest = maxf(widest, road["width"])
			extra[node] = [4 - road_graph.degree(node), widest]
			continue
		var across := Vector2i(-99999, 0)
		if key.begins_with(below_key):
			across = cell + Vector2i(0, -1)
		elif key.begins_with(left_key):
			across = cell + Vector2i(-1, 0)
		else:
			continue
		var other: Dictionary = _roads(across)
		var other_graph: RoadGraph = other["graph"]
		var other_node: int = other["by_key"].get(key, -1)
		if other_node < 0:
			continue
		var count: int = 0
		var widest: float = 0.0
		var other_keys: Array[String] = other["keys"]
		for id: int in other_graph.node_edges[other_node]:
			if other_keys[other_graph.other(id, other_node)] == "":
				count += 1
				widest = maxf(widest, other_graph.edge_width[id])
		if count > 0:
			extra[node] = [count, widest]
	return extra


# --- joining and leaving the live graph (main thread) --------------------------------------

func _attach(result: Dictionary) -> void:
	var started: int = Time.get_ticks_usec()
	var cell: Vector2i = result["cell"]
	var roads: Dictionary = result["roads"]
	var local: RoadGraph = roads["graph"]
	var keys: Array[String] = roads["keys"]
	var map := PackedInt32Array()
	map.resize(local.node_count())
	var used_keys: Array[String] = []
	var fresh := PackedInt32Array()
	for node: int in local.node_count():
		var key: String = keys[node]
		if key == "":
			if local.degree(node) > 0:
				map[node] = graph.add_node(local.positions[node])
				fresh.append(map[node])
			continue
		if not _key_nodes.has(key):
			_key_nodes[key] = graph.add_node(local.positions[node])
			_key_refs[key] = 0
		_key_refs[key] += 1
		used_keys.append(key)
		map[node] = _key_nodes[key]
	var pairs: Array[Vector2i] = []
	for id: int in local.alive_edges():
		var a: int = map[local.edge_a[id]]
		var b: int = map[local.edge_b[id]]
		var pair := Vector2i(mini(a, b), maxi(a, b))
		if _pairs.has(pair):
			_pairs[pair][1] += 1
		else:
			var live: int = graph.add_edge(a, b, local.edge_kind[id], local.edge_width[id], local.edge_style[id])
			_pairs[pair] = [live, 1]
			nav.add_edge(live)
		pairs.append(pair)
	var node: Node3D = result["node"]
	add_child(node)
	_adding.append_array(result["pieces"])
	cells[cell] = {"node": node, "pairs": pairs, "keys": used_keys, "fresh": fresh, "blocks": result["blocks"],
		"footprints": result["footprints"], "styles": result["styles"], "polygon": roads["polygon"]}
	last_build_ms = result["ms"]
	print("WORLD cell %d,%d built %.0f ms on the worker, attached %.1f ms" % [cell.x, cell.y, result["ms"],
		(Time.get_ticks_usec() - started) / 1000.0])


func _detach(cell: Vector2i) -> void:
	var started: int = Time.get_ticks_usec()
	var entry: Dictionary = cells[cell]
	cells.erase(cell)
	for pair: Vector2i in entry["pairs"]:
		var held: Array = _pairs[pair]
		held[1] -= 1
		if held[1] <= 0:
			_pairs.erase(pair)
			graph.remove_edge(held[0])
			nav.remove_edge(held[0])
	for key: String in entry["keys"]:
		_key_refs[key] -= 1
		if _key_refs[key] <= 0:
			_key_refs.erase(key)
			_key_nodes.erase(key)
	# Free the cell's pieces a few per frame: the cell node first in the list, so it goes last.
	var node: Node = entry["node"]
	_freeing.append(node)
	for tile_root: Node in node.get_children():
		_freeing.append(tile_root)
		_freeing.append_array(tile_root.get_children())
	print("WORLD cell %d,%d dropped %.1f ms" % [cell.x, cell.y, (Time.get_ticks_usec() - started) / 1000.0])


func _recenter_ground(force: bool) -> void:
	var at := Vector2(_ground.position.x, _ground.position.z)
	if force or at.distance_to(_focus) > GROUND_RECENTER:
		_ground.position = Vector3(_focus.x, 0.0, _focus.y)
		_floor.position = Vector3(_focus.x, 0.0, _focus.y)
