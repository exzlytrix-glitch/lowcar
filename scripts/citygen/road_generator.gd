class_name RoadGenerator
extends RefCounted
## Grows the street network in two passes: arterial spokes and cross-town avenues first,
## then district streets branching off them. Each district has its own street pattern,
## so roads change character as you cross the city instead of repeating one grid.

enum Style { OLD_TOWN, GRID, RESIDENTIAL, INDUSTRIAL }

const STYLE_NAMES: PackedStringArray = ["Old town", "Grid", "Residential", "Industrial"]
const ARTERIAL_SEGMENT: float = 34.0
const MIN_PIECE: float = 5.0
## Dead ends shorter than this are removed. Grids almost never keep them; suburbs keep cul-de-sacs.
const DEAD_END_KEEP: PackedFloat32Array = [45.0, 160.0, 45.0, 120.0]


class StreetStyle:
	var segment: float
	var block_min: float
	var block_max: float
	var curve: float
	var drift: float
	var gridded: bool
	var width: float
	var kind: int
	var through: float
	var dead_end: float
	var branch: float
	var spacing: float


class Proposal:
	var node: int
	var dir: float
	var length: float
	var kind: int
	var width: float
	var style: int
	var since_branch: float
	var next_branch: float
	var turn: float
	var arterial: bool
	var outward: bool
	var remaining: int = -1
	var trail := PackedInt32Array()


var settings: CityGenSettings
var graph := RoadGraph.new()
var rng := RandomNumberGenerator.new()
var district_sites := PackedVector2Array()
var district_styles := PackedInt32Array()
var district_angles := PackedFloat32Array()
var boundary := PackedVector2Array()
var styles: Array[StreetStyle] = []
var _warp := FastNoiseLite.new()
var _edge := FastNoiseLite.new()
var _queue: Array[Proposal] = []
var _deferred: Array[Proposal] = []
var _ring_nodes := PackedInt32Array()
var _segments: int = 0
var _min_angle: float = 0.6
## Roads that side streets may only join at existing junctions (never split): the infinite world's
## main roads between cells, so every cell meets its neighbours at the same points.
var locked: Dictionary = {}
## How far a street that runs into a locked road may bend to reach one of its junctions.
var gate_reach: float = 34.0


func generate(config: CityGenSettings) -> RoadGraph:
	settings = config
	rng.seed = config.city_seed
	_warp.seed = config.city_seed
	_warp.frequency = 0.0045
	_edge.seed = config.city_seed + 101
	_edge.frequency = 1.0
	_edge.fractal_octaves = 2
	_min_angle = deg_to_rad(config.min_junction_angle)
	_build_styles()
	_place_districts()
	_build_boundary()
	if config.ring_road:
		_build_ring()
	_grow_arterials()
	_run_queue()
	_seed_ring_streets()
	_queue = _deferred
	_deferred = []
	_run_queue()
	_tidy()
	return graph


func boundary_radius(angle: float) -> float:
	var wobble: float = _edge.get_noise_2d(cos(angle) * 1.15, sin(angle) * 1.15)
	return settings.city_radius * maxf(0.6, 1.0 + settings.edge_wobble * wobble * 1.5)


func district_index(at: Vector2) -> int:
	var warped: Vector2 = at + Vector2(_warp.get_noise_2d(at.x, at.y), _warp.get_noise_2d(at.x + 913.0, at.y - 377.0)) * 110.0
	var best: int = 0
	var best_distance: float = INF
	for index: int in district_sites.size():
		var distance: float = warped.distance_squared_to(district_sites[index])
		if distance < best_distance:
			best_distance = distance
			best = index
	return best


func style_at(at: Vector2) -> int:
	return district_styles[district_index(at)]


# --- setup ---------------------------------------------------------------

