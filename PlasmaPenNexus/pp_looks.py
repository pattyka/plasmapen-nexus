"""PlasmaPen Nexus — render appearances and physical materials.

FusionBackend.appearance(key) finds the first library appearance whose (lower-cased) name contains
every keyword of a match list, trying the lists in order, copies it into the design as
"PPN <label>" and hands the copy to tune(). FusionBackend.material(key) does the same lookup for
physical materials (no copy, no tuning).

Library names below were checked against a listing of app.materialLibraries taken from Fusion
2705.1.15 (Sept 2026): "Fusion Appearance Library" and the appearances of "Fusion Material Library".
Every list ends in a generic fallback ("Base Material - Opaque/Metal/Transparent" or a bare
category word) so a renamed library entry still lands on something sensible.

Spec keys used by tune():
    color       (r, g, b) 0-255, written to the schema's base colour (albedo / f0 / transmission)
    alpha       0-255; < 255 makes an opaque appearance translucent (Appearance.color, 2025+ API)
    roughness   0 (mirror) … 1 (matte); omitted = keep the library value (and its texture)
    luminance   cd/m²; turns on Prism opaque emission with the colour `glow` (default: color)
    glow        (r, g, b) emission tint
"""

# Prism schema property ids (Autodesk Prism / Standard Material, as used by Fusion):
#   opaque:      opaque_albedo, opaque_emission (bool), opaque_luminance (cd/m²),
#                opaque_luminance_modifier (emission colour), opaque_translucency
#   metal:       metal_f0
#   transparent: transparent_color, transparent_ior, transparent_distance
#   glazing:     glazing_transmission_color
#   layered:     layered_diffuse
#   all:         surface_roughness
_COLOR_IDS = (
    "opaque_albedo",
    "metal_f0",
    "transparent_color",
    "glazing_transmission_color",
    "layered_diffuse",
    "solidglass_transmittance_custom_color",
    "generic_diffuse",
)
_COLOR_NAMES = ("color", "colour", "base color", "albedo", "diffuse")
_EMISSION_ON_IDS = ("opaque_emission",)
_LUMINANCE_IDS = ("opaque_luminance", "generic_self_illum_luminance")
_LUMINANCE_NAMES = ("luminance",)
_GLOW_IDS = ("opaque_luminance_modifier", "generic_self_illum_filter_map")
_GLOW_NAMES = ("emission color", "filter color", "luminance modifier")
_ROUGHNESS_IDS = ("surface_roughness",)
_ROUGHNESS_NAMES = ("roughness",)

# Fallback tails shared by many looks.
_OPAQUE = [["base material - opaque"], ["plastic"]]
_METAL = [["base material - metal"], ["steel"]]
_CLEAR = [["base material - transparent"], ["glass"]]
_EMISSIVE = [["led ("], ["led -"], ["base material - opaque"], ["plastic", "matte", "white"]]


