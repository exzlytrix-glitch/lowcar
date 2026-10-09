class_name CarHandling
extends Resource
## City-lab handling experiment: sharp arcade steering, a real drift, and wall scrapes that keep speed.
## Tuned live from the lab's T panel; saved to resources/citygen/lab_car_handling.tres.

@export_group("Steering")
@export_range(0.5, 6.0, 0.05) var steer_low_speed: float = 2.8
@export_range(0.5, 6.0, 0.05) var steer_top_speed: float = 2.35
@export_range(0.3, 5.0, 0.05) var steer_boost_speed: float = 1.6
@export_range(1.0, 30.0, 0.5) var steer_response: float = 7.5
@export_range(2.0, 40.0, 0.5) var grip: float = 12.0
@export_range(0.0, 1.0, 0.05) var air_steer: float = 0.6

@export_group("Drift")
@export_range(0.5, 10.0, 0.1) var drift_grip: float = 2.2
@export_range(1.0, 3.0, 0.05) var drift_steer_boost: float = 1.5
@export_range(15.0, 80.0, 1.0) var drift_max_angle: float = 50.0
@export_range(0.0, 15.0, 0.25) var drift_speed_loss: float = 2.5
@export_range(0.0, 15.0, 0.25) var drift_exit_kick: float = 4.0
@export_range(5.0, 25.0, 0.5) var drift_min_speed: float = 12.0

@export_group("Walls")
@export_range(0.0, 1.0, 0.01) var wall_glance_keep: float = 0.92
@export_range(0.0, 1.0, 0.01) var wall_head_on_keep: float = 0.3
@export_range(0.0, 1.0, 0.05) var wall_align: float = 0.5
