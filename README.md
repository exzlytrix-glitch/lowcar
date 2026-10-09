# Lowcar

Godot 4.7 endless procedural-city chase through Belle Rive, starring a low-poly red muscle car.

Belle Rive's ordinary four-door police cruiser replaces the primitive patrol placeholder. Its GLB, editable Blender source, and studio previews are in `assets/models/vehicles/police_cruiser/`; rebuild with `tools/build_police_cruiser.py`. The model includes authored city livery, separate wheel pivots and independently flashing lightbar lenses.

## Open and run

Import project.godot in Godot and press F5. The project starts at its title screen.

The installed engine used for verification is Godot 4.7. There are no external add-ons or runtime dependencies. Compatibility rendering is the initial lightweight baseline; final render treatment comes later.

On this Mac, tools/launch.sh opens the project in the Godot editor. Set LOWCAR_GODOT to another Godot executable when needed.

## Controls

| Action | Keyboard and mouse | Gamepad |
| --- | --- | --- |
| Accelerate | W or Up | Right trigger |
| Brake or reverse | S or Down | Left trigger |
| Steer | A/D or Left/Right | Left stick |
| Charge boost | Hold Shift, release to fire | Hold right shoulder, release to fire |
| Handbrake | Ctrl | A / bottom face button |
| Ground Punch launcher | Space or double-click left mouse | X / left face button |
| Pause | Escape | Start |
| Restart same city | R | Pause-menu button |
| Debug overlay | F3 | — |

The chase starts after a three-second head start. Two patrols pursue you through the streets; every 30 seconds, backup adds a car and raises patrol speed, up to seven cars at pursuit six. The radar shows actual nearby patrols. Staying below 25 km/h beside a cop fills the arrest meter over roughly two to three seconds. Accelerating away, releasing a charged boost, or launching breaks the pin and drains that meter. Police contact slows you; hard building impacts still end the run. Survive for distance and time, then press R to immediately replay the same city.

The launcher requires road contact and has a short cooldown. Hold acceleration while airborne to keep forward travel. Buildings end a run on a sufficiently strong impact.

Holding boost slows the car while charging, up to ten seconds. Release for a forward burst: longer holds give both higher speed and longer thrust. A full charge reaches 64 m/s (230 km/h) for four seconds before settling back to cruise speed. Pressing Shift again cuts thrust and begins a new charge; brake or handbrake cancels it. The bottom-right meter shows charge and remaining thrust. Twin exhaust flames and the chassis kick use the same held-pose style as the car.

## Working foundation

- Title, driving, pause, result, restart, and return-to-title states.
- Dedicated bright-red muscle-car GLB with editable Blender source and a separate presentation rig.
- All 107 finished buildings populate the streamed city: the three original studies and all twenty-six four-model batches. Authored scales, street-facing placement, seeded variety, and world collision are active.
- Tunable arcade driving, braking, reverse, handbrake, and wall-impact handling.
- Charge/release boost with a ten-second charge cap, charge-speed tradeoff, exhaust fire, and charge/thrust HUD.
- Ground Punch attachment driven by a resource, with keyboard, gamepad, and double-click inputs.
- Speed-driven airflow, impact rings, low-poly dust clusters, and launch swishes.
- Smooth rear camera and a 34-clip car animation pack: stepped body poses, real trunk hinge, varied turns, graded squash, and recovery.
- Seeded street blocks generated around the car, with a bounded active neighborhood.
- Run time, traveled distance, and attachment-readiness HUD.
- Named physics layers and Master, SFX, Music, and UI audio buses.
- Physical police pursuit along the street grid, predictive interception, corner braking, and reverse recovery.
- Escalating reinforcements, a bounded seven-patrol population, capture and escape, live radar, flashing lights, and positional sirens.

Roadblocks, more police types, the remaining city models, and a broader sound pass are future work. The first survival chase is playable now. Building batch automation is paused while gameplay is developed.

The car model, Blender source, and front/rear/side previews are in assets/models/vehicles/red_muscle_car. Its reusable visual scene is scenes/vehicles/red_muscle_car.tscn. Run tools/animation_garage.sh to review all clips, inspect held frames, and replay a real launch or 12-meter drop. Press V in the garage for wind + impact review. Front / Left / Right / Explode play the four death animations; pause and scrub the timeline to inspect them. Wall impacts squash and shorten the car, with trim following the body. The standalone explosion uses the booster's faceted orange fire and cream cores, four loose wheels, and a flattened red wreck. It is an explicit visual clip, with no new gameplay rule. See [the car animation pack](docs/CAR_ANIMATION_PACK.md) and [motion effects](docs/MOTION_EFFECTS.md) for the short handoff.

Run `tools/building_gallery.sh` to inspect the three new buildings beside the red car. Press 1/2/3 to isolate a model, drag to orbit, G for street view, and B for the rear. The assets, editable sources, and native previews are in `assets/models/buildings/style_trial`; reusable visual scenes are in `scenes/buildings`. All 107 completed models now replace the former procedural placeholder buildings. The city discovers completed building batches automatically, uses shared model resources, draws from the full catalog as the city streams, preserves the layout on restart, and gives the garage collision that keeps its two service bays open. See [building asset notes](assets/models/buildings/style_trial/README.md).

## Project layout

| Folder | Purpose |
| --- | --- |
| scenes/main | Boot scene and system wiring |
| scenes/vehicles | Player car and reusable red muscle car |
| scenes/camera | Chase-camera scene |
| scenes/world | Daylight test world |
| scenes/chase | Director and pursuing patrol vehicles |
| scenes/ui | Starter menu and HUD entry scene |
| scripts | Matching system code, separated by responsibility |
| resources | Vehicle, attachment, and chase tuning data |
| assets | Future production models, materials, textures, shaders, fonts, and audio |
| tests | Main-scene lifecycle and car animation checks |
| tools | Editor / animation-garage launchers, asset builders, verification |
| docs | Short technical handoff |
| exports | Future build outputs, excluded from Git |

## Verify

Run tools/verify.sh. Its 191 checks cover the real main scene through driving, launching, pausing, restarting, streaming, capture, and title transitions; nine city-model checks for coverage, bounds, scale, street clearance, collision, seeded layouts, and the open duplex courtyard; 59 animation checks; 20 directional-crash and explosion checks; 20 motion-effect checks; 38 charge-boost checks; and 21 police checks for actual pursuit, street turns, capture, boost/launch escapes, physical contact, pause, restart, and escalation. Boost coverage includes physical Shift/Ctrl mapping, short and full charges, real speed/duration differences, the ten-second cap, recharging, stationary and airborne releases, pause, restart, boosted collisions, and bounded 12 FPS exhaust geometry.

The headless check validates runtime behavior and lifecycle. Camera composition and visual quality also require review in the running window.

Current verification result: all 169 behavior assertions pass, including the 21 police checks. The full runner still exits with failure because the editor and city-model test report retained asset-cache resources during engine shutdown. The standalone chase/boost checks and rendered chase replay complete successfully; the game also opens and responds to start, pause, and restart in its native window.

## Next implementation

Play the chase and tune how patrols intercept turns, how much pressure each tier adds, and how generous the pin escape window feels. The current police body reuses the existing patrol template so the first pass focuses on gameplay.
