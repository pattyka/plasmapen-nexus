"""Package S — the shell: alu housing, frosted PC end cap, cover glass, button.

One tensioned side line (two parabolas meeting with zero slope at x_max, BRIEF "Outer form"),
cut by two planes: the display flat on top, the dock flat underneath. Because the planes cut a
body whose radius changes, both flats come out drop-shaped and their 45° chamfer reads as a line
of varying width. Every other exterior edge is a 45° segment inside a revolve or cut profile
(joint chamfers, the Kamm cut at the tail, the joint V across the flats), so it cannot fail.

Build order of the housing (each step is one Fusion feature):
    stock tube r bore_r … body_r + 0.5 (the extrusion blank) → join the two D-flat wall segments
    of the bore → revolve cut of everything outside the outer line (turns the blank) → rail
    grooves → top / bottom flat cuts → facet chamfers → joint V across both flats → glass
    pocket (+ corner radii) → panel window → button hole.
The cap repeats the flats, the chamfers and the V, then adds the Kamm cut across the flats,
the dock pocket, the pad holes and the blind magnet seats.

Interface for the other packages (all expressions use pp_params names only, so a module that
may not import this one can copy them verbatim):
    outer_r(x)     outer radius of housing / cap at x, nose_split ≤ x ≤ pen_len
    bore()         the housing bore section (constant along X)
    cap_lugs()     the bayonet lugs on the cap spigot that pass through B3 (H cuts the slots)
"""

import math

from pp_core import neg


def outer_r(x):
    """Outer radius at x as a Fusion expression (pp_params names only). Front parabola for
    x ≤ x_max, rear parabola beyond. Over the cap a boat tail closes it by tail_dr more,
    starting with zero slope at body_end (the joint stays G1), so the flats narrow into the
    Kamm cut and the tail reads as the end of the drop, not as a plug. Written
    as one expression, r = body_r − kf·s² (s < 0) / − kr·s² (s > 0), s = x − x_max, so it stays
    valid whichever side of x_max a parameter change moves x to."""
    s = f"(({x}) - x_max)"
    kf = "(body_r - body_r0) / (x_max - nose_split) ^ 2"
    kr = "(body_r - body_rt) / (body_end - x_max) ^ 2"
    c = f"(({x}) - body_end + abs(({x}) - body_end)) / 2 / cap_len"   # 0 before the cap
    return (f"(body_r - {s} ^ 2 * ({kf} + {kr}) / 2 - {s} * abs{s} * ({kr} - {kf}) / 2"
            f" - tail_dr * ({c}) ^ 2)")


_R_GLASS_X1 = outer_r("glass_x1")

