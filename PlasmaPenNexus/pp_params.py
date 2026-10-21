"""PlasmaPen Nexus — every user parameter of the Fusion model. REVISION 4.

Coordinate frame (every component, local space):
    X = pen axis. x = 0 is the nozzle face, +X runs toward the back (end cap).
    Y = up. The display flat sits on top (+Y), the dock flat at the bottom (−Y).
    Angles around X are measured from +Y toward +Z.
    Z = side. The engineering cutaway removes everything at z > 0.
    The plasma plume and the petri dish live at x < 0.

All lengths are mm, all angles deg. Expressions use Fusion syntax and may only reference
parameters defined ABOVE them in this list. Every literal length carries "mm".
Group headers are only for the order of the Fusion parameter table. BRIEF.md "REVISION 4"
explains every number; the chk_* rows at the end must all stay ≥ 0.
"""

# (name, expression, unit, comment). unit "" = unitless count.
PARAMS = [
    # ── Kijelző: 1,91" érintős AMOLED (RM67162, 240×536, FT3168 touch) ────────
    ("oled_len", "51.32 mm", "mm", "AMOLED panel hossz (X)"),
    ("oled_w", "22.4 mm", "mm", "AMOLED panel szélesség (Z)"),
    ("oled_t", "1.25 mm", "mm", "Panel + érintőréteg vastagság"),
    ("oled_act_len", "44.22 mm", "mm", "Aktív terület hossz"),
    ("oled_act_w", "19.8 mm", "mm", "Aktív terület szélesség"),
    ("oled_act_x", "1.55 mm", "mm", "Aktív terület eleje a panel elejétől (hátul a meghajtó)"),
    ("oled_fpc_w", "12 mm", "mm", "Panel FPC szélesség (hátul lép ki)"),
    ("oled_fpc_bend", "0.6 mm", "mm", "Hely az FPC hajlításának a panel hátsó éle mögött"),
    ("glass_t", "0.7 mm", "mm", "Fedőüveg vastagság (alumínoszilikát)"),
    ("glass_border", "1 mm", "mm", "Üveg túlnyúlása a panel körül"),
    ("glass_len", "oled_len + 2 * glass_border", "mm", "= fedőüveg hossz"),
    ("glass_w", "oled_w + 2 * glass_border", "mm", "= fedőüveg szélesség"),
    ("glass_r", "2.5 mm", "mm", "Fedőüveg sarok sugár"),
    ("glass_c", "0.1 mm", "mm", "Fedőüveg ↔ zseb hézag"),
    ("glass_ch", "0.15 mm", "mm", "Fedőüveg élletörés"),

    # ── Keresztmetszet: alu ház ───────────────────────────────────────────────
    ("body_od", "36 mm", "mm", "Ház legnagyobb átmérője (a legvastagabb pontban)"),
    ("body_r", "body_od / 2", "mm", "= legnagyobb sugár"),
    ("body_r0", "body_r - 0.8 mm", "mm", "Ház sugara elöl, az orrkúp illesztésénél"),
    ("body_rt", "body_r - 0.5 mm", "mm", "Ház sugara hátul, a kupak illesztésénél"),
    ("shell_wall", "1.2 mm", "mm", "Min. alu falvastagság"),
    ("bore_r", "body_r0 - shell_wall", "mm", "= ház belső furat sugara (extrudált, állandó)"),
    ("top_land", "1 mm", "mm", "Alu perem az üveg mellett a lapos oldalon"),
    ("top_ch", "0.6 mm", "mm", "Felső lapos oldal élletörése"),
    ("bot_ch", "0.6 mm", "mm", "Alsó (dokk) lapos oldal élletörése"),
    ("joint_ch", "0.3 mm", "mm", "Élletörés az illesztéseken (orrkúp | ház | kupak)"),
    ("rail_w", "2 mm", "mm", "Vezetőhorony szélesség a furatban (z = ±bore_r)"),
    ("rail_d", "0.6 mm", "mm", "Vezetőhorony mélység"),

    # ── Betét (PEI) keresztmetszet ────────────────────────────────────────────
    ("sled_c", "0.25 mm", "mm", "Betét ↔ furat hézag"),
    ("sled_wall", "1 mm", "mm", "Betét falvastagság (szigetelés)"),
    ("sled_r", "bore_r - sled_c", "mm", "= betét külső sugara"),
    ("sled_ri", "sled_r - sled_wall", "mm", "= betét belső sugara"),
    ("rib_w", "rail_w - 0.3 mm", "mm", "= betét csúszóborda szélesség"),
    ("rib_h", "rail_d - 0.15 mm", "mm", "= csúszóborda magassága a furat fölött"),
    ("b_t", "1 mm", "mm", "Válaszfalak vastagsága (B0 … B3)"),

    # ── Orrkúp (PEEK) + nagyfeszültség ────────────────────────────────────────
    ("hv_clear", "20 mm", "mm", "TDK: semmi vezető 20 mm-en belül a piezo kimenetétől"),
    ("hv_clear_edge", "30 mm", "mm", "TDK: éles vezető élre 30 mm"),
    ("nozzle_d", "5 mm", "mm", "Fúvóka furat"),
    ("nozzle_len", "9.5 mm", "mm", "Fúvóka furat hossz (homloktól a bélésig)"),
    ("tip_r0", "4.75 mm", "mm", "Csőr sugara a homloklapon"),
    ("face_x0", "26 mm", "mm", "Üveggyűrűs letörés eleje (csőr töve)"),
    ("face_r0", "8 mm", "mm", "Csőr sugara a letörésnél"),
    ("face_len", "5 mm", "mm", "Elülső letörés (üveggyűrű) hossza"),
    ("face_x1", "face_x0 + face_len", "mm", "= letörés vége"),
    ("nose_r1", "body_r0 - 0.25 mm", "mm", "= letörés külső sugara (gallér eleje)"),
    ("face_k", "(nose_r1 - face_r0) / face_len", "", "= letörés meredeksége (dr/dx)"),
    ("win_t", "1 mm", "mm", "Üveggyűrű vastagság (a felületre merőlegesen)"),
    ("win_tx", "win_t * sqrt(1 + face_k ^ 2) / face_k", "mm", "= üveggyűrű vastagsága X irányban"),
    ("win_r0", "face_r0 + 0.4 mm", "mm", "Üveggyűrű belső sugara"),
    ("win_r1", "nose_r1 - 1.6 mm", "mm", "Üveggyűrű külső sugara (a váll íve előtt)"),
    ("nose_split", "38 mm", "mm", "Orrkúp | ház illesztés (az orrkúp hátsó homloka)"),
    ("nose_gap", "0.4 mm", "mm", "Árnyékrés az illesztésen = levegő beszívás"),
    ("nose_spigot", "3 mm", "mm", "Orrkúp csapja a ház furatában (az illesztés mögött)"),
    ("body_x0", "nose_split + nose_gap", "mm", "= alu ház eleje"),

    # ── TDK CeraPlas HF (B54310N5100A010, 45,2 × 4 × 2,75, 5 W) ───────────────
    ("cp_len", "45.2 mm", "mm", "CeraPlas HF hossz"),
    ("cp_w", "4 mm", "mm", "CeraPlas HF szélesség (Z)"),
    ("cp_h", "2.75 mm", "mm", "CeraPlas HF vastagság (Y)"),
    ("cp_x0", "nozzle_len + 2 mm", "mm", "= kimeneti (HV) vég"),
    ("cp_x1", "cp_x0 + cp_len", "mm", "= bemeneti vég"),
    ("cp_pin_x", "cp_x1 - 11.3 mm", "mm", "= tüskék helye (11,3 mm a bemeneti végtől)"),
    ("cp_pin_z", "2.3 mm", "mm", "Tüskék oldaltávolsága (4,6 / 2)"),
    ("cp_pin_d", "0.6 mm", "mm", "Tüske átmérő"),
    ("liner_air", "0.85 mm", "mm", "Levegő a piezo sarka és a bélés furata között"),
    ("liner_ri", "sqrt((cp_w / 2) ^ 2 + (cp_h / 2) ^ 2) + liner_air", "mm",
     "= HV bélés (PEEK) furat sugara"),
    ("liner_wall", "2 mm", "mm", "HV bélés falvastagság"),
    ("liner_ro", "liner_ri + liner_wall", "mm", "= bélés külső sugara"),
    ("liner_x0", "nozzle_len", "mm", "= bélés eleje (a fúvóka mögött)"),
    ("liner_x1", "cp_x1 + 2.8 mm", "mm", "= bélés vége"),

    # ── Kamera (OV5640, 8,5 × 8,5 × 6 modul) + LED gyűrű ──────────────────────
    ("cam_mod", "8.5 mm", "mm", "OV5640 modul oldalhossz"),
    ("cam_depth", "6 mm", "mm", "OV5640 modul mélység (X)"),
    ("cam_ap", "3 mm", "mm", "Objektív szabad nyílás"),
    ("cam_peek", "0.6 mm", "mm", "Min. PEEK a kamera modul és a bélés között"),
    ("cam_y", "liner_ro + cam_peek + 0.35 mm + cam_mod / 2", "mm",
     "= kamera tengely magassága (θ = 0), közvetlenül a bélés fölött"),
    ("cam_tilt", "5 deg", "deg", "Kamera dőlése a tengely felé"),
    ("cam_x0", "face_x0 + (cam_y + cam_mod / 2 - face_r0) / face_k + win_tx + 0.3 mm", "mm",
     "= modul eleje (felső éle is az üveg mögött)"),
    ("cam_x1", "cam_x0 + cam_depth", "mm", "= modul hátulja"),
    ("led_pairs", "3", "", "405 nm + 660 nm LED párok a gyűrűn"),
    ("led_ring_r", "13.5 mm", "mm", "LED-ek köre a letörésen"),
    ("led_d", "1.6 mm", "mm", "LED lencse átmérő"),
    ("led_h", "0.8 mm", "mm", "LED magasság"),
    ("led_x", "face_x0 + (led_ring_r - face_r0) / face_k + win_tx + 0.1 mm", "mm",
     "= LED homloka (az üveg mögött)"),

    # ── Betét X lánc: B0 | plazma rekesz | B1 | AI rekesz | B2 | akku | B3 ────
    ("sled_x0", "body_x0 + nose_spigot + 0.2 mm", "mm", "= betét eleje (B0 elülső lapja)"),
    ("pcb_t", "1 mm", "mm", "AI + híd NYÁK vastagság"),
    ("pboard_t", "1.6 mm", "mm", "Plazma NYÁK vastagság (áram)"),
    ("pcb_y", "-(liner_ro + 0.6 mm)", "mm", "= minden NYÁK felső lapja (a bélés alatt)"),
    ("pboard_x0", "sled_x0 + b_t + 0.8 mm", "mm", "= plazma NYÁK eleje"),
    ("pboard_w", "20 mm", "mm", "Plazma NYÁK szélesség"),
    ("fan_len", "17 mm", "mm", "Sunon UB3H3-700 fúvó hossz"),
    ("fan_w", "17 mm", "mm", "Fúvó szélesség"),
    ("fan_h", "3 mm", "mm", "Fúvó vastagság"),
    ("fan_x0", "liner_x1 + 0.5 mm", "mm", "= fúvó eleje (kifúvó a bélés felé)"),
    ("fan_y0", "-(fan_h / 2)", "mm", "= fúvó alja"),
    ("b1_x0", "fan_x0 + fan_len + 0.5 mm", "mm", "= B1 (plazma | AI) válaszfal"),
    ("bridge_len", "16 mm", "mm", "Vezérlő híd NYÁK hossz (átmegy B1-en)"),
    ("bridge_w", "16 mm", "mm", "Vezérlő híd NYÁK szélesség"),
    ("bridge_x0", "b1_x0 + b_t / 2 - bridge_len / 2", "mm", "= híd eleje"),
    ("bridge_x1", "bridge_x0 + bridge_len", "mm", "= híd vége"),
    ("pboard_x1", "bridge_x0 - 0.8 mm", "mm", "= plazma NYÁK vége"),
    ("ai_x0", "bridge_x1 + 0.8 mm", "mm", "= AI NYÁK eleje"),
    ("ai_w", "22 mm", "mm", "AI NYÁK szélesség"),

    # ── Gomb + kijelző a hüvelykujjnál ────────────────────────────────────────
    ("thumb_x", "64 mm", "mm", "Hüvelykujj-párna közepe a csúcstól"),
    ("btn_x", "thumb_x", "mm", "= gomb közepe (plazma indítás, tartani kell)"),
    ("btn_d", "9 mm", "mm", "Gomb átmérő"),
    ("btn_proud", "0.35 mm", "mm", "Gomb kiemelkedése a lapos oldalból"),
    ("glass_x0", "btn_x + btn_d / 2 + 3 mm", "mm", "= fedőüveg eleje"),
    ("glass_x1", "glass_x0 + glass_len", "mm", "= fedőüveg vége"),
    ("oled_x0", "glass_x0 + glass_border", "mm", "= panel eleje"),
    ("oled_x1", "oled_x0 + oled_len", "mm", "= panel vége (FPC itt hajlik le)"),
    ("ai_min_len", "32 mm", "mm", "AI NYÁK min. hossz (ESP32-S3-WROOM-1U + csatlakozók)"),
    ("b2_x0", "(oled_x1 + 2.5 mm + ai_x0 + ai_min_len + 0.6 mm"
     " + abs(oled_x1 + 2.5 mm - ai_x0 - ai_min_len - 0.6 mm)) / 2", "mm",
     "= B2 (AI | akku) válaszfal: a panel FPC mögött, de az AI NYÁK-nak is legyen hely"),
    ("ai_x1", "b2_x0 - 0.6 mm", "mm", "= AI NYÁK vége"),

    # ── Akku: Samsung INR21700-50E (Ø21,25 × 70,8 max, 4900 mAh) ─────────────
    ("bat_d", "21.25 mm", "mm", "21700 cella átmérő"),
    ("bat_len", "70.8 mm", "mm", "21700 cella hossz"),
    ("bat_contact", "1.2 mm", "mm", "Rugós érintkező hely a cella végein"),
    ("bat_x0", "b2_x0 + b_t + bat_contact", "mm", "= akku eleje (+)"),
    ("bat_x1", "bat_x0 + bat_len", "mm", "= akku vége (−)"),
    ("b3_x0", "bat_x1 + bat_contact", "mm", "= B3 hátsó fal"),
    ("sled_x1", "b3_x0 + b_t", "mm", "= betét vége"),

    # ── Hátsó kupak (fénykivezető PC: dokk, antenna, státuszfény) ─────────────
    ("cap_spigot", "3 mm", "mm", "Kupak csapja a ház furatában"),
    ("cap_gap", "0.2 mm", "mm", "Kupak csap ↔ betét hézag"),
    ("body_end", "sled_x1 + cap_gap + cap_spigot", "mm", "= ház hátsó vége, itt kezdődik a kupak"),
    ("cap_len", "13 mm", "mm", "Kupak hossz"),
    ("cap_ch", "1.6 mm", "mm", "Kupak hátsó élének letörése (Kamm-vég)"),
    ("cap_floor", "1.6 mm", "mm", "PC fenék a dokk NYÁK alatt (érintkezők ezen át)"),
    ("cap_rear", "2 mm", "mm", "Kupak hátsó fala"),
    ("dock_pcb_t", "0.8 mm", "mm", "Dokk NYÁK vastagság"),
    ("mag_skin", "0.3 mm", "mm", "PC bőr a mágnesek alatt (nem látszanak)"),
    ("pen_len", "body_end + cap_len", "mm", "= teljes hossz"),

    # ── Külső forma (Pininfarina: egy feszes vonal, csepp) ────────────────────
    ("max_frac", "0.58", "", "Legvastagabb pont a hossz hányadában (a csúcstól)"),
    ("x_max", "pen_len * max_frac", "mm", "= legvastagabb pont"),
    ("tail_dr", "1.2 mm", "mm",
     "Csónakfar: a kupak ennyivel szűkül a hátsó parabola alá (érintőlegesen indul a kupak elején)"),
    ("tc_x0", "nose_split + 4 mm", "mm", "Felső vágás: itt kezd lemenni (a felület fölött)"),
    ("tc_x1", "btn_x - btn_d / 2 - 4 mm", "mm", "Felső vágás: innen sík"),
    ("tc_x2", "glass_x1 + 6 mm", "mm", "Felső vágás: eddig sík, utána hátrafelé emelkedik"),
    ("top_rise", "1.2 mm", "mm", "Felső sík emelkedése a kupak végéig"),
    ("glass_r_body", "body_r0 + (body_r - body_r0) * (1 - (1 - (glass_x0 - nose_split) / "
     "(x_max - nose_split)) ^ 2)", "mm", "= ház sugara az üveg elején"),
    ("top_y", "sqrt(glass_r_body ^ 2 - (glass_w / 2 + top_land + top_ch) ^ 2)", "mm",
     "= felső lapos oldal síkja (az üveg + perem épp ráfér)"),
    ("bore_top", "top_y - glass_t - oled_t - 0.1 mm", "mm", "= furat felső síkja (panel a falban)"),

    # ── Akku helye → alsó sík ─────────────────────────────────────────────────
    ("bat_gap", "0.5 mm", "mm", "Akku ↔ furat sík hézag (Kapton + játék)"),
    ("bat_y", "bore_top - bat_gap - bat_d / 2", "mm", "= akku tengelye (tengely alatt)"),
    ("pcb_under", "4 mm", "mm", "Hely a NYÁK-ok alatt az alkatrészeknek (trafó, tekercs, ESP32)"),
    ("bore_bot", "(-(bat_y - bat_d / 2 - bat_gap) - pcb_y + pboard_t + pcb_under + sled_wall"
     " + sled_c + 0.1 mm + abs(-(bat_y - bat_d / 2 - bat_gap) + pcb_y - pboard_t - pcb_under"
     " - sled_wall - sled_c - 0.1 mm)) / 2", "mm",
     "= furat alsó síkja (nagyság, −Y): az akku vagy a NYÁK-ok alatti hely közül a nagyobb"),
    ("bot_y", "bore_bot + shell_wall", "mm", "= alsó (dokk) lapos oldal (nagyság, −Y)"),
    ("bc_x1", "body_end - 30 mm", "mm", "Alsó vágás: innen sík"),
    ("bc_x0", "bc_x1 - 28 mm", "mm", "Alsó vágás: itt kezd felfutni (a felület alatt)"),
    ("sled_top", "bore_top - sled_c", "mm", "= betét felső síkja"),
    ("sled_bot", "bore_bot - sled_c", "mm", "= betét alsó síkja (nagyság)"),
    ("sled_top_i", "sled_top - sled_wall", "mm", "= betét belső felső síkja"),
    ("sled_bot_i", "sled_bot - sled_wall", "mm", "= betét belső alsó síkja (nagyság)"),

    # ── A-tartomány csatorna (kamera flex + gomb kupola) a betét tetején ──────
    ("tun_w", "9 mm", "mm", "Kamera flex csatorna szélesség (0,3 mm osztású 24 eres flex)"),
    ("tun_floor", "liner_ro + 0.1 mm", "mm", "= csatorna padló alja"),
    ("tun_floor_t", "0.5 mm", "mm", "Csatorna padló vastagság"),

    # ── Dokk (kupak alja): 4 arany érintkező + 2 mágnes ───────────────────────
    ("dock_pins", "4", "", "Érintkezők (V+, GND, TX, RX)"),
    ("dock_pitch", "2.54 mm", "mm", "Érintkező osztás (Mill-Max 0906 rugós tűk a dokkban)"),
    ("dock_pad_d", "1.8 mm", "mm", "Érintkező tárcsa átmérő"),
    ("dock_xc", "body_end + (cap_len - cap_ch - bot_ch) / 2", "mm",
     "= érintkezősor (Z irányú sor) X helye a kupak alsó síkjának közepén"),
    ("mag_d", "3 mm", "mm", "Mágnes átmérő (N52, a tengelyen)"),
    ("mag_t", "1.5 mm", "mm", "Mágnes vastagság"),
    ("mag_dx", "3.2 mm", "mm", "Mágnesek távolsága az érintkezősortól (elöl + hátul)"),

    # ── Működés (render jelenet) ──────────────────────────────────────────────
    ("standoff", "10 mm", "mm", "Fúvóka ↔ felület távolság"),
    ("plume_r", "3.2 mm", "mm", "Plazmaláng legnagyobb sugara"),
    ("spot_d", "16 mm", "mm", "Megvilágított folt a lemezen"),
    ("dish_d", "90 mm", "mm", "Petri-csésze átmérő"),
    ("dish_h", "14 mm", "mm", "Petri-csésze magasság"),
    ("dish_wall", "1 mm", "mm", "Petri-csésze fal"),
    ("agar_t", "6 mm", "mm", "Agar réteg"),

    # ── ELLENŐRZÉSEK: mind ≥ 0 kell ───────────────────────────────────────────
    ("chk_top_fade", "tc_x1 - tc_x0 - 6 mm", "mm",
     "ELLENŐRZÉS: a felső lapos oldal felfutása ≥ 6 mm (gomb nem kerül a gallérra)"),
    ("chk_hv_cam", "sqrt((cam_x0 - cp_x0) ^ 2 + (cam_y - cam_mod / 2) ^ 2) - hv_clear", "mm",
     "ELLENŐRZÉS: kamera ↔ piezo kimenet ≥ 20 mm"),
    ("chk_hv_led", "sqrt((led_x - cp_x0) ^ 2 + (led_ring_r - led_d / 2) ^ 2) - hv_clear", "mm",
     "ELLENŐRZÉS: LED-ek ↔ piezo kimenet ≥ 20 mm"),
    ("chk_hv_alu", "sqrt((body_x0 - cp_x0) ^ 2 + bore_r ^ 2) - hv_clear_edge",
     "mm", "ELLENŐRZÉS: alu ház éle ↔ piezo kimenet ≥ 30 mm"),
    ("chk_hv_board", "sqrt((pboard_x0 - cp_x0) ^ 2 + (pcb_y) ^ 2) - hv_clear", "mm",
     "ELLENŐRZÉS: plazma NYÁK ↔ piezo kimenet ≥ 20 mm"),
    ("chk_hv_target", "cp_x0 + standoff - hv_clear", "mm",
     "ELLENŐRZÉS: seb ↔ piezo kimenet ≥ 20 mm (nincs átütés a betegre)"),
    ("chk_cam_liner", "cam_y - cam_mod / 2 - liner_ro - cam_peek", "mm",
     "ELLENŐRZÉS: kamera modul ↔ bélés között ≥ cam_peek PEEK"),
    ("chk_cam_out", "nose_r1 - 1 mm - sqrt((cam_y + cam_mod / 2) ^ 2 + (cam_mod / 2) ^ 2)", "mm",
     "ELLENŐRZÉS: kamera modul sarka ↔ gallér külseje ≥ 1 mm"),
    ("chk_cam_win", "cam_y - cam_ap / 2 - win_r0", "mm",
     "ELLENŐRZÉS: objektív nyílása az üveggyűrűn belül"),
    ("chk_cam_view",
     "plume_r + (cam_y - plume_r) * standoff / (face_x0 + (cam_y - face_r0) / face_k + standoff)"
     " - tip_r0", "mm", "ELLENŐRZÉS: kamera rálát a láng széléig (a csőr nem takar)"),
    ("chk_pins", "cp_pin_x - sled_x0 - b_t - 1 mm", "mm",
     "ELLENŐRZÉS: piezo tüskék a B0 fal mögött, a plazma NYÁK fölött"),
    ("chk_fan", "sqrt(sled_ri ^ 2 - (fan_h / 2) ^ 2) - fan_w / 2 - 0.5 mm", "mm",
     "ELLENŐRZÉS: fúvó befér a betétbe"),
    ("chk_board_w", "sqrt(sled_ri ^ 2 - (pcb_y - pboard_t) ^ 2) - ai_w / 2 - 0.3 mm", "mm",
     "ELLENŐRZÉS: NYÁK-ok férnek a betétben"),
    ("chk_ai_len", "ai_x1 - ai_x0 - ai_min_len", "mm",
     "ELLENŐRZÉS: AI NYÁK legalább ai_min_len hosszú"),
    ("chk_tunnel", "sled_top_i - tun_floor - tun_floor_t - 1 mm", "mm",
     "ELLENŐRZÉS: kamera flex csatorna ≥ 1 mm magas"),
    ("chk_under", "sled_bot_i + pcb_y - pboard_t - pcb_under", "mm",
     "ELLENŐRZÉS: a betét alja a NYÁK-ok alatti hely (pcb_under) alatt van"),
    ("chk_bat_side", "sqrt(sled_ri ^ 2 - bat_y ^ 2) - bat_d / 2 - 1.5 mm", "mm",
     "ELLENŐRZÉS: koax + szalag fér az akku mellett"),
    ("chk_wall_top", "top_y - bore_top - glass_t - 0.5 mm", "mm",
     "ELLENŐRZÉS: alu fal a lapos oldal alatt (üvegzseb mellett)"),
    ("chk_dock_w",
     "sqrt((body_r - (body_r - body_rt) * ((dock_xc - x_max) / (body_end - x_max)) ^ 2"
     " - tail_dr * ((dock_xc - body_end) / cap_len) ^ 2) ^ 2 - bot_y ^ 2) - bot_ch - (dock_pins - 1) * dock_pitch / 2 - dock_pad_d / 2 - 0.5 mm", "mm",
     "ELLENŐRZÉS: érintkezősor elfér a kupak alsó síkján (Z)"),
    ("chk_dock_len", "(cap_len - cap_ch - bot_ch) / 2 - mag_dx - mag_d / 2 - 0.3 mm", "mm",
     "ELLENŐRZÉS: mágnesek a kupak alsó síkján belül (X)"),
]


def names():
    return [p[0] for p in PARAMS]
