extends "res://scripts/review/road_review.gd"
## Reuses the approved road review; furniture sits on its existing 18 cm sidewalks.
var street_items: Array[Node3D] = []
var sidewalk_items: Array[Node3D] = []
func _ready() -> void:
	super._ready()
	# Gentle daylight keeps the pale paving and cream furniture readable.
	for child: Node in get_children():
		if child is WorldEnvironment:
			child.environment.ambient_light_energy = .22
		elif child is DirectionalLight3D:
			child.light_energy = .35
	for entry: Array in [["streetlamp",Vector3(4.80,.18,-3.0),0.0],
		["trashcan",Vector3(5.15,.18,.4),-PI/2],
		["bench",Vector3(5.15,.18,4.0),-PI/2],
		["hydrant",Vector3(4.80,.18,7.2),0.0],
		["streetlamp",Vector3(-4.80,.18,5.0),0.0]]:
		var item := (load("res://scenes/streets/street_stuff/%s.tscn" % entry[0]) as PackedScene).instantiate() as Node3D
		item.position = entry[1]
		item.rotation.y = entry[2]
		add_child(item)
		street_items.append(item)
	var kit_floor := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(21,.12,6.5)
	kit_floor.mesh = box
	kit_floor.position = Vector3(0,-.07,50)
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color("8cabb3")
	mat.roughness = .95
	kit_floor.material_override = mat
	add_child(kit_floor)
	for index: int in range(3):
		var id: String = ["sidewalk_straight","sidewalk_corner","sidewalk_ramp"][index]
		var item := (load("res://scenes/streets/street_stuff/%s.tscn" % id) as PackedScene).instantiate() as Node3D
		item.position = Vector3(-6.5 + index*6.5,0,50)
		add_child(item)
		sidewalk_items.append(item)
	show_furniture()
func show_furniture() -> void:
	camera.projection = Camera3D.PROJECTION_PERSPECTIVE
	camera.position = Vector3(.2,3.9,10.7)
	camera.fov = 49
	camera.look_at(Vector3(5,1.85,1.7))
func show_sidewalks() -> void:
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 19
	camera.position = Vector3(6,13,63)
	camera.look_at(Vector3(0,.1,50))
func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_1:
			show_sidewalks()
		elif event.physical_keycode == KEY_2:
			show_furniture()
