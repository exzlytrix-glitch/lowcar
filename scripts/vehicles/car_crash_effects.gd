class_name CarCrashEffects
extends Node3D
## Held drawings, the booster's faceted fire, and a recognizable red wreck.
const CRUMPLE: Shader = preload("res://resources/animation/car_crumple.gdshader")
const PARTS: PackedScene = preload("res://assets/models/vehicles/red_muscle_car/explosion_parts.glb")
const DEATH_CLIPS: Array[String] = ["crash_front", "crash_left", "crash_right", "explode"]
var damage: Vector3 = Vector3.ZERO
var _model: Node3D
var _chassis: Node3D
var _wheels: Node3D
var _materials: Array[ShaderMaterial] = []
var _debris: Node3D
var _pieces: Array[Node3D] = []
var _rest: Dictionary = {}
var _ground_points: Dictionary = {}
var _fire_mesh := ImmediateMesh.new()
var _stroke_mesh := ImmediateMesh.new()
var _fire_visual: MeshInstance3D
var _stroke_visual: MeshInstance3D
var _dust: Array[MeshInstance3D] = []
var _active_clip: String = ""
var _sample_time: float = 0.0
var _flash: bool = false
var _flame_count: int = 0

func setup(model: Node3D, chassis: Node3D, wheels: Node3D) -> void:
	_model = model
	_chassis = chassis
	_wheels = wheels
	var lid := chassis.get_node("TrunkHinge")
	# Trim, bumper and headlights follow the same clean deformation as the body.
	for item: MeshInstance3D in chassis.find_children("*", "MeshInstance3D", true, false):
		if lid.is_ancestor_of(item):
			continue
		for surface: int in range(item.mesh.get_surface_count()):
			var original := item.get_active_material(surface) as StandardMaterial3D
			if original == null:
				continue
			var material := ShaderMaterial.new()
			material.shader = CRUMPLE
			material.set_shader_parameter("paint", original.albedo_color)
			material.set_shader_parameter("roughness_value", original.roughness)
			material.set_shader_parameter("metallic_value", original.metallic)
			material.set_shader_parameter("local_to_body", chassis.global_transform.affine_inverse() * item.global_transform)
			item.set_surface_override_material(surface, material)
			_materials.append(material)
	_debris = PARTS.instantiate() as Node3D
	add_child(_debris)
	for piece: Node3D in _debris.get_node("CarExplosionParts").get_children():
		piece.visible = String(piece.get_child(0).name) in ["FrontLeftMesh", "FrontRightMesh", "RearLeftMesh", "RearRightMesh"]
		if not piece.visible:
			continue
		_pieces.append(piece)
		_rest[piece.name] = piece.transform
		var corners: Array[Vector3] = []
		for item: MeshInstance3D in piece.find_children("*", "MeshInstance3D", true, false):
			var bounds: AABB = item.get_aabb()
			for corner: int in range(8):
				corners.append(item.transform * bounds.get_endpoint(corner))
		_ground_points[piece.name] = corners
	_fire_visual = _mesh("BoosterStyleBlast", _fire_mesh, Color.WHITE)
	_stroke_visual = _mesh("ImpactSwishes", _stroke_mesh, Color.WHITE)
	var cloud: ArrayMesh = CarMotionAccents._make_dust_mesh()
	for index: int in range(8):
		_dust.append(_mesh("LandingDust%d" % index, cloud, Color("f5dfb5")))
	clear()

func _mesh(label: String, mesh: Mesh, color: Color) -> MeshInstance3D:
	var item := MeshInstance3D.new()
	item.name = label
	item.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.vertex_color_use_as_albedo = true
	item.material_override = material
	item.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(item)
	return item

