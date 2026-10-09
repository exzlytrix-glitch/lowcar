"""Package the actual native boost replay. Requires Pillow from the bundled runtime."""
from pathlib import Path
import json
from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT.parents[1] / 'work/car_boost_frames'
DEST = PROJECT / 'assets/models/vehicles/red_muscle_car/animation_previews'
metadata = json.loads((SOURCE/'frames.json').read_text())
frames = [Image.open(SOURCE/f'frame_{item["index"]:03d}.png').convert('RGB').resize((960,600),Image.Resampling.LANCZOS) for item in metadata]
palette = Image.new('RGB',(960,1800))
for row,index in enumerate([30,140,148]):
    palette.paste(frames[index],(0,row*600))
palette = palette.quantize(colors=192)
quantized = [frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
quantized[0].save(DEST/'charge_boost.gif',save_all=True,append_images=quantized[1:],duration=[80 if i%3!=2 else 90 for i in range(len(frames))],loop=0,optimize=False,disposal=1)
frames[148].save(DEST/'charge_boost.png')
manifest = {'renderer':'Godot 4.7 Compatibility / actual native chase-camera viewport',
            'frames':len(metadata),'pose_fps':12,'max_charge_seconds':max(x['charge'] for x in metadata),
            'maximum_speed_mps':max(x['speed'] for x in metadata),
            'maximum_flame_length_m':max(x['fire_length'] for x in metadata),
            'all_frames_driving':all(x['run_phase']==1 for x in metadata)}
(DEST/'boost_preview_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('LOWCAR_BOOST_PREVIEW_PACKAGED',json.dumps(manifest))
