class_name CarMotionAccents
extends Node3D
## A bounded, texture-free effects rig: smooth car-local airflow and held world-space impacts.

@export var effect_rate_hz: float = 12.0
@export var wind_start_speed_mps: float = 8.0
@export var wind_full_speed_mps: float = 32.0
const BURST_POOL_SIZE: int = 6
const MAX_DUST_PUFFS: int = 18
const MAX_WIND_STREAKS: int = 12
var wind_strength: float = 0.0
var wind_streak_count: int = 0
var effect_sample_count: int = 0
var _wind_mesh := ImmediateMesh.new()
var _wind_visual: MeshInstance3D
var _bursts: Array[Dictionary] = []
var _stroke_material: StandardMaterial3D
var _dust_material: StandardMaterial3D
var _clock: float = 0.0
var _wind_time: float = 0.0
var _speed: float = 0.0
var _steering: float = 0.0
var _grounded: bool = true
var _next_slot: int = 0
var _serial: int = 0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	set_as_top_level(true)
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	_stroke_material = _material()
	_dust_material = _material()
	_dust_material.cull_mode = BaseMaterial3D.CULL_BACK
	var dust_mesh: ArrayMesh = _make_dust_mesh()
	_wind_visual = MeshInstance3D.new()
	_wind_visual.name = "Airflow"
	_wind_visual.mesh = _wind_mesh
	_wind_visual.material_override = _stroke_material
	_wind_visual.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_wind_visual)
	_wind_visual.set_as_top_level(true)
	for index: int in range(BURST_POOL_SIZE):
		var anchor := Node3D.new()
		anchor.name = "Impact_%d" % index
		add_child(anchor)
		anchor.set_as_top_level(true)
		var strokes := MeshInstance3D.new()
		var geometry := ImmediateMesh.new()
		strokes.mesh = geometry
		strokes.material_override = _stroke_material
		strokes.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		anchor.add_child(strokes)
		var cloud := MultiMeshInstance3D.new()
		var instances := MultiMesh.new()
		instances.transform_format = MultiMesh.TRANSFORM_3D
		instances.use_colors = true
		instances.mesh = dust_mesh
		instances.instance_count = MAX_DUST_PUFFS
		instances.visible_instance_count = 0
		instances.custom_aabb = AABB(Vector3(-7,-1,-8),Vector3(14,5,16))
		cloud.multimesh = instances
		cloud.material_override = _dust_material
		cloud.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		anchor.add_child(cloud)
		_bursts.append({"anchor":anchor,"mesh":geometry,"dust":instances,
			"age":10.0,"duration":0.7,"strength":1.0,"landing":true,"variant":0.0})
	clear()


func _material() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.vertex_color_use_as_albedo = true
	material.albedo_color = Color.WHITE
	return material


func tick(delta: float, at: Transform3D, speed: float, steering: float, grounded: bool, active: bool) -> void:
	# Air follows the interpolated car each render frame. Its drawing changes only on a pose tick.
	_wind_visual.global_transform = at
	_speed = speed
	_steering = steering
	_grounded = grounded
	var target: float = smoothstep(wind_start_speed_mps,wind_full_speed_mps,absf(speed)) if active else 0.0
	wind_strength = move_toward(wind_strength,target,maxf(delta,0.0)*2.4)
	_clock += maxf(delta,0.0)
	var quantum: float = 1.0 / maxf(effect_rate_hz,1.0)
	var steps: int = int(floor((_clock + 0.000001)/quantum))
	if steps > 0:
		_clock -= steps * quantum
		sample(steps * quantum)
		effect_sample_count += steps


func burst(at: Transform3D, landing: bool, strength: float) -> void:
	var entry: Dictionary = _bursts[_next_slot]
	_next_slot = (_next_slot + 1) % BURST_POOL_SIZE
	_serial += 1
	# Ground impacts use the actual physics position, rather than a trailing interpolated pose.
	(entry.anchor as Node3D).global_transform = at.orthonormalized()
	entry.age = 0.0
	entry.landing = landing
	entry.strength = clampf(strength,0.2,1.2)
	entry.duration = lerpf(0.48,0.78,entry.strength/1.2) if landing else 0.34
	entry.variant = _rng.randf_range(-0.12,0.12)
	_draw_burst(entry)


