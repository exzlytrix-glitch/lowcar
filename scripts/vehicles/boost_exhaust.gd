class_name BoostExhaust
extends Node3D
## Two texture-free, faceted flames attached to the actual tailpipes. Shapes are held at 12 FPS.

const RATE: float = 12.0
const FLICKER: Array[float] = [0.90,1.15,0.86,1.05,1.19,0.94,1.07]
const OUTER := Color("ff8d36")
const TIP := Color("ff5b2a")
const CORE := Color("fff1b7")
var sample_count: int = 0
var flame_length: float = 0.0
var flame_width: float = 0.0
var _clock: float = 0.0
var _phase: int = 0
var _mesh := ImmediateMesh.new()
var _visual: MeshInstance3D
var _grounded: bool = true


func _ready() -> void:
	name = "BoostExhaust"
	_visual = MeshInstance3D.new()
	_visual.name = "TwinFlames"
	_visual.mesh = _mesh
	_visual.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.vertex_color_use_as_albedo = true
	_visual.material_override = material
	add_child(_visual)
	clear()


func tick(delta: float, boost: ChargeBoost, tuning: VehicleTuning, active: bool, grounded: bool = true) -> void:
	_grounded = grounded
	_clock += maxf(0.0,delta)
	var steps: int = int(floor((_clock + 0.000001)*RATE))
	if steps <= 0:
		return
	_clock -= steps/RATE
	_phase += steps
	sample_count += steps
	var length_target: float = 0.0
	var width_target: float = 0.0
	if active and boost.phase == ChargeBoost.Phase.CHARGING:
		var charge: float = boost.charge_ratio(tuning)
		length_target = lerpf(0.35,1.25,charge)
		width_target = lerpf(0.065,0.15,charge)
	elif active and boost.phase == ChargeBoost.Phase.BOOSTING:
		length_target = lerpf(1.45,2.85,boost.power)
		width_target = lerpf(0.18,0.27,boost.power)
	flame_length = move_toward(flame_length,length_target,steps*0.75)
	flame_width = move_toward(flame_width,width_target,steps*0.12)
	_draw()


func ignite(power: float, grounded: bool = true) -> void:
	# Release is an event drawing, like landing contact; the next held sample keeps its cadence.
	flame_length = lerpf(1.45,2.85,clampf(power,0.0,1.0))
	flame_width = lerpf(0.18,0.27,clampf(power,0.0,1.0))
	_grounded = grounded
	_draw()


func _draw() -> void:
	_mesh.clear_surfaces()
	_visual.visible = flame_length > 0.015
	if not _visual.visible:
		return
	_mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)
	for side: int in [-1,1]:
		var origin := Vector3(side*0.76,0.363,2.55)
		var flicker: float = FLICKER[posmod(_phase+(2 if side>0 else 0),FLICKER.size())]
		var lean: float = sin(float(_phase+side)*2.2)*0.08
		_tongue(origin,flame_length*flicker,flame_width,lean,false)
		# The shorter core is lifted just above the outer shell so both colors read in the chase view.
		_tongue(origin+Vector3(0,flame_width*0.35,-0.015),flame_length*flicker*0.65,flame_width*0.62,lean*0.4,true)
	_mesh.surface_end()


func _tongue(origin: Vector3, length: float, width: float, lean: float, core: bool) -> void:
	for ring: int in range(3):
		var a: float = ring/3.0
		var b: float = (ring+1)/3.0
		for face: int in range(6):
			var angle_a: float = face*TAU/6.0
			var angle_b: float = (face+1)*TAU/6.0
			var p0: Vector3 = _point(origin,length,width,lean,a,angle_a)
			var p1: Vector3 = _point(origin,length,width,lean,a,angle_b)
			var p2: Vector3 = _point(origin,length,width,lean,b,angle_b)
			var p3: Vector3 = _point(origin,length,width,lean,b,angle_a)
			var color: Color = CORE if core else OUTER.lerp(TIP,a)
			color = color.darkened(0.06 if face%2==0 else 0.0)
			for vertex: Vector3 in [p0,p1,p2,p0,p2,p3]:
				_mesh.surface_set_color(color)
				_mesh.surface_add_vertex(vertex)


func _point(origin: Vector3, length: float, width: float, lean: float, along: float, angle: float) -> Vector3:
	var radius: float = width * (1.0-along) * (1.0+sin(along*PI)*0.55)
	var parent_body := get_parent() as Node3D
	# The mouth follows its pipe; the grounded jet bends level instead of burying itself during nose lift.
	var pitch_rise: float = tan(parent_body.rotation.x)*parent_body.scale.z/maxf(parent_body.scale.y,0.01) if _grounded else 0.0
	return origin+Vector3(cos(angle)*radius+lean*along*along,sin(angle)*radius*0.7+0.035*along+pitch_rise*length*along,length*along)


func clear() -> void:
	_clock = 0.0
	_phase = 0
	sample_count = 0
	flame_length = 0.0
	flame_width = 0.0
	_mesh.clear_surfaces()
	if _visual != null:
		_visual.visible = false


func snapshot() -> Dictionary:
	return {"samples":sample_count,"length":flame_length,"width":flame_width,"visible":_visual.visible,
		"surfaces":_mesh.get_surface_count(),"nodes":get_child_count()}
