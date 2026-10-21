"""PlasmaPen Nexus — every user parameter of the Fusion model.

Coordinate frame (every component, local space):
    X = pen axis. x = 0 is the nozzle face, +X runs toward the back (USB-C end).
    Y = up. The flat facet (display, button) and the camera sit on the +Y side (top, θ = 0).
    Angles around X are measured from +Y toward +Z.
    Z = side. The engineering cutaway removes everything at z > 0.
    The plasma plume and the petri dish live at x < 0.

All lengths are mm, all angles deg. Expressions use Fusion syntax and may only reference
parameters defined ABOVE them in this list. Every literal length carries "mm".
Group headers are only for the order of the Fusion parameter table.
"""

# (name, expression, unit, comment). unit "" = unitless count.
PARAMS = [
    # ── Unibody (egy darab eloxált alu) ───────────────────────────────────────
    ("body_od", "29 mm", "mm", "Test legnagyobb átmérője"),
    ("body_r", "body_od / 2", "mm", "= külső sugár"),
    ("bore_r", "11.3 mm", "mm", "Belső furat sugara (akku + hézag)"),
    ("body_wall", "body_r - bore_r", "mm", "= falvastagság a hengeres részen"),
    ("front_wall", "0.75 mm", "mm", "Alu fal az elülső élnél"),
    ("flat_y", "12.2 mm", "mm", "Lapos oldal síkja (tengelytől)"),
    ("facet_w", "2 * sqrt(body_r ^ 2 - flat_y ^ 2)", "mm", "= lapos oldal szélessége"),
    ("edge_r", "1.2 mm", "mm", "Külső élek lekerekítése"),
    ("back_r", "4.5 mm", "mm", "Hátsó él lekerekítése"),
    ("cap_len", "7 mm", "mm", "Hátsó kupak vastagság (USB-C ebben)"),
    ("cap_spigot", "3 mm", "mm", "Kupak csapja a testben"),

    # ── PEEK orr + bélés — szigeteli a 15 kV-os piezót ────────────────────────
    ("tip_od", "22.4 mm", "mm", "Orr átmérő"),
    ("tip_r", "tip_od / 2", "mm", "= orr sugár"),
    ("nose_len", "6 mm", "mm", "Látható fekete PEEK orr hossza"),
    ("cone_len", "96 mm", "mm", "Elülső ív hossza (orr → legnagyobb átmérő)"),
    ("taper_x1", "nose_len + cone_len", "mm", "= itt éri el a legnagyobb átmérőt"),
    ("swell_x1", "taper_x1 + 52 mm", "mm", "Eddig tart a legnagyobb átmérő"),
    ("back_od", "2 * (bore_r + 2 mm)", "mm", "Átmérő a hátsó végén (orsóforma)"),
    ("nozzle_d", "5 mm", "mm", "Fúvóka furat"),
    ("nozzle_len", "14 mm", "mm", "Egyenes fúvóka furat hossza"),
    ("collar_r", "nozzle_d / 2 + 1.5 mm", "mm", "PEEK gallér a fúvóka körül"),
    ("win_ro", "tip_r - 1 mm", "mm", "Üveggyűrű külső sugara"),
    ("win_t", "1 mm", "mm", "Üveggyűrű vastagság"),
    ("ring_r", "6.6 mm", "mm", "LED-ek + kamera köre az orron"),
    ("led_pairs", "3", "", "405 nm + 660 nm LED párok"),
    ("led_d", "1.4 mm", "mm", "LED lencse átmérő"),
    ("led_h", "0.8 mm", "mm", "LED magasság"),
    ("cam_d", "4 mm", "mm", "Kamera lencse átmérő"),
    ("cam_mod", "6 mm", "mm", "OV5640 modul oldalhossz"),
    ("cam_depth", "8 mm", "mm", "Kamera modul mélység"),
    ("liner_ri", "7 mm", "mm", "PEEK bélés belső sugara"),

    # ── TDK CeraPlas F elem (csupasz piezo rúd, 72 × 6 × 2,8 mm) ──────────────
    ("cp_len", "72 mm", "mm", "CeraPlas F hossz"),
    ("cp_w", "6 mm", "mm", "CeraPlas F szélesség (Z)"),
    ("cp_h", "2.8 mm", "mm", "CeraPlas F vastagság (Y)"),
    ("cp_x0", "nozzle_len + 4 mm", "mm", "Piezo rúd csúcsa"),
    ("funnel_x1", "nozzle_len + 6 mm", "mm", "Tölcsér vége (itt éri el a bélést)"),
    ("head_len", "cp_x0 + cp_len + 3 mm", "mm", "= PEEK bélés vége"),
    ("chk_bore", "liner_ri - sqrt((cp_w / 2) ^ 2 + (cp_h / 2) ^ 2)", "mm",
     "ELLENŐRZÉS: piezo sarka ↔ bélés, ≥ 0 kell"),

    # ── Levegő (mikroventi + szellőzők) ───────────────────────────────────────
    ("fan_d", "20 mm", "mm", "Mikroventi átmérő"),
    ("fan_len", "8 mm", "mm", "Mikroventi hossz"),
    ("fan_x0", "head_len + 2 mm", "mm", "Ventilátor eleje"),
    ("vent_count", "12", "", "Szellőző rések száma"),
    ("vent_w", "1.6 mm", "mm", "Rés szélesség"),
    ("vent_len", "10 mm", "mm", "Rés hossz"),
    ("vent_x0", "fan_x0 - 1 mm", "mm", "Rések eleje"),

    # ── Elektronika ───────────────────────────────────────────────────────────
    ("pcb_x0", "fan_x0 + fan_len + 4 mm", "mm", "Fő NYÁK eleje"),
    ("pcb_len", "48 mm", "mm", "Fő NYÁK hossz"),
    ("pcb_w", "17 mm", "mm", "Fő NYÁK szélesség"),
    ("pcb_t", "1.6 mm", "mm", "NYÁK vastagság"),
    ("pcb_y", "2 mm", "mm", "Fő NYÁK alja (tengelytől fel)"),
    ("drv_y", "4 mm", "mm", "Driver NYÁK teteje (tengelytől le)"),
    ("drv_w", "16 mm", "mm", "Driver NYÁK szélesség"),
    ("esp_x0", "pcb_x0 + 24 mm", "mm", "ESP32-S3 modul eleje"),
    ("esp_len", "15.4 mm", "mm", "ESP32-S3-MINI-1U hossz"),
    ("esp_w", "15.4 mm", "mm", "ESP32-S3-MINI-1U szélesség"),
    ("esp_h", "2.4 mm", "mm", "ESP32-S3-MINI-1U magasság"),
    ("btn_x", "pcb_x0 + 6 mm", "mm", "Gomb közepe"),
    ("btn_d", "7 mm", "mm", "Gomb átmérő"),
    ("btn_proud", "0.4 mm", "mm", "Gomb kiemelkedése a lapos oldalból"),
    ("glass_t", "0.55 mm", "mm", "Fedőüveg vastagság"),
    ("oled_len", "30.94 mm", "mm", "1,1\" AMOLED (126×294) panel hossz"),
    ("oled_w", "12.96 mm", "mm", "1,1\" AMOLED panel szélesség"),
    ("oled_t", "0.95 mm", "mm", "AMOLED panel vastagság (üveg + polarizátor)"),
    ("oled_act_len", "25.578 mm", "mm", "Aktív terület hossz"),
    ("oled_act_w", "10.962 mm", "mm", "Aktív terület szélesség"),
    ("oled_win_len", "oled_len + 1.6 mm", "mm", "Üvegablak hossz"),
    ("oled_win_w", "oled_w + 0.6 mm", "mm", "Üvegablak szélesség"),
    ("win_x0", "btn_x + btn_d / 2 + 4 mm", "mm", "Üvegablak eleje"),
    ("win_x1", "win_x0 + oled_win_len", "mm", "= üvegablak vége"),
    ("oled_x0", "win_x0 + (oled_win_len - oled_len) / 2", "mm", "= panel eleje"),
    ("oled_y", "flat_y - glass_t - oled_t", "mm", "= panel alja (tengelytől)"),

    # ── Akku + töltés ─────────────────────────────────────────────────────────
    ("bat_d", "21.4 mm", "mm", "21700 cella átmérő"),
    ("bat_len", "70.3 mm", "mm", "21700 cella hossz"),
    ("bat_x0", "pcb_x0 + pcb_len + 4 mm", "mm", "Akku eleje"),
    ("bms_d", "20 mm", "mm", "BMS + USB-C NYÁK átmérő"),
    ("bms_x0", "bat_x0 + bat_len + 1.5 mm", "mm", "BMS NYÁK eleje"),
    ("usb_w", "8.94 mm", "mm", "USB-C aljzat szélesség"),
    ("usb_h", "3.26 mm", "mm", "USB-C aljzat magasság"),
    ("usb_len", "7.35 mm", "mm", "USB-C aljzat hossz"),
    ("pen_len", "bms_x0 + pcb_t + usb_len + 0.3 mm", "mm", "= teljes hossz"),
    ("body_end", "pen_len - cap_len", "mm", "= unibody hátsó vége (itt kezdődik a kupak)"),

    # ── Működés (render jelenet) ──────────────────────────────────────────────
    ("standoff", "10 mm", "mm", "Fúvóka ↔ felület távolság"),
    ("plume_r", "3.2 mm", "mm", "Plazmaláng legnagyobb sugara"),
    ("spot_d", "16 mm", "mm", "Megvilágított folt a lemezen"),
    ("dish_d", "90 mm", "mm", "Petri-csésze átmérő"),
    ("dish_h", "14 mm", "mm", "Petri-csésze magasság"),
    ("dish_wall", "1 mm", "mm", "Petri-csésze fal"),
    ("agar_t", "6 mm", "mm", "Agar réteg"),
]


def names():
    return [p[0] for p in PARAMS]
