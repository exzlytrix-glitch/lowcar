class_name StandoffRule
extends RefCounted
## "Slowing down means death": when the runner crawls (under SPEED) with a cop close by (within RANGE,
## centre to centre, about two car lengths) for more than GRACE seconds, it takes DAMAGE_PER_SECOND
## until it gets moving or the cops are gone. In training it counts for the cops as a team, not as any
## cop's own hit (paid for it per cop, they parked at exactly this range and let the rule do the work):
## the runner learns that standoffs always lose, and the cops still have to ram a slowed runner to score.
## The same rule runs in chase training and in the lab, for the AI runner and for you.

const SPEED: float = 15.0 / 3.6
const RANGE: float = 12.0
const DAMAGE_PER_SECOND: float = 5.0
const GRACE: float = 2.0

var _standoff_for: float = 0.0


func reset() -> void:
	_standoff_for = 0.0


## Call every physics frame. Applies the damage and returns the cops in the standoff (empty if none).
func tick(runner: LabVehicle, cops: Array, delta: float) -> Array:
	var near: Array = []
	if Vector2(runner.velocity.x, runner.velocity.z).length() < SPEED:
		for cop: LabVehicle in cops:
			if is_instance_valid(cop) and cop.global_position.distance_to(runner.global_position) < RANGE:
				near.append(cop)
	if near.is_empty():
		_standoff_for = 0.0
		return near
	_standoff_for += delta
	if _standoff_for >= GRACE:
		runner.apply_damage(DAMAGE_PER_SECOND * delta, "standoff")
	return near
