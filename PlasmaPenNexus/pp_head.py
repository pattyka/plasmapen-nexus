"""PlasmaPen Nexus — PEEK nose + liner (shell) and the optics behind the nose window (shared).

Frame: X = pen axis, x = 0 nozzle face, +X toward the back. Y = up (facet, camera side),
Z = side. Angles around X run from +Y toward +Z.

Shell: ONE PEEK part, "Orr + bélés (PEEK)", one revolve of a single closed half-section.
  · x 0 … nose_len   the visible black nose: a slight taper from head_nose_r0 at the face to
                     tip_r where it enters the alu (so it reads as a drawn-out tip, not a plug),
                     0.5 mm round on the face edge. Face: PEEK collar r nozzle_d/2 … collar_r,
                     window recess r collar_r … win_ro × win_t, PEEK rim r win_ro … head_nose_r0.
  · behind it        the outside follows the unibody's inner surface (pp_body.inner_profile_pts)
                     head_alu_c inside it, back to head_len, so the liner slides in from the back
                     and fills the taper.
  · inside           nozzle bore r nozzle_d/2 to nozzle_len, funnel to liner_ri at funnel_x1,
                     liner bore r liner_ri open at the back (piezo leads, air).
Pockets for the camera and the LEDs are cut into the recess floor (x = win_t), so every optical
part sits directly behind the glass.

Camera pocket in two steps: a round lens bore (Ø cam_d + 2·head_fit) the full pocket depth and
the square module seat (cam_mod + 2·head_fit) at its back, placed as far back as the funnel
allows while keeping head_cam_wall under the seat (head_cam_x1_funnel), and never in front of
the LED pockets. head_chk_cam ≥ 0 says the seat corners also keep head_cam_wall to the outside;
it is measured against head_out_r, the smallest radius the PEEK outside has from the seat front
back (the nose taper there, or tip_r: behind nose_len the outside follows the alu, which only
opens up), so it holds wherever the seat lands.

Wiring (camera + LEDs → main PCB): an axial channel at θ = 0 inside the liner wall, from the
camera seat to the back face. Its top is derived from head_out_r — the smallest outside radius
the PEEK has anywhere along the channel — so it can never break through to the alu or the nose,
whatever the unibody profile does. HV rule (air ~3 kV/mm, PEEK ~20 kV/mm vs 15 kV):
channel ↔ bar ≥ head_hv_total with ≥ head_hv_peek of it solid PEEK; head_chk_hv ≥ 0 says so.

LED seeds sit at θ = +180°/(2·led_pairs) (405 nm) and θ = −180°/(2·led_pairs) (660 nm). The
mirrored 660 nm seed is the same set of positions as 3·180°/(2·led_pairs) after patterning, but
its sketch centre never lands on the sketch X axis (cos θ > 0, sin θ ≠ 0 for every
led_pairs ≥ 2), so changing led_pairs in Fusion cannot leave a zero-pinned point behind.
"""

from pp_body import inner_profile_pts
from pp_core import neg


def _max(a, b):
    """max(a, b) in plain Fusion arithmetic (ExprEval has no max())."""
    return f"(({a}) + ({b}) + abs(({a}) - ({b}))) / 2"


def _min(a, b):
    return f"(({a}) + ({b}) - abs(({a}) - ({b}))) / 2"