LOOKS = {
    # ── shells ──────────────────────────────────────────────────────────────
    "alu": {
        "label": "Alumínium",
        "match": [["aluminum - bead blasted"], ["aluminum", "bead"], ["aluminum - satin"],
                  ["aluminum", "anodized", "grey"], ["aluminum -"]] + _METAL,
        "color": (214, 216, 219),
    },
    "alu_dark": {
        "label": "Alumínium sötét",
        "match": [["aluminum - anodized rough (grey)"], ["aluminum", "anodized", "grey"],
                  ["aluminum", "anodized"], ["aluminum - satin"]] + _METAL,
        "color": (62, 64, 68),
    },
    # Nose cone + HV liner: PEEK compounded to the anodised silver (TiO2-based grey, no carbon
    # black: it must stay an insulator). Tone-on-tone with the housing, so the violet glass ring
    # is the only accent and the nose reads as the front of the body, not a black speculum.
    "peek": {
        "label": "PEEK ezüstszürke",
        "match": [["plastic - matte (gray)"], ["plastic", "matte", "gr"], ["plastic", "gr"]]
        + _OPAQUE,
        "color": (138, 141, 147),
        "roughness": 0.42,
    },
    # Insert: ULTEM-type PEI, natural amber, translucent — reads as "the inner part" in the cutaway.
    "pei": {
        "label": "PEI borostyán",
        "match": [["plastic - translucent glossy (yellow)"], ["plastic", "translucent", "yellow"],
                  ["phenolic (amber)"], ["plastic", "translucent"]] + _OPAQUE,
        "color": (196, 132, 46),
        "roughness": 0.3,
        "alpha": 210,
    },
    # ── glass ───────────────────────────────────────────────────────────────
    # End cap: bead-blasted optical PC light guide; the status LED behind it lights the whole cap.
    "glass_frost": {
        "label": "Matt üveghatás",
        "match": [["glass - frosted"], ["glass", "frosted"], ["acrylic (frosted)"],
                  ["polycarbonate (frosted)"], ["plastic - translucent matte (white)"],
                  ["plastic", "translucent", "white"]] + _CLEAR,
        "color": (236, 238, 240),
        "roughness": 0.55,
    },
    "glass_window": {
        "label": "Üveg ibolya",
        "match": [["glass (clear)"], ["acrylic (clear)"], ["polycarbonate (clear)"],
                  ["glass", "clear"], ["glass - window"]] + _CLEAR,
        "color": (242, 236, 255),
    },
    "glass_black": {
        "label": "Üveg füst",
        "match": [["glass (grey)"], ["glass", "grey"], ["glass", "gray"], ["glass - heavy color"],
                  ["glass (clear)"]] + _CLEAR,
        "color": (74, 74, 80),
    },
    "lens": {
        "label": "Lencse",
        "match": [["glass (clear)"], ["glass", "clear"], ["acrylic (clear)"]] + _CLEAR,
        "color": (222, 230, 242),
    },
    # ── light sources ───────────────────────────────────────────────────────
    "led405": {
        "label": "LED 405 nm",
        "match": [["led (blue)"], ["led", "blue"]] + _EMISSIVE,
        "color": (118, 58, 255),
        "luminance": 6000.0,
    },
    "led660": {
        "label": "LED 660 nm",
        "match": [["led (red)"], ["led", "red"]] + _EMISSIVE,
        "color": (236, 18, 22),
        "luminance": 4500.0,
    },
    "plasma_core": {
        "label": "Plazma mag",
        "match": [["led (blue)"], ["led", "blue"]] + _EMISSIVE,
        "color": (190, 166, 255),
        "glow": (176, 150, 255),
        "luminance": 2200.0,
        "alpha": 200,
    },
    "plasma_halo": {
        "label": "Plazma fényudvar",
        "match": [["led (blue)"], ["led", "blue"]] + _EMISSIVE,
        "color": (132, 98, 255),
        "luminance": 320.0,
        "alpha": 64,
    },
    "spot405": {
        "label": "Folt 405 nm",
        "match": [["led (blue)"], ["led", "blue"]] + _EMISSIVE,
        "color": (150, 112, 255),
        "luminance": 60.0,
        "alpha": 96,
    },
    # Colour AMOLED active area: true black (off pixels), glossy like the polarizer. The UI is the
    # decal assets/oled_ui.png on top; no emission here, or it would wash out the decal's black.
    "oled_on": {
        "label": "AMOLED",
        "match": [["plastic - glossy (black)"], ["plastic", "glossy", "black"],
                  ["paint - enamel glossy (black)"], ["plastic", "black"]] + _OPAQUE,
        "color": (0, 0, 0),
        "roughness": 0.04,
    },
    # ── internals ───────────────────────────────────────────────────────────
    "ceramic": {
        "label": "Piezo kerámia",
        "match": [["ceramic"], ["porcelain"], ["plastic - matte (white)"], ["aluminum nitride"],
                  ["plastic", "white"]] + _OPAQUE,
        "color": (228, 226, 220),
        "roughness": 0.5,
    },
    "pcb": {
        "label": "NYÁK",
        "match": [["fr4"], ["fr-4"], ["plastic - glossy (green)"], ["plastic", "green"]] + _OPAQUE,
        "color": (24, 46, 38),
        "roughness": 0.35,
    },
    "shield": {
        "label": "Árnyékoló",
        "match": [["nickel - satin"], ["stainless steel - satin"], ["nickel"],
                  ["steel", "satin"]] + _METAL,
        "color": None,
    },
    "copper": {
        "label": "Réz",
        "match": [["copper - polished"], ["copper - raw"], ["copper"], ["brass"]] + _METAL,
        "color": None,
    },
    "gold": {
        "label": "Arany",
        "match": [["gold - polished"], ["gold"], ["brass - polished"], ["brass"]] + _METAL,
        "color": None,
        "roughness": 0.25,
    },
    "steel": {
        "label": "Acél",
        "match": [["stainless steel - satin"], ["steel - satin"], ["stainless steel"],
                  ["steel"]] + _METAL,
        "color": None,
    },
    "battery_wrap": {
        "label": "Akku fólia",
        "match": [["plastic - glossy (blue)"], ["plastic", "glossy", "blue"],
                  ["plastic", "blue"], ["paint - enamel glossy (blue)"]] + _OPAQUE,
        "color": (46, 74, 122),
        "roughness": 0.2,
    },
    "plastic_black": {
        "label": "Műanyag fekete",
        "match": [["plastic - matte (black)"], ["plastic", "matte", "black"],
                  ["plastic", "black"]] + _OPAQUE,
        "color": (24, 24, 25),
    },
    "plastic_white": {
        "label": "Műanyag fehér",
        "match": [["plastic - matte (white)"], ["plastic", "matte", "white"], ["abs (white)"],
                  ["plastic", "white"]] + _OPAQUE,
        "color": (240, 240, 238),
    },
    "rubber": {
        "label": "Gumi",
        "match": [["rubber - soft"], ["rubber"], ["silicone"], ["plastic - matte (black)"]] + _OPAQUE,
        "color": (26, 26, 28),
    },
    "fan": {
        "label": "Ventilátor",
        "match": [["plastic - matte (gray)"], ["plastic", "matte", "gr"], ["plastic", "gr"],
                  ["plastic - matte (black)"]] + _OPAQUE,
        "color": (50, 52, 56),
    },
    # ── scene ───────────────────────────────────────────────────────────────
    "agar": {
        "label": "Agar",
        "match": [["plastic - translucent glossy (yellow)"], ["plastic", "translucent", "yellow"],
                  ["phenolic (amber)"], ["plastic", "translucent"], ["wax (natural)"]] + _OPAQUE,
        "color": (214, 168, 94),
        "roughness": 0.08,
    },
    "petri": {
        "label": "Petri-csésze",
        "match": [["acrylic (clear)"], ["polycarbonate (clear)"], ["glass (clear)"],
                  ["acrylic"], ["glass", "clear"]] + _CLEAR,
        "color": (248, 249, 250),
    },
}


