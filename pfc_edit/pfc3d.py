"""3D 'How it works' animation of the Perfect Force Clamp (Blender, bpy).

    python pfc_edit/pfc3d.py --out DIR [--res 1920x1080] [--engine EEVEE|CYCLES]
                             [--frames A-B] [--samples N] [--blend file.blend]

Scene: a 4-stud-bolt flanged joint on a live line (cut-away pipe with moving
fluid) and the PFC as in reference/pfc_photos: four V-shaped lug plates on each
face (PFC stud bolt + two cap screws each) and four split, ribbed jaws on the
diagonals around the flange OD, pulled together by four PFC stud bolts outside
the flange OD. Proportions follow the photos; illustrative, not to scale.

Sequence (seconds at 24 fps), shared with the 2D overlay in gfx.py (PFC3D_*):
  0.0 -  3.5  establishing shot, line under pressure
  3.5 -  8.5  A  flange preparation: existing bolts torqued (criss-cross)
  8.5 - 17.5  B  PFC segments seated, PFC stud bolts fitted and torqued
 17.5 - 33.5  C  four flange stud bolts replaced one at a time
 33.5 - 39.5  D  PFC removed
 39.5 - 43.0  hero: four new stud bolts, line still live
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfc_steps import (B8_ROLL, B8_STEP, B8_T0, C10_SPAN, DUR,  # noqa: E402
                       FLANGE_ORDER_ANG, PFC_LOOSEN_ANG, S, SIDE_ORDER, TOTAL)
import bpy
import bmesh  # noqa: E402  (available once bpy is loaded)
from mathutils import Vector

FPS = 24
T = dict(end=TOTAL)

# ----------------------------------------------------------------- sizes ---
PIPE_R, PIPE_BORE = 0.36, 0.29
FL_R, FL_T, GAP = 1.6, 0.35, 0.05          # flange radius, thickness, gasket gap
HUB_R0, HUB_R1, HUB_L = 0.72, PIPE_R, 0.5  # weld-neck hub
BC_R = 1.2                                 # flange bolt circle
STUD_R, NUT_AF, NUT_T = 0.10, 0.34, 0.22
# PFC proportions taken from the reference photos (front view: flange OD is
# ~0.55 of the PFC OD; four V-shaped lug plates at 0/90/180/270 deg; four
# split, ribbed jaws on the diagonals wrapped around the flange OD)
PFC_RO = 2.9                               # PFC outer radius
LUG_HALF = 29.0                            # lug outer arc half-angle (deg)
LUG_TIP_R, LUG_TIP_W = 1.15, 0.13          # flat tip of the V, half-width
LUG_T = 0.42                               # lug plate thickness (axial)
JAW_RI = FL_R + 0.03                       # jaws sit just outside the flange OD
GAPC = 0.012                               # clearance between PFC parts
PFC_BC, PFC_STUD_R, PFC_NUT_AF, PFC_NUT_T = 2.42, 0.14, 0.44, 0.30
X_FL = GAP / 2 + FL_T                      # outer face of each flange
X_RING = X_FL + LUG_T                      # outer face of the lug plates
JAW_X = X_FL + LUG_T * 0.72               # jaws slightly recessed from the lugs

FLANGE_ANG = [45, 135, 225, 315]           # flange studs on the diagonals
PFC_ANG = [0, 90, 180, 270]                # PFC studs / segments
REPLACE_ORDER = [0, 2, 1, 3]               # criss-cross: 1, 3, 2, 4


def sec(t):
    return int(round(t * FPS)) + 1


def polar(r, ang_deg):
    a = math.radians(ang_deg)
    return r * math.cos(a), r * math.sin(a)  # (y, z)


# -------------------------------------------------------------- helpers ----
def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def activate(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def cyl_x(name, r, x0, x1, verts=64, y=0.0, z=0.0):
    """Cylinder along the X axis from x0 to x1."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=abs(x1 - x0),
                                        location=((x0 + x1) / 2, y, z),
                                        rotation=(0, math.radians(90), 0))
    o = bpy.context.object
    o.name = name
    return o


def cone_x(name, r0, r1, x0, x1, verts=64):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r0, radius2=r1, depth=abs(x1 - x0),
                                    location=((x0 + x1) / 2, 0, 0),
                                    rotation=(0, math.radians(90 if x1 > x0 else -90), 0))
    o = bpy.context.object
    o.name = name
    return o


def box(name, size, loc, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.scale = size
    o.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def boolean(target, cutter, op="DIFFERENCE", keep=False):
    m = target.modifiers.new("b", "BOOLEAN")
    m.operation = op
    m.object = cutter
    m.solver = "EXACT"
    activate(target)
    bpy.ops.object.modifier_apply(modifier=m.name)
    if not keep:
        bpy.data.objects.remove(cutter, do_unlink=True)


def bevel(o, w=0.012, seg=2, weighted=True):
    m = o.modifiers.new("bev", "BEVEL")
    m.width = w
    m.segments = seg
    m.limit_method = "ANGLE"
    if weighted:
        o.modifiers.new("wn", "WEIGHTED_NORMAL")


def smooth(o):
    activate(o)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))


def set_mat(o, m):
    """Single material on every face (booleans can leave stray empty slots)."""
    o.data.materials.clear()
    o.data.materials.append(m)
    for poly in o.data.polygons:
        poly.material_index = 0


def set_origin_center(o):
    activate(o)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")


# ------------------------------------------------------------ materials ----
def mat(name, color, metal=0.0, rough=0.4, emit=None, emit_strength=0.0, coat=0.0,
        aniso=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    if coat:
        b.inputs["Coat Weight"].default_value = coat
    if aniso:
        b.inputs["Anisotropic"].default_value = aniso
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    return m


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def fluid_material():
    m = bpy.data.materials.new("fluid")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexWave")
    tex.wave_type = "BANDS"
    tex.bands_direction = "X"
    tex.inputs["Scale"].default_value = 1.6
    tex.inputs["Distortion"].default_value = 2.0
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*srgb("#0E4F5A"), 1)
    ramp.color_ramp.elements[1].color = (*srgb("#6FD3C6"), 1)
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    em.inputs["Strength"].default_value = 2.2
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    # flow: slide the texture along X over the whole shot
    loc = mapping.inputs["Location"]
    loc.default_value = (0, 0, 0)
    loc.keyframe_insert("default_value", frame=1)
    loc.default_value = (-T["end"] * 1.2, 0, 0)
    loc.keyframe_insert("default_value", frame=sec(T["end"]))
    return m


