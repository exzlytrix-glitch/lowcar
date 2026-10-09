class_name ChaseTuning
extends Resource
## First playable pursuit: tune difficulty independently of the street geometry.

@export var seconds_per_tier: float = 30.0
@export var initial_police_budget: int = 2
@export var additional_police_per_tier: int = 1
@export var maximum_tier: int = 6
@export var maximum_police: int = 7
@export var start_grace_seconds: float = 3.0
@export var spawn_interval_seconds: float = 1.2
@export var recycle_distance_m: float = 150.0
@export var patrol_speed_mps: float = 30.0
@export var speed_per_tier_mps: float = 2.4
@export var capture_radius_m: float = 7.5
@export var capture_max_speed_mps: float = 7.0
@export var capture_seconds: float = 3.0
@export var capture_decay_seconds: float = 1.5
