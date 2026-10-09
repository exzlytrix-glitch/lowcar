"""Author Lowcar's reusable twelve-frame-per-second pose clips.

This JSON is the animation source. build_car_animation_library.gd creates the
Godot AnimationLibrary from it; the native Godot preview stage reads the same data.
"""
from pathlib import Path
import json

PROJECT = Path(__file__).resolve().parents[1]
TARGET = PROJECT / "resources/animation/car_clips.json"
TARGET.parent.mkdir(parents=True, exist_ok=True)
CLIPS = {}


def pose(frame, scale=(1, 1, 1), rotation=(0, 0, 0), offset=(0, 0, 0),
         trunk=0, tires=(1, 1, 1), lift=0, foot=.12):
    return {"frame": frame, "body_scale": list(scale), "body_rotation": list(rotation),
            "body_offset": list(offset), "trunk_rotation": [trunk, 0, 0],
            "tire_scale": list(tires), "tire_offset": [0, lift, 0], "foot_offset": [0, foot, .2]}


def clip(name, frames, keys, description, loop=False):
    assert keys[0]["frame"] == 0 and keys[-1]["frame"] == frames
    CLIPS[name] = {"frames": frames, "loop": loop, "description": description, "keys": keys}


clip("RESET", 1, [pose(0), pose(1)], "Neutral bind pose.")
clip("idle", 12, [pose(0), pose(3, scale=(1, .997, 1)), pose(6),
                  pose(9, scale=(1, 1.003, 1)), pose(12)], "Very small engine rumble.", True)
clip("drive", 12, [pose(0), pose(3, rotation=(.25, 0, .18), offset=(0, .007, 0)),
                   pose(6), pose(9, rotation=(-.2, 0, -.18), offset=(0, .004, 0)),
                   pose(12)], "Restrained road rhythm beneath smooth travel.", True)
clip("accelerate", 7, [pose(0), pose(1, scale=(1.02, .95, 1.01), rotation=(2.5, 0, 0)),
                       pose(2, scale=(.98, 1.05, .99), rotation=(6.0, 0, 0), tires=(1, .97, 1)),
                       pose(3, scale=(.993, 1.025, 1), rotation=(4.2, 0, 0)),
                       pose(5, rotation=(2.0, 0, 0)), pose(7, rotation=(1.2, 0, 0))],
     "Rear-loaded anticipation, nose lift, and settle.")
clip("brake", 7, [pose(0), pose(1, scale=(1.055, .89, 1.015), rotation=(-6.0, 0, 0), tires=(1.03, .92, 1)),
                  pose(2, scale=(1.045, .91, 1.01), rotation=(-4.8, 0, 0), trunk=-2, tires=(1.02, .94, 1)),
                  pose(3, scale=(.992, 1.025, 1), rotation=(1.0, 0, 0), trunk=-1),
                  pose(5, scale=(1.02, .97, 1), rotation=(-2.5, 0, 0)),
                  pose(7, scale=(1.015, .98, 1), rotation=(-2.0, 0, 0))],
     "Nose dip, one short rebound, and a loaded stance while braking is held.")
clip("recover", 5, [pose(0), pose(1, scale=(.997, 1.025, 1)), pose(3, scale=(1.006, .987, 1)), pose(5)],
     "Small overshoot when the driver releases a maneuver.")

for direction, sign in (("left", -1), ("right", 1)):
    for variant, lean, anticipation in (("a", 9.0, 1.2), ("b", 9.5, .8), ("c", 8.7, 1.5)):
        clip(f"turn_{direction}_{variant}", 8,
             [pose(0), pose(1, rotation=(0, 0, -sign * anticipation)),
              pose(2, scale=(1.018, .98, 1), rotation=(-.8, -sign * 1.5, sign * (lean + 2))),
              pose(4, scale=(1.008, .995, 1), rotation=(.4, -sign * .8, sign * (lean - .6)), trunk=-.7),
              pose(6, rotation=(0, -sign * .6, sign * lean)),
              pose(8, rotation=(0, -sign * .6, sign * lean))],
             f"{direction.title()} turn with a bounded {variant.upper()} anticipation and overshoot.")
    clip(f"turn_{direction}_hold", 12,
         [pose(0, rotation=(0, -sign * .6, sign * 9)),
          pose(4, rotation=(.3, -sign * .7, sign * 9.25), trunk=-.5),
          pose(8, rotation=(-.2, -sign * .5, sign * 8.85)),
          pose(12, rotation=(0, -sign * .6, sign * 9))], "Small loaded-body drift through a held turn.", True)
    clip(f"handbrake_{direction}", 8,
         [pose(0), pose(1, scale=(1.04, .92, 1), rotation=(-1.8, -sign * 4, sign * 8)),
          pose(3, scale=(1.045, .94, 1.01), rotation=(-1, -sign * 8, sign * 11), trunk=-2),
          pose(5, scale=(1.01, .99, 1), rotation=(.5, -sign * 6, sign * 9)),
          pose(8, rotation=(0, -sign * 6, sign * 9), trunk=-1)],
         "Rear steps out while the chassis loads the outside tires.")

