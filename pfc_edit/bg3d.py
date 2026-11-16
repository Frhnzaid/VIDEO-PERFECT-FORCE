"""3D animation behind the four 'Background' cards (Blender, bpy).

    python pfc_edit/bg3d.py -- --out DIR [--res 1280x720] [--samples 12] [--frames A-B]

Shots follow the voice-over (bg_timing.json, written from cards.section_timing):
  bg1  oil and gas / power / chemical plant pipework with corroded flanges,
       then a close look at a corroded bolted joint
  bg2  dusk: a valve is closed and a beacon flashes (shutdown)
  bg3  the joint on a live line (cut-away, product flowing); the PFC arrives as
       the temporary load path
  bg4  plant at sunset; then flange studs replaced one at a time with the PFC on

Plants and corrosion are illustrative (procedural), not a specific site.
The joint and the PFC reuse the geometry from pfc3d.py. The left part of the
frame is kept quiet for the on-screen text (lens shift).
"""
import argparse
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import bmesh  # noqa: E402  (after bpy)
from mathutils import Matrix, Vector  # noqa: E402

import pfc3d as P  # noqa: E402
from pfc3d import (FLANGE_ANG, REPLACE_ORDER, X_FL, activate, key_hide, key_loc,  # noqa: E402
                   mat, srgb)

FPS = 24
TIMING = json.load(open(os.path.join(HERE, "bg_timing.json")))
CARD = {c["id"]: c for c in TIMING["cards"]}
TOTAL = TIMING["total"]


def F(t):
    return int(round(t * FPS)) + 1


def beat(cid, k):
    c = CARD[cid]
    return c["start"] + c["times"][k]


# ----------------------------------------------------------------- shots ---
B1 = CARD["bg1"]["start"]
S = {}
S["offshore"] = (0.0, 2.8)
S["power"] = (2.8, 5.0)
S["chem"] = (5.0, beat("bg1", 1) - 0.15)
S["closeup"] = (S["chem"][1], CARD["bg2"]["start"])
S["valve"] = (CARD["bg2"]["start"], CARD["bg3"]["start"])
S["live"] = (CARD["bg3"]["start"], beat("bg3", 2) - 0.2)
S["pressure"] = (S["live"][1], beat("bg3", 3) - 0.2)
S["clamp"] = (S["pressure"][1], CARD["bg4"]["start"])
S["sunset"] = (CARD["bg4"]["start"], beat("bg4", 1) - 0.2)
S["replace"] = (S["sunset"][1], TOTAL)
SHOT_ORDER = ["offshore", "power", "chem", "closeup", "valve", "live", "pressure", "clamp",
              "sunset", "replace"]

# where each set sits in the world
ORG = dict(offshore=Vector((1000, 0, 0)), power=Vector((2000, 0, 0)),
           chem=Vector((3000, 0, 0)), valve=Vector((4000, 0, 0)))