func _build_styles() -> void:
	styles.clear()
	var s := settings
	var bend: float = s.curviness
	styles.append(_style(15.0, 40.0, 66.0, 13.0 * bend, 0.0, false, s.lane_width, RoadGraph.Kind.LANE,
		s.through_chance * 0.55, s.dead_end_chance * 1.4, 1.0, 0.72))
	styles.append(_style(26.0, 74.0, 98.0, 1.5 * bend, 0.0, true, s.street_width, RoadGraph.Kind.STREET,
		minf(1.0, s.through_chance * 1.5), s.dead_end_chance * 0.3, 1.0, 1.0))
	styles.append(_style(20.0, 90.0, 135.0, 9.0 * bend, 2.6 * bend, false, s.street_width * 0.9, RoadGraph.Kind.STREET,
		s.through_chance * 0.7, s.dead_end_chance * 2.5, 0.85, 1.1))
	styles.append(_style(30.0, 120.0, 170.0, 2.0 * bend, 0.0, true, s.street_width * 1.15, RoadGraph.Kind.STREET,
		s.through_chance, s.dead_end_chance * 0.6, 0.8, 1.4))


func _style(segment: float, block_min: float, block_max: float, curve_degrees: float, drift_degrees: float,
		gridded: bool, width: float, kind: int, through: float, dead_end: float, branch: float, spacing: float) -> StreetStyle:
	var style := StreetStyle.new()
	style.segment = segment
	style.block_min = block_min * settings.block_scale
	style.block_max = block_max * settings.block_scale
	style.curve = deg_to_rad(curve_degrees)
	style.drift = deg_to_rad(drift_degrees)
	style.gridded = gridded
	style.width = width
	style.kind = kind
	style.through = through
	style.dead_end = dead_end
	style.branch = branch
	style.spacing = settings.min_road_spacing * spacing
	return style


func _place_districts() -> void:
	district_sites.clear()
	district_styles.clear()
	district_angles.clear()
	var weights := PackedFloat32Array([settings.old_town_weight, settings.grid_weight,
		settings.residential_weight, settings.industrial_weight])
	var radius: float = settings.city_radius
	for index: int in settings.district_count:
		var site: Vector2 = Vector2.from_angle(rng.randf() * TAU) * radius * 0.12 * rng.randf()
		if index > 0:
			# Best-candidate sampling spreads districts without a visible pattern.
			var best_score: float = -1.0
			for attempt: int in 14:
				var candidate: Vector2 = Vector2.from_angle(rng.randf() * TAU) * radius * 0.95 * sqrt(rng.randf())
				var score: float = INF
				for other: Vector2 in district_sites:
					score = minf(score, candidate.distance_to(other))
				if score > best_score:
					best_score = score
					site = candidate
		district_sites.append(site)
		var style: int = Style.GRID if index == 0 and settings.grid_weight > 0.0 else _weighted(weights)
		district_styles.append(style)
		district_angles.append(rng.randf() * PI * 0.5)


func _weighted(weights: PackedFloat32Array) -> int:
	var total: float = 0.0
	for weight: float in weights:
		total += weight
	if total <= 0.0:
		return Style.GRID
	var roll: float = rng.randf() * total
	for index: int in weights.size():
		roll -= weights[index]
		if roll <= 0.0:
			return index
	return weights.size() - 1


func _build_boundary() -> void:
	boundary.clear()
	var steps: int = maxi(32, int(TAU * settings.city_radius / 36.0))
	for index: int in steps:
		var angle: float = TAU * float(index) / float(steps)
		boundary.append(Vector2.from_angle(angle) * boundary_radius(angle))


func _build_ring() -> void:
	_ring_nodes.clear()
	for point: Vector2 in boundary:
		_ring_nodes.append(graph.add_node(point))
	for index: int in _ring_nodes.size():
		var a: int = _ring_nodes[index]
		var b: int = _ring_nodes[(index + 1) % _ring_nodes.size()]
		graph.add_edge(a, b, RoadGraph.Kind.RING, settings.arterial_width, style_at(graph.positions[a]))


func _grow_arterials() -> void:
	var hub: int = graph.add_node(Vector2(rng.randf_range(-1.0, 1.0), rng.randf_range(-1.0, 1.0)) * settings.city_radius * 0.07)
	var offset: float = rng.randf() * TAU
	for index: int in settings.arterial_count:
		var spoke := _arterial(hub, offset + TAU * float(index) / float(settings.arterial_count) + rng.randf_range(-0.22, 0.22))
		spoke.outward = true
		_queue.append(spoke)
	# Cross-town avenues cut chords through the city, so not every big road leads to the centre.
	for index: int in maxi(1, int(settings.arterial_count / 2.0)):
		var angle: float = rng.randf() * TAU
		var edge_point: Vector2 = Vector2.from_angle(angle) * boundary_radius(angle)
		var start: int = _nearest_ring_node(edge_point) if settings.ring_road else graph.add_node(edge_point * 0.97)
		var target: Vector2 = Vector2.from_angle(angle + PI + rng.randf_range(-0.8, 0.8)) * settings.city_radius * 0.85
		_queue.append(_arterial(start, (target - graph.positions[start]).angle()))


