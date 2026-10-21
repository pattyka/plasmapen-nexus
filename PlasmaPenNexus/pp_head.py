"""PlasmaPen Nexus — Package H, front of the cartridge: PEEK nose cone, HV liner, optics, piezo.

    build_shell(bk, parent, cutaway)  "Orrkúp (PEEK)", "HV bélés (PEEK)"   (cut in half if cutaway)
    build_shared(bk, parent)          "Üveggyűrű", "LED 405 nm", "LED 660 nm", "Kamera (OV5640)",
                                      "CeraPlas HF"

Frame of pp_params: X = pen axis (x = 0 nozzle face, +X back), Y = up (display flat, camera at
θ = 0), Z = side. Every part here is non-conductive or sits ≥ hv_clear from the piezo's output
end (TDK: nothing conductive within 20 mm of it).

Nose cone, one revolve (y ≥ 0): nozzle bore, the slim beak (straight cone tip_r0 → face_r0; where a
thicker liner (CeraPlas F) would leave less than head_beak_min of wall at the liner's front, the
beak line bends out at liner_x0 to head_beak_r1 instead of thinning — the tip and the camera's
view past it stay as they are, head_chk_beak_view; a 45° break at the front edge and at the
nozzle mouth, both in the profile), the 61° glass
chamfer face with its recess, the collar with joint_ch at the shadow gap, and the spigot that
enters the housing bore. Then: the spigot is cut to the bore's double-D, three air grooves run
through it (θ = ±90° and 180°, never near the A tunnel at θ = 0), the optics chamber behind the
glass is cut as a second revolve, and a slot carries the camera/LED flex from the chamber to the
insert's A tunnel.

Optics chamber: behind the glass's back face, with a head_win_land ledge at both glass edges so
the ring is bonded on PEEK all round. Its floor is cam_peek of PEEK over the liner socket; its
outer wall head_collar_wall under the collar; its rear wall head_cav_wall before the joint.

Camera: the OV5640 module is a lens barrel (head_cam_lb long, Ø 2·head_cam_rb) on a square body
(cam_mod × cam_mod, cam_depth − head_cam_lb deep, the last head_cam_pcb of it the sensor board),
tilted cam_tilt toward the axis about Z. Its lowest corner rests head_fit above the chamber
floor; along X it sits as far forward as the glass allows — both the barrel's top edge and the
body's top front corners keep head_fit behind the glass / ledge — but never nearer than
hv_clear + head_hv_margin to the piezo's output end (head_cam_xq). head_chk_cam_back
and head_chk_cam_top say it still fits the chamber.

LEDs: lens cylinders along X on led_ring_r, their front face head_fit behind the glass at their
OUTER edge (the glass is conical, so the centre-based led_x of pp_params would put the outer half
of each lens into the glass). Seeds at θ = +180°/(2·led_pairs) (405 nm) and θ = −180°/(2·led_pairs)
(660 nm), patterned: same positions as alternating 405 / 660, and no seed centre ever lands on the
sketch X axis.
"""

from pp_core import neg


def _p(e):
    return f"({e})"


def _max(a, b):
    """max(a, b) in plain Fusion arithmetic (the preview evaluator has no max())."""
    return f"({_p(a)} + {_p(b)} + abs({_p(a)} - {_p(b)})) / 2"


def _min(a, b):
    return f"({_p(a)} + {_p(b)} - abs({_p(a)} - {_p(b)})) / 2"


def x_face(r):
    """x of the chamfer face (front surface) at radius r."""
    return f"face_x0 + ({_p(r)} - face_r0) / face_k"


def x_glass(r):
    """x of the glass ring's back face at radius r."""
    return f"{x_face(r)} + win_tx"


def beak_r(x):
    return f"tip_r0 + (face_r0 - tip_r0) * {_p(x)} / face_x0"


