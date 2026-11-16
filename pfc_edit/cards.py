"""Full-screen cards for the v2 edit: background, problem / solution, safety, references.

All on-screen text below is the client's wording, word for word (titles set in
caps to match the rest of the video). Each beat is one voice-over line; a beat's
text appears when its line starts. Timing comes from the voice-over durations
(see timing()), so the cards always fit the narration.
"""
import math

import skia

from gfx import (BOLT_NEW, H, NAVY, NAVY_DEEP, RED, STEEL, STEEL_LIGHT, STEEL_MID,
                 TEAL, TEAL_DARK, TEAL_LIGHT, W, WHITE, _arrow, brand_background, clamp01,
                 draw_text, ease_in_out_cubic, ease_out_cubic, ease_out_expo, font, paint,
                 prog, text_width, wrap)

DOC_NO = "PESB/WI/2026/XX"   # client to confirm the real document number

CARDS = {
    # ------------------------------------------------------------ background
    "bg1": dict(layout="story", kicker="BACKGROUND", page=1, title="WHY FLANGE BOLTS MATTER",
                diagram="joint", beats=[
        dict(text="Flange joints connect pipes and equipment across oil and gas, power "
                  "generation and chemical plants.",
             vo="Flange joints connect pipes and equipment across oil and gas, power "
                "generation, and chemical plants."),
        dict(text="Their seal depends on the clamping force from the bolts.",
             vo="Their seal depends on the clamping force from the bolts."),
    ]),
    "bg2": dict(layout="story", kicker="BACKGROUND", page=2, title="THE CHALLENGE",
                diagram="shutdown", beats=[
        dict(text="Replacing or tightening flange bolts normally means shutting down part of "
                  "the plant, which brings downtime and financial loss.",
             vo="Replacing or tightening flange bolts normally means shutting down part of "
                "the plant, which brings downtime, and financial loss."),
    ]),
    "bg3": dict(layout="story", kicker="BACKGROUND", page=3, title="HOT BOLTING",
                diagram="hot", beats=[
        dict(text="Hot bolting maintains flange bolts while the line stays in operation.",
             vo="Hot bolting maintains flange bolts while the line stays in operation."),
        dict(text="It is increasingly used in plants that run around the clock, where a "
                  "shutdown costs more than the work itself.",
             vo="It is increasingly used in plants that run around the clock, where a "
                "shutdown costs more than the work itself."),
        dict(text="The flange stays under pressure, so enough clamping force must be kept on "
                  "the joint.",
             vo="The flange stays under pressure, so enough clamping force must be kept on "
                "the joint."),
        dict(text="A temporary, separate load path around the flange makes this possible.",
             vo="A temporary, separate load path around the flange makes this possible."),
    ]),
    "bg4": dict(layout="story", kicker="BACKGROUND", page=4,
                title="HOW THE PERFECT FORCE CLAMP CAME ABOUT", diagram="pfc", beats=[
        dict(text="In daily maintenance, teams often work under tight deadlines, strict "
                  "budgets and an approaching shutdown.",
             vo="In daily maintenance, teams often work under tight deadlines, strict "
                "budgets, and an approaching shutdown."),
        dict(text="That need for a dependable way to replace bolts safely, without waiting "
                  "for the plant to stop, led to the Perfect Force Clamp: a clamp that "
                  "provides the temporary load path while bolts are replaced one at a time.",
             vo="That need for a dependable way to replace bolts safely, without waiting "
                "for the plant to stop, led to the Perfect Force Clamp. A clamp that "
                "provides the temporary load path, while bolts are replaced one at a time."),
    ]),
    # ----------------------------------------------------- problem / solution
    "problem": dict(layout="columns", kicker="PROBLEM STATEMENT", title="THE PROBLEM",
                    tone="red", beats=[
        dict(text=None, vo="The problem."),
        dict(icon="load", text="Bolting left to the shutdown makes the shutdown heavier and "
                               "harder to schedule.",
             vo="Bolting left to the shutdown makes the shutdown heavier, and harder to "
                "schedule."),
        dict(icon="warn", text="Problems found mid-shutdown mean last-minute surprises.",
             vo="Problems found mid-shutdown mean last-minute surprises."),
        dict(icon="clock", text="Waiting for an isolation window costs time and money.",
             vo="Waiting for an isolation window costs time and money."),
    ]),
    "solution": dict(layout="columns", kicker="PERFECT FORCE CLAMP", title="THE SOLUTION",
                     tone="teal", beats=[
        dict(text=None, vo="The solution."),
        dict(icon="flow", text="We replace bolts while the plant keeps running, without "
                               "waiting for a shutdown.",
             vo="We replace bolts while the plant keeps running, without waiting for a "
                "shutdown."),
        dict(icon="record", text="Every joint is verified and logged to give your planners "
                                 "a clear, closed-out record.",
             vo="Every joint is verified and logged, to give your planners a clear, "
                "closed-out record."),
    ]),
    # ---------------------------------------------------------------- safety
    "safety": dict(layout="grid", kicker="HOT BOLTING", title="SAFETY FIRST", beats=[
        dict(text=None, vo="Safety first."),
        dict(icon="permit", text="Client approval and valid work permit required",
             vo="Client approval and valid work permit required."),
        dict(icon="ppe", text="Full PPE: helmet, coverall (flame-resistant where required), "
                              "safety shoes, safety glasses, impact gloves",
             vo="Full P-P-E. Helmet, coverall, flame-resistant where required, safety shoes, "
                "safety glasses, and impact gloves."),
        dict(icon="gauge", text="System pressure not above 75% of flange MAWP (ASME B16.5)",
             vo="System pressure not above seventy-five percent of flange M-A-W-P, "
                "A-S-M-E B sixteen point five."),
        dict(icon="temp", text="System temperature not above 70 °C (158 °F)",
             vo="System temperature not above seventy degrees Celsius, "
                "one hundred and fifty-eight degrees Fahrenheit."),
        dict(icon="bolts48", text="Flanges with 4 or 8 bolts only",
             vo="Flanges with four or eight bolts only."),
        dict(icon="criss", text="One stud bolt at a time, criss-cross pattern",
             vo="One stud bolt at a time, criss-cross pattern."),
        dict(icon="wind", text="Workers positioned upwind",
             vo="Workers positioned upwind."),
        dict(icon="barrier", text="5 m ignition-source barrier, firewatcher and firefighting "
                                  "equipment on standby",
             vo="Five metre ignition-source barrier, firewatcher, and firefighting "
                "equipment on standby."),
        dict(icon="sheet", text="Canvas sheet laid beneath the work area to prevent items "
                                "from falling",
             vo="Canvas sheet laid beneath the work area to prevent items from falling."),
        dict(icon="stages", text="Tightening in stages: 30% > 60% > 100%, then rolling pass "
                                 "and sound check",
             vo="Tightening in stages. Thirty, sixty, then one hundred percent. "
                "Then a rolling pass, and a sound check."),
    ]),
    # ------------------------------------------------------------ references
    "references": dict(layout="refs", kicker="DOCUMENTATION", title="REFERENCES", beats=[
        dict(text=None, vo="References."),
        dict(text="ASME PCC-1-2019, Guidelines for Pressure Boundary Bolted Flange Joint "
                  "Assembly",
             vo="A-S-M-E P-C-C one, twenty nineteen. Guidelines for Pressure Boundary "
                "Bolted Flange Joint Assembly."),
        dict(text="PTG 12.00.06 (August 2022), Guideline for Bolted Flange Joint Integrity "
                  "(BFJI)",
             vo="P-T-G twelve point zero zero point zero six, August twenty twenty-two. "
                "Guideline for Bolted Flange Joint Integrity."),
        dict(text="ASME B16.5, Pipe Flanges and Flanged Fittings (NPS 1/2 through NPS 24)",
             vo="A-S-M-E B sixteen point five. Pipe Flanges and Flanged Fittings."),
        dict(text="Perfect Emerald Sdn Bhd, Hot Bolting Procedure by Using Perfect Force "
                  f"Clamp, Doc. No. {DOC_NO}",
             vo="Perfect Emerald Sendirian Berhad. Hot Bolting Procedure by Using "
                "Perfect Force Clamp."),
    ]),
}

