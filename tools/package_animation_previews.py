"""Package native Godot captures into a GIF and an impact contact sheet.

Uses Pillow; captures are produced by the Animation Garage's --capture-* modes.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[1]
WORK = PROJECT.parents[1] / 'work'
DEST = PROJECT / 'assets/models/vehicles/red_muscle_car/animation_previews'
DEST.mkdir(parents=True, exist_ok=True)
(DEST/'.gdignore').write_text('')

def gif(folder, name):
    metadata = json.loads((folder/'frames.json').read_text())
    frames = [Image.open(folder/f'frame_{entry["index"]:03d}.png').convert('RGB').resize((960,600),Image.Resampling.LANCZOS) for entry in metadata]
    palette = Image.new('RGB',(960,600*len(frames)))
    for i,frame in enumerate(frames): palette.paste(frame,(0,i*600))
    palette = palette.quantize(colors=192)
    converted = [frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
    # GIF durations are multiples of ten milliseconds: 80/80/90 averages 12 FPS.
    converted[0].save(DEST/name,save_all=True,append_images=converted[1:],duration=[80 if i%3!=2 else 90 for i in range(len(frames))],loop=0,optimize=False,disposal=1)
    return metadata

authored = gif(WORK/'car_animation_frames','animation_pack.gif')
physics = gif(WORK/'car_physics_frames','real_launch_and_landing.gif')
effects = gif(WORK/'car_effects_frames','motion_effects.gif') if (WORK/'car_effects_frames/frames.json').exists() else []
gameplay_effects = gif(WORK/'car_effects_gameplay_frames','motion_effects_gameplay.gif') if (WORK/'car_effects_gameplay_frames/frames.json').exists() else []
polish = gif(WORK/'car_animation_polish_frames','animation_polish.gif') if (WORK/'car_animation_polish_frames/frames.json').exists() else []
fontpath='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
font=ImageFont.truetype(fontpath,24)
small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
canvas=Image.new('RGB',(1500,1000),'#152735')
draw=ImageDraw.Draw(canvas)
draw.text((28,20),'LOWCAR / TRUNK, IMPACT, REBOUND',font=font,fill='#fff0ce')
examples=[('drive',0,'NEUTRAL'),('air_drop',2,'FALL / TRUNK OPENS'),('land_hard_b',1,'IMPACT / 49% HEIGHT'),('land_hard_b',2,'HELD COMPRESSION'),('land_hard_b',4,'REBOUND / 115% HEIGHT'),('recover',4,'RECOVERY')]
for i,(clip,frame,label) in enumerate(examples):
    entry=next(x for x in authored if x['clip']==clip and x['frame']==frame)
    im=Image.open(WORK/'car_animation_frames'/f'frame_{entry["index"]:03d}.png').convert('RGB')
    # Crop only the model stage, excluding the review controls on the right.
    im=im.crop((250,80,850,690)).resize((470,400),Image.Resampling.LANCZOS)
    x=25+(i%3)*495;y=75+(i//3)*460
    canvas.paste(im,(x,y))
    draw.text((x,y+409),label,font=small,fill='#fff0ce')
canvas.save(DEST/'impact_contact_sheet.png')
(DEST/'preview_manifest.json').write_text(json.dumps({'renderer':'Godot 4.7 Compatibility / native viewport','pose_fps':12,'authored_frames':len(authored),'real_physics_frames':len(physics),'real_physics_clip_states':list(dict.fromkeys(x['clip'] for x in physics)),'real_physics_minimum_body_height':min(x['scale_y'] for x in physics),'real_physics_minimum_trunk_degrees':min(x['trunk_degrees'] for x in physics),'motion_effects_frames':len(effects),'motion_effects_gameplay_frames':len(gameplay_effects),'animation_polish_frames':len(polish),'animation_polish_states':list(dict.fromkeys(x['clip'] for x in polish))},indent=2)+'\n')
print('LOWCAR_ANIMATION_PREVIEWS_PACKAGED',json.loads((DEST/'preview_manifest.json').read_text()))
