class_name WreckSmoke
extends Node3D
## A wrecked cop: a flash, the car charred dark, and low-poly smoke puffs rising off it until it is
## cleared away.

const PUFF_EVERY: float = 0.22
const PUFF_LIFE: float = 2.4

var _clock: float = 0.0
var _flash: OmniLight3D
var _puff_mesh: SphereMesh
var _puff_material: StandardMaterial3D
var _rng := RandomNumberGenerator.new()


static func attach(car: Node3D) -> void:
	var smoke := WreckSmoke.new()
	smoke.name = "WreckSmoke"
	car.add_child(smoke)


func _ready() -> void:
	_rng.randomize()
	var charred := StandardMaterial3D.new()
	charred.albedo_color = Color(0.08, 0.07, 0.07, 0.62)
	charred.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	charred.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	for found: Node in get_parent().find_children("*", "MeshInstance3D", true, false):
		(found as MeshInstance3D).material_overlay = charred
	_flash = OmniLight3D.new()
	_flash.light_color = Color("#FFB347")
	_flash.light_energy = 9.0
	_flash.omni_range = 14.0
	_flash.position.y = 1.2
	add_child(_flash)
	create_tween().tween_property(_flash, "light_energy", 0.0, 0.5)
	_puff_mesh = SphereMesh.new()
	_puff_mesh.radius = 0.7
	_puff_mesh.height = 1.2
	_puff_mesh.radial_segments = 6
	_puff_mesh.rings = 3
	_puff_material = StandardMaterial3D.new()
	_puff_material.albedo_color = Color(0.22, 0.22, 0.24, 0.75)
	_puff_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_puff_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED


func _process(delta: float) -> void:
	_clock -= delta
	if _clock > 0.0:
		return
	_clock = PUFF_EVERY
	var puff := MeshInstance3D.new()
	puff.mesh = _puff_mesh
	puff.material_override = _puff_material
	puff.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	puff.top_level = true
	add_child(puff)
	puff.global_position = global_position + Vector3(_rng.randf_range(-0.6, 0.6), 1.3, _rng.randf_range(-0.8, 0.8))
	puff.scale = Vector3.ONE * 0.5
	var tween := puff.create_tween().set_parallel(true)
	tween.tween_property(puff, "global_position", puff.global_position + Vector3(_rng.randf_range(-1.0, 1.0), 4.5, _rng.randf_range(-1.0, 1.0)), PUFF_LIFE)
	tween.tween_property(puff, "scale", Vector3.ONE * 1.8, PUFF_LIFE)
	tween.chain().tween_callback(puff.queue_free)