func _seed_ring_streets() -> void:
	if _ring_nodes.is_empty():
		return
	var since: float = 0.0
	var next_at: float = rng.randf_range(30.0, 80.0)
	for index: int in _ring_nodes.size():
		var node: int = _ring_nodes[index]
		var at: Vector2 = graph.positions[node]
		since += at.distance_to(graph.positions[_ring_nodes[index - 1]])
		if since < next_at:
			continue
		var style: int = style_at(at * 0.96)
		var street_style: StreetStyle = styles[style]
		var inward: float = (-at).angle()
		var dir: float = inward + rng.randf_range(-0.25, 0.25)
		if street_style.gridded:
			var snapped: float = _snap_to_grid(inward, district_angles[district_index(at)])
			if absf(angle_difference(snapped, inward)) < 0.6:
				dir = snapped
		_deferred.append(_street(node, dir, style))
		since = 0.0
		next_at = rng.randf_range(street_style.block_min, street_style.block_max)


func _nearest_ring_node(at: Vector2) -> int:
	var best: int = _ring_nodes[0]
	for node: int in _ring_nodes:
		if graph.positions[node].distance_squared_to(at) < graph.positions[best].distance_squared_to(at):
			best = node
	return best


func _arterial(node: int, dir: float) -> Proposal:
	var proposal := Proposal.new()
	proposal.node = node
	proposal.dir = dir
	proposal.length = ARTERIAL_SEGMENT
	proposal.kind = RoadGraph.Kind.ARTERIAL
	proposal.width = settings.arterial_width
	proposal.style = -1
	proposal.since_branch = 0.0
	proposal.next_branch = rng.randf_range(30.0, 60.0)
	proposal.arterial = true
	proposal.trail = PackedInt32Array([node])
	return proposal


func _street(node: int, dir: float, style: int) -> Proposal:
	var street_style: StreetStyle = styles[style]
	var proposal := Proposal.new()
	proposal.node = node
	proposal.dir = dir
	proposal.length = street_style.segment
	proposal.kind = street_style.kind
	proposal.width = street_style.width
	proposal.style = style
	proposal.since_branch = 0.0
	proposal.next_branch = rng.randf_range(street_style.block_min, street_style.block_max)
	proposal.trail = PackedInt32Array([node])
	# Some streets are planned as dead ends: they run a few segments and stop.
	if rng.randf() < street_style.dead_end:
		proposal.remaining = rng.randi_range(3, 8)
	return proposal


# --- growth --------------------------------------------------------------

func _run_queue() -> void:
	var index: int = 0
	while index < _queue.size() and _segments < settings.max_segments:
		_try(_queue[index])
		index += 1
	_queue.clear()


func _try(p: Proposal) -> void:
	var a: Vector2 = graph.positions[p.node]
	if not _angle_free(p.node, p.dir):
		return
	var forward: Vector2 = Vector2.from_angle(p.dir)
	var length: float = p.length
	# Look a little past the end so near misses become proper T-junctions.
	var hit: Dictionary = graph.first_crossing(a, a + forward * (length + settings.snap_radius * 0.75), p.node)
	if not hit.is_empty():
		_join_crossing(p, a, hit, true)
		return
	var last: bool = false
	var b: Vector2 = a + forward * length
	if _outside(b):
		if settings.ring_road:
			return
		length = _distance_to_city_edge(a, forward, length)
		if length < 8.0:
			return
		last = true
		b = a + forward * length
	var near: int = graph.nearest_node(b, settings.snap_radius, p.node)
	if near >= 0 and _join_node(p, a, near, not _locked_node(near)):
		return
	if _crowded(p, a, b):
		return
	var node: int = graph.add_node(b)
	graph.add_edge(p.node, node, p.kind, p.width, _edge_style(p, b))
	_segments += 1
	if not last:
		_follow(p, node, b, length)


