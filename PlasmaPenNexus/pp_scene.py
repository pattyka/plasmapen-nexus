"""PlasmaPen Nexus — render scene: plasma plume, petri dish with agar, 405 nm spot.

Everything lives at x < 0 (in front of the nozzle face) and is built with pen=False so it never
enters the mass report. All bodies are revolved about the X axis.

    x = 0                       nozzle face
    x = -scene_gap              plume starts (a hair in front of the face)
    x = -standoff               agar surface
    x = scene_dish_in           inner floor of the dish   = -(standoff + agar_t)
    x = scene_dish_out          outer floor of the dish   = -(standoff + agar_t + dish_wall)
    x = scene_rim_x             dish rim                  = scene_dish_out + dish_h

Plume: a piezo direct discharge (CeraPlas) jet leaves the bore slightly narrower than the bore,
swells into a soft bulge, necks down and spreads into a skirt where it strikes the agar
(impinging jet). The core follows the same shape, thinner and a hair shorter at both ends so no
face of the core coincides with a face of the halo.
"""

from pp_core import neg

EXTRA_PARAMS = [
    ("scene_gap", "0.05 mm", "mm", "Hézag, hogy ne essenek egybe lapok"),

    # ── Plazmaláng ──
    ("scene_plume_x0", "-scene_gap", "mm", "= láng kezdete a fúvóka előtt"),
    ("scene_halo_r0", "nozzle_d / 2 - 0.3 mm", "mm", "Fényudvar sugara a fúvókánál"),
    ("scene_halo_neck", "plume_r * 0.74", "mm", "Fényudvar szűkülete"),
    ("scene_halo_foot", "plume_r * 1.45", "mm", "Fényudvar szétterülése a felületen"),
    ("scene_core_r0", "nozzle_d / 2 * 0.42", "mm", "Mag sugara a fúvókánál"),
    ("scene_core_max", "plume_r * 0.44", "mm", "Mag legnagyobb sugara"),
    ("scene_core_neck", "plume_r * 0.3", "mm", "Mag szűkülete"),
    ("scene_core_foot", "plume_r * 0.72", "mm", "Mag szétterülése a felületen"),

    # ── Petri-csésze ──
    ("scene_dish_in", "-(standoff + agar_t)", "mm", "= csésze belső alja"),
    ("scene_dish_out", "scene_dish_in - dish_wall", "mm", "= csésze külső alja"),
    ("scene_rim_x", "scene_dish_out + dish_h", "mm", "= csésze pereme"),
    ("scene_dish_draft", "0.4 mm", "mm", "Fal kúposság (sugár csökkenés az aljig)"),
    ("scene_dish_rc", "1.5 mm", "mm", "Külső alsó sarok lekerekítés"),
    ("scene_dish_ro", "dish_d / 2", "mm", "= csésze külső sugara a peremnél"),
    ("scene_dish_rb", "scene_dish_ro - scene_dish_draft", "mm", "= külső sugár az aljnál"),
    ("scene_dish_ri", "scene_dish_rb - dish_wall", "mm", "= belső sugár az aljnál"),
    ("scene_dish_rci", "scene_dish_rc - dish_wall", "mm", "= belső alsó sarok lekerekítés"),

    # ── Agar ──
    ("scene_agar_r", "scene_dish_ri - scene_gap", "mm", "= agar sugara"),
    ("scene_men_h", "0.8 mm", "mm", "Agar meniszkusz magassága a falnál"),
    ("scene_men_w", "2.5 mm", "mm", "Agar meniszkusz szélessége"),

    # ── 405 nm folt ──
    ("scene_spot_t", "0.05 mm", "mm", "Folt vastagság"),
    ("scene_spot_x0", "-standoff + scene_gap", "mm", "= folt alja az agar fölött"),
    ("scene_spot_x1", "scene_spot_x0 + scene_spot_t", "mm", "= folt teteje"),
    ("scene_plume_x1", "scene_spot_x1 + scene_gap", "mm", "= láng vége a folt fölött"),
]


def _at(frac):
    """x at a fraction of the way from the nozzle face to the agar surface."""
    return neg(f"standoff * {frac}")


def _near(x_end, frac):
    """x a fraction of the standoff short of the plume end (toward the nozzle)."""
    return f"{x_end} + standoff * {frac}"