EXTRA_PARAMS = [
    ("head_fit", "0.1 mm", "mm", "Illesztési hézag (sugárban) a zsebekben"),
    ("head_alu_c", "body_nose_gap", "mm", "= PEEK ↔ alu hézag (sugárban), az orr nyílásával azonos"),
    ("head_nose_taper", "0.2 mm", "mm", "Orr kúposság: ennyivel kisebb a sugár a homlokon"),
    ("head_nose_r0", "tip_r - head_nose_taper", "mm", "= orr sugara a homloklapon"),
    ("head_nose_fillet", "0.5 mm", "mm", "Orr homlokél lekerekítés"),
    # ── kamera ──
    ("head_cam_wall", "1 mm", "mm", "Min. PEEK fal a kamera fészek körül"),
    ("head_cam_body_t", "2.5 mm", "mm", "OV5640 modul test vastagság (objektív nélkül)"),
    ("head_cam_pcb_t", "0.5 mm", "mm", "Kamera szenzor NYÁK vastagság"),
    ("head_cam_len", "head_cam_body_t + head_cam_pcb_t + 2 * head_fit", "mm",
     "= modul fészek hossza"),
    ("head_cam_x1_funnel",
     "nozzle_len + (ring_r - cam_mod / 2 - head_fit - head_cam_wall - nozzle_d / 2)"
     " * (funnel_x1 - nozzle_len) / (liner_ri - nozzle_d / 2)",
     "mm", "= eddig hagy a tölcsér head_cam_wall falat a fészek alatt"),
    ("head_cam_x0",
     _max("head_cam_x1_funnel - head_cam_len", "win_t + led_h + 0.3 mm + head_cam_wall"),
     "mm", "= kamera modul fészek eleje"),
    ("head_cam_x1", _max("win_t + cam_depth", "head_cam_x0 + head_cam_len"), "mm",
     "= kamera zseb hátulja"),
    ("head_out_r", _min("tip_r", "head_nose_r0 + head_nose_taper * head_cam_x0 / nose_len"), "mm",
     "= legkisebb külső PEEK sugár a kamera fészektől hátra"),
    ("head_chk_cam",
     "head_out_r - head_cam_wall - sqrt((ring_r + cam_mod / 2 + head_fit) ^ 2"
     " + (cam_mod / 2 + head_fit) ^ 2)",
     "mm", "ELLENŐRZÉS: kamera fészek sarka ↔ orr felület ≥ head_cam_wall, ≥ 0 kell"),
    ("head_cam_rim", "0.5 mm", "mm", "Objektív perem a lencse körül"),
    ("head_cam_glass_t", "0.5 mm", "mm", "Kamera fedőlencse vastagság"),
    ("head_cam_recess", "0.3 mm", "mm", "Lencse besüllyesztése az objektív elejétől"),
    # ── kábelcsatorna (kamera + LED → fő NYÁK), felül θ = 0 ──
    ("head_wire_w", "4 mm", "mm", "Kábelcsatorna szélesség (Z) — hajtott FPC"),
    ("head_wire_h", "1 mm", "mm", "Kábelcsatorna magasság (Y)"),
    ("head_wire_cover", "0.5 mm", "mm", "Min. PEEK a csatorna sarka fölött"),
    ("head_wire_y1", "sqrt((head_out_r - head_wire_cover) ^ 2 - (head_wire_w / 2) ^ 2)", "mm",
     "= kábelcsatorna teteje"),
    ("head_wire_y0", "head_wire_y1 - head_wire_h", "mm", "= kábelcsatorna alja"),
    ("head_hv_total", "6 mm", "mm", "Előírt min. távolság csatorna ↔ piezo rúd (levegő + PEEK)"),
    ("head_hv_peek", "1.2 mm", "mm", "Előírt min. tömör PEEK ebből (a csatorna alatt)"),
    ("head_chk_hv",
     _min("head_wire_y0 - cp_h / 2 - head_hv_total", "head_wire_y0 - liner_ri - head_hv_peek"),
     "mm", "ELLENŐRZÉS: csatorna ↔ rúd ≥ head_hv_total és PEEK ≥ head_hv_peek, ≥ 0 kell"),
]

# ── shared expressions ───────────────────────────────────────────────────────
NOZZLE_R = "nozzle_d / 2"

CAM_X1 = "head_cam_x1"                   # back of the camera pocket
CAM_LENS_R = "cam_d / 2 + head_fit"      # lens bore radius
CAM_SEAT = "cam_mod / 2 + head_fit"      # half side of the square module seat

LED_X1 = "win_t + led_h"                 # LED lens back face
LED_POCKET_X1 = "win_t + led_h + 0.3 mm"
LED_POCKET_R = "led_d / 2 + head_fit"

