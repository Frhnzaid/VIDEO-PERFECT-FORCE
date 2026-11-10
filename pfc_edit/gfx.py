"""Motion graphics for the Perfect Force Clamp client video.

Every graphic is a pure function of time (seconds since the graphic started)
that draws onto a 3840x2160 skia canvas. Nothing here touches the footage.
"""
import math
import os

import numpy as np
import skia

W, H = 3840, 2160
FPS = 24

# ---------------------------------------------------------------- brand ----
# Sampled from the Perfect Emerald logo in the source video, then lifted to
# clean, saturated values that hold up on screen.
NAVY = 0xFF0B1238        # deep navy  (logo outline)
NAVY_DEEP = 0xFF050820
RED = 0xFFD8262F         # PE red     (the "P")
TEAL = 0xFF3BB3A4        # emerald    (the "E")
TEAL_LIGHT = 0xFF6FD3C6
WHITE = 0xFFF4F6F8
STEEL = 0xFF9AA4B8

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.environ.get("PFC_FONT_DIR", os.path.join(HERE, "fonts"))
_tf_cache = {}


def typeface(name):
    if name not in _tf_cache:
        tf = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, name))
        if tf is None:
            raise FileNotFoundError(os.path.join(FONT_DIR, name))
        _tf_cache[name] = tf
    return _tf_cache[name]


def font(kind, size):
    files = {
        "cond_bold": "barlow-condensed-latin-700-normal.woff",
        "cond_semi": "barlow-condensed-latin-600-normal.woff",
        "cond_med": "barlow-condensed-latin-500-normal.woff",
        "bold": "barlow-latin-700-normal.woff",
        "semi": "barlow-latin-600-normal.woff",
        "med": "barlow-latin-500-normal.woff",
        "reg": "barlow-latin-400-normal.woff",
    }
    f = skia.Font(typeface(files[kind]), size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


# --------------------------------------------------------------- easing ----
def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def prog(t, a, b):
    """0..1 progress of t across [a, b]."""
    return clamp01((t - a) / (b - a)) if b > a else float(t >= a)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_in_out_cubic(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_expo(x):
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def ease_in_cubic(x):
    return x ** 3


def with_alpha(color, a):
    a = clamp01(a)
    return ((int(((color >> 24) & 0xFF) * a)) << 24) | (color & 0x00FFFFFF)


def paint(color, alpha=1.0, stroke=None, cap=skia.Paint.kRound_Cap):
    p = skia.Paint(AntiAlias=True, Color=with_alpha(color, alpha))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(cap)
    return p


# ---------------------------------------------------------------- text -----
def text_width(txt, f, tracking=0.0):
    if not txt:
        return 0.0
    return f.measureText(txt) + tracking * (len(txt) - 1)


def draw_text(c, txt, x, y, f, color, alpha=1.0, tracking=0.0, align="left",
              shadow=False):
    """Draw text with letter-spacing. y is the baseline."""
    w = text_width(txt, f, tracking)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    p = paint(color, alpha)
    if shadow:
        p.setImageFilter(skia.ImageFilters.DropShadow(
            0, 6, 14, 14, with_alpha(0xFF000000, 0.55 * alpha)))
    if tracking == 0:
        c.drawString(txt, x, y, f, p)
        return w
    cx = x
    for ch in txt:
        c.drawString(ch, cx, y, f, p)
        cx += f.measureText(ch) + tracking
    return w


# ------------------------------------------------------------ background ---
def brand_background(c, t):
    """Deep navy field with a slowly drifting hairline pattern."""
    shader = skia.GradientShader.MakeRadial(
        skia.Point(W * 0.5, H * 0.46), W * 0.72,
        [0xFF18245E, 0xFF0B1238, NAVY_DEEP], [0.0, 0.55, 1.0])
    c.drawRect(skia.Rect(0, 0, W, H), skia.Paint(Shader=shader))
    # diagonal hairlines
    p = paint(WHITE, 0.035, stroke=2, cap=skia.Paint.kButt_Cap)
    drift = (t * 40) % 140
    for i in range(-30, 60):
        x = i * 140 + drift
        c.drawLine(x, 0, x - H * 0.58, H, p)
    # corner accents
    c.drawRect(skia.Rect(0, 0, W, 10), paint(TEAL, 0.9))
    c.drawRect(skia.Rect(0, 0, 360, 10), paint(RED, 1.0))


def load_logo(path):
    if not path or not os.path.exists(path):
        return None
    return skia.Image.open(path)


def draw_logo(c, logo, cx, cy, width, alpha):
    if logo is None or alpha <= 0:
        return
    h = width * logo.height() / logo.width()
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp01(alpha))
    c.drawImageRect(logo, skia.Rect.MakeXYWH(cx - width / 2, cy - h / 2, width, h),
                    skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear), p)


