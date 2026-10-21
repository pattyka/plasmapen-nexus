"""PlasmaPen Nexus — Package H, the insert: "Betét (PEI)" sled and the B1 shield foil.

    build_shell(bk, parent, cutaway)  "Betét (PEI)"     (cut in half if cutaway)
    build_shared(bk, parent)          "Árnyékolás"

Frame of pp_params: X = pen axis (x = 0 nozzle face, +X back), Y = up (display flat), Z = side.

One injection-moulded PEI part, sled_wall thick: a tube r sled_ri … sled_r sliced to the housing
bore's double-D (flats sled_top / −sled_bot, sled_c inside the bore all round), four bulkheads
B0 … B3 (b_t), two ribs that ride the housing's rail grooves. Nose cone + liner + this sled +
everything inside slide into the housing from the front as one cartridge; the end cap's spigot
lugs pass the B3 slots and lock behind B3.

Compartments (BRIEF "architecture"):
  P  plasma island, B0 → B1: HV liner + piezo, plasma board on two ledges under the liner, the
     blower with its plenum into the liner's rear opening. Air enters through the B0 notches,
     which line up with the nose spigot's grooves (θ = ±90°, 180°, never near θ = 0).
  A  the flex tunnel on top of P (PEI floor tun_floor_t over the liner, walls ins_tun_wall), the
     AI bay B1 → B2 (bridge board through the B1 window, AI board on ledges, display FPC window in
     the roof), the battery bay B2 → B3 (open top and bottom: the cell's sleeve faces the alu).
Barrier = B1 + the tunnel floor; liner_wall + tun_floor_t of solid plastic between the piezo and
every A-side part (ins_chk_hv). "Árnyékolás": 0.1 mm copper on B1's A face, windows cut out.
"""

from pp_core import neg


def _p(e):
    return f"({e})"


def _max(a, b):
    return f"({_p(a)} + {_p(b)} + abs({_p(a)} - {_p(b)})) / 2"


EXTRA_PARAMS = [
    ("ins_tun_wall", "0.8 mm", "mm", "A-csatorna oldalfala"),
    ("ins_air_w", "4.5 mm", "mm", "B0 légbeömlő szélesség (az orrkúp csap hornyaihoz igazítva)"),
    ("ins_air_in", "2 mm", "mm", "B0 légbeömlő mélysége befelé a betét falától"),
    ("ins_chk_air", "3 * ins_air_w * ins_air_in / (1 mm) - 20 mm", "mm",
     "ELLENŐRZÉS: B0 légbeömlők keresztmetszete ≥ 20 mm² (mm²-ben)"),
    ("ins_chk_fit", "sled_c - 0.2 mm", "mm", "ELLENŐRZÉS: betét ↔ furat hézag ≥ 0,2 mm"),
    ("ins_chk_hv", "liner_wall + tun_floor_t - 2.5 mm", "mm",
     "ELLENŐRZÉS: ≥ 2,5 mm tömör műanyag a piezo és az A-oldal között"),
    ("ins_ledge_in", "1 mm", "mm", "NYÁK-tartó borda a NYÁK széle alatt (befelé)"),
    ("ins_ledge_out", "0.3 mm", "mm", "NYÁK-tartó borda a NYÁK szélén túl"),
    ("ins_plenum_r", "liner_ro + 0.5 mm", "mm", "= fúvó plénum külső sugara"),
    ("ins_plenum_t", "0.4 mm", "mm", "Plénum hátfal (a fúvó kifúvója előtt)"),
    ("ins_coax_z", "bat_d / 2 + 1 mm", "mm", "Antenna koax átvezetés helye (Z, y = bat_y)"),
    ("ins_coax_r", "0.8 mm", "mm", "Koax átvezetés sugara (Ø0,81 koax + hézag)"),
    ("ins_flex_r", "4 mm", "mm", "Dokk flex átvezetés sugara B3-ban (Ø8)"),
    ("ins_bay_w", "3.4 mm", "mm", "Bajonett horony szélesség B3-ban (θ = ±90°)"),
    ("ins_bay_r0", "6 mm", "mm", "Bajonett horony belső sugara"),
    ("ins_bay_r1", "bore_top + 0.1 mm", "mm", "= bajonett horony külső sugara"),
    ("ins_shield_t", "0.1 mm", "mm", "Réz árnyékoló fólia vastagság"),
]