EXTRA_PARAMS = [
    ("shell_stock", "body_r + 0.5 mm", "mm", "Nyers cső külső sugara (esztergálás előtt)"),
    ("shell_seg_t", "sqrt(bore_r ^ 2 - bore_top ^ 2)", "mm", "= felső furatsík fél szélessége"),
    ("shell_seg_b", "sqrt(bore_r ^ 2 - bore_bot ^ 2)", "mm", "= alsó furatsík fél szélessége"),
    ("shell_cut_w", "body_od + 8 mm", "mm", "Lapos vágások szélessége (Z)"),
    ("shell_top_e", "top_y + top_rise * ((body_end - tc_x2) / (pen_len + 1 mm - tc_x2)) ^ 2",
     "mm", "= felső sík magassága a ház | kupak illesztésnél"),
    ("shell_top_t", "top_y + top_rise * ((pen_len - tc_x2) / (pen_len + 1 mm - tc_x2)) ^ 2",
     "mm", "= felső sík magassága a kupak végén"),
    ("shell_hole_ch", "0.2 mm", "mm", "Gombfurat peremének élletörése"),
    ("shell_cap_x0", "body_end - cap_spigot", "mm", "= kupak csap eleje"),
    ("shell_sp_r", "bore_top - 0.15 mm", "mm", "Kupak csap sugara (befér a felső furatsík alá)"),
    ("shell_cav_r", "8 mm", "mm", "Kupak belső üreg sugara (dokk flex, antenna)"),
    ("shell_dock_z", "8 mm", "mm", "Dokk zseb fél szélessége (Z)"),
    ("shell_cap_hz", "sqrt((" + outer_r("pen_len - cap_rear") + " - 1.4 mm) ^ 2 - (shell_top_e"
     " - 1.6 mm) ^ 2)", "mm", "= kupak üreg fél szélessége (1,4 mm PC fal a hátsó sarkánál)"),
    ("shell_lug_w", "3 mm", "mm", "Bajonett fül szélessége (Y)"),
    ("shell_lug_h", "1.5 mm", "mm", "Bajonett fül radiális magassága"),
    ("shell_btn_t", "1.6 mm", "mm", "Gombsapka vastagság"),
    ("shell_btn_ch", "0.3 mm", "mm", "Gombsapka élletörése"),
    ("shell_btn_stem", "1.5 mm", "mm", "Gomb szár sugara (Ø3)"),
    ("shell_chk_wall_tail", "body_rt - bore_r - shell_wall", "mm",
     "ELLENŐRZÉS: alu fal a ház hátsó végén ≥ shell_wall"),
    ("shell_chk_rail", "body_r0 - joint_ch - bore_r - rail_d - 0.2 mm", "mm",
     "ELLENŐRZÉS: alu a vezetőhorony fölött az elülső élnél ≥ 0,2 mm"),
    ("shell_chk_land", "sqrt(" + _R_GLASS_X1 + " ^ 2 - top_y ^ 2) - glass_w / 2 - glass_c - top_ch"
     " - 0.5 mm", "mm", "ELLENŐRZÉS: alu perem az üveg hátsó vége mellett ≥ 0,5 mm"),
    ("shell_chk_btn", "top_y + btn_proud - shell_btn_t - bore_top", "mm",
     "ELLENŐRZÉS: gombsapka a falban ül (nem lóg a furatba)"),
    ("shell_chk_spigot", "bore_top - shell_sp_r - 0.1 mm", "mm",
     "ELLENŐRZÉS: kupak csap ↔ felső furatsík hézag ≥ 0,1 mm"),
    ("shell_chk_lug", "bore_top + 0.1 mm - sqrt((bore_top - 0.3 mm) ^ 2 + (1.5 mm) ^ 2) - 0.15 mm",
     "mm", "ELLENŐRZÉS: bajonett fül sarka ↔ B3 horony (r ≤ bore_top + 0,1) ≥ 0,15 mm"),
    ("shell_chk_tail", "sqrt(" + outer_r("pen_len - cap_ch") + " ^ 2 - bot_y ^ 2) - bot_ch - 2 mm",
     "mm", "ELLENŐRZÉS: a dokk sík a Kamm-vágásnál is ≥ 2 mm széles (fél szélesség)"),
    ("shell_chk_cav", "bot_y - cap_floor - shell_cav_r - 1 mm", "mm",
     "ELLENŐRZÉS: dokk zseb mélyebb az üregnél (a NYÁK befér)"),
]

N_FIT = 8          # fit points per formula (BRIEF: ≥ 8)
N_EASE = 10        # fit points of the fade / rise splines of the flat cuts


# ─────────────────────────────────────────────────────────────────────────────
# Interface
# ─────────────────────────────────────────────────────────────────────────────

def bore():
    """The housing bore section, constant over body_x0 … body_end: circle r, flat at y = top,
    flat at y = −bot, rail grooves at z = ±r (|y| ≤ rail_w/2, from z0 to z1)."""
    return {"r": "bore_r", "top": "bore_top", "bot": "bore_bot",
            "rail_w": "rail_w", "rail_z0": "bore_r - 0.3 mm", "rail_z1": "bore_r + rail_d"}


def cap_lugs():
    """Bayonet lugs on the cap spigot at θ = ±90° (z > 0 and z < 0): boxes x b3_x0 …
    body_end − cap_spigot, |y| ≤ 1.5 mm, |z| from bore_top − 1.65 mm to bore_top − 0.3 mm
    (outer corner at r 8.85 for the defaults). They pass through B3's slots (pp_insert: 3.4 mm
    wide, r 6 … bore_top + 0.1 mm), ≥ 0.2 mm clear on every side."""
    return {"x0": "b3_x0", "x1": "body_end - cap_spigot", "y": "1.5 mm",
            "z0": "bore_top - 1.65 mm", "z1": "bore_top - 0.3 mm"}


