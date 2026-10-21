"""PlasmaPen Nexus — modelling core.

Part builders (pp_shell, pp_head, pp_insert, pp_electronics, pp_scene) talk ONLY to the Backend interface
below, never to adsk directly. Two implementations exist:

    FusionBackend   (this file)            builds real parametric features in Fusion
    PreviewBackend  (../tools/preview_backend.py)  builds the same geometry in CadQuery so the
                                            model can be checked and previewed without Fusion

Every coordinate / size is a Fusion expression string ("cp_x0 + 2 mm", "-(standoff)").
FusionBackend turns each sketch point into a fully dimensioned point (horizontal + vertical
dimension to the sketch origin, driven by the expression), so editing any parameter in
Modify → Change Parameters rebuilds the whole model.

Profiles are drawn in a component's XY plane (or an XY plane offset by `plane_z`).
A profile is a list of vertices:
    (x_expr, y_expr)                       a vertex, joined to the previous one by a line
    ("spline", [(x, y), (x, y), ...])      a fitted spline from the previous vertex through
                                           these points; the last point becomes the vertex
The loop closes itself (last vertex → first vertex by a line). Segment i runs from vertex i to
vertex i+1; segment n-1 is the closing line. Do not repeat the first vertex at the end.

Sign convention: an expression may be negative ("-(standoff)") or zero ("0 mm"); the backend
handles both. A point must not cross the sketch origin's axes when parameters change.
"""

import math
import re
import traceback

from pp_params import PARAMS

# ─────────────────────────────────────────────────────────────────────────────
# Expression evaluation (pure Python, used by checks and the preview backend)
# ─────────────────────────────────────────────────────────────────────────────

_UNIT_RE = re.compile(r"(?<=[0-9.)\s])\s*\b(mm|deg)\b")


class ExprEval:
    """Evaluates Fusion-style expressions against the PARAMS table. Lengths → mm, angles → rad."""

    def __init__(self, overrides=None):
        self.values = {}
        overrides = overrides or {}
        for name, expr, unit, _ in PARAMS:
            self.values[name] = self(overrides.get(name, expr))

    def __call__(self, expr):
        if isinstance(expr, (int, float)):
            return float(expr)
        py = str(expr).replace("^", "**")
        py = _UNIT_RE.sub(lambda m: "*__" + m.group(1), py)
        env = {
            "__mm": 1.0, "__deg": math.pi / 180.0, "PI": math.pi,
            "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "atan": math.atan, "asin": math.asin, "acos": math.acos, "abs": abs,
            "floor": math.floor, "ceil": math.ceil, "round": round,
        }
        env.update(self.values)
        return float(eval(py, {"__builtins__": {}}, env))  # noqa: S307 — our own table


def neg(expr):
    """-(expr), for readability in builders."""
    return f"-({expr})"


class Op:
    """Result of a modelling operation: the feature (for patterns) and any new bodies."""

    def __init__(self, feature=None, bodies=None):
        self.feature = feature
        self.bodies = list(bodies or [])

    @property
    def body(self):
        return self.bodies[0] if self.bodies else None


# ─────────────────────────────────────────────────────────────────────────────
# Backend interface
# ─────────────────────────────────────────────────────────────────────────────