BIG = "body_r + 3 mm"
TUN_IN = "tun_floor + tun_floor_t"          # tunnel interior bottom (flex rests here)


def _vrect(xc, r, y0, y1):
    """Rectangle with segment 3 on x = xc (revolve axis=3 → cylinder along Y)."""
    return [(xc, y0), (f"{_p(xc)} + {_p(r)}", y0), (f"{_p(xc)} + {_p(r)}", y1), (xc, y1)]


def _xrect(x0, x1, yc, r):
    """Rectangle with segment 0 on y = yc (revolve axis=0 → cylinder along X)."""
    return [(x0, yc), (x1, yc), (x1, f"{_p(yc)} + {_p(r)}"), (x0, f"{_p(yc)} + {_p(r)}")]


def _ledge_y0(z_out):
    """Bottom of a board ledge: 0.4 mm into the sled wall at its outer edge, never below the
    bottom flat's wall."""
    return _max(f"-(sqrt(sled_ri ^ 2 - ({z_out}) ^ 2) + 0.4 mm)", "-(sled_bot - 0.3 mm)")


def _ledges(bk, comp, sled, name, x0, x1, half_w, top):
    zi = f"{half_w} - ins_ledge_in"
    zo = f"{half_w} + ins_ledge_out"
    y0 = _ledge_y0(zo)
    bk.box(comp, f"{name} 1", x0, x1, y0, top, zi, zo, op="join", targets=[sled])
    bk.box(comp, f"{name} 2", x0, x1, y0, top, neg(zo), neg(zi), op="join", targets=[sled])


def _wall_cut(bk, comp, sled, name, x0, y0, y1, width):
    """Rectangular window through a bulkhead whose front face is at x0."""
    return bk.box_sym(comp, name, f"{x0} - 0.1 mm", f"{x0} + b_t + 0.1 mm", y0, y1, width,
                      op="cut", targets=[sled])


def _section_cut(bk, comp, body, x0, x1, inset):
    """Trim to the double-D: remove y > sled_top − inset and y < −(sled_bot − inset)."""
    bk.box_sym(comp, "Felső sík", x0, x1, f"sled_top - {_p(inset)}", BIG, "2 * body_r + 6 mm",
               op="cut", targets=[body])
    bk.box_sym(comp, "Alsó sík", x0, x1, neg(BIG), f"-(sled_bot - {_p(inset)})",
               "2 * body_r + 6 mm", op="cut", targets=[body])


