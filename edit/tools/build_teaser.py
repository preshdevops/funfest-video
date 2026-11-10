#!/usr/bin/env python3
"""Vertical teaser (1080x1920, 13.6s). Pure typography, nothing revealed: no name, logo, dates, region or people.

  python3 build_teaser.py --out teaser.mp4 [--audio music.wav]
  python3 build_teaser.py --preview 0.5,2,3.4,4,5,7,9,10.2,11,13 <outdir>
Assets (font, logo, slice frames) live in $TEASER_ASSETS (default edit/teaser_assets); see teaser_logo.py / teaser_prep.py.
"""
import os, sys, math, random, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import teaser_timing as TT
EDIT = os.path.abspath(os.path.join(HERE, ".."))
A = os.environ.get("TEASER_ASSETS", os.path.join(EDIT, "teaser_assets"))
W, H, FPS = 1080, 1920, TT.FPS
ANTON = os.path.join(A, "Anton_400Regular.ttf")
POPPINS = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
GOLD = (240, 199, 102); INK = (66, 20, 88)
KENTE = [(230, 180, 34), (24, 18, 30), (212, 135, 155), (230, 180, 34), (122, 42, 150)]

def eo_back(t, k=1.7): t = min(max(t, 0), 1); u = t - 1; return 1 + (k + 1) * u ** 3 + k * u ** 2
def eo_cubic(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def ei_cubic(t): t = min(max(t, 0), 1); return t ** 3
def lerp(a, b, t): return a + (b - a) * t

def fit_font(text, target, path=ANTON):
    lo, hi = 10, 700
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if ImageFont.truetype(path, mid).getlength(text) > target: hi = mid
        else: lo = mid
    return ImageFont.truetype(path, lo)

def paste(canvas, im, x, y):
    x, y = int(x), int(y)
    cx0, cy0 = max(0, -x), max(0, -y); cx1 = min(im.width, canvas.width - x); cy1 = min(im.height, canvas.height - y)
    if cx1 <= cx0 or cy1 <= cy0: return
    canvas.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))

def with_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * max(a, 0)))); return im

def scaled(im, s):
    return im if abs(s - 1) < 1e-3 else im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BICUBIC)

def star(d, x, y, r, col):
    pts = []
    for j in range(8):
        rr = r if j % 2 == 0 else r * 0.28; a2 = math.pi / 2 + j * math.pi / 4
        pts.append((x + math.cos(a2) * rr, y + math.sin(a2) * rr))
    d.polygon(pts, fill=col)