def _ledge(r):
    return (f"head_ledge_x0 + ({_p(r)} - head_ws1) * (head_ledge_x1 - head_ledge_x0)"
            f" / (head_cav_ro - head_ws1)")


def chamber_front(r):
    """x of the optics chamber's front boundary at radius r (glass back face, then the outer
    ledge line)."""
    return _max(x_glass(r), _ledge(r))


def cam_pt(s, w):
    """Point of the camera at distance s behind the body's front-bottom edge along the optical
    axis and w above it (perpendicular), in the XY plane."""
    return (f"head_cam_xq + {_p(s)} * head_ct - {_p(w)} * head_st",
            f"head_cam_yq + {_p(s)} * head_st + {_p(w)} * head_ct")


EXTRA_PARAMS = [
    ("head_fit", "0.05 mm", "mm", "Illesztési hézag a fej alkatrészei között"),
    ("head_tip_ch", "0.3 mm", "mm", "Csőr homlokélének letörése (45°)"),
    ("head_noz_ch", "0.25 mm", "mm", "Fúvóka szájának letörése (45°)"),
    ("head_sock_r", "liner_ro + 0.05 mm", "mm", "= bélés fészek sugara az orrkúpban"),
    ("head_beak_min", "0.5 mm", "mm", "Min. PEEK fal a csőrben a bélés eleje fölött"),
    ("head_beak_r1", _max(beak_r("liner_x0"), "head_sock_r + head_beak_min"), "mm",
     "= csőr sugara a bélés elejénél: a csőr vonala, vagy kifelé tér, ha a bélés vastagabb"),
    ("head_chk_beak_view",
     "plume_r + (cam_y - plume_r) * (liner_x0 + standoff)"
     " / (face_x0 + (cam_y - face_r0) / face_k + standoff) - head_beak_r1", "mm",
     "ELLENŐRZÉS: a kamera rálátása a láng szélére a csőr töréspontja fölött is megvan"),
    ("head_spig_r", "bore_r - 0.1 mm", "mm", "= orrkúp csap sugara"),
    ("head_spig_x1", "body_x0 + nose_spigot", "mm", "= orrkúp csap vége"),
    # ── optics chamber ──
    ("head_win_land", "0.4 mm", "mm", "PEEK perem az üveggyűrű két szélén (ragasztás)"),
    ("head_sh_land", "0.6 mm", "mm", "PEEK sáv az üveggyűrű külső széle és a váll íve között"),
    ("head_sh_len", "4 mm", "mm", "Váll íve: ennyi mm-en simul a gallérba (X)"),
    ("head_ws0", "win_r0 + head_win_land", "mm", "= kamra eleje belül (üveg mögött)"),
    ("head_ws1", "win_r1 - head_win_land", "mm", "= kamra eleje kívül (üveg mögött)"),
    ("head_collar_wall", "0.9 mm", "mm", "PEEK fal a gallérban a kamra fölött"),
    ("head_cav_ro", "nose_r1 - head_collar_wall", "mm", "= optikai kamra külső sugara"),
    ("head_cav_ri", "head_sock_r + cam_peek", "mm", "= optikai kamra padlója (cam_peek PEEK)"),
    ("head_cav_wall", "0.5 mm", "mm", "Kamra hátfala az illesztés előtt"),
    ("head_cav_x1", "nose_split - head_cav_wall", "mm", "= optikai kamra hátfala"),
    ("head_ledge_x0", x_glass("head_ws1"), "mm", "= külső perem kezdete"),
    ("head_ledge_x1", x_glass("win_r1") + " + head_win_land", "mm", "= külső perem vége"),
    # ── camera ──
    ("head_ct", "cos(cam_tilt)", "", "= kamera dőlés koszinusza"),
    ("head_st", "sin(cam_tilt)", "", "= kamera dőlés szinusza"),
    ("head_cam_lb", "2 mm", "mm", "Objektív kiállása a modul elé"),
    ("head_cam_rb", "cam_ap / 2 + 0.5 mm", "mm", "= objektív külső sugara"),
    ("head_cam_lm", "cam_depth - head_cam_lb", "mm", "= modul test hossza (tengely mentén)"),
    ("head_cam_pcb", "1 mm", "mm", "Szenzor NYÁK a modul hátulján"),
    ("head_cam_h", "cam_mod / 2", "mm", "= modul fél oldalhossza"),
    ("head_cam_yq", "head_cav_ri + head_fit", "mm", "= modul legalsó éle (elöl lent)"),
    ("head_cam_r1",
     "head_cam_yq + head_cam_h * head_ct - head_cam_lb * head_st + head_cam_rb * head_ct",
     "mm", "= objektív felső elülső éle (sugár)"),
    ("head_cam_r2", "sqrt((head_cam_yq + 2 * head_cam_h * head_ct) ^ 2 + head_cam_h ^ 2)", "mm",
     "= modul felső elülső sarka (sugár)"),
    ("head_hv_margin", "0.25 mm", "mm", "Ráhagyás a 20 mm-es HV távolságon"),
    ("head_cam_xq_glass",
     _max(chamber_front("head_cam_r1") + " + head_fit + head_cam_rb * head_st"
          " + head_cam_lb * head_ct + head_cam_h * head_st",
          chamber_front("head_cam_r2") + " + head_fit + 2 * head_cam_h * head_st"),
     "mm", "= legelső modulhelyzet: objektív és sarkok az üveg mögött"),
    ("head_cam_xq_hv",
     _max("cp_x0 + sqrt((hv_clear + head_hv_margin) ^ 2 - (head_cam_yq + head_cam_h * head_ct"
          " - head_cam_lb * head_st - head_cam_rb * head_ct) ^ 2) - head_cam_rb * head_st"
          " + head_cam_h * head_st + head_cam_lb * head_ct",
          "cp_x0 + sqrt((hv_clear + head_hv_margin) ^ 2 - head_cam_yq ^ 2)"),
     "mm", "= legelső modulhelyzet a piezo kimenetétől hv_clear-en túl"),
    ("head_cam_xq", _max("head_cam_xq_glass", "head_cam_xq_hv"), "mm",
     "= modul elülső alsó éle (x)"),
    ("head_cam_xb", "head_cam_xq + head_cam_lm * head_ct", "mm", "= modul hátsó alsó éle (x)"),
    ("head_cam_r3",
     "sqrt((head_cam_yq + head_cam_lm * head_st + 2 * head_cam_h * head_ct) ^ 2"
     " + head_cam_h ^ 2)", "mm", "= modul felső hátsó sarka (sugár)"),
    ("head_chk_cam_back", "head_cav_x1 - head_fit - head_cam_xb", "mm",
     "ELLENŐRZÉS: kamera modul a kamra hátfala előtt"),
    ("head_chk_cam_top", "head_cav_ro - head_fit - head_cam_r3", "mm",
     "ELLENŐRZÉS: kamera modul sarka a kamra külső fala alatt"),
    ("head_cam_xa", "head_cam_xq - head_cam_h * head_st - head_cam_lb * head_ct", "mm",
     "= objektív homloka (tengelyen, x)"),
    ("head_cam_ya", "head_cam_yq + head_cam_h * head_ct - head_cam_lb * head_st", "mm",
     "= objektív homloka (tengelyen, y)"),
    ("head_chk_hv_cam",
     _min("sqrt((head_cam_xa + head_cam_rb * head_st - cp_x0) ^ 2"
          " + (head_cam_ya - head_cam_rb * head_ct) ^ 2)",
          "sqrt((head_cam_xq - cp_x0) ^ 2 + head_cam_yq ^ 2)") + " - hv_clear",
     "mm", "ELLENŐRZÉS: kamera legközelebbi pontja ↔ piezo kimenet ≥ hv_clear"),
    ("head_chk_hv_plastic", "liner_wall + cam_peek - 2.5 mm", "mm",
     "ELLENŐRZÉS: ≥ 2,5 mm tömör PEEK a piezo és a kamera között"),
    # ── LEDs ──
    ("head_led_x", x_glass("led_ring_r + led_d / 2") + " + head_fit", "mm",
     "= LED homloka (a külső szélénél is az üveg mögött)"),
    ("head_chk_led_win",
     _min("head_ws1 - led_ring_r - led_d / 2", "led_ring_r - led_d / 2 - head_ws0"), "mm",
     "ELLENŐRZÉS: LED-ek az üveggyűrű szabad része mögött"),
    ("head_chk_led_cam",
     "led_ring_r * sin(180 deg / (2 * led_pairs)) - led_d / 2 - cam_mod / 2 - head_fit", "mm",
     "ELLENŐRZÉS: a kamera melletti LED nem ér a modulhoz (Z)"),
    # ── air intake: shadow gap → spigot grooves → B0 ──
    ("head_air_w", "4.5 mm", "mm", "Légcsatorna szélesség a csapon (3 db: ±90°, 180°)"),
    ("head_air_d", "1.7 mm", "mm", "Légcsatorna mélység"),
    ("head_chk_air",
     "(2 * head_air_w * (sqrt(head_spig_r ^ 2 - (head_air_w / 2) ^ 2) - head_spig_r"
     " + head_air_d) + head_air_w * head_air_d) / (1 mm) - 20 mm", "mm",
     "ELLENŐRZÉS: légút keresztmetszete ≥ 20 mm² (érték mm²-ben)"),
    # ── piezo mounting ──
    ("head_clip_len", "2.4 mm", "mm", "PEEK tüsketartó hossza"),
    ("head_cradle_len", "3 mm", "mm", "Szilikon bölcső hossza"),
    ("head_cp_rd", "sqrt((cp_w / 2) ^ 2 + (cp_h / 2) ^ 2)", "mm", "= piezo fél-átlója"),
    ("head_pin_y1", "pcb_y - pboard_t - 1 mm", "mm", "= tüskék alsó vége"),
]