def build_shell(bk, parent, cutaway):
    comp = bk.component(parent, "Betét (PEI)")
    sled = bk.tube_x(comp, "Betét", "sled_x0", "sled_x1", "sled_r", "sled_ri",
                     look="pei", material="pei").body
    for label, x0 in (("B0", "sled_x0"), ("B1", "b1_x0"), ("B2", "b2_x0"), ("B3", "b3_x0")):
        bk.tube_x(comp, label, x0, f"{x0} + b_t", "sled_r", op="join", targets=[sled])
    # Flat walls of the double-D, then trim the round tube + bulkheads to it.
    bk.box_sym(comp, "Felső fal", "sled_x0", "sled_x1", "sled_top_i", "sled_top",
               "2 * sqrt(sled_r ^ 2 - sled_top ^ 2)", op="join", targets=[sled])
    bk.box_sym(comp, "Alsó fal", "sled_x0", "sled_x1", "-(sled_bot)", "-(sled_bot_i)",
               "2 * sqrt(sled_r ^ 2 - sled_bot ^ 2)", op="join", targets=[sled])
    _section_cut(bk, comp, sled, "sled_x0 - 1 mm", "sled_x1 + 1 mm", "0 mm")
    # Ribs that ride the rail grooves.
    for k, (z0, z1) in enumerate((("sled_r - 0.3 mm", "bore_r + rib_h"),
                                  ("-(bore_r + rib_h)", "-(sled_r - 0.3 mm)")), 1):
        bk.box(comp, f"Csúszóborda {k}", "sled_x0", "sled_x1", "-(rib_w / 2)", "rib_w / 2",
               z0, z1, op="join", targets=[sled])

    # ── P compartment ──
    bk.tube_x(comp, "B0 bélés furat", "sled_x0 - 0.1 mm", "sled_x0 + b_t + 0.1 mm",
              "liner_ro + 0.1 mm", op="cut", targets=[sled])
    hw = "ins_air_w / 2"
    side = bk.box(comp, "B0 légbeömlő", "sled_x0 - 0.5 mm", "sled_x0 + b_t", neg(hw), hw,
                  "sled_ri - ins_air_in", BIG, op="cut", targets=[sled])
    bk.pattern_x(comp, "B0 légbeömlők oldalt", side, "2")
    bk.box_sym(comp, "B0 légbeömlő alul", "sled_x0 - 0.5 mm", "sled_x0 + b_t", neg(BIG),
               "-(sled_bot_i - ins_air_in)", "ins_air_w", op="cut", targets=[sled])
    _ledges(bk, comp, sled, "Plazma NYÁK borda", "pboard_x0", "pboard_x1", "pboard_w / 2",
            "pcb_y - pboard_t")
    # ── A tunnel over the P compartment ──
    bk.box_sym(comp, "Csatorna padló", "sled_x0", "b1_x0", "tun_floor", TUN_IN,
               "tun_w + 2 * ins_tun_wall", op="join", targets=[sled])
    for k, (z0, z1) in enumerate((("tun_w / 2", "tun_w / 2 + ins_tun_wall"),
                                  ("-(tun_w / 2 + ins_tun_wall)", "-(tun_w / 2)")), 1):
        bk.box(comp, f"Csatorna fal {k}", "sled_x0", "b1_x0", "tun_floor", "sled_top_i + 0.5 mm",
               z0, z1, op="join", targets=[sled])
    _wall_cut(bk, comp, sled, "B0 csatorna átvezetés", "sled_x0", TUN_IN, "sled_top_i", "tun_w")
    bk.revolve(comp, "Gomb furat", _vrect("btn_x", "1.65 mm", "sled_top_i - 0.1 mm",
                                          "sled_top + 0.1 mm"),
               axis=3, op="cut", targets=[sled])

    # Blower plenum (hangs from the tunnel floor): sleeve over the liner's rear end + a back wall with the outlet port.
    bk.revolve(comp, "Plénum", [("liner_x1 - 2 mm", "liner_ro + 0.1 mm"),
                                ("fan_x0", "liner_ro + 0.1 mm"),
                                ("fan_x0", "ins_plenum_r"),
                                ("liner_x1 - 2 mm", "ins_plenum_r")],
               op="join", targets=[sled])
    bk.tube_x(comp, "Plénum fal", "fan_x0 - ins_plenum_t", "fan_x0", "ins_plenum_r",
              op="join", targets=[sled])
    bk.box_sym(comp, "Plénum nyílás", "fan_x0 - ins_plenum_t - 0.1 mm", "fan_x0 + 0.1 mm",
               "-(fan_h / 2 - 0.3 mm)", "fan_h / 2 - 0.3 mm", "2 * liner_ri", op="cut",
               targets=[sled])


    # ── B1: barrier, bridge window, tunnel exit ──
    _wall_cut(bk, comp, sled, "B1 híd ablak", "b1_x0", "pcb_y - 5 mm", "pcb_y + 4 mm",
              "bridge_w + 1 mm")
    _wall_cut(bk, comp, sled, "B1 csatorna kijárat", "b1_x0", TUN_IN, "sled_top_i", "tun_w")
    _ledges(bk, comp, sled, "Híd borda P", "bridge_x0", "b1_x0", "bridge_w / 2", "pcb_y - pcb_t")
    _ledges(bk, comp, sled, "Híd borda A", "b1_x0 + b_t + ins_shield_t", "bridge_x1",
            "bridge_w / 2", "pcb_y - pcb_t")

    # ── AI bay ──
    _ledges(bk, comp, sled, "AI NYÁK borda", "ai_x0", "ai_x1", "ai_w / 2", "pcb_y - pcb_t")
    bk.box_sym(comp, "Kijelző FPC ablak", "oled_x1 - 4 mm", "oled_x1 + 1.5 mm",
               "sled_top_i - 0.1 mm", "sled_top + 0.1 mm", "oled_fpc_w + 1 mm",
               op="cut", targets=[sled])

    # ── B2: cell contact window + antenna coax ──
    bk.revolve(comp, "B2 érintkező ablak",
               _xrect("b2_x0 - 0.1 mm", "b2_x0 + b_t + 0.1 mm", "bat_y", "5 mm"),
               axis=0, op="cut", targets=[sled])
    for label, x0 in (("B2", "b2_x0"), ("B3", "b3_x0")):
        bk.revolve(comp, f"{label} koax furat",
                   _xrect(f"{x0} - 0.1 mm", f"{x0} + b_t + 0.1 mm", "bat_y", "ins_coax_r"),
                   axis=0, plane_z="ins_coax_z", op="cut", targets=[sled])

    # ── battery bay: open top and bottom ──
    bk.box_sym(comp, "Akku ablak felül", "bat_x0", "bat_x1", "sled_top_i - 0.1 mm",
               "sled_top + 0.1 mm", "bat_d - 2 mm", op="cut", targets=[sled])
    bk.box_sym(comp, "Akku ablak alul", "bat_x0", "bat_x1", "-(sled_bot + 0.1 mm)",
               "-(sled_bot_i - 0.1 mm)", "bat_d - 2 mm", op="cut", targets=[sled])

    # ── B3: dock flex + bayonet slots for the cap lugs ──
    bk.tube_x(comp, "B3 flex furat", "b3_x0 - 0.1 mm", "sled_x1 + 0.1 mm", "ins_flex_r",
              op="cut", targets=[sled])
    for k, (z0, z1) in enumerate((("ins_bay_r0", "ins_bay_r1"),
                                  ("-(ins_bay_r1)", "-(ins_bay_r0)")), 1):
        bk.box(comp, f"Bajonett horony {k}", "b3_x0 - 0.1 mm", "sled_x1 + 0.1 mm",
               "-(ins_bay_w / 2)", "ins_bay_w / 2", z0, z1, op="cut", targets=[sled])

    if cutaway:
        bk.cut_half(comp, "Metszet", [sled])
    return [comp]


