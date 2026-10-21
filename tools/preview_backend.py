"""PreviewBackend — runs the PlasmaPen Nexus builder modules in CadQuery/OCP, without Fusion.

HOW TO RUN YOUR MODULE (from ~/Documents/PlasmaPen):

    UVR="uv run --python 3.12 --with cadquery --with matplotlib --with numpy python"

    $UVR tools/preview_backend.py pp_head          # build one module, print bodies / errors
    $UVR tools/preview_backend.py                  # every builder module that exists
    $UVR tools/check.py                            # full model: interference, mass, robustness,
                                                   #   static check of FusionBackend
    $UVR tools/check.py --quick                    # same without robustness + pyright
    $UVR tools/preview.py                          # PNGs + STEP into tools/out/
    $UVR tools/preview.py --only pp_head           # PNGs of just your module

What the backend enforces (each of these RAISES, like Fusion would reject the feature):
  · expressions: unknown names, Python-only syntax ("**", "//", comparisons), wrong units —
    a bare number where a length is expected ("x + 2", "0", 5) is an error, angles need "deg",
    counts (pattern quantity) must be unitless integers. EXTRA_PARAMS are checked against their
    declared unit.
  · profiles: fewer than 3 vertices, zero-length segments, duplicate vertices, self-intersection
    or touching (Fusion would split the sketch into several profiles), zero area, a spline as
    the first item.
  · revolve: profile crossing the X axis (or the chosen segment's line), axis=int that is not a
    straight segment, angle outside (0, 360] deg.
  · extrude: z1 <= z0, zero width.
  · cut / join / intersect: no targets, a tool that misses every target, a cut that deletes a
    whole body, an empty intersection, unknown look/material keys.
Things Fusion would accept but that look wrong go to bk.warnings (cut that splits a body into
several lumps, cross-component targets, a pattern instance missing its targets, a revolve about
X drawn on an offset plane, ...). Fillets that fail are only logged (bk.fillet_failures).

Frame: identical to Fusion — every component has its own XY plane, profiles are drawn in it
(offset by plane_z for revolve / z0 for extrude), X is the pen axis. Units are mm.

Programmatic use:
    import preview_backend as pb
    mods, import_errors = pb.load_modules(["pp_head"])   # from PlasmaPenNexus/
    bk = pb.PreviewBackend(extra_params=pb.collect_extra_params(mods))
    result = pb.build_model(bk, mods)             # mirrors the orchestrator
    for body, trsf, path in bk.iter_bodies(result.render): ...
"""

from __future__ import annotations

import ast
import importlib
import math
import os
import sys
import traceback
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
NEXUS = os.path.normpath(os.path.join(HERE, "..", "PlasmaPenNexus"))
if NEXUS not in sys.path:
    sys.path.insert(0, NEXUS)

import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402
from OCP.BRep import BRep_Tool  # noqa: E402
from OCP.BRepAdaptor import BRepAdaptor_Curve  # noqa: E402
from OCP.BRepCheck import BRepCheck_Analyzer  # noqa: E402
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet  # noqa: E402
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeRevol  # noqa: E402
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Vec  # noqa: E402
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Line  # noqa: E402
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE  # noqa: E402
from OCP.TopExp import TopExp, TopExp_Explorer  # noqa: E402
from OCP.TopoDS import TopoDS  # noqa: E402
from OCP.TopTools import TopTools_IndexedMapOfShape  # noqa: E402

import pp_core  # noqa: E402
from pp_params import PARAMS  # noqa: E402

BUILDER_MODULES = ["pp_body", "pp_head", "pp_internals", "pp_scene"]  # pp_body first: pp_head uses body_* params

DENSITY = {  # g/cm³
    "aluminum": 2.70, "peek": 1.30, "glass": 2.50, "plastic": 1.15, "steel": 7.85,
    "copper": 8.96, "fr4": 1.85, "battery": 2.80,
}
BRIEF_LOOKS = {
    "alu", "alu_dark", "peek", "glass_window", "glass_black", "lens", "led405", "led660",
    "plasma_core", "plasma_halo", "spot405", "ceramic", "pcb", "shield", "copper", "gold",
    "steel", "battery_wrap", "plastic_black", "plastic_white", "rubber", "fan", "agar", "petri",
    "oled_on",
}
BRIEF_MATERIALS = set(DENSITY)

GEO_EPS = 1e-4      # mm — coincidence tolerance for profile checks
SEL_TOL = 0.05      # mm — FusionBackend._select_edges tolerance (0.005 cm)


# ─────────────────────────────────────────────────────────────────────────────
# Errors
# ─────────────────────────────────────────────────────────────────────────────

class BuildError(Exception):
    """Something Fusion would reject (or that is wrong by the brief's rules)."""


class ExprError(BuildError):
    pass


class ProfileError(BuildError):
    pass


class OccError(Exception):
    """OCC kernel failure in the preview only — Fusion may well succeed. Reported separately."""


# ─────────────────────────────────────────────────────────────────────────────
# Unit-checked expression evaluation
# ─────────────────────────────────────────────────────────────────────────────

class Q:
    """A value with dimensions: L = length exponent (mm), A = angle exponent (rad)."""

    __slots__ = ("v", "L", "A")

    def __init__(self, v, L=0.0, A=0.0):
        self.v, self.L, self.A = float(v), float(L), float(A)

    @staticmethod
    def of(o):
        return o if isinstance(o, Q) else Q(o)

    def dim(self):
        return (round(self.L, 9), round(self.A, 9))

    def dimstr(self):
        return dimname(self.dim())

    def _same(self, o, what):
        o = Q.of(o)
        if self.dim() != o.dim():
            raise ExprError(f"{what} of {self.dimstr()} and {o.dimstr()} "
                            f"(a literal length needs ' mm', an angle ' deg')")
        return o

    def __add__(self, o):
        o = self._same(o, "adding")
        return Q(self.v + o.v, self.L, self.A)

    def __radd__(self, o):
        return Q.of(o).__add__(self)

    def __sub__(self, o):
        o = self._same(o, "subtracting")
        return Q(self.v - o.v, self.L, self.A)

    def __rsub__(self, o):
        return Q.of(o).__sub__(self)

    def __mul__(self, o):
        o = Q.of(o)
        return Q(self.v * o.v, self.L + o.L, self.A + o.A)

    __rmul__ = __mul__

    def __truediv__(self, o):
        o = Q.of(o)
        if o.v == 0:
            raise ExprError("division by zero")
        return Q(self.v / o.v, self.L - o.L, self.A - o.A)

    def __rtruediv__(self, o):
        return Q.of(o).__truediv__(self)

    def __pow__(self, o):
        o = Q.of(o)
        if o.dim() != (0, 0):
            raise ExprError(f"exponent must be unitless, got {o.dimstr()}")
        if self.v < 0 and o.v != int(o.v):
            raise ExprError("negative base with fractional exponent")
        return Q(self.v ** o.v, self.L * o.v, self.A * o.v)

    def __rpow__(self, o):
        return Q.of(o).__pow__(self)

    def __neg__(self):
        return Q(-self.v, self.L, self.A)

    def __pos__(self):
        return self