LEAD, GAP, TAIL = 1.0, 0.45, 1.4


def vo_lines():
    """Voice-over lines for narration.py."""
    out = []
    for cid, cd in CARDS.items():
        for k, b in enumerate(cd["beats"]):
            out.append(dict(id=f"card_{cid}_{k}", card=cid, beat=k, text=b["vo"]))
    return out


def estimate(text):
    return 0.6 + len(text.split()) / 2.6


def timing(cid, durs=None):
    """Beat start times (s from card start) and card duration, from VO durations."""
    cd = CARDS[cid]
    t, times = LEAD, []
    for k, b in enumerate(cd["beats"]):
        d = (durs or {}).get(f"card_{cid}_{k}") or estimate(b["vo"])
        times.append(round(t, 3))
        t += d + GAP
    tail = TAIL + (1.2 if cd["layout"] in ("grid", "refs", "columns") else 0.0)
    return times, round(t - GAP + tail, 2)


# ================================================================ drawing ==
def _ease_in(t, t0, d=0.6):
    return ease_out_cubic(prog(t, t0, t0 + d))


def header(c, t, cd, a):
    head = ease_out_cubic(prog(t, 0.1, 0.8)) * a
    draw_text(c, cd["kicker"], 200 - (1 - head) * 60, 300, font("cond_semi", 62), TEAL_LIGHT,
              alpha=head, tracking=12)
    draw_text(c, cd["title"], 196 - (1 - head) * 60, 450, font("cond_bold", 150), WHITE,
              alpha=head, tracking=4)
    k = ease_out_expo(prog(t, 0.3, 1.1)) * a
    c.drawRect(skia.Rect(200, 505, 200 + 240 * k, 515), paint(RED, a))
    if cd.get("page"):
        for i in range(4):
            x = W - 200 - (4 - i) * 100 + 30
            on = i + 1 == cd["page"]
            c.drawRect(skia.Rect(x, 262, x + 70, 274),
                       paint(TEAL if on else STEEL, head * (1.0 if on else 0.35)))


