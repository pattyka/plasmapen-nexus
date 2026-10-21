"""Self-test of preview_backend: a tiny throwaway builder + every rejection rule.

    uv run --python 3.12 --with cadquery --with matplotlib --with numpy python tools/_selftest.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import preview_backend as pb  # noqa: E402
from pp_core import neg  # noqa: E402

EXTRA_PARAMS = [
    ("st_len", "face_x0 + 6 mm", "mm", "teszt"),
    ("st_nose", "face_x0 / 2", "mm", "teszt"),
    ("st_er", "1 mm", "mm", "teszt"),
    ("st_vw", "2 mm", "mm", "teszt"),
    ("st_vc", "6", "", "teszt"),
    ("st_half", "st_len / 2", "mm", "teszt"),
    ("st_cyl_r", "14.5 mm", "mm", "teszt henger sugara"),
    ("st_cyl_len", "40 mm", "mm", "teszt henger hossza"),
    ("st_flat_y", "12.2 mm", "mm", "teszt lapos oldal magassaga"),
    ("st_pk0", "8 mm", "mm", "teszt zseb eleje"),
    ("st_pk1", "32 mm", "mm", "teszt zseb vege"),
    ("st_brk", "0.4 mm", "mm", "teszt elletores"),
    ("st_fr", "0.25 mm", "mm", "teszt lekerekites"),
]


def build_shell(bk, parent, cutaway):
    c = bk.component(parent, "Teszt fej")
    nose = bk.revolve(c, "Orr", [
        ("0 mm", "nozzle_d / 2"), ("st_len", "nozzle_d / 2"), ("st_len", "body_r"),
        ("st_nose", "body_r"), ("spline", [("st_nose / 2", "tip_r0 + 2 mm"), ("0 mm", "tip_r0")]),
    ], look="peek", material="peek")
    bk.fillet(c, "Orr él", nose.body, [("circle", "st_len", "body_r")], "st_er")
    slot = bk.box_sym(c, "Rés", "st_nose + 2 mm", "st_nose + 6 mm", "body_r - 3 mm",
                      "body_r + 1 mm", "st_vw", op="cut", targets=[nose.body])
    bk.pattern_x(c, "Rések", slot, "st_vc")
    if cutaway:
        bk.cut_half(c, "Metszet", [nose.body])
    return [c]


def build_shared(bk, parent):
    c = bk.component(parent, "Teszt LED")
    led = bk.tube_x(c, "LED", "0.2 mm", "0.2 mm + led_h", "led_d / 2", plane_z="0 mm",
                    look="led405", material="glass")
    bk.extrude(c, "Talp", [("0.2 mm + led_h", "-1 mm"), ("2 mm", "-1 mm"), ("2 mm", "1 mm"),
                           ("0.2 mm + led_h", "1 mm")], "-1 mm", "1 mm", look="pcb",
               material="fr4")
    bk.pattern_x(c, "LED-ek", led, "2 * led_pairs")
    btn = bk.revolve(c, "Gomb", [("btn_x - btn_d / 2", "body_r"), ("btn_x + btn_d / 2", "body_r"),
                                 ("btn_x + btn_d / 2", "body_r + btn_proud"),
                                 ("btn_x - btn_d / 2", "body_r + btn_proud")],
                     axis=0, angle="360 deg", look="rubber", material="plastic")
    return [c]


def _n(bk, body, sel):
    """Edges matched, counted as Fusion would: OCC splits an arc where it crosses the seam of a
    revolved face (Fusion bodies have no seams), so arc pieces of one circle count once."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_Circle
    keys = set()
    for i, e in enumerate(bk._collect_edges(body.shape, [bk._sel_values(sel)])):
        ad = BRepAdaptor_Curve(e)
        if ad.GetType() == GeomAbs_Circle:
            c = ad.Circle()
            p = c.Location()
            keys.add(("circle", round(p.X(), 3), round(p.Y(), 3), round(p.Z(), 3),
                      round(c.Radius(), 3)))
        else:
            keys.add(i)
    return len(keys)


def check(label, ok, detail=""):
    print(f"  {'ok ' if ok else 'BAD'} {label}{': ' + detail if detail else ''}")
    return ok