# ─────────────────────────────────────────────────────────────────────────────
# Profiles
# ─────────────────────────────────────────────────────────────────────────────

def _r_at(x):
    return outer_r(x)


def _fit(x0, x1, n=N_FIT):
    """n points of the outer formula strictly after x0 up to x1 (inclusive), evenly in x."""
    return [(f"{x0} + ({x1} - ({x0})) * {k} / {n}" if k < n else x1,
             _r_at(f"{x0} + ({x1} - ({x0})) * {k} / {n}" if k < n else x1))
            for k in range(1, n + 1)]


def _housing_line():
    """The housing's outer line from the front face to the rear face: front joint chamfer
    (45°) → spline through the front and rear formula → rear face at full radius. The rear
    joint chamfer is a separate ring cut (_ring_ch) made after the facet chamfers, so those
    end cleanly on the end face instead of running onto a 0.3 mm cone."""
    xa = "body_x0 + joint_ch"
    return [
        ("body_x0", f"{_r_at('body_x0')} - joint_ch"),
        (xa, _r_at(xa)),
        ("spline", _fit(xa, "x_max") + _fit("x_max", "body_end")),
    ]


def _ring_ch(x_face, ch, sign):
    """Revolve-cut profile of a 45° ring chamfer `ch` on the outer edge of the end face at
    x_face; sign = −1: the material lies in front of the face (housing rear, cap tail),
    +1: behind it (cap front)."""
    x_in = f"{x_face} - {ch}" if sign < 0 else f"{x_face} + {ch}"
    x_out = f"{x_face} + 1 mm" if sign < 0 else f"{x_face} - 1 mm"
    return [(x_in, _r_at(x_in)), (x_face, f"{_r_at(x_in)} - {ch}"),
            (x_out, f"{_r_at(x_in)} - {ch}"), (x_out, "body_r + 1 mm"),
            (x_in, "body_r + 1 mm")]


def _ease_down(n=N_EASE):
    """Fractions s ∈ (0, 1], dense toward s = 1 (where the fade must meet the flat level)."""
    return [math.sin(math.pi / 2 * k / n) for k in range(1, n + 1)]


def _ease_up(n=N_EASE):
    """Fractions s ∈ (0, 1], dense toward s = 0 (where the rise leaves the flat level)."""
    return [1 - math.cos(math.pi / 2 * k / n) for k in range(1, n + 1)]


def _top_cut():
    """Side-view profile of everything above the display flat: fade-in from above the surface
    at tc_x0, level from tc_x1 to tc_x2, rising by top_rise to the tail (zero slope at both
    ends of the level stretch)."""
    y0 = f"{_r_at('tc_x0')} + 0.8 mm"
    fade = []
    for s in _ease_down():
        if s >= 1 - 1e-12:
            fade.append(("tc_x1", "top_y"))
        else:
            fade.append((f"tc_x0 + (tc_x1 - tc_x0) * {s:.6f}",
                         f"top_y + ({y0} - top_y) * {(1 - s) ** 2:.6f}"))
    rise = []
    for s in _ease_up():
        if s >= 1 - 1e-12:
            rise.append(("pen_len + 1 mm", "top_y + top_rise"))
        else:
            rise.append((f"tc_x2 + (pen_len + 1 mm - tc_x2) * {s:.6f}",
                         f"top_y + top_rise * {s * s:.6f}"))
    return [("tc_x0", y0), ("spline", fade), ("tc_x2", "top_y"), ("spline", rise),
            ("pen_len + 1 mm", "body_r + 6 mm"), ("tc_x0", "body_r + 6 mm")]


def _bottom_cut():
    """Everything below the dock flat: fade-in from below the surface at bc_x0, level from
    bc_x1 to the tail."""
    y0 = f"{_r_at('bc_x0')} + 0.8 mm"
    fade = []
    for s in _ease_down():
        if s >= 1 - 1e-12:
            fade.append(("bc_x1", neg("bot_y")))
        else:
            fade.append((f"bc_x0 + (bc_x1 - bc_x0) * {s:.6f}",
                         neg(f"bot_y + ({y0} - bot_y) * {(1 - s) ** 2:.6f}")))
    return [("bc_x0", neg(y0)), ("spline", fade), ("pen_len + 1 mm", neg("bot_y")),
            ("pen_len + 1 mm", neg("body_r + 6 mm")), ("bc_x0", neg("body_r + 6 mm"))]


