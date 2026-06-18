import io
import os

from PIL import Image, ImageDraw, ImageFont, features
import arabic_reshaper
from bidi.algorithm import get_display

_RAQM = features.check("raqm")

_DIR = os.path.dirname(os.path.abspath(__file__))
_FONT_R = os.path.join(_DIR, "assets", "Tajawal-Regular.ttf")
_FONT_B = os.path.join(_DIR, "assets", "Tajawal-Bold.ttf")

BG = (21, 23, 30)
PANEL = (32, 36, 46)
DIV = (42, 47, 58)
TEAL = (45, 212, 191)
WHITE = (245, 247, 250)
GRAY = (154, 163, 178)
LGRAY = (220, 226, 234)
GREEN = (46, 212, 122)
RED = (255, 93, 93)
GREEN_DK = (22, 50, 31)
RED_DK = (58, 26, 28)
GREEN_LB = (110, 231, 168)
RED_LB = (246, 161, 161)
GREEN_TX = (185, 246, 207)
RED_TX = (255, 208, 208)
PILL_GTX = (11, 61, 36)
PILL_RTX = (74, 20, 20)
BADGE_BG = (20, 50, 47)
BADGE_TX = (94, 234, 212)


def _ar(t):
    t = str(t)
    if _RAQM:
        return t
    return get_display(arabic_reshaper.reshape(t))


_FONT_CACHE = {}


def _font(size, bold=False):
    key = (size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(_FONT_B if bold else _FONT_R, size)
    return _FONT_CACHE[key]


def render_result(you, opp, yp, op, win, loss, mode, name, frac=0.0, avatar_bytes=None):
    W, H = 700, 760
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    cx, cy, r = 86, 92, 46
    drew_avatar = False
    if avatar_bytes:
        try:
            av = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize((2 * r, 2 * r))
            mask = Image.new("L", (2 * r, 2 * r), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 2 * r, 2 * r), fill=255)
            img.paste(av, (cx - r, cy - r), mask)
            drew_avatar = True
        except Exception:
            drew_avatar = False
    if not drew_avatar:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PANEL)
        ch = (name or "?").strip()[:1] or "?"
        d.text((cx, cy), _ar(ch), font=_font(44, True), fill=TEAL, anchor="mm")
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=TEAL, width=3)

    d.text((150, cy), _ar(name or "لاعب"), font=_font(32, True), fill=WHITE, anchor="lm")

    label = "فريق" if mode == "team" else "فردية"
    bw, bh = 150, 52
    bx, by = W - 40 - bw, 66
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=26, fill=BADGE_BG, outline=TEAL, width=2)
    d.text((bx + bw / 2, by + bh / 2), _ar(label), font=_font(26, True), fill=BADGE_TX, anchor="mm")

    d.line((40, 162, W - 40, 162), fill=DIV, width=2)

    def player_row(y, accent, label_txt, value, pts, pill_tx):
        d.rounded_rectangle((40, y, W - 40, y + 100), radius=14, fill=PANEL)
        d.rounded_rectangle((48, y + 14, 56, y + 86), radius=4, fill=accent)
        d.text((W - 62, y + 50), _ar(f"{label_txt}: {value:,}"), font=_font(28, True), fill=LGRAY, anchor="rm")
        pw, ph = 150, 48
        px, py = 72, y + 26
        d.rounded_rectangle((px, py, px + pw, py + ph), radius=24, fill=accent)
        d.text((px + pw / 2, py + ph / 2), _ar(f"{pts} نقطة"), font=_font(24, True), fill=pill_tx, anchor="mm")

    player_row(188, GREEN, "شعبيتك", you, yp, PILL_GTX)
    player_row(302, RED, "الخصم", opp, op, PILL_RTX)

    gap = 30
    bw2 = (W - 80 - gap) // 2
    by2 = 432
    bh2 = 168
    d.rounded_rectangle((40, by2, 40 + bw2, by2 + bh2), radius=16, fill=GREEN_DK, outline=(31, 82, 54), width=2)
    d.text((40 + bw2 / 2, by2 + 44), _ar("فوزك يعطيك"), font=_font(24, True), fill=GREEN_LB, anchor="mm")
    d.text((40 + bw2 / 2, by2 + 108), f"+{win}", font=_font(56, True), fill=GREEN_TX, anchor="mm")
    lx = 40 + bw2 + gap
    d.rounded_rectangle((lx, by2, lx + bw2, by2 + bh2), radius=16, fill=RED_DK, outline=(90, 37, 40), width=2)
    d.text((lx + bw2 / 2, by2 + 44), _ar("خسارتك تخصم"), font=_font(24, True), fill=RED_LB, anchor="mm")
    d.text((lx + bw2 / 2, by2 + 108), f"\u2212{loss}", font=_font(56, True), fill=RED_TX, anchor="mm")

    py3 = 648
    d.text((W / 2, py3), _ar("تقدّمك للشريحة التالية"), font=_font(22), fill=GRAY, anchor="mm")
    bx3, bw3, bh3 = 40, W - 80, 18
    by3 = py3 + 26
    d.rounded_rectangle((bx3, by3, bx3 + bw3, by3 + bh3), radius=9, fill=DIV)
    fw = max(0, min(1.0, frac)) * bw3
    if fw >= 1:
        d.rounded_rectangle((bx3, by3, bx3 + fw, by3 + bh3), radius=9, fill=GREEN)

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
