class_name WorldGen
extends RoadGenerator
## The infinite city. Space is split into cells by a backbone of main roads that exists everywhere:
## junctions on a jittered lattice (CELL apart) joined by curving links, each link randomly an
## arterial or a smaller avenue. Every link has fixed "gates" where side streets may join it. Each cell
## between the main roads gets its streets grown from its own gates with the usual district street
## styles (RoadGenerator), so cells can be generated one at a time, in any order, and still meet their
## neighbours exactly. Everything depends only on the world seed and the cell, never on what was built
## before. Districts come from a large-scale cellular noise, so a style spans several cells.
##
## cell_roads(i, j) builds one cell; window(ci, cj, radius) stitches cells into one RoadGraph (the map
## preview); WorldStreamer builds cells around the player as it drives and drops the far ones.

const CELL: float = 480.0
const JITTER: float = 0.3
const LINK_SEGMENT: float = 38.0
const LINK_WOBBLE: float = 0.07
const ARTERIAL_SHARE: float = 0.4
const GATE_MIN: float = 58.0
const GATE_MAX: float = 125.0
const GATE_END_CLEAR: float = 32.0
## Chance a cell starts a street from a gate on its side (each side of a gate decides on its own).
const GATE_USE: float = 0.72
const DISTRICT_SIZE: float = 1500.0

var world_seed: int = 1
## Added to every position before reading the district noise: a piece moved to the origin for training
## (training_city) keeps the districts of where its cells really are.
var offset := Vector2.ZERO
var _districts := FastNoiseLite.new()
var _angles := FastNoiseLite.new()
var _wobble := FastNoiseLite.new()
var _cell_polygon := PackedVector2Array()


func setup(config: CityGenSettings) -> void:
	settings = config
	world_seed = config.city_seed
	_min_angle = deg_to_rad(config.min_junction_angle)
	for noise: FastNoiseLite in [_districts, _angles]:
		noise.noise_type = FastNoiseLite.TYPE_CELLULAR
		noise.cellular_return_type = FastNoiseLite.RETURN_CELL_VALUE
		noise.frequency = 1.0 / DISTRICT_SIZE
		noise.cellular_jitter = 0.9
		noise.fractal_type = FastNoiseLite.FRACTAL_NONE  # one layer: big districts, not speckles
	_districts.seed = world_seed + 11
	_angles.seed = world_seed + 11  # same cells as the districts, read as a grid angle
	_wobble.seed = world_seed + 23
	_wobble.frequency = 1.0 / 260.0
	_build_styles()


# --- what is where ------------------------------------------------------------

func style_at(at: Vector2) -> int:
	at += offset
	var value: float = (_districts.get_noise_2d(at.x, at.y) + 1.0) * 0.5
	var weights := PackedFloat32Array([settings.old_town_weight, settings.grid_weight, settings.residential_weight,
		settings.industrial_weight])
	var total: float = 0.0
	for weight: float in weights:
		total += weight
	var roll: float = fposmod(value * 7919.0, 1.0) * total
	for index: int in weights.size():
		roll -= weights[index]
		if roll <= 0.0:
			return index
	return weights.size() - 1


func district_index(at: Vector2) -> int:
	at += offset
	return int(fposmod((_districts.get_noise_2d(at.x, at.y) + 1.0) * 104729.0, 100000.0))


func grid_angle(at: Vector2) -> float:
	at += offset
	return fposmod((_angles.get_noise_2d(at.x, at.y) + 1.0) * 3571.0, 1.0) * PI * 0.5


func cell_of(at: Vector2) -> Vector2i:
	return Vector2i(int(floor(at.x / CELL)), int(floor(at.y / CELL)))


## A main-road junction: the lattice point (i, j), nudged randomly.
func corner(i: int, j: int) -> Vector2:
	var r := _random(i, j, 1)
	return Vector2((i + r.randf_range(-JITTER, JITTER)) * CELL, (j + r.randf_range(-JITTER, JITTER)) * CELL)


