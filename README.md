# VIDEO-PERFECT-FORCE

Client edit of the Perfect Force Clamp (PFC) demo video — Perfect Emerald Sdn. Bhd.

## Pipeline
- `pfc_edit/gfx.py` – motion graphics (intro, lower-thirds, callouts, branded wipe, outro), drawn with skia at 3840x2160.
- `pfc_edit/timeline.py` – edit decision lists (`preview`, `full`).
- `pfc_edit/pfc3d.py` – Blender (bpy) 3D how-it-works animation: flanged joint, PFC rings and stud bolts, live line.
- `pfc_edit/clean_logo.py` – rebuilds a clean flat-colour logo from the old intro frames.
- `pfc_edit/build.py` – renders graphics, grades footage (crop letterbox → UHD, contrast/WB/sharpen) and assembles with ffmpeg. Never writes to the source file.

```
pip install skia-python numpy        # needs libegl1 on Linux
python pfc_edit/build.py preview --src pfc_demo.mp4 --out output/pfc_preview.mp4 --logo logo.png
pip install bpy   # Blender as a Python module
python pfc_edit/pfc3d.py --out work/3d --res 1600x900 --engine CYCLES --samples 12   # ~5 h on 4 CPU cores
python pfc_edit/build.py full    --src pfc_demo.mp4 --out output/pfc_demo_client.mp4 --frames3d work/3d
python pfc_edit/build.py full2d  --src pfc_demo.mp4 --out output/pfc_demo_client_2d.mp4   # 2D explainer version
```

Fonts: Barlow / Barlow Condensed (SIL OFL, see `pfc_edit/fonts/OFL-LICENSE.txt`).
