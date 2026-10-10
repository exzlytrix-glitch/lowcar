class_name Hideout
extends Node3D
## The hideout garage (Codex's Redline garage model) standing in the endless city beside a street near
## the start of the world: finding a lot for it before the city there is built, keeping that lot free of
## buildings, the car on the spinning display, and the way out of the door onto the street.
## Garage frame: front (the vehicle door) toward -Z, floor at y = 0, 15 × 12.8 m.

const GARAGE_PATH: String = "res://scenes/garages/redline_hideout_garage.tscn"
const HALF_WIDTH: float = 7.5
const HALF_DEPTH: float = 6.45
const FRONT_Z: float = -6.1
## Metres of lot between the sidewalk and the garage front.
const SETBACK: float = 1.5
## Turntable angle that points the display car at the door (the car sits at -20° on the stand).
const DOOR_ANGLE: float = deg_to_rad(20.0)

var garage: Node3D
## Where the garage stands and which way its door faces (toward the street).
var center := Vector2.ZERO
var facing := Vector2.UP
## The street in front of the door: a point on its centreline and its direction.
var street_point := Vector2.ZERO
var street_dir := Vector2.RIGHT
var street_width: float = 13.0


## Looks along the streets near the origin for a lot where the garage fits with its door to the street.
## Uses the planned (not yet built) cells, so it must run before the city there is built.
static func find_spot(streamer: WorldStreamer, settings: CityGenSettings) -> Dictionary:
	var grounds: Array[PackedVector2Array] = []
	var streets: Array = []
	for cell: Vector2i in [Vector2i(0, 0), Vector2i(-1, 0), Vector2i(0, -1), Vector2i(-1, -1)]:
		var plan: Dictionary = streamer.plan_cell(cell)
		for block: CityBlocks.Block in plan["blocks"]:
			if not block.park:
				grounds.append_array(block.ground)
		var graph: RoadGraph = plan["graph"]
		for id: int in graph.alive_edges():
			var a: Vector2 = graph.positions[graph.edge_a[id]]
			var b: Vector2 = graph.positions[graph.edge_b[id]]
			if a.distance_to(b) >= 26.0 and graph.edge_kind[id] != RoadGraph.Kind.LANE:
				streets.append([a, b, graph.edge_width[id]])
	streets.sort_custom(func(x: Array, y: Array) -> bool:
		return ((x[0] + x[1]) * 0.5).length() < ((y[0] + y[1]) * 0.5).length())
	for street: Array in streets:
		var a: Vector2 = street[0]
		var b: Vector2 = street[1]
		var width: float = street[2]
		var dir: Vector2 = (b - a).normalized()
		var middle: Vector2 = (a + b) * 0.5
		for side: float in [1.0, -1.0]:
			var inward: Vector2 = dir.orthogonal() * side
			var front: float = width * 0.5 + settings.sidewalk_width + SETBACK
			var spot_center: Vector2 = middle + inward * (front + HALF_DEPTH)
			var outline: PackedVector2Array = rectangle(spot_center, -inward, HALF_WIDTH + 1.0, HALF_DEPTH + 1.0)
			for ground: PackedVector2Array in grounds:
				if Geometry2D.clip_polygons(outline, ground).is_empty():
					return {"center": spot_center, "facing": -inward, "street_point": middle, "street_dir": dir,
						"street_width": width}
	return {}


## Corners of a rectangle centred at `at` whose front (half_depth away) faces `front_dir`.
static func rectangle(at: Vector2, front_dir: Vector2, half_width: float, half_depth: float) -> PackedVector2Array:
	var side: Vector2 = front_dir.orthogonal()
	return PackedVector2Array([at + front_dir * half_depth + side * half_width, at + front_dir * half_depth - side * half_width,
		at - front_dir * half_depth - side * half_width, at - front_dir * half_depth + side * half_width])


## The lot kept free of buildings: the garage, a margin around it, and the drive out to the sidewalk.
static func clear_area(spot: Dictionary) -> PackedVector2Array:
	var front_dir: Vector2 = spot["facing"]
	var at: Vector2 = spot["center"] + front_dir * 1.5
	return rectangle(at, front_dir, HALF_WIDTH + 2.5, HALF_DEPTH + 3.5)