def linear_all(id_data):
    ad = getattr(id_data, "animation_data", None)
    if not ad or not ad.action:
        return
    act = ad.action
    curves = []
    if hasattr(act, "fcurves"):
        curves = list(act.fcurves)
    else:  # Blender 4.4+ layered actions
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves += list(bag.fcurves)
    for fc in curves:
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"


# ------------------------------------------------------------- geometry ----
def hex_nut(name, af, t, hole_r, x, y, z, m):
    r = af / math.sqrt(3)  # circumradius from across-flats
    n = cyl_x(name, r, x - t / 2, x + t / 2, verts=6, y=y, z=z)
    activate(n)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    n.rotation_euler = (math.radians(30), 0, 0)  # flat on top
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    h = cyl_x(name + "_h", hole_r, x - t, x + t, verts=24, y=y, z=z)
    boolean(n, h)
    bevel(n, 0.015)
    set_mat(n, m)
    return n


def stud_assembly(name, ang, radius, rod_r, af, nt, x_face, extra, m_rod, m_nut, parent_at=None):
    """Stud bolt along X with a nut on each outer face. Returns parent empty."""
    y, z = polar(radius, ang)
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, y, z))
    root = bpy.context.object
    root.name = name
    half = x_face + nt + extra
    rod = cyl_x(name + "_rod", rod_r, -half, half, verts=32, y=y, z=z)
    set_mat(rod, m_rod)
    smooth(rod)
    nuts = []
    for side in (-1, 1):
        nx = side * (x_face + nt / 2)
        nut = hex_nut(f"{name}_nut{'L' if side < 0 else 'R'}", af, nt, rod_r * 1.02, nx, y, z, m_nut)
        nuts.append(nut)
    bpy.context.view_layer.update()
    for o in [rod] + nuts:
        o.parent = root
        o.matrix_parent_inverse = root.matrix_world.inverted()
    return root, rod, nuts


def build_joint(M):
    objs = {}
    # pipe (tube) with a cut-away window to show the live line
    for side in (-1, 1):
        x0, x1 = side * (X_FL + HUB_L - 0.02), side * 9.0
        p = cyl_x(f"pipe{side}", PIPE_R, min(x0, x1), max(x0, x1))
        bore = cyl_x("bore", PIPE_BORE, min(x0, x1) - 0.1, max(x0, x1) + 0.1)
        boolean(p, bore)
        cx = side * 3.2
        cut = box("cut", (3.2, 1.0, 1.0), (cx, -0.5, 0.5))
        boolean(p, cut)
        set_mat(p, M["pipe"])
        smooth(p)
        bevel(p, 0.01)
        objs[f"pipe{side}"] = p
        hub = cone_x(f"hub{side}", HUB_R0, HUB_R1, side * X_FL, side * (X_FL + HUB_L))
        hb = cyl_x("hb", PIPE_BORE, -2, 2)
        boolean(hub, hb)
        set_mat(hub, M["flange"])
        smooth(hub)
        fl = cyl_x(f"flange{side}", FL_R, min(side * GAP / 2, side * X_FL),
                   max(side * GAP / 2, side * X_FL), verts=128)
        fb = cyl_x("fb", PIPE_BORE, -2, 2)
        boolean(fl, fb)
        for a in FLANGE_ANG:
            y, z = polar(BC_R, a)
            h = cyl_x("bh", STUD_R * 1.15, -2, 2, verts=24, y=y, z=z)
            boolean(fl, h)
        set_mat(fl, M["flange"])
        bevel(fl, 0.02)
        smooth(fl)
    gk = cyl_x("gasket", FL_R * 0.78, -GAP / 2, GAP / 2, verts=96)
    set_mat(gk, M["gasket"])
    # fluid inside the bore
    fluid = cyl_x("fluid", PIPE_BORE * 0.985, -9, 9, verts=48)
    set_mat(fluid, M["fluid"])
    smooth(fluid)
    return objs


def build_flange_studs(M):
    studs = []
    for i, a in enumerate(FLANGE_ANG):
        old = stud_assembly(f"old{i}", a, BC_R, STUD_R, NUT_AF, NUT_T, X_FL, 0.12,
                            M["old_rod"], M["old_nut"])
        new = stud_assembly(f"new{i}", a, BC_R, STUD_R, NUT_AF, NUT_T, X_FL, 0.12,
                            M["blue_new"], M["blue_new"])
        studs.append((old, new))
    return studs


def prism(name, pts, x0, x1):
    """Extrude a closed (y, z) polygon along X from x0 to x1."""
    n = len(pts)
    verts = [(x0, y, z) for y, z in pts] + [(x1, y, z) for y, z in pts]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    # concave n-gon caps shade badly under bevel + weighted normals: triangulate them
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4],
                          quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(me)
    bm.free()
    me.update()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    activate(o)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return o


def arc(r, a0, a1, n=24):
    return [polar(r, a0 + (a1 - a0) * i / n) for i in range(n + 1)]


def _rot(p, ang):
    a = math.radians(ang)
    y, z = p
    return (y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))


def _offset_line(p0, p1, d):
    """Shift segment p0->p1 sideways by d (positive = left of direction)."""
    dy, dz = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dy, dz)
    ny, nz = -dz / L * d, dy / L * d
    return (p0[0] + ny, p0[1] + nz), (p1[0] + ny, p1[1] + nz)


def _line_circle(p0, p1, r):
    """Point on the infinite line p0->p1 at distance r from the origin (towards p1)."""
    dy, dz = p1[0] - p0[0], p1[1] - p0[1]
    a = dy * dy + dz * dz
    b = 2 * (p0[0] * dy + p0[1] * dz)
    c = p0[0] ** 2 + p0[1] ** 2 - r * r
    s = (-b + math.sqrt(max(b * b - 4 * a * c, 0))) / (2 * a)
    return (p0[0] + s * dy, p0[1] + s * dz)