def dimname(d):
    L, A = d
    if (L, A) == (0, 0):
        return "a unitless number"
    parts = []
    if L:
        parts.append("mm" if L == 1 else f"mm^{L:g}")
    if A:
        parts.append("deg" if A == 1 else f"deg^{A:g}")
    return " ".join(parts)


UNIT_DIM = {"mm": (1, 0), "deg": (0, 1), "": (0, 0)}


def _f_sqrt(x):
    x = Q.of(x)
    if x.v < 0:
        raise ExprError("sqrt of a negative value")
    return Q(math.sqrt(x.v), x.L / 2, x.A / 2)


def _f_trig(fn):
    def f(x):
        x = Q.of(x)
        if x.L != 0 or x.A not in (0, 1):
            raise ExprError(f"{fn.__name__}() needs an angle, got {x.dimstr()}")
        return Q(fn(x.v))
    return f


def _f_atrig(fn):
    def f(x):
        x = Q.of(x)
        if x.dim() != (0, 0):
            raise ExprError(f"{fn.__name__}() needs a unitless ratio, got {x.dimstr()}")
        try:
            return Q(fn(x.v), 0, 1)
        except ValueError as e:
            raise ExprError(f"{fn.__name__}({x.v:g}): {e}") from None
    return f


def _f_keep(fn):
    def f(x):
        x = Q.of(x)
        return Q(fn(x.v), x.L, x.A)
    return f


FUNCS = {
    "sqrt": _f_sqrt,
    "sin": _f_trig(math.sin), "cos": _f_trig(math.cos), "tan": _f_trig(math.tan),
    "asin": _f_atrig(math.asin), "acos": _f_atrig(math.acos), "atan": _f_atrig(math.atan),
    "abs": _f_keep(abs), "floor": _f_keep(math.floor), "ceil": _f_keep(math.ceil),
    "round": _f_keep(round),
}
_ALLOWED_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load,
                  ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd)


class Evaluator:
    """PARAMS (+ overrides) evaluated by pp_core.ExprEval, then EXTRA_PARAMS in order, with a
    dimensional check of every expression. Lengths → mm, angles → rad."""

    def __init__(self, overrides=None, extra_params=()):
        overrides = dict(overrides or {})
        self.ee = pp_core.ExprEval({k: v for k, v in overrides.items()
                                    if k in {p[0] for p in PARAMS}})
        self.q = {}
        self.units = {}
        self.sources = {}
        for name, expr, unit, _ in PARAMS:
            self._define(name, overrides.get(name, expr), unit, "pp_params")
            ref = self.ee.values[name]
            if abs(ref - self.q[name].v) > 1e-9 * max(1.0, abs(ref)):
                raise ExprError(f"{name}: ExprEval={ref} vs unit evaluator={self.q[name].v}")
        for src, items in extra_params:
            for item in items:
                if not (isinstance(item, (tuple, list)) and len(item) == 4):
                    raise ExprError(f"{src}.EXTRA_PARAMS entry {item!r} must be "
                                    "(name, expr, unit, comment)")
                name, expr, unit, _ = item
                if name in self.q:
                    raise ExprError(f"{src}.EXTRA_PARAMS: '{name}' already defined by "
                                    f"{self.sources[name]}")
                self._define(name, overrides.get(name, expr), unit, src)
                self.ee.values[name] = self.q[name].v

    def _define(self, name, expr, unit, src):
        if unit not in UNIT_DIM:
            raise ExprError(f"{src}: parameter '{name}' has unit '{unit}' (use 'mm', 'deg' or '')")
        if not name.isidentifier():
            raise ExprError(f"{src}: '{name}' is not a valid parameter name")
        try:
            qv = self.eval_q(expr)
        except ExprError as e:
            raise ExprError(f"{src}: parameter {name} = '{expr}': {e}") from None
        if qv.dim() != UNIT_DIM[unit]:
            raise ExprError(f"{src}: parameter {name} = '{expr}' is {qv.dimstr()}, declared "
                            f"unit '{unit}'")
        self.q[name] = qv
        self.units[name] = unit
        self.sources[name] = src

    @property
    def values(self):
        return {k: v.v for k, v in self.q.items()}

    def eval_q(self, expr):
        if isinstance(expr, bool) or expr is None:
            raise ExprError(f"expression expected, got {expr!r}")
        if isinstance(expr, (int, float)):
            return Q(expr)
        s = str(expr)
        if not s.strip():
            raise ExprError("empty expression")
        if "**" in s:
            raise ExprError(f"'{s}': Fusion uses '^' for powers, not '**'")
        py = pp_core._UNIT_RE.sub(lambda m: "*__" + m.group(1), s.replace("^", "**"))
        try:
            tree = ast.parse(py, mode="eval")
        except SyntaxError:
            raise ExprError(f"'{s}': not a valid expression (units need a space: '2 mm')") from None
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED_NODES):
                raise ExprError(f"'{s}': {type(node).__name__} is not Fusion expression syntax")
            if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
                raise ExprError(f"'{s}': literal {node.value!r} is not a number")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS or node.keywords:
                    raise ExprError(f"'{s}': unsupported function call")
                if len(node.args) != 1:
                    raise ExprError(f"'{s}': {node.func.id}() takes one argument")
            if isinstance(node, ast.Name) and node.id not in FUNCS and node.id not in (
                    "__mm", "__deg", "PI") and node.id not in self.q:
                raise ExprError(f"'{s}': unknown name '{node.id}'")
        env = {"__mm": Q(1, 1, 0), "__deg": Q(math.pi / 180.0, 0, 1), "PI": Q(math.pi)}
        env.update(FUNCS)
        env.update(self.q)
        try:
            out = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, env)  # noqa: S307
        except ExprError as e:
            raise ExprError(f"'{s}': {e}") from None
        except (ZeroDivisionError, OverflowError, ValueError) as e:
            raise ExprError(f"'{s}': {e}") from None
        return Q.of(out)

    def length(self, expr, what="length"):
        qv = self.eval_q(expr)
        if qv.dim() != (1, 0):
            raise ExprError(f"{what} '{expr}' is {qv.dimstr()}, expected a length (mm)")
        return qv.v

    def angle(self, expr, what="angle"):
        qv = self.eval_q(expr)
        if qv.dim() != (0, 1):
            raise ExprError(f"{what} '{expr}' is {qv.dimstr()}, expected an angle (deg)")
        return qv.v

    def count(self, expr, what="count"):
        qv = self.eval_q(expr)
        if qv.dim() != (0, 0):
            raise ExprError(f"{what} '{expr}' is {qv.dimstr()}, expected a unitless count")
        if abs(qv.v - round(qv.v)) > 1e-9:
            raise ExprError(f"{what} '{expr}' = {qv.v:g} is not an integer")
        return int(round(qv.v))