def card(c, t, dur, cid, times):
    cd = CARDS[cid]
    brand_background(c, t + 20)
    a = 1 - ease_in_out_cubic(prog(t, dur - 0.45, dur))
    header(c, t, cd, a)
    {"story": _story, "columns": _columns, "grid": _grid, "refs": _refs}[cd["layout"]](
        c, t, dur, cd, times, a)


def _active(t, times):
    k = -1
    for i, ti in enumerate(times):
        if t >= ti:
            k = i
    return k


# ------------------------------------------------------------------ story --
def _story(c, t, dur, cd, times, a):
    x0, width, y0, max_h = 200, 1640, 720, 1230
    size = 84
    while True:
        f = font("med", size)
        lh, pg = size * 1.38, size * 0.7
        paras = [wrap(b["text"], f, width) for b in cd["beats"]]
        h = sum(len(p) * lh for p in paras) + pg * (len(paras) - 1)
        if h <= max_h or size <= 48:
            break
        size -= 2
    act = _active(t, times)
    y = y0 + (max_h - h) * 0.35
    for k, lines in enumerate(paras):
        ak = _ease_in(t, times[k], 0.7)
        if ak > 0:
            dim = 1.0 if k == act else 0.55
            for line in lines:
                draw_text(c, line, x0, y + size + (1 - ak) * 30, f, WHITE, alpha=ak * a * dim)
                y += lh
        else:
            y += lh * len(lines)
        y += pg
    DIAGRAMS[cd["diagram"]](c, t, times, a * _ease_in(t, 0.3, 0.9), 2780, 1250)


def _flow_offset(t, stop_at=None, v=260.0, decel=1.6):
    if stop_at is None or t < stop_at:
        return v * t
    d = min(t - stop_at, decel)
    return v * stop_at + v * (d - d * d / (2 * decel))


def _joint(c, cx, cy, a, flow=0.0, flow_a=1.0, gasket_glow=0.0, bolt_a=(1.0, 1.0),
           pipe_dim=0.0):
    """Side section of a flanged joint: two pipes, two flanges, gasket, two studs."""
    if a <= 0:
        return
    pipe_col = STEEL_MID
    # pipes
    c.drawRect(skia.Rect(cx - 780, cy - 150, cx - 150, cy + 150), paint(pipe_col, a))
    c.drawRect(skia.Rect(cx + 150, cy - 150, cx + 780, cy + 150), paint(pipe_col, a))
    # hubs
    for s in (-1, 1):
        p = skia.Path()
        p.moveTo(cx + s * 330, cy - 150)
        p.lineTo(cx + s * 150, cy - 230)
        p.lineTo(cx + s * 150, cy + 230)
        p.lineTo(cx + s * 330, cy + 150)
        p.close()
        c.drawPath(p, paint(STEEL_LIGHT, a))
    # flanges
    for s in (-1, 1):
        x_in, x_out = cx + s * 12, cx + s * 150
        c.drawRect(skia.Rect(min(x_in, x_out), cy - 440, max(x_in, x_out), cy + 440),
                   paint(STEEL_LIGHT, a))
        c.drawRect(skia.Rect(min(x_in, x_out), cy - 440, max(x_in, x_out), cy + 440),
                   paint(0xFF1A2238, a * 0.6, stroke=4, cap=skia.Paint.kButt_Cap))
    # gasket (seal)
    gcol = TEAL_LIGHT if gasket_glow > 0 else STEEL
    for s in (-1, 1):
        r = skia.Rect(cx - 12, cy + s * 100 if s > 0 else cy - 250, cx + 12,
                      cy + 250 if s > 0 else cy - 100)
        c.drawRect(r, paint(gcol, a * (0.7 + 0.3 * gasket_glow)))
        if gasket_glow > 0:
            gp = paint(TEAL_LIGHT, a * 0.45 * gasket_glow)
            gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
            c.drawRect(r.makeOutset(10, 6), gp)
    # bore + flow
    c.drawRect(skia.Rect(cx - 780, cy - 95, cx + 780, cy + 95), paint(NAVY_DEEP, a))
    if flow_a > 0:
        c.save()
        c.clipRect(skia.Rect(cx - 780, cy - 95, cx + 780, cy + 95))
        for k in range(14):
            x = cx - 800 + ((k * 120 + flow) % 1680)
            yy = cy + (-40, 20, -10, 45, -35, 5, 35)[k % 7]
            c.drawCircle(x, yy, 13, paint(TEAL_LIGHT, a * flow_a * 0.85))
        c.restore()
    if pipe_dim > 0:
        c.drawRect(skia.Rect(cx - 780, cy - 95, cx + 780, cy + 95), paint(0xFF000000, a * pipe_dim * 0.5))
    # studs at two rows
    for row, ba in zip((-1, 1), bolt_a):
        y = cy + row * 330
        aa = a * ba
        if aa <= 0:
            continue
        c.drawRect(skia.Rect(cx - 230, y - 22, cx + 230, y + 22), paint(BOLT_NEW, aa))
        for nx in (cx - 230, cx + 155):
            c.drawRect(skia.Rect(nx, y - 62, nx + 75, y + 62), paint(BOLT_NEW, aa))
            c.drawRect(skia.Rect(nx, y - 62, nx + 75, y + 62),
                       paint(0xFF1A2238, aa, stroke=4, cap=skia.Paint.kButt_Cap))