## The main road from corner (i, j) to (i + 1, j) (horizontal) or (i, j + 1): its points, which of them
## are gates, and its kind and width. Identical whichever cell asks for it.
func link(i: int, j: int, horizontal: bool) -> Dictionary:
	var a: Vector2 = corner(i, j)
	var b: Vector2 = corner(i + 1, j) if horizontal else corner(i, j + 1)
	var r := _random(i, j, 2 if horizontal else 3)
	var arterial: bool = r.randf() < ARTERIAL_SHARE
	var length: float = a.distance_to(b)
	var side := (b - a).normalized().orthogonal()
	var steps: int = maxi(2, int(ceil(length / LINK_SEGMENT)))
	var amplitude: float = length * LINK_WOBBLE * r.randf_range(0.4, 1.0)
	var bend: float = r.randf_range(-1.0, 1.0)
	var base := (a + b) * 0.5
	var line := PackedVector2Array()
	for k: int in steps + 1:
		var t: float = float(k) / steps
		var along: Vector2 = a.lerp(b, t)
		var swing: float = sin(PI * t) * (bend * 0.6 + _wobble.get_noise_2d(base.x + t * 97.0, base.y - t * 61.0))
		line.append(along + side * swing * amplitude)
	# Gates: points along the road where side streets may join, kept clear of both ends.
	var cumulative := PackedFloat32Array([0.0])
	for k: int in range(1, line.size()):
		cumulative.append(cumulative[k - 1] + line[k - 1].distance_to(line[k]))
	var total: float = cumulative[cumulative.size() - 1]
	var gates := PackedFloat32Array()
	var at: float = GATE_END_CLEAR + r.randf_range(0.0, GATE_MIN * 0.6)
	while at < total - GATE_END_CLEAR:
		gates.append(at)
		at += r.randf_range(GATE_MIN, GATE_MAX)
	# Merge gate points into the polyline.
	var points := PackedVector2Array([line[0]])
	var is_gate := PackedByteArray([0])
	var g: int = 0
	for k: int in range(1, line.size()):
		while g < gates.size() and gates[g] < cumulative[k] - 4.0:
			if gates[g] > cumulative[k - 1] + 4.0:
				var f: float = (gates[g] - cumulative[k - 1]) / maxf(cumulative[k] - cumulative[k - 1], 0.01)
				points.append(line[k - 1].lerp(line[k], f))
				is_gate.append(1)
			g += 1
		points.append(line[k])
		is_gate.append(0)
	return {"points": points, "gate": is_gate, "kind": RoadGraph.Kind.ARTERIAL if arterial else RoadGraph.Kind.STREET,
		"width": settings.arterial_width if arterial else settings.street_width * 1.1,
		"key": "%s%d:%d" % ["h" if horizontal else "v", i, j]}


# --- one cell -------------------------------------------------------------------