NOZZLE_R = "nozzle_d / 2"
TOP_CUT = "body_r + 2 mm"

LED_SEEDS = (
    ("405", "led405", "180 deg / (2 * led_pairs)"),
    ("660", "led660", "-(180 deg / (2 * led_pairs))"),
)


# ─────────────────────────────────────────────────────────────────────────────
# Profiles (module level so tools can draw them)
# ─────────────────────────────────────────────────────────────────────────────

def shoulder_fit():
    """Glass face → collar as one curve: a quadratic Bezier (a parabola) tangent to the face
    line at r = win_r1 + head_sh_land and to the collar line head_sh_len behind face_x1, its
    control point the old corner (face_x1, nose_r1). Fit points from the collar end to the face
    (profile order)."""
    r0 = "win_r1 + head_sh_land"
    p0 = (x_face(r0), r0)
    p1 = ("face_x1", "nose_r1")
    p2 = ("face_x1 + head_sh_len",
          "nose_r1 + (body_r0 - nose_r1) * head_sh_len / (nose_split - joint_ch - face_x1)")
    pts = []
    for k in range(1, 9):
        t = 1 - k / 8
        a, b, c = (1 - t) ** 2, 2 * t * (1 - t), t * t
        if k == 8:
            pts.append(p0)
        else:
            pts.append((f"{a:.6f} * ({p0[0]}) + {b:.6f} * ({p1[0]}) + {c:.6f} * ({p2[0]})",
                        f"{a:.6f} * ({p0[1]}) + {b:.6f} * ({p1[1]}) + {c:.6f} * ({p2[1]})"))
    return p2, pts


