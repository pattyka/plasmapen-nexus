"""PlasmaPen Nexus — internal parts, shared by the render and the engineering assembly.

    build_shared(bk, parent) -> [CeraPlas F, Ventilátor, Fő NYÁK, OLED 1,1", BLE antenna,
                                 Driver NYÁK, Akku 21700, BMS + USB-C]

Frame of pp_params (X = pen axis, +X toward the back, Y = up, Z = side). The engineering
cutaway removes z > 0 from the shells only, so the internals that face the viewer sit at
z > 0: the CeraPlas lead pair runs at z = ±(cp_w / 2 + …), the fan blade is drawn at θ = 90°.

Outlines come from the datasheets:
  · TDK CeraPlas F: Rosen-type PZT transformer bar 72 × 6 × 2.8, HV output end at the front,
    multilayer input half with the side electrodes at the back, held only at its vibration
    nodes (¼ and ¾ length); leads soldered on the input electrodes.
  · ESP32-S3-MINI-1U (datasheet §10.1/10.2): 15.4 × 15.4 × 2.4, PCB 0.8, shield 14 × 13.55
    notched at one corner for the 3rd-gen (MHF III / W.FL) antenna receptacle 2.0 × 2.05.
  · Taoglas FXP75 "Atom" 2.4 GHz flex antenna 5.9 × 4.1 × 0.24 on Ø0.81 mm coax — the only
    standard 2.4 GHz flex that fits the end cap's 4 mm pocket (λ/4 parts are ≥ 35 × 7).
  · 1.1" AMOLED YX011T90332 (JD9613, 126 × 294): LTPS 0.5 + cap 0.3 + polarizer 0.15, glass
    30.94 × 12.96, polarizer 26.90 × 12.50 over the active area, 4.04 mm shelf with the driver
    at the front, 12.68 mm FPC into an FH26-13S-0.3SHW.
  · USB-C receptacle shell 8.94 × 3.26, tongue 6.69 × 0.7; 6 × 6 × 2.5 SMD tact switch;
    21700 cell with the + cap and insulating ring at the front.
"""

from pp_core import neg