def _joint_v_top():
    """45° V across the display flat at the housing | cap joint (each part keeps its half),
    the same joint_ch as the ring chamfers carried by the revolve profiles."""
    return [("body_end - joint_ch - 1 mm", "shell_top_e + 1 mm"),
            ("body_end", "shell_top_e - joint_ch"),
            ("body_end + joint_ch + 1 mm", "shell_top_e + 1 mm")]


def _joint_v_bottom():
    return [("body_end - joint_ch - 1 mm", neg("bot_y + 1 mm")),
            ("body_end + joint_ch + 1 mm", neg("bot_y + 1 mm")),
            ("body_end", "joint_ch - bot_y")]


def _kamm_top():
    """The Kamm cut (cap_ch at 45°) continued across the display flat at the tail."""
    return [("pen_len - cap_ch - 1 mm", "shell_top_t + 1 mm"),
            ("pen_len", "shell_top_t - cap_ch"),
            ("pen_len + 1 mm", "shell_top_t - cap_ch"),
            ("pen_len + 1 mm", "shell_top_t + 1 mm")]


def _kamm_bottom():
    return [("pen_len - cap_ch - 1 mm", neg("bot_y + 1 mm")),
            ("pen_len + 1 mm", neg("bot_y + 1 mm")),
            ("pen_len + 1 mm", "cap_ch - bot_y"),
            ("pen_len", "cap_ch - bot_y")]


def _vertical_cyl(xc, r, y0, y1):
    """Profile for a cylinder along Y at x = xc (revolve about segment 3, the axis line)."""
    return [(xc, y0), (f"{xc} + {r}", y0), (f"{xc} + {r}", y1), (xc, y1)]


def _rim(cut, *faces_x):
    """Chamfer selector: the outer rim of a flat cut, without its edges on the given end
    faces (those are broken by the joint V / the Kamm cut instead)."""
    sel = ("op_edges", cut, "outer")
    for x in faces_x:
        sel = ("minus", sel, ("plane_x", x))
    return [sel]


# ─────────────────────────────────────────────────────────────────────────────
# Parts
# ─────────────────────────────────────────────────────────────────────────────

def _flats(bk, comp, body, what, faces_x):
    """Top and bottom flat cuts on `body` + their facet chamfers. Returns (top_op, bottom_op)."""
    top = bk.extrude_sym(comp, f"Kijelző sík ({what})", _top_cut(), "shell_cut_w", op="cut",
                         targets=[body])
    bot = bk.extrude_sym(comp, f"Dokk sík ({what})", _bottom_cut(), "shell_cut_w", op="cut",
                         targets=[body])
    bk.chamfer(comp, f"Kijelző sík éle ({what})", body, _rim(top, *faces_x), "top_ch")
    bk.chamfer(comp, f"Dokk sík éle ({what})", body, _rim(bot, *faces_x), "bot_ch")
    return top, bot