clip("launch", 6,
     [pose(0, scale=(1.11, .74, 1.035), tires=(1.06, .78, 1.02), foot=-.22),
      pose(1, scale=(.92, 1.25, .965), rotation=(5, 0, 0), lift=-.035, foot=-.10),
      pose(2, scale=(.96, 1.15, .98), rotation=(6, 0, 0), lift=-.07),
      pose(4, scale=(.98, 1.07, .99), rotation=(4, 0, 0), lift=-.06),
      pose(6, scale=(.98, 1.05, .99), rotation=(3, 0, 0), lift=-.045)],
     "One-frame compression, a tall release silhouette, and trailing wheels.")
clip("air_rise", 8,
     [pose(0, scale=(.98, 1.05, .99), rotation=(3, 0, 0), lift=-.045),
      pose(4, scale=(.98, 1.07, .99), rotation=(4, 0, .3), trunk=-1, lift=-.06),
      pose(8, scale=(.98, 1.05, .99), rotation=(3, 0, 0), lift=-.045)], "Light stretched rise with wheels trailing underneath.", True)
clip("air_hang", 6,
     [pose(0, scale=(1.025, .98, 1.015), rotation=(.8, 0, 0), trunk=-5, lift=-.035),
      pose(3, scale=(1.04, .96, 1.025), rotation=(-.7, 0, .4), trunk=-8, lift=-.05),
      pose(6, scale=(1.025, .98, 1.015), rotation=(.8, 0, 0), trunk=-5, lift=-.035)],
     "A broad apex silhouette before the body tips into the fall.", True)
clip("air_drop", 8,
     [pose(0, scale=(.98, 1.07, .985), rotation=(-3, 0, 0), trunk=-14, lift=-.065),
      pose(2, scale=(.97, 1.09, .98), rotation=(-4.4, 0, .4), trunk=-18, lift=-.08),
      pose(4, scale=(.975, 1.08, .982), rotation=(-4, 0, -.3), trunk=-16, lift=-.07),
      pose(6, scale=(.98, 1.07, .985), rotation=(-3.4, 0, .2), trunk=-17, lift=-.065),
      pose(8, scale=(.98, 1.07, .985), rotation=(-3, 0, 0), trunk=-14, lift=-.065)],
     "Trunk lifts during descent; its small flutter is held in drawn poses.", True)

for level, count, depth, spread, rebound, length in (
    ("soft", 2, .86, 1.06, 1.045, 7),
    ("medium", 3, .69, 1.13, 1.09, 9),
    ("hard", 3, .49, 1.23, 1.15, 11),
):
    for index in range(count):
        letter = "abc"[index]
        variation = (index - (count - 1) * .5)
        d = depth + variation * .018
        w = spread + variation * .009
        rot = variation * .7
        clip(f"land_{level}_{letter}", length,
             [pose(0, scale=(w - .025, d + .045, .96), rotation=(0, 0, rot), trunk=0,
                   tires=(w - .04, d + .045, .96)),
              pose(1, scale=(w, d, .945), rotation=(0, 0, rot), trunk=0,
                   tires=(w - .035, d, .945)),
              pose(2, scale=(w, d, .945), rotation=(0, 0, rot * .8), trunk=-1.2,
                   tires=(w - .035, d, .945)),
              pose(3, scale=(1.035, .93, 1.00), trunk=-2.5, tires=(1.025, .94, 1)),
              pose(4, scale=(.965, rebound, 1.015), rotation=(.7, 0, -rot * .5), trunk=-3.5,
                   tires=(.99, 1.015, 1)),
              pose(5, scale=(.988, 1.045, 1.005), trunk=-.8),
              pose(6, scale=(1.012, .975, .997), trunk=0),
              pose(length)],
             f"{level.title()} impact {letter.upper()}: contact, two held compression poses, rebound, and trunk latch.")

for variant, roll in (("a", 1.7), ("b", -1.7)):
    clip("crash_" + variant, 12,
         [pose(0, scale=(1.16, .72, .84), rotation=(-4, 0, roll), trunk=-3, tires=(1.08, .8, .91)),
          pose(1, scale=(1.19, .65, .82), rotation=(-5, 0, roll * 1.4), trunk=-16, tires=(1.09, .73, .91)),
          pose(3, scale=(1.07, 1.02, .94), rotation=(2, 0, -roll), trunk=-8),
          pose(5, scale=(1.04, .92, .96), rotation=(-1, 0, roll * .5), trunk=-3),
          pose(8, scale=(1.01, .98, .995), trunk=-.5), pose(12)],
         "Short accordion impact with a sprung trunk and a stable settled car.")

def death_pose(frame, damage=(0, 0, 0), **kwargs):
    value = pose(frame, **kwargs)
    value["damage"] = list(damage)  # left side, right side, nose; shader deformation only
    return value