def lug_outline():
    """V-shaped lug plate centred on angle 0 (pointing at the pipe)."""
    tip_hi, tip_lo = (LUG_TIP_R, LUG_TIP_W), (LUG_TIP_R, -LUG_TIP_W)
    pts = [tip_lo] + arc(PFC_RO, -LUG_HALF, LUG_HALF) + [tip_hi]
    return pts


def lug_sides(ang):
    """The two V edges of the lug at `ang`, as (outer point, tip point)."""
    hi = (_rot(polar(PFC_RO, LUG_HALF), ang), _rot((LUG_TIP_R, LUG_TIP_W), ang))
    lo = (_rot(polar(PFC_RO, -LUG_HALF), ang), _rot((LUG_TIP_R, -LUG_TIP_W), ang))
    return hi, lo


def jaw_half_outline(diag, which):
    """Half of the ribbed jaw on diagonal `diag`; which=-1 (towards the lower lug) or +1."""
    if which < 0:
        lug_ang = diag - 45
        p_out, p_tip = lug_sides(lug_ang)[0]           # upper edge of the lower lug
        p_out, p_tip = _offset_line(p_tip, p_out, -GAPC)[::-1]
        a_split = diag - 0.25
    else:
        lug_ang = diag + 45
        p_out, p_tip = lug_sides(lug_ang)[1]           # lower edge of the upper lug
        p_out, p_tip = _offset_line(p_tip, p_out, GAPC)[::-1]
        a_split = diag + 0.25
    q_in = _line_circle(p_tip, p_out, JAW_RI)
    q_out = _line_circle(p_tip, p_out, PFC_RO)
    def near(a):  # same turn as the split line, so arcs take the short way
        return a_split + (a - a_split + 180.0) % 360.0 - 180.0
    a_in = near(math.degrees(math.atan2(q_in[1], q_in[0])))
    a_out = near(math.degrees(math.atan2(q_out[1], q_out[0])))
    inner = arc(JAW_RI, a_in, a_split, 10)
    outer = arc(PFC_RO, a_split, a_out, 10)
    pts = inner + outer
    if which > 0:
        pts = pts[::-1]
    return pts


def build_pfc(M):
    jaws, lugs, caps = [], [], []
    # ribbed jaws (eight halves) spanning both flanges
    for d in FLANGE_ANG:
        for which in (-1, 1):
            o = prism(f"jaw{d}{'a' if which < 0 else 'b'}", jaw_half_outline(d, which), -JAW_X, JAW_X)
            # axial ribs on the outer face and face ribs, as on the real jaws
            mid = d + which * 8
            for k in range(-3, 4):
                g = box("rib", (2 * JAW_X + 0.2, 0.03, 0.07),
                        (0, *polar(PFC_RO, mid + k * 2.0)), (math.radians(mid + k * 2.0), 0, 0))
                boolean(o, g)
            set_mat(o, M["machined_jaw"])
            set_origin_center(o)
            bevel(o, 0.012, weighted=False)
            jaws.append(o)
    # V lug plates on both faces with two socket cap screws each
    base = lug_outline()
    for side in (-1, 1):
        for a in PFC_ANG:
            pts = [_rot(p, a) for p in base]
            x0, x1 = sorted((side * X_FL, side * X_RING))
            o = prism(f"lug{a}{'L' if side < 0 else 'R'}", pts, x0 + side * 0.001, x1)
            y, z = polar(PFC_BC, a)
            h = cyl_x("lh", PFC_STUD_R * 1.12, x0 - 0.1, x1 + 0.1, verts=32, y=y, z=z)
            boolean(o, h)
            set_mat(o, M["machined_face"])
            set_origin_center(o)
            bevel(o, 0.014)
            for da in (-LUG_HALF + 8, LUG_HALF - 8):
                cy, cz = polar(PFC_RO - 0.32, a + da)
                xf = side * X_RING
                cap = cyl_x("cap", 0.085, xf - 0.02 * side, xf + 0.012 * side, verts=24, y=cy, z=cz)
                sock = cyl_x("sock", 0.04, xf - 0.05, xf + 0.05, verts=6, y=cy, z=cz)
                boolean(cap, sock)
                activate(cap)
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
                bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
                set_mat(cap, M["dark"])
                bpy.context.view_layer.update()
                cap.parent = o
                cap.matrix_parent_inverse = o.matrix_world.inverted()
            lugs.append(o)
    studs = []
    for i, a in enumerate(PFC_ANG):
        studs.append(stud_assembly(f"pfc{i}", a, PFC_BC, PFC_STUD_R, PFC_NUT_AF, PFC_NUT_T,
                                   X_RING, 0.22, M["blue"], M["blue_pfc"]))
    return jaws, lugs, studs


# ------------------------------------------------------------ animation ----
def key_loc(o, frame, loc=None):
    if loc is not None:
        o.location = loc
    o.keyframe_insert("location", frame=frame)


def key_rot(o, frame, rot=None):
    if rot is not None:
        o.rotation_euler = rot
    o.keyframe_insert("rotation_euler", frame=frame)


def key_hide(o, frame, hidden):
    for ob in [o] + list(o.children_recursive):
        ob.hide_render = hidden
        ob.hide_viewport = hidden
        ob.keyframe_insert("hide_render", frame=frame)
        ob.keyframe_insert("hide_viewport", frame=frame)


def key_emit(m, frame, strength):
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Strength"].default_value = strength
    b.inputs["Emission Strength"].keyframe_insert("default_value", frame=frame)


# ------------------------------------------------------------- tools -------
def _parent_all(root, parts):
    bpy.context.view_layer.update()
    for p in parts:
        p.parent = root
        p.matrix_parent_inverse = root.matrix_world.inverted()


def _empty(name):
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    e = bpy.context.object
    e.name = name
    return e


