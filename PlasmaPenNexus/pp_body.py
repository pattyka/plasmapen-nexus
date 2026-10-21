"""PlasmaPen Nexus — anodised aluminium unibody, PEEK end cap, display glass, button.

    build_shell(bk, parent, cutaway)  "Unibody (alu)", "Hátsó kupak (PEEK)"   (cut in half if cutaway)
    build_shared(bk, parent)          "Fedőüveg", "Gomb"
    inner_profile_pts()               the unibody's inner surface, nose_len → head_len, for the
                                      PEEK nose + liner (agent A) to follow exactly

Frame of pp_params: X = pen axis, Y = up (facet), Z = side. All parts are open at the back only.

Spindle (Pininfarina Cambiano), tangent-continuous end to end:
  ogive  x nose_len … taper_x1:  r = body_r0 + (body_r - body_r0)·(1 - (1 - t)^body_ogive_p),
         steeper at the front, flat at taper_x1
  swell  x taper_x1 … swell_x1:  r = body_r (display + button live here)
  fall   x swell_x1 … body_end:  r = body_r - (body_r - body_r_be)·(3u² - 2u³), a smoothstep that
         is flat at both ends, so the PEEK cap continues it as a short cylinder r = body_r_be.
         Flat at body_end on purpose: the cap's facet edge is then a straight line, so the facet
         blend can be selected there and runs unbroken across the joint.
The facet at flat_y becomes lens-shaped by itself: pointed fade on the ogive, full width on the
swell, narrowing on the fall. Inside, a parabola runs from the front opening
(nose_len, tip_r + body_nose_gap) to (body_xi, bore_r) with its vertex at body_xi, so the inner
surface also flows tangentially into the bore. body_xi is where the outer taper is front_wall
above the bore, clamped so it stays inside the taper for any sane body_od / tip_od / bore_r.
All curves are fitted splines through exact points of the parabolas.

Edges follow Apple's rule: 0.05 mm edge breaks or large form radii, nothing in between.
"""

from pp_core import neg

