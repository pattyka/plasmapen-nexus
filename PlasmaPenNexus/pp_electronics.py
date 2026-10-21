"""PlasmaPen Nexus — electronics, shared by the render and the engineering assembly.

    build_shared(bk, parent) -> ["Plazma NYÁK", "Ventilátor", "Vezérlő híd", "AI NYÁK",
                                 'AMOLED 1,91"', "Akku 21700", "Dokk NYÁK", "Dokk érintkezők",
                                 "Mágnesek", "BLE antenna"]

Frame of pp_params (X = pen axis, +X toward the back, Y = up / display, Z = side). Every board
top face lies on pcb_y, under the HV liner. Plasma island (P) between B0 and B1, user side (A)
behind B1; only the bridge board crosses B1, through its sealed window.

Outlines from the datasheets (BRIEF.md "REVISION 4 — research"):
  · STM32G474 UFQFPN48 7 × 7 × 0.55; half-bridge MOSFETs 3.3 × 3.3 DFN; resonant inductor
    5.5 × 5.3 × 3.0 (shielded, 82 kHz CeraPlas HF drive).
  · Sunon UB3H3-700 blower 17 × 17 × 3, axial inlet on top, outlet toward the liner.
  · TI ISO7741 wide SOIC-16 (body 10.3 × 7.5 × 2.65, 16 leads, 1.27 pitch) with its isolation
    barrier on B1's mid-plane; TI SN6507 HVSSOP-10 3 × 3 × 1.1; Würth WE-PPTI 1308 push-pull
    transformer (13 × 8 × 3.8 reserved) under the bridge, straddling B1.
  · ESP32-S3-WROOM-1U-N16R8 18 × 19.2 × 3.2 (PCB 0.8 + shield can), U.FL at its antenna end.
  · 1.91" AMOLED 240 × 536 (RM67162 + FT3168 touch), panel 22.4 × 51.32, active area
    19.8 × 44.22; driver shelf at the back; FPC wraps round the back edge and drops to the
    AI board.
  · Samsung INR21700-50E Ø21.25 × 70.8, + cap at the front (B2), − at the back (B3).
  · Dock: flush gold targets in the cap's bottom flat (the dock carries Mill-Max 0906 spring
    pins), N52 magnets Ø3 × 1.5, status LED that lights the frosted cap from inside.
  · Taoglas FXP75 flex antenna 5.9 × 4.1 × 0.24 on Ø0.81 coax.
Battery leads and the dock flex reach the AI board (charger + BMS) through B2's contact
window (Ø10 on the cell axis); the dock flex crosses B3 through its Ø8 hole on the pen axis;
the coax runs along the cell through the B2 and B3 coax holes and enters the cap through the
coax slot in the cap spigot (pp_shell).
"""

from pp_core import neg