clip("crash_front", 20,
     [death_pose(0), death_pose(1, rotation=(-2, 0, 0)),
      death_pose(2, damage=(0, 0, 1), scale=(1.16, .63, .84), rotation=(-4, 0, 0),
                 offset=(0, .01, -.54), trunk=-18, tires=(1.10, .69, .92)),
      death_pose(3, damage=(0, 0, 1), scale=(1.16, .63, .84), rotation=(-4, 0, 0),
                 offset=(0, .01, -.54), trunk=-23, tires=(1.10, .69, .92)),
      death_pose(4, damage=(0, 0, .70), scale=(.99, 1.10, .94), rotation=(4, 0, 0),
                 offset=(0, .08, -.28), trunk=-15, lift=.025),
      death_pose(6, damage=(0, 0, .82), scale=(1.07, .83, .91), rotation=(-1.5, 0, 0),
                 offset=(0, 0, -.38), trunk=-5, tires=(1.03, .91, .97)),
      death_pose(8, damage=(0, 0, .80), scale=(1.03, .91, .92),
                 offset=(0, 0, -.39), trunk=-2, tires=(1.02, .94, .98)),
      death_pose(20, damage=(0, 0, .80), scale=(1.03, .91, .92),
                 offset=(0, 0, -.39), trunk=-2, tires=(1.02, .94, .98))],
     "Front wall: broad held squash, sprung trunk, one sharp rebound, then a shortened red wreck.")

for side, sign, dent in (("left", 1, (1, 0, 0)), ("right", -1, (0, 1, 0))):
    d = lambda value: tuple(value * x for x in dent)
    clip("crash_" + side, 20,
         [death_pose(0), death_pose(1, rotation=(0, 0, sign * 3)),
          death_pose(2, damage=dent, scale=(.88, .68, 1.08), rotation=(0, -sign * 3, sign * 11),
                     offset=(-sign * .22, .025, 0), trunk=-17, tires=(1.05, .76, 1)),
          death_pose(3, damage=dent, scale=(.88, .68, 1.08), rotation=(0, -sign * 3, sign * 11),
                     offset=(-sign * .22, .025, 0), trunk=-21, tires=(1.05, .76, 1)),
          death_pose(4, damage=d(.68), scale=(1.025, 1.07, .99), rotation=(0, sign * 1.5, -sign * 5),
                     offset=(sign * .15, .06, .06), trunk=-12, lift=.02),
          death_pose(6, damage=d(.78), scale=(.96, .88, 1.03), rotation=(0, 0, sign * 3),
                     offset=(-sign * .08, 0, .03), trunk=-4, tires=(1, .93, 1)),
          death_pose(9, damage=d(.76), scale=(.97, .93, 1.02), rotation=(0, 0, sign * 1.5),
                     offset=(-sign * .10, 0, .03), trunk=-2, tires=(1, .96, 1)),
          death_pose(20, damage=d(.76), scale=(.97, .93, 1.02), rotation=(0, 0, sign * 1.5),
                     offset=(-sign * .10, 0, .03), trunk=-2, tires=(1, .96, 1))],
         f"{side.title()} wall: held sideways squash, outside suspension kicks, body snaps back and settles.")

clip("explode", 36,
     [death_pose(0), death_pose(2, scale=(1.06, .87, 1.035), trunk=-3, tires=(1.025, .91, 1)),
      death_pose(3, scale=(1.09, .77, 1.05), trunk=-5, tires=(1.045, .84, 1)),
      death_pose(4, scale=(1.09, .77, 1.05), trunk=-5, tires=(1.045, .84, 1)),
      death_pose(5, scale=(1.14, .68, 1.06), trunk=-8, tires=(1.06, .74, 1)),
      death_pose(6, scale=(.92, 1.25, .96), offset=(0, .55, 0), rotation=(3, 0, -3), trunk=-24),
      death_pose(7, scale=(.97, 1.14, 1.02), offset=(0, .72, 0), rotation=(5, 0, -4), trunk=-24),
      death_pose(9, scale=(1.04, .97, 1.03), offset=(0, .39, 0), rotation=(-3, 0, 2), trunk=-17),
      death_pose(11, scale=(1.20, .48, 1.06), trunk=0),
      death_pose(12, scale=(1.20, .48, 1.06), trunk=0),
      death_pose(14, scale=(1.09, .69, 1.02), offset=(0, .04, 0), trunk=-5),
      death_pose(17, scale=(1.13, .59, 1.04), trunk=-2),
      death_pose(36, scale=(1.13, .59, 1.04), trunk=-2)],
     "Standalone explosion: pressure squeeze, booster-style flame burst, wheels pop loose, red body slaps down into a flat wreck.")

TARGET.write_text(json.dumps({"pose_fps": 12, "clips": CLIPS}, indent=2) + "\n")
print(f"LOWCAR_POSES_AUTHORED: {len(CLIPS)} clips at 12 FPS")
