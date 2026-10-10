class_name GameProfile
extends RefCounted
## What carries over between runs, saved to user://profile.json: banked chaos points, the best run, and
## the garage upgrades bought with them.

const PATH: String = "user://profile.json"
## Garage upgrades: id, name, what a level does, and the price of each level.
const UPGRADES: Array[Dictionary] = [
	{"id": "armor", "name": "Armor plating", "info": "+15 max health a level", "costs": [400, 900, 1800, 3500]},
	{"id": "engine", "name": "Engine tune", "info": "+4% top speed a level", "costs": [500, 1100, 2200, 4200]},
	{"id": "nitro", "name": "Nitro tank", "info": "boost charges faster, lasts longer", "costs": [450, 1000, 2000, 3800]},
]

var bank: int = 0
var best_points: int = 0
var best_seconds: float = 0.0
var best_wrecks: int = 0
var runs: int = 0
var levels: Dictionary = {}


static func load_profile() -> GameProfile:
	var profile := GameProfile.new()
	if not FileAccess.file_exists(PATH):
		return profile
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(PATH))
	if data is Dictionary:
		profile.bank = int(data.get("bank", 0))
		profile.best_points = int(data.get("best_points", 0))
		profile.best_seconds = float(data.get("best_seconds", 0.0))
		profile.best_wrecks = int(data.get("best_wrecks", 0))
		profile.runs = int(data.get("runs", 0))
		var saved: Variant = data.get("levels", {})
		if saved is Dictionary:
			for id: String in saved:
				profile.levels[id] = int(saved[id])
	return profile


func save() -> void:
	var file := FileAccess.open(PATH, FileAccess.WRITE)
	if file == null:
		return
	file.store_string(JSON.stringify({"bank": bank, "best_points": best_points, "best_seconds": best_seconds,
		"best_wrecks": best_wrecks, "runs": runs, "levels": levels}, "\t"))


func level(id: String) -> int:
	return int(levels.get(id, 0))


## Price of the next level, or -1 when the upgrade is maxed.
func next_cost(id: String) -> int:
	for upgrade: Dictionary in UPGRADES:
		if upgrade["id"] == id:
			var costs: Array = upgrade["costs"]
			return int(costs[level(id)]) if level(id) < costs.size() else -1
	return -1


func buy(id: String) -> bool:
	var cost: int = next_cost(id)
	if cost < 0 or cost > bank:
		return false
	bank -= cost
	levels[id] = level(id) + 1
	save()
	return true


## Banks a finished run; true when it beat the best score.
func add_run(points: int, seconds: float, wrecks: int) -> bool:
	runs += 1
	bank += points
	var record: bool = points > best_points
	best_points = maxi(best_points, points)
	best_seconds = maxf(best_seconds, seconds)
	best_wrecks = maxi(best_wrecks, wrecks)
	save()
	return record


## Applies the bought upgrades to the player's car (base: the car's own unmodified tuning).
func apply(car: LabVehicle, base: VehicleTuning) -> void:
	var tuning := base.duplicate() as VehicleTuning
	tuning.maximum_speed_mps *= 1.0 + 0.04 * level("engine")
	tuning.boost_max_charge_seconds *= 1.0 - 0.1 * level("nitro")
	tuning.boost_max_duration_seconds += 0.4 * level("nitro")
	car.tuning = tuning
	car.max_health = 100.0 + 15.0 * level("armor")
	car.health = car.max_health