def _clamp_arrows(c, cx, cy, a, t):
    if a <= 0:
        return
    pulse = 12 * math.sin(t * 2 * math.pi / 1.3)
    for row in (-1, 1):
        y = cy + row * 330
        _arrow(c, cx - 450 + pulse, y, +1, a, 150)
        _arrow(c, cx + 450 - pulse, y, -1, a, 150)


def d_joint(c, t, times, a, cx, cy):
    glow = _ease_in(t, times[1] + 0.4, 0.8) if len(times) > 1 else 0
    _joint(c, cx, cy, a, flow=_flow_offset(t), flow_a=1.0, gasket_glow=glow)
    _clamp_arrows(c, cx, cy, a * glow, t)


def _icon_clock(c, cx, cy, s, a, t, col=WHITE):
    c.drawCircle(cx, cy, s * 0.42, paint(col, a, stroke=s * 0.07))
    ang = t * 2.4
    c.drawLine(cx, cy, cx + math.sin(ang) * s * 0.3, cy - math.cos(ang) * s * 0.3,
               paint(col, a, stroke=s * 0.06))
    c.drawLine(cx, cy, cx + math.sin(ang / 12) * s * 0.2, cy - math.cos(ang / 12) * s * 0.2,
               paint(col, a, stroke=s * 0.07))


def _icon_loss(c, cx, cy, s, a, t, col=RED):
    base = cy + s * 0.4
    for i, hgt in enumerate((0.75, 0.55, 0.35)):
        x = cx - s * 0.4 + i * s * 0.3
        c.drawRect(skia.Rect(x, base - hgt * s, x + s * 0.2, base), paint(STEEL, a * 0.8))
    p = paint(col, a, stroke=s * 0.07)
    c.drawLine(cx - s * 0.45, cy - s * 0.4, cx + s * 0.35, cy + s * 0.15, p)
    tri = skia.Path()
    tri.moveTo(cx + s * 0.47, cy + s * 0.24)
    tri.lineTo(cx + s * 0.22, cy + s * 0.22)
    tri.lineTo(cx + s * 0.4, cy + s * 0.0)
    tri.close()
    c.drawPath(tri, paint(col, a))


def d_shutdown(c, t, times, a, cx, cy):
    stop = times[0] + 1.6
    st = _ease_in(t, stop + 0.6, 0.8)
    _joint(c, cx, cy, a, flow=_flow_offset(t, stop), flow_a=1 - 0.6 * st, pipe_dim=st)
    # stop sign above the joint
    if st > 0:
        y = cy - 640
        c.drawCircle(cx, y, 95, paint(RED, a * st))
        c.drawRect(skia.Rect(cx - 36, y - 36, cx + 36, y + 36), paint(WHITE, a * st))
    ic = _ease_in(t, stop + 1.6, 0.8)
    _icon_clock(c, cx - 330, cy + 690, 190, a * ic, t, WHITE)
    _icon_loss(c, cx + 330, cy + 690, 190, a * ic, t)


