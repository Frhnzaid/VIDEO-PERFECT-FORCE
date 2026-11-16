"""Rebuild a clean, flat-colour Perfect Emerald logo from the old video intro.

    python pfc_edit/clean_logo.py frames_dir out_dir

frames_dir holds PNG crops of the static logo (black background). The frames
are averaged to remove compression noise, upscaled, and every pixel is snapped
to the nearest brand colour (red / teal / navy) with a soft alpha edge, which
drops the glow halo. Two files are written:
  logo_full.png      navy kept   (for light backgrounds)
  logo_reverse.png   navy->white (for the dark navy intro/outro)
"""
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

RED = np.array([216, 38, 47])
TEAL = np.array([59, 179, 164])
NAVY = np.array([27, 31, 107])
WHITE = np.array([244, 246, 248])
SCALE = 3


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def main(frames_dir, out_dir):
    files = sorted(glob.glob(os.path.join(frames_dir, "*.png")))
    acc = None
    for f in files:
        a = np.asarray(Image.open(f).convert("RGB")).astype(np.float64)
        acc = a if acc is None else acc + a
    img = acc / len(files)
    h, w, _ = img.shape
    big = np.asarray(Image.fromarray(img.clip(0, 255).astype(np.uint8)).resize(
        (w * SCALE, h * SCALE), Image.LANCZOS)).astype(np.float64)
    r, g, b = big[..., 0], big[..., 1], big[..., 2]

    # colour masks from channel dominance (robust against the soft glow)
    red_m = smoothstep(25, 60, r - np.maximum(g, b)) * smoothstep(70, 110, r)
    teal_m = smoothstep(15, 45, g - r) * smoothstep(70, 105, g)
    navy_m = smoothstep(14, 30, b - np.maximum(r, g)) * smoothstep(40, 60, b) * (1 - teal_m)
    masks = np.stack([red_m, teal_m, navy_m])
    # light blur then sharpen the alpha edge for clean anti-aliasing
    sm = []
    for m, radius in zip(masks, (1.2, 1.2, 2.6)):  # thin navy strokes are noisier
        im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
        sm.append(smoothstep(0.35, 0.65, np.asarray(im) / 255.0))
    masks = np.stack(sm)
    alpha = masks.max(0)
    which = masks.argmax(0)

    ys, xs = np.where(alpha > 0.05)
    pad = 8 * SCALE
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, alpha.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, alpha.shape[1])

    os.makedirs(out_dir, exist_ok=True)
    for name, navy_col in (("logo_full.png", NAVY), ("logo_reverse.png", WHITE)):
        pal = np.stack([RED, TEAL, navy_col])
        rgb = pal[which]
        out = np.dstack([rgb, alpha * 255]).astype(np.uint8)[y0:y1, x0:x1]
        Image.fromarray(out).save(os.path.join(out_dir, name))
        print("wrote", os.path.join(out_dir, name), out.shape)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