# ----------------------------------------------------------------- intro ---
def intro(c, t, dur, logo=None, title="PERFECT FORCE CLAMP",
          tagline="HOT BOLTING SOLUTION", company="PERFECT EMERALD SDN. BHD."):
    brand_background(c, t)
    cy = 1150  # divider line

    # divider line grows from centre
    k = ease_out_expo(prog(t, 0.15, 1.1))
    half = 1250 * k
    c.drawRect(skia.Rect(W / 2 - half, cy - 4, W / 2 + half, cy + 4), paint(TEAL))
    if k > 0:
        red_w = 220 * ease_out_cubic(prog(t, 0.6, 1.2))
        c.drawRect(skia.Rect(W / 2 - half, cy - 4, W / 2 - half + red_w, cy + 4), paint(RED))

    # title rises from behind the line
    ft = font("cond_bold", 290)
    rise = 1 - ease_out_expo(prog(t, 0.45, 1.45))
    c.save()
    c.clipRect(skia.Rect(0, 0, W, cy - 6))
    base_y = cy - 70 + rise * 330
    c.saveLayer()
    draw_text(c, title, W / 2, base_y, ft, WHITE, tracking=18, align="center")
    # light sweep across the title
    s = prog(t, 2.2, 3.3)
    if 0 < s < 1:
        gx = -800 + s * (W + 1600)
        sh = skia.GradientShader.MakeLinear(
            [skia.Point(gx - 380, 0), skia.Point(gx + 380, 0)],
            [0x00FFFFFF, 0x99BFF5EE, 0x00FFFFFF], [0.0, 0.5, 1.0])
        sp = skia.Paint(Shader=sh)
        sp.setBlendMode(skia.BlendMode.kSrcATop)
        c.drawRect(skia.Rect(0, 0, W, H), sp)
    c.restore()
    c.restore()

    # tagline drops from behind the line
    fg = font("semi", 84)
    drop = 1 - ease_out_expo(prog(t, 1.15, 2.0))
    c.save()
    c.clipRect(skia.Rect(0, cy + 6, W, H))
    draw_text(c, tagline, W / 2, cy + 150 - drop * 170, fg, TEAL_LIGHT,
              tracking=30, align="center")
    c.restore()

    # logo + company
    a = ease_out_cubic(prog(t, 1.8, 2.7))
    draw_logo(c, logo, W / 2, 610 - (1 - a) * 30, 900, a)
    fc = font("med", 46)
    draw_text(c, company, W / 2, 1960, fc, STEEL, alpha=ease_out_cubic(prog(t, 2.3, 3.1)),
              tracking=14, align="center")


# ------------------------------------------------------------------ wipe ---
def wipe(c, t, dur):
    """Branded diagonal wipe. Screen is fully covered at t = dur/2."""
    x = ease_in_out_cubic(prog(t, 0, dur))
    skew = H * math.tan(math.radians(16))
    slab = W * 1.5
    left = -1.75 * W + x * 3.0 * W  # -0.25W at midpoint

    def slab_path(l):
        pth = skia.Path()
        pth.moveTo(l + skew, 0)
        pth.lineTo(l + skew + slab, 0)
        pth.lineTo(l + slab, H)
        pth.lineTo(l, H)
        pth.close()
        return pth

    c.drawPath(slab_path(left + 190), paint(RED))
    c.drawPath(slab_path(left + 110), paint(TEAL))
    c.drawPath(slab_path(left), paint(NAVY))
    # small mark on the slab while it covers the frame
    a = 1 - abs(x - 0.5) * 6
    if a > 0:
        c.drawRect(skia.Rect(W / 2 - 90, H / 2 - 4, W / 2 + 90, H / 2 + 4), paint(TEAL, a))