def _load_path(c, cx, cy, a, t):
    if a <= 0:
        return
    p = paint(TEAL_LIGHT, a, stroke=16)
    p.setPathEffect(skia.DashPathEffect.Make([46, 30], -t * 120))
    for s in (-1, 1):
        path = skia.Path()
        path.moveTo(cx - 200, cy + s * 470)
        path.lineTo(cx - 200, cy + s * 545)
        path.lineTo(cx + 200, cy + s * 545)
        path.lineTo(cx + 200, cy + s * 470)
        c.drawPath(path, p)


def _side_clamp(c, cx, cy, a):
    if a <= 0:
        return
    for s in (-1, 1):
        # bridge outside the flange OD, jaws hooking the flange back faces
        y_in, y_out = cy + s * 455, cy + s * 600
        c.drawRect(skia.Rect(cx - 290, min(y_in, y_out), cx + 290, max(y_in, y_out)),
                   paint(TEAL, a))
        for jx in (-1, 1):
            x0, x1 = (cx - 290, cx - 155) if jx < 0 else (cx + 155, cx + 290)
            y0, y1 = cy + s * 380, cy + s * 455
            c.drawRect(skia.Rect(x0, min(y0, y1), x1, max(y0, y1)), paint(TEAL, a))
        c.drawRect(skia.Rect(cx - 290, min(y_in, y_out), cx + 290, max(y_in, y_out)),
                   paint(TEAL_DARK, a, stroke=5, cap=skia.Paint.kButt_Cap))


def d_hot(c, t, times, a, cx, cy):
    press = _ease_in(t, times[2], 0.8) if len(times) > 2 else 0
    clamp = _ease_in(t, times[3], 0.9) if len(times) > 3 else 0
    # top bolt goes out and back while the clamp holds the joint
    top = 1.0
    if clamp >= 1:
        cyc = ((t - times[3] - 1.4) % 3.2) / 3.2 if t > times[3] + 1.4 else 0
        top = 1 - math.sin(math.pi * cyc) ** 2 * 0.85
    _joint(c, cx, cy, a, flow=_flow_offset(t), flow_a=1.0, bolt_a=(top, 1.0),
           gasket_glow=press)
    if press > 0:
        pulse = (t * 0.8) % 1.0
        c.drawRect(skia.Rect(cx - 780, cy - 95, cx + 780, cy + 95),
                   paint(TEAL_LIGHT, a * press * 0.25 * (1 - pulse), stroke=8,
                         cap=skia.Paint.kButt_Cap))
    _side_clamp(c, cx, cy, a * clamp)
    _load_path(c, cx, cy, a * _ease_in(t, times[3] + 0.6, 0.8) if len(times) > 3 else 0, t)


def d_pfc(c, t, times, a, cx, cy, r_scale=1.0):
    """Front view: flange with 4 studs inside the PFC ring with 4 lugs."""
    s = r_scale
    c.drawCircle(cx, cy, 430 * s, paint(STEEL_LIGHT, a))
    c.drawCircle(cx, cy, 165 * s, paint(NAVY_DEEP, a))
    ring = _ease_in(t, times[0] + 0.8, 1.0)
    if ring > 0:
        rp = paint(TEAL, a * ring, stroke=95 * s, cap=skia.Paint.kButt_Cap)
        c.drawCircle(cx, cy, (488 + (1 - ring) * 120) * s, rp)
        for k in range(4):
            ang = math.radians(90 * k)
            lx, ly = cx + math.cos(ang) * 600 * s, cy + math.sin(ang) * 600 * s
            c.save()
            c.translate(lx, ly)
            c.rotate(90 * k)
            c.drawRect(skia.Rect(-80 * s, -105 * s, 80 * s, 105 * s), paint(TEAL, a * ring))
            c.drawCircle(0, 0, 34 * s, paint(WHITE, a * ring))
            c.restore()
    # flange studs, replaced one at a time in criss-cross order
    order = (135, 315, 45, 225)
    t0 = times[1] + 1.0 if len(times) > 1 else 1e9
    step = 1.7
    for n, deg in enumerate(order):
        ang = math.radians(deg)
        bx, by = cx + math.cos(ang) * 320 * s, cy + math.sin(ang) * 320 * s
        local = t - t0 - n * step
        col, ba = BOLT_NEW, 1.0
        if 0 <= local < step:
            ph = local / step
            if ph < 0.35:
                col = RED
            elif ph < 0.65:
                ba = 0.12
                col = RED
            else:
                ba = ease_out_cubic((ph - 0.65) / 0.35)
        c.drawCircle(bx, by, 58 * s, paint(col, a * ba))
        c.drawCircle(bx, by, 58 * s, paint(0xFF1A2238, a * ba, stroke=5))
        if local >= 0:
            draw_text(c, str(n + 1), bx, by + 22 * s, font("cond_bold", 64 * s), WHITE,
                      alpha=a * ba, align="center")