func sample(delta: float) -> void:
	_wind_time += delta
	_draw_wind()
	for entry: Dictionary in _bursts:
		if entry.age <= entry.duration:
			entry.age += delta
			_draw_burst(entry)


func clear(seed_value: int = 1) -> void:
	_rng.seed = seed_value ^ 0x4c4f5743
	_serial = 0
	_next_slot = 0
	_clock = 0.0
	_wind_time = 0.0
	wind_strength = 0.0
	wind_streak_count = 0
	effect_sample_count = 0
	_wind_mesh.clear_surfaces()
	for entry: Dictionary in _bursts:
		entry.age = 10.0
		(entry.mesh as ImmediateMesh).clear_surfaces()
		(entry.dust as MultiMesh).visible_instance_count = 0


func _draw_wind() -> void:
	_wind_mesh.clear_surfaces()
	wind_streak_count = 0
	if wind_strength < 0.018:
		return
	wind_streak_count = clampi(2 + int(wind_strength * 10.0),2,MAX_WIND_STREAKS)
	_wind_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	var direction: float = -1.0 if _speed < -0.5 else 1.0
	var camera: Camera3D = get_viewport().get_camera_3d()
	var viewer := Vector3(6,4,7)
	if camera != null:
		viewer = _wind_visual.global_basis.inverse() * (camera.global_position-_wind_visual.global_position)
	for index: int in range(wind_streak_count):
		var side: float = -1.0 if index % 2 == 0 else 1.0
		var lane: int = index / 2
		var phase: float = fposmod(_wind_time * (1.8 + wind_strength*1.1) + index*0.381,1.0)
		var x: float = side * (1.36 + (lane % 3)*0.20)
		var y: float = 0.42 + (lane % 3)*0.48
		var z: float = direction * lerpf(-2.7,4.8,phase)
		var length: float = lerpf(0.55,1.95,wind_strength) * (0.8 + (index % 3)*0.13)
		var a := Vector3(x,y,z)
		var b: Vector3 = a + Vector3(-_steering*0.20,0.035,direction*length)
		var fade: float = sin(phase*PI)
		var opacity: float = wind_strength * fade * (0.52 if _grounded else 0.36)
		var color := Color(0.93,0.98,1.0,opacity)
		var width_direction: Vector3 = (b-a).cross(viewer-a).normalized()
		if width_direction.length_squared() < 0.5:
			width_direction = Vector3.RIGHT
		_swish(_wind_mesh,a,b,width_direction*lerpf(0.025,0.060,wind_strength),color,side*0.05)
	_wind_mesh.surface_end()


func _draw_burst(entry: Dictionary) -> void:
	var geometry: ImmediateMesh = entry.mesh
	var dust: MultiMesh = entry.dust
	geometry.clear_surfaces()
	dust.visible_instance_count = 0
	if entry.age > entry.duration:
		return
	var progress: float = clampf(entry.age/entry.duration,0.0,1.0)
	var strength: float = entry.strength
	var fade: float = pow(1.0-progress,1.5)
	geometry.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	if entry.landing:
		# An elliptical, deliberately broken ring leaves the center and the car silhouette clear.
		var expansion: float = (0.16 + sqrt(progress)*1.9)*strength
		for segment: int in range(8):
			var angle: float = segment*TAU/8.0 + entry.variant
			for step: int in range(3):
				var a: float = angle + step*0.085
				var b: float = a + 0.085
				var start := Vector3(cos(a)*(1.23+expansion),0.045,sin(a)*(2.15+expansion))
				var end := Vector3(cos(b)*(1.23+expansion),0.045,sin(b)*(2.15+expansion))
				var radial := Vector3(cos(a),0,sin(a)) * (0.035+0.055*strength)*(1.0-progress*0.65)
				_ribbon(geometry,start,end,radial,Color(0.98,0.90,0.72,fade*0.65))
		# The initial flicks are short, fast, and much briefer than the cloud.
		if progress < 0.55:
			for index: int in range(12):
				var angle: float = index*TAU/12.0 + entry.variant + 0.1
				var direction := Vector3(cos(angle),0,sin(angle))
				var start: Vector3 = direction*Vector3(1.30+expansion,0.0,2.12+expansion)
				start.y = 0.065 + progress*0.16
				var end: Vector3 = start + direction*(0.25+progress*1.6)*strength
				_swish(geometry,start,end,Vector3(-direction.z,0.10,direction.x)*0.055,Color(1.0,0.96,0.82,fade*0.9),0.0)
		var groups: int = 3 + int(strength*2.5)
		dust.visible_instance_count = groups*3
		for group: int in range(groups):
			var angle: float = group*TAU/groups + entry.variant + 0.22
			var radial := Vector3(cos(angle),0,sin(angle))
			var center: Vector3 = radial*Vector3(1.20+expansion,0.0,2.05+expansion)
			center.y = 0.17 + progress*0.22*strength
			var grow: float = (0.15 + sin(progress*PI*0.9)*0.38)*strength
			for lobe: int in range(3):
				var radius: float = grow*(1.0 if lobe == 1 else 0.74)
				var at: Vector3 = center + Vector3(radial.z,0,-radial.x)*(lobe-1)*grow*0.8
				at.y += radius*0.3 + (0.07 if lobe == 1 else 0.0)
				var shape := Vector3(radius*1.25,radius*0.85,radius)
				var basis := Basis(Vector3.UP,angle+lobe*0.35).scaled(shape)
				dust.set_instance_transform(group*3+lobe,Transform3D(basis,at))
				dust.set_instance_color(group*3+lobe,Color(0.96,0.89,0.74,fade*0.82))
	else:
		for side: float in [-1.0,1.0]:
			var start := Vector3(side*1.33,0.05+progress*0.3,0.25)
			_swish(geometry,start,start+Vector3(side*0.10,0.8*(1.0-progress),0.12),Vector3(0.045,0,0),Color(1.0,0.96,0.83,fade),side*0.06)
	geometry.surface_end()


