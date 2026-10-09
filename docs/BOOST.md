# Charge boost

Hold Shift (gamepad right shoulder) to charge while driving more slowly. Release to fire. Charge caps at ten seconds and stays full until released. Longer holds increase both speed and thrust duration. Ctrl is now the handbrake. Brake/handbrake cancels charge or thrust; a new Shift hold cuts the current burst and starts charging again.

Measured on the real vehicle with acceleration held:

| Hold | Speed while charging | Released speed | Thrust duration |
| --- | --- | --- | --- |
| 1 second | 21.91 m/s | 38.73 m/s | 0.99 seconds |
| 4 seconds | 18.45 m/s | 47.15 m/s | 1.99 seconds |
| 10 seconds | 11.54 m/s | 64.00 m/s | 4.00 seconds |

The car returns gradually to its normal 32 m/s cruise speed after thrust expires. Release works from rest and during a Ground Punch jump. Pause freezes both charge and flame drawings; restart/title/crash clears thrust. New charges replace earlier bursts, so their duration and power cannot stack.

Twin faceted orange flames with cream cores attach directly to the animated chassis at the authored tailpipes. Their shapes change at 12 FPS while their parent moves smoothly. Flame length builds during charging and flares immediately on release. The body compresses and rumbles during charge, then kicks upward on release. A small camera FOV change supports the increased speed.

`scripts/vehicles/charge_boost.gd` owns the physics-time state; `VehicleTuning` exposes charge, speed, and duration limits. `boost_exhaust.gd` reuses one ImmediateMesh for both flames. The original GLB and its editable model source remain the car geometry source.

Run `tools/verify.sh` for 139 checks, including 38 boost checks. Rebuild the native preview with:

```sh
/Applications/Godot.app/Contents/MacOS/Godot --fixed-fps 60 --path . --script res://tools/capture_boost.gd
python3 tools/package_boost_preview.py
```

`animation_previews/charge_boost.gif` contains the full actual ten-second charge and release from the normal chase camera. The matching manifest records captured speed, charge, and flame length.
