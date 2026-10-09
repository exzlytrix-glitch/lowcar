class_name PolicyNet
extends RefCounted
## Runs a trained cop brain in plain GDScript: the small actor network exported by training/train.py
## or training/train_chase.py as JSON (layer weights plus the observation scaling used during
## training). No plugins, no C#.
##
## Chase brains also list their output heads: "gauss" (smooth controls like steering: the brain's
## average is used), "bern" (on/off like the handbrake) and "cat" (pick one of N). On/off and pick
## outputs are rolled with the brain's own odds, exactly as in training: using only the most likely
## answer would hide anything the brain does less than half the time (a burst it fires 30% of the
## time would never happen).

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
## [kind, size] pairs, empty for older brains.
var heads: Array = []


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
	for head: Dictionary in data.get("heads", []):
		heads.append([String(head["kind"]), int(head["size"])])


## The brain's answer in wire order (one value per head output: gauss values, 0/1 per on/off, the index
## picked per choice). Brains without heads answer like act().
func decide(obs: PackedFloat32Array, rng: RandomNumberGenerator) -> PackedFloat32Array:
	var raw: PackedFloat32Array = _forward(obs)
	if heads.is_empty():
		for i: int in raw.size():
			raw[i] = clampf(raw[i], -1.0, 1.0)
		return raw
	var out := PackedFloat32Array()
	var at: int = 0
	for head: Array in heads:
		var size: int = head[1]
		match String(head[0]):
			"gauss":
				for k: int in size:
					out.append(clampf(raw[at + k], -1.0, 1.0))
			"bern":
				for k: int in size:
					out.append(1.0 if rng.randf() < 1.0 / (1.0 + exp(-raw[at + k])) else 0.0)
			"cat":
				var top: float = -INF
				for k: int in size:
					top = maxf(top, raw[at + k])
				var total: float = 0.0
				for k: int in size:
					total += exp(raw[at + k] - top)
				var roll: float = rng.randf() * total
				var pick: int = size - 1
				for k: int in size:
					roll -= exp(raw[at + k] - top)
					if roll <= 0.0:
						pick = k
						break
				out.append(float(pick))
		at += size
	return out


## Deterministic action (the policy's mean), each value clamped to -1..1.
func act(obs: PackedFloat32Array) -> PackedFloat32Array:
	var x: PackedFloat32Array = _forward(obs)
	for i: int in x.size():
		x[i] = clampf(x[i], -1.0, 1.0)
	return x


func _forward(obs: PackedFloat32Array) -> PackedFloat32Array:
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
	return x