EXTRA_PARAMS = [
    # ── front / taper ──
    ("body_nose_gap", "0.05 mm", "mm", "Orr (PEEK) ↔ alu nyílás hézag sugárban"),
    ("body_r0", "tip_r + body_nose_gap + front_wall", "mm", "= alu test elülső élének külső sugara"),
    ("body_edge_brk", "0.05 mm", "mm", "Élletörés (elülső él, test ↔ kupak illesztés)"),
    ("body_ogive_p", "2.5", "", "Elülső ív kitevője (nagyobb = meredekebb elöl)"),
    ("body_r_be", "back_od / 2", "mm", "= sugár a test hátsó végén és a kupakon"),
    ("body_fall_l", "body_end - swell_x1", "mm", "= hátsó elvékonyodás hossza"),
    ("body_cap_fw", "2 * sqrt(body_r_be ^ 2 - flat_y ^ 2)", "mm", "= lapos oldal szélessége a kupakon"),
    ("body_q", "(bore_r - tip_r - body_nose_gap) / (abs(body_r - body_r0) + 0.01 mm)", "",
     "= belső átmenet aránya a kúpban"),
    ("body_qm", "(body_q + 0.9 - abs(body_q - 0.9)) / 2", "", "= min(body_q, 0.9)"),
    ("body_qc", "(body_qm + 0.02 + abs(body_qm - 0.02)) / 2", "", "= body_q 0,02 … 0,9 közé szorítva"),
    ("body_ti", "1 - sqrt(1 - body_qc)", "", "= kúp paraméter a belső átmenet végén"),
    ("body_xi", "nose_len + body_ti * (taper_x1 - nose_len)", "mm",
     "= itt simul a belső felület a furatba"),
    # ── facet / joints ──
    ("body_facet_r", "2 mm", "mm", "Lapos oldal ↔ henger lágy átmenete"),
    # ── display ──
    ("body_glass_c", "0.12 mm", "mm", "Fedőüveg ↔ zseb hézag"),
    ("body_win_r", "1.25 mm", "mm", "Üvegzseb sarok sugár (a panelzseb sarka belül marad)"),
    ("body_pnl_c", "0.1 mm", "mm", "AMOLED ↔ panelzseb hézag"),
    ("body_pnl_r", "0.3 mm", "mm", "Panelzseb sarok sugár (szögletes panel sarka befér)"),
    ("body_fpc_w", "12.68 mm", "mm", "AMOLED FPC szélesség (a panel elején lép ki)"),
    ("body_fpc_bend", "0.7 mm", "mm", "Hely az FPC hajlításának a panel előtt"),
    ("body_fpc_len", "3 mm", "mm", "FPC átvezető nyílás hossza a furatba"),
    # ── vents (bottom grille under the fan) ──
    ("body_vent_r", "vent_w / 2", "mm", "= szellőző rés végének sugara"),
    ("body_vent_pitch", "vent_w + 1.2 mm", "mm", "Szellőző rések osztása (oldalirányban)"),
    # ── coax to the BLE antenna in the end cap ──
    ("body_coax_w", "1.0 mm", "mm", "Koax horony szélesség (Ø0,81 koax)"),
    ("body_coax_d", "1.0 mm", "mm", "Koax horony mélység a furatban"),
    ("body_coax_x0", "pcb_x0 + pcb_len", "mm", "Koax horony eleje"),
    # ── end cap (black PEEK = BLE antenna window) ──
    ("body_cap_spigot_in", "bms_d / 2 + 0.4 mm", "mm", "Kupak csap belső sugara (BMS NYÁK körül)"),
    ("body_usb_c", "0.15 mm", "mm", "USB-C aljzat ↔ nyílás hézag"),
    ("body_usb_r", "usb_h / 2 + body_usb_c - 0.02 mm", "mm", "USB-C nyílás végsugár (stadion)"),
    ("body_ant_ri", "6 mm", "mm", "Antennazseb belső sugara (USB-C körüli csonk)"),
    ("body_ant_d", "cap_len - 3 mm", "mm", "Antennazseb mélysége a kupakban"),
    ("body_cap_relief", "1 mm", "mm", "Kupak belső homloka hátrébb: hely a BMS hátoldali IC-inek"),
    # ── button ──
    ("body_btn_c", "0.15 mm", "mm", "Gomb ↔ furat radiális hézag"),
    ("body_sw_top", "pcb_y + pcb_t + 2.5 mm", "mm", "Tapintókapcsoló teteje (tengelytől)"),
    ("body_btn_gap", "0.2 mm", "mm", "Gombszár ↔ kapcsoló hézag"),
    ("body_btn_stem_r", "1.5 mm", "mm", "Gombszár sugara"),
    ("body_btn_tip_ch", "0.3 mm", "mm", "Gombszár vég letörés"),
    ("body_btn_root", "0.4 mm", "mm", "Gombszár ↔ perem 45°-os átmenet"),
    ("body_btn_flange", "1 mm", "mm", "Gomb tartóperem túlnyúlása"),
    ("body_btn_flange_t", "0.8 mm", "mm", "Gomb tartóperem vastagság"),
    ("body_btn_flange_top", "sqrt(bore_r ^ 2 - (btn_d / 2 + body_btn_flange) ^ 2) - 0.2 mm", "mm",
     "= tartóperem teteje, 0,2 mm a furatfal alatt"),
    ("body_btn_er", "0.3 mm", "mm", "Gomb felső élének lágy lekerekítése"),
]

TOP = "body_r + 1 mm"
VENT_ROWS = (-2, -1, 0, 1, 2)   # bottom grille: slots at z = k · body_vent_pitch


def _ogive_pt(t):
    return (f"nose_len + {t} * (taper_x1 - nose_len)",
            f"body_r0 + (body_r - body_r0) * (1 - (1 - {t}) ^ body_ogive_p)")


def _fall_pt(u):
    return (f"swell_x1 + {u} * body_fall_l",
            f"body_r - (body_r - body_r_be) * (3 * {u} ^ 2 - 2 * {u} ^ 3)")