def build_tools(M):
    """Simple tools modelled around the origin. Local +X points away from the
    nut (towards the operator), local +Z is the handle direction."""
    T_ = {}
    # torque wrench (calibrated MTW): socket, head, long handle with grip
    root = _empty("tool_mtw")
    parts = [cyl_x("mtw_socket", 0.27, -0.12, 0.42, verts=32)]
    set_mat(parts[-1], M["chrome"])
    parts.append(box("mtw_head", (0.22, 0.3, 0.42), (0.52, 0, 0.1)))
    set_mat(parts[-1], M["chrome"])
    parts.append(box("mtw_bar", (0.12, 0.16, 2.3), (0.52, 0, 1.35)))
    set_mat(parts[-1], M["chrome"])
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.12, depth=0.8, location=(0.52, 0, 2.15))
    grip = bpy.context.object
    set_mat(grip, M["grip"])
    scale = box("mtw_scale", (0.02, 0.17, 0.5), (0.585, 0, 0.9))
    set_mat(scale, M["teal_glow"])
    for p in parts:
        bevel(p, 0.01)
    parts += [grip, scale]
    _parent_all(root, parts)
    T_["mtw"] = root

    # socket ratchet for loosening
    root = _empty("tool_socket")
    parts = [cyl_x("sk_socket", 0.25, -0.12, 0.4, verts=32)]
    parts.append(cyl_x("sk_head", 0.2, 0.4, 0.62, verts=32))
    parts.append(box("sk_bar", (0.1, 0.13, 1.3), (0.51, 0, 0.75)))
    for p in parts:
        set_mat(p, M["chrome_dark"])
        bevel(p, 0.01)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.1, depth=0.55, location=(0.51, 0, 1.25))
    parts.append(bpy.context.object)
    set_mat(parts[-1], M["grip"])
    _parent_all(root, parts)
    T_["socket"] = root

    # hammer (slugging) wrench: box-end ring and a heavy short handle
    root = _empty("tool_hammer")
    ring = cyl_x("hw_ring", 0.34, -0.09, 0.09, verts=12)
    hole = cyl_x("hw_hole", 0.21, -0.2, 0.2, verts=12)
    boolean(ring, hole)
    bar = box("hw_bar", (0.18, 0.2, 1.3), (0, 0, 0.95))
    strike = box("hw_strike", (0.3, 0.34, 0.3), (0, 0, 1.65))
    for p in (ring, bar, strike):
        set_mat(p, M["tool_dark"])
        bevel(p, 0.015)
    _parent_all(root, [ring, bar, strike])
    T_["hammer"] = root

    # digital caliper: beam along X, two jaws pointing to -Z (towards the part)
    root = _empty("tool_caliper")
    beam = box("cal_beam", (1.9, 0.05, 0.16), (0, 0, 0.42))
    jaw1 = box("cal_jaw1", (0.07, 0.05, 0.42), (-1.0, 0, 0.2))
    jaw2 = box("cal_jaw2", (0.07, 0.05, 0.42), (1.0, 0, 0.2))
    body = box("cal_body", (0.5, 0.09, 0.3), (0.65, 0, 0.42))
    screen = box("cal_screen", (0.32, 0.1, 0.15), (0.65, -0.005, 0.45))
    for p in (beam, jaw1, jaw2, body):
        set_mat(p, M["chrome"])
        bevel(p, 0.008)
    set_mat(screen, M["teal_glow"])
    _parent_all(root, [beam, jaw1, jaw2, body, screen])
    T_["caliper"] = root
    T_["caliper_jaws"] = (jaw1, jaw2)

    # brush for Molykote
    root = _empty("tool_brush")
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.07, depth=1.2, location=(0, 0, 0.95))
    handle = bpy.context.object
    set_mat(handle, M["red_handle"])
    ferrule = box("br_ferrule", (0.34, 0.14, 0.18), (0, 0, 0.32))
    set_mat(ferrule, M["chrome"])
    bristle = box("br_bristle", (0.32, 0.12, 0.26), (0, 0, 0.12))
    set_mat(bristle, M["bristle"])
    _parent_all(root, [handle, ferrule, bristle])
    T_["brush"] = root
    for r in T_.values():
        if isinstance(r, tuple):
            continue
        key_hide(r, 1, True)
    return T_


def build_numbers(M):
    """Marker numbers 1-4 on the front flange face, readable from the -X side."""
    from mathutils import Matrix
    nums = {}
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts",
                             "barlow-condensed-latin-700-normal.woff")
    fnt = None
    try:
        fnt = bpy.data.fonts.load(font_path)
    except Exception:
        fnt = None
    rot = Matrix(((0, 0, -1), (-1, 0, 0), (0, 1, 0))).to_euler()
    for n, ang in enumerate(SIDE_ORDER, start=1):
        y, z = polar(1.42, ang)
        bpy.ops.object.text_add(location=(-X_FL - 0.003, y, z), rotation=rot)
        t = bpy.context.object
        t.name = f"mark{n}"
        t.data.body = str(n)
        if fnt:
            t.data.font = fnt
        t.data.size = 0.3
        t.data.align_x = "CENTER"
        t.data.align_y = "CENTER"
        t.data.extrude = 0.002
        t.data.materials.append(M["marker"])
        t.scale = (0.001, 0.001, 0.001)
        t.keyframe_insert("scale", frame=1)
        nums[ang] = t
    return nums


def build_tray(M, studs, pfc_studs):
    """Tray in front of / below the joint holding the PFC and new stud bolts."""
    tray = box("tray", (3.4, 3.7, 0.08), (0.0, -4.75, -2.62))
    set_mat(tray, M["tray"])
    bevel(tray, 0.02)
    rack = {}
    items = [s[0] for s in pfc_studs] + [new[0] for _, new in studs]
    for i, root in enumerate(items):
        rack[root.name] = Vector((0.0, -3.15 - i * 0.45, -2.3))
    return tray, rack


# ------------------------------------------------------------ animation ----
def tool_place(tool, frame, x, ang, radius, swing=0.0, side=-1):
    """Tool root at the nut centre (x, angle, radius) with the handle radial
    outward; `swing` turns it about the stud axis (degrees)."""
    y, z = polar(radius, ang)
    tool.location = (x, y, z)
    tool.rotation_euler = (math.radians(ang - 90 + swing), 0.0, 0.0)
    tool.keyframe_insert("location", frame=frame)
    tool.keyframe_insert("rotation_euler", frame=frame)


def key_scale(o, frame, s):
    o.scale = (s, s, s) if not isinstance(s, tuple) else s
    o.keyframe_insert("scale", frame=frame)