# ─────────────────────────────────────────────────────────────────────────────
# Model objects
# ─────────────────────────────────────────────────────────────────────────────

class Comp:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.bodies: list[Body] = []
        self.occurrences: list[Occ] = []

    def path(self):
        parts = []
        c = self
        while c is not None:
            parts.append(c.name)
            c = c.parent
        return "/".join(reversed(parts))

    def __repr__(self):
        return f"<Comp {self.path()}>"


class Occ:
    def __init__(self, comp, transform=None, shared=False):
        self.comp = comp
        self.transform = transform  # 4x4 numpy or None
        self.shared = shared


class Body:
    def __init__(self, comp, name, shape, look, material, pen, module, source_feature):
        self.comp = comp
        self.name = name
        self.shape = shape
        self.look = look
        self.material = material
        self.pen = pen
        self.module = module
        self.feature = source_feature
        self.valid = True
        self.lumps = 1
        self.stage = None

    @property
    def volume(self):
        return abs(self.shape.Volume())

    def __repr__(self):
        return f"<Body {self.comp.name}/{self.name}>"


@dataclass
class Feature:
    kind: str
    name: str
    comp: Comp
    op: str
    tool: object = None          # cq.Shape of the tool (local coords)
    targets: list = field(default_factory=list)


def _check_valid(shape):
    return BRepCheck_Analyzer(shape.wrapped).IsValid()


def _solids(shape):
    return list(shape.Solids())


def _as_shape(solids):
    if len(solids) == 1:
        return solids[0]
    return cq.Compound.makeCompound(solids)


def _to_matrix(t):
    if t is None:
        return None
    if isinstance(t, cq.Location):
        tr = t.wrapped.Transformation()
        m = np.eye(4)
        for i in range(3):
            for j in range(4):
                m[i, j] = tr.Value(i + 1, j + 1)
        return m
    if hasattr(t, "asArray"):
        t = t.asArray()
    m = np.array(t, dtype=float)
    if m.size == 16:
        return m.reshape(4, 4)
    raise BuildError(f"transform {t!r} is not a 4x4 matrix")


def _loc(m):
    """numpy 4x4 → cq.Location (mm)."""
    from OCP.gp import gp_Trsf
    tr = gp_Trsf()
    tr.SetValues(*[float(m[i, j]) for i in range(3) for j in range(4)])
    return cq.Location(tr)


# ─────────────────────────────────────────────────────────────────────────────
# The backend
# ─────────────────────────────────────────────────────────────────────────────