func apply(clip: String, time: float, dent: Vector3) -> void:
	if clip not in DEATH_CLIPS:
		if not _active_clip.is_empty():
			clear()
		return
	_active_clip = clip
	_sample_time = floor(time * 12.0 + 0.001) / 12.0
	damage = dent
	for material: ShaderMaterial in _materials:
		material.set_shader_parameter("damage", damage)
	_fire_mesh.clear_surfaces()
	_stroke_mesh.clear_surfaces()
	_fire_visual.visible = false
	_stroke_visual.visible = false
	_flash = false
	_flame_count = 0
	for blob: MeshInstance3D in _dust:
		blob.visible = false
	_model.visible = true
	if clip == "explode":
		_apply_explosion(_sample_time)
	else:
		_debris.visible = false
		_wheels.visible = true
		_apply_dented_wheels()
		_apply_impact(_sample_time - 2.0 / 12.0, clip)

func _apply_dented_wheels() -> void:
	for wheel: Node3D in _wheels.get_children():
		var left: bool = String(wheel.name).ends_with("Left")
		var dent: float = damage.x if left else damage.y
		wheel.position += Vector3(_chassis.position.x, 0, _chassis.position.z)
		wheel.position.x += (1.0 if left else -1.0) * dent * 0.13
		wheel.rotation.z = (1.0 if left else -1.0) * dent * 0.15
		wheel.scale.y *= 1.0 - dent * 0.07
		if String(wheel.name).begins_with("Front"):
			wheel.position.z += damage.z * 0.12
			wheel.rotation.y = (1.0 if left else -1.0) * damage.z * 0.12

func _apply_impact(t: float, clip: String) -> void:
	if t < 0 or t >= 0.67:
		return
	var contact := Vector3(0, 0.38, -2.35)
	var normal := Vector3.BACK
	if clip != "crash_front":
		var sign_value: float = 1.0 if clip == "crash_left" else -1.0
		contact = Vector3(-sign_value * 1.02, 0.38, -0.1)
		normal = Vector3(sign_value, 0, 0)
	var tangent: Vector3 = normal.cross(Vector3.UP)
	_stroke_visual.visible = t < .25
	if _stroke_visual.visible:
		_stroke_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
		for i: int in range(7):
			var dir: Vector3 = (normal * .25 + tangent * (i - 3) * .4 + Vector3.UP * (.4 + (i % 3) * .3)).normalized()
			var start: Vector3 = contact + dir * (0.10 + t * 2.5)
			_swish(start, start + dir * (.45 - t), .055 * (1.0 - t / .25), BoostExhaust.CORE)
		_stroke_mesh.surface_end()
	for i: int in range(6):
		var blob := _dust[i]
		var life: float = .45 + (i % 3) * .08
		blob.visible = t < life
		if not blob.visible:
			continue
		var side: float = -1.0 if i % 2 == 0 else 1.0
		blob.position = contact + normal * (.15 + t * .7) + tangent * side * (.12 + t * (1.2 + i * .1))
		blob.position.y = .16 + t * .25
		var radius: float = (.15 + t * .3) * (1.0 - pow(t / life, 2.0))
		blob.scale = Vector3(radius * 1.5, radius * .7, radius)

