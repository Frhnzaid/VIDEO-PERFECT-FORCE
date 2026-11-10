"""3D 'How it works' animation of the Perfect Force Clamp (Blender, bpy).

    python pfc_edit/pfc3d.py --out DIR [--res 1920x1080] [--engine EEVEE|CYCLES]
                             [--frames A-B] [--samples N] [--blend file.blend]

Scene: a 4-stud-bolt flanged joint on a live line (cut-away pipe with moving
fluid) and the PFC: two rings of four segments each, joined by four PFC stud
bolts outside the flange OD. Proportions follow the reference photos; they are
illustrative, not to scale.

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

import bpy
from mathutils import Vector

FPS = 24
T = dict(est=0.0, A=3.5, B=8.5, C=17.5, D=33.5, hero=39.5, end=43.0)

# ----------------------------------------------------------------- sizes ---
PIPE_R, PIPE_BORE = 0.36, 0.29
FL_R, FL_T, GAP = 1.6, 0.35, 0.05          # flange radius, thickness, gasket gap
HUB_R0, HUB_R1, HUB_L = 0.72, PIPE_R, 0.5  # weld-neck hub
BC_R = 1.2                                 # flange bolt circle
STUD_R, NUT_AF, NUT_T = 0.10, 0.34, 0.22
RING_RO, RING_RI, RING_T = 2.35, 0.86, 0.40
PFC_BC, PFC_STUD_R, PFC_NUT_AF, PFC_NUT_T = 1.98, 0.13, 0.42, 0.28
X_FL = GAP / 2 + FL_T                      # outer face of each flange
X_RING = X_FL + RING_T                     # outer face of each PFC ring

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


def bevel(o, w=0.012, seg=2):
    m = o.modifiers.new("bev", "BEVEL")
    m.width = w
    m.segments = seg
    m.limit_method = "ANGLE"
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
                            M["blue"], M["blue"])
        studs.append((old, new))
    return studs


def build_ring(name, x0, x1, M):
    ring = cyl_x(name, RING_RO, x0, x1, verts=160)
    inner = cyl_x("ri", RING_RI, x0 - 0.1, x1 + 0.1, verts=96)
    boolean(ring, inner)
    # slots for the flange nuts on the diagonals
    for a in FLANGE_ANG:
        y, z = polar(BC_R, a)
        s = cyl_x("slot", 0.30, x0 - 0.1, x1 + 0.1, verts=48, y=y, z=z)
        boolean(ring, s)
        yc, zc = polar(BC_R * 0.55, a)
        sb = box("slotb", (abs(x1 - x0) + 0.2, 0.6, BC_R * 1.1),
                 ((x0 + x1) / 2, yc, zc), (math.radians(a - 90), 0, 0))
        boolean(ring, sb)
    # PFC stud holes
    for a in PFC_ANG:
        y, z = polar(PFC_BC, a)
        h = cyl_x("ph", PFC_STUD_R * 1.12, x0 - 0.1, x1 + 0.1, verts=32, y=y, z=z)
        boolean(ring, h)
    # grooves on the jaw faces (machined ribs, as in the photos)
    for a in FLANGE_ANG:
        for k in range(-3, 4):
            g = box("rib", (abs(x1 - x0) + 0.2, 0.025, 0.06),
                    ((x0 + x1) / 2, *polar(RING_RO, a + k * 4.0)),
                    (math.radians(a + k * 4.0), 0, 0))
            boolean(ring, g)
    # split into four segments along the diagonals
    for a in FLANGE_ANG:
        yc, zc = polar(RING_RO * 0.75, a)
        cut = box("split", (abs(x1 - x0) + 0.3, 0.035, RING_RO * 1.0),
                  ((x0 + x1) / 2, yc, zc), (math.radians(a - 90), 0, 0))
        boolean(ring, cut)
    set_mat(ring, M["machined"])
    activate(ring)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    segs = [o for o in bpy.context.selected_objects]
    for o in segs:
        set_origin_center(o)
        bevel(o, 0.015)
        smooth(o)
        # grub screw on the outer rim of each segment
        oy, oz = o.location.y, o.location.z
        ang = math.degrees(math.atan2(oz, oy))
        gy, gz = polar(RING_RO, ang)
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.05, depth=0.08,
                                            location=((x0 + x1) / 2, gy, gz),
                                            rotation=(math.radians(ang - 90), 0, 0))
        gs = bpy.context.object
        set_mat(gs, M["dark"])
        gs.parent = o
        gs.matrix_parent_inverse = o.matrix_world.inverted()
    return segs


def build_pfc(M):
    rings = build_ring("ringL", -X_RING, -X_FL - 0.002, M) + build_ring("ringR", X_FL + 0.002, X_RING, M)
    studs = []
    for i, a in enumerate(PFC_ANG):
        studs.append(stud_assembly(f"pfc{i}", a, PFC_BC, PFC_STUD_R, PFC_NUT_AF, PFC_NUT_T,
                                   X_RING, 0.22, M["blue"], M["blue"]))
    return rings, studs


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


def animate(studs, rings, pfc_studs, M):
    f = sec
    # --- A: torque pulses on existing studs (criss-cross) -----------------
    for k, i in enumerate(REPLACE_ORDER):
        old_root = studs[i][0][0]
        t0 = T["A"] + 0.6 + k * 0.9
        for nut in studs[i][0][2]:
            key_rot(nut, f(t0), (0, 0, 0))
            key_rot(nut, f(t0 + 0.6), (math.radians(20), 0, 0))
    for k in range(4):
        t0 = T["A"] + 0.6 + k * 0.9
        key_emit(M["old_nut"], f(t0), 0.0)
        key_emit(M["old_nut"], f(t0 + 0.3), 1.5)
        key_emit(M["old_nut"], f(t0 + 0.7), 0.0)

    # --- B: PFC segments slide in radially, studs in, nuts torqued --------
    for k, seg in enumerate(rings):
        home = seg.location.copy()
        dirv = Vector((0, home.y, home.z)).normalized()
        away = home + dirv * 3.5 + Vector((math.copysign(1.2, home.x), 0, 0))
        t0 = T["B"] + 0.2 + (k % 4) * 0.35 + (0.15 if home.x > 0 else 0)
        key_hide(seg, 1, True)
        key_hide(seg, f(t0) - 1, True)
        key_hide(seg, f(t0), False)
        key_loc(seg, f(t0), away)
        key_loc(seg, f(t0 + 1.1), home)
        # removal in D
        t1 = T["D"] + 2.6 + (k % 4) * 0.3
        key_loc(seg, f(t1), home)
        key_loc(seg, f(t1 + 1.1), away)
        key_hide(seg, f(t1 + 1.1), False)
        key_hide(seg, f(t1 + 1.1) + 1, True)
    for k, (root, rod, nuts) in enumerate(pfc_studs):
        t0 = T["B"] + 2.6 + k * 0.35
        home = root.location.copy()
        key_hide(root, 1, True)
        key_hide(root, f(t0) - 1, True)
        key_hide(root, f(t0), False)
        key_loc(root, f(t0), home + Vector((-5.0, 0, 0)))
        key_loc(root, f(t0 + 1.0), home)
        # torque stages: three small nut turns
        for s, ts in enumerate((5.0, 6.2, 7.4)):
            for nut in nuts:
                key_rot(nut, f(T["B"] + ts), (math.radians(s * 40), 0, 0))
                key_rot(nut, f(T["B"] + ts + 0.6), (math.radians((s + 1) * 40), 0, 0))
        # D: loosen and withdraw
        t1 = T["D"] + 0.3 + k * 0.3
        for nut in nuts:
            key_rot(nut, f(t1), (math.radians(120), 0, 0))
            key_rot(nut, f(t1 + 0.8), (0, 0, 0))
        key_loc(root, f(t1 + 0.8), home)
        key_loc(root, f(t1 + 2.0), home + Vector((5.5, 0, 0)))
        key_hide(root, f(t1 + 2.0), False)
        key_hide(root, f(t1 + 2.0) + 1, True)

    # --- C: replace flange studs one at a time ----------------------------
    span = (T["D"] - T["C"]) / 4
    for k, i in enumerate(REPLACE_ORDER):
        (old_root, old_rod, old_nuts), (new_root, new_rod, new_nuts) = studs[i]
        t0 = T["C"] + k * span
        home = old_root.location.copy()
        # unscrew far nut, withdraw old stud
        for nut in old_nuts:
            key_rot(nut, f(t0 + 0.2), (0, 0, 0))
            key_rot(nut, f(t0 + 1.2), (math.radians(-360), 0, 0))
        key_loc(old_root, f(t0 + 1.2), home)
        key_loc(old_root, f(t0 + 2.1), home + Vector((-3.6, 0, 0)))  # out towards camera
        key_hide(old_root, f(t0 + 2.1), False)
        key_hide(old_root, f(t0 + 2.1) + 1, True)
        # new stud slides in from the same side and is torqued
        key_hide(new_root, 1, True)
        key_hide(new_root, f(t0 + 2.3) - 1, True)
        key_hide(new_root, f(t0 + 2.3), False)
        key_loc(new_root, f(t0 + 2.3), home + Vector((-3.6, 0, 0)))
        key_loc(new_root, f(t0 + 3.2), home)
        for nut in new_nuts:
            key_rot(nut, f(t0 + 3.2), (math.radians(360), 0, 0))
            key_rot(nut, f(t0 + 3.9), (0, 0, 0))


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
    shots = [  # (time, camera location, target location)
        (0.0, (10.5, -9.5, 4.6), (0, 0, 0)),
        (3.5, (7.5, -8.0, 3.2), (0, 0, 0)),
        (8.5, (5.5, -8.2, 4.2), (0, 0, 0.2)),
        (12.0, (-6.5, -7.2, 3.6), (0, 0, 0.2)),
        (17.5, (-6.5, -4.5, 4.0), (0, *polar(BC_R, FLANGE_ANG[REPLACE_ORDER[0]]))),
        (21.5, (-6.5, -5.0, -2.5), (0, *polar(BC_R, FLANGE_ANG[REPLACE_ORDER[1]]))),
        (25.5, (-6.5, -6.0, 3.5), (0, *polar(BC_R, FLANGE_ANG[REPLACE_ORDER[2]]))),
        (29.5, (-6.5, -3.5, -3.0), (0, *polar(BC_R, FLANGE_ANG[REPLACE_ORDER[3]]))),
        (33.5, (-8.0, -8.5, 3.6), (0, 0, 0)),
        (39.5, (8.5, -8.0, 2.6), (0, 0, 0)),
        (43.0, (10.0, -7.0, 2.2), (0, 0, 0)),
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
        flange=mat("flange", srgb("#2C3038"), metal=0.6, rough=0.45, coat=0.3),
        gasket=mat("gasket", srgb("#20242C"), rough=0.7),
        machined=mat("machined", srgb("#D2D7DE"), metal=1.0, rough=0.3, aniso=0.5),
        blue=mat("blue", srgb("#1A47B8"), metal=0.0, rough=0.42, coat=0.15),
        old_rod=mat("old_rod", srgb("#4A4038"), metal=0.7, rough=0.65),
        old_nut=mat("old_nut", srgb("#4A4038"), metal=0.7, rough=0.65,
                    emit=srgb("#6FD3C6"), emit_strength=0.0),
        dark=mat("dark", srgb("#15181E"), metal=0.8, rough=0.4),
        fluid=fluid_material(),
    )
    build_joint(M)
    studs = build_flange_studs(M)
    rings, pfc_studs = build_pfc(M)
    camera_rig()
    lights_world()
    animate(studs, rings, pfc_studs, M)
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
