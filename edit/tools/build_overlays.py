#!/usr/bin/env python3
"""Rebuild the Fun Fest 1.0 motion-graphic overlays (v2).

Look: flyer palette (purple + gold + kente stripe), icon badge, sized-to-text
cards so nothing overflows. Output: edit/animations_v2/<slot>/render.mov (ARGB qtrle, 1920x1080@30).
Usage: python3 build_overlays.py [slot_name ...]   (default: all slots)
"""
import io, os, subprocess, sys
import cairosvg
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H, FPS = 1920, 1080, 30
SS = 2  # supersample for crisp edges
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "animations_v2")
FONT_B = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"

PURPLE_L, PURPLE_R = (122, 42, 150), (86, 24, 112)
GOLD, GOLD_L = (201, 153, 64), (240, 199, 102)
ICON_INK = "#4B1262"
KENTE = [(230, 180, 34), (24, 18, 30), (212, 135, 155), (230, 180, 34), (122, 42, 150)]

ICONS = {
 "cap": '<path d="M24 8 44 18 24 28 4 18Z" fill="{c}"/><path d="M12 23v9c0 4 24 4 24 0v-9"/><path d="M44 18v13"/>',
 "parasol": '<path d="M5 26C5 14 14 7 24 7s19 7 19 19Z" fill="{c}"/><path d="M24 7v19M15 9l2 17M33 9l-2 17" stroke="#F0C766" stroke-width="2"/><path d="M24 26v13a4.5 4.5 0 0 1-9 0"/>',
 "gamepad": '<rect x="5" y="14" width="38" height="22" rx="11"/><path d="M16 20v10M11 25h10"/><circle cx="32" cy="22" r="1.8" fill="{c}"/><circle cx="37" cy="27" r="1.8" fill="{c}"/>',
 "users": '<circle cx="18" cy="16" r="6"/><path d="M6 38c0-8 5-12 12-12s12 4 12 12"/><circle cx="33" cy="19" r="4.5"/><path d="M33 28c6 0 10 3.5 10 10"/>',
 "link": '<path d="M21 27a7 7 0 0 0 10 0l6-6a7 7 0 0 0-10-10l-3 3"/><path d="M27 21a7 7 0 0 0-10 0l-6 6a7 7 0 0 0 10 10l3-3"/>',
 "doc": '<path d="M12 5h17l10 10v26a2 2 0 0 1-2 2H12a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"/><path d="M29 5v10h10M16 26h16M16 34h16"/>',
 "briefcase": '<rect x="5" y="14" width="38" height="26" rx="4"/><path d="M17 14v-4a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4M5 26h38"/><path d="M21 26v4h6v-4"/>',
 "target": '<circle cx="22" cy="26" r="15"/><circle cx="22" cy="26" r="8"/><circle cx="22" cy="26" r="2" fill="{c}"/><path d="M22 26 40 8M33 7h8v8"/>',
 "heart": '<path d="M24 41C9 30 6 20 11 14a9 9 0 0 1 13 2 9 9 0 0 1 13-2c5 6 2 16-13 27Z" fill="{c}"/>',
 "pin": '<path d="M24 44C14 32 10 26 10 19a14 14 0 0 1 28 0c0 7-4 13-14 25Z" fill="{c}"/><circle cx="24" cy="19" r="5" fill="#F0C766" stroke="none"/>',
 "cal": '<rect x="6" y="10" width="36" height="32" rx="4"/><path d="M6 20h36M16 5v9M32 5v9"/><path d="M15 28h4M22 28h4M29 28h4M15 35h4M22 35h4" stroke-width="3"/>',
 "plane": '<path d="M44 5 4 21l15 6 6 15Z" fill="{c}"/><path d="M19 27 44 5" stroke="#F0C766" stroke-width="2.4"/>',
}

def icon_img(name, px, color=ICON_INK, stroke=3.4):
    inner = ICONS[name].replace("{c}", color)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" fill="none" stroke="{color}" '
           f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{inner}</svg>')
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=px, output_height=px)
    return Image.open(io.BytesIO(png)).convert("RGBA")

def spaced_width(txt, font, sp):
    return sum(font.getlength(ch) + sp for ch in txt) - sp