class Backend:
    """What a part builder may call. All size arguments are expression strings.

    look      key into pp_looks.LOOKS (render appearance)       e.g. "alu", "peek", "led405"
    material  key into pp_looks.MATERIALS (physical, for mass)   e.g. "aluminum", "peek"
    pen       True if the body is part of the pen (counted in the mass report)
    op        "new" | "cut" | "join" | "intersect"; cut/join/intersect need `targets`
    """

    # ── structure ──
    def component(self, parent, name):
        """New child component of `parent` (None = root). Returns a component handle."""
        raise NotImplementedError

    def add_existing(self, parent, comp):
        """Place another occurrence of an already built component (shared parts)."""
        raise NotImplementedError

    # ── geometry ──
    def revolve(self, comp, name, pts, axis="x", angle="360 deg", plane_z="0 mm",
                op="new", targets=None, look=None, material=None, pen=True):
        """Revolve a closed XY profile. axis="x" → component X axis, or an int = index of a
        straight profile segment to revolve about (e.g. a vertical segment for a button)."""
        raise NotImplementedError

    def extrude(self, comp, name, pts, z0, z1, op="new", targets=None, look=None,
                material=None, pen=True):
        """Extrude a closed profile drawn on the XY plane offset to z0, up to z1 (z1 > z0)."""
        raise NotImplementedError

    def extrude_sym(self, comp, name, pts, width, op="new", targets=None, look=None,
                    material=None, pen=True):
        """Extrude a closed XY profile symmetrically about z = 0, total thickness `width`."""
        raise NotImplementedError

    def pattern_x(self, comp, name, op_result, count, look=None):
        """Circular pattern (360°, `count` instances incl. the original) about the component X
        axis. op_result: an Op from a previous call. A "new" Op patterns its bodies, a cut/join
        Op patterns the feature. Returns an Op whose .bodies are the new copies."""
        raise NotImplementedError

    def fillet(self, comp, name, body, edges, radius):
        """Constant-radius fillet, tangent chain on. edges = list of selectors, each one of
            ("circle", x_expr, r_expr)   circular/arc edge centred on the X axis at x, radius r
            ("line_y", x_expr, z_expr)   straight edge parallel to Y through (x, *, z)
            ("line_x", y_expr, z_expr)   straight edge parallel to X through (*, y, z)
            ("plane_y", y_expr)          every edge lying entirely in the plane y = value
            ("plane_y", y_expr, 1 | -1)  … and only on the z > 0 (1) / z < 0 (-1) side
                                         (no point at z < 0 / z > 0; an edge on z = 0 is out)
            ("plane_x", x_expr)          every edge lying entirely in the plane x = value
            ("op_edges", op)             every edge bounding a face that `op` (an Op from a
                                         previous call) CREATED, resolved in the current state
                                         of `body` (Fusion: feature.faces), so later ops that
                                         reshape those faces are followed
            ("op_edges", op, "outer")    … only the edges shared with a face `op` did NOT
                                         create: the rim between a cut face and the original
                                         body (the edges you break after slicing a flat)
            ("minus", sel_a, sel_b)      the edges sel_a matches that sel_b does not (e.g. a
                                         facet rim without its edge on a joint face:
                                         ("minus", ("op_edges", cut, "outer"), ("plane_x", x)))
        Tolerance 0.05 mm. Only edges of `body` are selected. Returns an Op, or None.
        Cosmetic: a failed fillet is logged, never fatal."""
        raise NotImplementedError

    def chamfer(self, comp, name, body, edges, distance):
        """Equal-distance chamfer, tangent chain on. `edges` = the same selectors as fillet.
        Cosmetic: a failed chamfer is logged, never fatal (returns None)."""
        raise NotImplementedError

    def count(self, expr):
        """Value of a unitless integer expression in the current parameter state, for building
        a row of N features in a loop (e.g. dock pads). The row has as many features as the
        count had when the model was built; a later Fusion parameter edit moves them but does
        not add or remove any."""
        raise NotImplementedError

    # ── convenience (implemented on top of the primitives) ──
    def box(self, comp, name, x0, x1, y0, y1, z0, z1, **kw):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return self.extrude(comp, name, pts, z0, z1, **kw)

    def box_sym(self, comp, name, x0, x1, y0, y1, width, **kw):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return self.extrude_sym(comp, name, pts, width, **kw)

    def tube_x(self, comp, name, x0, x1, r_out, r_in=None, **kw):
        """Cylinder (r_in None) or tube along X between x0 and x1."""
        if r_in is None:
            pts = [(x0, "0 mm"), (x1, "0 mm"), (x1, r_out), (x0, r_out)]
        else:
            pts = [(x0, r_in), (x1, r_in), (x1, r_out), (x0, r_out)]
        return self.revolve(comp, name, pts, **kw)

    def cut_half(self, comp, name, targets):
        """Engineering cutaway: removes z > 0 from `targets`."""
        big = "pen_len + dish_h + standoff + 60 mm"
        return self.box(comp, name, neg("standoff + dish_h + 30 mm"), big,
                        neg("body_od + 10 mm"), "body_od + 10 mm", "0 mm", "body_od + 10 mm",
                        op="cut", targets=targets)

    def log(self, msg):
        print(msg)


