"""Package native Godot renders of the four new red-car death animations."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT.parents[1] / "work/car_death_frames"
DEST = PROJECT / "assets/models/vehicles/red_muscle_car/animation_previews"
DEST.mkdir(parents=True, exist_ok=True)
labels = {"crash_front": "FRONT WALL", "crash_left": "LEFT WALL",
          "crash_right": "RIGHT WALL", "explode": "STANDALONE EXPLOSION"}
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 23)
small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
clips = {}
metadata = json.loads((SOURCE / "frames.json").read_text())


def save_gif(frames, target, hold=0):
    swatches = Image.new("RGB", (frames[0].width, frames[0].height * 4))
    for i, index in enumerate([0, len(frames) // 4, len(frames) // 2, len(frames) - 1]):
        swatches.paste(frames[index], (0, i * frames[0].height))
    palette = swatches.quantize(colors=224)
    images = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    durations = [80 if i % 3 != 2 else 90 for i in range(len(frames))]
    durations[-1] += hold
    images[0].save(target, save_all=True, append_images=images[1:], duration=durations,
                   loop=0, disposal=2, optimize=False)


for clip, label in labels.items():
    entries = [item for item in metadata if item["clip"] == clip]
    frames = []
    for item in entries:
        frame = Image.open(SOURCE / f'{clip}_{item["frame"]:02d}.png').convert("RGB").resize((960, 600), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(frame)
        draw.rounded_rectangle((16, 16, 425, 81), radius=9, fill="#203548")
        draw.text((31, 25), label, font=font, fill="#fff0d6")
        draw.text((31, 54), "LOWCAR / 12 FPS HELD POSES", font=small, fill="#fac078")
        frames.append(frame)
    clips[clip] = frames
    save_gif(frames, DEST / (clip + ".gif"), 500)

montage = []
for i in range(37):
    canvas = Image.new("RGB", (1312, 880), "#203548")
    draw = ImageDraw.Draw(canvas)
    for panel, (clip, label) in enumerate(labels.items()):
        x, y = 8 + (panel % 2) * 656, 8 + (panel // 2) * 436
        source_frame = min(i, len(clips[clip]) - 1)
        # Raw native renders avoid stacking labels at the two preview sizes.
        image = Image.open(SOURCE / f'{clip}_{source_frame:02d}.png').convert("RGB").resize((640, 400), Image.Resampling.LANCZOS)
        canvas.paste(image, (x, y + 29))
        draw.text((x + 9, y + 2), label, font=font, fill="#fff0d6")
    montage.append(canvas)
save_gif(montage, DEST / "four_death_animations.gif", 500)
montage[9].save(DEST / "death_animations_contact_sheet.png")
manifest = {"renderer": "Godot 4.7 Compatibility / native viewport", "pose_fps": 12,
            "clips": {name: len(frames) for name, frames in clips.items()},
            "fragment_count": 4, "native_frames": len(metadata),
            "fire_style": "BoostExhaust six-sided orange tongues with cream cores; 12 FPS",
            "source": "resources/animation/car_clips.json",
            "library": "resources/animation/car_animation_pack.tres"}
(DEST / "death_preview_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("LOWCAR_DEATH_PREVIEWS_PACKAGED", json.dumps(manifest))