EXTRA_PARAMS = [
    # ── CeraPlas F ──
    ("int_cp_x1", "cp_x0 + cp_len", "mm", "= piezo rúd vége (bemeneti oldal)"),
    ("int_cp_el_t", "0.05 mm", "mm", "Bemeneti elektróda vastagság"),
    ("int_cp_mount_t", "4 mm", "mm", "Csomóponti tartó vastagság (X)"),
    ("int_cp_mount_r", "liner_ri - 0.1 mm", "mm", "= tartó külső sugara (0,1 mm a bélés furatán belül)"),
    ("int_cp_hole_r", "1.1 mm", "mm", "Légátömlő furat sugara a tartóban"),
    ("int_cp_hole_c", "(int_cp_mount_r + sqrt((cp_w / 2) ^ 2 + (cp_h / 2) ^ 2)) / 2", "mm",
     "= légátömlő furatok köre"),
    ("int_cp_holes", "6", "", "Légátömlő furatok száma"),
    ("int_w_r", "0.25 mm", "mm", "Bekötő huzal sugara"),
    ("int_w_z", "cp_w / 2 + int_cp_el_t + int_w_r", "mm", "= huzalok oldaltávolsága"),
    ("int_w_x0", "cp_x0 + cp_len * 0.85", "mm", "Forrasztási pont a bemeneti elektródán"),
    ("int_w_r1", "liner_ri - int_w_r - 0.25 mm", "mm", "= huzal sugárpályája a bélés furatában"),
    ("int_w_y1", "sqrt(int_w_r1 ^ 2 - int_w_z ^ 2)", "mm", "= huzal mélysége a bélés furatában"),
    ("int_w_r2", "(fan_d / 2 + bore_r) / 2", "mm", "= huzal sugárpályája a ventilátor mellett"),
    ("int_w_y2", "sqrt(int_w_r2 ^ 2 - int_w_z ^ 2)", "mm", "= huzal mélysége a ventilátornál"),
    ("int_w_xj1", "(head_len + fan_x0) / 2", "mm", "Huzal kitérése a bélés vége és a ventilátor között"),
    ("int_w_xj2", "fan_x0 + fan_len + 1.2 mm", "mm", "Huzal visszatérése a ventilátor után"),
    ("int_w_y3", "drv_y + pcb_t + int_w_r", "mm", "= huzal a driver NYÁK alján"),
    # ── Ventilátor ──
    ("int_fan_wall", "0.7 mm", "mm", "Ventilátor keret falvastagság"),
    ("int_fan_ri", "fan_d / 2 - int_fan_wall", "mm", "= keret belső sugara"),
    ("int_fan_hub_r", "4.5 mm", "mm", "Rotor agy sugara"),
    ("int_fan_blades", "7", "", "Lapátok száma"),
    ("int_fan_blade_c", "2.3 mm", "mm", "Lapát fél-húrja érintő irányban"),
    ("int_fan_blade_t", "0.7 mm", "mm", "Lapát vastagsága tengelyirányban"),
    ("int_fan_tip_gap", "0.35 mm", "mm", "Lapátvég ↔ keret hézag"),
    ("int_fan_blade_r1", "sqrt((int_fan_ri - int_fan_tip_gap) ^ 2 - int_fan_blade_c ^ 2)", "mm",
     "= lapát vége (Z), a sarka is int_fan_tip_gap-re a kerettől"),
    ("int_fan_base_t", "1.2 mm", "mm", "Motortartó tárcsa vastagsága"),
    ("int_fan_base_r", "5 mm", "mm", "Motortartó tárcsa sugara"),
    ("int_fan_strut_w", "1.2 mm", "mm", "Küllő szélesség"),
    # ── Fő NYÁK ──
    ("int_pcb_corner_r", "1 mm", "mm", "NYÁK sarok lekerekítés"),
    ("int_esp_len", "15.4 mm", "mm", "ESP32-S3-MINI-1U hossz (külső antennás, MHF III)"),
    ("int_esp_x1", "esp_x0 + int_esp_len", "mm", "= modul hátsó éle"),
    ("int_esp_pcb_t", "0.8 mm", "mm", "ESP32-S3-MINI-1U NYÁK vastagság"),
    ("int_esp_shield_w", "14 mm", "mm", "Árnyékoló szélesség (Z)"),
    ("int_esp_shield_len", "13.55 mm", "mm", "Árnyékoló hossz (X)"),
    ("int_esp_shield_x0", "esp_x0 + 0.7 mm", "mm", "= árnyékoló eleje"),
    ("int_mhf_x", "int_esp_x1 - 1.6 mm", "mm", "= MHF III aljzat közepe (X)"),
    ("int_mhf_z", "esp_w / 2 - 2 mm", "mm", "= MHF III aljzat közepe (−Z oldalon)"),
    # ── BLE antenna + koax ──
    ("int_cx_r", "0.405 mm", "mm", "Koax sugara (Ø0,81 mm)"),
    ("int_cx_yp", "pcb_y + pcb_t + int_esp_pcb_t + 0.97 mm", "mm", "= koax a dugóból (Y)"),
    ("int_cx_xd", "pcb_x0 + pcb_len + 1.2 mm", "mm", "Koax lefutása a NYÁK-ok mögött"),
    ("int_cx_ym", "sqrt((bore_r - 0.2 mm) ^ 2 - (int_mhf_z + int_cx_r) ^ 2) - int_cx_r", "mm",
     "= koax oldalirányú átvezetése (könyöke is 0,2 mm-re a furattól)"),
    ("int_cx_yc", "bat_d / 2 + 0.2 mm + int_cx_r", "mm", "= koax a cella alatt, a horonyban"),
    ("int_ant_ri", "bms_d / 2 - 0.04 mm", "mm", "Antenna belső sugara (a kupak zsebének falán)"),
    ("int_ant_t", "0.24 mm", "mm", "Antenna vastagság (Taoglas FXP75)"),
    ("int_ant_len", "5.9 mm", "mm", "Antenna hossza (ív mentén)"),
    ("int_ant_w", "4.1 mm", "mm", "Antenna szélessége (X)"),
    ("int_ant_x0", "bms_x0 + pcb_t + 0.25 mm", "mm", "= antenna eleje"),
    ("int_cx_xr", "int_ant_x0 - int_cx_r", "mm", "= koax felfutása az antenna elülső élénél"),
    ("int_sw", "6 mm", "mm", "Tapintókapcsoló test oldalhossz"),
    ("int_sw_top", "pcb_y + pcb_t + 2.5 mm", "mm", "= kapcsoló teteje"),
    ("int_sw_body_t", "1.5 mm", "mm", "Kapcsoló műanyag test magassága"),
    ("int_sw_plate_t", "0.2 mm", "mm", "Kapcsoló acél fedőlap"),
    ("int_sw_act_r", "1.75 mm", "mm", "Kapcsoló nyomószár sugara"),
    ("int_b2b_h", "2 mm", "mm", "Panelcsatlakozó fél magassága (mindkét NYÁK-on)"),
    # ── OLED ──
    ("int_oled_x1", "oled_x0 + oled_len", "mm", "= AMOLED panel vége"),
    ("int_oled_ltps_t", "0.5 mm", "mm", "LTPS üveg vastagság"),
    ("int_oled_cap_t", "0.3 mm", "mm", "Fedőüveg vastagság"),
    ("int_oled_shelf", "4.04 mm", "mm", "Szabad LTPS perem az elején (meghajtó IC + FPC)"),
    ("int_oled_pol_w", "12.5 mm", "mm", "Polarizátor szélesség"),
    ("int_oled_act_t", "0.1 mm", "mm", "Aktív terület réteg"),
    ("int_oled_act_x0",
     "oled_x0 + int_oled_shelf + (oled_len - int_oled_shelf - oled_act_len) / 2", "mm",
     "= aktív terület eleje (a polarizátor közepén)"),
    ("int_fpc_w", "12.68 mm", "mm", "AMOLED FPC szélesség"),
    ("int_fpc_tw", "4.6 mm", "mm", "FPC vég szélessége a csatlakozóban (13 pin, 0,3 mm)"),
    ("int_fpc_t", "0.2 mm", "mm", "AMOLED FPC vastagság"),
    ("int_fpc_bond", "1.4 mm", "mm", "FPC kötés hossza a peremen"),
    ("int_fpc_xb", "oled_x0 + 1.5 mm", "mm", "FPC lehajlás kezdete a panel alatt"),
    ("int_fpc_rb", "1.2 mm", "mm", "FPC hajlítási sugár (külső)"),
    ("int_fh_h", "1 mm", "mm", "FH26 csatlakozó magasság"),
    ("int_fh_d", "2.5 mm", "mm", "FH26 csatlakozó mélység (X)"),
    ("int_fh_w", "6.3 mm", "mm", "FH26-13S hossz (Z)"),
    ("int_fpc_yt", "pcb_y + pcb_t + int_fh_h / 2 - int_fpc_t / 2", "mm",
     "= FPC vég alja (a csatlakozó nyílásának közepén)"),
    ("int_fpc_xn", "int_fpc_xb - 0.8 mm", "mm", "= FPC szűkülése a vég előtt"),
    ("int_fh_x1", "int_fpc_xn - 1.2 mm", "mm", "= FH26 bemenete"),
    # ── Akku ──
    ("int_bat_r", "bat_d / 2", "mm", "= cella sugara"),
    ("int_bat_cap_r", "4 mm", "mm", "Pozitív sapka sugara"),
    ("int_bat_cap_h", "0.6 mm", "mm", "Pozitív sapka kiemelkedése"),
    ("int_bat_wrap_t", "0.12 mm", "mm", "Zsugorcső vastagság"),
    ("int_bat_lip", "1.2 mm", "mm", "Zsugorcső peremének szélessége a cella végein"),
    ("int_bat_ins_t", "0.3 mm", "mm", "Szigetelőgyűrű vastagság"),
    ("int_tab_w", "5 mm", "mm", "Nikkel szalag szélesség"),
    ("int_tab_t", "0.15 mm", "mm", "Nikkel szalag vastagság"),
    # ── BMS + USB-C ──
    ("int_usb_mouth", "bms_x0 + pcb_t + usb_len", "mm", "= USB-C aljzat szája"),
    ("int_usb_wall", "0.3 mm", "mm", "USB-C köpeny falvastagság"),
    ("int_usb_depth", "5.8 mm", "mm", "USB-C dugó fészek mélysége"),
    ("int_spring_r", "3 mm", "mm", "Negatív érintkező rugó külső sugara"),
]