def nose_profile():
    """Half-section of the nose cone, y ≥ 0. Segment order: front face → nozzle → socket →
    spigot → shadow-gap face → collar → glass face + recess → beak."""
    sh_end, sh_fit = shoulder_fit()
    return [
        ("0 mm", f"{NOZZLE_R} + head_noz_ch"),
        ("head_noz_ch", NOZZLE_R),                                  # nozzle mouth break
        ("nozzle_len", NOZZLE_R),                                   # nozzle bore
        ("nozzle_len", "head_sock_r"),                              # liner seat
        ("head_spig_x1", "head_sock_r"),                            # liner socket
        ("head_spig_x1", "head_spig_r"),                            # spigot back face
        ("nose_split", "head_spig_r"),                              # spigot
        ("nose_split", "body_r0 - joint_ch"),                       # shadow-gap face
        ("nose_split - joint_ch", "body_r0"),                       # joint chamfer
        sh_end,                                                     # collar
        ("spline", sh_fit),                                         # shoulder into the face
        (x_face("win_r1"), "win_r1"),                               # face, outer land
        (x_glass("win_r1"), "win_r1"),                              # recess outer wall
        (x_glass("win_r0"), "win_r0"),                              # recess floor
        (x_face("win_r0"), "win_r0"),                               # recess inner wall
        ("face_x0", "face_r0"),                                     # face, inner land
        ("liner_x0", "head_beak_r1"),                               # beak (follows the liner)
        ("head_tip_ch", beak_r("head_tip_ch")),                     # beak
        ("0 mm", "tip_r0 - head_tip_ch"),                           # front edge break
    ]