def _housing(bk, parent, cutaway):
    comp = bk.component(parent, "Ház (alu)")
    h = bk.tube_x(comp, "Ház", "body_x0", "body_end", "shell_stock", "bore_r", look="alu",
                  material="aluminum").body
    # the bore's two flat walls (extruded double-D section)
    bk.box(comp, "Furat felső sík", "body_x0", "body_end", "bore_top", "bore_r + 0.5 mm",
           neg("shell_seg_t + 0.5 mm"), "shell_seg_t + 0.5 mm", op="join", targets=[h])
    bk.box(comp, "Furat alsó sík", "body_x0", "body_end", neg("bore_r + 0.5 mm"),
           neg("bore_bot"), neg("shell_seg_b + 0.5 mm"), "shell_seg_b + 0.5 mm", op="join",
           targets=[h])
    # turned outside: everything beyond the tensioned line goes
    bk.revolve(comp, "Külső forma", [("body_x0 - 1 mm", f"{_r_at('body_x0')} - joint_ch")]
               + _housing_line()
               + [("body_end + 1 mm", _r_at("body_end")),
                  ("body_end + 1 mm", "body_r + 6 mm"), ("body_x0 - 1 mm", "body_r + 6 mm")],
               op="cut", targets=[h])
    for side, z0, z1 in (("+", "bore_r - 0.3 mm", "bore_r + rail_d"),
                         ("−", neg("bore_r + rail_d"), neg("bore_r - 0.3 mm"))):
        bk.box(comp, f"Vezetőhorony {side}", "body_x0 - 1 mm", "body_end + 1 mm",
               neg("rail_w / 2"), "rail_w / 2", z0, z1, op="cut", targets=[h])

    _flats(bk, comp, h, "ház", ["body_end"])
    bk.revolve(comp, "Illesztés letörés", _ring_ch("body_end", "joint_ch", -1), op="cut",
               targets=[h])
    bk.extrude_sym(comp, "Illesztés V (fent)", _joint_v_top(), "shell_cut_w", op="cut",
                   targets=[h])
    bk.extrude_sym(comp, "Illesztés V (lent)", _joint_v_bottom(), "shell_cut_w", op="cut",
                   targets=[h])

    # cover glass pocket, flush: glass + glass_c all round, corners glass_r + glass_c
    px0, px1 = "glass_x0 - glass_c", "glass_x1 + glass_c"
    pz = "glass_w / 2 + glass_c"
    bk.box(comp, "Üvegzseb", px0, px1, "top_y - glass_t", "top_y + 1 mm", neg(pz), pz,
           op="cut", targets=[h])
    bk.fillet(comp, "Üvegzseb sarkai", h,
              [("line_y", x, z) for x in (px0, px1) for z in (pz, neg(pz))], "glass_r + glass_c")
    # panel window: the AMOLED sits in the wall, its FPC drops into the bore
    wz = "oled_w / 2 + 0.1 mm"
    bk.box(comp, "Panelablak", "oled_x0 - 0.1 mm", "oled_x1 + 0.1 mm", "bore_top - 1 mm",
           "top_y", neg(wz), wz, op="cut", targets=[h])
    fz = "oled_fpc_w / 2 + 0.5 mm"  # room for the FPC bend behind the panel
    bk.box(comp, "FPC rés", "oled_x1 - 1 mm", "oled_x1 + oled_fpc_bend + 0.9 mm", "bore_top - 1 mm",
           "top_y - glass_t", neg(fz), fz, op="cut", targets=[h])
    hole = bk.revolve(comp, "Gombfurat",
                      _vertical_cyl("btn_x", "(btn_d + 0.3 mm) / 2", "bore_top - 1 mm",
                                    "top_y + 1 mm"), axis=3, op="cut", targets=[h])
    bk.chamfer(comp, "Gombfurat éle", h,
               [("minus", ("op_edges", hole, "outer"), ("plane_y", "bore_top"))],
               "shell_hole_ch")
    if cutaway:
        bk.cut_half(comp, "Metszet", [h])
    return comp