DIAGRAMS = {"joint": d_joint, "shutdown": d_shutdown, "hot": d_hot, "pfc": d_pfc}


# ---------------------------------------------------------------- icons ----
def _tri(c, cx, cy, s, a, col):
    p = skia.Path()
    p.moveTo(cx, cy - s * 0.45)
    p.lineTo(cx + s * 0.5, cy + s * 0.4)
    p.lineTo(cx - s * 0.5, cy + s * 0.4)
    p.close()
    pp = paint(col, a)
    pp.setPathEffect(skia.CornerPathEffect.Make(s * 0.06))
    c.drawPath(p, pp)


def icon(c, kind, cx, cy, s, a, t, col=WHITE):
    st = s * 0.07
    if kind == "warn":
        _tri(c, cx, cy, s, a, RED)
        c.drawRect(skia.Rect(cx - st * 0.6, cy - s * 0.17, cx + st * 0.6, cy + s * 0.15), paint(WHITE, a))
        c.drawCircle(cx, cy + s * 0.27, st * 0.7, paint(WHITE, a))
    elif kind == "clock":
        _icon_clock(c, cx, cy, s, a, t, col)
    elif kind == "load":   # stacked blocks on a calendar bar
        for i, (w, y) in enumerate(((0.8, 0.28), (0.6, 0.04), (0.42, -0.2))):
            c.drawRect(skia.Rect(cx - w * s / 2, cy + (y - 0.1) * s, cx + w * s / 2, cy + (y + 0.11) * s),
                       paint(col, a * (1 - i * 0.18)))
        c.drawLine(cx - s * 0.48, cy + s * 0.44, cx + s * 0.48, cy + s * 0.44, paint(RED, a, stroke=st))
    elif kind == "flow":
        c.drawRect(skia.Rect(cx - s * 0.5, cy - s * 0.16, cx + s * 0.5, cy + s * 0.16), paint(STEEL_MID, a))
        for k in range(4):
            x = cx - s * 0.5 + ((k * 0.28 + t * 0.35) % 1.0) * s
            c.drawCircle(x, cy, s * 0.06, paint(TEAL_LIGHT, a))
        c.drawRect(skia.Rect(cx - s * 0.05, cy - s * 0.32, cx + s * 0.05, cy + s * 0.32), paint(STEEL_LIGHT, a))
    elif kind in ("record", "permit"):
        r = skia.RRect.MakeRectXY(skia.Rect(cx - s * 0.32, cy - s * 0.44, cx + s * 0.32, cy + s * 0.44), s * 0.05, s * 0.05)
        c.drawRRect(r, paint(col, a, stroke=st))
        for i in range(3):
            y = cy - s * 0.22 + i * s * 0.15
            c.drawLine(cx - s * 0.18, y, cx + s * 0.18, y, paint(col, a * 0.7, stroke=st * 0.6))
        p = skia.Path()
        p.moveTo(cx - s * 0.12, cy + s * 0.24)
        p.lineTo(cx - s * 0.02, cy + s * 0.33)
        p.lineTo(cx + s * 0.2, cy + s * 0.12)
        c.drawPath(p, paint(TEAL_LIGHT, a, stroke=st * 1.2))
    elif kind == "ppe":    # hard hat
        p = skia.Path()
        p.addArc(skia.Rect(cx - s * 0.36, cy - s * 0.38, cx + s * 0.36, cy + s * 0.34), 180, 180)
        p.close()
        c.drawPath(p, paint(col, a))
        c.drawRect(skia.Rect(cx - s * 0.5, cy - s * 0.04, cx + s * 0.5, cy + s * 0.08), paint(col, a))
        c.drawRect(skia.Rect(cx - s * 0.05, cy - s * 0.4, cx + s * 0.05, cy - s * 0.05), paint(NAVY, a))
    elif kind == "gauge":
        c.drawCircle(cx, cy, s * 0.44, paint(col, a, stroke=st))
        arc = paint(RED, a, stroke=st * 1.4, cap=skia.Paint.kButt_Cap)
        c.drawArc(skia.Rect(cx - s * 0.32, cy - s * 0.32, cx + s * 0.32, cy + s * 0.32), -40, 55, False, arc)
        ang = math.radians(-150 + 100 * (0.5 + 0.5 * math.sin(t * 1.2)) * 0.9)
        c.drawLine(cx, cy, cx + math.cos(ang) * s * 0.3, cy + math.sin(ang) * s * 0.3, paint(TEAL_LIGHT, a, stroke=st))
        c.drawCircle(cx, cy, st, paint(col, a))
    elif kind == "temp":
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(cx - s * 0.09, cy - s * 0.45, cx + s * 0.09, cy + s * 0.2), s * 0.09, s * 0.09),
                    paint(col, a, stroke=st))
        c.drawCircle(cx, cy + s * 0.28, s * 0.16, paint(RED, a))
        c.drawRect(skia.Rect(cx - s * 0.035, cy - s * 0.15, cx + s * 0.035, cy + s * 0.2), paint(RED, a))
        for i in range(3):
            y = cy - s * 0.35 + i * s * 0.12
            c.drawLine(cx + s * 0.16, y, cx + s * 0.28, y, paint(col, a, stroke=st * 0.6))
    elif kind == "bolts48":
        for j, (n, ox) in enumerate(((4, -0.24), (8, 0.24))):
            x = cx + ox * s
            c.drawCircle(x, cy, s * 0.22, paint(col, a, stroke=st * 0.8))
            for k in range(n):
                ang = 2 * math.pi * (k + 0.5) / n
                c.drawCircle(x + math.cos(ang) * s * 0.15, cy + math.sin(ang) * s * 0.15, s * 0.03, paint(TEAL_LIGHT, a))
    elif kind == "criss":
        c.drawCircle(cx, cy, s * 0.44, paint(col, a, stroke=st * 0.8))
        pts = {1: 135, 2: 315, 3: 45, 4: 225}
        P = {k: (cx + math.cos(math.radians(d)) * s * 0.3, cy + math.sin(math.radians(d)) * s * 0.3) for k, d in pts.items()}
        ph = (t * 0.5) % 1.0
        lp = paint(RED, a, stroke=st * 0.7)
        if ph > 0.1:
            k = min(1, (ph - 0.1) / 0.3)
            c.drawLine(*P[1], P[1][0] + (P[2][0] - P[1][0]) * k, P[1][1] + (P[2][1] - P[1][1]) * k, lp)
        if ph > 0.5:
            k = min(1, (ph - 0.5) / 0.3)
            c.drawLine(*P[3], P[3][0] + (P[4][0] - P[3][0]) * k, P[3][1] + (P[4][1] - P[3][1]) * k, lp)
        f = font("cond_bold", s * 0.2)
        for k, (x, y) in P.items():
            c.drawCircle(x, y, s * 0.1, paint(BOLT_NEW, a))
            draw_text(c, str(k), x, y + s * 0.07, f, WHITE, alpha=a, align="center")
    elif kind == "wind":
        for i, (y, w) in enumerate(((-0.22, 0.7), (0.0, 0.85), (0.22, 0.6))):
            x0 = cx - s * 0.45 + ((t * 0.3 + i * 0.2) % 1.0) * s * 0.06
            p = skia.Path()
            p.moveTo(x0, cy + y * s)
            p.lineTo(x0 + w * s * 0.75, cy + y * s)
            p.arcTo(skia.Rect(x0 + w * s * 0.75 - s * 0.1, cy + y * s - s * 0.2, x0 + w * s * 0.75 + s * 0.1, cy + y * s),
                    90, -270, False)
            c.drawPath(p, paint(col, a, stroke=st * 0.8))
    elif kind == "barrier":
        dp = paint(TEAL_LIGHT, a, stroke=st * 0.7)
        dp.setPathEffect(skia.DashPathEffect.Make([s * 0.08, s * 0.06], 0))
        c.drawCircle(cx, cy, s * 0.45, dp)
        fl = skia.Path()
        fl.moveTo(cx, cy - s * 0.26)
        fl.cubicTo(cx + s * 0.2, cy - s * 0.05, cx + s * 0.18, cy + s * 0.22, cx, cy + s * 0.24)
        fl.cubicTo(cx - s * 0.18, cy + s * 0.22, cx - s * 0.2, cy - s * 0.02, cx, cy - s * 0.26)
        c.drawPath(fl, paint(0xFFF2A33A, a))
        c.drawLine(cx - s * 0.3, cy - s * 0.3, cx + s * 0.3, cy + s * 0.3, paint(RED, a, stroke=st * 1.1))
    elif kind == "sheet":
        p = skia.Path()
        p.moveTo(cx - s * 0.48, cy + s * 0.38)
        p.lineTo(cx + s * 0.48, cy + s * 0.38)
        p.lineTo(cx + s * 0.32, cy + s * 0.18)
        p.lineTo(cx - s * 0.32, cy + s * 0.18)
        p.close()
        c.drawPath(p, paint(0xFFC9B48A, a))
        drop = (t * 0.6) % 1.0
        y = cy - s * 0.4 + ease_in_out_cubic(drop) * s * 0.5
        c.drawRect(skia.Rect(cx - s * 0.07, y - s * 0.08, cx + s * 0.07, y + s * 0.08), paint(BOLT_NEW, a))
    elif kind == "stages":
        for i, hgt in enumerate((0.3, 0.6, 1.0)):
            x = cx - s * 0.42 + i * s * 0.3
            grow = clamp01((t * 0.6 % 1.6) * 3 - i)
            c.drawRect(skia.Rect(x, cy + s * 0.4 - hgt * s * 0.8 * grow, x + s * 0.22, cy + s * 0.4),
                       paint(TEAL_LIGHT if i < 2 else TEAL, a))
        c.drawLine(cx - s * 0.48, cy + s * 0.42, cx + s * 0.48, cy + s * 0.42, paint(col, a, stroke=st * 0.6))


