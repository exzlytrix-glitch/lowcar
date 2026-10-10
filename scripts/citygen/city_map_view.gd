class_name CityMapView
extends Control
## Top-down map of the generated city. Wheel zooms, left-drag pans, right-click drops the car there.

signal teleport_requested(world: Vector2)

const BACKGROUND := Color("#B3D39F")
const ROAD := Color("#8A929B")
const SIDEWALK := Color("#F1ECE1")
const PARK := Color("#A8CF93")
const LOTS: Array[Color] = [Color("#EBD9C2"), Color("#DCE3EC"), Color("#CFE3BE"), Color("#D9D3CA")]
const BUILDINGS: Array[Color] = [Color("#D69A86"), Color("#8EA6C9"), Color("#E3B98A"), Color("#9C9890")]
const GRAPH_COLORS: Array[Color] = [Color("#46505A"), Color("#5E6873"), Color("#8A7A6E"), Color("#3A444E")]

var player: Node3D
var show_graph: bool = false
var show_player_marker: bool = true
## Extra drawing for replays: [points (world x/z), color, width] and [world point, color].
var overlay_lines: Array = []
var overlay_markers: Array = []
var _mesh: ArrayMesh
var _graph_lines := PackedVector2Array()
var _graph_line_colors := PackedColorArray()
var _center := Vector2.ZERO
var _zoom: float = 0.5
var _dragging: bool = false
var _radius: float = 700.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


func set_city(graph: RoadGraph, generator: RoadGenerator, blocks: Array[CityBlocks.Block],
		footprints: Array[PackedVector2Array], footprint_styles: PackedInt32Array, radius: float) -> void:
	_radius = radius
	var vertices := PackedVector2Array()
	var colors := PackedColorArray()
	var land := PackedVector2Array()
	for point: Vector2 in generator.boundary:
		land.append(point.normalized() * (point.length() + 10.0))
	_add_polygon(vertices, colors, land, ROAD)
	for block: CityBlocks.Block in blocks:
		_add_polygon(vertices, colors, block.curb, SIDEWALK)
		for ground: PackedVector2Array in block.ground:
			_add_polygon(vertices, colors, ground, PARK if block.park else LOTS[block.style])
	for index: int in footprints.size():
		_add_polygon(vertices, colors, footprints[index], BUILDINGS[footprint_styles[index]])
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_COLOR] = colors
	_mesh = ArrayMesh.new()
	if not vertices.is_empty():
		_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	_graph_lines.clear()
	_graph_line_colors.clear()
	for id: int in graph.alive_edges():
		_graph_lines.append(graph.positions[graph.edge_a[id]])
		_graph_lines.append(graph.positions[graph.edge_b[id]])
		_graph_line_colors.append(GRAPH_COLORS[graph.edge_kind[id]])
	fit()


func fit(center: Vector2 = Vector2.ZERO) -> void:
	var area: Vector2 = size if minf(size.x, size.y) > 0.0 else get_viewport_rect().size
	_center = center
	_zoom = minf(area.x, area.y) / (_radius * 2.5)


func center_on_player() -> void:
	if is_instance_valid(player):
		_center = Vector2(player.global_position.x, player.global_position.z)
		_zoom = maxf(_zoom, 1.2)


func screen_to_world(at: Vector2) -> Vector2:
	return (at - size * 0.5) / _zoom + _center


func _process(_delta: float) -> void:
	if visible:
		queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BACKGROUND)
	var view := Transform2D(0.0, Vector2(_zoom, _zoom), 0.0, size * 0.5 - _center * _zoom)
	if _mesh != null and _mesh.get_surface_count() > 0:
		draw_mesh(_mesh, null, view)
	if show_graph and not _graph_lines.is_empty():
		var points := PackedVector2Array()
		points.resize(_graph_lines.size())
		for index: int in _graph_lines.size():
			points[index] = view * _graph_lines[index]
		draw_multiline_colors(points, _graph_line_colors, 1.0)
	for line: Array in overlay_lines:
		var world_points: PackedVector2Array = line[0]
		if world_points.size() < 2:
			continue
		var screen := PackedVector2Array()
		for point: Vector2 in world_points:
			screen.append(view * point)
		draw_polyline(screen, line[1], line[2])
	for marker: Array in overlay_markers:
		draw_circle(view * (marker[0] as Vector2), 7.0, marker[1])
		draw_arc(view * (marker[0] as Vector2), 7.0, 0.0, TAU, 16, Color.WHITE, 2.0)
	if show_player_marker and is_instance_valid(player):
		var at: Vector2 = view * Vector2(player.global_position.x, player.global_position.z)
		var forward: Vector3 = -player.global_basis.z
		var heading := Vector2(forward.x, forward.z).normalized()
		var side := Vector2(-heading.y, heading.x)
		var marker := PackedVector2Array([at + heading * 14.0, at - heading * 8.0 + side * 8.0, at - heading * 8.0 - side * 8.0])
		draw_colored_polygon(marker, Color("#D94B3D"))
		draw_polyline(PackedVector2Array([marker[0], marker[1], marker[2], marker[0]]), Color.WHITE, 2.0)
	var font: Font = get_theme_default_font()
	draw_string(font, Vector2(16, size.y - 18), "MAP  wheel zoom · drag pan · right-click drop car · F find car · L road lines · M close",
		HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color("#24394B"))


func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if button.button_index == MOUSE_BUTTON_WHEEL_UP or button.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			if button.pressed:
				var anchor: Vector2 = screen_to_world(button.position)
				_zoom = clampf(_zoom * (1.15 if button.button_index == MOUSE_BUTTON_WHEEL_UP else 1.0 / 1.15), 0.05, 12.0)
				_center = anchor - (button.position - size * 0.5) / _zoom
			accept_event()
		elif button.button_index == MOUSE_BUTTON_LEFT:
			_dragging = button.pressed
			accept_event()
		elif button.button_index == MOUSE_BUTTON_RIGHT and button.pressed:
			teleport_requested.emit(screen_to_world(button.position))
			accept_event()
	elif event is InputEventMouseMotion and _dragging:
		_center -= (event as InputEventMouseMotion).relative / _zoom
		accept_event()


func _add_polygon(vertices: PackedVector2Array, colors: PackedColorArray, polygon: PackedVector2Array, color: Color) -> void:
	var indices: PackedInt32Array = Geometry2D.triangulate_polygon(polygon)
	for index: int in indices:
		vertices.append(polygon[index])
		colors.append(color)
