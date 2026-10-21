"""PlasmaPen Nexus — full-model check without Fusion.

    cd ~/Documents/PlasmaPen
    uv run --python 3.12 --with cadquery --with matplotlib --with numpy python tools/check.py

Options:
    --quick           skip parameter robustness and the static check
    --no-robust       skip parameter robustness
    --no-static       skip the pyright check of pp_core.FusionBackend / PlasmaPenNexus.py
    --all-lengths     robustness on every literal length parameter ±15 % (PARAMS and the
                      modules' EXTRA_PARAMS) instead of the default short list (body_od, tip_od,
                      cone_len, cp_len, pcb_len, bat_len, standoff ±15 %, led_pairs 2/4,
                      vent_count 8)
    --only pp_head    restrict to some modules (comma separated)
    -j N              robustness worker processes (default: min(4, CPU count - 1))

Builds the model the way PlasmaPenNexus.run() does (see preview_backend.build_model) and
reports: build errors per module, pairwise interference of the pen bodies in the render
assembly, internals outside the bore, bodies outside the pen silhouette, mass against the 280 g
target, length / diameter, ELLENŐRZÉS (chk_*) parameters, robustness under parameter changes,
and a static check of the Fusion code against the adsk stub. Report → tools/out/check_report.txt
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import preview_backend as pb  # noqa: E402
import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402

OUT = os.path.join(HERE, "out")
STUB = "/tmp/pp_adsk/adsk-2.0.12157"
MASS_TARGET = 280.0
TOUCH_TOL = 0.01      # mm³ — overlaps below this count as "designed to touch"

SUBSET = [("body_od", None), ("tip_od", None), ("cone_len", None), ("cp_len", None),
          ("pcb_len", None), ("bat_len", None), ("standoff", None)]
COUNT_VARIANTS = [("led_pairs", "2"), ("led_pairs", "4"), ("vent_count", "8")]


# ─────────────────────────────────────────────────────────────────────────────
# Building
# ─────────────────────────────────────────────────────────────────────────────

def build(only=None, overrides=None, quiet=True):
    mods, imp_err = pb.load_modules(only or pb.BUILDER_MODULES)
    try:
        bk = pb.PreviewBackend(overrides=overrides, extra_params=pb.collect_extra_params(mods),
                               quiet=quiet)
    except pb.ExprError as e:
        return None, None, mods, imp_err, f"{e}"
    res = pb.build_model(bk, mods)
    return bk, res, mods, imp_err, None


def pen_bodies(bk, res):
    """(body, world shape, pen-local shape) for every pen body of the render assembly."""
    out = []
    for b, m, _ in bk.iter_bodies(res.render):
        if b.pen:
            out.append((b, bk.world_shape(b, m)))
    return out


def label(b):
    return f"{b.comp.name}/{b.name}" if b.comp.name != b.name else b.name


def interferences(items, tol=TOUCH_TOL):
    boxes = [pb.fast_bb(s) for _, s in items]
    hits = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if not pb._bb_overlap(boxes[i], boxes[j], 1e-6):
                continue
            try:
                v = abs(items[i][1].intersect(items[j][1]).Volume())
            except Exception as ex:  # OCC boolean trouble is itself worth knowing
                hits.append((float("nan"), items[i][0], items[j][0], f"OCC failed: {ex}"))
                continue
            if v >= tol:
                hits.append((v, items[i][0], items[j][0], ""))
    hits.sort(key=lambda h: -(h[0] if h[0] == h[0] else 1e18))
    return hits


def radial_extent(shape):
    """(max radius from the X axis, x min, x max, max |y|, max |z|) from a fine tessellation."""
    verts, _ = shape.tessellate(0.05, 0.2)
    if not verts:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    a = np.array([(v.x, v.y, v.z) for v in verts])
    r = np.sqrt(a[:, 1] ** 2 + a[:, 2] ** 2)
    return (float(r.max()), float(a[:, 0].min()), float(a[:, 0].max()),
            float(np.abs(a[:, 1]).max()), float(np.abs(a[:, 2]).max()))


# Internals that sit outside the bore by design: the AMOLED panel lies in the unibody wall
# pocket under the display glass and its FPC drops through the pocket opening; the antenna
# coax runs in the groove along the bottom of the bore (pp_body cuts all three).
# Interference against the unibody is still checked for them.
OUTSIDE_BORE_OK = {'OLED 1,1"', "BLE antenna"}


def bore_violations(bk, res):
    """Internals volume outside the bore cylinder + any pen body outside the silhouette.
    Shapes are compared in pen-local coordinates (component space)."""
    ev = bk.ev
    bore = ev.length("bore_r")
    body_r = ev.length("body_r")
    proud = ev.length("btn_proud")
    pen_len = ev.length("pen_len")
    cyl = cq.Solid.makeCylinder(bore, pen_len + 400, cq.Vector(-200, 0, 0), cq.Vector(1, 0, 0))
    out_bore, out_sil = [], []
    for b, _, _ in bk.iter_bodies(res.render):
        if not b.pen:
            continue
        rmax, x0, x1, ymax, zmax = radial_extent(b.shape)
        if b.module == "pp_internals" and b.comp.name not in OUTSIDE_BORE_OK:
            try:
                v = abs(b.shape.cut(cyl).Volume())
            except Exception:
                v = float("nan")
            if v != v or v > TOUCH_TOL:
                out_bore.append((v, rmax, b))
        # silhouette = tube OD everywhere except straight up, where the button may stand
        # btn_proud above it (a flat-topped cap's corners lie outside r, but not above y)
        lim = body_r + 0.05
        if (max(zmax, ymax - proud) > lim and rmax > lim) or x0 < -0.05 or x1 > pen_len + 0.05:
            out_sil.append((b, rmax, x0, x1))
    out_bore.sort(key=lambda t: -t[0] if t[0] == t[0] else -1e18)
    return out_bore, out_sil, bore, body_r, pen_len


def mass_table(bk):
    rows, missing = [], []
    seen = set()
    for b in bk.pen_bodies:
        if not b.valid or id(b) in seen:
            continue
        seen.add(id(b))
        if b.material not in pb.DENSITY:
            missing.append(b)
            continue
        rows.append((b.volume / 1000.0 * pb.DENSITY[b.material], b))
    rows.sort(key=lambda r: -r[0])
    return rows, missing


def chk_params(bk):
    return [(n, q.v) for n, q in bk.ev.q.items() if n.startswith("chk_")]


def short_errors(res, imp_err, perr):
    out = []
    if perr:
        out.append(("params", "", perr))
    for n, tb in imp_err:
        out.append((n, "import", tb.strip().splitlines()[-1]))
    for mod, stage, kind, msg, _ in res.errors if res else []:
        out.append((mod, stage, f"({kind}) {msg}"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Robustness (runs in worker processes)
# ─────────────────────────────────────────────────────────────────────────────

def _variant(args):
    name, expr, only, base_pairs = args
    t = time.time()
    bk, res, mods, imp_err, perr = build(only, {name: expr})
    out = {"name": name, "expr": expr, "errors": short_errors(res, imp_err, perr),
           "warnings": [], "chk": [], "new_hits": [], "out_bore": [], "secs": 0.0}
    if bk is not None:
        out["warnings"] = list(bk.warnings)
        out["chk"] = [(n, v) for n, v in chk_params(bk) if v < 0]
        items = pen_bodies(bk, res)
        for v, a, b, note in interferences(items, 0.5):
            key = tuple(sorted((label(a), label(b))))
            prev = base_pairs.get("|".join(key), 0.0)
            if v != v or v > prev + 0.5:
                out["new_hits"].append((key[0], key[1], v, prev))
        ob, _, _, _, _ = bore_violations(bk, res)
        out["out_bore"] = [(label(b), v) for v, _, b in ob]
    out["secs"] = time.time() - t
    return out


def variants(bk, subset):
    """Every parameter whose expression is a plain 'N mm' literal ±15 %, plus count variants."""
    lit = re.compile(r"^\s*(-?[0-9]*\.?[0-9]+)\s*mm\s*$")
    out = []
    if subset:
        names = [n for n, _ in SUBSET]
    else:
        names = []
        for n, expr, unit, _ in pb.PARAMS:
            if unit == "mm" and lit.match(expr):
                names.append(n)
    exprs = {p[0]: p[1] for p in pb.PARAMS}
    for n in names:
        if n not in exprs or not lit.match(exprs[n]):
            continue
        m = lit.match(exprs[n])
        v = float(m.group(1))
        for f in (0.85, 1.15):
            out.append((n, f"{v * f:.4g} mm"))
    if not subset:
        # literal lengths among the modules' EXTRA_PARAMS too
        for n, src in bk.ev.sources.items():
            if src == "pp_params":
                continue
            # find the original expression
            for mod in sys.modules.values():
                for item in getattr(mod, "EXTRA_PARAMS", []) if getattr(
                        mod, "__name__", "") == src else []:
                    if item[0] == n and item[2] == "mm" and lit.match(item[1]):
                        v = float(lit.match(item[1]).group(1))
                        for f in (0.85, 1.15):
                            out.append((n, f"{v * f:.4g} mm"))
    out += COUNT_VARIANTS
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Static check
# ─────────────────────────────────────────────────────────────────────────────

# Members that exist in today's Fusion API but not in the 2021 stub (2.0.12157).
NEWER_API = {
    "edgeSetInputs": "FilletFeatureInput.edgeSetInputs (2023+)",
    "defineAsRotate": "MoveFeatureInput.defineAsRotate (2022+)",
    "defineAsTranslateXYZ": "MoveFeatureInput.defineAsTranslateXYZ (2022+)",
    "defineAsFreeMove": "MoveFeatureInput.defineAsFreeMove (2022+)",
    "namedViews": "Design.namedViews (2022+)",
    "addConstantRadiusEdgeSet": "FilletEdgeSetInputs.addConstantRadiusEdgeSet (2023+)",
    "roughness": "Appearance.roughness (2025+, guarded by pp_looks._has_api)",
    "color": "Appearance.color (2025+, guarded by pp_looks._has_api)",
}

ANNOTATE_CORE = [
    # (bare parameter name regex, annotation) — applied inside class FusionBackend only
    (r"comp", "adsk.fusion.Component"),
    (r"parent", "adsk.fusion.Component | None"),
    (r"sk", "adsk.fusion.Sketch"),
    (r"sp", "adsk.fusion.SketchPoint"),
    (r"body", "adsk.fusion.BRepBody"),
    (r"app", "adsk.core.Application"),
    (r"design", "adsk.fusion.Design"),
    (r"feature", "adsk.fusion.ExtrudeFeature | adsk.fusion.RevolveFeature"),
    (r"inp", "adsk.fusion.ExtrudeFeatureInput | adsk.fusion.RevolveFeatureInput"),
    (r"transform", "adsk.core.Matrix3D | None"),
]
ANNOTATE_LOOKS = [
    (r"appearance", "adsk.core.Appearance"),
    (r"props", "adsk.core.Properties"),
]
# Parameters the real API documents as optional although the stub lists them as required.
KNOWN_OPTIONAL = {"occurrenceForCreation", "visible", "options"}


def _annotate(src, rules, scope=None):
    """Typed copy of a module for pyright: annotate the adsk-handle parameters of every def
    (inside `class <scope>` only, if given) and import adsk at module level (the real files
    import it lazily)."""
    out = []
    inside = scope is None
    for line in src.splitlines():
        if scope is not None and re.match(r"^class \w+", line):
            inside = line.startswith(f"class {scope}")
        m = re.match(r"^(\s*def \w+\()(.*)(\):.*)$", line)
        if m and inside:
            params = []
            for p in m.group(2).split(","):
                ps = p.strip()
                bare = ps.split("=")[0].strip()
                if ":" not in ps and bare != "self":
                    for rx, ann in rules:
                        if re.fullmatch(rx, bare):
                            if "=" in ps:
                                ps = f"{bare}: {ann} = {ps.split('=', 1)[1].strip()}"
                            else:
                                ps = f"{bare}: {ann}"
                            break
                params.append(ps)
            line = m.group(1) + ", ".join(params) + m.group(3)
        out.append(line)
    return "import adsk.core\nimport adsk.fusion\n" + "\n".join(out) + "\n"


def _stub_optional_params():
    """Parameter names whose stub docstring calls them optional."""
    names = set(KNOWN_OPTIONAL)
    for fn in ("core.py", "fusion.py"):
        path = os.path.join(STUB, "adsk", fn)
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            m = re.match(r"^\s+(\w+) : (.*)$", line)
            if m and re.search(r"\boptional\b", m.group(2), re.I):
                names.add(m.group(1))
    return names


def static_check():
    if not os.path.isdir(os.path.join(STUB, "adsk")):
        return None, f"stub not found at {STUB}"
    tmp = tempfile.mkdtemp(prefix="pp_static_")
    nexus = pb.NEXUS
    files = []
    for fn in ("pp_core.py", "PlasmaPenNexus.py", "pp_looks.py"):
        src_path = os.path.join(nexus, fn)
        if not os.path.exists(src_path):
            continue
        src = open(src_path, encoding="utf-8").read()
        if fn == "pp_core.py":
            src = _annotate(src, ANNOTATE_CORE, "FusionBackend")
        elif fn == "pp_looks.py":
            src = _annotate(src, ANNOTATE_LOOKS)
        else:
            src = "import adsk.core\nimport adsk.fusion\n" + src
        with open(os.path.join(tmp, fn), "w", encoding="utf-8") as f:
            f.write(src)
        files.append(fn)
    for fn in os.listdir(nexus):
        if fn.endswith(".py") and fn not in files:
            shutil.copy(os.path.join(nexus, fn), tmp)
    cfg = {"extraPaths": [STUB], "include": files, "typeCheckingMode": "basic",
           "pythonVersion": "3.12", "reportMissingModuleSource": "none",
           "reportAttributeAccessIssue": "error", "reportCallIssue": "error",
           "reportArgumentType": "error", "reportOptionalMemberAccess": "none",
           "reportPossiblyUnbound": "warning"}
    with open(os.path.join(tmp, "pyrightconfig.json"), "w") as f:
        json.dump(cfg, f)
    cmds = [["uvx", "pyright", "--outputjson"], ["npx", "-y", "pyright", "--outputjson"]]
    data = None
    err = ""
    for cmd in cmds:
        try:
            p = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=600)
            data = json.loads(p.stdout)
            break
        except Exception as ex:
            err += f"{' '.join(cmd)}: {ex}\n"
    if data is None:
        return None, "pyright did not run:\n" + err
    findings = []
    for d in data.get("generalDiagnostics", []):
        fn = os.path.basename(d["file"])
        line = d["range"]["start"]["line"] + 1
        msg = d["message"].replace("\n", " ").replace(" ", " ")
        src_line = ""
        try:
            src_line = open(d["file"], encoding="utf-8").read().splitlines()[line - 1].strip()
        except Exception:
            pass
        line -= 2  # the two added import lines
        findings.append({"file": fn, "line": line, "sev": d["severity"],
                         "rule": d.get("rule", ""), "msg": msg, "src": src_line})
    return findings, tmp


def classify(findings):
    newer, stub_gap, real = [], [], []
    optional = _stub_optional_params()
    for f in findings:
        miss = re.search(r'Arguments? missing for parameters? (.*)', f["msg"])
        if miss:
            missing = re.findall(r'"(\w+)"', miss.group(1))
            if missing and all(p in optional for p in missing):
                stub_gap.append((f, "optional in the real API; the stub drops defaults"))
                continue
        if re.search(r'"int" is not assignable to "\w+"', f["msg"]):
            stub_gap.append((f, "stub enums are plain ints"))
            continue
        m = re.search(r'Cannot (?:access|assign to) attribute "(\w+)"', f["msg"]) or re.search(
            r'"(\w+)" is not a known attribute', f["msg"])
        name = m.group(1) if m else None
        if name in NEWER_API:
            newer.append((f, NEWER_API[name]))
        elif "is not iterable" in f["msg"] or '"__iter__" method not defined' in f["msg"]:
            stub_gap.append((f, "stub collections lack __iter__; real Fusion collections iterate"))
        elif f["sev"] == "error":
            real.append(f)
        else:
            stub_gap.append((f, f["sev"]))
    return newer, stub_gap, real


# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────

class Report:
    def __init__(self):
        self.lines = []

    def __call__(self, s=""):
        print(s, flush=True)
        self.lines.append(s)

    def h(self, s):
        self("")
        self(f"━━ {s} " + "━" * max(0, 76 - len(s)))

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-robust", action="store_true")
    ap.add_argument("--no-static", action="store_true")
    ap.add_argument("--all-lengths", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("-j", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1)))
    a = ap.parse_args()
    only = [s.strip() for s in a.only.split(",") if s.strip()] or None
    os.makedirs(OUT, exist_ok=True)
    R = Report()
    t0 = time.time()

    present = [m for m in pb.BUILDER_MODULES
               if os.path.exists(os.path.join(pb.NEXUS, m + ".py"))]
    R(f"PlasmaPen Nexus check — modules present: {', '.join(present) or 'none'}"
      f"{'  (only ' + ', '.join(only) + ')' if only else ''}")
    missing = [m for m in pb.BUILDER_MODULES if m not in present]
    if missing:
        R(f"missing modules: {', '.join(missing)}")

    bk, res, mods, imp_err, perr = build(only)
    R.h("Build")
    if perr:
        R(f"PARAMETER ERROR: {perr}")
    for n, tb in imp_err:
        R(f"✗ {n}: import failed\n{tb}")
    if bk is None:
        R.save(os.path.join(OUT, "check_report.txt"))
        return 1
    stages = {}
    for mod, stage, kind, msg, tb in res.errors:
        stages.setdefault(mod, []).append((stage, kind, msg, tb))
    for m in mods:
        n_b = sum(1 for b, _, _ in bk.iter_bodies(res.render) if b.module == m.__name__)
        if m.__name__ in stages:
            for stage, kind, msg, tb in stages[m.__name__]:
                R(f"✗ {m.__name__}.{stage}  [{kind}]  {msg}")
                R("    " + "\n    ".join(tb.strip().splitlines()[-8:]))
        else:
            R(f"✓ {m.__name__}  ({n_b} bodies in the render assembly)")
    if bk.warnings:
        R(f"warnings ({len(bk.warnings)}):")
        for w in bk.warnings:
            R(f"  · {w}")
    if bk.fillet_failures:
        R(f"fillets skipped in preview ({len(bk.fillet_failures)}; cosmetic, Fusion may "
          "succeed):")
        for f in bk.fillet_failures:
            R(f"  · {f}")

    items = pen_bodies(bk, res)
    R.h(f"Interference — {len(items)} pen bodies, render assembly (≥ {TOUCH_TOL} mm³)")
    hits = interferences(items)
    base_pairs = {}
    if not hits:
        R("none")
    for v, b1, b2, note in hits:
        key = "|".join(sorted((label(b1), label(b2))))
        base_pairs[key] = v if v == v else 1e9
        R(f"  {v:10.3f} mm³  {label(b1)}  ×  {label(b2)}  {note}")

    R.h("Bore / silhouette")
    ob, osil, bore, body_r, pen_len = bore_violations(bk, res)
    if not ob:
        R(f"internals: all inside the bore (r ≤ {bore:g} mm)")
    for v, rmax, b in ob:
        R(f"  internals outside bore: {label(b)}  {v:.3f} mm³ outside, r_max {rmax:.2f} "
          f"(bore {bore:g})")
    if not osil:
        R(f"silhouette: every pen body within r ≤ body_r + btn_proud and 0 ≤ x ≤ pen_len")
    for b, rmax, x0, x1 in osil:
        R(f"  outside silhouette: {label(b)}  r_max {rmax:.2f}, x {x0:.2f} … {x1:.2f}")

    R.h("Mass")
    rows, nomat = mass_table(bk)
    total = sum(r[0] for r in rows)
    by_mat = {}
    for g, b in rows:
        by_mat[b.material] = by_mat.get(b.material, 0) + g
    R(f"total {total:.1f} g   target {MASS_TARGET:.0f} g   ({total - MASS_TARGET:+.1f} g)")
    R("by material: " + ", ".join(f"{k} {v:.1f}" for k, v in sorted(by_mat.items(),
                                                                    key=lambda kv: -kv[1])))
    R("heaviest: " + ", ".join(f"{label(b)} {g:.1f}" for g, b in rows[:8]))
    if nomat:
        R(f"no material (Fusion falls back to its default, usually Steel — mass wrong): "
          + ", ".join(label(b) for b in nomat))

    R.h("Size")
    if items:
        lo = np.array([1e9] * 3)
        hi = -lo
        rmax_all = 0.0
        for b, _ in items:
            bb = b.shape.BoundingBox()
            lo = np.minimum(lo, [bb.xmin, bb.ymin, bb.zmin])
            hi = np.maximum(hi, [bb.xmax, bb.ymax, bb.zmax])
            if (b.stage or "").startswith("build_shell"):
                rmax_all = max(rmax_all, radial_extent(b.shape)[0])
        R(f"length {hi[0] - lo[0]:.2f} mm (x {lo[0]:.2f} … {hi[0]:.2f}; pen_len = "
          f"{pen_len:.2f})   shells max Ø {2 * rmax_all:.2f} mm (body_od = {2 * body_r:g})")
    for n, v in chk_params(bk):
        R(f"{n} = {v:+.3f} mm {'OK' if v >= 0 else '✗ NEGATIVE'}")

    if not (a.quick or a.no_robust):
        vs = variants(bk, not a.all_lengths)
        R.h(f"Robustness — {len(vs)} variants, one parameter at a time")
        jobs = [(n, e, only, base_pairs) for n, e in vs]
        results = []
        with cf.ProcessPoolExecutor(max_workers=a.j) as ex:
            for r in ex.map(_variant, jobs):
                results.append(r)
        base_warn = set(bk.warnings)
        fails = 0
        for r in results:
            new_w = [w for w in r["warnings"] if w not in base_warn]
            bad = r["errors"] or r["chk"] or r["new_hits"] or r["out_bore"]
            if not bad and not new_w:
                continue
            fails += 1 if bad else 0
            R(f"{'✗' if bad else '·'} {r['name']} = {r['expr']}")
            for mod, stage, msg in r["errors"]:
                R(f"    {mod}.{stage}: {msg[:300]}")
            for n, v in r["chk"]:
                R(f"    {n} = {v:+.3f} mm")
            for a_, b_, v, prev in r["new_hits"]:
                R(f"    new interference {a_} × {b_}: {v:.2f} mm³ (default {prev:.2f})")
            for n, v in r["out_bore"]:
                R(f"    outside bore: {n} {v:.2f} mm³")
            for w in new_w[:4]:
                R(f"    warn: {w[:200]}")
        ok = [f"{r['name']}={r['expr']}" for r in results if not (
            r["errors"] or r["chk"] or r["new_hits"] or r["out_bore"])]
        R(f"{len(ok)}/{len(results)} variants clean; {fails} broken "
          f"({sum(r['secs'] for r in results):.0f} s CPU)")

    if not (a.quick or a.no_static):
        R.h("Static check — FusionBackend + PlasmaPenNexus.py vs adsk stub 2.0.12157 (pyright)")
        findings, tmp = static_check()
        if findings is None:
            R(tmp)
        else:
            newer, gap, real = classify(findings)
            R(f"{len(real)} real problems, {len(newer)} verify-on-Fusion, {len(gap)} stub gaps")
            for f in real:
                R(f"  ✗ {f['file']}:{f['line']}  {f['msg']}")
                R(f"      {f['src']}")
            if newer:
                R("verify on real Fusion (newer than the stub):")
                for f, why in newer:
                    R(f"  ? {f['file']}:{f['line']}  {why}  — {f['src']}")
            if gap:
                R("stub gaps / warnings (not errors):")
                for f, why in gap:
                    R(f"  · {f['file']}:{f['line']}  {f['msg'][:140]}  [{why}]")
            R(f"(typed copy in {tmp})")

    R(f"\n{time.time() - t0:.0f} s")
    R.save(os.path.join(OUT, "check_report.txt"))
    return 1 if res.errors or imp_err else 0


if __name__ == "__main__":
    sys.exit(main())