func _join_crossing(p: Proposal, a: Vector2, hit: Dictionary, allow_through: bool) -> bool:
	var edge: int = hit["edge"]
	var point: Vector2 = hit["point"]
	if locked.has(edge):
		return _join_locked(p, a, edge, point)
	var ea: int = graph.edge_a[edge]
	var eb: int = graph.edge_b[edge]
	var crossed_kind: int = graph.edge_kind[edge]
	var snap: float = settings.snap_radius * 0.6
	var end: int = -1
	if point.distance_to(graph.positions[ea]) < snap:
		end = ea
	elif point.distance_to(graph.positions[eb]) < snap:
		end = eb
	if end >= 0:
		var target: Vector2 = graph.positions[end]
		if end == p.node or graph.connected(p.node, end):
			return false
		var dir_in: float = (target - a).angle()
		if absf(angle_difference(dir_in, p.dir)) > 0.6 or a.distance_to(target) < MIN_PIECE:
			return false
		if graph.crosses(a, target, p.node, end):
			return false
		if not _angle_free(p.node, dir_in) or not _angle_free(end, dir_in + PI):
			return false
	else:
		var road: float = (graph.positions[eb] - graph.positions[ea]).angle()
		var crossing: float = absf(angle_difference(p.dir, road))
		crossing = minf(crossing, PI - crossing)
		if crossing < _min_angle or a.distance_to(point) < MIN_PIECE:
			return false
		end = graph.split_edge(edge, point)
	var travelled: float = a.distance_to(graph.positions[end])
	graph.add_edge(p.node, end, p.kind, p.width, _edge_style(p, graph.positions[end]))
	_segments += 1
	if allow_through and crossed_kind != RoadGraph.Kind.RING:
		var through: float = 1.0 if p.arterial else styles[style_at(graph.positions[end])].through
		if rng.randf() < through:
			_pass_through(p, end, travelled)
	return true


## A street ran into a locked road: meet it at the nearest of its junctions if that is close and
## reachable, otherwise stop here (the street becomes a dead end, tidied up later).
func _join_locked(p: Proposal, a: Vector2, edge: int, point: Vector2) -> bool:
	var best: int = -1
	var best_distance: float = gate_reach
	for end: int in [graph.edge_a[edge], graph.edge_b[edge]]:
		var distance: float = graph.positions[end].distance_to(point)
		if distance < best_distance:
			best_distance = distance
			best = end
	if best < 0:
		return false
	return _join_node(p, a, best, false)


func _join_node(p: Proposal, a: Vector2, near: int, allow_through: bool) -> bool:
	if near == p.node or graph.connected(p.node, near):
		return false
	var target: Vector2 = graph.positions[near]
	var dir_in: float = (target - a).angle()
	if absf(angle_difference(dir_in, p.dir)) > 0.7 or a.distance_to(target) < MIN_PIECE:
		return false
	if graph.crosses(a, target, p.node, near):
		return false
	if not _angle_free(p.node, dir_in) or not _angle_free(near, dir_in + PI):
		return false
	var mid_road: bool = graph.degree(near) == 2
	graph.add_edge(p.node, near, p.kind, p.width, _edge_style(p, target))
	_segments += 1
	if allow_through and (p.arterial or (mid_road and rng.randf() < styles[style_at(target)].through)):
		_pass_through(p, near, a.distance_to(target))
	return true


func _pass_through(p: Proposal, node: int, travelled: float) -> void:
	var at: Vector2 = graph.positions[node]
	var next := Proposal.new()
	next.node = node
	next.dir = p.dir
	next.arterial = p.arterial
	next.outward = p.outward
	next.turn = p.turn
	next.since_branch = p.since_branch + travelled
	next.next_branch = p.next_branch
	if p.arterial:
		next.kind = p.kind
		next.width = p.width
		next.style = -1
		next.length = ARTERIAL_SEGMENT
	else:
		var style: int = style_at(at)
		next.kind = styles[style].kind
		next.width = styles[style].width
		next.style = style
		next.length = styles[style].segment
	next.trail = PackedInt32Array([p.node, node])
	_queue.append(next)


