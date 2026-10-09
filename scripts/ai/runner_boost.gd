class_name RunnerBoost
extends RefCounted
## How a learned runner uses the charge boost: one decision commits to a whole charge ("charge for this
## long, then let go"), instead of having to keep the button held decision after decision. The boost
## itself is the player's (ChargeBoost: slower while charging, fires on release); only the choosing is
## easier to learn, because a single try now shows what a charged boost is worth.

const MIN_CHARGE: float = 0.3
const MAX_CHARGE: float = 6.0

var charge_left: float = 0.0


func reset() -> void:
	charge_left = 0.0


## Whether to hold the boost until the next decision. `action` > 0 starts a charge; how far above 0
## sets its length.
func hold(dt: float, action: float, car: ArcadeVehicle) -> bool:
	if charge_left > 0.0:
		if car.boost.phase != ChargeBoost.Phase.CHARGING:
			charge_left = 0.0  # braking cancelled the charge
			return false
		charge_left -= dt
		return charge_left > 0.0
	if action > 0.0 and car.boost.phase == ChargeBoost.Phase.READY:
		charge_left = lerpf(MIN_CHARGE, MAX_CHARGE, clampf(action, 0.0, 1.0))
		return true
	return false