# ------------------------------------------------------------ lower third --
def lower_third(c, t, dur, kicker, title, sub=None):
    out_t = dur - 0.55
    o = ease_in_cubic(prog(t, out_t, dur))  # 0 -> 1 while leaving
    x0, yb = 170, 1880
    ph = 250 if not sub else 300
    yt = yb - ph

    fk = font("cond_semi", 60)
    ft = font("cond_bold", 118)
    fs = font("med", 50)
    tw = max(text_width(kicker, fk, 10), text_width(title, ft, 4),
             text_width(sub or "", fs, 2))
    pw_full = tw + 150

    # red bar grows upward
    bh = ph * ease_out_cubic(prog(t, 0.0, 0.35)) * (1 - o)
    c.drawRect(skia.Rect(x0, yb - bh, x0 + 16, yb), paint(RED))

    # panel extends to the right
    pw = pw_full * ease_out_expo(prog(t, 0.18, 0.8)) * (1 - ease_in_out_cubic(prog(t, out_t - 0.05, dur - 0.1)))
    if pw > 1:
        rect = skia.Rect(x0 + 16, yt, x0 + 16 + pw, yb)
        sp = paint(0xFF000000, 0.35)
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
        c.drawRect(rect.makeOffset(0, 12), sp)
        c.drawRect(rect, paint(NAVY, 0.86))
        c.drawRect(skia.Rect(x0 + 16, yb - 6, x0 + 16 + pw, yb), paint(TEAL, 0.95))
        c.save()
        c.clipRect(rect)
        ak = ease_out_cubic(prog(t, 0.45, 0.9))
        draw_text(c, kicker, x0 + 80 - (1 - ak) * 60, yt + 92, fk, TEAL_LIGHT,
                  alpha=ak, tracking=10)
        at = ease_out_cubic(prog(t, 0.55, 1.05))
        draw_text(c, title, x0 + 76 - (1 - at) * 90, yt + 210, ft, WHITE,
                  alpha=at, tracking=4)
        if sub:
            asub = ease_out_cubic(prog(t, 0.7, 1.2))
            draw_text(c, sub, x0 + 80 - (1 - asub) * 60, yt + 272, fs, STEEL,
                      alpha=asub, tracking=2)
        c.restore()


# --------------------------------------------------------------- callout ---
def callout(c, t, dur, cx, cy, r, label, side="right", rise=260, run=300):
    """Circle highlight + leader line + label tag."""
    fade = 1 - prog(t, dur - 0.4, dur)
    if fade <= 0:
        return
    c.saveLayer(None, skia.Paint(Alphaf=fade))
    shadow = skia.ImageFilters.DropShadow(0, 4, 10, 10, 0x99000000)

    # circle draws on
    k = ease_out_cubic(prog(t, 0.0, 0.55))
    ring = paint(TEAL, stroke=11)
    ring.setImageFilter(shadow)
    if k > 0:
        pth = skia.Path()
        pth.addArc(skia.Rect(cx - r, cy - r, cx + r, cy + r), -90, 359.9 * k)
        c.drawPath(pth, ring)
    # pulse rings
    if t > 0.55:
        ph = ((t - 0.55) % 1.6) / 1.6
        rr = r * (1 + 0.28 * ease_out_cubic(ph))
        c.drawCircle(cx, cy, rr, paint(TEAL_LIGHT, 0.55 * (1 - ph), stroke=6))

    # leader line
    sgn = 1 if side == "right" else -1
    ang = math.radians(-45)
    sx, sy = cx + sgn * r * math.cos(ang), cy + r * math.sin(ang)
    ex, ey = sx + sgn * rise, sy - rise
    fx = ex + sgn * run
    l1 = ease_out_cubic(prog(t, 0.4, 0.75))
    l2 = ease_out_cubic(prog(t, 0.7, 1.0))
    lp = paint(WHITE, stroke=7)
    lp.setImageFilter(shadow)
    if l1 > 0:
        pth = skia.Path()
        pth.moveTo(sx, sy)
        pth.lineTo(sx + (ex - sx) * l1, sy + (ey - sy) * l1)
        if l2 > 0:
            pth.lineTo(ex + (fx - ex) * l2, ey)
        c.drawPath(pth, lp)
        c.drawCircle(sx, sy, 12, paint(WHITE))

    # label
    a = ease_out_expo(prog(t, 0.95, 1.5))
    if a > 0:
        f = font("cond_bold", 84)
        tw = text_width(label, f, 6)
        bw, bh = (tw + 110) * a, 132
        lx = fx if sgn > 0 else fx - bw
        rect = skia.Rect(lx, ey - bh / 2, lx + bw, ey + bh / 2)
        bp = paint(NAVY, 0.9)
        bp.setImageFilter(shadow)
        c.drawRect(rect, bp)
        tab = skia.Rect(lx, rect.top(), lx + 14, rect.bottom()) if sgn > 0 else \
            skia.Rect(rect.right() - 14, rect.top(), rect.right(), rect.bottom())
        c.drawRect(tab, paint(RED))
        c.save()
        c.clipRect(rect)
        tx = lx + 62 if sgn > 0 else rect.right() - 48 - tw
        draw_text(c, label, tx, ey + 30, f, WHITE, alpha=prog(t, 1.1, 1.45), tracking=6)
        c.restore()
    c.restore()