def chamber_profile():
    """Optics chamber (cut), revolved about X."""
    return [
        (x_glass("head_ws0"), "head_ws0"),
        ("head_ledge_x0", "head_ws1"),
        ("head_ledge_x1", "head_cav_ro"),
        ("head_cav_x1", "head_cav_ro"),
        ("head_cav_x1", "head_cav_ri"),
        (x_glass("head_ws0"), "head_cav_ri"),
    ]


def glass_profile():
    return [
        (x_face("win_r0"), "win_r0"),
        (x_face("win_r1"), "win_r1"),
        (x_glass("win_r1"), "win_r1"),
        (x_glass("win_r0"), "win_r0"),
    ]


def liner_profile():
    """HV liner half-section: 45° funnel from the nozzle bore, open at the back."""
    return [
        ("liner_x0", NOZZLE_R),
        (f"liner_x0 + liner_ri - {NOZZLE_R}", "liner_ri"),
        ("liner_x1", "liner_ri"),
        ("liner_x1", "liner_ro"),
        ("liner_x0", "liner_ro"),
    ]


def axial_rect(x0, x1, yc, r):
    """Rectangle x0…x1 × yc…yc+r; segment 0 lies on y = yc (revolve axis=0 → cylinder)."""
    top = f"{_p(yc)} + {_p(r)}"
    return [(x0, yc), (x1, yc), (x1, top), (x0, top)]


def vertical_rect(xc, r, y0, y1):
    """Rectangle xc…xc+r × y0…y1; segment 3 lies on x = xc (revolve axis=3 → cylinder along Y)."""
    return [(xc, y0), (f"{_p(xc)} + {_p(r)}", y0), (f"{_p(xc)} + {_p(r)}", y1), (xc, y1)]


def camera_body_pts(s0, s1):
    """Rotated rectangle of the camera body between axial distances s0 and s1."""
    w = "2 * head_cam_h"
    return [cam_pt(s0, "0 mm"), cam_pt(s1, "0 mm"), cam_pt(s1, w), cam_pt(s0, w)]


def camera_axis_pts(s, w):
    """Point on the camera's optical axis frame: s along the axis from the body front (negative
    = in front of the body), w off the axis."""
    return cam_pt(s, f"head_cam_h + {_p(w)}")