# ─────────────────────────────────────────────────────────────────────────────
# helpers (only Backend calls)
# ─────────────────────────────────────────────────────────────────────────────

def _rod_x(bk, comp, name, x0, x1, yc, zc, r, **kw):
    """Round rod along X with its axis at (yc, zc): a rectangle revolved about its own
    bottom edge, drawn on the plane z = zc."""
    pts = [(x0, yc), (x1, yc), (x1, f"({yc}) + ({r})"), (x0, f"({yc}) + ({r})")]
    return bk.revolve(comp, name, pts, axis=0, plane_z=zc, **kw)


def _rod_y(bk, comp, name, xc, y0, y1, zc, r, **kw):
    """Round rod along Y with its axis at (xc, zc): a rectangle revolved about its own
    vertical edge (segment 3), drawn on the plane z = zc. Needs y0 < y1."""
    pts = [(xc, y0), (f"({xc}) + ({r})", y0), (f"({xc}) + ({r})", y1), (xc, y1)]
    return bk.revolve(comp, name, pts, axis=3, plane_z=zc, **kw)


def _rod_z(bk, comp, name, xc, yc, z0, z1, r, **kw):
    """Round rod along Z with its axis at (xc, yc): a circle (four fitted spline arcs,
    closed by a chord of 30° — 0.034·r sagitta, invisible) extruded from z0 to z1."""
    def p(c, s_, sx, sy):
        return (f"({xc}) {sx} ({r}) * {c}", f"({yc}) {sy} ({r}) * {s_}")
    pts = [
        p("1", "0", "+", "+"),
        ("spline", [p("0.707107", "0.707107", "+", "+"), p("0", "1", "+", "+"),
                    p("0.707107", "0.707107", "-", "+"), p("1", "0", "-", "+")]),
        ("spline", [p("0.707107", "0.707107", "-", "-"), p("0", "1", "+", "-"),
                    p("0.866025", "0.5", "+", "-")]),
    ]
    return bk.extrude(comp, name, pts, z0, z1, **kw)


def _round_corners(bk, comp, name, body, x0, x1, half_w, radius):
    """Fillets the four edges parallel to Y of a board drawn x0…x1, z = ±half_w."""
    edges = [("line_y", x, z) for x in (x0, x1) for z in (half_w, neg(half_w))]
    bk.fillet(comp, name, body, edges, radius)


def _ic(bk, comp, name, x0, x1, y0, y1, z0, z1):
    """Moulded SMD package (QFN / SOT / DFN)."""
    return bk.box(comp, name, x0, x1, y0, y1, z0, z1, look="plastic_black",
                  material="plastic").body


def _mlcc(bk, comp, name, x0, y0, y1, z0, z1, length="3.2 mm", term="0.5 mm"):
    """Ceramic chip capacitor along X: ceramic body between two plated terminations."""
    xa = f"{x0} + {term}"
    xb = f"{x0} + {length} - {term}"
    xe = f"{x0} + {length}"
    bk.box(comp, name, xa, xb, y0, y1, z0, z1, look="ceramic", material="glass")
    for i, (a, b) in enumerate(((x0, xa), (xb, xe))):
        bk.box(comp, f"{name} végelektróda {i + 1}", a, b, y0, y1, z0, z1,
               look="steel", material="steel")


# ─────────────────────────────────────────────────────────────────────────────
# CeraPlas F
# ─────────────────────────────────────────────────────────────────────────────