# ----------------------------------------------------------------- outro ---
def outro(c, t, dur, logo=None, contact=None):
    brand_background(c, t + 10)
    a = lambda s, e: ease_out_cubic(prog(t, s, e))
    draw_logo(c, logo, W / 2, 430, 760, a(0.1, 0.9))
    ft = font("cond_bold", 230)
    draw_text(c, "PERFECT FORCE CLAMP", W / 2, 980 - (1 - a(0.3, 1.1)) * 40, ft, WHITE,
              alpha=a(0.3, 1.1), tracking=14, align="center")
    k = ease_out_expo(prog(t, 0.6, 1.4))
    c.drawRect(skia.Rect(W / 2 - 900 * k, 1050, W / 2 + 900 * k, 1058), paint(TEAL))
    c.drawRect(skia.Rect(W / 2 - 900 * k, 1050, W / 2 - 900 * k + 200 * k, 1058), paint(RED))
    draw_text(c, "HOT BOLTING SOLUTION", W / 2, 1180, font("semi", 76), TEAL_LIGHT,
              alpha=a(0.9, 1.6), tracking=26, align="center")
    draw_text(c, "PERFECT EMERALD SDN. BHD.", W / 2, 1400, font("bold", 84), WHITE,
              alpha=a(1.3, 2.0), tracking=10, align="center")
    contact = contact or ["Tel: [ +60 X-XXXX XXXX ]", "Email: [ email@company.com ]",
                          "Web: [ www.website.com ]"]
    fc = font("med", 58)
    y = 1600
    for i, line in enumerate(contact):
        draw_text(c, line, W / 2, y + i * 100, fc, STEEL, alpha=a(1.7 + i * 0.15, 2.4 + i * 0.15),
                  tracking=4, align="center")
    # fade to black at the very end
    fb = prog(t, dur - 0.8, dur)
    if fb > 0:
        c.drawRect(skia.Rect(0, 0, W, H), paint(0xFF000000, fb))


# -------------------------------------------------------------- renderer ---
def render_frames(fn, dur, opaque=False, **kw):
    """Yield RGBA uint8 frames (H, W, 4) for a graphic function."""
    surface = skia.Surface(W, H)
    n = int(round(dur * FPS))
    for i in range(n):
        t = i / FPS
        c = surface.getCanvas()
        c.clear(0xFF000000 if opaque else 0x00000000)
        fn(c, t, dur, **kw)
        img = surface.makeImageSnapshot()
        yield img.toarray(colorType=skia.kRGBA_8888_ColorType,
                          alphaType=skia.kUnpremul_AlphaType)


def still(fn, t, dur, path, opaque=False, bg=None, **kw):
    surface = skia.Surface(W, H)
    c = surface.getCanvas()
    c.clear(0xFF000000 if opaque else 0x00000000)
    if bg is not None:
        c.drawImage(bg, 0, 0)
    fn(c, t, dur, **kw)
    surface.makeImageSnapshot().save(path, skia.kPNG)
