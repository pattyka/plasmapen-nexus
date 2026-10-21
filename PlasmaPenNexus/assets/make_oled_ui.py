"""Renders oled_ui.png — the 1.1" colour AMOLED (YX011T90332, 294 × 126 landscape,
active area 25.578 × 10.962 mm) during a treatment.

    uv run --python 3.12 --with pillow --with numpy python make_oled_ui.py

Left: the camera's live fluorescence map of the wound patch under 405 nm (porphyrin red,
pyoverdine green), the plasma spot on it and the dose arc around the spot. Right: dose, time
remaining, battery, and the change in each fluorescence signal since the start.
Drawn at 4× and downsampled to 2340 × 1003 so curves and type stay crisp.
"""

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 2340, 1003                 # 25.578 × 10.962 mm, ≈ 91.5 px/mm
S = 4                             # supersampling for vector drawing
U = W / 294.0                     # one display pixel in output px (7.96)
WHITE = (255, 255, 255)
GREY = (142, 142, 147)            # Apple secondary label on black
VIOLET = (172, 142, 255)          # dose accent = the plume's colour
RED = (255, 59, 74)
GREEN = (52, 230, 128)
FONT = "/System/Library/Fonts/SFNS.ttf"
FONT_FALLBACK = "/System/Library/Fonts/Helvetica.ttc"

DOSE = 0.64
REMAINING = "0:43"
BATTERY = 0.82
SEED = 11

# Map placement in display pixels.
MX, MY, MS, MR = 8, 8, 110, 14    # x, y, size, corner radius
SPOT = (0.47, 0.52, 0.25)         # plasma spot centre (fraction of map) and radius (fraction)
KILL = 0.62                       # porphyrin left inside the treated spot
KILL_G = 0.78                     # pyoverdine left inside the treated spot


_WEIGHTS = {"Regular": 400, "Medium": 510, "Semibold": 590, "Bold": 700}


def font(size_u, weight):
    """SF Pro at `size_u` display pixels; optical size follows the point size (Display cut for
    big figures, Text cut for small ones)."""
    px = int(round(size_u * U * S))
    try:
        f = ImageFont.truetype(FONT, px)
    except OSError:
        return ImageFont.truetype(FONT_FALLBACK, px)
    try:
        axes = []
        for ax in f.get_variation_axes():
            name = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
            if name == "Weight":
                axes.append(_WEIGHTS[weight])
            elif name == "Optical Size":
                axes.append(min(max(size_u * 1.4, ax["minimum"]), ax["maximum"]))
            elif name == "Width":
                axes.append(100)
            else:
                axes.append(ax["default"])
        f.set_variation_by_axes(axes)
    except (OSError, ValueError):
        pass
    return f


def u(v):
    return v * U * S


# ─────────────────────────────────────────────────────────────────────────────
# Fluorescence map
# ─────────────────────────────────────────────────────────────────────────────

def _field(rng, n, sigmas, weights):
    """Smooth random field: white noise filtered at several scales (FFT gaussian), ~N(0, 1)."""
    fx = np.fft.fftfreq(n)[:, None]
    fy = np.fft.fftfreq(n)[None, :]
    k2 = fx * fx + fy * fy
    out = np.zeros((n, n))
    for s, w in zip(sigmas, weights):
        noise = np.fft.fft2(rng.standard_normal((n, n)))
        f = np.real(np.fft.ifft2(noise * np.exp(-2 * (math.pi * s) ** 2 * k2)))
        out += w * f / f.std()
    return out / out.std()


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def fluorescence_map(n):
    rng = np.random.default_rng(SEED)
    yy, xx = np.mgrid[0:n, 0:n] / n
    # Wound bed: an irregular oval, bacteria concentrate in clusters toward its margin.
    warp = _field(rng, n, [n * 0.12], [1.0])
    r = np.hypot((xx - 0.5) / 0.44, (yy - 0.53) / 0.38) + 0.09 * warp
    bed = 1.0 - _smooth(0.86, 1.0, r)
    margin = np.exp(-((r - 0.72) / 0.26) ** 2)

    # Porphyrin (red): colonies, dense in clusters near the margin, sparse elsewhere.
    # Feature sizes stay at or above one display pixel (the map is MS px wide on the panel).
    p_cluster = _field(rng, n, [n * 0.07, n * 0.03], [1.0, 0.5])
    p_dens = _smooth(-0.2, 1.6, p_cluster + 1.0 * margin - 0.45)
    colonies = _field(rng, n, [n * 0.014, n * 0.008], [1.0, 0.6])
    speck = _smooth(0.1, 1.5, colonies + 1.6 * p_dens - 0.9)
    hot = _smooth(-1.2, 2.2, _field(rng, n, [n * 0.02, n * 0.01], [1.0, 0.5]) + p_dens)
    por = (p_dens ** 1.3) * speck * (0.25 + 0.75 * hot ** 1.8) * bed

    # Pyoverdine (green): fewer, diffuse sheets with soft fall-off, offset to one side.
    g_shape = _field(rng, n, [n * 0.09, n * 0.035], [1.0, 0.35])
    side = _smooth(0.2, 0.9, 1.0 - xx) * _smooth(0.05, 0.75, yy)
    pyo = (_smooth(0.0, 1.9, g_shape + 1.4 * side - 0.9) ** 1.5) * bed * 0.8

    # Tissue autofluorescence: barely above black.
    # Skin around the wound fills the frame faintly, the wound bed a touch brighter.
    tissue = (0.035 + 0.03 * bed) * (0.8 + 0.2 * np.tanh(_field(rng, n, [n * 0.02], [1.0])))

    # The plasma spot has been working for 64 % of the dose: signal knocked down inside it.
    sx, sy, sr = SPOT
    d = np.hypot(xx - sx, yy - sy) / sr
    inside = 1.0 - _smooth(0.85, 1.05, d)
    por *= 1.0 - (1.0 - KILL) * inside
    pyo *= 1.0 - (1.0 - KILL_G) * inside

    rgb = np.zeros((n, n, 3))
    red = np.array([255, 24, 40]) / 255.0
    red_hot = np.array([255, 110, 90]) / 255.0
    green = np.array([30, 232, 120]) / 255.0
    rgb += por[..., None] * red + (por ** 6)[..., None] * (red_hot - red) * 0.5
    rgb += pyo[..., None] * green
    rgb += tissue[..., None] * np.array([0.55, 0.75, 0.9])
    rgb = 1.0 - np.exp(-1.5 * rgb)                    # soft shoulder, never clips hard
    return Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8), "RGB")