EXTRA_PARAMS = [
    # ── allgemein ──
    ("el_pcb_r", "1 mm", "mm", "NYÁK sarok lekerekítés"),
    ("el_fpc_t", "0.12 mm", "mm", "FPC vastagság"),
    ("el_y_top", "pcb_y", "mm", "= NYÁK-ok felső lapja"),
    # ── Plazma NYÁK ──
    ("el_pb_bot", "pcb_y - pboard_t", "mm", "= plazma NYÁK alja"),
    ("el_pin_hole_r", "cp_pin_d / 2 + 0.15 mm", "mm", "= piezo tüske furat sugara a NYÁK-ban"),
    ("el_pin_pad_r", "0.8 mm", "mm", "Tüske forrasztási pad sugara"),
    ("el_fet_x0", "cp_pin_x + 1.6 mm", "mm", "= FET-ek eleje (a tüskék mögött)"),
    ("el_drv_x0", "el_fet_x0 + 4.5 mm", "mm", "= gate driver eleje"),
    ("el_mcu_x0", "el_drv_x0 + 4 mm", "mm", "= STM32G474 eleje"),
    ("el_ind_x0", "el_mcu_x0 + 7.8 mm", "mm", "= rezonáns tekercs eleje"),
    # ── Vezérlő híd ──
    ("el_b1_mid", "b1_x0 + b_t / 2", "mm", "= B1 középsíkja (izolációs gát)"),
    ("el_iso_top", "pcb_y + 2.65 mm", "mm", "= ISO7741 teteje"),
    ("el_xf_h", "3.8 mm", "mm", "Leválasztó trafó magasság (a híd alján)"),
    # ── AI NYÁK ──
    ("el_ai_bot", "pcb_y - pcb_t", "mm", "= AI NYÁK alja"),
    ("el_cc_x0", "ai_x0 + 1.2 mm", "mm", "= kamera FPC csatlakozó eleje"),
    ("el_esp_x0", "ai_x0 + 1.2 mm", "mm", "= ESP32-S3-WROOM-1U eleje (a NYÁK alján)"),
    ("el_esp_x1", "el_esp_x0 + 19.2 mm", "mm", "= modul vége (U.FL itt)"),
    ("el_esp_pcb", "pcb_y - pcb_t - 0.8 mm", "mm", "= modul NYÁK alsó lapja (lefelé szerelve)"),
    ("el_ufl_z", "7.1 mm", "mm", "U.FL aljzat közepe (Z)"),
    ("el_dc_x0", "oled_x1 - 6.8 mm", "mm", "= kijelző FPC csatlakozó eleje"),
    ("el_conn_mid", "pcb_y + 0.5 mm", "mm", "= FPC csatlakozók résének közepe"),
    # ── Kamera flex (A csatorna) ──
    ("el_cf_x0", "nose_split - 0.3 mm", "mm", "= kamera flex eleje (az orrkúp résében)"),
    ("el_cf_y0", "tun_floor + tun_floor_t + 0.02 mm", "mm", "= flex alja a csatornában"),
    ("el_cf_w", "8 mm", "mm", "Kamera flex szélesség"),
    ("el_cf_xb", "ai_x0 - 2.8 mm", "mm", "= flex lehajlásának kezdete az AI rekeszben"),
    ("el_cf_r1", "1.2 mm", "mm", "Flex felső hajlítás sugara"),
    ("el_cf_r2", "1 mm", "mm", "Flex alsó hajlítás sugara"),
    # ── AMOLED ──
    ("el_pan_y0", "top_y - glass_t - oled_t", "mm", "= panel alja"),
    ("el_pan_y1", "top_y - glass_t", "mm", "= panel teteje (az üveg alatt)"),
    ("el_shelf", "4 mm", "mm", "Meghajtó perem hossza a panel hátulján"),
    ("el_shelf_y", "el_pan_y0 + 0.5 mm", "mm", "= perem felülete (TFT üveg)"),
    ("el_df_r1", "0.4 mm", "mm", "Kijelző FPC hajlítás a panel élén"),
    ("el_df_r2", "1 mm", "mm", "Kijelző FPC hajlítás a csatlakozó előtt"),
    ("el_df_xo", "oled_x1 + el_df_r1", "mm", "= FPC függőleges szakasz külső lapja"),
    # ── Akku ──
    ("el_bat_r", "bat_d / 2", "mm", "= cella sugara"),
    ("el_bat_wrap", "0.12 mm", "mm", "Zsugorcső vastagság"),
    ("el_bat_lip", "1.2 mm", "mm", "Zsugorcső pereme a cella végein"),
    ("el_bat_cap_r", "4 mm", "mm", "Pozitív sapka sugara"),
    ("el_bat_cap_h", "0.6 mm", "mm", "Pozitív sapka kiemelkedése"),
    ("el_plate_r", "2.9 mm", "mm", "Érintkező lemez sugara"),
    ("el_spring_r", "2.8 mm", "mm", "Érintkező rugó külső sugara"),
    ("el_tab_w", "3 mm", "mm", "Nikkel szalag szélesség"),
    ("el_tab_t", "0.15 mm", "mm", "Nikkel szalag vastagság"),
    ("el_ptab_y", "bat_y - 2.9 mm", "mm", "= + szalag magassága a B2 ablakban"),
    ("el_mplate_x0", "b3_x0 - 0.2 mm", "mm", "= − lemez eleje (B3 előtt)"),
    # ── Dokk ──
    ("el_dk_y0", "-(bot_y) + cap_floor", "mm", "= dokk NYÁK alja"),
    ("el_dk_y1", "el_dk_y0 + dock_pcb_t", "mm", "= dokk NYÁK teteje"),
    ("el_dk_x0", "body_end + 0.8 mm", "mm", "= dokk NYÁK eleje"),
    ("el_dk_x1", "pen_len - cap_rear - 0.3 mm", "mm", "= dokk NYÁK vége"),
    ("el_dk_w", "14 mm", "mm", "Dokk NYÁK szélesség"),
    ("el_dfx_z", "-3.4 mm", "mm", "Dokk flex Z helye a B2 / B3 nyílásban"),
    ("el_dfx_w", "1.5 mm", "mm", "Dokk flex szélesség"),
    ("el_dfx_side", "-(el_bat_r + 0.68 mm)", "mm", "= dokk flex a cella oldalán (Z)"),
    ("el_dfx_xf", "bat_x0 - 0.72 mm", "mm", "= dokk flex befordulás a cella előtt"),
    ("el_dfx_xr", "bat_x1 + 0.1 mm", "mm", "= dokk flex befordulás a cella mögött"),
    ("el_dfx_xd", "b3_x0 + b_t + 1 mm", "mm", "= dokk flex lefordulása a kupak csapjában"),
    ("el_dfx_yd", "-6.25 mm", "mm", "Dokk flex magassága a kupakban"),
    # ── Koax + antenna ──
    ("el_cx_r", "0.405 mm", "mm", "Koax sugara (Ø0,81)"),
    ("el_cx_y", "el_esp_pcb - 1.68 mm", "mm", "= koax a dugóból (Y, a NYÁK alatt)"),
    ("el_cx_xa", "ai_x1 - 1 mm", "mm", "= koax felfut az AI NYÁK sarokkivágásán át"),
    ("el_cx_zs", "bat_d / 2 + 1 mm", "mm", "= koax a cella oldalán (Z), a B2 / B3 koax furatban"),
    ("el_cx_xn", "body_end - cap_spigot + 0.8 mm", "mm",
     "= koax befordul a kupak csapjának résén át (B3 koax furata mögött)"),
    ("el_cx_zh", "3.5 mm", "mm", "Koax Z helye a kupak üregében (antenna betáp)"),
    ("el_cx_yd", "-4.5 mm", "mm", "Koax magassága a kupakban"),
    ("el_ant_x0", "dock_xc - 2.1 mm", "mm", "= antenna eleje"),
    ("el_ant_y1", "-2.06 mm", "mm", "Antenna teteje (dokk zseb teteje alatt)"),
    ("el_ant_z0", "0.55 mm", "mm", "Antenna Z kezdete"),
    # ── ellenőrzések ──
    ("el_chk_aa", "glass_border + oled_act_x - 0.5 mm", "mm",
     "ELLENŐRZÉS: aktív terület az üveg látható részén belül (X)"),
    ("el_chk_aa_w", "glass_w / 2 - oled_act_w / 2 - 0.5 mm", "mm",
     "ELLENŐRZÉS: aktív terület az üveg látható részén belül (Z)"),
    ("el_chk_cf", "el_cf_xb - b1_x0 - b_t - 3 mm", "mm",
     "ELLENŐRZÉS: kamera flex lehajlása B1 és az ISO7741 mögött"),
    ("el_chk_df", "el_df_xo - el_df_r2 - el_dc_x0 - 4 mm", "mm",
     "ELLENŐRZÉS: kijelző FPC alsó íve a csatlakozó mögött"),
    ("el_chk_aa_len", "oled_len - oled_act_x - oled_act_len - el_shelf - 0.3 mm", "mm",
     "ELLENŐRZÉS: aktív terület nem lóg a meghajtó peremre"),
    ("el_chk_ai_pack", "el_cx_xa - 0.8 mm - el_esp_x1 - 3.6 mm", "mm",
     "ELLENŐRZÉS: ESP32 + töltő a koax kivágás előtt fér el az AI NYÁK alján"),
    ("el_chk_cx_cav", "8 mm - sqrt(el_cx_yd ^ 2 + el_cx_zh ^ 2) - el_cx_r - 0.3 mm", "mm",
     "ELLENŐRZÉS: koax a kupak Ø16 üregében"),
    ("el_chk_under", "pcb_under + pboard_t - pcb_t - el_xf_h - 0.3 mm", "mm",
     "ELLENŐRZÉS: trafó (a legmélyebb alkatrész) fér a pcb_under helyre"),
    ("el_chk_flex", "4 mm - sqrt((el_dfx_z - el_fpc_t) ^ 2 + (el_dfx_w / 2) ^ 2) - 0.2 mm", "mm",
     "ELLENŐRZÉS: dokk flex a B3 Ø8 nyílásában"),
]


