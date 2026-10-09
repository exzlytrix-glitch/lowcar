# Lowcar red muscle car

Original stylized muscle car with bright red paint, a long sculpted hood, a fastback cabin, polygonal wheel openings, four round headlights, broad rear shoulders, and segmented taillights.

- `red_muscle_car.glb`: game asset with embedded materials and no texture dependencies.
- `source/red_muscle_car.blend`: editable individual parts, the studio setup, and 30 named sections of held animation poses.
- `previews/`: front, rear, and side renders.
- `animation_previews/`: native Godot GIFs, an impact contact sheet, and current wind / landing effects previews.
- `manifest.json`: geometry counts, wheel radii, and the exported GLB hash.

The model uses meters, faces -Z in Godot, and rests on Y=0. It is roughly five meters long. The reusable scene is `res://scenes/vehicles/red_muscle_car.tscn`; the player instances it under Presentation/Model.

Inside the imported Lowcar_Red_Muscle node are Chassis, Wheels, and GroundPunchSocket children. Each wheel has its own pivot under Wheels: FrontLeft, FrontRight, RearLeft, RearRight. Each wheel contains a named {Wheel}Steer child and {Wheel}Spin grandchild. Spin uses local X, steer uses local Y, and the outer pivot handles suspension deformation. Chassis/TrunkHinge opens a separate lid over a real dark cavity. Front tire radius is 0.445 meters; rear radius is 0.48 meters. The physics collider stays in player_car.tscn.

Rebuild from the project root:

```sh
'/Applications/Blender.app/Contents/MacOS/Blender' --background --python tools/build_red_muscle_car.py
'/Applications/Blender.app/Contents/MacOS/Blender' --background --python tools/add_blender_animation_timeline.py
```

Built with Blender 5.1.2 and imported in Godot 4.7. Source and preview directories have .gdignore files so they are excluded from game imports.
