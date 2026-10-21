# PlasmaPen Nexus — paraméteres Fusion modell (4. változat)

## Futtatás
1. Fusion → **Utilities → Add-Ins → Scripts and Add-Ins** → Scripts fül → **+** → válaszd ki a `PlasmaPenNexus/` mappát.
2. **Run**. Új design nyílik, a progress ablak 9 lépést mutat, a végén egy sor: hossz × Ø · tömeg · paraméterek száma.
3. Ha valami nem épült meg, a mappában lesz `build_log.txt` a pontos hibával. Ezt küldd át.

Egy design, két assembly:
- **PlasmaPen Nexus — működés**: a toll lefelé néz egy agaros Petri-csészére, plazma be, LED-ek világítanak.
- **PlasmaPen Nexus — engineering**: ugyanaz a toll fekve. A ház, a kupak, az üveg, az orrkúp, a HV bélés és a betét félbevágva, látszik minden belső alkatrész.

A belső alkatrészek közös komponensek, így a kettő mindig ugyanazt a hardvert mutatja.

## Felépítés
- **Tok, 3 darab**: fekete PEEK orrkúp az üveggyűrűvel, eloxált alu ház (extrudált cső, kívül esztergálva), matt PC hátsó kupak (dokk, antenna, státuszfény).
- **Betét (PEI)**: az orrkúppal együtt elölről csúszik a házba, a kupak hátul rögzíti.
  - Elöl a plazma rekesz (piezo, plazma NYÁK, fúvó), galvanikusan leválasztva.
  - Mögötte az AI rekesz, az akku és a dokk.
  - A kettőt a B1 falon átmenő vezérlő híd köti össze (ISO7741 + leválasztó trafó).

## Szerkesztés
**Modify → Change Parameters.** Minden méret ott van magyar kommenttel, és mindkét assembly követi.

A `chk_` kezdetű sorok ellenőrzések, ezeknek ≥ 0-nak kell lenniük. A modulok saját ellenőrzései `shell_chk_`, `head_chk_`, `ins_chk_` és `el_chk_` előtaggal vannak. A legfontosabbak:
- `chk_hv_*`: 20 mm a piezo kimenetétől minden vezetőig (alu élre 30 mm), a TDK előírása szerint.
- `chk_cam_*`: a kamera befér a gallér alá, és rálát a láng széléig.
- `chk_under`, `el_chk_under`: hely a NYÁK-ok alatt.
- `chk_dock_*`: a dokk érintkezők és a mágnesek a kupak alsó síkján.

A legfontosabb méretek:
- `body_od`: legalább 35, a CeraPlas F-hez 37.
- `thumb_x`: hüvelykujj, gomb, kijelző.
- `cp_len`/`cp_w`: HF 45,2 × 4, F 70,6 × 6.
- `bat_d`/`bat_len`: 21700 vagy 18650.
- `max_frac`: a legvastagabb pont helye.
- `standoff`, `top_y` (származtatott), `top_rise`.

Egy paraméterváltás után a teljes idővonal újraszámol.

## Render
1. **Render workspace** → Scene Settings: környezet „Photo Booth”, háttér sima szín.
2. A plazma, a LED-ek, a státuszfény és a megvilágított folt emisszív anyagot kapott. **Local/Cloud render**-ben izzanak, a sima viewportban nem.
3. Kijelző: **Insert → Decal** →
   - kép: `PlasmaPenNexus/assets/oled_ui.png` (álló, 240 × 536),
   - felület: az „AMOLED aktív terület” test teteje,
   - méret: 19,8 × 44,22 mm, arány zárva,
   - a kép **teteje az orr felé** néz (a szünet gomb a hüvelykujjnál van).
4. Engineering képhez nézz a metszett oldalra (front view).

## Ami eltér a pitch-től, és miért
- **CeraPlas HF** (45,2 × 4 × 2,75, 5 W) az F helyett. 25 mm-rel rövidebb a toll, a teljesítmény a pitch 5 W-os alsó határa. Az F 37 mm-es átmérővel befér.
- **1,91" 240×536 érintős AMOLED** a 0,96" OLED helyett. Ez a legnagyobb panel, ami Ø36-on ráfér a lapos oldalra.
- **Nincs USB-C.** Töltés és adat a 4 érintkezős dokkon át, a kupak alján. A kupak egyben a BLE antenna ablaka és a státuszfény.
- **Két külön NYÁK**, galvanikus leválasztással: ISO7741 + SN6507 + trafó. A felhasználó felőli oldalon van minden, amit meg lehet fogni vagy dugni.
- **Ø36 a minimum**, nem stílus. Alatta nem fér el az OV5640 kamera, a flex csatorna és a dokk.
- **Tömeg ~225 g** (CadQuery becslés), a cél 280 g.

## Ellenőrzés Fusion nélkül
```
uv run --python 3.12 --with cadquery --with matplotlib --with numpy python tools/check.py
uv run --python 3.12 --with cadquery --with matplotlib --with numpy python tools/preview.py
```
- `check.py`: ütközések, furatba férés, tömeg + súlypont, minden `chk_`, 15 tervváltozat, és a Fusion API hívások statikus ellenőrzése.
- `preview.py`: képek a `tools/out/` mappába.
- A kijelzőkép újragenerálása: `uv run --python 3.12 --with pillow --with numpy python PlasmaPenNexus/assets/make_oled_ui.py`