# --------------------------------------------------------------- columns --
def _columns(c, t, dur, cd, times, a):
    beats = [(b, ti) for b, ti in zip(cd["beats"], times) if b["text"]]
    n = len(beats)
    gap = 90
    w = (3440 - gap * (n - 1)) / n
    tone = RED if cd["tone"] == "red" else TEAL
    act = _active(t, times)
    f = font("med", 88 if n == 2 else 80)
    for i, (b, ti) in enumerate(beats):
        ak = _ease_in(t, ti, 0.7) * a
        if ak <= 0:
            continue
        x = 200 + i * (w + gap)
        y0, y1 = 720 + (1 - ak) * 50, 1760
        c.drawRect(skia.Rect(x, y0, x + w, y1), paint(NAVY, 0.82 * ak))
        c.drawRect(skia.Rect(x, y0, x + w, y0 + 14), paint(tone, ak))
        cur = times.index(ti) == act
        if cur:
            c.drawRect(skia.Rect(x, y0, x + w, y1), paint(TEAL_LIGHT, ak * 0.5, stroke=4, cap=skia.Paint.kButt_Cap))
        draw_text(c, f"{i + 1:02d}", x + 90, y0 + 260, font("cond_bold", 190), tone, alpha=ak)
        icon(c, b["icon"], x + w - 230, y0 + 190, 230, ak, t)
        y = y0 + 470
        for line in wrap(b["text"], f, w - 180):
            draw_text(c, line, x + 90, y, f, WHITE, alpha=ak)
            y += f.getSize() * 1.36