def key_spin(o, frame, deg):
    o.rotation_euler = (math.radians(deg), 0, 0)
    o.keyframe_insert("rotation_euler", frame=frame)


def animate(studs, jaws, lugs, pfc_studs, M, tools, nums, tray, rack):
    f = sec
    jaw_by = {j.name: j for j in jaws}
    lug_by = {l.name: l for l in lugs}
    pfc_by_ang = dict(zip(PFC_ANG, pfc_studs))
    flange_by_ang = dict(zip(FLANGE_ANG, studs))
    x_fnut = -(X_FL + NUT_T / 2)            # front flange nut centre
    x_bnut = X_FL + NUT_T / 2               # back flange nut centre
    x_pnut = -(X_RING + PFC_NUT_T / 2)      # front PFC nut centre
    mtw, sock, ham, cal, brush = (tools[k] for k in ("mtw", "socket", "hammer", "caliper", "brush"))

    # ---- tray and the stud bolts waiting on it ----------------------------
    a1, a1e = S["A1"]
    key_hide(tray, 1, True)
    key_hide(tray, f(a1) - 1, True)
    key_hide(tray, f(a1), False)
    key_loc(tray, f(a1), tray.location + Vector((0, 0, -2.0)))
    key_loc(tray, f(a1 + 0.6), tray.location + Vector((0, 0, 2.0)))
    key_hide(tray, f(S["C11"][0]), False)
    key_hide(tray, f(S["C11"][0]) + 1, True)
    for root_name, pos in rack.items():
        root = bpy.data.objects[root_name]
        key_hide(root, 1, True)
        key_hide(root, f(a1) - 1, True)
        key_hide(root, f(a1), False)
        key_loc(root, f(a1), pos + Vector((0, 0, -2.0)))
        key_loc(root, f(a1 + 0.6), pos)
        # back nut goes on only once the bolt is through the joint
        back = [c for c in root.children if c.name.endswith("nutR")][0]
        key_hide(back, 1, True)

    # ---- A1 Molykote: brush passes over the bolts on the tray -------------
    key_hide(brush, f(a1 + 0.8), False)
    for i, (t, x, y) in enumerate(((a1 + 0.8, 0.6, -2.9), (a1 + 4.0, 0.6, -6.4),
                                   (a1 + 4.3, -0.6, -6.4), (a1 + 7.6, -0.6, -2.9))):
        brush.location = (x, y, -2.05)
        brush.rotation_euler = (math.radians(12), 0, 0)
        brush.keyframe_insert("location", frame=f(t))
        brush.keyframe_insert("rotation_euler", frame=f(t))
    key_hide(brush, f(a1e - 0.2), True)

    # ---- A2 caliper at the four sides, numbers marked ---------------------
    a2 = S["A2"][0]
    key_hide(cal, f(a2 + 0.2), False)
    for k, ang in enumerate(SIDE_ORDER):
        sp = (DUR["A2"] - 0.8) / 4
        t = a2 + 0.3 + k * sp
        tool_place(cal, f(t), 0.0, ang, FL_R + 0.02)
        tool_place(cal, f(t + sp * 0.75), 0.0, ang, FL_R + 0.02)
        key_scale(nums[ang], f(t + 0.5), 0.001)
        key_scale(nums[ang], f(t + 0.8), 1.0)
    key_hide(cal, f(S["A2"][1] - 0.3), True)

    # ---- A3 torque existing stud bolts + sound check ----------------------
    a3 = S["A3"][0]
    key_scale(mtw, 1, 1.0)
    key_hide(mtw, f(a3 + 0.2), False)
    for k, ang in enumerate(FLANGE_ORDER_ANG):
        t = a3 + 0.3 + k * (DUR["A3"] - 2.0) / 4
        old_root, old_rod, old_nuts = flange_by_ang[ang][0]
        tool_place(mtw, f(t), x_fnut, ang, BC_R, 0)
        tool_place(mtw, f(t + 0.65), x_fnut, ang, BC_R, 28)
        key_spin(old_nuts[0], f(t), 0)
        key_spin(old_nuts[0], f(t + 0.65), 28)
    key_hide(mtw, f(a3 + 0.4 + (DUR["A3"] - 2.0)), True)
    for k in range(4):
        t = S["A3"][1] - 0.9 + k * 0.2
        key_emit(M["old_nut"], f(t), 0.0)
        key_emit(M["old_nut"], f(t + 0.1), 0.6)
        key_emit(M["old_nut"], f(t + 0.2), 0.0)

    # ---- B4 install PFC: female jaws then male lug, side by side ----------
    b4 = S["B4"][0]

    def radial(piece, t_in, t_out, dist=3.2):
        home = piece.location.copy()
        dirv = Vector((0, home.y, home.z)).normalized()
        away = home + dirv * dist
        key_hide(piece, 1, True)
        key_hide(piece, f(t_in) - 1, True)
        key_hide(piece, f(t_in), False)
        key_loc(piece, f(t_in), away)
        key_loc(piece, f(t_in + 0.7), home)
        key_loc(piece, f(t_out), home)
        key_loc(piece, f(t_out + 0.8), away)
        key_hide(piece, f(t_out + 0.8), False)
        key_hide(piece, f(t_out + 0.8) + 1, True)

    d12 = S["D12"][0]
    out_rank = {a: i for i, a in enumerate(PFC_LOOSEN_ANG)}
    for k, ang in enumerate(SIDE_ORDER):
        t0 = b4 + 0.2 + k * (DUR["B4"] - 1.6) / 4
        t_lug_out = d12 + 3.2 + out_rank[ang] * 0.3
        t_jaw_out = d12 + 4.3 + out_rank[ang] * 0.3
        for d, half in (((ang + 45) % 360, "a"), ((ang - 45) % 360, "b")):
            radial(jaw_by[f"jaw{d}{half}"], t0, t_jaw_out)
        for side in ("L", "R"):
            radial(lug_by[f"lug{ang}{side}"], t0 + 0.6, t_lug_out)

    # ---- B5 PFC stud bolts from the tray, hand-tight ----------------------
    b5 = S["B5"][0]
    for k, ang in enumerate(SIDE_ORDER):
        root, rod, nuts = pfc_by_ang[ang]
        home = Vector((0, *polar(PFC_BC, ang)))
        t0 = b5 + 0.15 + k * (DUR["B5"] - 1.6) / 4
        key_loc(root, f(t0), rack[root.name])
        key_loc(root, f(t0 + 0.45), home + Vector((-2.4, 0, 0)))
        key_loc(root, f(t0 + 0.85), home)
        key_hide(nuts[1], f(t0 + 0.85) - 1, True)
        key_hide(nuts[1], f(t0 + 0.85), False)
        key_spin(nuts[0], f(t0 + 0.85), 0)
        key_spin(nuts[0], f(t0 + 1.25), 540)

    # ---- B6 caliper check across the PFC ----------------------------------
    b6 = S["B6"][0]
    j1, j2 = tools["caliper_jaws"]
    key_hide(cal, f(b6 + 0.1), False)
    for jw, sgn in ((j1, -1), (j2, 1)):
        jw.location.x = sgn * 1.0
        jw.keyframe_insert("location", frame=f(b6))
    for k, ang in enumerate(SIDE_ORDER[:2]):
        sp = (DUR["B6"] - 0.6) / 2
        t = b6 + 0.2 + k * sp
        tool_place(cal, f(t), 0.0, ang, PFC_RO + 0.02)
        tool_place(cal, f(t + sp * 0.8), 0.0, ang, PFC_RO + 0.02)
    key_hide(cal, f(S["B6"][1] - 0.2), True)

    # ---- B7 grub screws: No. 1 first, then criss-cross --------------------
    b7 = S["B7"][0]
    for k, ang in enumerate(SIDE_ORDER):
        sp = (DUR["B7"] - 0.6) / 4
        t = b7 + 0.2 + k * sp
        for side in ("L", "R"):
            for cap in lug_by[f"lug{ang}{side}"].children:
                key_spin(cap, f(t), 0)
                key_spin(cap, f(t + sp * 0.8), 360)

    # ---- B8 torque PFC stud bolts: 30 / 60 / 100 %, rolling pass, sound ---
    key_hide(mtw, f(B8_T0 - 0.1), False)
    key_scale(mtw, f(B8_T0 - 0.1), 1.22)
    n = 0
    for r in range(3):
        for k, ang in enumerate(SIDE_ORDER):
            t = B8_T0 + n * B8_STEP
            nut = pfc_by_ang[ang][2][0]
            tool_place(mtw, f(t), x_pnut, ang, PFC_BC, 0)
            tool_place(mtw, f(t + B8_STEP * 0.75), x_pnut, ang, PFC_BC, 25)
            key_spin(nut, f(t), 540 + r * 20)
            key_spin(nut, f(t + B8_STEP * 0.75), 540 + (r + 1) * 20)
            n += 1
    for k, ang in enumerate(SIDE_ORDER):  # rolling pass at 100 %
        t = B8_ROLL + k * 0.3
        tool_place(mtw, f(t), x_pnut, ang, PFC_BC, 0)
        tool_place(mtw, f(t + 0.22), x_pnut, ang, PFC_BC, 10)
    key_hide(mtw, f(B8_ROLL + 1.3), True)
    key_scale(mtw, f(B8_ROLL + 1.3), 1.22)
    for k in range(4):
        t = S["B8"][1] - 0.7 + k * 0.15
        key_emit(M["blue_pfc"], f(t), 0.0)
        key_emit(M["blue_pfc"], f(t + 0.08), 0.5)
        key_emit(M["blue_pfc"], f(t + 0.16), 0.0)

    # ---- C10 replace flange stud bolts one at a time ----------------------
    c10 = S["C10"][0]
    key_scale(mtw, f(c10), 1.0)
    for k, ang in enumerate(FLANGE_ORDER_ANG):
        (old_root, _, old_nuts), (new_root, _, new_nuts) = flange_by_ang[ang]
        t0 = c10 + k * C10_SPAN
        home = old_root.location.copy()
        # socket on the near nut, hammer wrench holding the far nut
        key_hide(sock, f(t0), False)
        key_hide(ham, f(t0), False)
        tool_place(sock, f(t0), x_fnut, ang, BC_R, 0)
        tool_place(sock, f(t0 + 1.1), x_fnut, ang, BC_R, -300)
        tool_place(ham, f(t0), x_bnut, ang, BC_R, 0, side=1)
        tool_place(ham, f(t0 + 1.1), x_bnut, ang, BC_R, 0, side=1)
        key_spin(old_nuts[0], f(t0), 28)
        key_spin(old_nuts[0], f(t0 + 1.1), 28 - 300)
        key_hide(sock, f(t0 + 1.2), True)
        key_hide(ham, f(t0 + 1.2), True)
        key_hide(old_nuts[1], f(t0 + 1.2), True)
        key_loc(old_root, f(t0 + 1.25), home)
        key_loc(old_root, f(t0 + 2.0), home + Vector((-3.6, 0, 0)))
        key_hide(old_root, f(t0 + 2.0), False)
        key_hide(old_root, f(t0 + 2.0) + 1, True)
        # new bolt from the tray
        key_loc(new_root, f(t0 + 1.5), rack[new_root.name])
        key_loc(new_root, f(t0 + 2.2), home + Vector((-3.6, 0, 0)))
        key_loc(new_root, f(t0 + 2.9), home)
        key_hide(new_nuts[1], f(t0 + 2.9) - 1, True)
        key_hide(new_nuts[1], f(t0 + 2.9), False)
        # torque with the calibrated MTW
        key_hide(mtw, f(t0 + 3.0), False)
        tool_place(mtw, f(t0 + 3.0), x_fnut, ang, BC_R, 0)
        tool_place(mtw, f(t0 + 3.7), x_fnut, ang, BC_R, 30)
        key_spin(new_nuts[0], f(t0 + 3.0), 0)
        key_spin(new_nuts[0], f(t0 + 3.7), 30)
        key_hide(mtw, f(t0 + 4.0), True)
    key_scale(mtw, f(c10 + 3 * C10_SPAN + 4.0), 1.0)
    # ---- C11 sound check new bolts ----------------------------------------
    for k in range(4):
        t = S["C11"][0] + 0.4 + k * 0.45
        key_emit(M["blue_new"], f(t), 0.0)
        key_emit(M["blue_new"], f(t + 0.15), 0.5)
        key_emit(M["blue_new"], f(t + 0.35), 0.0)

    # ---- D12 loosen PFC bolts farthest first, withdraw, remove PFC --------
    key_hide(mtw, f(d12 + 0.1), False)
    key_scale(mtw, f(d12 + 0.05), 1.22)
    for k, ang in enumerate(PFC_LOOSEN_ANG):
        root, rod, nuts = pfc_by_ang[ang]
        home = root.location.copy() if False else Vector((0, *polar(PFC_BC, ang)))
        t = d12 + 0.2 + k * 0.6
        tool_place(mtw, f(t), x_pnut, ang, PFC_BC, 25)
        tool_place(mtw, f(t + 0.45), x_pnut, ang, PFC_BC, -20)
        key_spin(nuts[0], f(t), 600)
        key_spin(nuts[0], f(t + 0.45), 560)
        t2 = d12 + 2.0 + k * 0.25
        key_hide(nuts[1], f(t2), True)
        key_loc(root, f(t2), home)
        key_loc(root, f(t2 + 0.9), home + Vector((-4.5, 0, 0)))
        key_hide(root, f(t2 + 0.9), False)
        key_hide(root, f(t2 + 0.9) + 1, True)
    key_hide(mtw, f(d12 + 2.6), True)