func _apply_explosion(time: float) -> void:
	var t: float = time - .5
	_debris.visible = t >= 0
	_wheels.visible = t < 0
	if t < 0:
		if time >= 4.0 / 12.0:
			_fire_visual.visible = true
			_fire_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
			_flame(Vector3(-.65, .68, -1.5), Vector3(-.3, .8, -.2), .55, .085, 0)
			_flame(Vector3(.65, .68, -1.5), Vector3(.3, .8, -.2), .45, .075, 2)
			_fire_mesh.surface_end()
		return
	var sample: int = int(round(t * 12))
	_flash = sample == 0
	if t < 1.0:
		_fire_visual.visible = true
		_fire_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
		# Same six-sided tongues, taper, flicker sequence and flat colors as the tailpipes.
		var envelope: float = [0.78, 1.0, .94, .79, .65, .53, .42, .34, .27, .20, .13, .06][mini(sample, 11)]
		for i: int in range(9):
			var angle: float = i * TAU / 9.0 + .16
			var radial := Vector3(cos(angle), 0, sin(angle))
			var dir: Vector3 = (radial * .95 + Vector3.UP * (.45 + (i % 3) * .25)).normalized()
			var origin: Vector3 = Vector3(radial.x * .9, .35 + t * .3, radial.z * 1.5)
			var flicker: float = BoostExhaust.FLICKER[posmod(sample + i * 2, BoostExhaust.FLICKER.size())]
			_flame(origin, dir, (2.9 + (i % 3) * .35) * envelope * flicker, .43 * envelope, i, _flash)
		_flame(Vector3(0, .85 + t * .45, 0), Vector3.UP, 3.8 * envelope, .57 * envelope, 1, _flash)
		_fire_mesh.surface_end()
	_stroke_visual.visible = t < .42
	if _stroke_visual.visible:
		_stroke_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
		for i: int in range(8):
			var dir := Vector3(cos(i * TAU / 8.0), .17 + (i % 3) * .13, sin(i * TAU / 8.0)).normalized()
			var start: Vector3 = Vector3(0, .6, 0) + dir * (1.15 + t * 5)
			_swish(start, start + dir * (.85 - t), .09 * (1.0 - t / .42), BoostExhaust.CORE)
		_stroke_mesh.surface_end()
	# Small cream clouds accompany the body slap, as in the approved landing animation.
	var landing_age: float = t - 5.0 / 12.0
	for i: int in range(_dust.size()):
		var blob := _dust[i]
		blob.visible = landing_age >= 0 and landing_age < .65
		if blob.visible:
			var angle: float = i * TAU / _dust.size()
			blob.position = Vector3(cos(angle) * (1.3 + landing_age * 1.5), .15 + landing_age * .24, sin(angle) * (2.2 + landing_age * 1.5))
			var radius: float = (.18 + landing_age * .25) * (1.0 - pow(landing_age / .65, 2.0))
			blob.scale = Vector3(radius * 1.5, radius * .75, radius)
	_apply_loose_wheels(t)

func _flame(origin: Vector3, direction: Vector3, length: float, width: float, phase: int, flash: bool = false) -> void:
	var dir := direction.normalized()
	var across: Vector3 = Vector3.UP.cross(dir).normalized() if absf(dir.y) < .99 else Vector3.RIGHT
	var frame := Basis(across, dir.cross(across), dir)
	var lean: float = sin(float(phase + int(_sample_time * 12)) * 2.2) * .08
	_tongue(origin, frame, length, width, lean, false, flash)
	# Lay the core onto the visible side of each tongue, like the lifted tailpipe core.
	var camera: Camera3D = get_viewport().get_camera_3d()
	var viewer: Vector3 = to_local(camera.global_position) - origin if camera != null else Vector3(6, 5, 7) - origin
	var face_viewer: Vector3 = (viewer - dir * viewer.dot(dir)).normalized()
	_tongue(origin + face_viewer * width * .66, frame, length * .65, width * .52, lean * .4, true, flash)
	_flame_count += 1

func _tongue(origin: Vector3, frame: Basis, length: float, width: float, lean: float, core: bool, flash: bool) -> void:
	for ring: int in range(3):
		var a: float = ring / 3.0
		var b: float = (ring + 1) / 3.0
		for face: int in range(6):
			var angle_a: float = face * TAU / 6.0
			var angle_b: float = (face + 1) * TAU / 6.0
			var p0: Vector3 = _flame_point(origin, frame, length, width, lean, a, angle_a)
			var p1: Vector3 = _flame_point(origin, frame, length, width, lean, a, angle_b)
			var p2: Vector3 = _flame_point(origin, frame, length, width, lean, b, angle_b)
			var p3: Vector3 = _flame_point(origin, frame, length, width, lean, b, angle_a)
			var color: Color = BoostExhaust.CORE if core or flash else BoostExhaust.OUTER.lerp(BoostExhaust.TIP, a)
			color = color.darkened(.06 if face % 2 == 0 else 0)
			_fire_mesh.surface_set_color(color)
			for vertex: Vector3 in [p0, p1, p2, p0, p2, p3]:
				_fire_mesh.surface_add_vertex(vertex)

