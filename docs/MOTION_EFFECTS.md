# Car motion effects

Wind uses actual forward speed. It starts lightly above 8 m/s and builds to full strength near 32 m/s. Twelve tapered, pale blue-white streaks are the upper limit. They pass along the car's sides, bend slightly with steering, and fade out when speed falls or driving ends. Their ribbons face the camera so angled views keep them readable. Airborne wind is quieter.

A real landing event triggers three layers: a broken cream ring that expands along the ground, brief outward flicks, and rounded clusters of low-poly dust lobes. Impact speed controls cloud size, density, and lifetime. The center stays clear so the body squash and trunk slam remain visible. Clouds last roughly half to three-quarters of a second. The launch retains two short upward swishes.

Wind follows the interpolated car every render frame. Effect geometry and cloud poses change at 12 FPS on their own clock, independent of animation clip changes. Landings anchor to the actual physics contact position; their dust remains on the road as the car moves away. Pause freezes both layers, and restart clears them.

`CarMotionAccents` uses a six-slot reusable impact pool, one airflow mesh, and at most 18 dust lobes per impact. Clouds use [Godot MultiMesh](https://docs.godotengine.org/en/stable/classes/class_multimesh.html) instances rather than spawning a node for each particle. Materials and geometry are created once; this pack needs no external textures or add-ons. Decorative effects never change collision or handling.

## Review

Run `tools/animation_garage.sh`, then press V or click **Wind + impact review**. Space pauses; its timeline scrubs the body and effects together. L and D run an actual launch and 12-meter drop. Left/right returns to individual car clips.

`animation_previews/motion_effects.gif` shows the effects clearly from the garage angle. `animation_previews/motion_effects_gameplay.gif` records actual acceleration, travel, Ground Punch, and floor contact from the normal chase camera.

## Rebuild the previews

From the project root:

```sh
'/Applications/Godot.app/Contents/MacOS/Godot' --fixed-fps 60 --path . res://scenes/review/car_animation_garage.tscn -- --capture-effects
'/Applications/Godot.app/Contents/MacOS/Godot' --fixed-fps 60 --path . --script res://tools/capture_motion_effects_gameplay.gd
python3 tools/package_animation_previews.py
```

The packaging script uses Pillow. Runtime gameplay has no Python dependency.

`tools/verify.sh` runs 139 checks: 22 driving checks, 59 animation checks, 20 effects checks, and 38 boost checks. The added coverage includes speed response, idle/disabled cleanup, held geometry with smooth following, 30/60/120 render FPS, stronger impact clouds, world-space dust, bounded reuse across 100 impacts, expiry, actual floor-contact emission, pause, reset, and the review timeline. Native rendering was also inspected from both garage and gameplay cameras.