def camera_rig():
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    target = bpy.context.object
    target.name = "cam_target"
    bpy.ops.object.camera_add(location=(9, -9, 4))
    cam = bpy.context.object
    cam.data.lens = 50
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = target
    cam.data.dof.aperture_fstop = 5.6
    tr = cam.constraints.new("TRACK_TO")
    tr.target = target
    tr.track_axis = "TRACK_NEGATIVE_Z"
    tr.up_axis = "UP_Y"
    bpy.context.scene.camera = cam

    f = sec
    def stud(ang):
        return (0, *polar(BC_R, ang))

    def st(k, d=0.0):
        return S[k][0] + d

    def en(k, d=0.0):
        return S[k][1] - d

    c10 = S["C10"][0]
    shots = [  # (time, camera location, target location)
        (0.0, (11.5, -10.5, 5.0), (0, 0, 0)),
        (en("est", 0.6), (8.0, -9.5, 3.0), (0, -0.8, -0.6)),
        # A1 Molykote on the tray
        (st("A1", 0.4), (-1.5, -9.8, 1.6), (0, -4.6, -2.4)),
        (en("A1", 0.3), (2.0, -10.0, 1.2), (0, -4.6, -2.4)),
        # A2 caliper around the flange
        (st("A2", 0.3), (-9.6, -8.4, 4.2), (0, 0, -0.2)),
        (en("A2", 0.4), (-9.2, -9.2, 2.4), (0, 0, -0.2)),
        # A3 torque existing bolts
        (st("A3", 0.4), (-9.0, -6.2, 3.6), (-0.4, 0, 0)),
        (en("A3", 0.4), (-9.0, -7.0, 2.0), (-0.4, 0, 0)),
        # B4 install PFC
        (st("B4", 0.4), (-9.8, -8.6, 5.2), (0, 0, 0)),
        (en("B4", 0.3), (-8.8, -9.6, 3.4), (0, 0, 0)),
        # B5 PFC stud bolts from the tray
        (st("B5", 0.3), (-6.5, -11.0, 1.0), (0, -1.6, -0.8)),
        (en("B5", 0.3), (-8.2, -7.4, 2.8), (0, 0, 0)),
        # B6 caliper check
        (st("B6", 0.3), (-6.5, -5.8, 5.6), (0, 0, 2.3)),
        (en("B6", 0.3), (-6.2, -6.4, 3.0), (0, -1.0, 0.0)),
        # B7 grub screws
        (st("B7", 0.3), (-7.4, -3.8, 3.0), (-0.6, 0, 0.6)),
        (en("B7", 0.3), (-7.4, -4.6, 1.6), (-0.6, 0, 0.0)),
        # B8 torque PFC bolts
        (st("B8", 0.3), (-12.0, -8.6, 4.8), (-0.6, 0, 0)),
        (en("B8", 0.3), (-12.0, -7.0, 1.6), (-0.6, 0, 0)),
        # C9 workers upwind: wide, high
        (st("C9", 0.4), (-5.0, -10.0, 8.5), (0, -1.0, 0)),
        (en("C9", 0.3), (-6.0, -9.0, 6.5), (0, -0.5, 0)),
        # C10 four bolts
        (c10 + 0.3, (-8.6, -6.0, 4.6), stud(FLANGE_ORDER_ANG[0])),
        (c10 + 0.3 + C10_SPAN, (-8.6, -6.4, -3.0), stud(FLANGE_ORDER_ANG[1])),
        (c10 + 0.3 + 2 * C10_SPAN, (-8.6, -7.4, 4.0), stud(FLANGE_ORDER_ANG[2])),
        (c10 + 0.3 + 3 * C10_SPAN, (-8.6, -4.6, -3.4), stud(FLANGE_ORDER_ANG[3])),
        # C11 sound check
        (st("C11", 0.3), (-8.6, -6.6, 2.6), (0, 0, 0)),
        # D12 remove PFC
        (st("D12", 0.3), (-9.0, -9.5, 4.0), (0, 0, 0)),
        (en("D12", 0.1), (6.5, -10.0, 3.2), (0, 0, 0)),
        # hero
        (st("hero", 1.6), (9.0, -8.6, 2.8), (0, 0, 0)),
        (en("hero"), (10.5, -7.6, 2.4), (0, 0, 0)),
    ]
    for t, cl, tl in shots:
        key_loc(cam, f(t), cl)
        key_loc(target, f(t), tl)
    return cam