# ─────────────────────────────────────────────────────────────────────────────
# helpers (only Backend calls)
# ─────────────────────────────────────────────────────────────────────────────

def _p(e):
    return f"({e})"


def _rod_x(bk, comp, name, x0, x1, yc, zc, r, **kw):
    """Round rod along X, axis at (yc, zc): a rectangle revolved about its bottom edge on the
    plane z = zc."""
    pts = [(x0, yc), (x1, yc), (x1, f"{_p(yc)} + {_p(r)}"), (x0, f"{_p(yc)} + {_p(r)}")]
    return bk.revolve(comp, name, pts, axis=0, plane_z=zc, **kw)


def _rod_y(bk, comp, name, xc, y0, y1, zc, r, **kw):
    """Round rod along Y, axis at (xc, zc): a rectangle revolved about its vertical edge
    (segment 3) on the plane z = zc. Needs y0 < y1."""
    pts = [(xc, y0), (f"{_p(xc)} + {_p(r)}", y0), (f"{_p(xc)} + {_p(r)}", y1), (xc, y1)]
    return bk.revolve(comp, name, pts, axis=3, plane_z=zc, **kw)


def _rod_z(bk, comp, name, xc, yc, z0, z1, r, **kw):
    """Round rod along Z, axis at (xc, yc): four fitted spline arcs closed by a 30° chord
    (0.034 · r sagitta), extruded z0 … z1."""
    def p(c, s_, sx, sy):
        return (f"{_p(xc)} {sx} {_p(r)} * {c}", f"{_p(yc)} {sy} {_p(r)} * {s_}")
    pts = [
        p("1", "0", "+", "+"),
        ("spline", [p("0.707107", "0.707107", "+", "+"), p("0", "1", "+", "+"),
                    p("0.707107", "0.707107", "-", "+"), p("1", "0", "-", "+")]),
        ("spline", [p("0.707107", "0.707107", "-", "-"), p("0", "1", "+", "-"),
                    p("0.866025", "0.5", "+", "-")]),
    ]
    return bk.extrude(comp, name, pts, z0, z1, **kw)


def _tube_off(bk, comp, name, x0, x1, yc, r_out, r_in, **kw):
    """Tube along X on the axis (yc, 0): a rod, its core cut out."""
    tube = _rod_x(bk, comp, name, x0, x1, yc, "0 mm", r_out, **kw).body
    _rod_x(bk, comp, f"{name} furat", f"{x0} - 0.1 mm", f"{x1} + 0.1 mm", yc, "0 mm", r_in,
           op="cut", targets=[tube])
    return tube


def _corners(bk, comp, name, body, x0, x1, hw, radius):
    edges = [("line_y", x, z) for x in (x0, x1) for z in (hw, neg(hw))]
    bk.fillet(comp, name, body, edges, radius)


def _board(bk, comp, name, x0, x1, y0, y1, width):
    hw = f"{width} / 2"
    b = bk.box_sym(comp, name, x0, x1, y0, y1, width, look="pcb", material="fr4").body
    _corners(bk, comp, f"{name} sarkai", b, x0, x1, hw, "el_pcb_r")
    return b


def _ic(bk, comp, name, x0, x1, y0, y1, z0, z1):
    return bk.box(comp, name, x0, x1, y0, y1, z0, z1, look="plastic_black",
                  material="plastic").body


def _mlcc(bk, comp, name, x0, y0, y1, z0, z1, length="3.2 mm", term="0.5 mm"):
    """Chip capacitor along X: ceramic body between two plated terminations."""
    xa = f"{x0} + {term}"
    xb = f"{x0} + {length} - {term}"
    xe = f"{x0} + {length}"
    bk.box(comp, name, xa, xb, y0, y1, z0, z1, look="ceramic", material="glass")
    for i, (a, b) in enumerate(((x0, xa), (xb, xe))):
        bk.box(comp, f"{name} végelektróda {i + 1}", a, b, y0, y1, z0, z1,
               look="steel", material="steel")


def _arc(cx, cy, r, c, s_):
    """Point at (cx + r·c, cy + r·s) — c, s are numeric cos / sin literals with sign."""
    return (f"{_p(cx)} + {_p(r)} * ({c})", f"{_p(cy)} + {_p(r)} * ({s_})")


H = "0.707107"


# ─────────────────────────────────────────────────────────────────────────────
# Plazma NYÁK (P): STM32G474 + half-bridge + resonant inductor, CeraPlas pins soldered in
# ─────────────────────────────────────────────────────────────────────────────

