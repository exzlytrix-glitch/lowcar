class_name AttachmentDefinition
extends Resource
## The launcher is the first implementation; future attachments get their own behavior.

@export var display_name: String = "Ground Punch"
@export var cooldown_seconds: float = 1.8
@export var upward_speed_mps: float = 24.0
@export var requires_ground: bool = true

