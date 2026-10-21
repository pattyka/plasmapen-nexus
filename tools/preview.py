"""PlasmaPen Nexus — preview renders without Fusion.

    cd ~/Documents/PlasmaPen
    uv run --python 3.12 --with cadquery --with matplotlib --with numpy python tools/preview.py
        [--only pp_head,pp_body] [--no-step] [--scale 2]

Writes to tools/out/:
    a_hero.png          render assembly, 3/4 from the top-front, tip down onto the dish
    b_cutaway_side.png  engineering assembly, looking straight at the cut face (parallel)
    c_cutaway_34.png    engineering assembly, 3/4 view
    d_section.png       XY section at z = 0 (engineering), line drawing with part labels
    preview.step        both assemblies, coloured, for reference

Rendering: VTK offscreen (shipped with cadquery-ocp), OCC tessellation, studio light kit,
colours / translucency / glow from pp_looks.LOOKS (fallback palette for looks without a colour).
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import preview_backend as pb  # noqa: E402
import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402

OUT = os.path.join(HERE, "out")

# Fallback for looks whose pp_looks colour is None (Fusion library colour kept) or unknown.
FALLBACK = {
    "alu": (214, 216, 219), "alu_dark": (62, 64, 68), "peek": (28, 28, 30),
    "glass_window": (226, 218, 255), "glass_black": (40, 40, 46), "lens": (200, 214, 236),
    "led405": (118, 58, 255), "led660": (236, 18, 22), "plasma_core": (200, 180, 255),
    "plasma_halo": (132, 98, 255), "spot405": (150, 112, 255), "ceramic": (228, 226, 220),
    "pcb": (24, 70, 50), "shield": (186, 188, 192), "copper": (200, 118, 72),
    "gold": (222, 182, 92), "steel": (170, 172, 176), "battery_wrap": (46, 74, 122),
    "plastic_black": (30, 30, 32), "plastic_white": (240, 240, 238), "rubber": (30, 30, 32),
    "fan": (50, 52, 56), "agar": (214, 168, 94), "petri": (248, 249, 250),
    "oled_on": (236, 243, 255),
}
METALS = {"alu", "alu_dark", "shield", "copper", "gold", "steel"}
CLEAR_ALPHA = {"glass_window": 0.38, "lens": 0.45, "petri": 0.22, "glass_black": 0.92}


def look_style(key):
    """→ dict(rgb 0..1, opacity, metal, emissive, roughness)."""
    spec = {}
    try:
        import pp_looks
        spec = pp_looks.LOOKS.get(key, {}) or {}
    except Exception:
        pass
    rgb = spec.get("color") or FALLBACK.get(key, (180, 60, 180))
    alpha = spec.get("alpha", 255) / 255.0
    if key in CLEAR_ALPHA:
        alpha = min(alpha, CLEAR_ALPHA[key])
    return {
        "rgb": tuple(c / 255.0 for c in rgb),
        "opacity": alpha,
        "metal": key in METALS,
        "emissive": spec.get("luminance") is not None,
        "rough": spec.get("roughness", 0.3 if key in METALS else 0.5),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tessellation → VTK
# ─────────────────────────────────────────────────────────────────────────────

def tess(shape, m):
    bb = shape.BoundingBox()
    size = max(bb.xlen, bb.ylen, bb.zlen, 1e-3)
    tol = max(0.005, min(0.05, size / 600))
    verts, tris = shape.tessellate(tol, 0.12)
    v = np.array([(p.x, p.y, p.z) for p in verts], dtype=float)
    t = np.array(tris, dtype=np.int64).reshape(-1, 3)
    if m is not None and len(v):
        v = v @ m[:3, :3].T + m[:3, 3]
    return v, t


def vtk_poly(v, t):
    import vtk
    from vtk.util import numpy_support as ns
    pts = vtk.vtkPoints()
    pts.SetData(ns.numpy_to_vtk(np.ascontiguousarray(v), deep=True))
    cells = np.hstack([np.full((len(t), 1), 3, dtype=np.int64), t]).ravel()
    ca = vtk.vtkCellArray()
    ca.ImportLegacyFormat(ns.numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    nf = vtk.vtkPolyDataNormals()
    nf.SetInputData(pd)
    nf.SetFeatureAngle(32)
    nf.SplittingOn()
    nf.ConsistencyOn()
    nf.AutoOrientNormalsOff()
    nf.Update()
    return nf.GetOutput()


def make_actor(pd, look, edges=False):
    import vtk
    st = look_style(look)
    mp = vtk.vtkPolyDataMapper()
    mp.SetInputData(pd)
    a = vtk.vtkActor()
    a.SetMapper(mp)
    p = a.GetProperty()
    p.SetColor(*st["rgb"])
    p.SetOpacity(st["opacity"])
    p.SetInterpolationToPhong()
    if st["emissive"]:
        p.SetAmbient(0.85)
        p.SetAmbientColor(*st["rgb"])
        p.SetDiffuse(0.35)
        p.SetSpecular(0.1)
    elif st["metal"]:
        p.SetAmbient(0.12)
        p.SetDiffuse(0.75)
        p.SetSpecular(0.55)
        p.SetSpecularPower(18 + 60 * (1 - st["rough"]))
        p.SetSpecularColor(1, 1, 1)
    else:
        p.SetAmbient(0.10)
        p.SetDiffuse(0.85)
        p.SetSpecular(0.35 * (1 - st["rough"]) + 0.05)
        p.SetSpecularPower(10 + 50 * (1 - st["rough"]))
    out = [a]
    if edges:
        fe = vtk.vtkFeatureEdges()
        fe.SetInputData(pd)
        fe.BoundaryEdgesOn()
        fe.FeatureEdgesOn()
        fe.SetFeatureAngle(32)
        fe.ManifoldEdgesOff()
        fe.NonManifoldEdgesOff()
        fe.Update()
        em = vtk.vtkPolyDataMapper()
        em.SetInputData(fe.GetOutput())
        em.ScalarVisibilityOff()
        em.SetResolveCoincidentTopologyToPolygonOffset()
        ea = vtk.vtkActor()
        ea.SetMapper(em)
        lum = 0.299 * st["rgb"][0] + 0.587 * st["rgb"][1] + 0.114 * st["rgb"][2]
        c = 0.05 if lum > 0.3 else 0.45
        ea.GetProperty().SetColor(c, c, c)
        ea.GetProperty().SetLineWidth(1.2)
        ea.GetProperty().SetOpacity(min(1.0, st["opacity"] + 0.3))
        out.append(ea)
    return out


def shadow_actor(center, radius, y, strength=0.55, stretch=1.0):
    """Soft contact shadow: a horizontal quad at height y with a gaussian RGBA texture."""
    import vtk
    from vtk.util import numpy_support as ns
    n = 256
    u = np.linspace(-1, 1, n)
    X, Z = np.meshgrid(u, u)
    rr = np.sqrt((X / stretch) ** 2 + Z ** 2)
    a = strength * np.exp(-((np.maximum(rr - 0.55, 0) / 0.22) ** 2)) * (rr < 1)
    a = np.where(rr < 0.55, strength, a)
    a *= np.clip((1 - rr) / 0.25, 0, 1)
    rgba = np.zeros((n, n, 4), dtype=np.uint8)
    rgba[..., :3] = (30, 32, 36)
    rgba[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    img = vtk.vtkImageData()
    img.SetDimensions(n, n, 1)
    arr = ns.numpy_to_vtk(rgba.reshape(-1, 4), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
    arr.SetNumberOfComponents(4)
    img.GetPointData().SetScalars(arr)
    tex = vtk.vtkTexture()
    tex.SetInputData(img)
    tex.InterpolateOn()
    R = radius * 1.0
    cx, cz = center
    ps = vtk.vtkPlaneSource()
    ps.SetOrigin(cx - R * stretch, y, cz - R)
    ps.SetPoint1(cx + R * stretch, y, cz - R)
    ps.SetPoint2(cx - R * stretch, y, cz + R)
    mp = vtk.vtkPolyDataMapper()
    mp.SetInputConnection(ps.GetOutputPort())
    act = vtk.vtkActor()
    act.SetMapper(mp)
    act.SetTexture(tex)
    pr = act.GetProperty()
    pr.SetAmbient(1.0)
    pr.SetDiffuse(0.0)
    pr.SetSpecular(0.0)
    pr.SetOpacity(0.999)
    return act


def render(scene, path, size, cam, parallel=False, edges=False, scale=2, bg=((1, 1, 1),
           (0.90, 0.91, 0.93)), extra_actors=(), ssao=False, light=None):
    """scene: list of (v, t, look). cam: dict(dir=unit vector from focal point to eye, up,
    zoom, focal=None)."""
    import vtk
    from vtk.util import numpy_support as ns
    W, H = size
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetSize(W * scale, H * scale)
    rw.SetAlphaBitPlanes(1)
    rw.SetMultiSamples(0)
    ren = vtk.vtkRenderer()
    rw.AddRenderer(ren)
    ren.SetUseDepthPeeling(1)
    ren.SetMaximumNumberOfPeels(12)
    ren.SetOcclusionRatio(0.0)
    ren.GradientBackgroundOn()
    ren.SetBackground(*bg[1])
    ren.SetBackground2(*bg[0])
    opaque, clear = [], []
    for v, t, look in scene:
        if len(t) == 0:
            continue
        acts = make_actor(vtk_poly(v, t), look, edges)
        (clear if look_style(look)["opacity"] < 0.99 else opaque).extend(acts)
    for a in list(extra_actors) + opaque + clear:
        ren.AddActor(a)
    light = light or {}
    lk = vtk.vtkLightKit()
    lk.SetKeyLightIntensity(light.get("key", 0.95))
    lk.SetKeyToFillRatio(light.get("fill", 2.6))
    lk.SetKeyToHeadRatio(light.get("head", 3.0))
    lk.SetKeyToBackRatio(light.get("back", 2.5))
    lk.SetKeyLightElevation(light.get("elev", 48))
    lk.SetKeyLightAzimuth(light.get("az", -22))
    lk.AddLightsToRenderer(ren)
    c = ren.GetActiveCamera()
    allv = np.vstack([s[0] for s in scene if len(s[0])])
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    focal = np.array(cam.get("focal", (lo + hi) / 2), dtype=float)
    d = np.array(cam["dir"], dtype=float)
    d /= np.linalg.norm(d)
    radius = np.linalg.norm(hi - lo) / 2
    c.SetFocalPoint(*focal)
    c.SetPosition(*(focal + d * radius * 6))
    c.SetViewUp(*cam["up"])
    c.SetViewAngle(cam.get("fov", 14))
    if parallel:
        c.ParallelProjectionOn()
    ren.ResetCamera(*[lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]])
    if parallel:
        # fit the projected extent exactly
        up = np.array(c.GetViewUp())
        right = np.cross(d, up)
        right /= np.linalg.norm(right)
        up = np.cross(right, d)
        pr = (allv - focal) @ right
        pu = (allv - focal) @ up
        half_h = max((pu.max() - pu.min()) / 2, (pr.max() - pr.min()) / 2 * H / W)
        mid = focal + right * (pr.max() + pr.min()) / 2 + up * (pu.max() + pu.min()) / 2
        c.SetFocalPoint(*mid)
        c.SetPosition(*(mid + d * radius * 6))
        c.SetParallelScale(half_h * cam.get("margin", 1.08))
    else:
        c.Zoom(cam.get("zoom", 1.0))
    ren.ResetCameraClippingRange()
    if ssao:
        ren.UseSSAOOn()
        ren.SetSSAORadius(radius * 0.03)
        ren.SetSSAOBias(radius * 0.012)
        ren.SetSSAOKernelSize(128)
        ren.SSAOBlurOn()
    ren.UseFXAAOn()
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    img = w2i.GetOutput()
    x, y, _ = img.GetDimensions()
    arr = ns.vtk_to_numpy(img.GetPointData().GetScalars()).reshape(y, x, -1)[::-1]
    arr = arr.astype(float)
    if scale > 1:
        arr = arr[:H * scale, :W * scale].reshape(H, scale, W, scale, -1).mean(axis=(1, 3))
    import matplotlib.pyplot as plt
    plt.imsave(path, np.clip(arr / 255.0, 0, 1))
    rw.Finalize()
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Scenes
# ─────────────────────────────────────────────────────────────────────────────

def collect(bk, comp, pen_only=False):
    out = []
    for b, m, path in bk.iter_bodies(comp):
        if pen_only and not b.pen:
            continue
        v, t = tess(b.shape, m)
        out.append((v, t, b.look or "peek"))
    return out


def hero(bk, res, path, scale):
    """Product shot: pen vertical, tip down onto the plate, eye on the OLED side slightly above,
    long lens, seamless white-to-grey studio background, soft contact shadow under the dish."""
    scene = collect(bk, res.render)
    if not scene:
        return None
    allv = np.vstack([s[0] for s in scene if len(s[0])])
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    floor = lo[1]
    dish_r = max(hi[0] - lo[0], hi[2] - lo[2]) / 2
    centre = ((lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2)
    shadows = [shadow_actor(centre, dish_r * 1.32, floor - 0.02, 0.32),
               shadow_actor(centre, dish_r * 1.04, floor - 0.01, 0.30)]
    # pen +Y (OLED, button) maps to world +Z in the render frame → eye on the +Z side, above
    az = math.radians(-32)
    el = math.radians(17)
    d = (math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el))
    return render(scene, path, (1500, 2000), {"dir": d, "up": (0, 1, 0), "zoom": 1.32,
                                              "fov": 11},
                  scale=scale, bg=((1, 1, 1), (0.955, 0.955, 0.965)), extra_actors=shadows,
                  ssao=True, light={"key": 1.0, "fill": 2.2, "back": 1.6, "elev": 40, "az": 28})


def cut_side(bk, res, path, scale):
    scene = collect(bk, res.engineering)
    if not scene:
        return None
    return render(scene, path, (2400, 640), {"dir": (0, 0, 1), "up": (0, 1, 0),
                                             "margin": 1.04}, parallel=True, edges=True,
                  scale=scale)


def cut_34(bk, res, path, scale):
    scene = collect(bk, res.engineering)
    if not scene:
        return None
    az = math.radians(-28)
    el = math.radians(26)
    d = (math.sin(az) * math.cos(el), math.sin(el), math.cos(az) * math.cos(el))
    return render(scene, path, (2200, 1100), {"dir": d, "up": (0, 1, 0), "zoom": 1.85,
                                              "fov": 14}, edges=True, scale=scale)


# ─────────────────────────────────────────────────────────────────────────────
# Section drawing
# ─────────────────────────────────────────────────────────────────────────────

def section_faces(shape, span):
    """Faces of shape ∩ plane z = 0 (component space)."""
    plane = cq.Face.makePlane(span * 3, span * 3, basePnt=cq.Vector(span / 2, 0, 0),
                              dir=cq.Vector(0, 0, 1))
    try:
        sec = shape.intersect(plane)
    except Exception:
        return []
    return [f for f in sec.Faces() if f.Area() > 1e-6]


def _pastel(rgb, k=0.55):
    return tuple(c + (1 - c) * k for c in rgb)


def section(bk, res, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection

    comp = res.engineering
    pen_len = bk.ev.length("pen_len")
    body_r = bk.ev.length("body_r")
    regions = []  # (comp name, look, faces)
    for b, m, p in bk.iter_bodies(comp):
        faces = section_faces(b.shape, pen_len + 100)
        if faces:
            regions.append((b.comp.name, b.name, b.look or "peek", faces))
    if not regions:
        return None
    fig_w = 26
    fig, ax = plt.subplots(figsize=(fig_w, fig_w * 0.30), dpi=110)
    ax.set_aspect("equal")
    ax.axis("off")
    anchors = {}
    for cname, bname, look, faces in regions:
        st = look_style(look)
        fill = _pastel(st["rgb"], 0.62 if sum(st["rgb"]) < 1.2 else 0.25)
        for f in faces:
            vs, ts = f.tessellate(0.02, 0.1)
            v = np.array([(q.x, q.y) for q in vs])
            tri = [v[list(t)] for t in ts]
            ax.add_collection(PolyCollection(tri, facecolors=[fill], edgecolors=[fill],
                                             linewidths=0.3, zorder=1))
            for e in f.Edges():
                ps = e.positions(np.linspace(0, 1, 40 if e.geomType() != "LINE" else 2))
                xy = np.array([(q.x, q.y) for q in ps])
                ax.plot(xy[:, 0], xy[:, 1], color="black", lw=0.7, zorder=3,
                        solid_capstyle="round")
            # label anchor: centroid of the largest triangle of the biggest face
            if tri:
                areas = [abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0])) / 2 for t in tri]
                k = int(np.argmax(areas))
                a = f.Area()
                if cname not in anchors or a > anchors[cname][1]:
                    anchors[cname] = (tri[k].mean(axis=0), a)
    # centre line
    ax.plot([-6, pen_len + 6], [0, 0], color="#666", lw=0.6, ls=(0, (12, 3, 2, 3)), zorder=4)
    # labels: above / below the part, packed into levels so no two labels overlap
    ax.set_xlim(-12, pen_len + 20)
    fig.canvas.draw()
    bb = ax.get_window_extent()
    data_per_px = (pen_len + 32) / bb.width
    fs = 8.5
    char_w = fs * 0.62 * fig.dpi / 72 * data_per_px
    items = sorted(anchors.items(), key=lambda kv: kv[1][0][0])
    levels = {1: [], -1: []}  # side → list of occupied (x0, x1) per level
    counts = {1: 0, -1: 0}
    for name, (pt, _) in items:
        side = 1 if pt[1] >= 0 else -1
        if counts[side] > counts[-side] + 3:
            side = -side
        counts[side] += 1
        w = len(name) * char_w + 3
        lv = 0
        while True:
            if lv >= len(levels[side]):
                levels[side].append([])
            if all(x1 < pt[0] - w / 2 or x0 > pt[0] + w / 2 for x0, x1 in levels[side][lv]):
                break
            lv += 1
        levels[side][lv].append((pt[0] - w / 2, pt[0] + w / 2))
        ty = side * (body_r + 6 + lv * 5.0)
        ax.annotate(name, xy=pt, xytext=(pt[0], ty), fontsize=fs,
                    ha="center", va="bottom" if side > 0 else "top",
                    arrowprops=dict(arrowstyle="-", color="#444", lw=0.5, shrinkA=1, shrinkB=0),
                    zorder=5)
        ax.plot(*pt, marker="o", ms=2.2, color="#111", zorder=6)
    top_levels = max(1, len(levels[1]))
    bot_levels = max(1, len(levels[-1]))
    # overall dimensions
    yd = -(body_r + 10 + bot_levels * 5.0)
    ax.annotate("", xy=(0, yd), xytext=(pen_len, yd),
                arrowprops=dict(arrowstyle="<->", lw=0.6, color="#222", shrinkA=0, shrinkB=0))
    ax.text(pen_len / 2, yd - 1.2, f"{pen_len:.1f} mm", ha="center", va="top", fontsize=9)
    xd = pen_len + 10
    ax.annotate("", xy=(xd, -body_r), xytext=(xd, body_r),
                arrowprops=dict(arrowstyle="<->", lw=0.6, color="#222", shrinkA=0, shrinkB=0))
    ax.text(xd + 1.5, 0, f"Ø{2 * body_r:g}", ha="left", va="center", fontsize=9, rotation=90)
    ax.set_xlim(-12, pen_len + 20)
    ax.set_ylim(yd - 8, body_r + 12 + top_levels * 5.0)
    ax.set_title("PlasmaPen Nexus — XY metszet (z = 0)", fontsize=11, loc="left")
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


# ─────────────────────────────────────────────────────────────────────────────
# STEP
# ─────────────────────────────────────────────────────────────────────────────

def export_step(bk, res, path):
    asm = cq.Assembly(name="PlasmaPen Nexus")
    used = set()
    for top in (res.render, res.engineering):
        if top is None:
            continue
        sub = cq.Assembly(name=top.name)
        for b, m, p in bk.iter_bodies(top):
            nm = f"{p.split('/', 1)[-1]}/{b.name}".replace("/", " · ")
            k = nm
            i = 2
            while (top.name, k) in used:
                k = f"{nm} {i}"
                i += 1
            used.add((top.name, k))
            st = look_style(b.look or "peek")
            sub.add(b.shape, name=k, loc=pb._loc(m),
                    color=cq.Color(*st["rgb"], max(0.05, st["opacity"])))
        asm.add(sub, name=top.name)
    asm.save(path, "STEP")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--no-step", action="store_true")
    ap.add_argument("--scale", type=int, default=2, help="supersampling factor")
    a = ap.parse_args()
    only = [s.strip() for s in a.only.split(",") if s.strip()] or None
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    mods, imp_err = pb.load_modules(only or pb.BUILDER_MODULES)
    for n, tb in imp_err:
        print(f"IMPORT ERROR {n}\n{tb}")
    bk = pb.PreviewBackend(extra_params=pb.collect_extra_params(mods), quiet=True)
    res = pb.build_model(bk, mods)
    for mod, stage, kind, msg, _ in res.errors:
        print(f"BUILD ERROR [{mod}.{stage}] ({kind}) {msg}")
    print(f"built in {time.time() - t0:.1f} s")
    outs = [
        hero(bk, res, os.path.join(OUT, "a_hero.png"), a.scale),
        cut_side(bk, res, os.path.join(OUT, "b_cutaway_side.png"), a.scale),
        cut_34(bk, res, os.path.join(OUT, "c_cutaway_34.png"), a.scale),
        section(bk, res, os.path.join(OUT, "d_section.png")),
    ]
    if not a.no_step:
        outs.append(export_step(bk, res, os.path.join(OUT, "preview.step")))
    for o in outs:
        if o:
            print("wrote", o)
    print(f"done in {time.time() - t0:.1f} s")
    return 1 if res.errors or imp_err else 0


if __name__ == "__main__":
    sys.exit(main())
