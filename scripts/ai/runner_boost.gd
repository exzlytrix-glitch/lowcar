class_name RunnerBoost
extends RefCounted
## How a learned runner uses the charge boost: one decision commits to a whole charge ("charge for this
## long, then let go"), instead of having to keep the button held decision after decision. The boost
## itself is the player's (ChargeBoost: slower while charging, fires on release); only the choosing is
## easier to learn, because a single try shows what a charged boost is worth.

## Charge length for choices 1-4 (0 = no boost): a quick pop up to a big 6-second charge.
const CHARGES: PackedFloat32Array = [0.4, 1.5, 3.0, 6.0]

var charge_left: float = 0.0


func reset() -> void:
	charge_left = 0.0


## Whether to hold the boost until the next decision. `choice` 1-4 starts a charge of that length.
func hold(dt: float, choice: int, car: ArcadeVehicle) -> bool:
	if charge_left > 0.0:
		if car.boost.phase != ChargeBoost.Phase.CHARGING:
			charge_left = 0.0  # braking cancelled the charge
			return false
		charge_left -= dt
		return charge_left > 0.0
	if choice >= 1 and car.boost.phase == ChargeBoost.Phase.READY:
		charge_left = CHARGES[mini(choice, CHARGES.size()) - 1]
		return true
	return false