def _plasma_board(bk, parent):
    comp = bk.component(parent, "Plazma NYÁK")
    x0, x1 = "pboard_x0", "pboard_x1"
    top, bot = "el_y_top", "el_pb_bot"
    board = _board(bk, comp, "NYÁK", x0, x1, bot, top, "pboard_w")

    # The CeraPlas HF pins come straight down through the liner floor and the board.
    for i, z in enumerate(("cp_pin_z", neg("cp_pin_z"))):
        _rod_y(bk, comp, f"Tüske furat {i + 1}", "cp_pin_x", f"{bot} - 0.1 mm",
               f"{top} + 0.1 mm", z, "el_pin_hole_r", op="cut", targets=[board])
        pad = _rod_y(bk, comp, f"Tüske pad {i + 1}", "cp_pin_x", top, f"{top} + 0.05 mm", z,
                     "el_pin_pad_r", look="gold", material="copper").body
        _rod_y(bk, comp, f"Tüske pad furat {i + 1}", "cp_pin_x", f"{top} - 0.1 mm",
               f"{top} + 0.2 mm", z, "el_pin_hole_r", op="cut", targets=[pad])

    # Underside, in drive order from the pins backward: half-bridge FETs, gate driver,
    # STM32G474 (HRTIM phase-locks the 82 kHz drive), resonant inductor. Kept within
    # |z| ≤ 8 so the insert's board ledges stay clear.
    def down(h):
        return f"{bot} - {h}"
    for i, (za, zb) in enumerate((("0.5 mm", "3.8 mm"), ("-3.8 mm", "-0.5 mm"))):
        _ic(bk, comp, f"FET {i + 1}", "el_fet_x0", "el_fet_x0 + 3.3 mm", down("1 mm"), bot,
            za, zb)
    _ic(bk, comp, "Gate driver", "el_drv_x0", "el_drv_x0 + 3 mm", down("0.9 mm"), bot,
        "-1.5 mm", "1.5 mm")
    _ic(bk, comp, "STM32G474", "el_mcu_x0", "el_mcu_x0 + 7 mm", down("0.55 mm"), bot,
        "-3.5 mm", "3.5 mm")
    ind = bk.box(comp, "Rezonáns tekercs", "el_ind_x0", "el_ind_x0 + 5.5 mm", down("3 mm"), bot,
                 "-2.65 mm", "2.65 mm", look="plastic_black", material="steel").body
    _corners(bk, comp, "Tekercs sarkai", ind, "el_ind_x0", "el_ind_x0 + 5.5 mm", "2.65 mm",
             "0.6 mm")
    for i, (za, zb) in enumerate((("5.6 mm", "7.2 mm"), ("-7.2 mm", "-5.6 mm"))):
        _mlcc(bk, comp, f"Híd kondenzátor {i + 1}", "el_drv_x0", down("1.6 mm"), bot, za, zb)
    # Top side, outside the liner's footprint: 12 V bus capacitors.
    for i, (za, zb) in enumerate((("6.8 mm", "8.4 mm"), ("-8.4 mm", "-6.8 mm"))):
        _mlcc(bk, comp, f"12 V kondenzátor {i + 1}", "el_mcu_x0", top, f"{top} + 1.6 mm", za, zb)

    # Short jumper flex to the bridge board (P side), on top.
    bk.box(comp, "Átkötő flex", f"{x1} - 0.8 mm", "bridge_x0 + 1.4 mm", top,
           f"{top} + el_fpc_t", "-3 mm", "3 mm", look="copper", material="plastic")
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# Ventilátor: Sunon UB3H3-700
# ─────────────────────────────────────────────────────────────────────────────

def _blower(bk, parent):
    comp = bk.component(parent, "Ventilátor")
    x0, x1 = "fan_x0", "fan_x0 + fan_len"
    y0, y1 = "fan_y0", "fan_y0 + fan_h"
    hw = "fan_w / 2"
    body = bk.box_sym(comp, "Ház", x0, x1, y0, y1, "fan_w", look="fan", material="plastic").body
    _corners(bk, comp, "Ház sarkai", body, x0, x1, hw, "1.5 mm")
    xc = f"{x0} + fan_len / 2 + 1 mm"           # inlet centred over the impeller
    _rod_y(bk, comp, "Beszívó", xc, f"{y1} - 0.4 mm", f"{y1} + 0.1 mm", "0 mm", "5 mm",
           op="cut", targets=[body])
    _rod_y(bk, comp, "Rotor agy", xc, f"{y1} - 0.4 mm", f"{y1} - 0.05 mm", "0 mm", "2.4 mm",
           look="plastic_black", material="plastic")
    # Outlet: rectangular mouth on the front face, toward the liner.
    bk.box_sym(comp, "Kifúvó", f"{x0} - 0.1 mm", f"{x0} + 0.6 mm", f"{y0} + 0.5 mm",
               f"{y1} - 0.5 mm", "6 mm", op="cut", targets=[body])
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# Vezérlő híd: ISO7741 + SN6507 + transformer, straddling B1
# ─────────────────────────────────────────────────────────────────────────────