def barrel_profile():
    """Barrel: solid cylinder r head_cam_rb from its front to the body, with the aperture recess
    (r cam_ap/2, 0.5 mm deep) in front. Segment 0 lies on the optical axis."""
    lb = "-(head_cam_lb)"
    rec = "-(head_cam_lb) + 0.5 mm"
    return [
        camera_axis_pts(rec, "0 mm"),
        camera_axis_pts("0 mm", "0 mm"),
        camera_axis_pts("0 mm", "head_cam_rb"),
        camera_axis_pts(lb, "head_cam_rb"),
        camera_axis_pts(lb, "cam_ap / 2"),
        camera_axis_pts(rec, "cam_ap / 2"),
    ]


def filter_profile():
    return [
        camera_axis_pts("-(head_cam_lb) + 0.2 mm", "0 mm"),
        camera_axis_pts("-(head_cam_lb) + 0.5 mm", "0 mm"),
        camera_axis_pts("-(head_cam_lb) + 0.5 mm", "cam_ap / 2"),
        camera_axis_pts("-(head_cam_lb) + 0.2 mm", "cam_ap / 2"),
    ]


def led_centre(theta):
    return f"led_ring_r * cos({theta})", f"led_ring_r * sin({theta})"


# ─────────────────────────────────────────────────────────────────────────────
# Shells
# ─────────────────────────────────────────────────────────────────────────────

def _nose(bk, parent, cutaway):
    comp = bk.component(parent, "Orrkúp (PEEK)")
    nose = bk.revolve(comp, "Orrkúp", nose_profile(), look="peek", material="peek").body

    # Spigot → the bore's double-D (only behind the joint; the collar stays round).
    x0, x1 = "nose_split", "head_spig_x1 + 0.5 mm"
    bk.box_sym(comp, "Csap felső sík", x0, x1, "bore_top - 0.1 mm", TOP_CUT, "body_od + 4 mm",
               op="cut", targets=[nose])
    bk.box_sym(comp, "Csap alsó sík", x0, x1, neg(TOP_CUT), "-(bore_bot - 0.1 mm)",
               "body_od + 4 mm", op="cut", targets=[nose])

    # Air grooves: shadow gap → behind the spigot → the insert's B0 slots.
    hw = "head_air_w / 2"
    side = bk.box(comp, "Légcsatorna", x0, x1, neg(hw), hw, "head_spig_r - head_air_d",
                  TOP_CUT, op="cut", targets=[nose])
    bk.pattern_x(comp, "Légcsatornák oldalt", side, "2")
    bk.box_sym(comp, "Légcsatorna alul", x0, x1, neg(TOP_CUT),
               "-(bore_bot - 0.1 mm - head_air_d)", "head_air_w", op="cut", targets=[nose])

    # Optics chamber behind the glass + the flex slot to the A tunnel.
    bk.revolve(comp, "Optikai kamra", chamber_profile(), op="cut", targets=[nose])
    bk.box_sym(comp, "Flex csatorna", "head_cav_x1 - 0.2 mm", x1, "tun_floor + tun_floor_t",
               "sled_top_i", "tun_w", op="cut", targets=[nose])

    if cutaway:
        bk.cut_half(comp, "Metszet", [nose])
    return comp


def _liner(bk, parent, cutaway):
    comp = bk.component(parent, "HV bélés (PEEK)")
    liner = bk.revolve(comp, "HV bélés", liner_profile(), look="peek", material="peek").body
    r = "cp_pin_d / 2 + 0.15 mm"
    for k, z in (("1", "cp_pin_z"), ("2", neg("cp_pin_z"))):
        bk.revolve(comp, f"Tüske furat {k}",
                   vertical_rect("cp_pin_x", r, "-(liner_ro + 0.5 mm)", "-(cp_h / 2)"),
                   axis=3, plane_z=z, op="cut", targets=[liner])
    if cutaway:
        bk.cut_half(comp, "Metszet", [liner])
    return comp


def build_shell(bk, parent, cutaway):
    return [_nose(bk, parent, cutaway), _liner(bk, parent, cutaway)]