func _flame_point(origin: Vector3, frame: Basis, length: float, width: float, lean: float, along: float, angle: float) -> Vector3:
	var radius: float = width * (1.0 - along) * (1.0 + sin(along * PI) * .55)
	return origin + frame * Vector3(cos(angle) * radius + lean * along * along, sin(angle) * radius * .7 + .035 * along, length * along)

func _swish(start: Vector3, end: Vector3, width: float, color: Color) -> void:
	var camera: Camera3D = get_viewport().get_camera_3d()
	var viewer: Vector3 = to_local(camera.global_position) if camera != null else Vector3(6, 5, 7)
	var spread: Vector3 = (end - start).cross(viewer - start).normalized() * width
	var middle: Vector3 = start.lerp(end, .5)
	_stroke_mesh.surface_set_color(color)
	for point: Vector3 in [start, middle - spread, middle + spread, middle - spread, end, middle + spread]:
		_stroke_mesh.surface_add_vertex(point)

func _apply_loose_wheels(t: float) -> void:
	for i: int in range(_pieces.size()):
		var piece := _pieces[i]
		var rest: Transform3D = _rest[piece.name]
		var dir := Vector3(signf(rest.origin.x), 0, signf(rest.origin.z) * .65).normalized()
		var vy: float = 2.5 + i * .22
		var hit: float = (vy + sqrt(vy * vy + 19.6 * maxf(0, rest.origin.y - .24))) / 9.8
		var travel: float = minf(t, hit) + maxf(0, t - hit) * .14
		var at: Vector3 = rest.origin + dir * travel * (1.5 + i * .13)
		at.y += vy * t - 4.9 * t * t
		var spin := Vector3(.5 + i * .2, i * .27, (1.0 if i % 2 == 0 else -1.0) * t * 3.4)
		var rotation: Basis = Basis.from_euler(spin) * rest.basis
		if t > hit:
			var settled := Basis.from_euler(Vector3(0, i * .63, PI * .5)) * rest.basis
			rotation = Basis(rotation.get_rotation_quaternion().slerp(settled.get_rotation_quaternion(), clampf((t - hit) / .4, 0, 1)))
		var minimum: float = 0.0
		for point: Vector3 in _ground_points[piece.name]:
			minimum = minf(minimum, (rotation * point).y)
		var support: float = -minimum + .012
		if t > hit:
			var bounce_age: float = t - hit
			at.y = support + maxf(0, bounce_age * vy * .20 - 4.9 * bounce_age * bounce_age)
		else:
			at.y = maxf(at.y, support)
		piece.transform = Transform3D(rotation, at)

func clear() -> void:
	_active_clip = ""
	_sample_time = 0.0
	damage = Vector3.ZERO
	_flash = false
	_flame_count = 0
	_fire_mesh.clear_surfaces()
	_stroke_mesh.clear_surfaces()
	if _model != null:
		_model.visible = true
	for material: ShaderMaterial in _materials:
		material.set_shader_parameter("damage", Vector3.ZERO)
	if _debris != null:
		_debris.visible = false
	for piece: Node3D in _pieces:
		piece.transform = _rest[piece.name]
	for child: Node in get_children():
		if child is MeshInstance3D:
			child.visible = false
	if _wheels != null:
		_wheels.visible = true
		for wheel: Node3D in _wheels.get_children():
			wheel.rotation = Vector3.ZERO

func snapshot() -> Dictionary:
	return {"clip": _active_clip, "time": _sample_time, "damage": damage,
		"intact_visible": _model.visible, "parts_visible": _debris.visible,
		"pieces": _pieces.size(), "flash": _flash, "flames": _flame_count,
		"smoke": 0}