def _bridge(bk, parent):
    comp = bk.component(parent, "Vezérlő híd")
    x0, x1 = "bridge_x0", "bridge_x1"
    top, bot = "el_y_top", "el_ai_bot"
    _board(bk, comp, "NYÁK", x0, x1, bot, top, "bridge_w")

    # ISO7741 (DW): pin rows parallel to B1, one on each side, barrier on B1's mid-plane.
    m = "el_b1_mid"
    bk.box(comp, "ISO7741", f"{m} - 3.75 mm", f"{m} + 3.75 mm", f"{top} + 0.1 mm", "el_iso_top",
           "-5.15 mm", "5.15 mm", look="plastic_black", material="plastic")
    for side, (a, b) in (("P", (f"{m} - 5.15 mm", f"{m} - 3.75 mm")),
                         ("A", (f"{m} + 3.75 mm", f"{m} + 5.15 mm"))):
        for k in range(8):
            zc = f"{-4.445 + 1.27 * k:.3f} mm"
            bk.box(comp, f"ISO7741 láb {side}{k + 1}", a, b, top, f"{top} + 0.25 mm",
                   f"{zc} - 0.21 mm", f"{zc} + 0.21 mm", look="steel", material="copper")
    # A side: SN6507 push-pull driver. P side: rectifier + 12 V output capacitor.
    _ic(bk, comp, "SN6507", f"{m} + 4.6 mm", f"{m} + 7.6 mm", top, f"{top} + 1.1 mm",
        "4.9 mm", "7.9 mm")
    _ic(bk, comp, "Egyenirányító", f"{x0} + 1.2 mm", f"{x0} + 2.9 mm", top, f"{top} + 0.9 mm",
        "5.4 mm", "6.65 mm")
    _mlcc(bk, comp, "12 V kimenet", f"{x0} + 1 mm", top, f"{top} + 1.6 mm", "-7.4 mm", "-5.8 mm")
    # Underside: the isolation transformer across B1 (primary A, secondary P).
    xf = bk.box(comp, "Leválasztó trafó", f"{m} - 6.5 mm", f"{m} + 6.5 mm",
                f"{bot} - el_xf_h", bot, "-4 mm", "4 mm",
                look="plastic_black", material="steel").body
    _corners(bk, comp, "Trafó sarkai", xf, f"{m} - 6.5 mm", f"{m} + 6.5 mm", "4 mm", "0.8 mm")
    # Jumper flex to the AI board (A side), underneath.
    bk.box(comp, "Átkötő flex", f"{x1} - 0.8 mm", "ai_x0 + 0.8 mm", f"{bot} - el_fpc_t", bot,
           "-3 mm", "3 mm", look="copper", material="plastic")
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# AI NYÁK (A): ESP32-S3-WROOM-1U, camera + display connectors, charger, camera flex + dome
# ─────────────────────────────────────────────────────────────────────────────

def _connector(bk, comp, name, x0, x1, half_w, slot_x0, slot_x1, slot_hw):
    top = "el_y_top"
    c = bk.box(comp, name, x0, x1, top, f"{top} + 1 mm", neg(half_w), half_w,
               look="plastic_white", material="plastic").body
    bk.box(comp, f"{name} rés", slot_x0, slot_x1, "el_conn_mid - 0.1 mm",
           "el_conn_mid + 0.1 mm", neg(slot_hw), slot_hw, op="cut", targets=[c])
    return c


def _camera_flex(bk, comp):
    """Camera flex: along the A tunnel floor from the nose cone slot, down behind B1, forward
    into the camera connector at the front of the AI board. One XY band, extruded ±el_cf_w/2."""
    t = "el_fpc_t"
    x0 = "el_cf_x0"
    y0 = "el_cf_y0"
    y1 = f"{y0} + {t}"
    xb = "el_cf_xb"
    r1, r2 = "el_cf_r1", "el_cf_r2"
    ri1, ri2 = f"({r1} - {t})", f"({r2} - {t})"
    c1y = f"{y1} - {r1}"
    xv0 = f"{xb} + {ri1}"
    xv1 = f"{xb} + {r1}"
    yb0 = f"el_conn_mid - {t} / 2"
    yb1 = f"el_conn_mid + {t} / 2"
    c2x = f"{xv0} + {r2}"
    c2y = f"{yb0} + {r2}"
    xt = "el_cc_x0 + 2.2 mm"
    band = [
        (x0, y0),
        (xb, y0),
        ("spline", [_arc(xb, c1y, ri1, H, H), (xv0, c1y)]),
        (xv0, c2y),
        ("spline", [_arc(c2x, c2y, r2, f"-{H}", f"-{H}"), (c2x, yb0)]),
        (xt, yb0),
        (xt, yb1),
        (c2x, yb1),
        ("spline", [_arc(c2x, c2y, ri2, f"-{H}", f"-{H}"), (xv1, c2y)]),
        (xv1, c1y),
        ("spline", [_arc(xb, c1y, r1, H, H), (xb, y1)]),
        (x0, y1),
    ]
    bk.extrude_sym(comp, "Kamera flex", band, "el_cf_w", look="copper", material="plastic")
    # Button: metal dome on the same flex, under the button stem.
    top = y1
    dome = [("btn_x", top), ("btn_x + 2 mm", top),
            ("spline", [("btn_x + 1.2 mm", f"{top} + 0.27 mm"), ("btn_x", f"{top} + 0.35 mm")])]
    bk.revolve(comp, "Gomb kupola", dome, axis=2, look="steel", material="steel")