def blend_tests(bk):
    """Flat sliced off a revolved cylinder by an extrude cut, its rim broken by chamfer() /
    fillet() through the ("op_edges", op[, "outer"]) and ("plane_y", y[, side]) selectors."""
    print("chamfer / fillet on a sliced flat:")
    good = True
    c = bk.component(None, "Fazetta teszt")
    big = "st_cyl_r + 2 mm"

    # A — flat through the whole length (the pen's facet)
    a = bk.tube_x(c, "Henger A", "0 mm", "st_cyl_len", "st_cyl_r", look="alu",
                  material="aluminum").body
    flat_a = bk.box(c, "Lapos A", "-1 mm", "st_cyl_len + 1 mm", "st_flat_y", big, neg(big), big,
                    op="cut", targets=[a])
    good &= check("A op_edges = flat rim (2 sides + 2 end chords)",
                  _n(bk, a, ("op_edges", flat_a)) == 4, str(_n(bk, a, ("op_edges", flat_a))))
    good &= check("A op_edges outer = 4", _n(bk, a, ("op_edges", flat_a, "outer")) == 4)
    good &= check("A plane_x 0 = front face rim (arc + chord)",
                  _n(bk, a, ("plane_x", "0 mm")) == 2, str(_n(bk, a, ("plane_x", "0 mm"))))
    good &= check("A minus(op_edges outer, plane_x 0) = 3",
                  _n(bk, a, ("minus", ("op_edges", flat_a, "outer"), ("plane_x", "0 mm"))) == 3)
    good &= check("count st_vc = 6", bk.count("st_vc") == 6)
    area0 = sum(f.Area() for f in bk.op_faces(a, flat_a))
    v0 = a.volume
    ch = bk.chamfer(c, "Fazetta él", a, [("op_edges", flat_a, "outer")], "st_brk")
    good &= check("A chamfer via op_edges outer", ch is not None and a.volume < v0,
                  f"volume {v0:.2f} → {a.volume:.2f} mm³")
    faces = bk.op_faces(a, flat_a)
    area1 = sum(f.Area() for f in faces)
    good &= check("A flat re-resolved after the chamfer (1 face, smaller)",
                  len(faces) == 1 and area1 < area0 - 1e-3, f"{area0:.2f} → {area1:.2f} mm²")
    good &= check("A op_edges outer after chamfer = new rim (4)",
                  _n(bk, a, ("op_edges", flat_a, "outer")) == 4)
    good &= check("A chamfer op_edges = chamfer faces' edges",
                  _n(bk, a, ("op_edges", ch)) > 4 if ch else False)
    v1 = a.volume
    fl = bk.fillet(c, "Fazetta él lekerekítés", a, [("plane_y", "st_flat_y")], "st_fr")
    good &= check("A fillet via plane_y on the chamfered rim", fl is not None and a.volume < v1,
                  f"volume {v1:.2f} → {a.volume:.2f} mm³")

    # B — pocket flat in the middle: the outer filter must drop the flat/wall edges
    xb = "st_cyl_len + 10 mm"  # B and C sit further along X so the render shows all three
    b = bk.tube_x(c, "Henger B", xb, f"{xb} + st_cyl_len", "st_cyl_r", look="alu",
                  material="aluminum").body
    flat_b = bk.box(c, "Lapos B", f"{xb} + st_pk0", f"{xb} + st_pk1", "st_flat_y", big, neg(big),
                    big, op="cut", targets=[b])
    counts = {
        ("op_edges",): (_n(bk, b, ("op_edges", flat_b)), 6),
        ("op_edges", "outer"): (_n(bk, b, ("op_edges", flat_b, "outer")), 4),
        ("plane_y",): (_n(bk, b, ("plane_y", "st_flat_y")), 4),
        ("plane_y", 1): (_n(bk, b, ("plane_y", "st_flat_y", 1)), 1),
        ("plane_y", -1): (_n(bk, b, ("plane_y", "st_flat_y", -1)), 1),
    }
    for k, (got, want) in counts.items():
        good &= check(f"B {' '.join(map(str, k))} = {want}", got == want, f"got {got}")
    v0 = b.volume
    cb = bk.chamfer(c, "Zseb perem", b, [("op_edges", flat_b, "outer")], "st_brk")
    good &= check("B chamfer via op_edges outer (rim only, flat/wall edges stay sharp)",
                  cb is not None and b.volume < v0, f"volume {v0:.2f} → {b.volume:.2f} mm³")

    # C — same pocket, the two long rim edges filleted through plane_y with a side filter
    xc = "2 * (st_cyl_len + 10 mm)"
    d = bk.tube_x(c, "Henger C", xc, f"{xc} + st_cyl_len", "st_cyl_r", look="alu",
                  material="aluminum").body
    bk.box(c, "Lapos C", f"{xc} + st_pk0", f"{xc} + st_pk1", "st_flat_y", big, neg(big), big,
           op="cut", targets=[d])
    v0 = d.volume
    fc = bk.fillet(c, "Zseb oldalél", d, [("plane_y", "st_flat_y", 1),
                                          ("plane_y", "st_flat_y", -1)], "st_brk")
    good &= check("C fillet via plane_y +z and -z (the two long rim edges)",
                  fc is not None and d.volume < v0, f"volume {v0:.2f} → {d.volume:.2f} mm³")

    # selector rejections and the non-fatal path
    tests = [
        ("op_edges bad filter", lambda: bk.chamfer(c, "x", a, [("op_edges", flat_a, "inner")],
                                                   "st_brk"), "bad edge selector"),
        ("op_edges not an Op", lambda: bk.chamfer(c, "x", a, [("op_edges", a)], "st_brk"),
         "needs an op"),
        ("plane_y bad side", lambda: bk.fillet(c, "x", a, [("plane_y", "st_flat_y", 2)],
                                               "st_brk"), "bad edge selector"),
        ("count of a length", lambda: bk.count("st_cyl_r"), "unitless"),
        ("minus arity", lambda: bk.chamfer(c, "x", a, [("minus", ("plane_x", "0 mm"))], "st_brk"),
         "bad edge selector"),
        ("chamfer unitless", lambda: bk.chamfer(c, "x", a, [("plane_y", "st_flat_y")], "0.4"),
         "expected a length"),
    ]
    for label, fn, needle in tests:
        good &= expect(label, fn, needle)
    r = bk.chamfer(c, "semmi", a, [("plane_y", "st_cyl_r + 5 mm")], "st_brk")
    good &= check("chamfer with no matching edge is skipped, not fatal", r is None,
                  bk.fillet_failures[-1])

    try:
        import preview
        os.makedirs(preview.OUT, exist_ok=True)
        path = os.path.join(preview.OUT, "selftest_blend.png")
        scene = preview.collect(bk, c)
        preview.render(scene, path, (1400, 800), {"dir": (-0.45, 0.75, 0.5), "up": (0, 1, 0),
                                                  "zoom": 1.25, "fov": 16}, edges=True)
        print(f"  render → {path}")
    except Exception as ex:  # rendering is a convenience; geometry checks above decide
        good &= check("render", False, f"{type(ex).__name__}: {ex}")
    return good


