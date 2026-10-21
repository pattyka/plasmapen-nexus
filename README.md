# PlasmaPen Nexus — paraméteres Fusion modell

## Futtatás
1. Fusion → **Utilities → Add-Ins → Scripts and Add-Ins** → Scripts fül → **+** → válaszd ki a `PlasmaPenNexus/` mappát.
2. **Run**. Új design nyílik, a progress ablak 9 lépést mutat, a végén egy sor: hossz × Ø · tömeg · paraméterek száma.
3. Ha valami nem épült meg, a mappában lesz `build_log.txt` a pontos hibával. Ezt küldd át.

Egy design, két assembly:
- **PlasmaPen Nexus — működés**: a toll lefelé néz egy agaros Petri-csészére, plazma be, LED-ek világítanak.
- **PlasmaPen Nexus — engineering**: ugyanaz a toll fekve, a héjak félbevágva, látszik minden belső alkatrész.

A belső alkatrészek közös komponensek, így a kettő mindig ugyanazt a hardvert mutatja.

## Szerkesztés
**Modify → Change Parameters.** Minden méret ott van magyar kommenttel, és mindkét assembly követi.

A `chk_` kezdetű sorok ellenőrzések, ezeknek ≥ 0-nak kell lenniük:
- `chk_bore`: piezo ↔ bélés,
- `head_chk_cam`: kamera falak,
- `head_chk_hv`: 15 kV távolság.

A legfontosabbak: `body_od`, `flat_y` (a lapos oldal mélysége), `cone_len`, `swell_x1`, `back_od` (orsóforma), `tip_od`, `standoff`, `pcb_len`, `bat_d`/`bat_len`.

Egy paraméterváltás után a teljes idővonal újraszámol (~220 feature), ez 10–30 másodperc.

## Render
1. **Render workspace** → Scene Settings: környezet „Photo Booth”, háttér sima szín.
2. A plazma, a LED-ek és a megvilágított folt emisszív anyagot kapott. **Local/Cloud render**-ben izzanak, a sima viewportban nem.
3. Kijelző: **Insert → Decal** →
   - kép: `PlasmaPenNexus/assets/oled_ui.png`,
   - felület: az „OLED aktív terület” test teteje,
   - méret: 25,578 × 10,962 mm, arány zárva,
   - a kép bal széle az orr felé.
4. Engineering képhez nézz a metszett oldalra (front view).

## Ami eltér a pitch-től, és miért
- **CeraPlas F csupasz piezo rúd** (72 × 6 × 2,8) a HF modul (47,3 × 20 × 20) helyett. A HF doboz miatt Ø32 alá nem lehetett menni.
- **1,1" 126×294 színes AMOLED** a 0,96" OLED helyett. Keskeny csík, ráfér a lapos oldalra, és ki tudja rajzolni a kamera fluoreszcencia-térképét.
- **ESP32-S3-MINI-1U + antenna a fekete PEEK kupakban.** Alu csőből a BLE jel nem jut ki.
- **Mikroventilátor + szellőzők alul.** A „fúj”-hoz légáram kell, a BOM-ban nem volt benne.
- **Tömeg ~248 g** (CadQuery becslés), a cél 280 g.

## Ellenőrzés Fusion nélkül
```
uv run --python 3.12 --with cadquery --with matplotlib --with numpy python tools/check.py
uv run --python 3.12 --with cadquery --with matplotlib --with numpy python tools/preview.py
```
- `check.py`: ütközések, furatba férés, tömeg, 17 paraméter-variáns, és a Fusion API hívások statikus ellenőrzése.
- `preview.py`: képek a `tools/out/` mappába.