def _ai_board(bk, parent):
    comp = bk.component(parent, "AI NYÁK")
    x0, x1 = "ai_x0", "ai_x1"
    top, bot = "el_y_top", "el_ai_bot"
    board = _board(bk, comp, "NYÁK", x0, x1, bot, top, "ai_w")
    # Corner notch: the antenna coax comes up from the module side here.
    bk.box(comp, "Koax kivágás", "el_cx_xa - 0.8 mm", f"{x1} + 0.1 mm", f"{bot} - 0.1 mm",
           f"{top} + 0.1 mm", "el_ufl_z - 0.9 mm", "ai_w / 2 + 0.1 mm", op="cut", targets=[board])

    # ESP32-S3-WROOM-1U mounted upside down on the underside: the top side stays free for the
    # two FPC connectors wherever the display lands. U.FL + mated plug at the module's end.
    e0, e1 = "el_esp_x0", "el_esp_x1"
    eb = "el_esp_pcb"
    bk.box_sym(comp, "ESP32-S3 modul", e0, e1, eb, bot, "18 mm", look="pcb", material="fr4")
    sh = bk.box_sym(comp, "ESP32-S3 árnyékolás", f"{e0} + 0.5 mm", f"{e0} + 16 mm",
                    f"{bot} - 3.2 mm", eb, "16.6 mm", look="shield", material="steel").body
    _corners(bk, comp, "Árnyékolás sarkai", sh, f"{e0} + 0.5 mm", f"{e0} + 16 mm", "8.3 mm",
             "0.4 mm")
    bk.box(comp, "U.FL aljzat", f"{e1} - 2.9 mm", f"{e1} - 0.3 mm", f"{eb} - 0.9 mm", eb,
           "el_ufl_z - 1.5 mm", "el_ufl_z + 1.5 mm", look="gold", material="copper")
    bk.box(comp, "U.FL dugó", f"{e1} - 2.9 mm", f"{e1} - 0.3 mm", f"{eb} - 2.1 mm",
           f"{eb} - 0.9 mm", "el_ufl_z - 1.3 mm", "el_ufl_z + 1.3 mm",
           look="steel", material="steel")

    # FPC connectors on top: camera at the front (flex enters from −X), display under the
    # panel's back end (+X).
    _connector(bk, comp, "Kamera csatlakozó", "el_cc_x0", "el_cc_x0 + 3 mm", "4.4 mm",
               "el_cc_x0 - 0.1 mm", "el_cc_x0 + 2.4 mm", "4.1 mm")
    _connector(bk, comp, "Kijelző csatlakozó", "el_dc_x0", "el_dc_x0 + 3 mm", "6.4 mm",
               "el_dc_x0 + 0.6 mm", "el_dc_x0 + 3.1 mm", "6.1 mm")

    # Power path under the board behind the module: 1S charger, protection, 3.3 V buck coil.
    px = f"{e1} + 1 mm"
    _ic(bk, comp, "Töltő IC", px, f"{px} + 2.5 mm", f"{bot} - 0.8 mm", bot, "-9.4 mm", "-6.9 mm")
    _ic(bk, comp, "Akku védelem", px, f"{px} + 1.6 mm", f"{bot} - 0.75 mm", bot,
        "-5.8 mm", "-4.2 mm")
    ind = bk.box(comp, "3,3 V tekercs", px, f"{px} + 2.5 mm", f"{bot} - 1.2 mm", bot,
                 "-3.3 mm", "-1.3 mm", look="plastic_black", material="steel").body
    _corners(bk, comp, "Tekercs sarkai", ind, px, f"{px} + 2.5 mm", "-1.3 mm", "0.3 mm")

    _camera_flex(bk, comp)
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# AMOLED 1,91" + touch, FPC to the AI board
# ─────────────────────────────────────────────────────────────────────────────

def _amoled(bk, parent):
    comp = bk.component(parent, 'AMOLED 1,91"')
    x0, x1 = "oled_x0", "oled_x1"
    y0, y1 = "el_pan_y0", "el_pan_y1"
    gk = dict(look="glass_black", material="glass")
    xs = f"{x1} - el_shelf"
    # TFT glass + encapsulation + polariser + touch sensor as one stack; the driver shelf at
    # the back is the bare TFT glass with the RM67162 on it.
    stack = bk.box_sym(comp, "Panel + érintőréteg", x0, xs, y0, y1, "oled_w", **gk).body
    bk.box_sym(comp, "Meghajtó perem", xs, x1, y0, "el_shelf_y", "oled_w", **gk)
    bk.box_sym(comp, "RM67162", f"{xs} + 0.4 mm", f"{xs} + 2 mm", "el_shelf_y",
               "el_shelf_y + 0.25 mm", "12 mm", look="plastic_black", material="plastic")
    ax0 = "oled_x0 + oled_act_x"
    ax1 = f"{ax0} + oled_act_len"
    bk.box_sym(comp, "Aktív terület zseb", ax0, ax1, f"{y1} - 0.05 mm", f"{y1} + 0.1 mm",
               "oled_act_w", op="cut", targets=[stack])
    bk.box_sym(comp, "AMOLED aktív terület", ax0, ax1, f"{y1} - 0.05 mm", y1, "oled_act_w",
               look="oled_on", material="glass")

    # FPC: bonded on the shelf, round the back edge, down through the windows into the AI
    # bay, round once more and forward into the display connector.
    t = "el_fpc_t"
    ys0 = "el_shelf_y"
    ys1 = f"{ys0} + {t}"
    r1, r2 = "el_df_r1", "el_df_r2"
    ri1, ri2 = f"({r1} - {t})", f"({r2} - {t})"
    xo = "el_df_xo"
    xi = f"{xo} - {t}"
    c1y = f"{ys1} - {r1}"
    yb0 = f"el_conn_mid - {t} / 2"
    yb1 = f"el_conn_mid + {t} / 2"
    c2x = f"{xo} - {r2}"
    c2y = f"{yb0} + {r2}"
    xt = "el_dc_x0 + 0.9 mm"
    band = [
        (f"{x1} - 1.4 mm", ys0),
        (x1, ys0),
        ("spline", [_arc(x1, c1y, ri1, H, H), (xi, c1y)]),
        (xi, c2y),
        ("spline", [_arc(c2x, c2y, ri2, H, f"-{H}"), (c2x, yb1)]),
        (xt, yb1),
        (xt, yb0),
        (c2x, yb0),
        ("spline", [_arc(c2x, c2y, r2, H, f"-{H}"), (xo, c2y)]),
        (xo, c1y),
        ("spline", [_arc(x1, c1y, r1, H, H), (x1, ys1)]),
        (f"{x1} - 1.4 mm", ys1),
    ]
    bk.extrude_sym(comp, "Kijelző FPC", band, "oled_fpc_w", look="copper", material="plastic")
    # FT3168 touch controller on the FPC's lower leg.
    bk.box_sym(comp, "FT3168", f"{c2x} - 2.9 mm", f"{c2x} - 0.9 mm", yb1, f"{yb1} + 0.6 mm",
               "3 mm", look="plastic_black", material="plastic")
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# Akku 21700 + contacts
# ─────────────────────────────────────────────────────────────────────────────