def expect(label, fn, needle):
    try:
        fn()
    except pb.BuildError as e:
        ok = needle.lower() in str(e).lower()
        print(f"  {'ok ' if ok else 'BAD'} {label}: {e}")
        return ok
    print(f"  BAD {label}: did not raise")
    return False


def main():
    me = sys.modules[__name__]
    bk = pb.PreviewBackend(extra_params=pb.collect_extra_params([me]), quiet=True)
    res = pb.build_model(bk, [me])
    print(pb._summary(bk, res))
    for w in bk.warnings:
        print("WARN", w)
    for f in bk.fillet_failures:
        print("FILLET", f)
    good = not res.errors
    for e in res.errors:
        print("ERROR", e[3], e[4])
    bodies = {b.name: b for b, _, _ in bk.iter_bodies(res.render)}
    n_leds = sum(1 for n in bodies if n.startswith("LED"))
    print(f"  LEDs in render: {n_leds} (expect 6)")
    good &= n_leds == 6
    nose = bodies["Orr"]
    eng = [b for b, _, _ in bk.iter_bodies(res.engineering) if b.name == "Orr"][0]
    print(f"  nose volume whole {nose.volume:.1f}, cut {eng.volume:.1f} (expect ~half)")
    good &= abs(eng.volume / nose.volume - 0.5) < 0.02
    bb = eng.shape.BoundingBox()
    good &= bb.zmax < 1e-6
    print(f"  mass {bk.pen_mass_g():.2f} g")

    print("rejections:")
    c = bk.component(None, "Neg")
    sq = [("0 mm", "0 mm"), ("5 mm", "0 mm"), ("5 mm", "5 mm"), ("0 mm", "5 mm")]
    tests = [
        ("bare number", lambda: bk.box(c, "a", "0 mm", "x", "0 mm", "1 mm", "0 mm", "1 mm"),
         "unknown name"),
        ("x + 2", lambda: bk.box(c, "a", "0 mm", "body_r + 2", "0 mm", "1 mm", "0 mm", "1 mm"),
         "adding"),
        ("literal 0", lambda: bk.box(c, "a", "0", "2 mm", "0 mm", "1 mm", "0 mm", "1 mm"),
         "expected a length"),
        ("python int", lambda: bk.box(c, "a", 0, "2 mm", "0 mm", "1 mm", "0 mm", "1 mm"),
         "expected a length"),
        ("power **", lambda: bk.box(c, "a", "0 mm", "sqrt(body_r**2)", "0 mm", "1 mm",
                                    "0 mm", "1 mm"), "^"),
        ("angle unit", lambda: bk.revolve(c, "a", sq, angle="90"), "expected an angle"),
        ("count unit", lambda: bk.pattern_x(c, "p", bk.box(c, "b", "1 mm", "2 mm", "1 mm",
                                                           "2 mm", "0 mm", "1 mm"), "3 mm"),
         "unitless"),
        ("zero-length", lambda: bk.extrude(c, "a", sq[:2] + [("5 mm", "0 mm")] + sq[2:],
                                           "0 mm", "1 mm"), "zero-length"),
        ("first repeated", lambda: bk.extrude(c, "a", sq + [sq[0]], "0 mm", "1 mm"),
         "zero-length closing"),
        ("duplicate vtx", lambda: bk.extrude(c, "a", [("0 mm", "0 mm"), ("5 mm", "0 mm"),
                                                      ("2 mm", "3 mm"), ("5 mm", "0 mm"),
                                                      ("0 mm", "5 mm")], "0 mm", "1 mm"),
         "duplicate"),
        ("bowtie", lambda: bk.extrude(c, "a", [("0 mm", "0 mm"), ("5 mm", "5 mm"),
                                               ("5 mm", "0 mm"), ("0 mm", "5 mm")],
                                      "0 mm", "1 mm"), "self-intersects"),
        ("crosses axis", lambda: bk.revolve(c, "a", [("0 mm", "-1 mm"), ("5 mm", "-1 mm"),
                                                     ("5 mm", "5 mm"), ("0 mm", "5 mm")]),
         "crosses the x axis"),
        ("cut no targets", lambda: bk.box(c, "a", "0 mm", "1 mm", "0 mm", "1 mm", "0 mm", "1 mm",
                                          op="cut"), "needs targets"),
        ("cut misses", lambda: bk.box(c, "a", "50 mm", "51 mm", "0 mm", "1 mm", "0 mm", "1 mm",
                                      op="cut", targets=[nose]), "does not intersect"),
        ("z1 <= z0", lambda: bk.extrude(c, "a", sq, "1 mm", "1 mm"), "z1 > z0"),
        ("bad look", lambda: bk.extrude(c, "a", sq, "0 mm", "1 mm", look="chrome"),
         "unknown look"),
        ("spline axis", lambda: bk.revolve(c, "a", [("0 mm", "1 mm"), ("spline", [(
            "3 mm", "2 mm"), ("5 mm", "1 mm")]), ("5 mm", "0 mm"), ("0 mm", "0 mm")], axis=0), "spline"),
        ("bad extra", lambda: pb.PreviewBackend(extra_params=[("x", [("x_a", "3", "mm", "")])]),
         "declared unit"),
    ]
    for label, fn, needle in tests:
        good &= expect(label, fn, needle)
    # fillet failure must be non-fatal
    box = bk.box(c, "kocka", "0 mm", "1 mm", "0 mm", "1 mm", "0 mm", "1 mm")
    r = bk.fillet(c, "nagy", box.body, [("line_y", "1 mm", "1 mm")], "5 mm")
    print(f"  {'ok ' if r is None else 'BAD'} oversize fillet logged: {bk.fillet_failures[-1]}")
    good &= r is None
    good &= blend_tests(bk)
    print("SELFTEST", "PASS" if good else "FAIL")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
