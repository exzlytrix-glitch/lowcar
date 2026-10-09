extends Node3D
## One still model view, using the same gentle daylight as the street furniture.
@export var model_scene: PackedScene = preload("res://scenes/characters/pastel_pedestrian.tscn")
func _ready() -> void:
	var world := WorldEnvironment.new()
	world.environment = Environment.new()
	world.environment.background_mode = Environment.BG_COLOR
	world.environment.background_color = Color("b9dce8")
	world.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	world.environment.ambient_light_color = Color("e3f0ff")
	world.environment.ambient_light_energy = .22
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-47,-38,0)
	sun.light_color = Color("fff0d7")
	sun.light_energy = .35
	sun.shadow_enabled = true
	add_child(sun)
	var floor := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(200,.1,200)
	floor.mesh = box
	floor.position.y = -.05
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color("c8dbe1")
	mat.roughness = .95
	floor.material_override = mat
	add_child(floor)
	var person := model_scene.instantiate()
	add_child(person)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 3.45
	camera.position = Vector3(2.6,1.8,4.5)
	camera.look_at_from_position(camera.position,Vector3(0,.83,0))
	camera.current = true
	add_child(camera)