def _battery(bk, parent):
    comp = bk.component(parent, "Akku 21700")
    yc = "bat_y"
    R = "el_bat_r"
    wt = "el_bat_wrap"
    xa = "bat_x0 + el_bat_cap_h"           # front shoulder
    xb = "bat_x1"                          # negative end
    xf = f"{xa} + {wt}"
    xr = f"{xb} - {wt}"
    lip = f"{R} - el_bat_lip"

    wrap = _rod_x(bk, comp, "Zsugorcső", xa, xb, yc, "0 mm", R,
                  look="battery_wrap", material="plastic").body
    _rod_x(bk, comp, "Zsugorcső belső", xf, xr, yc, "0 mm", f"{R} - {wt}",
           op="cut", targets=[wrap])
    _rod_x(bk, comp, "Zsugorcső perem eleje", f"{xa} - 0.1 mm", f"{xf} + 0.01 mm", yc, "0 mm",
           lip, op="cut", targets=[wrap])
    _rod_x(bk, comp, "Zsugorcső perem vége", f"{xr} - 0.01 mm", f"{xb} + 0.1 mm", yc, "0 mm",
           lip, op="cut", targets=[wrap])
    _rod_x(bk, comp, "Cella", xf, xr, yc, "0 mm", f"{R} - {wt}", look="steel",
           material="battery")
    _rod_x(bk, comp, "Pozitív sapka", "bat_x0", xf, yc, "0 mm", "el_bat_cap_r",
           look="steel", material="steel")
    _tube_off(bk, comp, "Szigetelőgyűrű", xa, xf, yc, lip, "el_bat_cap_r + 0.5 mm",
              look="plastic_white", material="plastic")

    sk = dict(look="steel", material="steel")
    # + : spring and plate on B2, nickel strip through B2's window to the AI board underside.
    px0 = "b2_x0 + b_t + 0.1 mm"
    px1 = f"{px0} + 0.2 mm"
    _tube_off(bk, comp, "Pozitív rugó", px1, "bat_x0", yc, "el_spring_r", "el_spring_r - 0.4 mm",
              **sk)
    plate = _rod_x(bk, comp, "Pozitív lemez", px0, px1, yc, "0 mm", "el_plate_r", **sk).body
    j = dict(op="join", targets=[plate])
    hw = "el_tab_w / 2"
    tt = "el_tab_t"
    yp = "el_ptab_y"
    xd = "ai_x1 + 0.2 mm"
    bk.box(comp, "Pozitív szalag le", px0, f"{px0} + {tt}", yp, f"{yc} - 1.5 mm", neg(hw), hw, **j)
    bk.box(comp, "Pozitív szalag B2", xd, f"{px0} + {tt}", yp, f"{yp} + {tt}", neg(hw), hw, **j)
    bk.box(comp, "Pozitív szalag AI", xd, f"{xd} + {tt}", f"el_ai_bot - {tt}", f"{yp} + {tt}",
           neg(hw), hw, **j)
    bk.box(comp, "Pozitív szalag forrasztás", "ai_x1 - 2.1 mm", f"{xd} + {tt}",
           f"el_ai_bot - {tt}", "el_ai_bot", neg(hw), hw, **j)

    # − : spring and plate on B3; tab through B3's hole into the cap, down to the dock board.
    mx0 = "el_mplate_x0"
    _tube_off(bk, comp, "Negatív rugó", xr, mx0, yc, "el_spring_r", "el_spring_r - 0.4 mm", **sk)
    mp = _rod_x(bk, comp, "Negatív lemez", mx0, "b3_x0", yc, "0 mm", "el_plate_r", **sk).body
    j = dict(op="join", targets=[mp])
    xc1 = "b3_x0 + b_t + 0.35 mm"
    xc2 = "el_dk_x0 + 0.25 mm"
    ym = "-4.15 mm"
    bk.box(comp, "Negatív szalag B3", f"{mx0} + 0.05 mm", f"{xc1} + {tt}", f"{yc} - {tt}", yc,
           "-1 mm", "1 mm", **j)
    bk.box(comp, "Negatív szalag le", xc1, f"{xc1} + {tt}", ym, yc, "-1 mm", "1 mm", **j)
    bk.box(comp, "Negatív szalag kupak", xc1, f"{xc2} + {tt}", ym, f"{ym} + {tt}", "-1 mm",
           "1 mm", **j)
    bk.box(comp, "Negatív szalag dokk", xc2, f"{xc2} + {tt}", "el_dk_y1", f"{ym} + {tt}",
           "-1 mm", "1 mm", **j)
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# Dock: board in the cap, flush gold targets, magnets, status LED, flex to the AI board
# ─────────────────────────────────────────────────────────────────────────────

