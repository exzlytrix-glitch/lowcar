class_name PolicyNet
extends RefCounted
## Runs a trained cop brain in plain GDScript: the small actor network exported by training/train.py
## as JSON (layer weights plus the observation scaling used during training). No plugins, no C#.

var obs_dim: int = 0
var act_dim: int = 0
var meta: Dictionary = {}
var _mean := PackedFloat32Array()
var _std := PackedFloat32Array()
var _clip: float = 10.0
var _weights: Array[PackedFloat32Array] = []
var _biases: Array[PackedFloat32Array] = []
var _sizes: Array[Vector2i] = []
var _tanh: Array[bool] = []


static func load_file(path: String) -> PolicyNet:
	if not FileAccess.file_exists(path):
		return null
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (data is Dictionary):
		return null
	var net := PolicyNet.new()
	net._load(data)
	return net


func _load(data: Dictionary) -> void:
	meta = data
	obs_dim = int(data["obs_dim"])
	act_dim = int(data["act_dim"])
	_mean = PackedFloat32Array(data["obs_mean"])
	_std = PackedFloat32Array(data["obs_std"])
	_clip = float(data.get("obs_clip", 10.0))
	for layer: Dictionary in data["layers"]:
		var rows: Array = layer["w"]
		var flat := PackedFloat32Array()
		for row: Array in rows:
			flat.append_array(PackedFloat32Array(row))
		_weights.append(flat)
		_biases.append(PackedFloat32Array(layer["b"]))
		_sizes.append(Vector2i((rows[0] as Array).size(), rows.size()))
		_tanh.append(String(layer["act"]) == "tanh")


## Deterministic action (the policy's mean), each value clamped to -1..1.
func act(obs: PackedFloat32Array) -> PackedFloat32Array:
	var x := PackedFloat32Array()
	x.resize(obs_dim)
	for i: int in obs_dim:
		x[i] = clampf((obs[i] - _mean[i]) / _std[i], -_clip, _clip)
	for layer: int in _weights.size():
		var weights: PackedFloat32Array = _weights[layer]
		var bias: PackedFloat32Array = _biases[layer]
		var inputs: int = _sizes[layer].x
		var outputs: int = _sizes[layer].y
		var y := PackedFloat32Array()
		y.resize(outputs)
		for o: int in outputs:
			var total: float = bias[o]
			var row: int = o * inputs
			for i: int in inputs:
				total += weights[row + i] * x[i]
			y[o] = tanh(total) if _tanh[layer] else total
		x = y
	for i: int in x.size():
		x[i] = clampf(x[i], -1.0, 1.0)
	return x
