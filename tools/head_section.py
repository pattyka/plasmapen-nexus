"""PEEK nose + liner half-section and nose front view, with wall / clearance / HV checks.

    uv run --python 3.12 --with matplotlib python tools/head_section.py [name=value ...]

Evaluates pp_head's own profiles through pp_core.ExprEval (overrides like cam_mod="4.8 mm"
may be passed as name=value), prints every wall / clearance and writes
tools/out/head_section.png. If pp_body has no inner_profile_pts() yet, a stand-in is used
(and said so).
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "PlasmaPenNexus")
sys.path.insert(0, SRC)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

import pp_body  # noqa: E402

STANDIN = not hasattr(pp_body, "inner_profile_pts")
if STANDIN:
    def _standin():
        return [("nose_len", "tip_r + 0.05 mm"), ("nose_len + 2 mm", "tip_r + 0.05 mm"),
                ("taper_x1", "bore_r"), ("head_len", "bore_r")]
    pp_body.inner_profile_pts = _standin

import pp_core  # noqa: E402
import pp_head as H  # noqa: E402


def evaluator(overrides):
    ev = pp_core.ExprEval(overrides)
    extra = []
    for m in (pp_body,):
        extra += list(getattr(m, "EXTRA_PARAMS", []))
    for name, expr, _unit, _ in extra + list(H.EXTRA_PARAMS):
        try:
            ev.values[name] = ev(overrides.get(name, expr))
        except Exception:
            pass
    return ev


def flatten(E, items):
    out = []
    for item in items:
        if item[0] == "spline":
            out += [(E(x), E(y)) for x, y in item[1]]
        else:
            out.append((E(item[0]), E(item[1])))
    return out


def fillet_polygon(pts, fillets, n=16):
    out = []
    m = len(pts)
    for i, p in enumerate(pts):
        if i not in fillets:
            out.append(p)
            continue
        R = fillets[i]
        a, b = pts[i - 1], pts[(i + 1) % m]
        u = (a[0] - p[0], a[1] - p[1])
        v = (b[0] - p[0], b[1] - p[1])
        lu, lv = math.hypot(*u), math.hypot(*v)
        u, v = (u[0] / lu, u[1] / lu), (v[0] / lv, v[1] / lv)
        ang = math.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1])))
        t = R / math.tan(ang / 2)
        p1 = (p[0] + u[0] * t, p[1] + u[1] * t)
        p2 = (p[0] + v[0] * t, p[1] + v[1] * t)
        bis = (u[0] + v[0], u[1] + v[1])
        lb = math.hypot(*bis)
        d = R / math.sin(ang / 2)
        c = (p[0] + bis[0] / lb * d, p[1] + bis[1] / lb * d)
        a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
        a2 = math.atan2(p2[1] - c[1], p2[0] - c[0])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        out += [(c[0] + R * math.cos(a1 + da * k / n), c[1] + R * math.sin(a1 + da * k / n))
                for k in range(n + 1)]
    return out


def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def chain_dist(p, chain):
    return min(seg_dist(p, a, b) for a, b in zip(chain, chain[1:]))


def main():
    overrides = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    E = evaluator(overrides)
    if STANDIN:
        print("!! pp_body.inner_profile_pts missing — using a straight stand-in")
    raw = flatten(E, H.shell_profile())
    assert len(set(raw)) == len(raw), "duplicate vertex"
    i_back = raw.index((E("head_len"), E("liner_ri")))
    i_nose = raw.index((0.0, E("head_nose_r0")))
    poly = fillet_polygon(raw, {i_nose: E("head_nose_fillet")})
    inner = raw[0:i_back + 1]
    outer = raw[i_back + 1:i_nose + 1]
    alu = flatten(E, pp_body.inner_profile_pts())
    # wall
    best = (1e9, None, None)
    for a, b in zip(inner, inner[1:]):
        for k in range(200):
            p = (a[0] + (b[0] - a[0]) * k / 199, a[1] + (b[1] - a[1]) * k / 199)
            d = chain_dist(p, outer)
            if d < best[0]:
                best = (d, p)
    print(f"PEEK wall min (bore/funnel ↔ outside): {best[0]:.3f} mm at "
          f"({best[1][0]:.2f}, {best[1][1]:.2f})")
    gap = min(chain_dist(p, alu) for p in outer if p[0] >= E("nose_len") - 1e-9)
    print(f"PEEK ↔ alu inner surface min: {gap:.3f} mm")
    nr, lr = E(H.NOZZLE_R), E("liner_ri")
    print(f"collar {E('collar_r') - nr:.2f}, rim {E('tip_r') - E('win_ro'):.2f}, "
          f"chk_bore {E('chk_bore'):.3f}")
    x_n, x_f = E("nozzle_len"), E("funnel_x1")

    def r_in(x):
        if x <= x_n:
            return nr
        return nr + (lr - nr) * min(1.0, (x - x_n) / (x_f - x_n))

    tipc = math.hypot(E("cp_w / 2"), E("cp_h / 2"))
    print(f"bar tip corner ↔ funnel at x={E('cp_x0'):.1f}: {r_in(E('cp_x0')) - tipc:.3f} mm")

    ring, lens_r, seat = E("ring_r"), E(H.CAM_LENS_R), E(H.CAM_SEAT)
    cx0, cx1, wt = E("head_cam_x0"), E(H.CAM_X1), E("win_t")
    xs_seat = [cx0 + (cx1 - cx0) * i / 100 for i in range(101)]
    corner = math.hypot(ring + seat, seat)
    seat_noz = min(ring - seat - r_in(x) for x in xs_seat)
    seat_out = min(chain_dist((x, corner), outer) for x in xs_seat)
    print(f"camera seat x {cx0:.3f}…{cx1:.3f}: seat ↔ nozzle/funnel {seat_noz:.3f}, "
          f"seat corner (ρ {corner:.3f}) ↔ outside {seat_out:.3f} "
          f"{'(BREAKS THROUGH)' if corner > E('tip_r') else ''}, head_chk_cam {E('head_chk_cam'):.3f}")
    print(f"lens bore ↔ nozzle {ring - lens_r - nr:.3f}, ↔ outside {E('tip_r') - ring - lens_r:.3f},"
          f" in window r {ring - lens_r:.2f}…{ring + lens_r:.2f} of {E('collar_r'):.2f}…"
          f"{E('win_ro'):.2f}")
    n = int(E("led_pairs"))
    led_r = E(H.LED_POCKET_R)
    print(f"LED pocket ↔ lens bore {2 * ring * math.sin(math.pi / (4 * n)) - led_r - lens_r:.3f}"
          f", LED back x {E(H.LED_POCKET_X1):.2f} vs seat front {cx0:.2f}")
    print(f"camera body x {E(H.CAM_BODY_X0):.2f}…{E(H.CAM_BODY_X1):.2f}, pcb …{E(H.CAM_PCB_X1):.2f}")
    bar_top = E("cp_h / 2")
    print(f"seat back-bottom corner ↔ bar tip: "
          f"{math.hypot(cx1 - E('cp_x0'), ring - seat - bar_top):.2f} mm")
    wy0, wy1, wh = E("head_wire_y0"), E("head_wire_y1"), E(H.WIRE_HALF)
    wc = math.hypot(wy1, wh)
    wout = min(chain_dist((x, wc), outer) for x in
               [cx0 + i * 0.25 for i in range(int((E("head_len") - cx0) / 0.25))])
    print(f"wire channel y {wy0:.2f}…{wy1:.2f} z ±{wh:.2f}: PEEK under {wy0 - lr:.2f} "
          f"(head_chk_hv {E('head_chk_hv'):.2f}), channel ↔ bar {wy0 - bar_top:.2f} "
          f"(air {lr - bar_top:.2f}), corner ↔ outside min {wout:.3f}")

    fig = plt.figure(figsize=(16, 8), dpi=140)
    ax = fig.add_axes([0.04, 0.45, 0.92, 0.5])
    az = fig.add_axes([0.04, 0.04, 0.58, 0.36])
    af = fig.add_axes([0.66, 0.04, 0.30, 0.36])
    peek, glass, alu_c = "#2b2b2e", "#9fa8ff", "#c8ccd2"
    for a in (ax, az):
        a.add_patch(Polygon(alu + [(alu[-1][0], E("body_r")), (alu[0][0], E("body_r"))],
                            closed=True, fc=alu_c, ec="#888", lw=0.4, alpha=0.6))
        for sgn in (1, -1):
            a.add_patch(Polygon([(x, sgn * y) for x, y in poly], closed=True, fc=peek,
                                ec="k", lw=0.5))
            a.add_patch(Rectangle((0, sgn * E("collar_r") if sgn > 0 else -E("win_ro")), wt,
                                  E("win_ro") - E("collar_r"), fc=glass, lw=0.3, ec="k"))
        a.add_patch(Rectangle((wt, ring - lens_r), cx1 - wt, 2 * lens_r, fc="w", ec="r", lw=0.4))
        a.add_patch(Rectangle((cx0, ring - seat), cx1 - cx0, 2 * seat, fc="w", ec="r", lw=0.4))
        a.add_patch(Rectangle((cx0, wy0), E("head_len") - cx0, wy1 - wy0, fc="w", ec="r",
                              lw=0.4))
        bar = [(E(x), E(y)) for x, y in H.camera_barrel_profile()]
        a.add_patch(Polygon(bar, closed=True, fc="#111", lw=0))
        a.add_patch(Polygon([(x, 2 * ring - y) for x, y in bar], closed=True, fc="#111", lw=0))
        a.add_patch(Rectangle((E(H.CAM_GLASS_X0), ring - E(H.CAM_GLASS_R)),
                              E("head_cam_glass_t"), 2 * E(H.CAM_GLASS_R), fc="#4cc3ff", lw=0))
        hm = E("cam_mod / 2")
        a.add_patch(Rectangle((E(H.CAM_BODY_X0), ring - hm),
                              E(H.CAM_BODY_X1) - E(H.CAM_BODY_X0), 2 * hm, fc="#444", lw=0))
        a.add_patch(Rectangle((E(H.CAM_BODY_X1), ring - hm), E("head_cam_pcb_t"), 2 * hm,
                              fc="#2e7d32", lw=0))
        a.add_patch(Rectangle((E("cp_x0"), -bar_top), E("cp_len"), 2 * bar_top, fc="#e8e4da",
                              ec="#555", lw=0.5))
        a.axhline(E("tip_r"), color="r", lw=0.3, ls=":")
        a.set_aspect("equal")
    ax.set_xlim(-2, E("head_len") + 3)
    ax.set_ylim(-E("body_r") - 1, E("body_r") + 1)
    ax.set_title(f"Orr + bélés (PEEK) — z=0 section{'  [STAND-IN alu profile]' if STANDIN else ''}"
                 f" — wall {best[0]:.2f}, seat corner ρ {corner:.2f} vs nose r {E('tip_r'):.1f},"
                 f" PEEK under channel {wy0 - lr:.2f}", fontsize=10)
    az.set_xlim(-0.5, 30)
    az.set_ylim(-1, 13)
    af.add_patch(Circle((0, 0), E("tip_r"), fc=peek, ec="k", lw=0.5))
    af.add_patch(Circle((0, 0), E("win_ro"), fc=glass, ec="k", lw=0.4, alpha=0.7))
    af.add_patch(Circle((0, 0), E("collar_r"), fc=peek, ec="k", lw=0.4))
    af.add_patch(Circle((0, 0), nr, fc="w", ec="k", lw=0.4))
    af.add_patch(Rectangle((-seat, ring - seat), 2 * seat, 2 * seat, fill=False, ec="r",
                           ls="--", lw=0.6))
    af.add_patch(Rectangle((-wh, wy0), 2 * wh, wy1 - wy0, fill=False, ec="orange", ls="--",
                           lw=0.6))
    af.add_patch(Circle((0, ring), lens_r, fc="w", ec="r", lw=0.5))
    af.add_patch(Circle((0, ring), E(H.CAM_GLASS_R), fc="#4cc3ff", lw=0))
    for k in range(2 * n):
        th = (2 * k + 1) * math.pi / (2 * n)
        y, z = ring * math.cos(th), ring * math.sin(th)
        af.add_patch(Circle((z, y), led_r, fc="w", ec="k", lw=0.3))
        af.add_patch(Circle((z, y), E("led_d / 2"), fc="#5b3cff" if k % 2 == 0 else "#ff2a2a",
                            lw=0))
    af.set_xlim(-11, 11)
    af.set_ylim(-11, 11)
    af.set_aspect("equal")
    af.set_title("nose face, seen from behind (seat red, channel orange, dashed = deeper)",
                 fontsize=8)
    out = os.path.join(HERE, "out", "head_section.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out)
    print(out)


if __name__ == "__main__":
    main()