MATERIALS = {
    # Fusion Material Library: "Aluminum 6061" 2.70 g/cm³.
    "aluminum": [["aluminum 6061"], ["aluminum", "6061"], ["aluminum 6063"], ["aluminum", "alloy"],
                 ["aluminum"]],
    # Fusion has PAEK (the PEEK family, ~1.3 g/cm³) where PEEK itself is missing.
    "peek": [["peek"], ["polyetheretherketone"], ["paek"], ["polyether"], ["polycarbonate"],
             ["acrylic"], ["plastic"]],
    "glass": [["glass"], ["acrylic"], ["polycarbonate"], ["plastic"]],
    # Insert: polyetherimide (ULTEM 1000, 1.27 g/cm³); PC is the nearest library fallback.
    "pei": [["polyetherimide"], ["pei"], ["ultem"], ["polycarbonate"], ["plastic"]],
    "plastic": [["abs plastic"], ["abs"], ["polycarbonate"], ["nylon"], ["plastic"]],
    "steel": [["stainless steel"], ["steel"], ["iron"]],
    "copper": [["copper"], ["brass"], ["bronze"]],
    "fr4": [["fr4"], ["fr-4"], ["fr 4"], ["epoxy"], ["polycarbonate"], ["plastic"]],
    # A solid 21700 (Ø21.4 × 70.3 mm = 25.3 cm³) must weigh ~70 g → 2.7–2.9 g/cm³ = aluminium.
    "battery": [["aluminum 6061"], ["aluminum", "6061"], ["aluminum", "alloy"], ["aluminum"]],
}