func _ribbon(mesh: ImmediateMesh, start: Vector3, end: Vector3, width: Vector3, color: Color) -> void:
	mesh.surface_set_color(color)
	for point: Vector3 in [start-width,start+width,end+width,start-width,end+width,end-width]:
		mesh.surface_add_vertex(point)


func _swish(mesh: ImmediateMesh, start: Vector3, end: Vector3, width: Vector3, color: Color, bend: float) -> void:
	var middle: Vector3 = start.lerp(end,0.5) + Vector3(bend,0.03,0)
	mesh.surface_set_color(color)
	for point: Vector3 in [start,middle-width,middle+width,middle-width,end,middle+width]:
		mesh.surface_add_vertex(point)


static func _make_dust_mesh() -> ArrayMesh:
	# A subdivided octahedron gives rounded cloud lobes with broad, softly shaded facets.
	var points: Array[Vector3] = [Vector3.UP,Vector3.DOWN,Vector3.RIGHT,Vector3.LEFT,Vector3.FORWARD,Vector3.BACK]
	var faces: Array = [[0,2,4],[0,4,3],[0,3,5],[0,5,2],[1,4,2],[1,3,4],[1,5,3],[1,2,5]]
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	for index: int in range(faces.size()):
		var a: Vector3 = points[faces[index][0]]
		var b: Vector3 = points[faces[index][1]]
		var c: Vector3 = points[faces[index][2]]
		var ab: Vector3 = (a+b).normalized()
		var bc: Vector3 = (b+c).normalized()
		var ca: Vector3 = (c+a).normalized()
		for triangle: Array in [[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]:
			var normal: Vector3 = (triangle[1]-triangle[0]).cross(triangle[2]-triangle[0]).normalized()
			var tint: float = 0.9 + absf(normal.y)*0.1
			for point: Vector3 in triangle:
				vertices.append(point)
				normals.append(normal)
				colors.append(Color(tint,tint,tint,1.0))
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	var result := ArrayMesh.new()
	result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	return result


func snapshot() -> Dictionary:
	var active: int = 0
	var dust_count: int = 0
	var ages: Array[float] = []
	var origins: Array[Vector3] = []
	for entry: Dictionary in _bursts:
		if entry.age <= entry.duration:
			active += 1
			dust_count += (entry.dust as MultiMesh).visible_instance_count
			ages.append(entry.age)
			origins.append((entry.anchor as Node3D).global_position)
	return {"wind_strength":wind_strength,"wind_streaks":wind_streak_count,"wind_time":_wind_time,
		"wind_transform":_wind_visual.global_transform,"active_bursts":active,"dust_puffs":dust_count,
		"burst_ages":ages,"burst_origins":origins,"pool_nodes":get_child_count(),"samples":effect_sample_count}