WIRE_HALF = "head_wire_w / 2"

# θ of each LED seed (see module docstring for the mirrored 660 nm seed)
LED_SEEDS = (
    ("405", "led405", "180 deg / (2 * led_pairs)"),
    ("660", "led660", "-(180 deg / (2 * led_pairs))"),
)


def _p(expr):
    return f"({expr})"


def axial_rect(x0, x1, yc, r):
    """Rectangle x0…x1 × yc…yc+r. Segment 0 lies on y = yc: revolve with axis=0 for a
    cylinder of radius r whose axis is parallel to X through (yc, plane_z)."""
    top = f"{_p(yc)} + {_p(r)}"
    return [(x0, yc), (x1, yc), (x1, top), (x0, top)]


def led_centre(theta):
    """(y, z) expressions of an LED centre on the ring_r circle at angle theta."""
    return f"ring_r * cos({theta})", f"ring_r * sin({theta})"


def _inset(pt):
    x, r = pt
    return (x, f"{_p(r)} - head_alu_c")


def liner_outside():
    """The unibody's inner surface, head_alu_c inside it, walked from the back (head_len) to
    the front (nose_len), as profile items. Splines are reversed point by point: a spline item
    runs from the previous vertex through its points, so reversing moves the previous vertex
    to the end."""
    src = list(inner_profile_pts())
    if not src or src[0][0] == "spline":
        raise ValueError("inner_profile_pts() must start with a plain vertex")
    # flatten to (kind, point) with kind "v" (vertex reached by a line) or "s<k>" (spline k)
    seq = []
    for k, item in enumerate(src):
        if item[0] == "spline":
            for p in item[1]:
                seq.append((k, p))
        else:
            seq.append((None, item))
    out = []
    i = len(seq) - 1
    out.append(_inset(seq[i][1]))
    while i > 0:
        k = seq[i][0]
        if k is None:
            out.append(_inset(seq[i - 1][1]))
            i -= 1
            continue
        # walk back over spline k: its fit points (except the last, already emitted) and the
        # vertex before it become one reversed spline
        j = i
        while j - 1 >= 0 and seq[j - 1][0] == k:
            j -= 1
        pts = [_inset(seq[m][1]) for m in range(i - 1, j - 1, -1)] + [_inset(seq[j - 1][1])]
        out.append(("spline", pts))
        i = j - 1
    return out


def shell_profile():
    """Closed half-section of the PEEK nose + liner, y ≥ 0, revolved about X."""
    return [
        ("0 mm", NOZZLE_R),                              # collar inner edge
        ("nozzle_len", NOZZLE_R),                        # nozzle bore
        ("funnel_x1", "liner_ri"),                       # funnel
        ("head_len", "liner_ri"),                        # liner bore, open at the back
        *liner_outside(),                                # back face, then along the alu
        ("0 mm", "head_nose_r0"),                        # nose, a slight taper to tip_r
        ("0 mm", "win_ro"),                              # rim face
        ("win_t", "win_ro"),                             # recess outer wall
        ("win_t", "collar_r"),                           # recess floor
        ("0 mm", "collar_r"),                            # recess inner wall → collar face
    ]


def camera_seat_box():
    """(x0, x1, y0, y1, z0, z1) of the square module seat cut into the nose."""
    return ("head_cam_x0", CAM_X1,
            f"ring_r - {_p(CAM_SEAT)}", f"ring_r + {_p(CAM_SEAT)}",
            neg(CAM_SEAT), CAM_SEAT)


# ── camera stack (shared) ────────────────────────────────────────────────────
CAM_FRONT = "win_t + head_fit"                               # barrel front, behind the glass
CAM_GLASS_X0 = f"{CAM_FRONT} + head_cam_recess"
CAM_GLASS_X1 = f"{CAM_GLASS_X0} + head_cam_glass_t"
CAM_GLASS_R = "cam_d / 2 - head_cam_rim"
CAM_BODY_X0 = "head_cam_x0 + head_fit"
CAM_PCB_X1 = f"{CAM_X1} - head_fit"
CAM_BODY_X1 = f"{CAM_PCB_X1} - head_cam_pcb_t"