# ─────────────────────────────────────────────────────────────────────────────
# Shared parts
# ─────────────────────────────────────────────────────────────────────────────

def _camera(bk, parent):
    comp = bk.component(parent, "Kamera (OV5640)")
    bk.revolve(comp, "Objektív", barrel_profile(), axis=0, look="plastic_black",
               material="plastic")
    bk.revolve(comp, "Szűrő", filter_profile(), axis=0, look="lens", material="glass")
    body_end = "head_cam_lm - head_cam_pcb"
    h = "head_cam_h"
    bk.extrude(comp, "Modul", camera_body_pts("0 mm", body_end), neg(h), h,
               look="plastic_black", material="plastic")
    bk.extrude(comp, "Szenzor NYÁK", camera_body_pts(body_end, "head_cam_lm"), neg(h), h,
               look="pcb", material="fr4")
    return comp


def _piezo(bk, parent):
    comp = bk.component(parent, "CeraPlas HF")
    bk.box_sym(comp, "Piezo", "cp_x0", "cp_x1", "-(cp_h / 2)", "cp_h / 2", "cp_w",
               look="ceramic", material="steel")
    pin_r = "cp_pin_d / 2"
    for k, z in (("1", "cp_pin_z"), ("2", neg("cp_pin_z"))):
        bk.revolve(comp, f"Tüske {k}",
                   vertical_rect("cp_pin_x", pin_r, "head_pin_y1", "0 mm"),
                   axis=3, plane_z=z, look="gold", material="copper")
    # PEEK pin clip: a ring around the bar at the pins, the pins pass through it; it holds the
    # pins, never the bar (TDK Fig. 5).
    cx0 = "cp_pin_x - head_clip_len / 2"
    cx1 = "cp_pin_x + head_clip_len / 2"
    clip = bk.revolve(comp, "Tüsketartó",
                      [(cx0, "head_cp_rd + 0.15 mm"), (cx1, "head_cp_rd + 0.15 mm"),
                       (cx1, "liner_ri - head_fit"), (cx0, "liner_ri - head_fit")],
                      look="peek", material="peek").body
    for k, z in (("1", "cp_pin_z"), ("2", neg("cp_pin_z"))):
        bk.revolve(comp, f"Tüsketartó furat {k}",
                   vertical_rect("cp_pin_x", f"{pin_r} + 0.02 mm",
                                 "-(liner_ri + 0.1 mm)", "0.2 mm"),
                   axis=3, plane_z=z, op="cut", targets=[clip])
    # Soft silicone cradle at the front node, 0.05 mm clear of the bar corners.
    qx = "cp_x0 + cp_len / 4"
    bk.revolve(comp, "Bölcső",
               [(f"{qx} - head_cradle_len / 2", "head_cp_rd + head_fit"),
                (f"{qx} + head_cradle_len / 2", "head_cp_rd + head_fit"),
                (f"{qx} + head_cradle_len / 2", "liner_ri - head_fit"),
                (f"{qx} - head_cradle_len / 2", "liner_ri - head_fit")],
               look="rubber", material="plastic")
    return comp


def build_shared(bk, parent):
    win = bk.component(parent, "Üveggyűrű")
    bk.revolve(win, "Üveggyűrű", glass_profile(), look="glass_window", material="glass")
    comps = [win]
    for colour, look, theta in LED_SEEDS:
        comp = bk.component(parent, f"LED {colour} nm")
        yc, zc = led_centre(theta)
        seed = bk.revolve(comp, f"LED {colour} nm",
                          axial_rect("head_led_x", "head_led_x + led_h", yc, "led_d / 2"),
                          axis=0, plane_z=zc, look=look, material="plastic")
        bk.pattern_x(comp, f"LED {colour} nm", seed, "led_pairs", look=look)
        comps.append(comp)
    comps.append(_camera(bk, parent))
    comps.append(_piezo(bk, parent))
    return comps