def _dock_board(bk, parent):
    comp = bk.component(parent, "Dokk NYÁK")
    x0, x1 = "el_dk_x0", "el_dk_x1"
    y0, y1 = "el_dk_y0", "el_dk_y1"
    board = _board(bk, comp, "NYÁK", x0, x1, y0, y1, "el_dk_w")
    for i, xm in enumerate(("dock_xc - mag_dx", "dock_xc + mag_dx")):
        _rod_y(bk, comp, f"Mágnes furat {i + 1}", xm, f"{y0} - 0.1 mm", f"{y1} + 0.1 mm",
               "0 mm", "mag_d / 2 + 0.1 mm", op="cut", targets=[board])
    # Status LED in the middle: the frosted PC cap is its light guide.
    bk.box_sym(comp, "Státusz LED", "dock_xc - 0.8 mm", "dock_xc + 0.8 mm", y1,
               f"{y1} + 0.6 mm", "0.8 mm", look="led405", material="plastic")
    _ic(bk, comp, "ESD védelem", "dock_xc - 0.5 mm", "dock_xc + 0.5 mm", y1, f"{y1} + 0.55 mm",
        "4.6 mm", "6.2 mm")

    # Flex: up from the board, forward through the cap spigot and B3's hole, out along the
    # cell's side (z < 0), in again in front of the cell, through B2's window, down onto the
    # AI board. Thin boxes joined into one body; the width (el_dfx_w) turns with the flex.
    t = "el_fpc_t"
    hw = "el_dfx_w / 2"
    z0, z1 = "el_dfx_z", f"el_dfx_z + {t}"          # thin in Z (flat on the cell side)
    zw0, zw1 = f"el_dfx_z - {hw}", f"el_dfx_z + {hw}"   # width in Z (vertical runs)
    ya, yb = f"bat_y - {hw}", f"bat_y + {hw}"
    xd = "el_dfx_xd"
    yd = "el_dfx_yd"
    xu = "el_dk_x0 + 1 mm"
    k = dict(look="copper", material="plastic")
    flex = bk.box(comp, "Dokk flex fel", xu, f"{xu} + {t}", y1, f"{yd} + {t}", zw0, zw1,
                  **k).body
    j = dict(op="join", targets=[flex])
    bk.box(comp, "Dokk flex kupak", xd, f"{xu} + {t}", yd, f"{yd} + {t}", zw0, zw1, **j)
    # B3's flex hole (Ø8) is on the pen axis: the flex crosses it at y = 0.
    bk.box(comp, "Dokk flex csap", xd, f"{xd} + {t}", yd, hw, zw0, zw1, **j)
    bk.box(comp, "Dokk flex B3", "el_dfx_xr", f"{xd} + {t}", neg(hw), hw, z0, z1, **j)
    side0, side1 = f"el_dfx_side - {t}", "el_dfx_side"
    bk.box(comp, "Dokk flex hátul", "el_dfx_xr", f"el_dfx_xr + {t}", ya, hw, side0, z1, **j)
    bk.box(comp, "Dokk flex a cella mellett", "el_dfx_xf", f"el_dfx_xr + {t}", ya, yb,
           side0, side1, **j)
    bk.box(comp, "Dokk flex elöl", "el_dfx_xf", f"el_dfx_xf + {t}", ya, yb, side0, z1, **j)
    xa = "ai_x1 - 1.1 mm"
    bk.box(comp, "Dokk flex B2", xa, f"el_dfx_xf + {t}", ya, yb, z0, z1, **j)
    bk.box(comp, "Dokk flex le", xa, f"{xa} + {t}", "el_y_top", yb, zw0, zw1, **j)
    return comp


def _dock_contacts(bk, parent):
    comp = bk.component(parent, "Dokk érintkezők")
    n = 4
    for i in range(n):
        zc = f"({i} - (dock_pins - 1) / 2) * dock_pitch"
        # Gold-plated brass target, flush with the dock flat, soldered into the board.
        _rod_y(bk, comp, f"Érintkező {i + 1}", "dock_xc", "-(bot_y)", "el_dk_y0", zc,
               "dock_pad_d / 2", look="gold", material="copper")
    return comp


def _magnets(bk, parent):
    comp = bk.component(parent, "Mágnesek")
    for i, xm in enumerate(("dock_xc - mag_dx", "dock_xc + mag_dx")):
        _rod_y(bk, comp, f"Mágnes {i + 1}", xm, "-(bot_y) + mag_skin",
               "-(bot_y) + mag_skin + mag_t", "0 mm", "mag_d / 2", look="steel",
               material="steel")
    return comp


# ─────────────────────────────────────────────────────────────────────────────
# BLE antenna (Taoglas FXP75 in the cap) + Ø0.81 coax from the U.FL
# ─────────────────────────────────────────────────────────────────────────────

def _antenna(bk, parent):
    comp = bk.component(parent, "BLE antenna")
    ax0, ax1 = "el_ant_x0", "el_ant_x0 + 4.1 mm"
    bk.box(comp, "Flex antenna", ax0, ax1, "el_ant_y1 - 0.24 mm", "el_ant_y1", "el_ant_z0",
           "el_ant_z0 + 5.9 mm", look="copper", material="plastic")

    r = "el_cx_r"
    kw = dict(look="plastic_black", material="copper")
    yu, zu = "el_cx_y", "el_ufl_z"
    xa = "el_cx_xa"
    zs = "el_cx_zs"
    yc = "bat_y"
    xn = "el_cx_xn"
    zh = "el_cx_zh"
    yd = "el_cx_yd"
    xe = "dock_xc - 0.6 mm"
    # Legs overlap the next leg by 0.6 r past its axis: equal-radius cylinders meeting
    # exactly tangent make a degenerate boolean.
    e = f"0.6 * {r}"
    rz = f"0.94 * {r}"          # Z legs (spline circles) a hair thinner: no tangent faces
    coax = _rod_x(bk, comp, "Koax", "el_esp_x1 - 0.3 mm", f"{xa} + {e}", yu, zu, r, **kw).body
    j = dict(op="join", targets=[coax])
    _rod_y(bk, comp, "Koax fel", xa, f"{yu} - {e}", f"{yc} + {e}", zu, r, **j)
    _rod_z(bk, comp, "Koax oldalra", xa, yc, f"{zu} - {e}", f"{zs} + {e}", rz, **j)
    # Along the cell, through the B2 and B3 coax holes, past B3 to the slot in the cap spigot,
    # in through the slot into the cap cavity, down, back to the antenna feed.
    _rod_x(bk, comp, "Koax a cella mellett", f"{xa} - {e}", f"{xn} + {e}", yc, zs, r, **j)
    _rod_z(bk, comp, "Koax be", xn, yc, f"{zh} - {e}", f"{zs} + {e}", rz, **j)
    _rod_y(bk, comp, "Koax le", xn, f"{yd} - {e}", f"{yc} + {e}", zh, r, **j)
    _rod_x(bk, comp, "Koax a kupakban", f"{xn} - {e}", f"{xe} + {e}", yd, zh, r, **j)
    _rod_y(bk, comp, "Koax az antennához", xe, f"{yd} - {e}", "el_ant_y1 - 0.24 mm", zh, r, **j)
    return comp


def build_shared(bk, parent):
    return [
        _plasma_board(bk, parent),
        _blower(bk, parent),
        _bridge(bk, parent),
        _ai_board(bk, parent),
        _amoled(bk, parent),
        _battery(bk, parent),
        _dock_board(bk, parent),
        _dock_contacts(bk, parent),
        _magnets(bk, parent),
        _antenna(bk, parent),
    ]