def _ceraplas(bk, parent):
    comp = bk.component(parent, "CeraPlas F")
    x0, x1 = "cp_x0", "int_cp_x1"
    hy, hz = "cp_h / 2", "cp_w / 2"
    # PZT (≈ 7.6 g/cm³ — steel is the nearest density in the material table).
    bk.box_sym(comp, "Piezo rúd", x0, x1, neg(hy), hy, "cp_w", look="ceramic", material="steel")

    # Input half: co-fired Cu electrode terminations on both side faces.
    ex0 = "cp_x0 + cp_len / 2 + 1 mm"
    ey = f"{hy} - 0.2 mm"
    for i, (za, zb) in enumerate(((hz, f"{hz} + int_cp_el_t"),
                                  (neg(f"{hz} + int_cp_el_t"), neg(hz)))):
        bk.box(comp, f"Bemeneti elektróda {i + 1}", ex0, f"{x1} - 0.5 mm", neg(ey), ey, za, zb,
               look="copper", material="copper")

    # Soft silicone node mounts at ¼ and ¾ length inside the PEEK liner bore, slotted for the
    # bar, open for the air flow.
    mt = "int_cp_mount_t"
    mr = "int_cp_mount_r"
    for i, xc in enumerate(("cp_x0 + cp_len / 4", "cp_x0 + cp_len * 3 / 4")):
        a, b = f"{xc} - {mt} / 2", f"{xc} + {mt} / 2"
        ring = bk.tube_x(comp, f"Csomóponti tartó {i + 1}", a, b, mr,
                         look="rubber", material="plastic").body
        bk.box_sym(comp, f"Tartó {i + 1} rés", f"{a} - 0.5 mm", f"{b} + 0.5 mm", neg(hy), hy,
                   "cp_w + 2 * int_cp_el_t", op="cut", targets=[ring])
        hole = _rod_x(bk, comp, f"Tartó {i + 1} légfurat", f"{a} - 0.5 mm", f"{b} + 0.5 mm",
                      "int_cp_hole_c", "0 mm", "int_cp_hole_r", op="cut", targets=[ring])
        bk.pattern_x(comp, f"Tartó {i + 1} légfuratok", hole, "int_cp_holes")
        bk.fillet(comp, f"Tartó {i + 1} élek", ring, [("circle", a, mr), ("circle", b, mr)],
                  "0.5 mm")

    # Lead pair: from the input electrodes down under the bar, out of the back of the liner bore,
    # around the fan, to the bridge output pads under the driver board. Vertical runs end on the
    # horizontal runs' centrelines and the horizontal runs reach one wire radius past the
    # corner, so every elbow is closed and nothing pokes out beyond a run's own radius.
    r = "int_w_r"
    xs = "int_w_x0"
    xj1, xj2 = "int_w_xj1", "int_w_xj2"
    xe = "pcb_x0 + 3 mm"
    y1, y2, y3 = neg("int_w_y1"), neg("int_w_y2"), neg("int_w_y3")
    for i, (zc, look) in enumerate((("int_w_z", "plastic_white"),
                                    (neg("int_w_z"), "plastic_black"))):
        tag = f"Huzal {i + 1}"
        wire = _rod_y(bk, comp, tag, xs, y1, "0 mm", zc, r,
                      look=look, material="copper").body
        kw = dict(op="join", targets=[wire])
        _rod_x(bk, comp, f"{tag} b", f"{xs} - {r}", f"{xj1} + {r}", y1, zc, r, **kw)
        _rod_y(bk, comp, f"{tag} c", xj1, y2, y1, zc, r, **kw)
        _rod_x(bk, comp, f"{tag} d", f"{xj1} - {r}", f"{xj2} + {r}", y2, zc, r, **kw)
        _rod_y(bk, comp, f"{tag} e", xj2, y2, y3, zc, r, **kw)
        _rod_x(bk, comp, f"{tag} f", f"{xj2} - {r}", xe, y3, zc, r, **kw)
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# Ventilátor
# ─────────────────────────────────────────────────────────────────────────────

def _fan(bk, parent):
    comp = bk.component(parent, "Ventilátor")
    x0, x1 = "fan_x0", "fan_x0 + fan_len"
    kw = dict(look="fan", material="plastic")

    frame = bk.tube_x(comp, "Keret", x0, x1, "fan_d / 2", "int_fan_ri", **kw).body
    bk.fillet(comp, "Keret élek", frame, [("circle", x, "fan_d / 2") for x in (x0, x1)], "0.3 mm")

    # Motor mount on the outlet side: three spokes from the frame to a round base.
    sw = "int_fan_strut_w"
    strut = bk.box_sym(comp, "Küllő", f"{x1} - {sw}", x1, "int_fan_base_r - 0.5 mm",
                       "int_fan_ri + 0.3 mm", sw, op="join", targets=[frame])
    bk.pattern_x(comp, "Küllők", strut, "3")
    bk.tube_x(comp, "Motortartó", f"{x1} - int_fan_base_t", x1, "int_fan_base_r",
              op="join", targets=[frame])

    hub_x0 = f"{x0} + 0.6 mm"
    hub_x1 = f"{x1} - int_fan_base_t - 0.1 mm"
    hub = bk.tube_x(comp, "Rotor", hub_x0, hub_x1, "int_fan_hub_r", **kw).body
    bk.fillet(comp, "Rotor él", hub, [("circle", hub_x0, "int_fan_hub_r")], "1 mm")

    # One pitched blade at θ = 90° (+Z), joined to the hub: a thin slanted strip in XY,
    # extruded radially along Z, then patterned around X.
    bx0 = f"{x0} + 1.2 mm"
    bx1 = f"{hub_x1} - 0.6 mm"
    c, t = "int_fan_blade_c", "int_fan_blade_t"
    blade_pts = [(bx0, neg(c)), (f"{bx0} + {t}", neg(c)), (bx1, c), (f"{bx1} - {t}", c)]
    blade = bk.extrude(comp, "Lapát", blade_pts, "int_fan_hub_r - 1 mm", "int_fan_blade_r1",
                       op="join", targets=[hub])
    bk.pattern_x(comp, "Lapátok", blade, "int_fan_blades")
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# Fő NYÁK
# ─────────────────────────────────────────────────────────────────────────────