## Streets of cell (i, j): its four main roads (locked) and the streets grown inside from their gates.
## Returns {"graph", "keys" (per node: shared key for main-road points, "" inside), "polygon",
## "owned" (per edge: 1 for the cell's own streets and its bottom and left main roads, which it paints;
## its top and right main roads belong to the neighbours above and to the right)}.
func cell_roads(i: int, j: int) -> Dictionary:
	graph = RoadGraph.new()
	locked = {}
	_queue = []
	_deferred = []
	_segments = 0
	rng = _random(i, j, 4)
	var keys: Array[String] = []
	var sides: Array = [[link(i, j, true), false], [link(i + 1, j, false), false],
		[link(i, j + 1, true), true], [link(i, j, false), true]]
	# Walk the boundary counter-clockwise: bottom, right, top (reversed), left (reversed).
	_cell_polygon = PackedVector2Array()
	var by_key: Dictionary = {}
	var gate_nodes: Array = []
	var owned_main: Dictionary = {}
	for side_index: int in sides.size():
		var side: Array = sides[side_index]
		var road: Dictionary = side[0]
		var points: PackedVector2Array = road["points"]
		var gate: PackedByteArray = road["gate"]
		var order: Array = range(points.size())
		if side[1]:
			order.reverse()
		var previous: int = -1
		for k: int in order:
			var key: String = "%s:%d" % [road["key"], k]
			if k == 0:
				key = _corner_key(road["key"], true)
			elif k == points.size() - 1:
				key = _corner_key(road["key"], false)
			var node: int
			if by_key.has(key):
				node = by_key[key]
			else:
				node = graph.add_node(points[k])
				by_key[key] = node
				keys.append(key)
				_cell_polygon.append(points[k])
				if gate[k] == 1:
					gate_nodes.append([node, road["key"], k])
			if previous >= 0 and previous != node:
				var edge: int = graph.add_edge(previous, node, road["kind"], road["width"], style_at(points[k]))
				locked[edge] = true
				if side_index == 0 or side_index == 3:
					owned_main[edge] = true
			previous = node
	# Streets from the gates, pointing into the cell.
	var middle: Vector2 = CityBlocks.centroid(_cell_polygon)
	for entry: Array in gate_nodes:
		var node: int = entry[0]
		var gate_random := _random_key("%s:%d:%d:%d" % [entry[1], entry[2], i, j])
		if gate_random.randf() > GATE_USE:
			continue
		var at: Vector2 = graph.positions[node]
		var edges: Array = graph.node_edges[node]
		var along: Vector2 = (graph.positions[graph.other(edges[0], node)] - graph.positions[graph.other(edges[1], node)]).normalized()
		var inward: Vector2 = along.orthogonal()
		if inward.dot(middle - at) < 0.0:
			inward = -inward
		var style: int = style_at(at + inward * 20.0)
		var dir: float = inward.angle() + gate_random.randf_range(-0.12, 0.12)
		if styles[style].gridded:
			var snapped: float = _snap_to_grid(dir, grid_angle(at))
			if absf(angle_difference(snapped, inward.angle())) < 0.45:
				dir = snapped
		_queue.append(_street(node, dir, style))
	_run_queue()
	_queue = _deferred
	_deferred = []
	_run_queue()
	_tidy()
	while keys.size() < graph.node_count():
		keys.append("")
	var owned := PackedByteArray()
	owned.resize(graph.edge_count())
	for id: int in graph.edge_count():
		owned[id] = 0 if locked.has(id) and not owned_main.has(id) else 1
	return {"graph": graph, "keys": keys, "polygon": _cell_polygon.duplicate(), "owned": owned}


func _corner_key(link_key: String, start: bool) -> String:
	var horizontal: bool = link_key.begins_with("h")
	var parts: PackedStringArray = link_key.substr(1).split(":")
	var i: int = int(parts[0])
	var j: int = int(parts[1])
	if not start:
		if horizontal:
			i += 1
		else:
			j += 1
	return "c%d:%d" % [i, j]


func _outside(point: Vector2) -> bool:
	return not Geometry2D.is_point_in_polygon(point, _cell_polygon)


func _steer_street(next: Proposal, dir: float, style: int, at: Vector2) -> float:
	var street_style: StreetStyle = styles[style]
	if street_style.gridded:
		var target: float = _snap_to_grid(dir, grid_angle(at))
		return dir + clampf(angle_difference(dir, target), -0.35, 0.35) + rng.randf_range(-street_style.curve, street_style.curve)
	return super._steer_street(next, dir, style, at)


func _branch_dir(base: float, side: int, style: int, at: Vector2) -> float:
	var street_style: StreetStyle = styles[style]
	if not street_style.gridded:
		return super._branch_dir(base, side, style, at)
	var dir: float = base + float(side) * PI * 0.5
	var snapped: float = _snap_to_grid(dir, grid_angle(at))
	var clear: float = _min_angle + 0.05
	if absf(angle_difference(snapped, base)) > clear and absf(angle_difference(snapped, base + PI)) > clear:
		dir = snapped
	return dir