# ─────────────────────────────────────────────────────────────────────────────
# Vector parts
# ─────────────────────────────────────────────────────────────────────────────

def annulus(d, cx, cy, r_in, r_out, a0, a1, fill, steps=720):
    pts = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((u(cx + r_out * math.cos(a)), u(cy + r_out * math.sin(a))))
    for i in range(steps, -1, -1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((u(cx + r_in * math.cos(a)), u(cy + r_in * math.sin(a))))
    d.polygon(pts, fill=fill)


def dose_arc(d, cx, cy, r, width, frac):
    annulus(d, cx, cy, r - 0.45, r + 0.45, 0, 360, (255, 255, 255, 150))
    a0, a1 = -90.0, -90.0 + 360.0 * frac
    h = width / 2
    annulus(d, cx, cy, r - h, r + h, a0, a1, VIOLET + (255,))
    for a in (a0, a1):
        x = cx + r * math.cos(math.radians(a))
        y = cy + r * math.sin(math.radians(a))
        d.ellipse([u(x - h), u(y - h), u(x + h), u(y + h)], fill=VIOLET + (255,))


def battery(d, x, y, w, h, frac):
    lw = int(u(0.9))
    d.rounded_rectangle([u(x), u(y), u(x + w), u(y + h)], radius=u(2.2), outline=GREY, width=lw)
    pad = 1.5
    d.rounded_rectangle([u(x + pad), u(y + pad), u(x + pad + (w - 2 * pad) * frac),
                         u(y + h - pad)], radius=u(1.0), fill=WHITE)
    d.rounded_rectangle([u(x + w + 0.8), u(y + h * 0.33), u(x + w + 2.0), u(y + h * 0.67)],
                        radius=u(0.5), fill=GREY)


def text(d, xy, s, f, fill, anchor):
    d.text((u(xy[0]), u(xy[1])), s, font=f, fill=fill, anchor=anchor)


def tw(d, s, f):
    return d.textlength(s, font=f) / (U * S)


def main():
    canvas = Image.new("RGB", (W * S, H * S), (0, 0, 0))

    # Map, rounded corners, true black outside.
    side = int(round(u(MS)))
    fmap = fluorescence_map(512).resize((side, side), Image.BICUBIC)
    fmap = fmap.filter(ImageFilter.GaussianBlur(radius=u(0.35)))
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, side - 1, side - 1], radius=u(MR), fill=255)
    canvas.paste(fmap, (int(round(u(MX))), int(round(u(MY)))), mask)

    over = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    sx, sy, sr = SPOT
    dose_arc(d, MX + MS * sx, MY + MS * sy, MS * sr, 3.2, DOSE)

    # Right column.
    xl, xr = 134, 286
    battery(d, xr - 20.5, 9, 18.5, 9, BATTERY)

    f_dose = font(46, "Semibold")
    f_unit = font(22, "Semibold")
    pct = f"{round(DOSE * 100)}"
    text(d, (xl - 1.5, 60), pct, f_dose, WHITE, "ls")
    text(d, (xl - 1.5 + tw(d, pct, f_dose) + 1.2, 60), "%", f_unit, VIOLET, "ls")

    f_time = font(24, "Medium")
    text(d, (xl - 0.8, 90), REMAINING, f_time, GREY, "ls")

    # Change in each fluorescence signal since the start.
    f_val = font(16, "Semibold")
    yb = 116
    vals = [(RED, f"−{round((1 - KILL) * 100)}%"), (GREEN, f"−{round((1 - KILL_G) * 100)}%")]
    x = xl
    for col, s in vals:
        r = 3.1
        d.ellipse([u(x), u(yb - 5.6 - r), u(x + 2 * r), u(yb - 5.6 + r)], fill=col + (255,))
        text(d, (x + 2 * r + 3.2, yb), s, f_val, WHITE, "ls")
        x += 2 * r + 3.2 + tw(d, s, f_val) + 12

    canvas = Image.alpha_composite(canvas.convert("RGBA"), over).convert("RGB")
    out = canvas.resize((W, H), Image.LANCZOS)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oled_ui.png")
    out.save(path, optimize=True)
    print(path, out.size)


if __name__ == "__main__":
    main()