# ─────────────────────────────────────────────────────────────────────────────
# tune(): adjust a copied design appearance. Never raises.
# ─────────────────────────────────────────────────────────────────────────────

_logged = set()


def _once(log, key, msg):
    if key in _logged:
        return
    _logged.add(key)
    try:
        log(msg)
    except Exception:
        pass


def _prop(props, ids, names):
    """First property matching an id, then a (case-insensitive) display name substring."""
    for pid in ids:
        try:
            p = props.itemById(pid)
        except Exception:
            p = None
        if p is not None:
            return p
    try:
        n = props.count
    except Exception:
        return None
    for i in range(n):
        try:
            p = props.item(i)
            nm = (p.name or "").lower()
        except Exception:
            continue
        if any(w in nm for w in names):
            return p
    return None


def _ids(props):
    out = []
    try:
        for i in range(props.count):
            try:
                out.append(props.item(i).id)
            except Exception:
                continue
    except Exception:
        pass
    return ", ".join(out)


def _rgb(core, c, a=255):
    return core.Color.create(int(c[0]), int(c[1]), int(c[2]), int(a))


def _cast(cls, p):
    return None if p is None else cls.cast(p)


def _set_color(core, props, ids, names, rgb):
    p = _cast(core.ColorProperty, _prop(props, ids, names))
    if p is None:
        return False
    try:
        if p.isReadOnly:
            return False
    except Exception:
        pass
    p.value = _rgb(core, rgb)
    return True


def _set_float(core, props, ids, names, value):
    p = _cast(core.FloatProperty, _prop(props, ids, names))
    if p is None:
        return False
    v = float(value)
    try:
        if p.hasLimits:
            ok, lo, hi = p.getLimits()
            if ok:
                v = min(max(v, lo), hi)
    except Exception:
        pass
    p.value = v
    return True


def _set_bool(core, props, ids, value):
    p = _cast(core.BooleanProperty, _prop(props, ids, ()))
    if p is None:
        return False
    p.value = bool(value)
    return True


def _has_api(obj, attr):
    """True if the installed Fusion API defines `attr` (Appearance.color / .roughness are 2025+).
    Checked on the class so a missing property is never silently added as a Python attribute."""
    return hasattr(type(obj), attr)


def tune(appearance, spec, core, log):
    label = spec.get("label", "?")
    try:
        props = appearance.appearanceProperties
    except Exception:
        _once(log, (label, "props"), f"  · look '{label}': no appearanceProperties, library look kept")
        return

    def step(what, fn):
        try:
            if not fn():
                _once(log, (label, what),
                      f"  · look '{label}': no {what} property (has: {_ids(props)})")
        except Exception as exc:
            _once(log, (label, what), f"  · look '{label}': {what} not set ({exc})")

    color = spec.get("color")
    if color is not None:
        step("colour", lambda: _set_color(core, props, _COLOR_IDS, _COLOR_NAMES, color))

    rough = spec.get("roughness")
    if rough is not None:
        def set_rough():
            if _has_api(appearance, "roughness"):
                try:
                    appearance.roughness = float(rough)
                    return True
                except Exception:
                    pass
            return _set_float(core, props, _ROUGHNESS_IDS, _ROUGHNESS_NAMES, rough)
        step("roughness", set_rough)

    lum = spec.get("luminance")
    if lum is not None:
        glow = spec.get("glow") or color or (255, 255, 255)
        step("emission switch", lambda: _set_bool(core, props, _EMISSION_ON_IDS, True))
        step("luminance", lambda: _set_float(core, props, _LUMINANCE_IDS, _LUMINANCE_NAMES, lum))
        step("emission colour", lambda: _set_color(core, props, _GLOW_IDS, _GLOW_NAMES, glow))

    alpha = spec.get("alpha")
    if alpha is not None and color is not None and alpha < 255:
        def set_alpha():
            if not _has_api(appearance, "color"):
                return False
            appearance.color = _rgb(core, color, alpha)
            return True
        step("translucency", set_alpha)
