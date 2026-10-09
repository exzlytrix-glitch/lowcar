# Lowcar car animation pack

The red car now has 34 native Godot clips sampled as held poses at 12 FPS. World travel, camera tracking, wheel spin, and steering remain smooth. No body deformation changes the vehicle collider.

The four death clips are `crash_front`, `crash_left`, `crash_right`, and `explode`. Wall normals select the matching impact, with held squash, a single rebound, and a lasting shortened pose; bumpers, lights and trim follow the body deformation. The standalone explosion squeezes, pops upward through a faceted flame burst, then slaps down to a recognizable flat red wreck. Fire shares BoostExhaust's orange/cream palette, six-sided tapered tongues and flicker sequence. Four wheels kick loose and settle; small cream landing clouds accompany the body slap. The garage's Front / Left / Right / Explode buttons play all four, and its paused timeline scrubs the effects backwards. `CarPresentation.play_explosion()` is the explicit visual trigger. Crash results reveal after the drawing finishes; run-end timing and collision thresholds stay the same.

The polish pass carries the outgoing silhouette into new moves over one to three held poses. Releasing a turn unloads its existing bank; opposite steering crosses into the new bank without a neutral snap. A shared pose clock preserves 12 samples per second even during repeated maneuver changes. Impacts still apply their contact pose immediately.

The outside tires compress during turns, and front/rear tires show acceleration or braking load while preserving road contact. Airborne wheels hang under the body. Reverse braking pitches toward its direction of travel. Descent speed gradually opens the trunk further; contact shuts it, followed by one smaller lid bounce during rebound. Steering can resume after the main landing rebound, before its quiet recovery tail finishes.

## What plays

| Action | Treatment |
| --- | --- |
| Idle / driving | Small engine rumble and road rhythm |
| Acceleration / braking | Rear load and nose lift; nose dip and rebound |
| Turn left / right | Three turn-in variants per side, anticipation, overshoot, held bank |
| Handbrake left / right | Outside-wheel load and rear-body yaw |
| Ground Punch | One held compression pose, tall release, trailing wheels, deployed foot |
| Rising / apex / falling | Stretch, broad hang pose, nose-down descent |
| Falling trunk | Real hinged panel opens about 14–19 degrees above a dark cavity |
| Soft / medium / hard landing | Eight variants total; roughly 86%, 69%, and 49% body height before rebound |
| Trunk slam | Shut on contact, a small inertia bounce, then latch |
| Front / left / right wall | Struck-region crumple, held squash, rebound and lasting wreck |
| Standalone explosion | Pressure squeeze, single held flash, booster-style fire, four loose wheels, flat red wreck |
| Reset | Closed trunk, neutral scale, cleared wheel and variation state |

Turns choose one authored variant and a small 0.965–1.035 lean gain when the maneuver begins. Holding a turn keeps that choice. The next turn avoids immediately repeating the same variant. Each jump also gets a small fixed roll and trunk offset. The city seed makes the variation sequence reproducible on restart.

Physics events decide airborne states and landing strength. Landing speeds below 9 m/s select soft, 9–17 m/s medium, and 17 m/s or more hard. Contacts below 4 m/s do not trigger impact choreography. A crash or landing interrupts the current maneuver; opposite steering can interrupt turn-in immediately. Pause freezes animation with the run.

## Inspect it

Run `tools/animation_garage.sh`. The garage has every clip, a pauseable frame slider, a chase sequence, and actual physics launch/drop buttons. Left/right switches clips, Space pauses, C plays the sequence, L launches, and D drops from 12 meters. V opens the wind + impact review, with a pauseable effects timeline. See MOTION_EFFECTS.md for the effects handoff. Pause a clip before dragging its timeline. This scene is separate from normal F5 gameplay.

Native viewport previews live in `assets/models/vehicles/red_muscle_car/animation_previews/`:

- `real_launch_and_landing.gif`: real controller, gravity, floor contact, and event-driven animation.
- `animation_pack.gif`: authored turn, brake, launch, falling, landing, and recovery sequence.
- `animation_polish.gif`: actual driving, steering reversal, brake recovery, launch, landing, and handbrake from the normal chase camera.
- `impact_contact_sheet.png`: enlarged key poses for comparison.

The Blender source contains the original 30 clips as named timeline sections at 12 FPS. `source/animation_timeline.json` lists their frame ranges. Body, trunk, and suspension keys use constant interpolation. The four new death clips are authored in the native Godot library and JSON; their fragment geometry has its own editable `source/explosion_parts.blend`. Godot remains the runtime source of animation selection and subtle variations.

## Edit / rebuild

`resources/animation/car_clips.json` contains authored pose keys in degrees and meters. `car_animation_pack.tres` is the generated, editable Godot AnimationLibrary. The player's AnimationPlayer drives proxy pose nodes; CarPresentation applies those poses to the actual rig. Suspension, steering, and spin have separate pivots so flattened wheels keep spinning correctly.

From the project root:

```sh
python3 tools/author_car_animation_pack.py
'/Applications/Godot.app/Contents/MacOS/Godot' --headless --path . --script res://tools/build_car_animation_library.gd
'/Applications/Blender.app/Contents/MacOS/Blender' --background --python tools/add_blender_animation_timeline.py
./tools/verify.sh
```

Running the authoring Python script restores its authored defaults. To edit JSON directly, skip that first command. If rebuilding the geometry, run `build_red_muscle_car.py` before adding the Blender timeline.

## Validation

The verification command runs the existing main-scene lifecycle checks and 59 animation checks. Coverage includes all clips loading; finite, positive, stepped tracks; 12 pose samples at 30/60/120 render FPS, including rapid maneuver changes; wheel motion between held body poses; repeated turn variation and seed replay; bank continuity, recovery, and opposite steering; loaded tire contact heights; forward/reverse braking; an actual full launch; the falling trunk; three actual drop heights; graded squash; immediate trunk closure; steering after the rebound; pause/resume/reset; an actual wall crash; and unchanged physical collider dimensions.

Native rendering was also reviewed separately from headless tests. The GIF capture uses Godot's actual viewport. A 12 FPS GIF illustrates poses; smooth world and wheel motion are assessed in the running game.
