extends SceneTree
## Converts the authored pose source into a reusable native Godot AnimationLibrary.

const SOURCE := "res://resources/animation/car_clips.json"
const TARGET := "res://resources/animation/car_animation_pack.tres"
const TRACKS := {
	"body_scale": "Pose:scale",
	"body_rotation": "Pose:rotation",
	"body_offset": "Pose:position",
	"trunk_rotation": "Pose/Trunk:rotation",
	"tire_scale": "Pose/Tires:scale",
	"tire_offset": "Pose/Tires:position",
	"foot_offset": "Pose/Foot:position",
	"damage": "Pose/Crash:position",
}


func _initialize() -> void:
	var source: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(SOURCE))
	var fps: float = float(source.pose_fps)
	var library := AnimationLibrary.new()
	for clip_name: String in source.clips:
		var data: Dictionary = source.clips[clip_name]
		var animation := Animation.new()
		animation.resource_name = clip_name
		animation.length = float(data.frames) / fps
		animation.step = 1.0 / fps
		animation.loop_mode = Animation.LOOP_LINEAR if data.loop else Animation.LOOP_NONE
		for property: String in TRACKS:
			if not data.keys[0].has(property):
				continue
			var track: int = animation.add_track(Animation.TYPE_VALUE)
			animation.track_set_path(track, NodePath(TRACKS[property]))
			animation.track_set_interpolation_type(track, Animation.INTERPOLATION_NEAREST)
			animation.value_track_set_update_mode(track, Animation.UPDATE_CONTINUOUS)
			for frame: int in range(int(data.frames) + 1):
				var value: Vector3 = _sample(data.keys, property, float(frame))
				if property.ends_with("rotation"):
					value = Vector3(deg_to_rad(value.x), deg_to_rad(value.y), deg_to_rad(value.z))
				animation.track_insert_key(track, float(frame) / fps, value)
		library.add_animation(StringName(clip_name), animation)
	var error: Error = ResourceSaver.save(library, TARGET)
	if error != OK:
		printerr("LOWCAR_ANIMATION_BUILD_FAILED: ", error)
		quit(1)
		return
	print("LOWCAR_ANIMATION_LIBRARY_BUILT: ", library.get_animation_list().size(), " clips at ", fps, " FPS")
	quit(0)


func _sample(keys: Array, property: String, frame: float) -> Vector3:
	for index: int in range(keys.size() - 1):
		var a: Dictionary = keys[index]
		var b: Dictionary = keys[index + 1]
		if frame <= float(b.frame):
			var weight: float = clampf((frame - float(a.frame)) / (float(b.frame) - float(a.frame)), 0.0, 1.0)
			weight = weight * weight * (3.0 - 2.0 * weight)
			return _vector(a[property]).lerp(_vector(b[property]), weight)
	return _vector(keys.back()[property])


func _vector(value: Array) -> Vector3:
	return Vector3(float(value[0]), float(value[1]), float(value[2]))