# ─────────────────────────────────────────────────────────────────────────────
# Fusion implementation
# ─────────────────────────────────────────────────────────────────────────────

class FusionBackend(Backend):
    EPS = 1e-6  # cm

    def __init__(self, app, design, logger):
        import adsk.core
        import adsk.fusion
        self.core = adsk.core
        self.fusion = adsk.fusion
        self.app = app
        self.design = design
        self.root = design.rootComponent
        self.um = design.unitsManager
        self._log = logger
        self._planes = {}
        self._appearances = {}
        self._materials = {}
        self._lib_appearances = None
        self._lib_materials = None
        self.pen_bodies = []
        self.count_mass = True  # orchestrator turns this off while building the engineering copy
        self._pen_tokens = set()
        self.failures = []

    # ── helpers ──
    def log(self, msg):
        self._log(msg)

    def vi(self, expr):
        return self.core.ValueInput.createByString(str(expr))

    def val(self, expr):
        """Expression → internal units (cm or rad)."""
        v = self.um.evaluateExpression(str(expr), "mm")
        if v == -1 and self.um.evaluateExpression(f"({expr}) + 1 mm", "mm") == -1:
            raise ValueError(f"Bad expression: {expr}")
        return v

    def count(self, expr):
        v = self.um.evaluateExpression(str(expr), "")
        n = int(round(v))
        if abs(v - n) > 1e-6 or n < 0:
            raise ValueError(f"count '{expr}' = {v} is not a non-negative integer")
        return n

    def _op(self, op):
        F = self.fusion.FeatureOperations
        return {
            "new": F.NewBodyFeatureOperation,
            "cut": F.CutFeatureOperation,
            "join": F.JoinFeatureOperation,
            "intersect": F.IntersectFeatureOperation,
        }[op]

    def _plane(self, comp, plane_z):
        key = (comp.id, str(plane_z))
        if self._is_zero_literal(plane_z):
            return comp.xYConstructionPlane
        if key in self._planes:
            return self._planes[key]
        inp = comp.constructionPlanes.createInput()
        inp.setByOffset(comp.xYConstructionPlane, self.vi(plane_z))
        plane = comp.constructionPlanes.add(inp)
        plane.name = f"z = {plane_z}"
        plane.isLightBulbOn = False
        self._planes[key] = plane
        return plane

    @staticmethod
    def _is_zero_literal(expr):
        return str(expr).replace(" ", "") in ("0", "0mm", "0.0mm", "0.0")

    @staticmethod
    def _magnitude_expr(expr, value):
        e = str(expr).strip()
        if value >= 0:
            return e
        return f"-({e})"

    def _sketch_axes(self, sk):
        """Which component axis each sketch axis runs along: ((src, sign), (src, sign)) with
        src 0 = X, 1 = Y. A sketch on the XY plane or an XY offset is ((0, 1), (1, 1)).
        Read from Sketch.transform (component space, the sketch is never a proxy here) rather
        than assumed, so a flipped plane cannot silently mirror a part."""
        identity = ((0, 1.0), (1, 1.0))
        try:
            m = sk.transform.asArray()  # row-major 4x4
            cols = ((m[0], m[4], m[8]), (m[1], m[5], m[9]))
            out = []
            for c in cols:
                i = max(range(3), key=lambda k: abs(c[k]))
                if i == 2 or abs(abs(c[i]) - 1.0) > 1e-6:
                    self.log(f"  · {sk.name}: unexpected sketch transform, using XY mapping")
                    return identity
                out.append((i, 1.0 if c[i] > 0 else -1.0))
            if out[0][0] == out[1][0]:
                return identity
            return tuple(out)
        except Exception:
            return identity

    def _point(self, sk, axes, xe, ye):
        """Sketch point at component (xe, ye), fully fixed: one horizontal + one vertical
        driving dimension to the sketch origin, or a horizontal/vertical-points constraint where
        the coordinate is zero."""
        model = (self.val(xe), self.val(ye))
        exprs = (xe, ye)
        (su, gu), (sv, gv) = axes
        u, v = model[su] * gu, model[sv] * gv
        sp = sk.sketchPoints.add(self.core.Point3D.create(u, v, 0))
        D = self.fusion.DimensionOrientations
        dims = sk.sketchDimensions
        gc = sk.geometricConstraints
        origin = sk.originPoint
        if abs(u) < self.EPS and abs(v) < self.EPS:
            gc.addCoincident(sp, origin)
            return sp
        if abs(u) < self.EPS:
            gc.addVerticalPoints(origin, sp)
        else:
            d = dims.addDistanceDimension(origin, sp, D.HorizontalDimensionOrientation,
                                          self.core.Point3D.create(u / 2, v + 0.3, 0), True)
            d.parameter.expression = self._magnitude_expr(exprs[su], model[su])
        if abs(v) < self.EPS:
            gc.addHorizontalPoints(origin, sp)
        else:
            d = dims.addDistanceDimension(origin, sp, D.VerticalDimensionOrientation,
                                          self.core.Point3D.create(u + 0.3, v / 2, 0), True)
            d.parameter.expression = self._magnitude_expr(exprs[sv], model[sv])
        return sp

    def _profile_sketch(self, comp, name, pts, plane_z="0 mm"):
        """Draws the closed loop. Returns (sketch, profile, segments)."""
        sk = comp.sketches.add(self._plane(comp, plane_z))
        sk.name = name
        axes = self._sketch_axes(sk)
        sk.isComputeDeferred = True
        lines = sk.sketchCurves.sketchLines
        splines = sk.sketchCurves.sketchFittedSplines
        segments = []
        first = None
        prev = None
        for item in pts:
            if isinstance(item, tuple) and len(item) == 2 and item[0] == "spline":
                if prev is None:
                    raise ValueError(f"{name}: a profile cannot start with a spline segment")
                fit = self.core.ObjectCollection.create()
                fit.add(prev)
                last = prev
                for (xe, ye) in item[1]:
                    last = self._point(sk, axes, xe, ye)
                    fit.add(last)
                segments.append(splines.add(fit))
                prev = last
                continue
            xe, ye = item
            sp = self._point(sk, axes, xe, ye)
            if prev is None:
                first = sp
            else:
                segments.append(lines.addByTwoPoints(prev, sp))
            prev = sp
        segments.append(lines.addByTwoPoints(prev, first))
        sk.isComputeDeferred = False
        if sk.profiles.count == 0:
            raise RuntimeError(f"{name}: profile did not close")
        best = None
        best_area = -1.0
        for i in range(sk.profiles.count):
            prof = sk.profiles.item(i)
            area = prof.areaProperties(self.fusion.CalculationAccuracy.LowCalculationAccuracy).area
            if area > best_area:
                best, best_area = prof, area
        sk.isVisible = False
        return sk, best, segments

    def _finish(self, feature, name, op, look, material, pen):
        bodies = []
        if op == "new":
            for i in range(feature.bodies.count):
                b = feature.bodies.item(i)
                b.name = name if feature.bodies.count == 1 else f"{name} {i + 1}"
                self._dress(b, look, material)
                bodies.append(b)
                if pen and self.count_mass:
                    self.pen_bodies.append(b)
                    self._pen_tokens.add(b.entityToken)
        feature.name = name[:60]
        return Op(feature, bodies)

    def _participants(self, inp, op, targets):
        if op != "new":
            if not targets:
                raise ValueError("cut/join/intersect needs targets")
            inp.participantBodies = list(targets)

    # ── structure ──
    def component(self, parent, name, transform=None):
        parent = parent or self.root
        m = transform or self.core.Matrix3D.create()
        occ = parent.occurrences.addNewComponent(m)
        occ.component.name = name
        return occ.component

    def add_existing(self, parent, comp):
        parent = parent or self.root
        return parent.occurrences.addExistingComponent(comp, self.core.Matrix3D.create())

    # ── geometry ──
    def revolve(self, comp, name, pts, axis="x", angle="360 deg", plane_z="0 mm",
                op="new", targets=None, look=None, material=None, pen=True):
        sk, prof, segs = self._profile_sketch(comp, name, pts, plane_z)
        ax = comp.xConstructionAxis if axis == "x" else segs[int(axis)]
        feats = comp.features.revolveFeatures
        inp = feats.createInput(prof, ax, self._op(op))
        inp.setAngleExtent(False, self.vi(angle))
        self._participants(inp, op, targets)
        return self._finish(feats.add(inp), name, op, look, material, pen)

    def extrude(self, comp, name, pts, z0, z1, op="new", targets=None, look=None,
                material=None, pen=True):
        sk, prof, _ = self._profile_sketch(comp, name, pts, z0)
        feats = comp.features.extrudeFeatures
        inp = feats.createInput(prof, self._op(op))
        dist = str(z1) if self._is_zero_literal(z0) else f"({z1}) - ({z0})"
        inp.setDistanceExtent(False, self.vi(dist))
        self._participants(inp, op, targets)
        return self._finish(feats.add(inp), name, op, look, material, pen)

    def extrude_sym(self, comp, name, pts, width, op="new", targets=None, look=None,
                    material=None, pen=True):
        sk, prof, _ = self._profile_sketch(comp, name, pts)
        feats = comp.features.extrudeFeatures
        inp = feats.createInput(prof, self._op(op))
        try:
            inp.setSymmetricExtent(self.vi(width), True, self.vi("0 deg"))
        except TypeError:
            inp.setSymmetricExtent(self.vi(width), True)
        self._participants(inp, op, targets)
        return self._finish(feats.add(inp), name, op, look, material, pen)

    def pattern_x(self, comp, name, op_result, count, look=None):
        coll = self.core.ObjectCollection.create()
        is_bodies = bool(op_result.bodies)
        if is_bodies:
            for b in op_result.bodies:
                coll.add(b)
        else:
            coll.add(op_result.feature)
        feats = comp.features.circularPatternFeatures
        inp = feats.createInput(coll, comp.xConstructionAxis)
        inp.quantity = self.vi(count)
        inp.totalAngle = self.vi("360 deg")
        inp.isSymmetric = False
        feat = feats.add(inp)
        feat.name = name[:60]
        new = []
        if is_bodies:
            src = set(b.entityToken for b in op_result.bodies)
            counted = any(t in self._pen_tokens for t in src)
            for i in range(feat.bodies.count):
                b = feat.bodies.item(i)
                if b.entityToken in src:
                    continue
                b.name = f"{name} {len(new) + 2}"
                if look:
                    self._dress(b, look, None)
                new.append(b)
                if counted:
                    self.pen_bodies.append(b)
                    self._pen_tokens.add(b.entityToken)
        return Op(feat, new)

    def _edge_collection(self, body, edges):
        """ObjectCollection of the edges of `body` matched by any selector, each edge once
        (tempId is unique within one body and stable while the body is not modified)."""
        coll = self.core.ObjectCollection.create()
        seen = set()
        for sel in edges:
            for e in self._select_edges(body, sel):
                if e.tempId in seen:
                    continue
                seen.add(e.tempId)
                coll.add(e)
        return coll

    def fillet(self, comp, name, body, edges, radius):
        try:
            coll = self._edge_collection(body, edges)
            if coll.count == 0:
                self.log(f"  · {name}: no edge matched {edges}, fillet skipped")
                return None
            feats = comp.features.filletFeatures
            inp = feats.createInput()
            try:
                inp.edgeSetInputs.addConstantRadiusEdgeSet(coll, self.vi(radius), True)
            except AttributeError:
                inp.addConstantRadiusEdgeSet(coll, self.vi(radius), True)
            feat = feats.add(inp)
            feat.name = name[:60]
            return Op(feat, [])
        except Exception:  # cosmetic only
            self.log(f"  · {name}: fillet failed, model unaffected\n{traceback.format_exc(limit=1)}")
            return None

    def chamfer(self, comp, name, body, edges, distance):
        try:
            coll = self._edge_collection(body, edges)
            if coll.count == 0:
                self.log(f"  · {name}: no edge matched {edges}, chamfer skipped")
                return None
            feats = comp.features.chamferFeatures
            create2 = getattr(feats, "createInput2", None)
            if create2 is not None:  # December 2020+: edge sets
                inp = create2()
                if inp.chamferEdgeSets.addEqualDistanceChamferEdgeSet(
                        coll, self.vi(distance), True) is False:
                    raise RuntimeError("addEqualDistanceChamferEdgeSet returned False")
            else:  # older Fusion: one edge set per input
                inp = feats.createInput(coll, True)
                if inp.setToEqualDistance(self.vi(distance)) is False:
                    raise RuntimeError("setToEqualDistance returned False")
            feat = feats.add(inp)
            feat.name = name[:60]
            return Op(feat, [])
        except Exception:  # cosmetic only
            self.log(f"  · {name}: chamfer failed, model unaffected\n"
                     f"{traceback.format_exc(limit=1)}")
            return None

    def _edge_points(self, e, n=8):
        """n + 1 points spread over the edge's parameter range (cm)."""
        ev = e.evaluator
        ok, t0, t1 = ev.getParameterExtents()
        if not ok:
            return []
        ok, pts = ev.getPointsAtParameters([t0 + (t1 - t0) * i / n for i in range(n + 1)])
        return list(pts) if ok else []

    @staticmethod
    def _z_side_ok(pts, z_sign, tol):
        if z_sign is None:
            return True
        zs = [p.z * z_sign for p in pts]
        return min(zs) > -tol and max(zs) > tol

    def _own_face(self, body, face):
        """`face` (from some feature's .faces) as a face of `body`, or None. Matched by tempId
        inside `body`, confirmed by area + a point on the face, so a face of another body that
        happens to carry the same tempId is never taken (entity tokens must not be compared)."""
        try:
            cands = body.findByTempId(face.tempId)
        except Exception:
            return None
        p = face.pointOnFace
        for c in cands or []:
            f = self.fusion.BRepFace.cast(c)
            if f is None:
                continue
            if abs(f.area - face.area) <= 1e-9 * max(1.0, face.area) and \
                    f.pointOnFace.distanceTo(p) < 1e-6:
                return f
        return None

    def _op_edges(self, body, op_result, outer):
        feat = getattr(op_result, "feature", None)
        if feat is None:
            raise ValueError(f"op_edges: {op_result!r} carries no feature")
        mine = {}
        for f in feat.faces:  # faces created by the feature, in the current model state
            own = self._own_face(body, f)
            if own is not None:
                mine[own.tempId] = own
        out = []
        seen = set()
        for f in mine.values():
            for e in f.edges:
                if e.tempId in seen or e.isDegenerate:
                    continue
                if outer and all(g.tempId in mine for g in e.faces):
                    continue
                seen.add(e.tempId)
                out.append(e)
        return out

    def _select_edges(self, body, sel):
        kind = sel[0]
        tol = 0.005  # cm = 0.05 mm
        out = []
        if kind == "minus":
            if len(sel) != 3:
                raise ValueError(f"bad selector {sel!r}: ('minus', sel_a, sel_b)")
            drop = set(e.tempId for e in self._select_edges(body, sel[2]))
            return [e for e in self._select_edges(body, sel[1]) if e.tempId not in drop]
        if kind == "plane_x":
            if len(sel) != 2:
                raise ValueError(f"bad selector {sel!r}: ('plane_x', x_expr)")
            x = self.val(sel[1])
            for e in body.edges:
                if e.isDegenerate:
                    continue
                bb = e.boundingBox
                if bb.minPoint.x > x + tol or bb.maxPoint.x < x - tol:  # cheap reject
                    continue
                pts = self._edge_points(e)
                if pts and all(abs(p.x - x) < tol for p in pts):
                    out.append(e)
            return out
        if kind == "op_edges":
            if len(sel) not in (2, 3) or (len(sel) == 3 and sel[2] != "outer"):
                raise ValueError(f"bad selector {sel!r}: ('op_edges', op[, 'outer'])")
            return self._op_edges(body, sel[1], len(sel) == 3)
        if kind == "plane_y":
            z_sign = sel[2] if len(sel) == 3 else None
            if len(sel) not in (2, 3) or z_sign not in (None, 1, -1) or isinstance(z_sign, bool):
                raise ValueError(f"bad selector {sel!r}: ('plane_y', y_expr[, 1 | -1])")
            y = self.val(sel[1])
            for e in body.edges:
                if e.isDegenerate:
                    continue
                bb = e.boundingBox  # cheap reject before sampling
                if bb.minPoint.y > y + tol or bb.maxPoint.y < y - tol:
                    continue
                pts = self._edge_points(e)
                if pts and all(abs(p.y - y) < tol for p in pts) and \
                        self._z_side_ok(pts, z_sign, tol):
                    out.append(e)
            return out
        c3 = self.core.Circle3D.classType()
        a3 = self.core.Arc3D.classType()
        l3 = self.core.Line3D.classType()
        if kind == "circle":
            x, r = self.val(sel[1]), self.val(sel[2])
            for e in body.edges:
                g = e.geometry
                if g.objectType in (c3, a3):
                    c = g.center
                    if (abs(c.x - x) < tol and abs(c.y) < tol and abs(c.z) < tol
                            and abs(g.radius - r) < tol):
                        out.append(e)
        elif kind in ("line_y", "line_x"):
            a, b = self.val(sel[1]), self.val(sel[2])
            for e in body.edges:
                g = e.geometry
                if g.objectType != l3:
                    continue
                s, t = e.startVertex.geometry, e.endVertex.geometry
                if kind == "line_y":
                    ok = (abs(s.x - a) < tol and abs(t.x - a) < tol
                          and abs(s.z - b) < tol and abs(t.z - b) < tol)
                else:
                    ok = (abs(s.y - a) < tol and abs(t.y - a) < tol
                          and abs(s.z - b) < tol and abs(t.z - b) < tol)
                if ok:
                    out.append(e)
        return out

    # ── looks & materials ──
    def _library_items(self, kind):
        items = []
        libs = self.app.materialLibraries
        for i in range(libs.count):
            lib = libs.item(i)
            coll = lib.appearances if kind == "appearance" else lib.materials
            try:
                n = coll.count
            except Exception:
                continue
            for j in range(n):
                it = coll.item(j)
                items.append((it.name.lower(), it))
        return items

    def _find(self, kind, match_lists):
        if kind == "appearance":
            if self._lib_appearances is None:
                self._lib_appearances = self._library_items("appearance")
            pool = self._lib_appearances
        else:
            if self._lib_materials is None:
                self._lib_materials = self._library_items("material")
            pool = self._lib_materials
        for words in match_lists:
            words = [w.lower() for w in words]
            for name, it in pool:
                if all(w in name for w in words):
                    return it
        return None

    def appearance(self, key):
        if key in self._appearances:
            return self._appearances[key]
        import pp_looks
        spec = pp_looks.LOOKS[key]
        src = self._find("appearance", spec["match"])
        if src is None:
            self.log(f"  · look '{key}': no library appearance matched, left default")
            self._appearances[key] = None
            return None
        app_ = self.design.appearances.addByCopy(src, f"PPN {spec.get('label', key)}")
        pp_looks.tune(app_, spec, self.core, self.log)
        self._appearances[key] = app_
        return app_

    def material(self, key):
        if key in self._materials:
            return self._materials[key]
        import pp_looks
        mat = self._find("material", pp_looks.MATERIALS[key])
        if mat is None:
            self.log(f"  · material '{key}': not found in libraries")
        self._materials[key] = mat
        return mat

    def _dress(self, body, look, material):
        if material:
            m = self.material(material)
            if m is not None:
                try:
                    body.material = m
                except Exception:
                    self.log(f"  · {body.name}: material '{material}' rejected")
        if look:
            a = self.appearance(look)
            if a is not None:
                body.appearance = a

    # ── reporting ──
    def pen_mass_g(self):
        total = 0.0
        seen = set()
        for b in self.pen_bodies:
            try:
                if not b.isValid:
                    continue
                tok = b.entityToken
                if tok in seen:
                    continue
                seen.add(tok)
                total += b.physicalProperties.mass * 1000.0
            except Exception:
                continue
        return total