func _follow(p: Proposal, node: int, at: Vector2, length: float) -> void:
	var style: int = style_at(at)
	var street_style: StreetStyle = styles[style]
	var since: float = p.since_branch + length
	var next_branch: float = p.next_branch
	if since >= next_branch:
		# Gridded districts and arterials make crossroads; organic streets stagger their side streets.
		var sides: Array[int] = [-1, 1]
		if not street_style.gridded and not p.arterial:
			sides = [-1 if rng.randf() < 0.5 else 1]
		for side: int in sides:
			if rng.randf() < settings.branch_chance * street_style.branch:
				var branch := _street(node, _branch_dir(p.dir, side, style, at), style)
				if p.arterial:
					_deferred.append(branch)
				else:
					_queue.append(branch)
		since = 0.0
		next_branch = rng.randf_range(street_style.block_min, street_style.block_max)
		if sides.size() == 1:
			next_branch *= 0.55
	if p.remaining == 0:
		return
	var next := Proposal.new()
	next.node = node
	next.remaining = p.remaining - 1 if p.remaining > 0 else -1
	next.arterial = p.arterial
	next.outward = p.outward
	next.turn = p.turn
	next.since_branch = since
	next.next_branch = next_branch
	if p.arterial:
		next.kind = p.kind
		next.width = p.width
		next.style = -1
		next.length = ARTERIAL_SEGMENT * rng.randf_range(0.85, 1.15)
		next.dir = _steer_arterial(next, p.dir, at)
	else:
		next.kind = street_style.kind
		next.width = street_style.width
		next.style = style
		next.length = street_style.segment * rng.randf_range(0.85, 1.15)
		next.dir = _steer_street(next, p.dir, style, at)
	next.trail = p.trail.duplicate()
	next.trail.append(node)
	while next.trail.size() > 4:
		next.trail.remove_at(0)
	_queue.append(next)


func _steer_arterial(next: Proposal, dir: float, at: Vector2) -> float:
	var limit: float = 0.06 * settings.curviness + 0.001
	next.turn = clampf(next.turn + rng.randf_range(-0.03, 0.03) * settings.curviness, -limit, limit)
	var steered: float = dir + next.turn
	if next.outward:
		# Spokes drift but keep heading away from the centre instead of curling back.
		steered += clampf(angle_difference(steered, at.angle()), -0.05, 0.05)
	return steered


func _steer_street(next: Proposal, dir: float, style: int, at: Vector2) -> float:
	var street_style: StreetStyle = styles[style]
	if street_style.gridded:
		# Bend toward this district's grid; crossing into a new district visibly turns the street.
		var target: float = _snap_to_grid(dir, district_angles[district_index(at)])
		return dir + clampf(angle_difference(dir, target), -0.35, 0.35) + rng.randf_range(-street_style.curve, street_style.curve)
	if street_style.drift > 0.0:
		next.turn = clampf(next.turn + rng.randf_range(-street_style.drift, street_style.drift), -street_style.curve, street_style.curve)
		return dir + next.turn
	return dir + rng.randf_range(-street_style.curve, street_style.curve)


func _branch_dir(base: float, side: int, style: int, at: Vector2) -> float:
	var street_style: StreetStyle = styles[style]
	var dir: float = base + float(side) * PI * 0.5
	if street_style.gridded:
		var snapped: float = _snap_to_grid(dir, district_angles[district_index(at)])
		var clear: float = _min_angle + 0.05
		if absf(angle_difference(snapped, base)) > clear and absf(angle_difference(snapped, base + PI)) > clear:
			dir = snapped
	else:
		dir += rng.randf_range(-1.0, 1.0) * maxf(street_style.curve, deg_to_rad(6.0))
	return dir


func _snap_to_grid(dir: float, grid_angle: float) -> float:
	return grid_angle + roundf((dir - grid_angle) / (PI * 0.5)) * PI * 0.5


func _angle_free(node: int, dir: float) -> bool:
	for id: int in graph.node_edges[node]:
		if absf(angle_difference(dir, graph.direction_from(node, id))) < _min_angle:
			return false
	return true


func _crowded(p: Proposal, a: Vector2, b: Vector2) -> bool:
	var spacing: float = settings.min_road_spacing * 1.6 if p.arterial else styles[p.style].spacing
	var middle: Vector2 = (a + b) * 0.5
	var parallel: float = deg_to_rad(28.0)
	for id: int in graph.edges_in(Rect2(b, Vector2.ZERO).grow(spacing)):
		var ea: int = graph.edge_a[id]
		var eb: int = graph.edge_b[id]
		if ea == p.node or eb == p.node or p.trail.has(ea) or p.trail.has(eb):
			continue
		var distance: float = minf(graph.distance_to_edge(b, id), graph.distance_to_edge(middle, id))
		if distance >= spacing:
			continue
		var road: float = (graph.positions[eb] - graph.positions[ea]).angle()
		var relative: float = absf(angle_difference(p.dir, road))
		relative = minf(relative, PI - relative)
		if relative < parallel or distance < spacing * 0.4:
			return true
	return false