func setup(spot: Dictionary, settings: CityGenSettings) -> void:
	center = spot["center"]
	facing = spot["facing"]
	street_point = spot["street_point"]
	street_dir = spot["street_dir"]
	street_width = spot["street_width"]
	var back := Vector3(-facing.x, 0.0, -facing.y)
	transform = Transform3D(Basis(Vector3.UP.cross(back), Vector3.UP, back), Vector3(center.x, settings.curb_height + 0.02, center.y))
	if ResourceLoader.exists(GARAGE_PATH):
		garage = (load(GARAGE_PATH) as PackedScene).instantiate() as Node3D
	else:
		garage = _stand_in_garage()
	garage.name = "Garage"
	add_child(garage)
	show_inside(true)


## Roof and front wall hidden (looking in from above, for the menu) or the closed building.
func show_inside(enabled: bool) -> void:
	if garage.has_method("set_cutaway"):
		garage.set_cutaway(enabled)


func spin_display(enabled: bool) -> void:
	if "rotating" in garage:
		garage.rotating = enabled


## Turns the display to point the car at the door over `seconds` (forward, the way it spins).
func turn_to_door(seconds: float) -> void:
	spin_display(false)
	var turntable := _turntable()
	if turntable == null:
		return
	var target: float = DOOR_ANGLE
	while target < turntable.rotation.y + 0.6:
		target += TAU
	create_tween().tween_property(turntable, "rotation:y", target, seconds).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


## Swaps the display model for the real car, on the stand and facing the door.
func put_car_on_stand(car: LabVehicle) -> void:
	var display: Node3D = garage.get("display_car") if "display_car" in garage else null
	if is_instance_valid(display):
		display.visible = false
	var stand: Vector3 = to_global(Vector3(0.0, 0.25, -1.0))
	car.reset_vehicle(stand)
	car.rotation.y = atan2(-facing.x, -facing.y)
	car.reset_physics_interpolation()


## Back to the menu look: the display model on the spinning stand.
func reset_display() -> void:
	var display: Node3D = garage.get("display_car") if "display_car" in garage else null
	if is_instance_valid(display):
		display.visible = true
	spin_display(true)
	show_inside(true)


## A point in the garage's frame (metres; -Z toward the street) in the world, on the ground plane.
func local_point(x: float, z: float) -> Vector2:
	var at: Vector3 = to_global(Vector3(x, 0.0, z))
	return Vector2(at.x, at.z)


## The route out for the breakout: through the door, across the sidewalk, onto the street and away
## along `away` (+1 or -1 along the street). [point, speed] pairs for ScriptedDriver.
func route_out(away: float) -> Array:
	var along: Vector2 = street_dir * away
	var lane: Vector2 = street_point - facing * (street_width * 0.2)
	return [[local_point(0.0, FRONT_Z + 1.0), 7.0], [local_point(0.0, FRONT_Z - 3.0), 8.0],
		[lane + along * 5.0, 10.0], [lane + along * 22.0, 14.0], [lane + along * 60.0, 18.0], [lane + along * 120.0, 20.0]]


## The diorama view for the menu: from above the street, looking into the open garage.
func menu_camera(camera: Camera3D) -> void:
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 16.5
	camera.h_offset = 3.6
	camera.near = 0.5
	camera.far = 400.0
	camera.global_position = to_global(Vector3(13.0, 14.0, -19.0))
	camera.look_at(to_global(Vector3(0.0, 1.0, 0.2)), Vector3.UP)


func _turntable() -> Node3D:
	if "turntable" in garage:
		return garage.get("turntable") as Node3D
	return null


## Plain box garage when Codex's model is missing (a checkout without it).
func _stand_in_garage() -> Node3D:
	var root := Node3D.new()
	var body := StaticBody3D.new()
	root.add_child(body)
	for part: Array in [[Vector3(0, 2.25, 6.1), Vector3(14.4, 4.5, 0.3)], [Vector3(-7.1, 2.25, 0), Vector3(0.3, 4.5, 12.2)],
			[Vector3(7.1, 2.25, 0), Vector3(0.3, 4.5, 12.2)], [Vector3(-5.4, 2.25, -6.1), Vector3(3.4, 4.5, 0.3)],
			[Vector3(5.4, 2.25, -6.1), Vector3(3.4, 4.5, 0.3)]]:
		var shape := BoxShape3D.new()
		shape.size = part[1]
		var holder := CollisionShape3D.new()
		holder.shape = shape
		holder.position = part[0]
		body.add_child(holder)
		var mesh := MeshInstance3D.new()
		var box := BoxMesh.new()
		box.size = part[1]
		mesh.mesh = box
		mesh.position = part[0]
		root.add_child(mesh)
	return root