def lights_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("studio")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    mr = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])  # view direction
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value = -0.3
    mr.inputs["From Max"].default_value = 0.9
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (*srgb("#03050F"), 1)
    ramp.color_ramp.elements[1].color = (*srgb("#2A3A6A"), 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.9
    # what metal reflects: a studio with soft horizontal light bands
    refl = nt.nodes.new("ShaderNodeBackground")
    band = nt.nodes.new("ShaderNodeValToRGB")
    band.color_ramp.interpolation = "EASE"
    els = band.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.01, 0.012, 0.025, 1)
    els[1].position, els[1].color = 1.0, (0.02, 0.03, 0.06, 1)
    for pos, col in ((0.40, (0.10, 0.12, 0.18, 1)), (0.52, (4.0, 4.0, 4.2, 1)),
                     (0.60, (0.05, 0.07, 0.12, 1)), (0.72, (1.4, 2.0, 1.9, 1)),
                     (0.82, (0.03, 0.04, 0.08, 1))):
        e = els.new(pos)
        e.color = col
    nt.links.new(mr.outputs["Result"], band.inputs["Fac"])
    nt.links.new(band.outputs["Color"], refl.inputs["Color"])
    refl.inputs["Strength"].default_value = 1.0
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(refl.outputs["Background"], mix.inputs[1])
    nt.links.new(bg.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])

    def area(name, loc, energy, color, size):
        bpy.ops.object.light_add(type="AREA", location=loc)
        l = bpy.context.object
        l.name = name
        l.data.energy = energy
        l.data.color = color
        l.data.size = size
        tr = l.constraints.new("TRACK_TO")
        tr.target = bpy.data.objects["cam_target"]
        tr.track_axis = "TRACK_NEGATIVE_Z"
        tr.up_axis = "UP_Y"
        return l

    area("key", (6, -7, 8), 620, (1.0, 0.97, 0.93), 9)
    area("fill", (-9, -5, 2), 160, (0.85, 0.9, 1.0), 8)
    area("rim_teal", (-3, 9, 5), 650, srgb("#3BB3A4"), 5)
    area("soft_left", (-7, -9, 7), 380, (1.0, 1.0, 1.0), 9)
    area("top", (0, 0, 10), 180, (1, 1, 1), 10)