R_IN0 = "(tip_r + body_nose_gap)"
INNER_S = ("0.25", "0.5", "0.75")
OGIVE_T = ("0.9", "0.78", "0.65", "0.52", "0.4", "0.29", "0.2", "0.12", "0.06", "0.025")
FALL_U = ("0.92", "0.82", "0.7", "0.58", "0.46", "0.34", "0.22", "0.1")


def _inner_taper():
    """Front inner edge vertex + spline to (body_xi, bore_r)."""
    pts = [(f"nose_len + {s} * (body_xi - nose_len)",
            f"{R_IN0} + (bore_r - {R_IN0}) * (1 - (1 - {s}) ^ 2)") for s in INNER_S]
    pts.append(("body_xi", "bore_r"))
    return [("nose_len", R_IN0), ("spline", pts)]


def inner_profile_pts():
    """Unibody inner surface from the front opening (nose_len, tip_r + body_nose_gap) to
    (head_len, bore_r), in pp_core profile format: [vertex, ("spline", [...]), vertex].
    The outer surface of "Orr + bélés (PEEK)" must follow exactly this (same expressions)."""
    return _inner_taper() + [("head_len", "bore_r")]


def _wall_floor(half_w):
    """y just below the inner bore surface at |z| = half_w: a cut from here up to TOP opens
    the top wall completely and never reaches the bottom wall."""
    return f"sqrt(bore_r ^ 2 - ({half_w}) ^ 2) - 0.5 mm"


def _facet_cut(bk, comp, name, x0, x1, target):
    bk.box_sym(comp, name, x0, x1, "flat_y", TOP, "body_od + 2 mm", op="cut", targets=[target])


def _facet_edges(width):
    hw = f"{width} / 2"
    return [("line_x", "flat_y", hw), ("line_x", "flat_y", neg(hw))]


# ─────────────────────────────────────────────────────────────────────────────
# Shell
# ─────────────────────────────────────────────────────────────────────────────

def _unibody(bk, parent):
    comp = bk.component(parent, "Unibody (alu)")
    fall = [_fall_pt(u) for u in FALL_U] + [("swell_x1", "body_r")]
    ogive = [_ogive_pt(t) for t in OGIVE_T] + [("nose_len", "body_r0")]
    pts = _inner_taper() + [
        ("body_end", "bore_r"),
        ("body_end", "body_r_be"),
        ("spline", fall),
        ("taper_x1", "body_r"),
        ("spline", ogive),
    ]  # closing segment = front face
    uni = bk.revolve(comp, "Unibody", pts, look="alu", material="aluminum").body
    _vents(bk, comp, uni)  # first, on the clean revolve: the most robust order for the booleans

    # Facet over the full length: it fades out on the taper where r < flat_y, or runs out
    # through the front edge when body_r0 > flat_y. Its edge blend goes before the edge
    # breaks: the other order leaves corners the blend cannot close.
    _facet_cut(bk, comp, "Lapos oldal", "nose_len - 1 mm", "body_end + 1 mm", uni)
    bk.fillet(comp, "Lapos oldal élei", uni, _facet_edges("facet_w"), "body_facet_r")
    bk.fillet(comp, "Elülső él", uni, [("circle", "nose_len", "body_r0")], "body_edge_brk")
    bk.fillet(comp, "Illesztési él", uni, [("circle", "body_end", "body_r_be")], "body_edge_brk")

    # Display: glass pocket (glass_t deep), then the AMOLED pocket under it down to oled_y.
    # The AMOLED pocket floor lies below the bore top, so it is open to the bore along the
    # middle and the panel rests on two side ledges; at the front a full-width opening
    # takes the FPC down to the main board.
    gw = "oled_win_w / 2"
    bk.box_sym(comp, "Üvegzseb", "win_x0", "win_x1", "flat_y - glass_t", TOP, "oled_win_w",
               op="cut", targets=[uni])
    bk.fillet(comp, "Üvegzseb sarkai", uni,
              [("line_y", x, z) for x in ("win_x0", "win_x1") for z in (gw, neg(gw))],
              "body_win_r")
    px0 = "oled_x0 - body_fpc_bend"
    px1 = "oled_x0 + oled_len + body_pnl_c"
    pw = "oled_w / 2 + body_pnl_c"
    bk.box_sym(comp, "Panelzseb", px0, px1, "oled_y", "flat_y - glass_t",
               "oled_w + 2 * body_pnl_c", op="cut", targets=[uni])
    bk.fillet(comp, "Panelzseb sarkai", uni,
              [("line_y", x, z) for x in (px0, px1) for z in (pw, neg(pw))], "body_pnl_r")
    # FPC: leaves the panel's front edge, bends down into the bore through this opening.
    fw = "body_fpc_w / 2 + 0.15 mm"
    bk.box_sym(comp, "FPC nyílás", px0, "oled_x0 + body_fpc_len",
               _wall_floor(fw), "oled_y + 0.3 mm", "body_fpc_w + 0.3 mm",
               op="cut", targets=[uni])

    # Button hole through the facet.
    hr = "btn_d / 2 + body_btn_c"
    y0 = _wall_floor(hr)
    bk.revolve(comp, "Gomb furat",
               [("btn_x", y0), (f"btn_x + {hr}", y0), (f"btn_x + {hr}", TOP), ("btn_x", TOP)],
               axis=3, op="cut", targets=[uni])

    # Coax groove along the bottom of the bore, past the cell, out through the back end.
    bk.box_sym(comp, "Koax horony", "body_coax_x0", "body_end + 1 mm",
               neg("bore_r + body_coax_d"), neg("bore_r - 0.5 mm"), "body_coax_w",
               op="cut", targets=[uni])
    return comp, uni


