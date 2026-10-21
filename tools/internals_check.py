"""Clearances + plan views of the pp_internals parts against everything else in the pen.

    cd ~/Documents/PlasmaPen
    uv run --python 3.12 --with cadquery --with matplotlib --with numpy python tools/internals_check.py [pp_internals,pp_body]

Builds the full model with the preview backend (render assembly, shells whole), then
  · exact min distance (BRepExtrema) from every internals body to every body of another
    component, keeps the minimum per component pair, prints the tightest ones;
  · contacts (< 0.01 mm) are listed separately — they must all be designed seats;
  · PNGs: side projection (XY), top projection (XZ), YZ slices at a few stations
    → tools/out/internals_*.png
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import check  # noqa: E402
import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape  # noqa: E402

OUT = os.path.join(HERE, "out")


def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value() if d.IsDone() else float("nan")


def bb_gap(a, b):
    return max(a.xmin - b.xmax, b.xmin - a.xmax, a.ymin - b.ymax, b.ymin - a.ymax,
               a.zmin - b.zmax, b.zmin - a.zmax)


def main():
    only = sys.argv[1].split(",") if len(sys.argv) > 1 else None   # e.g. pp_internals,pp_body
    bk, res, mods, imp_err, perr = check.build(only=only)
    if bk is None:
        print(perr)
        return 1
    items = []
    for b, m, path in bk.iter_bodies(res.render):
        if not b.pen:
            continue
        items.append((b, b.shape))  # pen-local frame (the render pose is rotated)
    boxes = [s.BoundingBox() for _, s in items]
    mine = [i for i, (b, _) in enumerate(items) if b.module == "pp_internals"]

    pairs = {}
    for i in mine:
        bi, si = items[i]
        for j, (bj, sj) in enumerate(items):
            if bj.comp is bi.comp or (bj.module == "pp_internals" and j < i):
                continue
            if bb_gap(boxes[i], boxes[j]) > 1.5:
                continue
            d = dist(si, sj)
            key = (check.label(bi), bj.comp.name)
            cur = pairs.get(key)
            if cur is None or d < cur[0]:
                pairs[key] = (d, check.label(bi), check.label(bj))

    rows = sorted(pairs.values())
    contacts = [r for r in rows if r[0] < 0.01]
    gaps = [r for r in rows if r[0] >= 0.01]
    print("── contacts (< 0.01 mm) ──")
    for d, a, b in contacts:
        print(f"  {d:6.3f}  {a}  ↔  {b}")
    print("── tightest clearances ──")
    for d, a, b in gaps[:15]:
        print(f"  {d:6.3f}  {a}  ↔  {b}")

    # ── plots ──
    os.makedirs(OUT, exist_ok=True)
    comps = sorted({b.comp.name for b, _ in items})
    cmap = plt.get_cmap("tab20")
    col = {c: cmap(k % 20) for k, c in enumerate(comps)}
    tri = {}
    for b, s in items:
        v, t = s.tessellate(0.05, 0.3)
        a = np.array([(p.x, p.y, p.z) for p in v])
        tri[id(b)] = (a, np.array(t))
    ev = bk.ev
    bore = ev.length("bore_r")
    head_r = ev.length("liner_ri")
    head_len = ev.length("head_len")

    def proj(ax, i0, i1, only_mine, xlim):
        for b, s in items:
            if only_mine and b.module != "pp_internals":
                continue
            a, t = tri[id(b)]
            if not len(t):
                continue
            polys = a[t][:, :, [i0, i1]]
            alpha = 0.55 if b.module == "pp_internals" else 0.12
            ax.add_collection(PolyCollection(polys, facecolors=col[b.comp.name],
                                             edgecolors="none", alpha=alpha))
        for sgn in (1, -1):
            ax.plot([head_len, ev.length("pen_len")], [sgn * bore] * 2, "k-", lw=0.6)
            ax.plot([0, head_len], [sgn * head_r] * 2, "k--", lw=0.6)
        ax.set_xlim(*xlim)
        ax.set_ylim(-13, 13)
        ax.set_aspect("equal")
        ax.grid(True, lw=0.3)

    spans = [(0, 120), (100, 240)]
    for name, (i0, i1) in (("side_xy", (0, 1)), ("top_xz", (0, 2))):
        fig, axs = plt.subplots(2, 1, figsize=(18, 7.5))
        for ax, span in zip(axs, spans):
            proj(ax, i0, i1, False, span)
        axs[0].set_title(f"internals {name} (projection; shells faint, dashed = head bore)")
        handles = [plt.Rectangle((0, 0), 1, 1, color=col[c]) for c in comps]
        fig.legend(handles, comps, loc="lower center", ncol=8, fontsize=7)
        fig.tight_layout(rect=(0, 0.06, 1, 1))
        fig.savefig(os.path.join(OUT, f"internals_{name}.png"), dpi=130)
        plt.close(fig)

    stations = [("cp_x0 + cp_len / 4", "tartó"), ("int_w_x0 + 6 mm", "huzal a bélésben"),
                ("int_w_xj1", "bélés ↔ venti"), ("fan_x0 + 4 mm", "ventilátor"),
                ("btn_x", "gomb"), ("int_esp_shield_x0 + 5 mm", "ESP + OLED"),
                ("int_fh_x1 - 1 mm", "FH26"), ("int_fpc_xb + 1 mm", "FPC ív"),
                ("bat_x0 + 30 mm", "akku + koax"), ("int_ant_x0 + 2 mm", "antenna + USB-C")]
    fig, axs = plt.subplots(2, 5, figsize=(20, 8.4))
    for ax, (xe, lab) in zip(axs.flat, stations):
        x = ev.length(xe)
        slab = cq.Solid.makeBox(0.02, 40, 40, cq.Vector(x - 0.01, -20, -20))
        for b, s in items:
            bbx = s.BoundingBox()
            if not (bbx.xmin <= x <= bbx.xmax):
                continue
            try:
                sec = s.intersect(slab)
            except Exception:
                continue
            v, t = sec.tessellate(0.02, 0.2)
            if not t:
                continue
            a = np.array([(p.x, p.y, p.z) for p in v])
            polys = a[np.array(t)][:, :, [2, 1]]
            alpha = 0.8 if b.module == "pp_internals" else 0.25
            ax.add_collection(PolyCollection(polys, facecolors=col[b.comp.name],
                                             edgecolors="none", alpha=alpha))
        r = head_r if x < head_len else bore
        th = np.linspace(0, 2 * np.pi, 361)
        ax.plot(r * np.sin(th), r * np.cos(th), "k-", lw=0.6)
        ax.set_xlim(-12.8, 12.8)
        ax.set_ylim(-12.8, 12.8)
        ax.set_aspect("equal")
        ax.grid(True, lw=0.3)
        ax.set_title(f"x = {x:.1f}  {lab}  (Z →, Y ↑)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "internals_sections.png"), dpi=120)
    plt.close(fig)
    print("PNGs → tools/out/internals_side_xy.png, internals_top_xz.png, internals_sections.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