def _main_pcb(bk, parent):
    comp = bk.component(parent, "Fő NYÁK")
    x0, x1 = "pcb_x0", "pcb_x0 + pcb_len"
    top = "pcb_y + pcb_t"
    board = bk.box_sym(comp, "NYÁK", x0, x1, "pcb_y", top, "pcb_w",
                       look="pcb", material="fr4").body
    _round_corners(bk, comp, "NYÁK sarkok", board, x0, x1, "pcb_w / 2", "int_pcb_corner_r")

    # ESP32-S3-MINI-1U: module PCB + shield can, notched at the back −Z corner for the MHF III
    # receptacle that feeds the antenna in the PEEK end cap.
    esp_top = f"{top} + int_esp_pcb_t"
    sx0 = "int_esp_shield_x0"
    sx1 = "int_esp_shield_x0 + int_esp_shield_len"
    bk.box_sym(comp, "ESP32-S3 modul", "esp_x0", "int_esp_x1", top, esp_top, "esp_w",
               look="pcb", material="fr4")
    shield = bk.box_sym(comp, "ESP32-S3 árnyékolás", sx0, sx1, esp_top, f"{top} + esp_h",
                        "int_esp_shield_w", look="shield", material="steel").body
    _round_corners(bk, comp, "Árnyékolás sarkai", shield, sx0, sx1, "int_esp_shield_w / 2",
                   "0.3 mm")
    bk.box(comp, "Árnyékolás kivágás", "int_mhf_x - 1.6 mm", "int_esp_x1", esp_top,
           f"{top} + esp_h + 0.5 mm", "-(int_esp_shield_w / 2 + 0.5 mm)", "-(int_mhf_z - 1.6 mm)",
           op="cut", targets=[shield])
    bk.box(comp, "MHF III aljzat", "int_mhf_x - 1 mm", "int_mhf_x + 1 mm", esp_top,
           f"{esp_top} + 0.57 mm", "-(int_mhf_z + 1.025 mm)", "-(int_mhf_z - 1.025 mm)",
           look="gold", material="copper")

    # 6 × 6 × 2.5 SMD tact switch under the button.
    hs = "int_sw / 2"
    kx0, kx1 = f"btn_x - {hs}", f"btn_x + {hs}"
    body_top = f"{top} + int_sw_body_t"
    plate_top = f"{body_top} + int_sw_plate_t"
    bk.box_sym(comp, "Kapcsoló ház", kx0, kx1, top, body_top, "int_sw",
               look="plastic_black", material="plastic")
    bk.box_sym(comp, "Kapcsoló fedőlap", kx0, kx1, body_top, plate_top, "int_sw",
               look="steel", material="steel")
    _rod_y(bk, comp, "Kapcsoló nyomószár", "btn_x", plate_top, "int_sw_top", "0 mm",
           "int_sw_act_r", look="plastic_black", material="plastic")
    n = 0
    for lx in ("btn_x - 2.6 mm", "btn_x + 1.9 mm"):
        for za, zb in ((hs, f"{hs} + 1.2 mm"), (neg(f"{hs} + 1.2 mm"), neg(hs))):
            n += 1
            bk.box(comp, f"Kapcsoló láb {n}", lx, f"{lx} + 0.7 mm", top, f"{top} + 0.25 mm",
                   za, zb, look="steel", material="steel")

    # Between the switch and the module, under the display: 405/660 nm LED driver, the AMOLED
    # FH26-13S-0.3SHW (back-flip actuator), the 3.3 V buck + inductor in front of the module.
    _ic(bk, comp, "LED-meghajtó IC", "pcb_x0 + 10.5 mm", "pcb_x0 + 13.5 mm", top,
        f"{top} + 0.8 mm", "-7.5 mm", "-4.5 mm")
    fx0 = "int_fh_x1 - int_fh_d"
    bk.box_sym(comp, "AMOLED csatlakozó", f"{fx0} + 0.7 mm", "int_fh_x1", top,
               f"{top} + int_fh_h", "int_fh_w", look="plastic_white", material="plastic")
    bk.box_sym(comp, "AMOLED csatlakozó zár", fx0, f"{fx0} + 0.7 mm", top,
               f"{top} + int_fh_h - 0.1 mm", "int_fh_w", look="plastic_black",
               material="plastic")
    bx = "int_fpc_xb + int_fpc_rb + 0.8 mm"
    _ic(bk, comp, "3,3 V szabályzó", bx, f"{bx} + 1.6 mm", top, f"{top} + 1.1 mm",
        "-7 mm", "-4.1 mm")
    bk.box(comp, "3,3 V tekercs", bx, f"{bx} + 2.5 mm", top, f"{top} + 1.2 mm",
           "4 mm", "6 mm", look="plastic_black", material="steel")

    # Underside: board-to-board socket at the front (its header is on the driver board).
    bk.box_sym(comp, "Panelcsatlakozó aljzat", "pcb_x0 + 1 mm", "pcb_x0 + 9 mm",
               "pcb_y - int_b2b_h", "pcb_y", "4 mm", look="plastic_black", material="plastic")
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# OLED 1,1"
# ─────────────────────────────────────────────────────────────────────────────