def _vents(bk, comp, uni):
    """Bottom grille under the fan: parallel stadium slots cut straight up through the bottom
    wall at z = k · body_vent_pitch, far from the facet."""
    xa = "vent_x0 + body_vent_r"
    xb = "vent_x0 + vent_len - body_vent_r"
    for k in VENT_ROWS:
        zc = "0 mm" if k == 0 else (f"{abs(k)} * body_vent_pitch" if k > 0
                                     else neg(f"{abs(k)} * body_vent_pitch"))
        reach = f"{abs(k)} * body_vent_pitch + body_vent_r"
        y_top = neg(_wall_floor(reach))
        y_bot = neg(TOP)
        tag = f"Szellőző {VENT_ROWS.index(k) + 1}"
        bk.extrude(comp, tag, [(xa, y_bot), (xb, y_bot), (xb, y_top), (xa, y_top)],
                   f"{zc} - body_vent_r", f"{zc} + body_vent_r", op="cut", targets=[uni])
        for end, cx in (("eleje", xa), ("vége", xb)):
            pts = [(cx, y_bot), (f"{cx} + body_vent_r", y_bot),
                   (f"{cx} + body_vent_r", y_top), (cx, y_top)]
            bk.revolve(comp, f"{tag} {end}", pts, axis=3, plane_z=zc, op="cut", targets=[uni])


def _end_cap(bk, parent):
    """Black PEEK end cap: the BLE antenna window, mirroring the black nose. The facet runs
    out through it; the back corner is the large form radius back_r."""
    comp = bk.component(parent, "Hátsó kupak (PEEK)")
    spigot_x0 = "body_end - cap_spigot"
    pts = [
        (spigot_x0, "body_cap_spigot_in"),
        (spigot_x0, "bore_r"),
        ("body_end", "bore_r"),
        ("body_end", "body_r_be"),
        ("pen_len", "body_r_be"),
        ("pen_len", "0 mm"),
        ("body_end + body_cap_relief", "0 mm"),
        ("body_end + body_cap_relief", "body_ant_ri"),
        ("body_end + body_ant_d", "body_ant_ri"),
        ("body_end + body_ant_d", "body_cap_spigot_in"),
    ]  # ring pocket r body_ant_ri … spigot bore behind the alu: room for the flex antenna
    cap = bk.revolve(comp, "Hátsó kupak", pts, look="peek", material="peek").body
    _facet_cut(bk, comp, "Lapos oldal", "body_end - 1 mm", "pen_len + 1 mm", cap)
    bk.fillet(comp, "Lapos oldal élei", cap, _facet_edges("body_cap_fw"), "body_facet_r")
    bk.fillet(comp, "Hátsó él", cap, [("circle", "pen_len", "body_r_be")], "back_r")
    bk.fillet(comp, "Illesztési él", cap, [("circle", "body_end", "body_r_be")], "body_edge_brk")

    # Coax notch through the spigot, in line with the unibody groove, into the antenna space.
    bk.box_sym(comp, "Koax bevezető", f"{spigot_x0} - 1 mm", "body_end",
               neg("bore_r + 0.5 mm"), neg("body_cap_spigot_in - 0.5 mm"), "body_coax_w",
               op="cut", targets=[cap])

    # USB-C opening: rectangle through the cap, long edges rounded into a stadium.
    hy = "usb_h / 2 + body_usb_c"
    hz = "usb_w / 2 + body_usb_c"
    bk.box_sym(comp, "USB-C nyílás", "body_end - 1 mm", "pen_len + 1 mm", neg(hy), hy,
               "usb_w + 2 * body_usb_c", op="cut", targets=[cap])
    bk.fillet(comp, "USB-C nyílás ívek", cap,
              [("line_x", y, z) for y in (hy, neg(hy)) for z in (hz, neg(hz))], "body_usb_r")
    return comp, cap