# ---------------------------------------------------------------- beat 1: posters
def make_poster(gold, angle):
    S, pw, ph = 2, 300, 404
    im = Image.new("RGBA", (pw * S, ph * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, pw * S - 1, ph * S - 1), radius=8 * S, fill=(222, 170, 70, 255) if gold else (247, 244, 250, 255))
    f = fit_font("COMING SOON", 262 * S); bb = f.getbbox("COMING SOON"); th = bb[3] - bb[1]; lh = int(th * 1.25)
    y0 = (ph * S - 14 * S - 5 * lh) // 2
    for i in range(5):
        tw = f.getlength("COMING SOON"); d.text(((pw * S - tw) / 2, y0 + i * lh - bb[1] + (lh - th) // 2), "COMING SOON", font=f, fill=INK + (255,))
    seg, sh = 22 * S, 14 * S
    for i, x in enumerate(range(0, pw * S, seg)): d.rectangle((x, ph * S - sh, min(x + seg, pw * S), ph * S), fill=KENTE[i % 5] + (255,))
    im = im.rotate(angle, resample=Image.BICUBIC, expand=True).resize((im.width // S, im.height // S), Image.LANCZOS) if False else im.rotate(angle, resample=Image.BICUBIC, expand=True)
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    pad = 26
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh_a = Image.new("RGBA", out.size, (0, 0, 0, 0)); sh_a.paste((0, 0, 0, 110), (pad, pad + 8), im.getchannel("A"))
    from PIL import ImageFilter
    out.alpha_composite(sh_a.filter(ImageFilter.GaussianBlur(9))); out.alpha_composite(im, (pad, pad)); return out

_rng = random.Random(5)
_cells = [(180 + 360 * c, 190 + 385 * r) for r in range(5) for c in range(3)]; _rng.shuffle(_cells)
POS = [(x + _rng.randint(-22, 22), y + _rng.randint(-22, 22)) for x, y in _cells[:15]] + [(500, 900), (600, 1060)]
SPR = [make_poster(i % 4 == 2, _rng.uniform(-9, 9)) for i in range(len(TT.POSTER_T))]

def posters(t):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for sp, (cx, cy), pt in zip(SPR, POS, TT.POSTER_T):
        if t < pt: continue
        u = (t - pt) / 0.2; s = 0.55 + 0.45 * eo_back(u) if u < 1 else 1.0
        im = with_alpha(scaled(sp, s), min(1, u * 5))
        paste(lay, im, cx - im.width / 2, cy - im.height / 2)
    return lay

# ---------------------------------------------------------------- beat 2: ARE YOU READY?
_f2 = fit_font("ARE YOU", 880 * 2)      # drawn at 2x and downsampled with LANCZOS: no shimmer while it scales
def _ready_layer(col2):
    lh = int(_f2.size * 0.98); im = Image.new("RGBA", (2000, lh * 2 + 160), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, (txt, col) in enumerate((("ARE YOU", (255, 255, 255)), ("READY?", col2))):
        tw = _f2.getlength(txt); d.text(((2000 - tw) / 2, 60 + i * lh), txt, font=_f2, fill=col + (255,))
    return im
TXW, TXG = _ready_layer((255, 255, 255)), _ready_layer(GOLD)

def ready_params(t):
    """alpha, scale, gold?, ghosts?  Straight text, no shake: every move is an eased punch or a slow push-in."""
    if t < 3.6 or t >= 6.3: return None
    if t < 3.8: return .30, .92, False, False
    if t < 4.0: return 1.0, lerp(1.06, 1.0, eo_cubic((t - 3.8) / .2)), False, False
    if t < 4.15: return .22, .95, False, False
    if t < 4.45: return 1.0, lerp(1.08, 1.0, eo_cubic((t - 4.15) / .3)), False, False
    if t < 6.1: return 1.0, lerp(1.0, 1.05, eo_cubic((t - 4.45) / 1.65)), True, False
    u = (t - 6.1) / .2; return 1 - ei_cubic(u), lerp(1.05, 1.4, ei_cubic(u)), True, False

_TX1 = {k: v.resize((v.width // 2, v.height // 2), Image.LANCZOS).convert("RGBa") for k, v in (("w", TXW), ("g", TXG))}   # 1x, premultiplied
_OW, _OH = 1700, 1100
def _scale_layer(key, s):
    """Sub-pixel affine scale about the exact centre of a fixed-size canvas: no size rounding, no centre drift."""
    im1 = _TX1[key]; w1, h1 = im1.size
    out = im1.transform((_OW, _OH), Image.AFFINE, (1 / s, 0, w1 / 2 - (_OW / 2) / s, 0, 1 / s, h1 / 2 - (_OH / 2) / s), resample=Image.BICUBIC)
    return out.convert("RGBA")

def draw_ready(frame, t):
    p = ready_params(t)
    if not p: return
    a, s, gold, ghost = p
    im = _scale_layer("g" if gold else "w", s); cx, cy = 540, 940
    if ghost:
        off = int(round(30 * eo_cubic((t - 4.45) / 0.25)))
        for o in (-off, off): paste(frame, with_alpha(im, a * 0.32), cx + o - _OW // 2, cy - _OH // 2)
    paste(frame, with_alpha(im, a), cx - _OW // 2, cy - _OH // 2)

# ---------------------------------------------------------------- beat 3: diagonal word slices (type only, no pictures)
Y, X = np.mgrid[0:H, 0:W]; X = X.astype(np.float32); Y = Y.astype(np.float32)
PURPLE_BG, GOLD_BG, CREAM, DEEP, PURP_T = (92, 30, 118), (222, 170, 70), (247, 244, 250), (40, 12, 56), (122, 42, 150)
WORDS = [("SOMETHING", PURPLE_BG, GOLD), ("BIG", GOLD_BG, INK), ("IS", CREAM, PURP_T), ("COMING", DEEP, (255, 255, 255)),
         ("GET", PURPLE_BG, (255, 255, 255)), ("READY", GOLD_BG, INK)]

def _word_img(word, bg, fg):
    f = fit_font(word, 900)
    if f.size > 560: f = ImageFont.truetype(ANTON, 560)
    r = np.clip(np.sqrt(((X - 540) / 700) ** 2 + ((Y - 960) / 1200) ** 2), 0, 1)[..., None]
    base = Image.fromarray((np.array(bg, np.float32) * (1 - 0.28 * r ** 2)).astype(np.uint8)).convert("RGBA")
    bb = f.getbbox(word); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    lay = Image.new("RGBA", (W + 200, th + 260), (0, 0, 0, 0)); x0 = (lay.width - tw) / 2 - bb[0]
    sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).text((x0, 130 - bb[1] + 14), word, font=f, fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(8)); ImageDraw.Draw(lay).text((x0, 130 - bb[1]), word, font=f, fill=fg + (255,))
    lay = Image.alpha_composite(sh, lay).rotate(-3, resample=Image.BICUBIC, expand=True)
    paste(base, lay, 540 - lay.width / 2, 940 - lay.height / 2)
    d = ImageDraw.Draw(base); ry = int(940 + th / 2 + 90); seg = 26
    for i, x in enumerate(range(280, 800, seg)): d.rectangle((x, ry, min(x + seg, 800), ry + 12), fill=KENTE[i % 5] + (255,))
    return base.convert("RGB")
WORD_IMGS = [_word_img(*w) for w in WORDS]

def slice_frame(t):
    i = int((t - TT.SLICE_T0) / TT.SLICE_DUR); u = (t - TT.SLICE_T0) / TT.SLICE_DUR - i
    if i < 0 or i >= TT.N_SLICE: return None
    img = WORD_IMGS[i]; z = 1 + 0.07 * u
    if z > 1.001:
        w2, h2 = int(W / z), int(H / z); img = img.crop(((W - w2) // 2, (H - h2) // 2, (W - w2) // 2 + w2, (H - h2) // 2 + h2)).resize((W, H), Image.BILINEAR)
    arr = np.asarray(img, dtype=np.float32)
    sgn = 1 if i % 2 == 0 else -1; ang = math.radians(30 * sgn); nx, ny = math.sin(ang), math.cos(ang)
    dd = (X - 540) * nx + (Y - 960) * ny - (u - 0.5) * 340 * sgn
    hh = 620 * math.sin(math.pi * u) ** 0.55
    m = np.clip((hh - np.abs(dd)) / 1.5, 0, 1)
    out = arr * m[..., None] * (1 + 0.6 * max(0, 1 - u / 0.12))
    edge = np.clip(1 - np.abs(np.abs(dd) - hh) / 3.0, 0, 1) * (1.0 if hh > 3 else 0.0)
    for c in range(3): out[..., c] = out[..., c] * (1 - edge) + GOLD[c] * edge
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert("RGBA")

# ---------------------------------------------------------------- beat 4: STAY TUNED (no name, no logo, no details)
_r = np.sqrt(((X - 540) / (W * 0.85)) ** 2 + ((Y - 840) / (H * 0.55)) ** 2); _r = np.clip(_r, 0, 1)[..., None]
BG = Image.fromarray((np.array([92, 30, 118], np.float32) * (1 - _r) + np.array([12, 5, 20], np.float32) * _r).astype(np.uint8)).convert("RGBA")
def _stay_layer():
    f = fit_font("TUNED", 800); lh = int(f.size * 0.98)
    lay = Image.new("RGBA", (1000, lh * 2 + 160), (0, 0, 0, 0)); sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    for i, (txt, col) in enumerate((("STAY", (255, 255, 255)), ("TUNED", GOLD))):
        tw = f.getlength(txt); bb = f.getbbox(txt); pos = ((1000 - tw) / 2, 60 + i * lh - bb[1])
        ImageDraw.Draw(sh).text((pos[0], pos[1] + 14), txt, font=f, fill=(0, 0, 0, 130), stroke_width=7, stroke_fill=(0, 0, 0, 130))
        ImageDraw.Draw(lay).text(pos, txt, font=f, fill=col + (255,), stroke_width=7, stroke_fill=INK + (255,))
    return Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)), lay)
STAY = _stay_layer()
_tf = ImageFont.truetype(POPPINS, 46)
def _tagline():
    txt, sp = "WATCH THIS SPACE", 16; w = sum(_tf.getlength(c) + sp for c in txt) - sp
    im = Image.new("RGBA", (int(w) + 20, 90), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 10
    for c in txt: d.text((x, 12), c, font=_tf, fill=GOLD + (255,)); x += _tf.getlength(c) + sp
    seg = 26; rule = Image.new("RGBA", (560, 12), (0, 0, 0, 0)); rd = ImageDraw.Draw(rule)
    for i, x0 in enumerate(range(0, 560, seg)): rd.rectangle((x0, 0, min(x0 + seg, 560), 12), fill=KENTE[i % 5] + (255,))
    return im, rule
TAG, RULE = _tagline()
CENTER = (540, 800)
TAG_Y = int(CENTER[1] + STAY.height / 2 + 30); RULE_Y = TAG_Y + 100
_sr = random.Random(9)
BURST = [(_sr.uniform(0, 2 * math.pi), _sr.uniform(260, 640), _sr.uniform(11, 24), i % 4) for i in range(30)]
TWINK = [(540 + _sr.uniform(-470, 470), CENTER[1] + _sr.uniform(-420, 420), _sr.uniform(9, 20), _sr.random()) for _ in range(12)]

def reveal_frame(t):
    rt = t - TT.REVEAL; fr = BG.copy(); u = rt / 0.55
    s = 0.5 + 0.5 * eo_back(u, 2.4) if u < 1 else 1 + 0.035 * min(1, (rt - 0.55) / 3)
    logo = scaled(STAY, s)
    if 0.75 < rt < 1.45:
        arr = np.asarray(logo).astype(np.float32); h, w = arr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); pos = lerp(-0.2, 1.4, (rt - 0.75) / 0.7) * (w + 0.5 * h)
        band = np.clip(1 - np.abs((xx + yy * 0.5) - pos) / (0.07 * w), 0, 1) * 0.75
        arr[..., :3] += (255 - arr[..., :3]) * band[..., None]; logo = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    dx = 14 * math.exp(-rt * 12) * math.sin(rt * 70)
    paste(fr, with_alpha(logo, min(1, rt * 8)), CENTER[0] + dx - logo.width / 2, CENTER[1] - logo.height / 2)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    if 0 <= rt < 1.0:
        e = eo_cubic(rt); fade = 1 - ei_cubic(rt)
        for k, (ang, rad, r, c) in enumerate(BURST):
            col = [GOLD, (255, 255, 255), (212, 135, 155), (201, 153, 64)][c] + (int(255 * fade),)
            star(d, CENTER[0] + math.cos(ang) * (rad * e + 60) * 1.15, CENTER[1] + math.sin(ang) * (rad * e + 60) * 0.85, r * (1 - 0.5 * rt), col)
    if rt > 0.5:
        for (x, y, r, ph) in TWINK:
            a = max(0, math.sin(2 * math.pi * (rt * 0.7 + ph))) ** 3
            if a > 0.02: star(d, x, y, r, (255, 244, 214, int(255 * a)))
    fr.alpha_composite(ov)
    ta = min(1, max(0, (rt - 1.1) / 0.4))
    if ta > 0: paste(fr, with_alpha(TAG, ta), 540 - TAG.width / 2, TAG_Y); paste(fr, with_alpha(RULE, ta), 540 - RULE.width / 2, RULE_Y)
    if rt < 0.3: fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - rt / 0.3) ** 1.5))))
    return fr

# ---------------------------------------------------------------- frame assembly
BLACK = (6, 4, 10, 255)
def render(t):
    if t < TT.READY_T0:
        fr = Image.new("RGBA", (W, H), BLACK); lay = posters(t)
        g = lerp(1, 0.18, eo_cubic((t - TT.POSTER_DIM[0]) / (TT.POSTER_DIM[1] - TT.POSTER_DIM[0]))) if t > TT.POSTER_DIM[0] else 1
        if g < 1:
            a = np.asarray(lay).astype(np.float32); a[..., :3] *= g; lay = Image.fromarray(a.astype(np.uint8), "RGBA")
        fr.alpha_composite(lay)
    elif t < TT.READY_END + 0.1:
        fr = Image.new("RGBA", (W, H), BLACK); draw_ready(fr, t)
    elif t < TT.REVEAL:
        fr = slice_frame(t) or Image.new("RGBA", (W, H), BLACK)
        if fr is not None and t >= TT.SLICE_T0 and (t - TT.SLICE_T0) < 0: pass
    else:
        fr = reveal_frame(t)
    if t > TT.DUR - 0.6:
        k = max(0, (TT.DUR - t) / 0.6); a = np.asarray(fr).astype(np.float32); a[..., :3] *= k; fr = Image.fromarray(a.astype(np.uint8), "RGBA")
    return fr.convert("RGB")

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--preview":
        times = [float(x) for x in args[1].split(",")]; od = args[2]; os.makedirs(od, exist_ok=True)
        for t in times: render(t).resize((540, 960), Image.LANCZOS).save(os.path.join(od, "t_%05.2f.png" % t))
        sys.exit(0)
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(EDIT, "teaser_v1.mp4")
    audio = args[args.index("--audio") + 1] if "--audio" in args else None
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if audio: cmd += ["-i", audio]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p"]
    if audio: cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE); n = int(round(TT.DUR * FPS))
    for i in range(n):
        p.stdin.write(render(i / FPS).tobytes())
        if i % 60 == 0: print("frame", i, "/", n, flush=True)
    p.stdin.close(); p.wait(); print("wrote", out)
