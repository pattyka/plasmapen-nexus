"""PlasmaPen Nexus — builds the parametric Fusion model.

Fusion: Utilities → Add-Ins → Scripts and Add-Ins → "+" → pick this folder → Run.
Every run opens a NEW design; nothing existing is touched.

One design, two assemblies:
    PlasmaPen Nexus — működés     pen pointing down at an agar plate, plasma on, LEDs glowing
    PlasmaPen Nexus — engineering same pen lying flat, shells cut in half, internals visible
Internal parts are shared components, so both assemblies always show the same hardware.
Edit anything in Modify → Change Parameters; both assemblies follow.
"""

import importlib
import math
import os
import sys
import time
import traceback

import adsk.core
import adsk.fusion

HERE = os.path.dirname(os.path.realpath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Reload order matters: pp_core does `from pp_params import PARAMS`.
_MODULES = ["pp_params", "pp_core", "pp_looks", "pp_head", "pp_body", "pp_internals", "pp_scene"]

RENDER_NAME = "PlasmaPen Nexus — működés"
ENG_NAME = "PlasmaPen Nexus — engineering"


def _load_modules():
    mods = {}
    for name in _MODULES:
        if name in sys.modules:
            mods[name] = importlib.reload(sys.modules[name])
        else:
            mods[name] = importlib.import_module(name)
    return mods


class _Log:
    def __init__(self):
        self.lines = []
        self.t0 = time.time()

    def __call__(self, msg):
        self.lines.append(f"{time.time() - self.t0:6.1f}s  {msg}")

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")


def _create_parameters(design, mods, log):
    """PARAMS first, then each builder's EXTRA_PARAMS. Expressions stay live; if Fusion rejects
    one, the evaluated number is stored instead and the miss is logged."""
    from pp_core import ExprEval

    table = list(mods["pp_params"].PARAMS)
    # pp_body first: pp_head reuses the unibody inner surface (body_* params).
    for m in ("pp_body", "pp_head", "pp_internals", "pp_scene"):
        table += list(getattr(mods[m], "EXTRA_PARAMS", []))

    params = design.userParameters
    local = ExprEval()
    for name, expr, unit, comment in table:
        if params.itemByName(name):
            continue
        try:
            local.values[name] = local(expr)
        except Exception:
            local.values.pop(name, None)
        try:
            params.add(name, adsk.core.ValueInput.createByString(expr), unit, comment)
            continue
        except Exception:
            pass
        try:
            v = local.values[name]
            literal = f"{v:.4f} {unit}".strip() if unit != "deg" else f"{math.degrees(v):.4f} deg"
            params.add(name, adsk.core.ValueInput.createByString(literal), unit, comment)
            log(f"  · {name}: Fusion rejected '{expr}', stored {literal}")
        except Exception:
            log(f"  ✗ {name}: could not create\n{traceback.format_exc(limit=1)}")
            raise
    log(f"{len(table)} parameters")
    return len(table)


def _frames(app, design):
    """Render assembly: pen axis vertical, tip down onto the dish. Engineering: lying flat
    beside it, cut face toward the default front view. Handles Y-up and Z-up documents."""
    um = design.unitsManager
    P = adsk.core.Point3D.create
    V = adsk.core.Vector3D.create
    lift = um.evaluateExpression("standoff + agar_t + dish_wall", "mm")
    dx = um.evaluateExpression("dish_d / 2 + 45 mm", "mm")
    r = um.evaluateExpression("body_r", "mm")
    z_up = (app.preferences.generalPreferences.defaultModelingOrientation
            == adsk.core.DefaultModelingOrientations.ZUpModelingOrientation)
    render = adsk.core.Matrix3D.create()
    eng = adsk.core.Matrix3D.create()
    if z_up:
        render.setWithCoordinateSystem(P(0, 0, lift), V(0, 0, 1), V(0, -1, 0), V(1, 0, 0))
        eng.setWithCoordinateSystem(P(dx, 0, r), V(1, 0, 0), V(0, 0, 1), V(0, -1, 0))
    else:
        render.setWithCoordinateSystem(P(0, lift, 0), V(0, 1, 0), V(0, 0, 1), V(1, 0, 0))
        eng.setWithCoordinateSystem(P(dx, r, 0), V(1, 0, 0), V(0, 1, 0), V(0, 0, 1))
    return render, eng


def _step(log, failures, label, fn, *args):
    t = time.time()
    try:
        out = fn(*args)
        log(f"✓ {label} ({time.time() - t:.1f}s)")
        return out or []
    except Exception:
        failures.append(label)
        log(f"✗ {label}\n{traceback.format_exc()}")
        return []


def _named_views(app, design, log):
    try:
        vp = app.activeViewport
        vp.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
        vp.fit()
        views = design.namedViews
        views.add(vp.camera, "Működés + engineering")
    except Exception:
        log("  · named view not created (older Fusion API)")


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    log = _Log()
    failures = []
    progress = None
    try:
        mods = _load_modules()
        from pp_core import FusionBackend

        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = \
            adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        try:
            design.rootComponent.name = "PlasmaPen Nexus"
        except Exception:
            pass

        progress = ui.createProgressDialog()
        progress.isCancelButtonShown = False
        progress.show("PlasmaPen Nexus", "%v / %m", 0, 9, 0)

        n_params = _create_parameters(design, mods, log)
        progress.progressValue = 1

        bk = FusionBackend(app, design, log)
        t_render, t_eng = _frames(app, design)
        render = bk.component(None, RENDER_NAME, t_render)
        eng = bk.component(None, ENG_NAME, t_eng)

        head, body = mods["pp_head"], mods["pp_body"]
        internals, scene = mods["pp_internals"], mods["pp_scene"]

        _step(log, failures, "Fej", head.build_shell, bk, render, False)
        progress.progressValue = 2
        _step(log, failures, "Test + kupak", body.build_shell, bk, render, False)
        progress.progressValue = 3
        shared = []
        shared += _step(log, failures, "Optika (üveg, LED, kamera)", head.build_shared, bk, render)
        progress.progressValue = 4
        shared += _step(log, failures, "Kristály + gomb", body.build_shared, bk, render)
        shared += _step(log, failures, "Belső alkatrészek", internals.build_shared, bk, render)
        progress.progressValue = 5
        _step(log, failures, "Plazma + petri-csésze", scene.build_scene, bk, render)
        progress.progressValue = 6

        bk.count_mass = False
        _step(log, failures, "Fej metszet", head.build_shell, bk, eng, True)
        _step(log, failures, "Test metszet", body.build_shell, bk, eng, True)
        progress.progressValue = 7
        for comp in shared:
            try:
                bk.add_existing(eng, comp)
            except Exception:
                failures.append(f"engineering: {comp.name}")
                log(f"✗ engineering occurrence {comp.name}\n{traceback.format_exc()}")
        progress.progressValue = 8

        _named_views(app, design, log)
        um = design.unitsManager
        mass = bk.pen_mass_g()
        length = um.evaluateExpression("pen_len", "mm") * 10
        diameter = um.evaluateExpression("body_od", "mm") * 10
        margin = um.evaluateExpression("chk_bore", "mm") * 10
        log(f"pen: {length:.1f} × Ø{diameter:.1f} mm, {mass:.0f} g (target 280 g), "
            f"module clearance {margin:+.2f} mm")
        progress.progressValue = 9
        progress.hide()
        progress = None

        log_path = os.path.join(HERE, "build_log.txt")
        log.save(log_path)
        head_line = f"{length:.0f} × Ø{diameter:.0f} mm · {mass:.0f} g · {n_params} paraméter"
        if margin < 0:
            head_line += f"\nA CeraPlas modul sarka {-margin:.2f} mm-rel kilóg a furatból."
        if failures:
            ui.messageBox(head_line + "\n\nNem épült meg: " + ", ".join(failures) +
                          f"\n\nRészletek: {log_path}", "PlasmaPen Nexus")
        else:
            ui.messageBox(head_line, "PlasmaPen Nexus")
    except Exception:
        if progress:
            progress.hide()
        log(traceback.format_exc())
        log.save(os.path.join(HERE, "build_log.txt"))
        ui.messageBox("PlasmaPen Nexus: a script megállt.\n\n" + traceback.format_exc(),
                      "PlasmaPen Nexus")