def build_shell(bk, parent, cutaway):
    uni_c, uni = _unibody(bk, parent)
    cap_c, cap = _end_cap(bk, parent)
    if cutaway:
        bk.cut_half(uni_c, "Metszet", [uni])
        bk.cut_half(cap_c, "Metszet", [cap])
    return [uni_c, cap_c]


# ─────────────────────────────────────────────────────────────────────────────
# Shared parts
# ─────────────────────────────────────────────────────────────────────────────

def _glass(bk, parent):
    comp = bk.component(parent, "Fedőüveg")
    x0 = "win_x0 + body_glass_c"
    x1 = "win_x1 - body_glass_c"
    hw = "oled_win_w / 2 - body_glass_c"
    glass = bk.box_sym(comp, "Fedőüveg", x0, x1, "flat_y - glass_t", "flat_y",
                       "oled_win_w - 2 * body_glass_c",
                       look="glass_black", material="glass").body
    bk.fillet(comp, "Fedőüveg sarkai", glass,
              [("line_y", x, z) for x in (x0, x1) for z in (hw, neg(hw))],
              "body_win_r - body_glass_c")
    return comp


def _button(bk, parent):
    """Revolved about the vertical line x = btn_x (the profile's closing segment).
    Machined plunger: chamfered stem tip 0.2 mm above the tact switch, 45° root into a
    retaining flange under the wall, body through the hole, flat top btn_proud above the
    facet, its edge a soft quarter round (body_btn_er)."""
    comp = bk.component(parent, "Gomb")
    stem_bot = "body_sw_top + body_btn_gap"
    fl_top = "body_btn_flange_top"
    fl_bot = "body_btn_flange_top - body_btn_flange_t"
    fl_r = "btn_x + btn_d / 2 + body_btn_flange"
    rim = "btn_x + btn_d / 2"
    top = "flat_y + btn_proud"
    pts = [
        ("btn_x", stem_bot),
        ("btn_x + body_btn_stem_r - body_btn_tip_ch", stem_bot),
        ("btn_x + body_btn_stem_r", f"{stem_bot} + body_btn_tip_ch"),
        ("btn_x + body_btn_stem_r", f"{fl_bot} - body_btn_root"),
        ("btn_x + body_btn_stem_r + body_btn_root", fl_bot),
        (fl_r, fl_bot),
        (fl_r, fl_top),
        (rim, fl_top),
        (rim, f"{top} - body_btn_er"),
        ("spline", [(f"{rim} - body_btn_er * (1 - {c})", f"{top} - body_btn_er * (1 - {s_})")
                    for c, s_ in (("0.866", "0.5"), ("0.5", "0.866"))]
         + [(f"{rim} - body_btn_er", top)]),
        ("btn_x", top),
    ]
    bk.revolve(comp, "Gomb", pts, axis=len(pts) - 1, look="alu", material="aluminum")
    return comp


def build_shared(bk, parent):
    return [_glass(bk, parent), _button(bk, parent)]