def build_scene():
    clear()
    M = dict(
        pipe=mat("pipe", srgb("#8C949E"), metal=0.85, rough=0.38),
        flange=mat("flange", srgb("#17191E"), metal=0.3, rough=0.5, coat=0.35),
        machined_jaw=mat("machined_jaw", srgb("#C4C9D0"), metal=1.0, rough=0.4, aniso=0.6),
        machined_face=mat("machined_face", srgb("#B9BEC6"), metal=1.0, rough=0.42, aniso=0.6),
        gasket=mat("gasket", srgb("#20242C"), rough=0.7),
        machined=mat("machined", srgb("#D2D7DE"), metal=1.0, rough=0.3, aniso=0.5),
        blue=mat("blue", srgb("#1A47B8"), metal=0.0, rough=0.42, coat=0.15),
        blue_new=mat("blue_new", srgb("#1A47B8"), metal=0.0, rough=0.42, coat=0.15,
                     emit=srgb("#6FD3C6"), emit_strength=0.0),
        blue_pfc=mat("blue_pfc", srgb("#1A47B8"), metal=0.0, rough=0.42, coat=0.15,
                     emit=srgb("#6FD3C6"), emit_strength=0.0),
        chrome=mat("chrome", srgb("#D9DDE3"), metal=1.0, rough=0.18),
        chrome_dark=mat("chrome_dark", srgb("#7D848E"), metal=1.0, rough=0.25),
        tool_dark=mat("tool_dark", srgb("#2A2E35"), metal=0.8, rough=0.45),
        grip=mat("grip", srgb("#111317"), rough=0.7),
        red_handle=mat("red_handle", srgb("#B3262E"), rough=0.5, coat=0.4),
        bristle=mat("bristle", srgb("#2B2B2B"), rough=0.9),
        teal_glow=mat("teal_glow", srgb("#0E4F5A"), rough=0.3, emit=srgb("#6FD3C6"),
                      emit_strength=2.0),
        marker=mat("marker", srgb("#F2F2F2"), rough=0.6, emit=srgb("#FFFFFF"), emit_strength=0.4),
        tray=mat("tray", srgb("#1E232C"), metal=0.5, rough=0.55),
        old_rod=mat("old_rod", srgb("#4A4038"), metal=0.7, rough=0.65),
        old_nut=mat("old_nut", srgb("#4A4038"), metal=0.7, rough=0.65,
                    emit=srgb("#6FD3C6"), emit_strength=0.0),
        dark=mat("dark", srgb("#15181E"), metal=0.8, rough=0.4),
        fluid=fluid_material(),
    )
    build_joint(M)
    studs = build_flange_studs(M)
    jaws, lugs, pfc_studs = build_pfc(M)
    tools = build_tools(M)
    nums = build_numbers(M)
    tray, rack = build_tray(M, studs, pfc_studs)
    camera_rig()
    lights_world()
    animate(studs, jaws, lugs, pfc_studs, M, tools, nums, tray, rack)
    linear_all(bpy.data.materials["fluid"].node_tree)  # constant flow speed
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, sec(T["end"]) - 1
    sc.render.fps = FPS
    return M


def configure_render(engine, res, samples, out_dir):
    sc = bpy.context.scene
    w, h = res
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(out_dir, "f_")
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    if engine == "CYCLES":
        sc.render.engine = "CYCLES"
        sc.cycles.device = "CPU"
        sc.cycles.samples = samples
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.adaptive_threshold = 0.03
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.max_bounces = 4
        sc.cycles.diffuse_bounces = 2
        sc.cycles.glossy_bounces = 3
        sc.cycles.transmission_bounces = 0
        sc.cycles.caustics_reflective = False
        sc.cycles.caustics_refractive = False
        sc.render.use_persistent_data = True
    elif engine == "WORKBENCH":  # fast animatic for checking timing
        sc.render.engine = "BLENDER_WORKBENCH"
        sc.display.shading.color_type = "MATERIAL"
        sc.display.shading.light = "STUDIO"
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
    else:
        sc.render.engine = "BLENDER_EEVEE"
        sc.eevee.taa_render_samples = samples


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--engine", default="CYCLES")
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--frames", default=None, help="A-B or comma list")
    ap.add_argument("--blend", default=None)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    build_scene()
    configure_render(a.engine, tuple(int(x) for x in a.res.split("x")), a.samples, a.out)
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
    sc = bpy.context.scene
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
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("frame", fr, flush=True)


if __name__ == "__main__":
    main()