def _cap(bk, parent, cutaway):
    comp = bk.component(parent, "Hátsó kupak (PC)")
    cap = bk.revolve(comp, "Kupak", [
        ("shell_cap_x0", "shell_cav_r"),
        ("shell_cap_x0", "shell_sp_r"),
        ("body_end", "shell_sp_r"),
        ("body_end", _r_at("body_end")),
        ("spline", _fit("body_end", "pen_len")),
        ("pen_len", "0 mm"),
        ("pen_len - cap_rear", "0 mm"),
        ("pen_len - cap_rear", "shell_cav_r"),
    ], look="glass_frost", material="plastic").body
    lug = cap_lugs()
    for side, z0, z1 in (("+", lug["z0"], lug["z1"]), ("−", neg(lug["z1"]), neg(lug["z0"]))):
        bk.box(comp, f"Bajonett fül {side}", lug["x0"], "shell_cap_x0 + 0.5 mm",
               neg(lug["y"]), lug["y"], z0, z1, op="join", targets=[cap])

    _flats(bk, comp, cap, "kupak", ["body_end", "pen_len"])
    bk.revolve(comp, "Illesztés letörés", _ring_ch("body_end", "joint_ch", 1), op="cut",
               targets=[cap])
    bk.revolve(comp, "Kamm-vég", _ring_ch("pen_len", "cap_ch", -1), op="cut", targets=[cap])
    for name, pts in (("Illesztés V (fent)", _joint_v_top()),
                      ("Illesztés V (lent)", _joint_v_bottom()),
                      ("Kamm-vég (fent)", _kamm_top()), ("Kamm-vég (lent)", _kamm_bottom())):
        bk.extrude_sym(comp, name, pts, "shell_cut_w", op="cut", targets=[cap])

    # coax from the AI board's u.FL passes the spigot wall beside the cell (pp_electronics)
    bk.box(comp, "Koax rés", "shell_cap_x0 - 0.1 mm", "shell_cap_x0 + 1.7 mm",
           "bat_y - 0.6 mm", "bat_y + 0.55 mm", "shell_cav_r - 1 mm", "shell_sp_r + 0.2 mm",
           op="cut", targets=[cap])
    # hollow light guide: even 1.4 mm+ walls under the flats and at the sides, lighter tail
    bk.box(comp, "Kupak üreg", "body_end + 1 mm", "pen_len - cap_rear", "-3 mm",
           "shell_top_e - 1.6 mm", neg("shell_cap_hz"), "shell_cap_hz", op="cut",
           targets=[cap])
    # dock pocket for the dock board, opening into the spigot cavity
    floor = "cap_floor - bot_y"
    bk.box(comp, "Dokk zseb", "body_end + 0.5 mm", "pen_len - cap_rear", floor, "-2 mm",
           neg("shell_dock_z"), "shell_dock_z", op="cut", targets=[cap])
    pad_r = "(dock_pad_d + 0.1 mm) / 2"
    n = bk.count("dock_pins")
    for k in range(n):
        bk.revolve(comp, f"Érintkező furat {k + 1}",
                   _vertical_cyl("dock_xc", pad_r, neg("bot_y + 0.5 mm"), f"{floor} + 0.5 mm"),
                   axis=3, plane_z=f"({k} - (dock_pins - 1) / 2) * dock_pitch", op="cut",
                   targets=[cap])
    mag_r = "(mag_d + 0.1 mm) / 2"
    for name, xc in (("Mágnesfészek elöl", "dock_xc - mag_dx"),
                     ("Mágnesfészek hátul", "dock_xc + mag_dx")):
        bk.revolve(comp, name, _vertical_cyl(xc, mag_r, "mag_skin - bot_y", f"{floor} + 0.5 mm"),
                   axis=3, op="cut", targets=[cap])
    if cutaway:
        bk.cut_half(comp, "Metszet", [cap])
    return comp


def _glass(bk, parent, cutaway):
    comp = bk.component(parent, "Fedőüveg")
    gz = "glass_w / 2"
    g = bk.box(comp, "Fedőüveg", "glass_x0", "glass_x1", "top_y - glass_t", "top_y", neg(gz),
               gz, look="glass_black", material="glass").body
    bk.fillet(comp, "Üveg sarkai", g,
              [("line_y", x, z) for x in ("glass_x0", "glass_x1") for z in (gz, neg(gz))],
              "glass_r")
    bk.chamfer(comp, "Üveg éle", g, [("plane_y", "top_y")], "glass_ch")
    if cutaway:
        bk.cut_half(comp, "Metszet", [g])
    return comp


def build_shell(bk, parent, cutaway):
    return [_housing(bk, parent, cutaway), _cap(bk, parent, cutaway),
            _glass(bk, parent, cutaway)]


def build_shared(bk, parent):
    comp = bk.component(parent, "Gomb")
    top = "top_y + btn_proud"
    cap_bot = "top_y + btn_proud - shell_btn_t"
    r = "btn_d / 2"
    bk.revolve(comp, "Gomb", [
        ("btn_x", "sled_top_i - 0.4 mm"),
        ("btn_x + shell_btn_stem", "sled_top_i - 0.4 mm"),
        ("btn_x + shell_btn_stem", cap_bot),
        (f"btn_x + {r}", cap_bot),
        (f"btn_x + {r}", f"{top} - shell_btn_ch"),
        (f"btn_x + {r} - shell_btn_ch", top),
        ("btn_x", top),
    ], axis=6, look="alu", material="aluminum")
    return [comp]
