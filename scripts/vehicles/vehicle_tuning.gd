class_name VehicleTuning
extends Resource
## Shared tunable data for the initial arcade controller.

@export var maximum_speed_mps: float = 32.0
@export var reverse_speed_mps: float = 9.0
@export var acceleration_mps2: float = 15.0
@export var braking_mps2: float = 27.0
@export var coasting_drag_mps2: float = 4.0
@export var steering_radians_per_second: float = 1.65
@export var road_grip: float = 9.0
@export var handbrake_grip: float = 2.3
@export var gravity_mps2: float = 25.0
@export var terminal_impact_speed_mps: float = 12.0

@export_group("Charge boost")
@export var boost_max_charge_seconds: float = 10.0
@export var boost_min_speed_mps: float = 38.0
@export var boost_max_speed_mps: float = 64.0
@export var boost_min_duration_seconds: float = 0.9
@export var boost_max_duration_seconds: float = 4.0