def draw_spaced(d, xy, txt, font, fill, sp):
    x, y = xy
    for ch in txt:
        d.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + sp

def grad_h(w, h, c1, c2):
    base = Image.new("RGBA", (w, h))
    px = base.load()
    for x in range(w):
        t = x / max(1, w - 1)
        col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (255,)
        for y in range(h):
            px[x, y] = col
    return base

class Card:
    """Three layers (body, text, badge) in card-local coords, already supersampled."""
    def __init__(self, title, kicker, icon, kicker_icon=None):
        s = SS
        self.tf = ImageFont.truetype(FONT_B, 46 * s)
        self.kf = ImageFont.truetype(FONT_B, 21 * s)
        ksp = 3.2 * s
        tw = self.tf.getlength(title)
        kw = spaced_width(kicker, self.kf, ksp)
        kic = 30 * s if kicker_icon else 0
        kgap = 10 * s if kicker_icon else 0
        text_w = max(tw, kw + kic + kgap)
        D = 118 * s; BH = 106 * s
        pad_l, pad_r = 26 * s, 44 * s   # pad_l measured from badge right edge
        self.margin = 36 * s            # room for shadow
        body_x0 = self.margin + D // 2
        body_w = D // 2 + pad_l + int(text_w) + pad_r
        self.cw = self.margin * 2 + D // 2 + body_w
        self.ch = self.margin * 2 + D
        cy = self.ch // 2
        # body
        body = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        mask = Image.new("L", (self.cw, self.ch), 0)
        md = ImageDraw.Draw(mask)
        box = (body_x0, cy - BH // 2, body_x0 + body_w, cy + BH // 2)
        md.rounded_rectangle(box, radius=BH // 2.4, fill=255)
        g = grad_h(self.cw, self.ch, PURPLE_L, PURPLE_R)
        body.paste(g, (0, 0), mask)
        # kente stripe along the bottom edge
        stripe = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stripe)
        sh = 9 * s; seg = 14 * s
        x = box[0] - (box[0] % seg)
        i = 0
        while x < box[2]:
            sd.rectangle((x, box[3] - sh, x + seg, box[3]), fill=KENTE[i % len(KENTE)] + (255,))
            x += seg; i += 1
        stripe.putalpha(ImageChops.multiply(stripe.getchannel("A"), mask))
        body = Image.alpha_composite(body, stripe)
        # gold rim
        rim = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        ImageDraw.Draw(rim).rounded_rectangle(box, radius=BH // 2.4, outline=GOLD + (255,), width=2 * s)
        body = Image.alpha_composite(body, rim)
        # shadow
        sha = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        sha.putalpha(mask.point(lambda v: int(v * 0.45)))
        sha = sha.filter(ImageFilter.GaussianBlur(10 * s))
        sha = ImageChops.offset(sha, 0, 8 * s)
        self.body = Image.alpha_composite(sha, body)
        # text
        txt = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        td = ImageDraw.Draw(txt)
        tx = body_x0 + D // 2 + pad_l - D // 2 + D // 2 - D // 2  # == body_x0 + pad_l
        tx = body_x0 + pad_l + 0
        tx = self.margin + D + pad_l - 0 - (D // 2) + (D // 2) - 0  # badge right edge + pad
        tx = self.margin + D + pad_l - 8 * s
        ky = cy - 41 * s
        kx = tx
        if kicker_icon:
            ki = icon_img(kicker_icon, kic, color="#F0C766", stroke=3.0)
            txt.alpha_composite(ki, (kx, ky - 3 * s))
            kx += kic + kgap
        draw_spaced(td, (kx, ky), kicker, self.kf, GOLD_L + (255,), ksp)
        td.text((tx, cy - 19 * s), title, font=self.tf, fill=(255, 255, 255, 255))
        self.text = txt
        self.text_x0, self.text_x1 = tx, tx + int(text_w)
        # badge
        bd = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        bm = Image.new("L", (self.cw, self.ch), 0)
        bx0 = self.margin
        ImageDraw.Draw(bm).ellipse((bx0, cy - D // 2, bx0 + D, cy + D // 2), fill=255)
        gg = Image.new("RGBA", (self.cw, self.ch))
        gp = gg.load()
        for yy in range(cy - D // 2, cy + D // 2):
            t = (yy - (cy - D // 2)) / D
            col = tuple(int(GOLD_L[i] + (GOLD[i] - GOLD_L[i]) * t) for i in range(3)) + (255,)
            for xx in range(bx0, bx0 + D):
                gp[xx, yy] = col
        bd.paste(gg, (0, 0), bm)
        ring = Image.new("RGBA", (self.cw, self.ch), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((bx0, cy - D // 2, bx0 + D, cy + D // 2), outline=(255, 255, 255, 255), width=4 * s)
        bd = Image.alpha_composite(bd, ring)
        ic = icon_img(icon, int(D * 0.56))
        bd.alpha_composite(ic, (bx0 + (D - ic.width) // 2, cy - ic.height // 2))
        self.badge = bd
        self.badge_c = (bx0 + D // 2, cy)  # center, for scaling
        # downsample all layers
        K = 1.2  # overall card scale
        def dn(im): return im.resize((int(self.cw * K / s), int(self.ch * K / s)), Image.LANCZOS)
        self.body, self.text, self.badge = dn(self.body), dn(self.text), dn(self.badge)
        self.badge_c = (int(self.badge_c[0] * K / s), int(self.badge_c[1] * K / s))
        self.margin = int(self.margin * K / s)
        self.text_x0 = int(self.text_x0 * K / s); self.text_x1 = int(self.text_x1 * K / s)
        R = int(61 * K)
        self.badge_crop = self.badge.crop((self.badge_c[0] - R, self.badge_c[1] - R, self.badge_c[0] + R, self.badge_c[1] + R))
        self.w, self.h = self.body.size

def ease_out_cubic(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def ease_in_cubic(t): t = min(max(t, 0), 1); return t ** 3
def ease_out_back(t, k=1.9):
    t = min(max(t, 0), 1); u = t - 1
    return 1 + (k + 1) * u ** 3 + k * u ** 2

def full_card(card):
    im = card.body.copy()
    im.alpha_composite(card.text)
    im.alpha_composite(card.badge)
    return im

def render_frame(card, mode, t, dur):
    """t = seconds since item start; returns (RGBA layer, x, y) or None."""
    tin = min(0.5, dur * 0.35); tout = min(0.28, dur * 0.25)
    if t < 0 or t > dur: return None
    if mode == "center":
        if t < tin: p = ease_out_back(t / tin, 1.4); a = min(1, t / (tin * 0.5))
        elif t > dur - tout: p = 1 - ease_in_cubic((t - (dur - tout)) / tout) * 0.15; a = 1 - ease_in_cubic((t - (dur - tout)) / tout)
        else: p, a = 1.0, 1.0
        base = full_card(card)
        sw, sh = max(1, int(base.width * p)), max(1, int(base.height * p))
        im = base.resize((sw, sh), Image.LANCZOS)
        if a < 1: im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
        return im, (W - sw) // 2, (H - sh) // 2
    # top-left slide
    x_rest, y_rest = 64, 52
    if t < tin: e = ease_out_cubic(t / tin); xoff = -(card.w + 40) * (1 - e); a = min(1, t / (tin * 0.45))
    elif t > dur - tout: e = ease_in_cubic((t - (dur - tout)) / tout); xoff = -(card.w + 40) * e * 0.6; a = 1 - e
    else: xoff, a = 0, 1
    im = card.body.copy()
    # text wipe left->right
    ts = tin * 0.35; tdur = tin * 0.9
    wp = ease_out_cubic((t - ts) / tdur) if t >= ts else 0
    if wp > 0:
        tl = card.text.copy()
        cut = card.text_x0 - 6 + int((card.text_x1 - card.text_x0 + 40) * wp)
        m = Image.new("L", tl.size, 0); ImageDraw.Draw(m).rectangle((0, 0, cut, tl.height), fill=255)
        tl.putalpha(ImageChops.multiply(tl.getchannel("A"), m))
        im.alpha_composite(tl)
    # badge pop
    bp = ease_out_back((t - tin * 0.1) / (tin * 0.9), 2.4) if t >= tin * 0.1 else 0
    if bp > 0.01:
        bw, bh = card.badge_crop.size
        sb = card.badge_crop.resize((max(1, int(bw * bp)), max(1, int(bh * bp))), Image.LANCZOS)
        im.alpha_composite(sb, (card.badge_c[0] - sb.width // 2, card.badge_c[1] - sb.height // 2))
    if a < 1: im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im, int(x_rest + xoff - card.margin), y_rest - card.margin

# slot_name, edl_start, edl_dur, items(t0,t1,title,kicker,icon,kicker_icon,mode)
S = [
 ("slot_1_hook", 0.00, 4.40, [(0.15, 4.25, "SCHOOL IS BACK!", "FUN FEST 1.0", "cap", None, "tl")]),
 ("slot_2_center_all", 13.42, 2.15, [(13.52, 15.45, "FUN FEST 1.0", "TMGM OSUN REGION", "parasol", None, "center")]),
 ("slot_3_fungames", 15.57, 5.90, [
    (16.85, 18.50, "FUN & GAMES", "FEATURING", "gamepad", None, "tl"),
    (18.55, 19.70, "NEW FRIENDS", "FEATURING", "users", None, "tl"),
    (19.75, 21.40, "CONNECT WITH STUDENTS", "FEATURING", "link", None, "tl")]),
 ("slot_4_cv", 26.57, 4.22, [
    (26.92, 27.85, "BUILD A CV", "LEARN HOW TO", "doc", None, "tl"),
    (27.90, 28.80, "SET UP LINKEDIN", "LEARN HOW TO", "briefcase", None, "tl"),
    (28.85, 30.70, "FIND OPPORTUNITIES", "WORTH GOING FOR", "target", None, "tl")]),
 ("slot_5_godslove", 30.79, 3.24, [(32.00, 33.95, "GOD'S LOVE", "EXPERIENCE", "heart", None, "tl")]),
 ("slot_6_okuku", 35.71, 2.54, [(35.80, 38.20, "OKUKU CAMPUS", "WEDNESDAY, 2ND DECEMBER", "pin", "cal", "tl")]),
 ("slot_7_osogbo", 38.25, 2.38, [(38.33, 40.55, "OSOGBO CAMPUS", "FRIDAY, 4TH DECEMBER", "pin", "cal", "tl")]),
 ("slot_8_ifetedo", 40.63, 3.06, [(40.70, 43.65, "IFETEDO CAMPUS", "SATURDAY, 5TH DECEMBER", "pin", "cal", "tl")]),
 ("slot_9_campuses", 43.69, 2.92, [(43.78, 46.55, "ONE FEST, 3 CAMPUSES", "OKUKU · OSOGBO · IFETEDO", "pin", None, "tl")]),
 ("slot_10_savedate", 46.61, 3.48, [
    (46.72, 48.90, "INVITE YOUR FRIENDS", "YES, YOU!", "plane", None, "tl"),
    (48.95, 50.05, "SAVE THE DATE", "2ND · 4TH · 5TH DECEMBER", "cal", None, "tl")]),
 ("slot_11_finale", 50.09, 2.50, [(50.18, 52.55, "SEE YOU AT FUN FEST 1.0!", "TMGM OSUN REGION", "parasol", None, "center")]),
]

def build(slot):
    name, start, dur, items = slot
    cards = [Card(i[2], i[3], i[4], i[5]) for i in items]
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    out = os.path.join(d, "render.mov")
    n = int(round(dur * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", out], stdin=subprocess.PIPE)
    for f in range(n):
        tabs = start + f / FPS
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for it, card in zip(items, cards):
            r = render_frame(card, it[6], tabs - it[0], it[1] - it[0])
            if r:
                im, x, y = r
                _paste_clipped(canvas, im, x, y)
        p.stdin.write(canvas.tobytes())
    p.stdin.close(); p.wait()
    print("built", out, n, "frames", flush=True)

def _paste_clipped(canvas, im, x, y):
    # alpha_composite with negative offsets: crop the part that lands on canvas
    cx0, cy0 = max(0, -x), max(0, -y)
    if cx0 >= im.width or cy0 >= im.height: return
    sub = im.crop((cx0, cy0, im.width, im.height))
    canvas.alpha_composite(sub, (max(0, x), max(0, y)))

if __name__ == "__main__":
    want = set(sys.argv[1:])
    for s in S:
        if not want or s[0] in want: build(s)
