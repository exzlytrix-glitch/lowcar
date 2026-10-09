extends Node3D
## One street section repeated three times beside the approved car and buildings.
var camera: Camera3D
func _ready() -> void:
	var environment := WorldEnvironment.new()
	environment.environment = Environment.new()
	environment.environment.background_mode = Environment.BG_COLOR
	environment.environment.background_color = Color("b9dce8")
	environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.environment.ambient_light_color = Color("e3f0ff")
	environment.environment.ambient_light_energy = .4
	environment.environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-47, -38, 0)
	sun.light_color = Color("fff0d7")
	sun.light_energy = .75
	sun.shadow_enabled = true
	add_child(sun)
	var ground := MeshInstance3D.new()
	var floor_mesh := BoxMesh.new()
	floor_mesh.size = Vector3(60,.2,80)
	ground.mesh = floor_mesh
	ground.position.y = -.33
	var material := StandardMaterial3D.new()
	material.albedo_color = Color("d9e3ca")
	material.roughness = .95
	ground.material_override = material
	add_child(ground)
	var tile := load("res://scenes/streets/road_straight.tscn") as PackedScene
	for at: float in [-20, 0, 20]:
		var road := tile.instantiate() as Node3D
		road.position.z = at
		add_child(road)
	var market := (load("res://assets/models/buildings/style_trial/corner_market.glb") as PackedScene).instantiate() as Node3D
	market.rotation.y = PI / 2
	market.position = Vector3(-11.5,.18,-10)
	add_child(market)
	var apartments := (load("res://assets/models/buildings/style_trial/terrace_apartments.glb") as PackedScene).instantiate() as Node3D
	apartments.rotation.y = -PI / 2
	apartments.position = Vector3(12,.18,-15)
	add_child(apartments)
	var garage := (load("res://assets/models/buildings/style_trial/redline_garage.glb") as PackedScene).instantiate() as Node3D
	garage.rotation.y = PI / 2
	garage.position = Vector3(-12,.18,10)
	add_child(garage)
	var car := (load("res://scenes/vehicles/red_muscle_car.tscn") as PackedScene).instantiate() as Node3D
	car.position = Vector3(2.0,0,3)
	add_child(car)
	camera = Camera3D.new()
	camera.fov = 48
	camera.position = Vector3(21,18,27)
	camera.look_at_from_position(camera.position,Vector3(0,0,-1))
	camera.current = true
	add_child(camera)
