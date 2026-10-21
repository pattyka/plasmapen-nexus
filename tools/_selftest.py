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
    ("st_len", "cone_len + 6 mm", "mm", "teszt"),
    ("st_half", "st_len / 2", "mm", "teszt"),
]


def build_shell(bk, parent, cutaway):
    c = bk.component(parent, "Teszt fej")
    nose = bk.revolve(c, "Orr", [
        ("0 mm", "nozzle_d / 2"), ("st_len", "nozzle_d / 2"), ("st_len", "body_r"),
        ("nose_len", "body_r"), ("spline", [("nose_len / 2", "tip_r + 2 mm"), ("0 mm", "tip_r")]),
    ], look="peek", material="peek")
    bk.fillet(c, "Orr él", nose.body, [("circle", "st_len", "body_r")], "edge_r")
    slot = bk.box_sym(c, "Rés", "nose_len + 2 mm", "nose_len + 6 mm", "body_r - 3 mm",
                      "body_r + 1 mm", "vent_w", op="cut", targets=[nose.body])
    bk.pattern_x(c, "Rések", slot, "vent_count")
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
    print("SELFTEST", "PASS" if good else "FAIL")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