class PreviewBackend(pp_core.Backend):
    def __init__(self, overrides=None, extra_params=(), quiet=False, check_keys=True):
        self.ev = Evaluator(overrides, extra_params)
        self.root = Comp("(root)")
        self.pen_bodies: list[Body] = []
        self.count_mass = True
        self.failures = []
        self.warnings: list[str] = []
        self.logs: list[str] = []
        self.fillet_failures: list[str] = []
        self.features: list[Feature] = []
        self.current_module = None
        self.current_stage = None
        self.quiet = quiet
        self._looks, self._materials = self._known_keys() if check_keys else (None, None)

    # ── helpers ──
    @staticmethod
    def _known_keys():
        try:
            import pp_looks
            return set(pp_looks.LOOKS), set(pp_looks.MATERIALS)
        except Exception:
            return BRIEF_LOOKS, BRIEF_MATERIALS

    def log(self, msg):
        self.logs.append(str(msg))
        if not self.quiet:
            print(msg)

    def warn(self, msg):
        self.warnings.append(f"[{self.current_module or '-'}] {msg}")

    def _ctx(self, comp, name):
        return f"{comp.path() if isinstance(comp, Comp) else comp}: '{name}'"

    def _comp(self, comp, name):
        if not isinstance(comp, Comp):
            raise BuildError(f"'{name}': comp must be a component handle from bk.component(), "
                             f"got {comp!r}")
        return comp

    # ── structure ──
    def component(self, parent, name, transform=None):
        parent = self.root if parent is None else parent
        if not isinstance(parent, Comp):
            raise BuildError(f"component('{name}'): parent {parent!r} is not a component")
        if not isinstance(name, str) or not name.strip():
            raise BuildError("component name must be a non-empty string")
        c = Comp(name, parent)
        parent.occurrences.append(Occ(c, _to_matrix(transform)))
        return c

    def add_existing(self, parent, comp):
        parent = self.root if parent is None else parent
        if not isinstance(parent, Comp) or not isinstance(comp, Comp):
            raise BuildError(f"add_existing({parent!r}, {comp!r}): both must be components")
        p = parent
        while p is not None:
            if p is comp:
                raise BuildError(f"add_existing: {comp.path()} would contain itself")
            p = p.parent
        occ = Occ(comp, None, shared=True)
        parent.occurrences.append(occ)
        return occ

    # ── profiles ──
    def _parse_profile(self, ctx, pts):
        """→ (items, segments). items: list of vertices [(x, y)]; segments: list of
        ('line', [p0, p1]) / ('spline', [p0, p1, ...])."""
        if not isinstance(pts, (list, tuple)) or len(pts) < 2:
            raise ProfileError(f"{ctx}: profile needs at least 3 vertices")
        segs = []
        verts = []
        prev = None
        first = None
        for k, item in enumerate(pts):
            if (isinstance(item, (tuple, list)) and len(item) == 2 and item[0] == "spline"):
                if prev is None:
                    raise ProfileError(f"{ctx}: profile cannot start with a spline")
                fit = item[1]
                if not isinstance(fit, (list, tuple)) or not fit:
                    raise ProfileError(f"{ctx}: spline item {k} needs a list of points")
                ptsl = [prev]
                for p in fit:
                    ptsl.append(self._vertex(ctx, p, k))
                verts.extend(ptsl[1:])
                segs.append(("spline", ptsl))
                prev = ptsl[-1]
                continue
            p = self._vertex(ctx, item, k)
            verts.append(p)
            if prev is None:
                first = p
            else:
                segs.append(("line", [prev, p]))
            prev = p
        segs.append(("line", [prev, first]))
        if len(verts) < 3 and not any(s[0] == "spline" for s in segs):
            raise ProfileError(f"{ctx}: profile needs at least 3 vertices")
        return verts, segs

    def _vertex(self, ctx, p, k):
        if not (isinstance(p, (tuple, list)) and len(p) == 2):
            raise ProfileError(f"{ctx}: item {k} {p!r} is not an (x, y) vertex")
        try:
            return (self.ev.length(p[0], "x"), self.ev.length(p[1], "y"))
        except ExprError as e:
            raise ExprError(f"{ctx}: vertex {k}: {e}") from None

    def _build_face(self, ctx, segs, z):
        edges = []
        polys = []  # sampled polyline per segment (for intersection tests)
        for i, (kind, ps) in enumerate(segs):
            for a, b in zip(ps, ps[1:]):
                if math.dist(a, b) < GEO_EPS:
                    what = "closing line (first vertex repeated at the end?)" \
                        if i == len(segs) - 1 else f"segment {i} ({kind})"
                    raise ProfileError(f"{ctx}: zero-length {what} at "
                                       f"({a[0]:.3f}, {a[1]:.3f})")
            vs = [cq.Vector(x, y, z) for x, y in ps]
            if kind == "line":
                e = cq.Edge.makeLine(vs[0], vs[1])
                polys.append([ps[0], ps[1]])
            else:
                try:
                    e = cq.Edge.makeSpline(vs)
                except Exception as ex:
                    raise ProfileError(f"{ctx}: spline segment {i} could not be fitted: {ex}") \
                        from None
                n = max(24, 12 * (len(ps) - 1))
                samp = [e.positionAt(t / n) for t in range(n + 1)]
                polys.append([(v.x, v.y) for v in samp])
            edges.append(e)
        self._check_simple(ctx, polys, segs)
        try:
            wire = cq.Wire.assembleEdges(edges)
            face = cq.Face.makeFromWires(wire)
        except Exception as ex:
            raise ProfileError(f"{ctx}: profile did not close into a face: {ex}") from None
        if not _check_valid(face) or face.Area() < 1e-6:
            raise ProfileError(f"{ctx}: profile face is invalid or has zero area")
        return face, polys

    @staticmethod
    def _check_simple(ctx, polys, segs):
        # duplicate vertices (incl. spline fit points)
        vlist = []
        for i, (kind, ps) in enumerate(segs):
            for p in ps[1:]:
                vlist.append((i, p))
        for a in range(len(vlist)):
            for b in range(a + 1, len(vlist)):
                if math.dist(vlist[a][1], vlist[b][1]) < GEO_EPS:
                    p = vlist[a][1]
                    raise ProfileError(f"{ctx}: duplicate vertex ({p[0]:.3f}, {p[1]:.3f}) "
                                       f"(segments {vlist[a][0]} and {vlist[b][0]})")
        pieces = []  # (seg index, a, b)
        for i, pl in enumerate(polys):
            for a, b in zip(pl, pl[1:]):
                if math.dist(a, b) > 1e-9:
                    pieces.append((i, a, b))
        n = len(pieces)
        P = np.array([[p[1][0], p[1][1], p[2][0], p[2][1]] for p in pieces])
        for i in range(n):
            # adjacent piece: check fold-back (collinear overlap)
            j = (i + 1) % n
            a0, a1 = np.array(P[i, :2]), np.array(P[i, 2:])
            b1 = np.array(P[j, 2:])
            u, v = a1 - a0, b1 - a1
            cr = u[0] * v[1] - u[1] * v[0]
            if abs(cr) < 1e-9 * np.linalg.norm(u) * np.linalg.norm(v) and np.dot(u, v) < 0:
                raise ProfileError(f"{ctx}: profile folds back on itself at "
                                   f"({a1[0]:.3f}, {a1[1]:.3f}) (segments {pieces[i][0]}, "
                                   f"{pieces[j][0]})")
            # non-adjacent pieces: any contact = self-intersection
            others = [k for k in range(i + 2, n) if not (i == 0 and k == n - 1)]
            if not others:
                continue
            Q_ = P[others]
            hit = _seg_hits(P[i], Q_)
            if hit.any():
                k = others[int(np.argmax(hit))]
                pt = _seg_point(P[i], P[k])
                raise ProfileError(f"{ctx}: profile self-intersects / touches itself near "
                                   f"({pt[0]:.3f}, {pt[1]:.3f}) (segments {pieces[i][0]} and "
                                   f"{pieces[k][0]})")

    # ── features ──
    def _register(self, feat):
        self.features.append(feat)
        return feat

    def _keys(self, ctx, look, material):
        if look is not None and self._looks is not None and look not in self._looks:
            raise BuildError(f"{ctx}: unknown look '{look}'")
        if material is not None and self._materials is not None and material not in self._materials:
            raise BuildError(f"{ctx}: unknown material '{material}'")

    def _apply(self, comp, name, tool, op, targets, look, material, pen, kind):
        ctx = self._ctx(comp, name)
        if op not in ("new", "cut", "join", "intersect"):
            raise BuildError(f"{ctx}: op '{op}' must be new/cut/join/intersect")
        if not _check_valid(tool):
            raise OccError(f"{ctx}: tool solid is invalid in OCC")
        if abs(tool.Volume()) < 1e-9:
            raise BuildError(f"{ctx}: feature produces zero volume")
        if op == "new":
            self._keys(ctx, look, material)
            if targets:
                self.warn(f"{ctx}: targets given to a 'new' op are ignored by Fusion")
            feat = self._register(Feature(kind, name, comp, op, tool, []))
            solids = _solids(tool)
            bodies = []
            for i, s in enumerate(solids):
                bname = name if len(solids) == 1 else f"{name} {i + 1}"
                b = Body(comp, bname, s, look, material, pen, self.current_module, feat)
                b.stage = self.current_stage
                comp.bodies.append(b)
                bodies.append(b)
                if pen and self.count_mass:
                    self.pen_bodies.append(b)
            return pp_core.Op(feat, bodies)

        if not targets:
            raise BuildError(f"{ctx}: cut/join/intersect needs targets")
        targets = list(targets)
        for t in targets:
            if not isinstance(t, Body):
                raise BuildError(f"{ctx}: target {t!r} is not a body (pass op.body / op.bodies)")
            if not t.valid:
                raise BuildError(f"{ctx}: target {t.name} no longer exists (merged by a join)")
            if t.comp is not comp:
                self.warn(f"{ctx}: target body '{t.name}' lives in {t.comp.path()}, the feature "
                          f"in {comp.path()} — Fusion needs both in the same component")
        if look is not None or material is not None:
            self.warn(f"{ctx}: look/material on a '{op}' op are ignored by Fusion")
        feat = self._register(Feature(kind, name, comp, op, tool, targets))
        self._combine(ctx, feat, tool, op, targets, strict=True)
        return pp_core.Op(feat, [])

    def _combine(self, ctx, feat, tool, op, targets, strict):
        """Apply tool to targets in place. strict=False (pattern instances) downgrades
        'missed every target' to a warning, as Fusion's feature pattern does."""
        touched = []
        tbb = fast_bb(tool)
        for t in targets:
            if not t.valid:
                continue
            if not _bb_overlap(tbb, fast_bb(t.shape)):
                continue
            try:
                if op == "cut":
                    # one boolean: the cut result itself tells whether the tool touched
                    v0 = abs(t.shape.Volume())
                    result = t.shape.cut(tool)
                    v = v0 - abs(result.Volume())
                else:
                    result = t.shape.intersect(tool)
                    v = abs(result.Volume())
            except Exception as ex:
                raise OccError(f"{ctx}: OCC boolean failed on {t.name}: {ex}") from None
            if v > 1e-6:
                touched.append((t, result))
        if op == "join":
            if not touched:
                # Fusion joins a disjoint tool as an extra lump of the first participant
                self.warn(f"{ctx}: join tool does not touch any target; it becomes a separate "
                          f"lump of '{targets[0].name}'")
                touched = [(targets[0], None)]
            base = touched[0][0]
            shape = base.shape
            for t, _ in touched[1:]:
                shape = shape.fuse(t.shape)
            try:
                shape = shape.fuse(tool).clean()
            except Exception as ex:
                raise OccError(f"{ctx}: OCC fuse failed: {ex}") from None
            self._set_shape(ctx, base, shape)
            for t, _ in touched[1:]:
                t.valid = False
                if t in t.comp.bodies:
                    t.comp.bodies.remove(t)
                self.warn(f"{ctx}: join merged '{t.name}' into '{base.name}'")
            return
        if not touched:
            msg = f"{ctx}: {op} tool does not intersect any of its targets " \
                  f"({', '.join(t.name for t in targets)})"
            if strict:
                raise BuildError(msg)
            self.warn(msg + " — this pattern instance does nothing")
            return
        for t in targets:
            if t not in [x[0] for x in touched] and op == "cut":
                self.log(f"  · {ctx}: target '{t.name}' is not touched by the cut")
        for t, shape in touched:
            solids = [s for s in _solids(shape) if abs(s.Volume()) > 1e-6]
            if not solids:
                raise BuildError(f"{ctx}: {op} removes the whole body '{t.name}'")
            self._set_shape(ctx, t, _as_shape(solids))
        if op == "intersect":
            for t in targets:
                if t not in [x[0] for x in touched]:
                    raise BuildError(f"{ctx}: intersect leaves nothing of '{t.name}'")

    def _set_shape(self, ctx, body, shape):
        solids = [s for s in _solids(shape) if abs(s.Volume()) > 1e-6]
        if not solids:
            raise BuildError(f"{ctx}: '{body.name}' ended up empty")
        if not _check_valid(shape):
            self.warn(f"{ctx}: OCC reports '{body.name}' invalid after the operation")
        if len(solids) > 1 and len(solids) != body.lumps:
            vols = ", ".join(f"{abs(s.Volume()):.2f}" for s in solids)
            self.warn(f"{ctx}: '{body.name}' is now {len(solids)} separate lumps ({vols} mm³) "
                      f"— Fusion would split it into {len(solids)} bodies")
        body.lumps = len(solids)
        body.shape = _as_shape(solids)

    # ── geometry ──
    def revolve(self, comp, name, pts, axis="x", angle="360 deg", plane_z="0 mm",
                op="new", targets=None, look=None, material=None, pen=True):
        comp = self._comp(comp, name)
        ctx = self._ctx(comp, name)
        try:
            z = self.ev.length(plane_z, "plane_z")
            ang = self.ev.angle(angle, "revolve angle")
        except ExprError as e:
            raise ExprError(f"{ctx}: {e}") from None
        if not (1e-9 < ang <= 2 * math.pi + 1e-9):
            raise BuildError(f"{ctx}: revolve angle {math.degrees(ang):g} deg not in (0, 360]")
        _, segs = self._parse_profile(ctx, pts)
        face, polys = self._build_face(ctx, segs, z)
        allpts = np.array([p for pl in polys for p in pl])
        if axis == "x":
            if abs(z) > GEO_EPS:
                self.warn(f"{ctx}: revolve about the X axis from a sketch at z = {z:g} mm — the "
                          "axis is not in the sketch plane; verify on Fusion")
            ys = allpts[:, 1]
            if ys.min() < -GEO_EPS and ys.max() > GEO_EPS:
                raise ProfileError(f"{ctx}: revolve profile crosses the X axis "
                                   f"(y from {ys.min():.3f} to {ys.max():.3f})")
            if ys.min() < -GEO_EPS:
                self.warn(f"{ctx}: revolve profile lies at y < 0 (brief asks for y ≥ 0)")
            p0, d = cq.Vector(0, 0, 0), cq.Vector(1, 0, 0)
        else:
            if isinstance(axis, bool) or not isinstance(axis, int):
                raise BuildError(f"{ctx}: axis must be 'x' or a segment index, got {axis!r}")
            if not (-len(segs) <= axis < len(segs)):
                raise BuildError(f"{ctx}: axis segment {axis} out of range (profile has "
                                 f"{len(segs)} segments)")
            kind, ps = segs[axis]
            if kind != "line":
                raise BuildError(f"{ctx}: axis segment {axis} is a spline, not a straight line")
            a, b = np.array(ps[0]), np.array(ps[1])
            u = (b - a) / np.linalg.norm(b - a)
            sd = (allpts[:, 0] - a[0]) * u[1] - (allpts[:, 1] - a[1]) * u[0]
            if sd.min() < -GEO_EPS and sd.max() > GEO_EPS:
                raise ProfileError(f"{ctx}: profile crosses the line of axis segment {axis}")
            p0, d = cq.Vector(a[0], a[1], z), cq.Vector(u[0], u[1], 0)
        if abs(ang - 2 * math.pi) > 1e-9:
            self.warn(f"{ctx}: partial revolve ({math.degrees(ang):g} deg) — Fusion's direction "
                      "for setAngleExtent(False, …) assumed right-handed about the axis; verify")
        try:
            mk = BRepPrimAPI_MakeRevol(face.wrapped, gp_Ax1(gp_Pnt(p0.x, p0.y, p0.z),
                                       gp_Dir(d.x, d.y, d.z)), ang, True)
            mk.Build()
            solid = cq.Shape.cast(mk.Shape())
        except Exception as ex:
            raise OccError(f"{ctx}: OCC revolve failed: {ex}") from None
        return self._apply(comp, name, solid, op, targets, look, material, pen, "revolve")

    def extrude(self, comp, name, pts, z0, z1, op="new", targets=None, look=None,
                material=None, pen=True):
        comp = self._comp(comp, name)
        ctx = self._ctx(comp, name)
        try:
            a = self.ev.length(z0, "z0")
            b = self.ev.length(z1, "z1")
        except ExprError as e:
            raise ExprError(f"{ctx}: {e}") from None
        if b - a <= GEO_EPS:
            raise BuildError(f"{ctx}: extrude needs z1 > z0 (z0 = {a:g}, z1 = {b:g})")
        _, segs = self._parse_profile(ctx, pts)
        face, _ = self._build_face(ctx, segs, a)
        try:
            solid = _prism(face, b - a)
        except Exception as ex:
            raise OccError(f"{ctx}: OCC extrude failed: {ex}") from None
        return self._apply(comp, name, solid, op, targets, look, material, pen, "extrude")

    def extrude_sym(self, comp, name, pts, width, op="new", targets=None, look=None,
                    material=None, pen=True):
        comp = self._comp(comp, name)
        ctx = self._ctx(comp, name)
        try:
            w = self.ev.length(width, "width")
        except ExprError as e:
            raise ExprError(f"{ctx}: {e}") from None
        if w <= GEO_EPS:
            raise BuildError(f"{ctx}: symmetric extrude width {w:g} must be > 0")
        _, segs = self._parse_profile(ctx, pts)
        face, _ = self._build_face(ctx, segs, -w / 2)
        try:
            solid = _prism(face, w)
        except Exception as ex:
            raise OccError(f"{ctx}: OCC extrude failed: {ex}") from None
        return self._apply(comp, name, solid, op, targets, look, material, pen, "extrude_sym")

    def pattern_x(self, comp, name, op_result, count, look=None):
        comp = self._comp(comp, name)
        ctx = self._ctx(comp, name)
        if not isinstance(op_result, pp_core.Op):
            raise BuildError(f"{ctx}: pattern_x needs an Op from a previous call")
        try:
            n = self.ev.count(count, "pattern count")
        except ExprError as e:
            raise ExprError(f"{ctx}: {e}") from None
        if n < 1:
            raise BuildError(f"{ctx}: pattern count {n} < 1")
        if n == 1:
            self.warn(f"{ctx}: pattern count is 1 — Fusion may reject a 1-instance pattern")
        if look is not None:
            self._keys(ctx, look, None)
        feat = self._register(Feature("pattern", name, comp, "pattern"))
        new = []
        if op_result.bodies:
            for b in op_result.bodies:
                if not b.valid:
                    raise BuildError(f"{ctx}: source body '{b.name}' no longer exists")
                if b.comp is not comp:
                    self.warn(f"{ctx}: patterned body '{b.name}' lives in {b.comp.path()}")
            src_pen = op_result.bodies[0] in self.pen_bodies
            for k in range(1, n):
                deg = 360.0 * k / n
                for b in op_result.bodies:
                    s = b.shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), deg)
                    nb = Body(comp, f"{name} {len(new) + 2}", s, look or b.look, b.material,
                              b.pen, self.current_module, feat)
                    nb.lumps = b.lumps
                    nb.stage = b.stage
                    comp.bodies.append(nb)
                    new.append(nb)
                    if src_pen:
                        self.pen_bodies.append(nb)
            return pp_core.Op(feat, new)
        src = op_result.feature
        if not isinstance(src, Feature) or src.tool is None:
            raise BuildError(f"{ctx}: Op has neither bodies nor a patternable feature")
        if src.op == "new":
            raise BuildError(f"{ctx}: a 'new' Op without bodies cannot be patterned")
        if src.comp is not comp:
            self.warn(f"{ctx}: patterned feature '{src.name}' lives in {src.comp.path()}")
        for k in range(1, n):
            deg = 360.0 * k / n
            tool = src.tool.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), deg)
            self._combine(f"{ctx} #{k + 1}", feat, tool, src.op, src.targets, strict=False)
        return pp_core.Op(feat, [])

    def fillet(self, comp, name, body, edges, radius):
        comp = self._comp(comp, name)
        ctx = self._ctx(comp, name)
        try:
            r = self.ev.length(radius, "fillet radius")
            sels = [self._sel_values(sel) for sel in edges]
        except ExprError as e:
            raise ExprError(f"{ctx}: {e}") from None
        except (TypeError, ValueError, IndexError):
            raise BuildError(f"{ctx}: bad edge selector list {edges!r}") from None
        if not isinstance(body, Body) or not body.valid:
            msg = f"  · {name}: fillet target {body!r} is not a live body, fillet skipped"
            self.log(msg)
            self.fillet_failures.append(f"[{self.current_module}] {ctx}: not a live body")
            return None
        if r <= 0:
            raise BuildError(f"{ctx}: fillet radius {r:g} must be > 0")
        found = []
        for sel in sels:
            found.extend(self._select_edges(body.shape, sel))
        if not found:
            self.log(f"  · {name}: no edge matched {edges}, fillet skipped")
            self.fillet_failures.append(f"[{self.current_module}] {ctx}: no edge matched {edges}")
            return None
        try:
            mk = BRepFilletAPI_MakeFillet(body.shape.wrapped)
            for e in found:
                mk.Add(r, e)
            mk.Build()
            if not mk.IsDone():
                raise RuntimeError("BRepFilletAPI_MakeFillet not done")
            shp = cq.Shape.cast(mk.Shape())
            if not _check_valid(shp) or abs(shp.Volume()) < 1e-6:
                raise RuntimeError("fillet result invalid")
        except Exception as ex:
            self.log(f"  · {name}: fillet failed, model unaffected ({ex})")
            self.fillet_failures.append(f"[{self.current_module}] {ctx}: OCC fillet failed "
                                        f"(r = {r:g} mm, {len(found)} edges): {ex}")
            return None
        body.shape = shp
        feat = self._register(Feature("fillet", name, comp, "fillet"))
        return pp_core.Op(feat, [])

    def _sel_values(self, sel):
        kind = sel[0]
        if kind == "circle":
            return (kind, self.ev.length(sel[1], "circle x"), self.ev.length(sel[2], "circle r"))
        if kind == "line_y":
            return (kind, self.ev.length(sel[1], "line_y x"), self.ev.length(sel[2], "line_y z"))
        if kind == "line_x":
            return (kind, self.ev.length(sel[1], "line_x y"), self.ev.length(sel[2], "line_x z"))
        raise ValueError(kind)

    @staticmethod
    def _select_edges(shape, sel):
        """Same matching rules as FusionBackend._select_edges, tolerance 0.05 mm. Seam edges of
        periodic faces are skipped (Fusion/ASM bodies have none)."""
        kind, a, b = sel
        emap = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape.wrapped, TopAbs_EDGE, emap)
        seams = set()
        fexp = TopExp_Explorer(shape.wrapped, TopAbs_FACE)
        while fexp.More():
            f = TopoDS.Face_s(fexp.Current())
            eexp = TopExp_Explorer(f, TopAbs_EDGE)
            while eexp.More():
                e = TopoDS.Edge_s(eexp.Current())
                if BRep_Tool.IsClosed_s(e, f):
                    seams.add(emap.FindIndex(e))
                eexp.Next()
            fexp.Next()
        out = []
        for i in range(1, emap.Extent() + 1):
            if i in seams:
                continue
            e = TopoDS.Edge_s(emap.FindKey(i))
            if BRep_Tool.Degenerated_s(e):
                continue
            ad = BRepAdaptor_Curve(e)
            t = ad.GetType()
            if kind == "circle":
                if t != GeomAbs_Circle:
                    continue
                c = ad.Circle()
                p = c.Location()
                if (abs(p.X() - a) < SEL_TOL and abs(p.Y()) < SEL_TOL and abs(p.Z()) < SEL_TOL
                        and abs(c.Radius() - b) < SEL_TOL):
                    out.append(e)
            else:
                if t != GeomAbs_Line:
                    continue
                s = BRep_Tool.Pnt_s(TopExp.FirstVertex_s(e))
                f = BRep_Tool.Pnt_s(TopExp.LastVertex_s(e))
                if kind == "line_y":
                    ok = (abs(s.X() - a) < SEL_TOL and abs(f.X() - a) < SEL_TOL
                          and abs(s.Z() - b) < SEL_TOL and abs(f.Z() - b) < SEL_TOL)
                else:
                    ok = (abs(s.Y() - a) < SEL_TOL and abs(f.Y() - a) < SEL_TOL
                          and abs(s.Z() - b) < SEL_TOL and abs(f.Z() - b) < SEL_TOL)
                if ok:
                    out.append(e)
        return out

    # ── traversal / reporting ──
    def placement(self, comp):
        """World matrix of a component's first (primary) occurrence, walking up to the root."""
        m = np.eye(4)
        c = comp
        while c is not None and c.parent is not None:
            occ = next((o for o in c.parent.occurrences if o.comp is c and not o.shared), None)
            if occ is not None and occ.transform is not None:
                m = occ.transform @ m
            c = c.parent
        return m

    def iter_bodies(self, comp=None, trsf=None, path=None):
        """Yield (body, 4x4 world matrix, occurrence path) for every live body under comp.
        Starts from comp's own world placement unless trsf is given."""
        comp = comp or self.root
        trsf = self.placement(comp) if trsf is None else trsf
        path = path or comp.name
        for b in comp.bodies:
            if b.valid:
                yield b, trsf, path
        for occ in comp.occurrences:
            m = trsf if occ.transform is None else trsf @ occ.transform
            yield from self.iter_bodies(occ.comp, m, f"{path}/{occ.comp.name}")

    def world_shape(self, body, trsf):
        if trsf is None or np.allclose(trsf, np.eye(4)):
            return body.shape
        return body.shape.moved(_loc(trsf))

    def pen_mass_g(self):
        total = 0.0
        seen = set()
        for b in self.pen_bodies:
            if not b.valid or id(b) in seen:
                continue
            seen.add(id(b))
            total += b.volume / 1000.0 * DENSITY.get(b.material, 0.0)
        return total


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

