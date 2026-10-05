#!/usr/bin/env python3
"""Procedurally generates the Acid Rain wallpapers (no external assets).

    python3 tools/gen_backgrounds.py [outdir] [width height]

Needs: python3, numpy, pillow. Deterministic (fixed seeds) so the PNGs in
backgrounds/ can be reproduced exactly. Everything is drawn from the theme's
palette: magenta / cyan / radioactive green on ink-black violet.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "backgrounds"
W, H = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (3840, 2160)
S = W / 3840.0  # scale for sizes tuned at 4K

MAG = np.array([255, 0, 200], np.float32) / 255
CYA = np.array([0, 240, 255], np.float32) / 255
GRN = np.array([57, 255, 20], np.float32) / 255
AMB = np.array([255, 122, 61], np.float32) / 255
INK = np.array([7, 3, 15], np.float32) / 255
VIO = np.array([58, 10, 82], np.float32) / 255
NEON = [MAG, CYA, GRN]


def px(v):
    return max(1, int(round(v * S)))


def blur(a, r):
    """Gaussian blur a float HxWx3 array in 0..inf by blurring a 16-bit-safe copy."""
    if r <= 0:
        return a
    a = np.minimum(a, 4.0)
    peak = max(float(a.max()), 1.0)
    im = Image.fromarray(np.clip(a / peak * 255, 0, 255).astype(np.uint8))
    im = im.filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) / 255 * peak


def bloom(a, thresh=0.55, strength=1.0):
    lum = a.max(axis=2, keepdims=True)
    hot = a * np.clip((lum - thresh) / (1 - thresh + 1e-6), 0, 1)
    out = np.zeros_like(a)
    for r, w in ((px(6), 0.9), (px(22), 0.8), (px(70), 0.9), (px(180), 0.8)):
        out += blur(hot, r) * w
    return a + out * strength


def noise(h, w, cells, rng, octaves=5):
    """Cheap fractal value noise in 0..1, shape (h, w)."""
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        cy, cx = max(2, int(cells * 2 ** o * h / w)), max(2, cells * 2 ** o)
        g = rng.random((cy, cx)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += np.asarray(im, np.float32) / 255 * amp
        tot += amp
        amp *= 0.5
    return out / tot


def aberrate(a, shift):
    """Chromatic aberration: push red and blue apart horizontally."""
    out = a.copy()
    out[:, :, 0] = np.roll(a[:, :, 0], shift, axis=1)
    out[:, :, 2] = np.roll(a[:, :, 2], -shift, axis=1)
    return out


def finish(a, rng, name, grain=0.025, vignette=0.55, aberr=3):
    a = aberrate(a, px(aberr))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    a = a * (1 - vignette * np.clip(d - 0.35, 0, 1) ** 1.6)[:, :, None]
    # hue-preserving tonemap: compress by the brightest channel only, so heavy
    # additive overlap stays neon instead of washing out to white
    m = a.max(axis=2, keepdims=True) + 1e-6
    a = a * (1 - np.exp(-m * 1.35)) / m
    a = a + rng.normal(0, grain, a.shape[:2]).astype(np.float32)[:, :, None]
    a = np.clip(a, 0, 1) ** 0.95
    Image.fromarray((a * 255).astype(np.uint8)).save(OUT / name, quality=93, subsampling=0)
    print("wrote", OUT / name)


# --------------------------------------------------------------------------
# 1. RAIN DISTRICT — neon megacity skyline in acid rain, wet street mirror
# --------------------------------------------------------------------------
def rain_district():
    rng = np.random.default_rng(2077)
    ground = int(H * 0.80)

    # sky: ink -> violet -> magenta haze, radioactive green fog hugging the roofs
    t = np.linspace(0, 1, ground, dtype=np.float32)[:, None, None]
    sky = INK * (1 - t) + VIO * np.clip(t * 1.6, 0, 1)
    sky = sky + MAG * 0.55 * np.clip(t - 0.45, 0, 1) ** 1.3 * 2.2
    sky = sky + CYA * 0.18 * np.exp(-((t - 0.62) ** 2) / 0.01)
    sky = sky + GRN * 0.35 * np.exp(-((t - 0.97) ** 2) / 0.006)
    clouds = noise(ground, W, 4, rng)[:, :, None]
    sky = sky * (0.55 + 0.9 * clouds)
    scene = Image.fromarray(np.clip(np.pad(sky, ((0, H - ground), (0, 0), (0, 0))) * 255, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(scene)

    # giant holographic ring hanging in the smog
    cx, cy, R = int(W * 0.68), int(H * 0.30), px(430)
    for k, (col, wd) in enumerate(((MAG, 26), (CYA, 10), (GRN, 4))):
        rr = R + px(k * 34)
        c = tuple(int(v * 255) for v in col)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=c, width=px(wd))
    for a in np.linspace(0, 2 * np.pi, 72, endpoint=False):  # tick marks
        x0, y0 = cx + np.cos(a) * (R - px(40)), cy + np.sin(a) * (R - px(40))
        x1, y1 = cx + np.cos(a) * (R - px(90)), cy + np.sin(a) * (R - px(90))
        d.line([x0, y0, x1, y1], fill=(0, 240, 255), width=px(5))

    # three depth layers of towers
    layers = [  # (count, min_w, max_w, min_h, max_h, haze, windows)
        (46, 80, 190, 0.28, 0.62, 0.78, 0.50),
        (30, 120, 270, 0.22, 0.74, 0.52, 0.80),
        (18, 200, 420, 0.15, 0.88, 0.16, 1.00),
    ]
    haze_col = (MAG * 0.55 + VIO * 0.6)
    for li, (n, wmin, wmax, hmin, hmax, haze, wi) in enumerate(layers):
        x = -rng.integers(0, px(100))
        while x < W:
            bw = px(rng.integers(wmin, wmax))
            bh = int(H * rng.uniform(hmin, hmax) * 0.82)
            top = ground - bh
            base = (INK * (1 - haze) + haze_col * 0.5 * haze) * 0.9
            fill = tuple(int(v * 255) for v in np.clip(base, 0, 1))
            d.rectangle([x, top, x + bw, ground], fill=fill)
            if rng.random() < 0.5:  # stepped crown / antenna
                sw = int(bw * rng.uniform(0.3, 0.6))
                sh = int(bh * rng.uniform(0.05, 0.14))
                d.rectangle([x + (bw - sw) // 2, top - sh, x + (bw + sw) // 2, top], fill=fill)
                if rng.random() < 0.6:
                    ax = x + bw // 2
                    d.line([ax, top - sh, ax, top - sh - px(rng.integers(60, 200))], fill=fill, width=px(4))
                    d.ellipse([ax - px(6), top - sh - px(220), ax + px(6), top - sh - px(208)], fill=(255, 30, 90)) if li == 2 else None
            # lit windows on a grid
            ww, wh, gx, gy = px(9 + 3 * li), px(13 + 4 * li), px(22 + 6 * li), px(30 + 8 * li)
            col_main = NEON[rng.integers(0, 3)]
            for wy in range(top + gy, ground - gy, gy):
                for wx in range(x + gx // 2, x + bw - ww, gx):
                    if rng.random() < 0.34 * wi:
                        c = col_main if rng.random() < 0.7 else (AMB if rng.random() < 0.25 else NEON[rng.integers(0, 3)])
                        inten = rng.uniform(0.35, 1.0) * (1 - haze * 0.6)
                        d.rectangle([wx, wy, wx + ww, wy + wh], fill=tuple(int(v * 255 * inten) for v in c))
            # neon signage on the nearest layer
            if li == 2 and rng.random() < 0.85:
                c = NEON[rng.integers(0, 3)]
                sx = x + int(bw * rng.uniform(0.12, 0.65))
                sw2 = px(rng.integers(34, 70))
                sh2 = int(bh * rng.uniform(0.25, 0.55))
                sy = top + int(bh * rng.uniform(0.05, 0.3))
                col255 = tuple(int(v * 255) for v in c)
                d.rectangle([sx, sy, sx + sw2, sy + sh2], outline=col255, width=px(8))
                for gy2 in range(sy + px(24), sy + sh2 - px(24), px(34)):  # glyph blocks
                    gxo = sx + px(10)
                    while gxo < sx + sw2 - px(14):
                        gw = px(rng.integers(8, 20))
                        if rng.random() < 0.75:
                            d.rectangle([gxo, gy2, min(gxo + gw, sx + sw2 - px(10)), gy2 + px(16)], fill=col255)
                        gxo += gw + px(8)
            if li >= 1 and rng.random() < 0.4:  # horizontal light strip
                c = tuple(int(v * 255) for v in NEON[rng.integers(0, 3)])
                yy = top + int(bh * rng.uniform(0.1, 0.9))
                d.rectangle([x, yy, x + bw, yy + px(7)], fill=c)
            x += bw + px(rng.integers(0, 28))

    # volumetric searchlight beams from the horizon
    scn = np.asarray(scene, np.float32) / 255
    beams = np.zeros_like(scn)
    bi = Image.new("RGB", (W, H))
    bd = ImageDraw.Draw(bi)
    for bx, ang, col in ((0.22, -0.22, CYA), (0.40, 0.12, MAG), (0.86, 0.30, GRN)):
        x0, y0 = int(W * bx), ground - px(120)
        L = H
        for spread, a_ in ((0.05, 0.22), (0.02, 0.35)):
            pts = [(x0, y0), (x0 + np.sin(ang - spread) * L, y0 - np.cos(ang - spread) * L),
                   (x0 + np.sin(ang + spread) * L, y0 - np.cos(ang + spread) * L)]
            bd.polygon(pts, fill=tuple(int(v * 255 * a_) for v in col))
    beams = blur(np.asarray(bi, np.float32) / 255, px(14))
    scn = scn + beams * 0.7

    # wet street: mirrored scene, rippled and streaked
    rh = H - ground
    refl = scn[ground - rh:ground][::-1].copy()
    rows = np.arange(rh)[:, None].repeat(W, 1)
    shift = (np.sin(rows * 0.09 + rng.random() * 6) * (4 + rows * 0.05) * S).astype(int)
    idx = (np.arange(W)[None, :] + shift) % W
    refl = np.take_along_axis(refl, idx[:, :, None].repeat(3, 2), axis=1)
    refl = blur(refl, px(5))
    # vertical smear so light pools stretch like real puddles
    sm = np.zeros_like(refl)
    for k in range(0, px(46), max(1, px(6))):
        sm += np.roll(refl, k, axis=0) / (px(46) / max(1, px(6)))
    refl = (refl * 0.35 + sm * 0.9) * np.linspace(0.85, 0.12, rh, dtype=np.float32)[:, None, None]
    road = INK * 0.6 + MAG * 0.05 * noise(rh, W, 6, rng)[:, :, None]
    scn[ground:] = road + refl
    # puddle glints
    pg = Image.new("RGB", (W, H))
    pd_ = ImageDraw.Draw(pg)
    for _ in range(260):
        gx0, gy0 = rng.integers(0, W), rng.integers(ground + 8, H)
        ln = px(rng.integers(40, 340))
        c = tuple(int(v * 255 * rng.uniform(0.3, 0.9)) for v in NEON[rng.integers(0, 3)])
        pd_.line([gx0, gy0, gx0 + ln, gy0], fill=c, width=px(rng.integers(2, 5)))
    scn += blur(np.asarray(pg, np.float32) / 255, px(2)) * 0.8

    scn = bloom(scn, thresh=0.5, strength=1.15)

    # acid rain: thin slanted streaks, additive, brighter near the camera
    rain = Image.new("RGB", (W, H))
    rd = ImageDraw.Draw(rain)
    for _ in range(int(6500 * S * S + 2200)):
        x0, y0 = rng.integers(-200, W), rng.integers(-200, H)
        ln = px(rng.integers(40, 190))
        depth = rng.random()
        col = (CYA * 0.7 + 0.3) if rng.random() < 0.8 else MAG
        c = tuple(int(v * 255 * (0.15 + 0.5 * depth)) for v in col)
        rd.line([x0, y0, x0 - ln * 0.18, y0 + ln], fill=c, width=1 if depth < 0.7 else px(2))
    scn += np.asarray(rain, np.float32) / 255 * 0.7
    finish(scn, rng, "1-rain-district.jpg", aberr=4)


# --------------------------------------------------------------------------
# 2. DATASTORM — curl-noise streamlines, additive neon on black
# --------------------------------------------------------------------------
def datastorm():
    rng = np.random.default_rng(1982)
    acc = np.zeros((H, W, 3), np.float32)

    # smooth pseudo-random angle field: layered sines (cheap, tileable, no deps)
    waves = [(rng.uniform(0.6, 3.2), rng.uniform(0.6, 3.2), rng.uniform(0, 6.28), rng.uniform(0.6, 1.2)) for _ in range(9)]

    def field(x, y):
        a = np.zeros_like(x)
        for fx, fy, ph, am in waves:
            a += am * np.sin(fx * x * 5.0 + ph + np.sin(fy * y * 4.0 + ph * 1.7))
            a += am * 0.6 * np.cos(fy * y * 5.0 - ph + np.cos(fx * x * 3.0))
        return a * 1.15

    n, steps = 9000, 520
    x = rng.random(n).astype(np.float32)
    y = rng.random(n).astype(np.float32)
    # cluster seeds into a few bright bundles so it reads as flowing ribbons
    bundle = rng.integers(0, 22, n)
    bx, by = rng.random(22), rng.random(22)
    x = np.clip(bx[bundle] + rng.normal(0, 0.11, n), 0, 1).astype(np.float32)
    y = np.clip(by[bundle] + rng.normal(0, 0.11, n), 0, 1).astype(np.float32)
    hue = ((bundle / 22.0) * 1.0 + rng.normal(0, 0.035, n)).astype(np.float32) % 1.0
    speed = rng.uniform(0.0011, 0.0021, n).astype(np.float32)
    alive = np.ones(n, bool)
    ar = W / H
    for s in range(steps):
        ang = field(x * ar, y)
        x += np.cos(ang) * speed / ar + rng.normal(0, 0.0007, n).astype(np.float32) / ar
        y += np.sin(ang) * speed + rng.normal(0, 0.0007, n).astype(np.float32)
        ok = (x >= 0) & (x < 1) & (y >= 0) & (y < 1) & alive
        alive = ok
        ix = (np.clip(x, 0, 0.9999) * W).astype(int)
        iy = (np.clip(y, 0, 0.9999) * H).astype(int)
        # color drifts along the path: magenta -> cyan -> green -> magenta
        h = (hue + s / steps * 0.75) % 1.0
        k = h * 3
        w0 = np.clip(1 - np.abs(k - 0), 0, 1) + np.clip(1 - np.abs(k - 3), 0, 1)
        w1 = np.clip(1 - np.abs(k - 1), 0, 1)
        w2 = np.clip(1 - np.abs(k - 2), 0, 1)
        col = w0[:, None] * MAG + w1[:, None] * CYA + w2[:, None] * GRN
        fade = np.sin(np.pi * s / steps) ** 0.7
        np.add.at(acc, (iy[ok], ix[ok]), col[ok] * (0.045 * fade))
    acc = blur(acc, 1.2 * S + 0.5) * 1.1
    # deep violet nebula underlay
    neb = noise(H, W, 3, rng)[:, :, None]
    base = INK * 1.2 + VIO * 0.55 * neb ** 2.2 + MAG * 0.06 * neb ** 4
    img = base + bloom(acc, thresh=0.35, strength=0.7)
    # sparse data-points
    pts = np.zeros_like(img)
    for _ in range(2200):
        i, j = rng.integers(0, H), rng.integers(0, W)
        pts[i, j] = NEON[rng.integers(0, 3)] * rng.uniform(0.6, 1.8)
    img += bloom(blur(pts, 1.0), 0.2, 1.2)
    finish(img, rng, "2-datastorm.jpg", vignette=0.7, aberr=3)


# --------------------------------------------------------------------------
# 3. REACTOR CORE — nested neon hexagons, radioactive core, glitch tears
# --------------------------------------------------------------------------
def reactor_core():
    rng = np.random.default_rng(404)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W * 0.5, H * 0.52
    u = (xx - cx) / (H * 0.5)
    v = (yy - cy) / (H * 0.5)
    r = np.sqrt(u * u + v * v) + 1e-6
    th = np.arctan2(v, u)

    # slow spiral twist: rotation grows with radius, so the rings "corkscrew"
    tw = th + 0.05 * np.log(r + 0.2) * 3.0
    px_, py_ = r * np.cos(tw), r * np.sin(tw)
    # hexagon distance field (flat-top)
    ax, ay = np.abs(px_), np.abs(py_)
    hexd = np.maximum(ax * 0.8660254 + ay * 0.5, ay)

    img = np.zeros((H, W, 3), np.float32)
    ring_n = 22.0
    f = hexd * ring_n
    idx = np.floor(f).astype(int)
    frac = f - idx
    line = np.exp(-((frac - 0.5) ** 2) / 0.0009)  # thin core line
    halo = np.exp(-((frac - 0.5) ** 2) / 0.03) * 0.25
    cols = np.stack([MAG, CYA, GRN])
    # color rings in a repeating magenta/cyan/green rhythm with occasional skips
    pick = (idx + (idx // 7)) % 3
    ringcol = cols[pick]
    on = ((idx * 2654435761) % 11 > 2).astype(np.float32)  # some rings dark
    fall = np.clip(1.2 - hexd * 0.9, 0.0, 1.0) ** 1.4
    img += ringcol * ((line * 1.7 + halo) * on * fall)[:, :, None]

    # radial spokes (12), thin, cyan-white
    spokes = np.exp(-((((th * 12 / (2 * np.pi)) % 1.0) - 0.5) ** 2) / 0.0004) * np.clip(r - 0.12, 0, 1) * np.exp(-r * 0.9)
    img += (CYA * 0.5 + 0.25)[None, None, :] * spokes[:, :, None] * 0.8

    # radioactive core: hot green with white-hot center and magenta corona
    img += GRN * (np.exp(-r * r / 0.02) * 1.7)[:, :, None]
    img += (np.exp(-r * r / 0.0007) * 0.45)[:, :, None]
    img += MAG * (np.exp(-r * r / 0.22) * 0.55)[:, :, None]
    img += CYA * (np.exp(-((r - 0.62) ** 2) / 0.0006) * 0.9)[:, :, None]  # containment ring

    # ground the whole thing with a deep violet haze
    haze = noise(H, W, 3, rng)[:, :, None]
    img += (INK + VIO * 0.5 * haze ** 2) * 0.9
    img = bloom(img, thresh=0.45, strength=1.2)

    # glitch tears: shove horizontal slabs sideways and tint them
    for _ in range(11):
        y0 = rng.integers(0, H - 10)
        h_ = rng.integers(px(3), px(22))
        sh = int(rng.normal(0, 40 * S))
        slab = np.roll(img[y0:y0 + h_], sh, axis=1)
        tint = NEON[rng.integers(0, 3)] * 0.5 + 0.5
        img[y0:y0 + h_] = slab * (tint if rng.random() < 0.4 else 1.0)
    # scanlines
    img *= (0.93 + 0.07 * np.sin(yy * (np.pi / max(2, px(2)))))[:, :, None]
    finish(img, rng, "3-reactor-core.jpg", vignette=0.6, aberr=5)


def ramp(f, stops):
    """Map f in 0..1 through [(pos, rgb)] stops -> HxWx3."""
    pos = [q for q, _ in stops]
    return np.stack([np.interp(f, pos, [c[i] for _, c in stops]) for i in range(3)], -1).astype(np.float32)


def lowres_grid(w=1280):
    h = int(w * H / W)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx / w * (W / H), yy / h, h, w  # u spans aspect, v 0..1


def up(a, soft=0):
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    a = np.asarray(im, np.float32) / 255
    return blur(a, soft) if soft else a


# --------------------------------------------------------------------------
# 0. LIQUID NEON — the calm default: soft, blurry, wavy ribbons of light
# --------------------------------------------------------------------------
def liquid_neon():
    rng = np.random.default_rng(7)
    u, v, h, w = lowres_grid(1600)
    img = np.zeros((h, w, 3), np.float32)
    ribbons = [  # (colour, base v, amplitude, freq, phase, width, gain)
        (MAG, 0.36, 0.17, 1.15, 0.2, 0.17, 1.00),
        (CYA, 0.55, 0.15, 1.45, 2.1, 0.13, 0.95),
        (GRN, 0.74, 0.12, 0.95, 4.0, 0.10, 0.80),
        (MAG, 0.88, 0.09, 1.80, 5.3, 0.14, 0.45),
        (CYA, 0.16, 0.08, 1.30, 3.3, 0.12, 0.40),
    ]
    for col, base, amp, fr, ph, wd, gain in ribbons:
        # domain-warped centreline: two stacked sines make it genuinely wavy
        cl = base + amp * np.sin(u * fr * 2.4 + ph + 0.9 * np.sin(u * fr * 1.1 + v * 2.0)) \
            + amp * 0.45 * np.sin(u * fr * 4.1 - ph * 1.3)
        d = (v - cl) / wd
        thick = 0.75 + 0.45 * np.sin(u * 1.7 + ph * 2.0)  # ribbon swells and thins
        glow = np.exp(-(d / thick) ** 2) * gain
        core = np.exp(-(d / thick) ** 2 * 9) * 0.45
        img += col * (glow + core)[:, :, None]
    img += (INK * 1.4 + VIO * 0.35 * noise(h, w, 2, rng)[:, :, None] ** 1.6)
    img = up(img * 0.72)
    img = blur(img, px(14))  # deliberately out-of-focus
    img = bloom(img, thresh=0.5, strength=0.55)
    finish(img, rng, "0-liquid-neon.jpg", grain=0.018, vignette=0.5, aberr=2)


# --------------------------------------------------------------------------
# 4. AURORA SMOG — vertical neon curtains over a dark skyline
# --------------------------------------------------------------------------
def aurora_smog():
    rng = np.random.default_rng(88)
    u, v, h, w = lowres_grid(1600)
    img = np.zeros((h, w, 3), np.float32)
    for k, (col, ph) in enumerate(((GRN, 0.0), (CYA, 1.7), (MAG, 3.4), (GRN, 5.0))):
        hc = 0.38 + 0.12 * np.sin(u * (0.9 + k * 0.25) + ph) + 0.05 * np.sin(u * 3.1 + ph * 2)
        d = (v - hc) / (0.16 + 0.05 * k)
        rays = 0.55 + 0.45 * np.sin(u * 55 + 4 * np.sin(u * 3 + ph) + k)  # curtain folds
        fall = np.where(v < hc, np.exp(-d ** 2 * 0.5), np.exp(-d ** 2 * 2.2))
        img += col * (fall * rays ** 1.5 * (0.5 - k * 0.04))[:, :, None]
    img += INK * 1.3 + VIO * 0.4 * noise(h, w, 3, rng)[:, :, None] ** 2
    img = up(img, px(5))
    # stars
    st = np.zeros_like(img)
    for _ in range(1400):
        st[rng.integers(0, int(H * 0.7)), rng.integers(0, W)] = rng.uniform(0.4, 1.4)
    img += blur(st, 1.0)[:, :, :1] * np.array([0.8, 0.9, 1.0], np.float32)
    # layered dark ridgeline with a little neon rim light
    for li, (amp, col, a) in enumerate(((0.07, MAG, 0.5), (0.11, CYA, 0.7), (0.16, INK, 1.0))):
        x = np.arange(W) / W
        ridge = (0.86 - li * 0.07) + amp * (0.5 * np.sin(x * (5 + li * 3) + li) + 0.3 * np.sin(x * (13 + li * 5) + li * 2) + 0.2 * np.sin(x * 29))
        ridge_px = (ridge * H).astype(int)
        yy = np.arange(H)[:, None]
        mask = (yy >= ridge_px[None, :]).astype(np.float32)[:, :, None]
        rim = np.exp(-((yy - ridge_px[None, :]) / px(4)) ** 2)[:, :, None] * col * 0.9 * (li < 2)
        body = (INK * (0.9 - li * 0.2) + col * 0.05)
        img = img * (1 - mask) + mask * body + rim
    img = bloom(img, thresh=0.45, strength=0.9)
    finish(img, rng, "4-aurora-smog.jpg", grain=0.02, aberr=2)


# --------------------------------------------------------------------------
# 5. BOKEH WINDOW — rain-fogged window onto out-of-focus neon city lights
# --------------------------------------------------------------------------
def bokeh_window():
    rng = np.random.default_rng(55)
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    base = INK * 1.2 + VIO * 0.7 * t ** 1.5 + MAG * 0.12 * np.exp(-((t - 0.8) ** 2) / 0.02)
    img = np.broadcast_to(base, (H, W, 3)).copy()
    for layer, (n, rmin, rmax, soft, gain) in enumerate(((70, 120, 260, 10, 0.55), (150, 50, 130, 4, 0.7), (260, 18, 60, 1.5, 0.8))):
        im = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(im)
        for _ in range(n):
            r = px(rng.integers(rmin, rmax))
            x, y = rng.integers(0, W), int(H * rng.beta(2.2, 1.6))
            c = NEON[rng.integers(0, 3)] * rng.uniform(0.35, 1.0) * (0.4 if rng.random() < 0.3 else 1)
            fill = tuple(int(q * 255 * 0.55) for q in c)
            rim = tuple(int(q * 255) for q in c)
            d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=rim, width=max(1, r // 14))
        img += blur(np.asarray(im, np.float32) / 255, px(soft)) * gain
    # condensation: slow vertical droplet trails
    dr = Image.new("RGB", (W, H))
    dd = ImageDraw.Draw(dr)
    for _ in range(int(380 * S + 60)):
        x, y0 = rng.integers(0, W), rng.integers(0, H)
        ln = px(rng.integers(120, 520))
        c = tuple(int(q * 255 * 0.22) for q in (CYA * 0.6 + 0.4))
        dd.line([x, y0, x + rng.integers(-6, 6), y0 + ln], fill=c, width=px(rng.integers(2, 6)))
        dd.ellipse([x - px(7), y0 + ln - px(7), x + px(7), y0 + ln + px(9)], fill=tuple(int(q * 255 * 0.45) for q in (CYA * 0.6 + 0.4)))
    img += blur(np.asarray(dr, np.float32) / 255, px(2))
    img = bloom(img, thresh=0.5, strength=0.5)
    finish(img, rng, "5-bokeh-window.jpg", grain=0.022, aberr=3)


# --------------------------------------------------------------------------
# 6. WIREFRAME TERRAIN — neon vector mountains under a radioactive sun
# --------------------------------------------------------------------------
def wireframe_terrain():
    rng = np.random.default_rng(1984)
    horizon = int(H * 0.46)
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    img = INK * 1.1 + VIO * 0.8 * np.clip(t * 1.7, 0, 1) ** 2 + MAG * 0.5 * np.exp(-((t - 0.44) ** 2) / 0.006)
    img = np.broadcast_to(img, (H, W, 3)).copy()
    # sun: radioactive green disc with scan slits
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sx, sy, sr = W * 0.5, horizon - px(30), px(430)
    dist = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
    sun = np.clip((sr - dist) / px(3), 0, 1)
    slits = ((yy - sy) / px(26)) % 1.0
    cut = np.where((yy > sy - px(80)), (slits > 0.25 + 0.6 * np.clip((yy - sy) / sr, 0, 1)), 1.0)
    grad = ramp(np.clip((yy - (sy - sr)) / (2 * sr), 0, 1), [(0, GRN), (0.55, CYA), (1, MAG)])
    img += grad * (sun * cut)[:, :, None] * 1.3
    img = np.where((yy > horizon)[:, :, None], INK * 1.0, img)

    scene = Image.fromarray(np.clip(img * 255, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(scene)
    rows = 46
    xs = np.linspace(-1.6, 1.6, 420)
    for i in range(rows):
        z = (1 - i / rows)  # 1 = far, 0 = near
        zz = z ** 1.9
        ypos = horizon + (H - horizon) * (1 - zz) ** 1.0 * 1.0
        scale = 0.18 + (1 - zz) * 1.75
        # mountains: strong at the sides, calm valley in the middle
        amp = (np.abs(xs) ** 1.6) * 0.55 + 0.03
        hgt = amp * (0.6 * np.sin(xs * 5.0 + i * 0.27) + 0.4 * np.sin(xs * 11.0 - i * 0.43) + 0.9)
        pts = [(W / 2 + x * scale * W * 0.5, ypos - hh * scale * H * 0.38) for x, hh in zip(xs, hgt)]
        poly = pts + [(pts[-1][0], H + 5), (pts[0][0], H + 5)]
        d.polygon(poly, fill=(5, 2, 12))
        k = (1 - z)
        col = MAG * (1 - k) + CYA * k
        if i % 9 == 4:
            col = GRN
        d.line(pts, fill=tuple(int(c * 255) for c in np.clip(col, 0, 1)), width=px(2 + 3 * k))
    img = np.asarray(scene, np.float32) / 255
    # near-camera cross lines on the plain for a grid read
    img = bloom(img * 1.25, thresh=0.4, strength=1.1)
    finish(img, rng, "6-wireframe-terrain.jpg", aberr=3)


# --------------------------------------------------------------------------
# 7. PLASMA INK — marbled neon ink swirling in black water
# --------------------------------------------------------------------------
def plasma_ink():
    rng = np.random.default_rng(23)
    u, v, h, w = lowres_grid(1600)
    px_, py_ = u * 1.5, v * 1.5
    for k in range(5):  # iterated domain warp = marbling
        px_, py_ = px_ + 0.55 * np.sin(py_ * 2.3 + k * 1.7 + 0.5), py_ + 0.55 * np.sin(px_ * 2.1 - k * 1.3 + 1.2)
    f = 0.5 + 0.5 * np.sin(px_ * 2.6 + py_ * 1.9)
    g = 0.5 + 0.5 * np.sin(py_ * 3.1 - px_ * 1.4 + 2.0)
    stops = [(0.0, INK), (0.30, INK * 1.5 + VIO * 0.6), (0.52, MAG * 0.95), (0.66, CYA), (0.80, GRN), (1.0, INK)]
    col = ramp(f, stops)
    edge = np.exp(-((g - 0.5) ** 2) / 0.012)[:, :, None]  # bright vein lines
    img = col * (0.35 + 0.65 * g[:, :, None] ** 1.5) + edge * MAG * 0.55
    img = up(np.clip(img, 0, 3) / 3) * 3
    img = blur(img, px(2))
    img = bloom(img, thresh=0.5, strength=0.6)
    finish(img, rng, "7-plasma-ink.jpg", grain=0.02, aberr=3)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {"liquid": liquid_neon, "rain": rain_district, "storm": datastorm, "core": reactor_core,
            "aurora": aurora_smog, "bokeh": bokeh_window, "terrain": wireframe_terrain, "ink": plasma_ink}
    for name in (sys.argv[4:] or list(jobs)):
        jobs[name]()
