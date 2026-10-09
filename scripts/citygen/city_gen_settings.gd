class_name CityGenSettings
extends Resource
## Every tunable the city lab exposes. The lab saves tuned values to resources/citygen/city_lab_settings.tres.

@export_group("City")
@export var city_seed: int = 7
@export_range(250.0, 2000.0, 10.0) var city_radius: float = 700.0
@export_range(0.0, 0.45, 0.01) var edge_wobble: float = 0.2
@export var ring_road: bool = true
@export_range(1, 24) var district_count: int = 8
@export_range(2, 12) var arterial_count: int = 5

@export_group("District mix")
@export_range(0.0, 3.0, 0.05) var old_town_weight: float = 1.0
@export_range(0.0, 3.0, 0.05) var grid_weight: float = 1.0
@export_range(0.0, 3.0, 0.05) var residential_weight: float = 1.0
@export_range(0.0, 3.0, 0.05) var industrial_weight: float = 0.5

@export_group("Streets")
@export_range(8.0, 30.0, 0.5) var arterial_width: float = 18.0
@export_range(6.0, 20.0, 0.5) var street_width: float = 13.0
@export_range(5.0, 14.0, 0.5) var lane_width: float = 9.5
@export_range(0.5, 2.5, 0.05) var block_scale: float = 1.1
@export_range(0.0, 3.0, 0.05) var curviness: float = 0.7
@export_range(0.0, 1.0, 0.01) var branch_chance: float = 0.85
@export_range(0.0, 1.0, 0.01) var through_chance: float = 0.6
@export_range(0.0, 0.5, 0.005) var dead_end_chance: float = 0.05
@export_range(15.0, 70.0, 1.0) var min_junction_angle: float = 34.0
@export_range(2.0, 30.0, 0.5) var snap_radius: float = 14.0
@export_range(10.0, 80.0, 1.0) var min_road_spacing: float = 36.0
@export_range(500, 40000) var max_segments: int = 14000

@export_group("Blocks")
@export_range(1.0, 8.0, 0.1) var sidewalk_width: float = 3.6
@export_range(0.05, 0.4, 0.01) var curb_height: float = 0.16
@export_range(0.2, 2.0, 0.05) var curb_ramp: float = 0.7
@export_range(0.0, 14.0, 0.25) var corner_radius: float = 9.0
@export_range(0.0, 0.5, 0.01) var park_chance: float = 0.06

@export_group("Buildings")
@export_range(0.0, 1.0, 0.01) var building_fill: float = 0.92
@export_range(60.0, 600.0, 5.0) var detail_distance: float = 220.0
@export_range(150.0, 1500.0, 10.0) var view_distance: float = 600.0
@export_range(4.0, 40.0, 0.5) var tree_spacing: float = 12.0