## Whether a point lies outside the area being built (the city edge here; a cell in the infinite world).
func _outside(point: Vector2) -> bool:
	return point.length() > boundary_radius(point.angle())


func _locked_node(node: int) -> bool:
	for id: int in graph.node_edges[node]:
		if locked.has(id):
			return true
	return false


func _distance_to_city_edge(a: Vector2, forward: Vector2, length: float) -> float:
	var low: float = 0.0
	var high: float = length
	for step: int in 14:
		var middle: float = (low + high) * 0.5
		var point: Vector2 = a + forward * middle
		if not _outside(point):
			low = middle
		else:
			high = middle
	return low


func _edge_style(p: Proposal, at: Vector2) -> int:
	return p.style if p.style >= 0 else style_at(at)


# --- cleanup -------------------------------------------------------------

func _tidy() -> void:
	_resolve_dead_ends()
	_prune_stubs()
	_merge_straight_nodes()


## Streets that stopped just short of another road get connected to it.
func _resolve_dead_ends() -> void:
	for node: int in graph.node_count():
		if graph.degree(node) != 1:
			continue
		var id: int = graph.node_edges[node][0]
		var at: Vector2 = graph.positions[node]
		var dir: float = (at - graph.positions[graph.other(id, node)]).angle()
		var style: int = style_at(at)
		var reach: float = styles[style].spacing * 1.3
		var p := _street(node, dir, style)
		p.kind = graph.edge_kind[id]
		p.width = graph.edge_width[id]
		var hit: Dictionary = graph.first_crossing(at, at + Vector2.from_angle(dir) * reach, node)
		if not hit.is_empty() and _join_crossing(p, at, hit, false):
			continue
		var near: int = graph.nearest_node(at + Vector2.from_angle(dir) * reach * 0.5, reach * 0.6, node)
		if near >= 0:
			_join_node(p, at, near, false)


## Short dead-end stubs read as mistakes; long ones stay as cul-de-sacs.
func _prune_stubs() -> void:
	for node: int in graph.node_count():
		if graph.degree(node) != 1:
			continue
		var keep: float = DEAD_END_KEEP[style_at(graph.positions[node])]
		var chain := PackedInt32Array()
		var total: float = 0.0
		var current: int = node
		var previous: int = -1
		while true:
			var next_edge: int = -1
			for id: int in graph.node_edges[current]:
				if id != previous:
					next_edge = id
					break
			if next_edge < 0:
				break
			chain.append(next_edge)
			total += graph.edge_length(next_edge)
			current = graph.other(next_edge, current)
			previous = next_edge
			if graph.degree(current) != 2 or total >= keep:
				break
		if total < keep:
			for id: int in chain:
				graph.remove_edge(id)


## Collapse nearly straight in-between points so blocks stay simple.
func _merge_straight_nodes() -> void:
	for node: int in graph.node_count():
		if graph.degree(node) != 2:
			continue
		var first: int = graph.node_edges[node][0]
		var second: int = graph.node_edges[node][1]
		if locked.has(first) or locked.has(second):
			continue
		if graph.edge_kind[first] != graph.edge_kind[second] or not is_equal_approx(graph.edge_width[first], graph.edge_width[second]):
			continue
		var a: int = graph.other(first, node)
		var b: int = graph.other(second, node)
		if a == b or graph.connected(a, b):
			continue
		var bend: float = absf(angle_difference(graph.direction_from(node, first), graph.direction_from(node, second)))
		if bend < PI - deg_to_rad(4.0) or graph.edge_length(first) + graph.edge_length(second) > 140.0:
			continue
		var kind: int = graph.edge_kind[first]
		var width: float = graph.edge_width[first]
		var style: int = graph.edge_style[first]
		graph.remove_edge(first)
		graph.remove_edge(second)
		graph.add_edge(a, b, kind, width, style)