def _prism(face, dz):
    mk = BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(0, 0, dz), True)
    mk.Build()
    return cq.Shape.cast(mk.Shape())


def fast_bb(shape):
    """Axis-aligned box (cq.BoundBox) without BRepBndLib.AddOptimal — 50x faster, slightly
    loose (fine for overlap pre-filtering)."""
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    box = Bnd_Box()
    BRepBndLib.Add_s(shape.wrapped, box, True)
    return cq.BoundBox(box)


def _bb_overlap(a, b, tol=1e-6):
    return not (a.xmax < b.xmin - tol or b.xmax < a.xmin - tol or a.ymax < b.ymin - tol
                or b.ymax < a.ymin - tol or a.zmax < b.zmin - tol or b.zmax < a.zmin - tol)


def _seg_hits(s, Qs, eps=GEO_EPS):
    """Vectorised: does segment s=(x0,y0,x1,y1) touch any of Qs (n×4)? Touching counts."""
    p = s[:2]
    r = s[2:] - s[:2]
    q = Qs[:, :2]
    sv = Qs[:, 2:] - Qs[:, :2]
    rxs = r[0] * sv[:, 1] - r[1] * sv[:, 0]
    qp = q - p
    qpxr = qp[:, 0] * r[1] - qp[:, 1] * r[0]
    lr = np.linalg.norm(r)
    ls = np.linalg.norm(sv, axis=1)
    hits = np.zeros(len(Qs), dtype=bool)
    nonpar = np.abs(rxs) > 1e-12 * lr * np.maximum(ls, 1e-12)
    t = np.where(nonpar, (qp[:, 0] * sv[:, 1] - qp[:, 1] * sv[:, 0]) / np.where(nonpar, rxs, 1), 0)
    u = np.where(nonpar, qpxr / np.where(nonpar, rxs, 1), 0)
    et, eu = eps / max(lr, 1e-12), eps / np.maximum(ls, 1e-12)
    hits |= nonpar & (t >= -et) & (t <= 1 + et) & (u >= -eu) & (u <= 1 + eu)
    # parallel & collinear overlap, or endpoint proximity
    par = ~nonpar
    if par.any():
        dist_line = np.abs(qpxr) / max(lr, 1e-12)
        col = par & (dist_line < eps)
        t0 = (qp[:, 0] * r[0] + qp[:, 1] * r[1]) / max(lr * lr, 1e-24)
        q1p = Qs[:, 2:] - p
        t1 = (q1p[:, 0] * r[0] + q1p[:, 1] * r[1]) / max(lr * lr, 1e-24)
        lo, hi = np.minimum(t0, t1), np.maximum(t0, t1)
        hits |= col & (hi >= -et) & (lo <= 1 + et)
    return hits