def _oled(bk, parent):
    comp = bk.component(parent, "OLED 1,1\"")
    x0, x1 = "oled_x0", "int_oled_x1"
    hw = "oled_w / 2"
    y_l = "oled_y + int_oled_ltps_t"                 # LTPS top = shelf surface
    y_c = f"{y_l} + int_oled_cap_t"                  # cap glass top
    top = "oled_y + oled_t"                          # polarizer top
    sh = "oled_x0 + int_oled_shelf"
    gk = dict(look="glass_black", material="glass")

    # YX011T90332 stack: LTPS glass, cap glass behind the 4.04 mm shelf, polarizer on top
    # with the active area flush in its face; JD9613 driver on the exposed shelf.
    bk.box_sym(comp, "LTPS üveg", x0, x1, "oled_y", y_l, "oled_w", **gk)
    bk.box_sym(comp, "Tokozó üveg", sh, x1, y_l, y_c, "oled_w", **gk)
    pol = bk.box_sym(comp, "Polarizátor", sh, x1, y_c, top, "int_oled_pol_w", **gk).body
    ax0, ax1 = "int_oled_act_x0", "int_oled_act_x0 + oled_act_len"
    aw = "oled_act_w / 2"
    aa_bot = f"{top} - int_oled_act_t"
    bk.box_sym(comp, "Aktív terület zseb", ax0, ax1, aa_bot, f"{top} + 0.1 mm", "oled_act_w",
               op="cut", targets=[pol])
    bk.box(comp, "OLED aktív terület", ax0, ax1, aa_bot, top, neg(aw), aw,
           look="oled_on", material="glass")
    _ic(bk, comp, "JD9613 (COG)", "oled_x0 + int_fpc_bond + 0.6 mm",
        "oled_x0 + int_fpc_bond + 1.4 mm", y_l, f"{y_l} + 0.25 mm",
        f"-({hw} - 1.5 mm)", f"{hw} - 1.5 mm")

    # FPC: bonded on the shelf, wrapped round the front edge of the LTPS glass, back under it,
    # down in front of the ESP module and forward into the FH26 on the main PCB. One XY band,
    # extruded to the FPC width; the 0.3 mm-pitch tongue is narrower.
    t = "int_fpc_t"
    rb = "int_fpc_rb"
    rbi = f"({rb} - {t})"
    rwi = "int_oled_ltps_t / 2"
    rwo = f"(int_oled_ltps_t / 2 + {t})"
    yw = "oled_y + int_oled_ltps_t / 2"            # wrap centre (x0, yw)
    xs = "oled_x0 + int_fpc_bond"
    xb = "int_fpc_xb"
    yp = "oled_y"
    yt = "int_fpc_yt"
    c1y = f"{yp} - {rb}"
    c2y = f"{yt} + {rb}"
    xn = "int_fpc_xn"

    def pt(cx, cy, r, c, s_, sx, sy):
        return (f"{cx} {sx} {r} * {c}", f"{cy} {sy} {r} * {s_}")

    band = [
        (xs, f"{y_l} + {t}"),
        (x0, f"{y_l} + {t}"),
        ("spline", [pt(x0, yw, rwo, "0.707107", "0.707107", "-", "+"),
                    pt(x0, yw, rwo, "1", "0", "-", "+"),
                    pt(x0, yw, rwo, "0.707107", "0.707107", "-", "-"),
                    (x0, f"{yp} - {t}")]),
        (xb, f"{yp} - {t}"),
        ("spline", [pt(xb, c1y, rbi, "0.5", "0.866025", "+", "+"),
                    pt(xb, c1y, rbi, "0.866025", "0.5", "+", "+"), (f"{xb} + {rbi}", c1y)]),
        (f"{xb} + {rbi}", c2y),
        ("spline", [pt(xb, c2y, rbi, "0.866025", "0.5", "+", "-"),
                    pt(xb, c2y, rbi, "0.5", "0.866025", "+", "-"), (xb, f"{yt} + {t}")]),
        (xn, f"{yt} + {t}"),
        (xn, yt),
        (xb, yt),
        ("spline", [pt(xb, c2y, rb, "0.5", "0.866025", "+", "-"),
                    pt(xb, c2y, rb, "0.866025", "0.5", "+", "-"), (f"{xb} + {rb}", c2y)]),
        (f"{xb} + {rb}", c1y),
        ("spline", [pt(xb, c1y, rb, "0.866025", "0.5", "+", "+"),
                    pt(xb, c1y, rb, "0.5", "0.866025", "+", "+"), (xb, yp)]),
        (x0, yp),
        ("spline", [pt(x0, yw, rwi, "0.707107", "0.707107", "-", "-"),
                    pt(x0, yw, rwi, "1", "0", "-", "+"),
                    pt(x0, yw, rwi, "0.707107", "0.707107", "-", "+"),
                    (x0, y_l)]),
        (xs, y_l),
    ]
    fk = dict(look="copper", material="plastic")
    bk.extrude_sym(comp, "FPC", band, "int_fpc_w", **fk)
    bk.box_sym(comp, "FPC nyelv", "int_fh_x1", xn, yt, f"{yt} + {t}", "int_fpc_tw", **fk)
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# Antenna (Taoglas FXP75 in the PEEK end cap) + koax to the MINI-1U
# ─────────────────────────────────────────────────────────────────────────────

