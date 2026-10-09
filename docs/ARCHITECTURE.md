# Lowcar scaffold architecture

## Scene ownership

The main scene wires five responsibilities: CityWorld, the player vehicle, its camera and attachment, ChaseDirector, and GameUI. Main handles lifecycle transitions and forwards run events. It does not own car handling or procedural building construction.

RunSession is the only autoload. It stores current run state, seed, time, distance, pursuit tier, and ending reason. It communicates changes through signals. World and vehicle objects remain scene-local.

## Vehicle boundary

ArcadeVehicle owns movement and collision through CharacterBody3D. VehicleTuning supplies handling values. PlayerInput supplies driver commands; PoliceVehicle supplies AI through the same set_driver_command method.

The controller is an initial arcade blockout, with steering and controlled launch velocity. It is not finished tire or suspension simulation.

Presentation is a top-level visual node. It follows the interpolated physical transform every rendered frame and samples local chassis poses at a lower rate. Wheels and camera remain independently smooth. This keeps style timing out of steering and collisions.

The player's presentation instances red_muscle_car.tscn, backed by a GLB in assets/models/vehicles/red_muscle_car. Its Chassis, hinged trunk, and four independent suspension / steering / spin branches are preserved on import. The source Blender file keeps individual pieces editable; the runtime export combines them into six meshes. Front wheels steer visually and all wheels spin using their own radius. AnimationPlayer drives 12 FPS proxy poses, which CarPresentation applies without deforming the physical controller. See CAR_ANIMATION_PACK.md for clips and review controls.

## Attachments

GroundPunch is a child behavior node under Attachments. AttachmentDefinition stores its name, cooldown, launch speed, and ground requirement.

The attachment emits activation and readiness signals. The presentation observes activation for its short squash-and-release accent. The HUD reads actual readiness.

Future attachments get their own behavior nodes. Add only the common interface needed by real attachment types.

## City streaming

CityStreamer tracks the block coordinate around the vehicle and keeps a fixed-radius neighborhood loaded. CityChunk constructs placeholder roads and building sets from a seed plus grid coordinate.

Revisiting a coordinate recreates the same block for that seed. Only active nearby blocks are kept in memory. The generated geometry is a disposable kit behind a stable streaming boundary.

During movement, new blocks are added incrementally. Initial load and a fresh run build the starting neighborhood together.

## Chase boundary

ChaseDirector spawns actual PoliceVehicle actors on clear, loaded streets after an opening grace period. Every 30 seconds it raises pursuit speed and desired count, capped at seven cars and six tiers. Distant or unloaded patrols are recycled outside the player's immediate area.

ChaseRoads uses CityChunk's 64-meter grid. Each patrol routes via intersections, predicts the player's next position, brakes for bends, and reverses out of a physical obstruction. Patrols use the shared arcade movement controller and collide with buildings, the player, and each other. Their presentation holds body lean and warning lights at 12 FPS while travel stays smooth.

Capture fills only when a grounded, slow player has a nearby patrol with an unobstructed line of sight. Speed, separation, or a launcher jump drains the meter. Police contact slows the player; terminal world impact remains a separate crash condition. The HUD reads actual cars, capture progress, nearest distance, and reinforcement timing; the radar draws physical patrol positions. Positional sirens share one generated looping stream on the SFX bus.

## Pause and ending

The world, vehicle, and director are pausable. UI and lifecycle handling remain active so pause buttons work. The run timer advances only in the driving phase.

A strong actual wall impact ends a run through the vehicle's crashed signal. The capture detector supplies a separate ending reason. Restart resets seed-dependent world content, movement, attachment readiness, camera, and run counters.

## Renderer and production data

The current project uses Compatibility rendering. Named physics layers are World, Player, Police, and Traffic. The hero car uses a dedicated faceted model with embedded materials; street geometry and the patrol body use the existing simple kit. The audio bus layout is ready for later sound integration.

Export presets should be created when distribution targets are chosen. No export templates or third-party packages are installed by this scaffold.

## Documentation references

The project boundaries follow scene ownership and explicit system connections. See the official [Godot project organization guidance](https://docs.godotengine.org/en/stable/tutorials/best_practices/project_organization.html), [CharacterBody3D reference](https://docs.godotengine.org/en/stable/classes/class_characterbody3d.html), and [physics interpolation guide](https://docs.godotengine.org/en/stable/tutorials/physics/interpolation/physics_interpolation_quick_start_guide.html).