def _seg_point(s, q):
    pts = [s[:2], s[2:], q[:2], q[2:]]
    return np.mean(pts, axis=0)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration (mirrors PlasmaPenNexus.py)
# ─────────────────────────────────────────────────────────────────────────────

def load_modules(names=None, reload=False):
    """Import builder modules from PlasmaPenNexus/. Missing files are skipped; import errors are
    returned as (name, traceback) in the second element."""
    names = names or BUILDER_MODULES
    mods, errors = [], []
    for n in names:
        if not os.path.exists(os.path.join(NEXUS, n + ".py")):
            continue
        try:
            if n in sys.modules and reload:
                m = importlib.reload(sys.modules[n])
            else:
                m = importlib.import_module(n)
            mods.append(m)
        except Exception:
            errors.append((n, traceback.format_exc()))
    return mods, errors


def collect_extra_params(mods):
    return [(m.__name__, list(getattr(m, "EXTRA_PARAMS", []))) for m in mods]


RENDER_NAME = "PlasmaPen Nexus — működés"
ENG_NAME = "PlasmaPen Nexus — engineering"


@dataclass
class ModelResult:
    render: Comp = None
    engineering: Comp = None
    shared: list = field(default_factory=list)
    errors: list = field(default_factory=list)      # (module, stage, kind, message, traceback)