def _antenna(bk, parent):
    comp = bk.component(parent, "BLE antenna")
    # Flex antenna curved against the cap's inner wall, centred at the bottom (θ = 180°)
    # where the coax groove arrives: a tube, then only the bottom arc of int_ant_len kept.
    ro = "int_ant_ri + int_ant_t"
    ax0, ax1 = "int_ant_x0", "int_ant_x0 + int_ant_w"
    ant = bk.tube_x(comp, "Flex antenna", ax0, ax1, ro, "int_ant_ri",
                    look="copper", material="plastic").body
    half = "int_ant_len / (2 * (int_ant_ri + int_ant_t / 2)) * 180 / PI * 1 deg"
    bk.box_sym(comp, "Antenna ív", f"{ax0} - 0.5 mm", f"{ax1} + 0.5 mm",
               f"-({ro}) * cos({half})", f"{ro} + 1 mm", f"2 * ({ro}) + 2 mm",
               op="cut", targets=[ant])

    # MHF III plug on the module, then Ø0.81 coax: back over the main PCB, down behind the
    # boards, across to θ = 180°, along the cell in the bore groove, up onto the antenna feed.
    kw = dict(look="plastic_black", material="copper")
    zc = neg("int_mhf_z")
    bk.box(comp, "MHF III dugó", "int_mhf_x - 1 mm", "int_mhf_x + 1 mm",
           "pcb_y + pcb_t + int_esp_pcb_t + 0.57 mm", "pcb_y + pcb_t + int_esp_pcb_t + 1.4 mm",
           f"{zc} - 1 mm", f"{zc} + 1 mm", look="steel", material="steel")
    r = "int_cx_r"
    xd, xr = "int_cx_xd", "int_cx_xr"
    yp, ym, yc = "int_cx_yp", neg("int_cx_ym"), neg("int_cx_yc")
    coax = _rod_x(bk, comp, "Koax", "int_mhf_x + 1 mm", f"{xd} + {r}", yp, zc, r, **kw).body
    jk = dict(op="join", targets=[coax])
    _rod_y(bk, comp, "Koax le", xd, ym, yp, zc, r, **jk)
    _rod_z(bk, comp, "Koax át", xd, ym, f"{zc} - {r}", r, r, **jk)
    _rod_y(bk, comp, "Koax horony", xd, yc, ym, "0 mm", r, **jk)
    _rod_x(bk, comp, "Koax a cella mentén", f"{xd} - {r}", f"{xr} + {r}", yc, "0 mm", r, **jk)
    _rod_y(bk, comp, "Koax fel", xr, yc, neg(ro), "0 mm", r, **jk)
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# Driver NYÁK (CeraPlas full bridge + 3.7 V → 12 V boost)
# ─────────────────────────────────────────────────────────────────────────────

def _driver(bk, parent):
    comp = bk.component(parent, "Driver NYÁK")
    x0, x1 = "pcb_x0", "pcb_x0 + pcb_len"
    top = neg("drv_y")
    board = bk.box_sym(comp, "NYÁK", x0, x1, f"{top} - pcb_t", top, "drv_w",
                       look="pcb", material="fr4").body
    _round_corners(bk, comp, "NYÁK sarkok", board, x0, x1, "drv_w / 2", "int_pcb_corner_r")

    def up(h):
        return f"{top} + {h}"

    # Board-to-board header (2 × 4, 2 mm pitch) — the socket sits under the main PCB.
    bk.box_sym(comp, "Panelcsatlakozó", "pcb_x0 + 1 mm", "pcb_x0 + 9 mm", top, up("int_b2b_h"),
               "4 mm", look="plastic_black", material="plastic")
    n = 0
    for i in range(4):
        px = f"pcb_x0 + {1.75 + 2 * i:g} mm"
        for za, zb in (("0.75 mm", "1.25 mm"), ("-1.25 mm", "-0.75 mm")):
            n += 1
            bk.box(comp, f"Tüske {n}", px, f"{px} + 0.5 mm", up("int_b2b_h"),
                   "pcb_y - int_b2b_h", za, zb, look="gold", material="copper")

    # Boost stage: shielded power inductor, controller, input / output MLCC.
    ind = bk.box_sym(comp, "Boost tekercs", "pcb_x0 + 11 mm", "pcb_x0 + 16 mm", top,
                     up("3 mm"), "5 mm", look="plastic_black", material="steel").body
    _round_corners(bk, comp, "Tekercs sarkai", ind, "pcb_x0 + 11 mm", "pcb_x0 + 16 mm",
                   "2.5 mm", "0.5 mm")
    _mlcc(bk, comp, "Bemeneti kondenzátor", "pcb_x0 + 11.4 mm", top, up("2 mm"),
          "3.8 mm", "6.3 mm")
    _ic(bk, comp, "Boost IC", "pcb_x0 + 18.5 mm", "pcb_x0 + 21.5 mm", top, up("0.9 mm"),
        "-1.5 mm", "1.5 mm")
    _mlcc(bk, comp, "Kimeneti kondenzátor", "pcb_x0 + 18.4 mm", top, up("2 mm"),
          "3.8 mm", "6.3 mm")

    # CeraPlas drive: full-bridge driver IC + four FETs (3.3 × 3.3 DFN).
    _ic(bk, comp, "Híd-meghajtó IC", "pcb_x0 + 25 mm", "pcb_x0 + 29 mm", top, up("0.9 mm"),
        "-2 mm", "2 mm")
    n = 0
    for fx in ("pcb_x0 + 31.5 mm", "pcb_x0 + 36 mm"):
        for za, zb in (("0.9 mm", "4.2 mm"), ("-4.2 mm", "-0.9 mm")):
            n += 1
            _ic(bk, comp, f"FET {n}", fx, f"{fx} + 3.3 mm", top, up("1 mm"), za, zb)
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# Akku 21700
# ─────────────────────────────────────────────────────────────────────────────