def _plume_profile(x0, x1, r0, r_max, r_neck, r_foot):
    """Jet leaving the bore, soft bulge, neck, then a skirt that spreads along the surface."""
    return [
        (x0, "0 mm"),
        (x0, r0),
        ("spline", [
            (_at(0.12), f"{r_max} * 0.9"),
            (_at(0.32), r_max),
            (_at(0.56), f"{r_max} * 0.88"),
            (_at(0.76), r_neck),
            (_near(x1, 0.1), f"{r_neck} * 1.08"),
            (_near(x1, 0.035), f"{r_neck} + ({r_foot} - {r_neck}) * 0.36"),
            (_near(x1, 0.01), f"{r_neck} + ({r_foot} - {r_neck}) * 0.72"),
            (x1, r_foot),
        ]),
        (x1, "0 mm"),
    ]


def _plume(bk, comp):
    halo = _plume_profile("scene_plume_x0", "scene_plume_x1", "scene_halo_r0", "plume_r",
                          "scene_halo_neck", "scene_halo_foot")
    bk.revolve(comp, "Fényudvar", halo, look="plasma_halo", pen=False)
    # The core is a hair shorter at both ends so its end faces never coincide with the halo's.
    core = _plume_profile("scene_plume_x0 - scene_gap", "scene_plume_x1 + scene_gap",
                          "scene_core_r0", "scene_core_max", "scene_core_neck", "scene_core_foot")
    bk.revolve(comp, "Mag", core, look="plasma_core", pen=False)


def _dish(bk, comp):
    xo, xi, xr = "scene_dish_out", "scene_dish_in", "scene_rim_x"
    rb, ri, ro = "scene_dish_rb", "scene_dish_ri", "scene_dish_ro"
    rc, rci, w = "scene_dish_rc", "scene_dish_rci", "dish_wall"
    # Corners are quarter arcs about the same centre (xo + rc, rb - rc), sampled at 30° / 60°.
    # The rim is a half round of diameter dish_wall.
    profile = [
        (xo, "0 mm"),
        (xo, f"{rb} - {rc}"),
        ("spline", [
            (f"{xo} + {rc} * 0.134", f"{rb} - {rc} * 0.5"),
            (f"{xo} + {rc} * 0.5", f"{rb} - {rc} * 0.134"),
            (f"{xo} + {rc}", rb),
        ]),
        (f"{xr} - {w} / 2", ro),
        ("spline", [
            (f"{xr} - {w} * 0.1464", f"{ro} - {w} * 0.1464"),
            (xr, f"{ro} - {w} / 2"),
            (f"{xr} - {w} * 0.1464", f"{ro} - {w} * 0.8536"),
            (f"{xr} - {w} / 2", f"{ro} - {w}"),
        ]),
        (f"{xi} + {rci}", ri),
        ("spline", [
            (f"{xi} + {rci} * 0.5", f"{ri} - {rci} * 0.134"),
            (f"{xi} + {rci} * 0.134", f"{ri} - {rci} * 0.5"),
            (xi, f"{ri} - {rci}"),
        ]),
        (xi, "0 mm"),
    ]
    bk.revolve(comp, "Csésze", profile, look="petri", material="plastic", pen=False)

    xa = f"{xi} + scene_gap"
    ra = "scene_agar_r"
    agar = [
        (xa, "0 mm"),
        (xa, f"{ra} - {rci}"),
        (f"{xa} + {rci}", ra),
        ("-standoff + scene_men_h", ra),
        ("spline", [
            ("-standoff + scene_men_h * 0.3", f"{ra} - scene_men_w * 0.38"),
            ("-standoff", f"{ra} - scene_men_w"),
        ]),
        ("-standoff", "0 mm"),
    ]
    bk.revolve(comp, "Agar", agar, look="agar", pen=False)


def _spot(bk, comp):
    bk.tube_x(comp, "Folt", "scene_spot_x0", "scene_spot_x1", "spot_d / 2",
              look="spot405", pen=False)


def build_scene(bk, parent):
    plazma = bk.component(parent, "Plazma")
    _plume(bk, plazma)
    petri = bk.component(parent, "Petri-csésze")
    _dish(bk, petri)
    folt = bk.component(parent, "Folt")
    _spot(bk, folt)
    return [plazma, petri, folt]