# ------------------------------------------------------------ materials ----
def rust_mat(name, paint_hex, rust=0.4, scale=3.0, paint_rough=0.45, paint_metal=0.0,
             streak=False):
    """Painted / bare steel with procedural corrosion. rust 0..1 = coverage."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    if streak:  # stretched vertically: run-off streaks
        mp.inputs["Scale"].default_value = (1.0, 1.0, 0.45)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 12
    nz.inputs["Roughness"].default_value = 0.68
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    th = 0.5 + (rust - 0.5) * 0.36   # noise Fac sits mostly in 0.35..0.65
    paint = srgb(paint_hex)
    col = nt.nodes.new("ShaderNodeValToRGB")
    e = col.color_ramp.elements
    e[0].position, e[0].color = 0.0, (*srgb("#24130B"), 1)
    e[1].position, e[1].color = 1.0, (*[c * 1.08 for c in paint], 1)
    for pos, cc in ((max(th - 0.12, 0.01), srgb("#4A2614")), (max(th - 0.04, 0.02), srgb("#7A4424")),
                    (th, tuple(c * 0.55 for c in paint)), (th + 0.025, paint)):
        el = e.new(pos)
        el.color = (*cc, 1)
    nt.links.new(nz.outputs["Fac"], col.inputs["Fac"])
    nt.links.new(col.outputs["Color"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["From Min"].default_value = th - 0.01
    rr.inputs["From Max"].default_value = th + 0.03
    rr.inputs["To Min"].default_value = 0.93
    rr.inputs["To Max"].default_value = paint_rough
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    mm = nt.nodes.new("ShaderNodeMapRange")
    mm.inputs["From Min"].default_value = th - 0.01
    mm.inputs["From Max"].default_value = th + 0.03
    mm.inputs["To Min"].default_value = 0.0
    mm.inputs["To Max"].default_value = paint_metal
    nt.links.new(nz.outputs["Fac"], mm.inputs["Value"])
    nt.links.new(mm.outputs["Result"], b.inputs["Metallic"])
    # pitted relief where it has rusted
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = scale * 9
    n2.inputs["Detail"].default_value = 8
    nt.links.new(mp.outputs["Vector"], n2.inputs["Vector"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    inv = nt.nodes.new("ShaderNodeMapRange")
    inv.inputs["From Min"].default_value = th
    inv.inputs["From Max"].default_value = th - 0.1
    nt.links.new(nz.outputs["Fac"], inv.inputs["Value"])
    nt.links.new(n2.outputs["Fac"], mul.inputs[0])
    nt.links.new(inv.outputs["Result"], mul.inputs[1])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.45
    bump.inputs["Distance"].default_value = 0.02
    nt.links.new(mul.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def concrete_mat():
    m = bpy.data.materials.new("concrete")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.6
    nz.inputs["Detail"].default_value = 10
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (*srgb("#4B4A47"), 1)
    r.color_ramp.elements[1].color = (*srgb("#8A8780"), 1)
    nt.links.new(nz.outputs["Fac"], r.inputs["Fac"])
    nt.links.new(r.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.92
    return m


def sea_mat():
    m = bpy.data.materials.new("sea")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*srgb("#0A2430"), 1)
    b.inputs["Roughness"].default_value = 0.06
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.08, 0.3, 1)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.noise_dimensions = "4D"
    nz.inputs["Scale"].default_value = 6
    nz.inputs["Detail"].default_value = 6
    nz.inputs["W"].default_value = 0
    nz.inputs["W"].keyframe_insert("default_value", frame=1)
    nz.inputs["W"].default_value = 6
    nz.inputs["W"].keyframe_insert("default_value", frame=F(TOTAL) + 1)
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def emit_mat(name, hex_, strength):
    m = mat(name, srgb(hex_), rough=0.4, emit=srgb(hex_), emit_strength=strength)
    return m


# ------------------------------------------------------------- geometry ----
def _axis_matrix(c, d):
    d = Vector(d).normalized()
    q = d.to_track_quat("Z", "Y")
    return Matrix.Translation(Vector(c)) @ q.to_matrix().to_4x4()


def _cyl(bm, r, depth, m4, seg, mi):
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                radius1=r, radius2=r, depth=depth, matrix=m4)
    faces = {f for v in res["verts"] for f in v.link_faces}
    for f in faces:
        f.material_index = mi
        f.smooth = seg > 8


def new_obj(name, bm, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def pipe(name, p0, p1, r, m, seg=40):
    bm = bmesh.new()
    p0, p1 = Vector(p0), Vector(p1)
    _cyl(bm, r, (p1 - p0).length, _axis_matrix((p0 + p1) / 2, p1 - p0), seg, 0)
    return new_obj(name, bm, [m])


def flange_joint(name, c, d, r, m_fl, m_bolt, n_bolts=8):
    """A bolted flange pair on a pipe of radius r: two discs, n studs, 2n nuts."""
    bm = bmesh.new()
    base = _axis_matrix(c, d)
    t, g = r * 0.32, r * 0.03
    fr, bc = r * 2.0, r * 1.6
    for s in (-1, 1):
        _cyl(bm, fr, t, base @ Matrix.Translation((0, 0, s * (g + t / 2))), 48, 0)
        _cyl(bm, r * 1.25, t * 1.4, base @ Matrix.Translation((0, 0, s * (g + t * 1.6))), 32, 0)
    sr, nt_ = r * 0.11, r * 0.22
    L = 2 * (g + t) + 2 * nt_ + r * 0.24
    for k in range(n_bolts):
        a = 2 * math.pi * (k + 0.5) / n_bolts
        off = Matrix.Translation((math.cos(a) * bc, math.sin(a) * bc, 0))
        _cyl(bm, sr, L, base @ off, 10, 1)
        for s in (-1, 1):
            _cyl(bm, sr * 1.9, nt_, base @ off @ Matrix.Translation((0, 0, s * (g + t + nt_ / 2))), 6, 1)
    return new_obj(name, bm, [m_fl, m_bolt])


def flanged_line(name, p0, p1, r, m_pipe, m_fl, m_bolt, every, n_bolts=8, offset=0.5):
    p0, p1 = Vector(p0), Vector(p1)
    pipe(name, p0, p1, r, m_pipe)
    d = p1 - p0
    n = max(1, int(d.length // every))
    for i in range(n):
        c = p0 + d * ((i + offset) / n)
        flange_joint(f"{name}_fj{i}", c, d, r, m_fl, m_bolt, n_bolts)


def box_obj(name, size, loc, m, rot=(0, 0, 0)):
    o = P.box(name, size, loc, rot)
    P.set_mat(o, m)
    return o


def cyl_z(name, r, z0, z1, x, y, m, seg=48):
    bm = bmesh.new()
    _cyl(bm, r, z1 - z0, Matrix.Translation((x, y, (z0 + z1) / 2)), seg, 0)
    return new_obj(name, bm, [m])


def hyperboloid(name, x, y, r_base, r_waist, r_top, h, m):
    bm = bmesh.new()
    rings, seg = 12, 64
    prev = None
    for i in range(rings + 1):
        z = h * i / rings
        u = z / h
        r = (r_base * (1 - u) ** 2 + r_waist * 2 * u * (1 - u) * 0.9 + r_top * u ** 2) \
            if False else (r_waist + (r_base - r_waist) * ((0.62 - u) / 0.62) ** 2 if u < 0.62
                           else r_waist + (r_top - r_waist) * ((u - 0.62) / 0.38) ** 2)
        ring = [bm.verts.new((x + math.cos(2 * math.pi * k / seg) * r,
                              y + math.sin(2 * math.pi * k / seg) * r, z)) for k in range(seg)]
        if prev:
            for k in range(seg):
                f = bm.faces.new((prev[k], prev[(k + 1) % seg], ring[(k + 1) % seg], ring[k]))
                f.smooth = True
        prev = ring
    return new_obj(name, bm, [m])


def ground(name, center, size, m):
    bpy.ops.mesh.primitive_plane_add(size=size, location=center)
    o = bpy.context.object
    o.name = name
    P.set_mat(o, m)
    return o


def portal_rack(name, org, length, width, height, spacing, m_steel, levels=(1.0,)):
    """Steel pipe rack along +X: H-section columns and cross beams."""
    n = int(length // spacing) + 1
    for i in range(n):
        x = org.x + i * spacing
        for s in (-1, 1):
            box_obj(f"{name}_col{i}{s}", (0.35, 0.35, height), (x, org.y + s * width / 2, org.z + height / 2), m_steel)
        for lv in levels:
            box_obj(f"{name}_beam{i}_{lv}", (0.3, width + 0.4, 0.3), (x, org.y, org.z + height * lv), m_steel)
    for s in (-1, 1):
        box_obj(f"{name}_long{s}", (length, 0.25, 0.3), (org.x + length / 2, org.y + s * width / 2, org.z + height), m_steel)


# ---------------------------------------------------------------- world ----
SUN = dict(golden=(9.0, 3.2, 0.28), day=(28.0, 3.2, 0.22), dusk=(0.6, 0.35, 0.10),
           sunset=(2.5, 2.2, 0.22))
SUN["studio"] = (40.0, 0.6, 0.0)
SHOT_SUN = dict(offshore="golden", power="golden", chem="golden", closeup="golden",
                valve="dusk", live="day", pressure="day", clamp="studio", sunset="sunset",
                replace="studio")
STUDIO = {"clamp", "replace"}   # the PFC on a clean, light backdrop


def world_and_sun():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_rotation = math.radians(200)
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    studio = nt.nodes.new("ShaderNodeBackground")
    studio.inputs["Color"].default_value = (*srgb("#D3D7DD"), 1)
    studio.inputs["Strength"].default_value = 0.9
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(bg.outputs["Background"], mix.inputs[1])
    nt.links.new(studio.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 50))
    sun = bpy.context.object
    sun.name = "sun"
    sun.data.angle = math.radians(1.2)
    sun.data.color = (1.0, 0.86, 0.68)
    for shot in SHOT_ORDER:
        elev, energy, sky_str = SUN[SHOT_SUN[shot]]
        fr = F(S[shot][0])
        sky.sun_elevation = math.radians(elev)
        sky.keyframe_insert("sun_elevation", frame=fr)
        bg.inputs["Strength"].default_value = sky_str
        bg.inputs["Strength"].keyframe_insert("default_value", frame=fr)
        mix.inputs[0].default_value = 1.0 if shot in STUDIO else 0.0
        mix.inputs[0].keyframe_insert("default_value", frame=fr)
        e = math.radians(max(elev, 2.0))
        sun.rotation_euler = (math.pi / 2 - e, 0, math.radians(200) + math.pi / 2)
        sun.keyframe_insert("rotation_euler", frame=fr)
        sun.data.energy = energy
        sun.data.keyframe_insert("energy", frame=fr)
        warm = (1.0, 0.72, 0.5) if elev < 10 else (1.0, 0.93, 0.85)
        sun.data.color = warm
        sun.data.keyframe_insert("color", frame=fr)
    for idd in (w.node_tree, sky, sun, sun.data):
        _constant(idd)


def _constant(id_data):
    ad = getattr(id_data, "animation_data", None)
    if not ad or not ad.action:
        return
    act = ad.action
    curves = list(act.fcurves) if hasattr(act, "fcurves") else [
        fc for layer in act.layers for strip in layer.strips for bag in strip.channelbags
        for fc in bag.fcurves]
    for fc in curves:
        for k in fc.keyframe_points:
            k.interpolation = "CONSTANT"


# ----------------------------------------------------------------- sets ----
def build_offshore(M):
    o = ORG["offshore"]
    sea = ground("sea", o + Vector((0, 0, -22)), 3000, M["sea"])
    deck = box_obj("deck", (90, 50, 1.6), o + Vector((20, 8, -0.8)), M["steel_grey"])
    for x in (-20, 20, 55):
        for y in (-12, 28):
            cyl_z(f"leg{x}{y}", 1.6, -22, -1.6, o.x + x, o.y + y, M["steel_yellow"])
    portal_rack("rack", o + Vector((-12, 0, 0)), 60, 7, 6.5, 6, M["steel_grey"], levels=(0.55, 1.0))
    lines = [(-2.4, 6.5 * 0.55 + 0.45, 0.42, "pipe_yellow"), (-0.9, 6.5 * 0.55 + 0.35, 0.32, "pipe_grey"),
             (0.5, 6.5 * 0.55 + 0.45, 0.42, "pipe_green"), (2.2, 6.5 * 0.55 + 0.3, 0.28, "pipe_grey"),
             (-2.0, 6.5 + 0.4, 0.36, "pipe_grey"), (0.4, 6.5 + 0.5, 0.48, "pipe_yellow"),
             (2.4, 6.5 + 0.35, 0.3, "pipe_green")]
    for i, (y, z, r, mk) in enumerate(lines):
        flanged_line(f"os{i}", o + Vector((-14, y, z)), o + Vector((50, y, z)), r, M[mk],
                     M["flange_rust"], M["bolt_rust"], every=9.5, offset=0.3 + 0.13 * i)
    # vessel and a stack on the far side of the deck
    cyl_z("vessel", 3.2, 0, 11, o.x + 30, o.y + 20, M["tank_white"])
    cyl_z("stack", 1.0, 0, 34, o.x + 46, o.y + 24, M["steel_grey"])
    box_obj("module", (16, 12, 10), (o.x + 10, o.y + 26, 5), M["steel_grey"])
    # derrick: four leaning legs with girts
    dx, dy, h = o.x + 40, o.y + 8, 34
    for sx in (-1, 1):
        for sy in (-1, 1):
            p0 = Vector((dx + sx * 4, dy + sy * 4, 0))
            p1 = Vector((dx + sx * 1.2, dy + sy * 1.2, h))
            pipe(f"dleg{sx}{sy}", p0, p1, 0.22, M["steel_white"], seg=8)
    for z in range(4, h, 5):
        k = z / h
        e = 4 - 2.8 * k
        for (ax, ay, bx, by) in ((-e, -e, e, -e), (e, -e, e, e), (e, e, -e, e), (-e, e, -e, -e)):
            pipe(f"dg{z}{ax}{ay}", (dx + ax, dy + ay, z), (dx + bx, dy + by, z), 0.1, M["steel_white"], seg=6)
    # pedestal crane and a flare boom
    cyl_z("crane_ped", 1.2, 0, 8, o.x + 2, o.y + 30, M["steel_yellow"])
    pipe("crane_boom", (o.x + 2, o.y + 30, 8), (o.x - 14, o.y + 18, 24), 0.35, M["steel_yellow"], seg=8)
    pipe("flare", (o.x + 60, o.y + 20, 2), (o.x + 85, o.y + 34, 22), 0.4, M["steel_grey"], seg=8)
    cyl_z("flare_tip", 0.7, 22, 23.2, o.x + 85, o.y + 34, M["steel_grey"], seg=16)


def build_power(M):
    o = ORG["power"]
    ground("pw_ground", o, 1500, M["concrete"])
    hyperboloid("tower1", o.x + 120, o.y + 260, 55, 34, 38, 140, M["tower"])
    hyperboloid("tower2", o.x - 60, o.y + 320, 55, 34, 38, 140, M["tower"])
    box_obj("hall", (90, 40, 34), (o.x + 40, o.y + 110, 17), M["cladding"])
    # big steam line on sleepers toward the camera, plus two smaller lines
    for i, (y, r, z) in enumerate(((0.0, 0.85, 1.6), (3.2, 0.55, 1.2), (-2.8, 0.45, 1.1))):
        flanged_line(f"pw{i}", o + Vector((-30, y, z)), o + Vector((60, y, z)), r,
                     M["pipe_grey" if i else "pipe_insul"], M["flange_rust"], M["bolt_rust"],
                     every=14, n_bolts=12 if i == 0 else 8, offset=0.25 + 0.2 * i)
    for x in range(-30, 61, 7):
        box_obj(f"sleeper{x}", (0.6, 10, 0.5), (o.x + x, o.y, 0.25), M["concrete"])


def build_chem(M):
    o = ORG["chem"]
    ground("ch_ground", o, 1500, M["concrete"])
    for i, (x, y, r, h) in enumerate(((30, 40, 9, 14), (55, 52, 9, 14), (8, 62, 7, 12))):
        cyl_z(f"tank{i}", r, 0, h, o.x + x, o.y + y, M["tank_white"])
    cyl_z("column1", 2.6, 0, 48, o.x - 8, o.y + 30, M["tank_white"])
    cyl_z("column2", 1.8, 0, 38, o.x - 16, o.y + 38, M["tank_white"])
    for z in range(8, 48, 8):
        cyl_z(f"plat{z}", 3.6, z, z + 0.25, o.x - 8, o.y + 30, M["steel_grey"], seg=32)
    portal_rack("crack", o + Vector((-20, 6, 0)), 70, 6, 5.5, 6, M["steel_grey"], levels=(0.6, 1.0))
    for i, (y, z, r, mk) in enumerate(((4.0, 3.75, 0.3, "pipe_grey"), (5.4, 3.75, 0.38, "pipe_green"),
                                       (6.8, 3.75, 0.26, "pipe_yellow"), (8.0, 3.75, 0.34, "pipe_grey"),
                                       (5.0, 5.9, 0.3, "pipe_grey"), (7.2, 5.9, 0.4, "pipe_green"))):
        flanged_line(f"ch{i}", o + Vector((-22, y, z)), o + Vector((52, y, z)), r, M[mk],
                     M["flange_rust"], M["bolt_rust"], every=8.5, offset=0.2 + 0.17 * i)
    # vertical riser close to camera with a corroded joint
    flanged_line("riser", o + Vector((2, -1.5, 0)), o + Vector((2, -1.5, 9)), 0.4, M["pipe_grey"],
                 M["flange_rust"], M["bolt_rust"], every=9, offset=0.25)


def build_valve(M):
    o = ORG["valve"]
    ground("vl_ground", o, 1500, M["concrete"])
    portal_rack("vrack", o + Vector((-25, 6, 0)), 60, 6, 6, 6, M["steel_grey"], levels=(0.6, 1.0))
    for i, (y, z, r, mk) in enumerate(((4.2, 3.95, 0.32, "pipe_grey"), (5.8, 3.95, 0.4, "pipe_yellow"),
                                       (7.4, 3.95, 0.3, "pipe_grey"), (6.0, 6.3, 0.35, "pipe_green"))):
        flanged_line(f"vl{i}", o + Vector((-27, y, z)), o + Vector((33, y, z)), r, M[mk],
                     M["flange_rust"], M["bolt_rust"], every=10, offset=0.3 + 0.2 * i)
    # main line at working height with a gate valve
    y0, z0, r = 0.0, 1.3, 0.45
    flanged_line("vmain_a", o + Vector((-30, y0, z0)), o + Vector((-1.3, y0, z0)), r, M["pipe_grey"],
                 M["flange_rust"], M["bolt_rust"], every=12)
    flanged_line("vmain_b", o + Vector((1.3, y0, z0)), o + Vector((30, y0, z0)), r, M["pipe_grey"],
                 M["flange_rust"], M["bolt_rust"], every=12)
    for s in (-1, 1):
        flange_joint(f"vend{s}", o + Vector((s * 1.25, y0, z0)), (1, 0, 0), r, M["flange_rust"],
                     M["bolt_rust"])
    box_obj("vbody", (2.1, 1.3, 1.6), o + Vector((0, y0, z0)), M["valve_body"])
    cyl_z("vbonnet", 0.42, z0 + 0.8, z0 + 2.6, o.x, o.y + y0, M["valve_body"])
    cyl_z("vstem", 0.07, z0 + 2.6, z0 + 3.4, o.x, o.y + y0, M["chrome"])
    # handwheel: torus + spokes, parented to an empty that turns
    bpy.ops.object.empty_add(location=o + Vector((0, y0, z0 + 3.1)))
    hub = bpy.context.object
    hub.name = "wheel"
    bpy.ops.mesh.primitive_torus_add(major_radius=0.85, minor_radius=0.07,
                                     location=o + Vector((0, y0, z0 + 3.1)))
    rim = bpy.context.object
    P.set_mat(rim, M["wheel_red"])
    parts = [rim]
    for k in range(3):
        a = math.radians(60 * k)
        sp = box_obj(f"spoke{k}", (1.7, 0.08, 0.08), o + Vector((0, y0, z0 + 3.1)), M["wheel_red"],
                     rot=(0, 0, a))
        parts.append(sp)
    P._parent_all(hub, parts)
    t0, t1 = S["valve"][0] + 1.6, S["valve"][0] + 6.4
    hub.rotation_euler = (0, 0, 0)
    hub.keyframe_insert("rotation_euler", frame=F(t0))
    hub.rotation_euler = (0, 0, math.radians(-3 * 360))
    hub.keyframe_insert("rotation_euler", frame=F(t1))
    # beacon on a pole: flashes once the valve is closed
    cyl_z("bpole", 0.08, 0, 4.2, o.x + 3.4, o.y + 2.2, M["steel_grey"], seg=12)
    cyl_z("beacon", 0.22, 4.2, 4.7, o.x + 3.4, o.y + 2.2, M["beacon"], seg=24)
    bpy.ops.object.light_add(type="POINT", location=o + Vector((3.4, 1.6, 4.5)))
    bl = bpy.context.object
    bl.data.color = (1.0, 0.08, 0.05)
    bl.data.shadow_soft_size = 0.2
    bn = M["beacon"].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    on_t = t1 + 0.3
    fr0, fr1 = F(S["valve"][0]), F(S["valve"][1])
    for fr in range(fr0, fr1 + 1):
        t = (fr - 1) / FPS
        on = t >= on_t and ((t - on_t) % 0.9) < 0.45
        bl.data.energy = 900 if on else 0
        bl.data.keyframe_insert("energy", frame=fr)
        bn.default_value = 30 if on else 0.2
        bn.keyframe_insert("default_value", frame=fr)
    bl.data.energy = 0
    bl.data.keyframe_insert("energy", frame=fr1 + 1)
    _constant(bl.data)
    _constant(M["beacon"].node_tree)
    # sodium lamps on the rack
    for x in (-18, -6, 6, 18):
        bpy.ops.object.light_add(type="POINT", location=o + Vector((x, 3.0, 5.6)))
        l = bpy.context.object
        l.data.energy = 600
        l.data.color = (1.0, 0.62, 0.3)
        l.data.shadow_soft_size = 0.4


def build_joint_set(M):
    """The detailed joint from pfc3d.py, with corroded flanges and studs."""
    Mj = dict(
        pipe=M["pipe_grey_j"], flange=M["flange_rust_j"], gasket=mat("gasket", srgb("#20242C"), rough=0.7),
        machined_jaw=mat("machined_jaw", srgb("#C4C9D0"), metal=1.0, rough=0.4, aniso=0.6,
                         emit=srgb("#6FD3C6"), emit_strength=0.0),
        machined_face=mat("machined_face", srgb("#B9BEC6"), metal=1.0, rough=0.42, aniso=0.6,
                          emit=srgb("#6FD3C6"), emit_strength=0.0),
        blue=mat("blue", srgb("#1A47B8"), rough=0.42, coat=0.15),
        blue_new=mat("blue_new", srgb("#1A47B8"), rough=0.42, coat=0.15,
                     emit=srgb("#6FD3C6"), emit_strength=0.0),
        blue_pfc=mat("blue_pfc", srgb("#1A47B8"), rough=0.42, coat=0.15,
                     emit=srgb("#6FD3C6"), emit_strength=0.0),
        old_rod=M["bolt_rust_j"], old_nut=M["bolt_rust_j"], dark=mat("dark", srgb("#15181E"), metal=0.8, rough=0.4),
        fluid=P.fluid_material(),
    )
    P.build_joint(Mj)
    studs = P.build_flange_studs(Mj)
    jaws, lugs, pfc_studs = P.build_pfc(Mj)
    n0 = set(bpy.data.objects.keys())
    ground("j_ground", (0, 0, -6.0), 900, M["concrete"])
    for x in (-7.5, 7.5):
        box_obj(f"jsup{x}", (0.9, 1.6, 5.6), (x, 0, -3.2), M["steel_yellow"])
    # blurred plant behind: tanks, columns, a rack
    rnd = random.Random(7)
    for k in range(16):
        a = math.radians(rnd.uniform(0, 360))
        d = rnd.uniform(70, 140)
        x, y = math.cos(a) * d, math.sin(a) * d
        if rnd.random() < 0.5:
            cyl_z(f"bgt{k}", rnd.uniform(7, 14), -6, rnd.uniform(10, 30), x, y, M["tank_white"])
        else:
            cyl_z(f"bgc{k}", rnd.uniform(2, 4), -6, rnd.uniform(40, 80), x, y, M["steel_grey"])
    portal_rack("jrack", Vector((-60, 45, -6)), 120, 8, 10, 8, M["steel_grey"], levels=(0.6, 1.0))
    plant = [bpy.data.objects[k] for k in set(bpy.data.objects.keys()) - n0]
    # studio: light floor and soft boxes, only in the product shots
    floor = ground("studio_floor", (0, 0, -6.0), 900, M["studio_floor"])
    lights = []
    for name, loc, energy, size in (("st_key", (-6, -9, 9), 2600, 8), ("st_fill", (-11, 4, 3), 900, 8),
                                    ("st_rim", (6, 8, 7), 1800, 6), ("st_top", (0, 0, 12), 900, 10)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object
        l.name = name
        l.data.size = size
        l.data.color = (1.0, 0.98, 0.95)
        tr = l.constraints.new("TRACK_TO")
        bpy.ops.object.empty_add(location=(0, 0, 0))
        tr.target = bpy.context.object
        tr.track_axis = "TRACK_NEGATIVE_Z"
        tr.up_axis = "UP_Y"
        lights.append((l, energy))
    for shot in SHOT_ORDER:
        fr = F(S[shot][0])
        st = shot in STUDIO
        for o in plant:
            o.hide_render = st
            o.keyframe_insert("hide_render", frame=fr)
        floor.hide_render = not st
        floor.keyframe_insert("hide_render", frame=fr)
        for l, e in lights:
            l.data.energy = e if st else 0.0
            l.data.keyframe_insert("energy", frame=fr)
    for o in plant + [floor] + [l.data for l, _ in lights]:
        _constant(o)
    return Mj, studs, jaws, lugs, pfc_studs


def animate_joint(Mj, studs, jaws, lugs, pfc_studs):
    # new studs hidden until they go in; PFC hidden until it arrives
    for old, new in studs:
        key_hide(old[0], 1, False)
        key_hide(new[0], 1, True)
    pfc_parts = [(o, None) for o in jaws + lugs] + [(s[0], None) for s in pfc_studs]
    t_in = beat("bg3", 3) + 0.5
    for k, (o, _) in enumerate(pfc_parts):
        loc = o.location.copy()
        rad = Vector((0, loc.y, loc.z))
        rad = rad.normalized() if rad.length > 1e-3 else Vector((0, 0, 1))
        side = 1 if loc.x >= 0 else -1
        far = loc + rad * 3.2 + Vector((side * 2.0, 0, 0))
        st = t_in + (k % 8) * 0.12 + (0.6 if k >= len(jaws) + len(lugs) else 0)
        key_hide(o, 1, True)
        key_hide(o, F(st), False)
        key_loc(o, F(st), far)
        key_loc(o, F(st + 1.3), loc)
    t_glow = t_in + 2.6
    for m in (Mj["machined_face"], Mj["machined_jaw"], Mj["blue_pfc"]):
        P.key_emit(m, F(t_glow - 0.1), 0.0)
        P.key_emit(m, F(t_glow + 0.6), 0.7)
        P.key_emit(m, F(t_glow + 2.4), 0.0)
    # bolts replaced one at a time (criss-cross) in the last shot
    t0 = S["replace"][0] + 1.4
    step = 2.3
    for n, i in enumerate(REPLACE_ORDER):
        old, new = studs[i]
        oroot, nroot = old[0], new[0]
        a = t0 + n * step
        home_o, home_n = oroot.location.copy(), nroot.location.copy()
        key_loc(oroot, F(a), home_o)
        key_loc(oroot, F(a + 0.8), home_o + Vector((3.4, 0, 0)))
        key_hide(oroot, F(a + 0.85), True)
        key_hide(nroot, F(a + 0.9), False)
        key_loc(nroot, F(a + 0.85), home_n + Vector((3.4, 0, 0)))
        key_loc(nroot, F(a + 1.7), home_n)
    P.key_emit(Mj["blue_new"], F(t0), 0.0)
    P.key_emit(Mj["blue_new"], F(t0 + 4 * step), 0.6)
    P.key_emit(Mj["blue_new"], F(TOTAL), 0.2)
    # the line is live: brighter flow while 'under pressure'
    fl = Mj["fluid"].node_tree.nodes["Emission"].inputs["Strength"]
    for t, v in ((S["pressure"][0], 2.2), (S["pressure"][0] + 1.0, 4.0), (S["pressure"][1], 4.0),
                 (S["pressure"][1] + 0.6, 2.2)):
        fl.default_value = v
        fl.keyframe_insert("default_value", frame=F(t))


# --------------------------------------------------------------- cameras ---
def shot_camera(name, keys, lens=35, fstop=None, focus=None, shift_x=-0.235):
    """keys: [(t, cam_loc, target_loc)]"""
    bpy.ops.object.empty_add(location=keys[0][2])
    tgt = bpy.context.object
    tgt.name = name + "_tgt"
    bpy.ops.object.camera_add(location=keys[0][1])
    cam = bpy.context.object
    cam.name = name
    cam.data.lens = lens
    cam.data.shift_x = shift_x
    cam.data.clip_end = 3000
    tr = cam.constraints.new("TRACK_TO")
    tr.target = tgt
    tr.track_axis = "TRACK_NEGATIVE_Z"
    tr.up_axis = "UP_Y"
    if fstop:
        cam.data.dof.use_dof = True
        cam.data.dof.aperture_fstop = fstop
        cam.data.dof.focus_object = focus or tgt
    for t, cl, tl in keys:
        key_loc(cam, F(t), Vector(cl))
        key_loc(tgt, F(t), Vector(tl))
    return cam


def build_cameras():
    cams = {}
    a, b = S["offshore"]
    o = ORG["offshore"]
    cams["offshore"] = shot_camera("cam_off", [
        (a, o + Vector((-42, -50, -3.0)), o + Vector((16, 6, 3.0))),
        (b, o + Vector((-35, -47, -2.0)), o + Vector((18, 6, 3.5)))], lens=30)
    a, b = S["power"]
    o = ORG["power"]
    cams["power"] = shot_camera("cam_pw", [
        (a, o + Vector((-14, -6.5, 2.6)), o + Vector((6, 1, 3.0))),
        (b, o + Vector((-11, -6.0, 2.4)), o + Vector((9, 1, 3.4)))], lens=30)
    a, b = S["chem"]
    o = ORG["chem"]
    cams["chem"] = shot_camera("cam_ch", [
        (a, o + Vector((-6, -9, 1.4)), o + Vector((6, 6, 6.0))),
        (b, o + Vector((-5, -9.5, 3.8)), o + Vector((8, 6, 7.5)))], lens=26)
    a, b = S["closeup"]
    cams["closeup"] = shot_camera("cam_cu", [
        (a, (-6.2, -7.8, 3.4), (-0.3, 0, 0.3)),
        (b, (-4.6, -6.6, 2.3), (-0.4, 0.3, 0.6))], lens=45, fstop=0.7)
    a, b = S["valve"]
    o = ORG["valve"]
    cams["valve"] = shot_camera("cam_vl", [
        (a, o + Vector((-6.5, -6.8, 3.4)), o + Vector((0, 0.5, 3.0))),
        (b, o + Vector((-4.8, -5.8, 3.0)), o + Vector((0, 0.5, 3.2)))], lens=32, fstop=8)
    a, b = S["live"]
    cams["live"] = shot_camera("cam_live", [
        (a, (-11.5, -9.5, 4.2), (0.4, 0, 0)),
        (b, (-7.0, -9.0, 2.6), (0.6, 0, 0))], lens=40, fstop=0.9)
    a, b = S["pressure"]
    cams["pressure"] = shot_camera("cam_pr", [
        (a, (-7.8, -8.4, 3.4), (-1.0, 0, 0.3)),
        (b, (-6.2, -8.8, 2.4), (-1.2, 0, 0.2))], lens=40, fstop=1.4)
    a, b = S["clamp"]
    cams["clamp"] = shot_camera("cam_cl", [
        (a, (-12.5, -11.0, 6.0), (0.3, 0, 0)),
        (b, (-10.0, -11.5, 4.0), (0.3, 0, 0))], lens=38, fstop=2.0)
    a, b = S["sunset"]
    o = ORG["chem"]
    cams["sunset"] = shot_camera("cam_ss", [
        (a, o + Vector((-24, -22, 6.0)), o + Vector((10, 20, 10))),
        (b, o + Vector((-18, -24, 7.5)), o + Vector((14, 22, 12)))], lens=24)
    a, b = S["replace"]
    cams["replace"] = shot_camera("cam_rp", [
        (a, (-13.5, -11.0, 6.0), (0.3, 0, 0)),
        (a + 6.0, (-13.5, -8.5, 4.2), (0.3, 0, 0)),
        (b, (-11.0, -14.0, 3.6), (0.4, 0, 0))], lens=38, fstop=2.0)
    return cams


# ------------------------------------------------------------------ main ---
def build():
    P.clear()
    M = dict(
        sea=sea_mat(), concrete=concrete_mat(),
        flange_rust=rust_mat("flange_rust", "#3E4247", rust=0.72, scale=2.5, paint_metal=0.2),
        bolt_rust=rust_mat("bolt_rust", "#2E3034", rust=0.9, scale=6.0, paint_metal=0.4),
        pipe_grey=rust_mat("pipe_grey", "#8E959C", rust=0.28, scale=0.9, streak=True),
        pipe_yellow=rust_mat("pipe_yellow", "#C49A22", rust=0.3, scale=0.9, streak=True),
        pipe_green=rust_mat("pipe_green", "#4C7656", rust=0.3, scale=0.9, streak=True),
        pipe_insul=rust_mat("pipe_insul", "#B9BCBF", rust=0.12, scale=0.5, paint_rough=0.3,
                            paint_metal=0.8),
        steel_grey=rust_mat("steel_grey", "#6E747A", rust=0.25, scale=0.5, streak=True),
        steel_white=rust_mat("steel_white", "#E2E2DE", rust=0.2, scale=0.6, streak=True),
        steel_yellow=rust_mat("steel_yellow", "#C49A22", rust=0.35, scale=0.6, streak=True),
        tank_white=rust_mat("tank_white", "#D6D5CF", rust=0.18, scale=0.25, streak=True),
        studio_floor=mat("studio_floor", srgb("#D9DCE1"), rough=0.55),
        tower=rust_mat("tower", "#9C9A94", rust=0.08, scale=0.05, paint_rough=0.9),
        cladding=rust_mat("cladding", "#7D8A93", rust=0.1, scale=0.1),
        valve_body=rust_mat("valve_body", "#2F4F3A", rust=0.5, scale=2.0),
        wheel_red=rust_mat("wheel_red", "#A3231F", rust=0.25, scale=3.0),
        chrome=mat("chrome", srgb("#D9DDE3"), metal=1.0, rough=0.2),
        beacon=emit_mat("beacon", "#FF2A1A", 0.2),
        # joint scale (flange radius 1.6): finer patterns
        pipe_grey_j=rust_mat("pipe_grey_j", "#8E959C", rust=0.3, scale=1.2, streak=True),
        flange_rust_j=rust_mat("flange_rust_j", "#3B3F45", rust=0.75, scale=1.4, paint_metal=0.2),
        bolt_rust_j=rust_mat("bolt_rust_j", "#2E3034", rust=0.92, scale=4.0, paint_metal=0.4),
    )
    build_offshore(M)
    build_power(M)
    build_chem(M)
    build_valve(M)
    Mj, studs, jaws, lugs, pfc_studs = build_joint_set(M)
    animate_joint(Mj, studs, jaws, lugs, pfc_studs)
    world_and_sun()
    cams = build_cameras()
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, F(TOTAL) - 1
    sc.render.fps = FPS
    return cams


def shot_at(t):
    for k in SHOT_ORDER:
        if S[k][0] <= t < S[k][1]:
            return k
    return SHOT_ORDER[-1]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--frames", default=None, help="A-B or comma list")
    ap.add_argument("--blend", default=None)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    cams = build()
    P.configure_render("CYCLES", tuple(int(x) for x in a.res.split("x")), a.samples, a.out)
    sc = bpy.context.scene
    sc.cycles.max_bounces = 3
    sc.view_settings.look = "AgX - Medium High Contrast"
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
    if a.frames:
        if "-" in a.frames:
            s, e = (int(x) for x in a.frames.split("-"))
            frames = range(s, e + 1)
        else:
            frames = [int(x) for x in a.frames.split(",")]
    else:
        frames = range(sc.frame_start, sc.frame_end + 1)
    for fr in frames:
        path = os.path.join(a.out, f"f_{fr:05d}.png")
        if os.path.exists(path):
            continue
        sc.frame_set(fr)
        sc.camera = cams[shot_at((fr - 1) / FPS)]
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("frame", fr, flush=True)


if __name__ == "__main__":
    main()