def _battery(bk, parent):
    comp = bk.component(parent, "Akku 21700")
    R = "int_bat_r"
    wt = "int_bat_wrap_t"
    lip_r = f"{R} - int_bat_lip"
    xa = "bat_x0 + int_bat_cap_h"        # front shoulder
    xb = "bat_x0 + bat_len"              # negative end
    xf = f"{xa} + {wt}"                  # steel front face
    xr = f"{xb} - {wt}"                  # steel back face

    wrap = [(xa, lip_r), (xf, lip_r), (xf, f"{R} - {wt}"), (xr, f"{R} - {wt}"), (xr, lip_r),
            (xb, lip_r), (xb, R), (xa, R)]
    bk.revolve(comp, "Zsugorcső", wrap, look="battery_wrap", material="plastic")
    bk.revolve(comp, "Cella", [(xf, "0 mm"), (xr, "0 mm"), (xr, f"{R} - {wt}"),
                               (xf, f"{R} - {wt}")], look="steel", material="battery")
    cap = bk.tube_x(comp, "Pozitív sapka", "bat_x0", xf, "int_bat_cap_r",
                    look="steel", material="steel").body
    bk.fillet(comp, "Sapka él", cap, [("circle", "bat_x0", "int_bat_cap_r")], "0.25 mm")
    bk.tube_x(comp, "Szigetelőgyűrű", f"{xf} - int_bat_ins_t", xf, lip_r,
              "int_bat_cap_r + 0.5 mm", look="plastic_white", material="plastic")

    # Nickel strip from the + cap down to the boost input pad at the back of the driver board.
    bk.box_sym(comp, "Nikkel szalag", "bat_x0 - int_tab_t", "bat_x0", neg("drv_y"),
               "int_bat_cap_r - 1.5 mm", "int_tab_w", look="steel", material="steel")
    bk.box_sym(comp, "Nikkel szalag (forrasztás)", "pcb_x0 + pcb_len - 3.5 mm",
               "bat_x0 - int_tab_t", neg("drv_y"), "-(drv_y) + int_tab_t", "int_tab_w",
               look="steel", material="steel")
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# BMS + USB-C
# ─────────────────────────────────────────────────────────────────────────────

def _bms(bk, parent):
    comp = bk.component(parent, "BMS + USB-C")
    x0, x1 = "bms_x0", "bms_x0 + pcb_t"
    bk.tube_x(comp, "NYÁK", x0, x1, "bms_d / 2", look="pcb", material="fr4")

    # Vertical receptacle on the back face; its mouth is 0.3 mm inside the cap face.
    hy, hz = "usb_h / 2", "usb_w / 2"
    ux1 = "int_usb_mouth"
    shell = bk.box_sym(comp, "USB-C aljzat", x1, ux1, neg(hy), hy, "usb_w",
                       look="steel", material="steel").body
    bk.fillet(comp, "USB-C köpeny ív", shell,
              [("line_x", y, z) for y in (hy, neg(hy)) for z in (hz, neg(hz))],
              "usb_h / 2 - 0.05 mm")
    # Stadium plug opening: a box between the two end centres plus two round ends.
    pr = f"{hy} - int_usb_wall"
    zc = f"{hz} - {hy}"
    px0, px1 = f"{ux1} - int_usb_depth", f"{ux1} + 0.5 mm"
    bk.box_sym(comp, "USB-C fészek", px0, px1, neg(pr), pr, f"2 * ({zc})",
               op="cut", targets=[shell])
    for i, z in enumerate((zc, neg(zc))):
        _rod_x(bk, comp, f"USB-C fészek ív {i + 1}", px0, px1, "0 mm", z, pr,
               op="cut", targets=[shell])
    bk.box_sym(comp, "USB-C nyelv", f"{ux1} - int_usb_depth", f"{ux1} - 0.9 mm",
               "-0.35 mm", "0.35 mm", "6.69 mm", look="plastic_black", material="plastic")

    # Protection and charger ICs on the face toward the cell (the back face is the cap's).
    _ic(bk, comp, "Védő IC", f"{x0} - 1.1 mm", x0, "5 mm", "6.6 mm", "-1.45 mm", "1.45 mm")
    _ic(bk, comp, "Töltő IC", f"{x0} - 0.75 mm", x0, "-7 mm", "-4 mm", "-1.5 mm", "1.5 mm")

    # Compressed contact spring between the cell's negative end and the board.
    bk.tube_x(comp, "Negatív rugó", "bat_x0 + bat_len - int_bat_wrap_t", x0, "int_spring_r",
              "int_spring_r - 0.6 mm", look="steel", material="steel")
    return comp


def build_shared(bk, parent):
    return [
        _ceraplas(bk, parent),
        _fan(bk, parent),
        _main_pcb(bk, parent),
        _oled(bk, parent),
        _antenna(bk, parent),
        _driver(bk, parent),
        _battery(bk, parent),
        _bms(bk, parent),
    ]