def build_shared(bk, parent):
    comp = bk.component(parent, "Árnyékolás")
    x0 = "b1_x0 + b_t"
    x1 = "b1_x0 + b_t + ins_shield_t"
    foil = bk.tube_x(comp, "Árnyékolás", x0, x1, "sled_ri - 0.05 mm", look="shield",
                     material="copper").body
    bk.box_sym(comp, "Felső sík", f"{x0} - 0.1 mm", f"{x1} + 0.1 mm", "sled_top_i - 0.05 mm",
               BIG, "2 * body_r + 6 mm", op="cut", targets=[foil])
    bk.box_sym(comp, "Alsó sík", f"{x0} - 0.1 mm", f"{x1} + 0.1 mm", neg(BIG),
               "-(sled_bot_i - 0.05 mm)", "2 * body_r + 6 mm", op="cut", targets=[foil])
    bk.box_sym(comp, "Híd ablak", f"{x0} - 0.1 mm", f"{x1} + 0.1 mm", "pcb_y - 5 mm",
               "pcb_y + 4 mm", "bridge_w + 1 mm", op="cut", targets=[foil])
    bk.box_sym(comp, "Csatorna kijárat", f"{x0} - 0.1 mm", f"{x1} + 0.1 mm", TUN_IN,
               "sled_top_i", "tun_w", op="cut", targets=[foil])
    return [comp]