# ------------------------------------------------------------------ grid --
def _grid(c, t, dur, cd, times, a):
    # warning sign next to the title
    wa = ease_out_cubic(prog(t, 0.4, 1.1)) * a
    tw = text_width(cd["title"], font("cond_bold", 150), 4)
    icon(c, "warn", 196 + tw + 150, 395, 170, wa, t)
    items = [(b, ti) for b, ti in zip(cd["beats"], times) if b["text"]]
    act = _active(t, times)
    cw, chh, gx, gy = 1680, 262, 80, 26
    f = font("med", 57)
    for i, (b, ti) in enumerate(items):
        ak = _ease_in(t, ti, 0.6) * a
        if ak <= 0:
            continue
        col, row = divmod(i, 5)
        x = 200 + col * (cw + gx) + (1 - ak) * 60
        y = 610 + row * (chh + gy)
        cur = times.index(ti) == act
        c.drawRect(skia.Rect(x, y, x + cw, y + chh), paint(NAVY, (0.9 if cur else 0.72) * ak))
        c.drawRect(skia.Rect(x, y, x + 12, y + chh), paint(RED if cur else TEAL, ak))
        c.drawRect(skia.Rect(x + 40, y + 31, x + 240, y + 231), paint(NAVY_DEEP, ak))
        icon(c, b["icon"], x + 140, y + 131, 160, ak, t)
        lines = wrap(b["text"], f, cw - 340)
        lh = 70
        ty = y + chh / 2 - (len(lines) * lh) / 2 + 52
        for line in lines:
            draw_text(c, line, x + 290, ty, f, WHITE, alpha=ak * (1.0 if cur else 0.8))
            ty += lh


# ------------------------------------------------------------------ refs --
def _refs(c, t, dur, cd, times, a):
    items = [(b, ti) for b, ti in zip(cd["beats"], times) if b["text"]]
    act = _active(t, times)
    f = font("med", 74)
    y = 760
    for i, (b, ti) in enumerate(items):
        ak = _ease_in(t, ti, 0.6) * a
        lines = wrap(b["text"], f, 3000)
        if ak > 0:
            cur = times.index(ti) == act
            x = 200 + (1 - ak) * 60
            c.drawRect(skia.Rect(x, y - 10, x + 130, y + 120), paint(TEAL if cur else TEAL_DARK, ak))
            draw_text(c, str(i + 1), x + 65, y + 92, font("cond_bold", 100), NAVY, alpha=ak, align="center")
            ty = y + 80
            for line in lines:
                draw_text(c, line, x + 220, ty, f, WHITE, alpha=ak * (1.0 if cur else 0.8))
                ty += 100
        y += max(130, len(lines) * 100) + 120