def camera_barrel_profile():
    """Lens barrel: solid behind the glass, a rim around it in front. Segment 0 is the
    camera axis (y = ring_r)."""
    rin = f"ring_r + {_p(CAM_GLASS_R)}"
    rout = "ring_r + cam_d / 2"
    return [
        (CAM_GLASS_X1, "ring_r"),
        (CAM_BODY_X0, "ring_r"),
        (CAM_BODY_X0, rout),
        (CAM_FRONT, rout),
        (CAM_FRONT, rin),
        (CAM_GLASS_X1, rin),
    ]


# ── builders ─────────────────────────────────────────────────────────────────

def build_shell(bk, parent, cutaway):
    comp = bk.component(parent, "Orr + bélés (PEEK)")
    peek = bk.revolve(comp, "Orr + bélés", shell_profile(), look="peek", material="peek").body

    bk.fillet(comp, "Orr él", peek, [("circle", "0 mm", "head_nose_r0")],
              "head_nose_fillet")

    bk.revolve(comp, "Kamera furat", axial_rect("win_t", CAM_X1, "ring_r", CAM_LENS_R),
               axis=0, op="cut", targets=[peek])
    x0, x1, y0, y1, z0, z1 = camera_seat_box()
    bk.box(comp, "Kamera fészek", x0, x1, y0, y1, z0, z1, op="cut", targets=[peek])

    for colour, _look, theta in LED_SEEDS:
        yc, zc = led_centre(theta)
        cut = bk.revolve(comp, f"LED zseb {colour}",
                         axial_rect("win_t", LED_POCKET_X1, yc, LED_POCKET_R),
                         axis=0, plane_z=zc, op="cut", targets=[peek])
        bk.pattern_x(comp, f"LED zsebek {colour}", cut, "led_pairs")

    bk.box(comp, "Kábelcsatorna", "head_cam_x0", "head_len + 1 mm", "head_wire_y0",
           "head_wire_y1", neg(WIRE_HALF), WIRE_HALF, op="cut", targets=[peek])

    if cutaway:
        bk.cut_half(comp, "Metszet", [peek])
    return [comp]


def build_shared(bk, parent):
    comps = []

    win = bk.component(parent, "Üveggyűrű")
    bk.revolve(win, "Üveggyűrű",
               [("0 mm", "collar_r"), ("win_t", "collar_r"), ("win_t", "win_ro"),
                ("0 mm", "win_ro")],
               look="glass_window", material="glass")
    comps.append(win)

    for colour, look, theta in LED_SEEDS:
        comp = bk.component(parent, f"LED {colour} nm")
        yc, zc = led_centre(theta)
        seed = bk.revolve(comp, f"LED {colour} nm",
                          axial_rect("win_t", LED_X1, yc, "led_d / 2"),
                          axis=0, plane_z=zc, look=look, material="plastic")
        bk.pattern_x(comp, f"LED {colour} nm", seed, "led_pairs", look=look)
        comps.append(comp)

    cam = bk.component(parent, "Kamera (OV5640)")
    bk.revolve(cam, "Lencse", axial_rect(CAM_GLASS_X0, CAM_GLASS_X1, "ring_r", CAM_GLASS_R),
               axis=0, look="lens", material="glass")
    bk.revolve(cam, "Objektív", camera_barrel_profile(), axis=0,
               look="plastic_black", material="plastic")
    half = "cam_mod / 2"
    bk.box(cam, "Modul", CAM_BODY_X0, CAM_BODY_X1, f"ring_r - {half}", f"ring_r + {half}",
           neg(half), half, look="plastic_black", material="plastic")
    bk.box(cam, "Szenzor NYÁK", CAM_BODY_X1, CAM_PCB_X1, f"ring_r - {half}",
           f"ring_r + {half}", neg(half), half, look="pcb", material="fr4")
    comps.append(cam)

    return comps