def _call(bk, res, mod, stage, fn, *args, **kw):
    bk.current_module = mod.__name__
    bk.current_stage = stage
    try:
        out = fn(*args, **kw)
        if out is not None and not isinstance(out, (list, tuple)):
            raise BuildError(f"{mod.__name__}.{stage} must return a list of components, "
                             f"got {type(out).__name__}")
        for c in out or []:
            if not isinstance(c, Comp):
                raise BuildError(f"{mod.__name__}.{stage} returned {c!r}, not a component")
        return list(out or [])
    except Exception as e:
        kind = ("expression" if isinstance(e, ExprError) else "profile" if isinstance(
            e, ProfileError) else "fusion-reject" if isinstance(e, BuildError) else
            "occ-preview-only" if isinstance(e, OccError) else "python")
        res.errors.append((mod.__name__, stage, kind, f"{type(e).__name__}: {e}",
                           traceback.format_exc()))
        return []
    finally:
        bk.current_module = None
        bk.current_stage = None


def frames(ev):
    """PlasmaPenNexus._frames for a Y-up document, in mm: render = pen X → world +Y (tip down
    onto the dish), engineering = lying flat at +X beside it."""
    lift = ev.length("standoff + agar_t + dish_wall")
    dx = ev.length("dish_d / 2 + 45 mm")
    r = ev.length("body_r")

    def cs(o, x, y, z):
        m = np.eye(4)
        m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, o
        return m
    render = cs((0, lift, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0))
    eng = cs((dx, r, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
    return render, eng


def build_model(bk, mods, render=True, engineering=True):
    """Mirror of PlasmaPenNexus.run(): head shell, body shell, head/body/internals shared,
    scene — all directly in the render component (mass counted); then count_mass = False,
    cut shells in the engineering component + a second occurrence of every shared comp."""
    res = ModelResult()
    by = {m.__name__: m for m in mods}
    t_render, t_eng = frames(bk.ev)
    res.render = bk.component(None, RENDER_NAME, t_render) if render else None
    res.engineering = bk.component(None, ENG_NAME, t_eng) if engineering else None

    def step(name, fn_name, *args, **kw):
        m = by.get(name)
        if m is None or not hasattr(m, fn_name):
            return []
        stage = fn_name + (f"(cutaway={kw['cutaway']})" if "cutaway" in kw else "")
        return _call(bk, res, m, stage, getattr(m, fn_name), bk, *args, **kw)

    if render:
        bk.count_mass = True
        step("pp_head", "build_shell", res.render, cutaway=False)
        step("pp_body", "build_shell", res.render, cutaway=False)
        for n in ("pp_head", "pp_body", "pp_internals"):
            res.shared += step(n, "build_shared", res.render)
        step("pp_scene", "build_scene", res.render)
    if engineering:
        bk.count_mass = False
        step("pp_head", "build_shell", res.engineering, cutaway=True)
        step("pp_body", "build_shell", res.engineering, cutaway=True)
        for c in res.shared:
            bk.add_existing(res.engineering, c)
        bk.count_mass = True
    # modules outside the orchestrator's list (e.g. a test builder) run like the head
    for m in mods:
        if m.__name__ not in BUILDER_MODULES:
            if render:
                if hasattr(m, "build_shell"):
                    _call(bk, res, m, "build_shell(cutaway=False)", m.build_shell, bk,
                          res.render, cutaway=False)
                if hasattr(m, "build_shared"):
                    sh = _call(bk, res, m, "build_shared", m.build_shared, bk, res.render)
                    res.shared += sh
                    if engineering:
                        for c in sh:
                            bk.add_existing(res.engineering, c)
            if engineering and hasattr(m, "build_shell"):
                bk.count_mass = False
                _call(bk, res, m, "build_shell(cutaway=True)", m.build_shell, bk,
                      res.engineering, cutaway=True)
                bk.count_mass = True
    return res


def _summary(bk, res):
    lines = []
    for comp_name, comp in (("render", res.render), ("engineering", res.engineering)):
        if comp is None:
            continue
        lines.append(f"── {comp_name} ──")
        for b, _, path in bk.iter_bodies(comp):
            lines.append(f"  {path}/{b.name:<28} {b.volume:10.1f} mm³  look={b.look} "
                         f"mat={b.material}{'' if b.pen else '  (scene)'}"
                         f"{'  [' + str(b.lumps) + ' lumps]' if b.lumps > 1 else ''}")
    return "\n".join(lines)


def main(argv):
    names = [a for a in argv if not a.startswith("-")] or BUILDER_MODULES
    mods, imp_err = load_modules(names)
    for n, tb in imp_err:
        print(f"IMPORT ERROR {n}\n{tb}")
    if not mods:
        print("no builder modules found in", NEXUS)
        return 1
    try:
        bk = PreviewBackend(extra_params=collect_extra_params(mods), quiet=True)
    except ExprError as e:
        print(f"PARAMETER ERROR: {e}")
        return 1
    res = build_model(bk, mods)
    print(_summary(bk, res))
    for w in bk.warnings:
        print("WARN", w)
    for f in bk.fillet_failures:
        print("FILLET", f)
    for mod, stage, kind, msg, tb in res.errors:
        print(f"\nERROR [{mod}.{stage}] ({kind}) {msg}\n{tb}")
    print(f"\npen mass {bk.pen_mass_g():.1f} g   errors {len(res.errors) + len(imp_err)}   "
          f"warnings {len(bk.warnings)}   fillet skips {len(bk.fillet_failures)}")
    return 1 if (res.errors or imp_err) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
