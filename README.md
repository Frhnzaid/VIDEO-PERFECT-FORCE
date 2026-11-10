# VIDEO-PERFECT-FORCE

Client edit of the Perfect Force Clamp (PFC) demo video — Perfect Emerald Sdn. Bhd.

## Pipeline
- `pfc_edit/gfx.py` – motion graphics (intro, lower-thirds, callouts, branded wipe, outro), drawn with skia at 3840x2160.
- `pfc_edit/timeline.py` – edit decision lists (`preview`, `full`).
- `pfc_edit/build.py` – renders graphics, grades footage (crop letterbox → UHD, contrast/WB/sharpen) and assembles with ffmpeg. Never writes to the source file.

```
pip install skia-python numpy        # needs libegl1 on Linux
python pfc_edit/build.py preview --src pfc_demo.mp4 --out output/pfc_preview.mp4 --logo logo.png
python pfc_edit/build.py full    --src pfc_demo.mp4 --out output/pfc_demo_client.mp4 --logo logo.png
```

Fonts: Barlow / Barlow Condensed (SIL OFL, see `pfc_edit/fonts/OFL-LICENSE.txt`).