# --- stitching cells together ---------------------------------------------------------

## The cells within `radius` of cell (ci, cj) stitched into one road graph (main-road points shared by
## neighbours become the same junction). Sets `boundary` to the window's outline for the city builder.
func window(ci: int, cj: int, radius: int) -> RoadGraph:
	return cells_window(Rect2i(ci - radius, cj - radius, radius * 2 + 1, radius * 2 + 1))


## The cells in `area` (cell coordinates) stitched into one road graph, as window().
func cells_window(area: Rect2i) -> RoadGraph:
	var merged := RoadGraph.new()
	var shared: Dictionary = {}
	var seen_edges: Dictionary = {}
	for j: int in range(area.position.y, area.end.y):
		for i: int in range(area.position.x, area.end.x):
			var cell: Dictionary = cell_roads(i, j)
			var local: RoadGraph = cell["graph"]
			var keys: Array[String] = cell["keys"]
			var map := PackedInt32Array()
			map.resize(local.node_count())
			for node: int in local.node_count():
				var key: String = keys[node]
				if key != "" and shared.has(key):
					map[node] = shared[key]
				else:
					map[node] = merged.add_node(local.positions[node])
					if key != "":
						shared[key] = map[node]
			for id: int in local.alive_edges():
				var a: int = map[local.edge_a[id]]
				var b: int = map[local.edge_b[id]]
				var pair := Vector2i(mini(a, b), maxi(a, b))
				if seen_edges.has(pair):
					continue
				seen_edges[pair] = true
				merged.add_edge(a, b, local.edge_kind[id], local.edge_width[id], local.edge_style[id])
	graph = merged
	var low := Vector2(area.position) * CELL
	var high := Vector2(area.end) * CELL
	boundary = PackedVector2Array([low, Vector2(high.x, low.y), high, Vector2(low.x, high.y)])
	return merged


## A piece of the infinite city for training (the chase arena, the GPU world export): `cells` × `cells`
## cells from a random place, moved so the piece is centred on the origin like a round city. 2 × 2 cells
## (960 m) is about the size of the round training cities.
func training_city(cells: int, rng: RandomNumberGenerator) -> RoadGraph:
	var start := Vector2i(rng.randi_range(-20, 20), rng.randi_range(-20, 20))
	var piece: RoadGraph = cells_window(Rect2i(start, Vector2i(cells, cells)))
	var shift: Vector2 = (Vector2(start) + Vector2.ONE * cells * 0.5) * CELL
	var moved := RoadGraph.new()
	for node: int in piece.node_count():
		moved.add_node(piece.positions[node] - shift)
	for id: int in piece.alive_edges():
		moved.add_edge(piece.edge_a[id], piece.edge_b[id], piece.edge_kind[id], piece.edge_width[id], piece.edge_style[id])
	graph = moved
	offset = shift
	var half: float = cells * 0.5 * CELL
	boundary = PackedVector2Array([Vector2(-half, -half), Vector2(half, -half), Vector2(half, half), Vector2(-half, half)])
	return moved


## How far from the centre a training piece's roads can reach: its outer main roads are jittered and bend.
static func training_extent(cells: int) -> float:
	return cells * 0.5 * CELL + JITTER * CELL + 60.0


# --- randomness that only depends on the place ------------------------------------------

func _random(i: int, j: int, salt: int) -> RandomNumberGenerator:
	var r := RandomNumberGenerator.new()
	r.seed = hash([world_seed, i, j, salt])
	return r


func _random_key(key: String) -> RandomNumberGenerator:
	var r := RandomNumberGenerator.new()
	r.seed = hash([world_seed, key])
	return r
