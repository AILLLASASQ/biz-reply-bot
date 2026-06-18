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


def _short(n):
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 1000:
        return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "K"
    return f"{n:,}"


def _draw_avatar(img, d, cx, cy, r, name, avatar_bytes):
    drew = False
    if avatar_bytes:
        try:
            av = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize((2 * r, 2 * r))
            mask = Image.new("L", (2 * r, 2 * r), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 2 * r, 2 * r), fill=255)
            img.paste(av, (cx - r, cy - r), mask)
            drew = True
        except Exception:
            drew = False
    if not drew:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PANEL)
        ch = (name or "?").strip()[:1] or "?"
        d.text((cx, cy), _ar(ch), font=_font(int(r * 0.9), True), fill=TEAL, anchor="mm")
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=TEAL, width=3)


def _verdict(yp, op):
    if yp > op:
        return "فوز", GREEN_DK, GREEN_TX, (31, 82, 54), GREEN, PILL_GTX
    if yp < op:
        return "خسارة", RED_DK, RED_TX, (90, 37, 40), RED, PILL_RTX
    return "تعادل", PANEL, LGRAY, DIV, GRAY, (25, 25, 25)


def _awarded(yp, op):
    if yp > op:
        return yp + op // 2, op // 2
    if yp < op:
        return yp // 2, op + yp // 2
    return yp, op


def render_result(you, opp, yp, op, mode, name, avatar_bytes=None):
    W, H = 700, 600
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _draw_avatar(img, d, 84, 80, 42, name, avatar_bytes)
    d.text((142, 80), _ar(name or "لاعب"), font=_font(30, True), fill=WHITE, anchor="lm")
    label = "فريق" if mode == "team" else "فردية"
    bw, bh = 140, 48
    bx, by = W - 40 - bw, 56
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=24, fill=BADGE_BG, outline=TEAL, width=2)
    d.text((bx + bw / 2, by + bh / 2), _ar(label), font=_font(24, True), fill=BADGE_TX, anchor="mm")
    d.line((40, 140, W - 40, 140), fill=DIV, width=2)

    def poprow(y, accent, txt):
        d.rounded_rectangle((40, y, W - 40, y + 78), radius=14, fill=PANEL)
        d.rounded_rectangle((48, y + 12, 56, y + 66), radius=4, fill=accent)
        d.text((W - 62, y + 39), _ar(txt), font=_font(28, True), fill=LGRAY, anchor="rm")

    poprow(156, GREEN, f"شعبيتك: {you:,}")
    poprow(246, RED, f"الخصم: {opp:,}")

    verdict, fill, txt, bd, _, _ = _verdict(yp, op)
    d.rounded_rectangle((40, 342, W - 40, 408), radius=16, fill=fill, outline=bd, width=2)
    d.text((W / 2, 375), _ar(f"النتيجة: {verdict}"), font=_font(34, True), fill=txt, anchor="mm")

    gap = 30
    bw2 = (W - 80 - gap) // 2
    y2, h2 = 426, 134
    yf, of = _awarded(yp, op)
    d.rounded_rectangle((40, y2, 40 + bw2, y2 + h2), radius=16, fill=GREEN_DK, outline=(31, 82, 54), width=2)
    d.text((40 + bw2 / 2, y2 + 38), _ar("نقاطك"), font=_font(24, True), fill=GREEN_LB, anchor="mm")
    d.text((40 + bw2 / 2, y2 + 92), str(yf), font=_font(50, True), fill=GREEN_TX, anchor="mm")
    lx = 40 + bw2 + gap
    d.rounded_rectangle((lx, y2, lx + bw2, y2 + h2), radius=16, fill=RED_DK, outline=(90, 37, 40), width=2)
    d.text((lx + bw2 / 2, y2 + 38), _ar("نقاط الخصم"), font=_font(24, True), fill=RED_LB, anchor="mm")
    d.text((lx + bw2 / 2, y2 + 92), str(of), font=_font(50, True), fill=RED_TX, anchor="mm")

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def render_history(name, ops, avatar_bytes=None):
    W = 700
    rh, gap = 112, 12
    n = max(1, len(ops))
    H = 174 + n * (rh + gap) + 16
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    _draw_avatar(img, d, 80, 74, 38, name, avatar_bytes)
    d.text((132, 74), _ar(name or "لاعب"), font=_font(28, True), fill=WHITE, anchor="lm")
    bw, bh = 120, 44
    bx, by = W - 40 - bw, 52
    d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=22, fill=BADGE_BG, outline=TEAL, width=2)
    d.text((bx + bw / 2, by + bh / 2), _ar("السجل"), font=_font(22, True), fill=BADGE_TX, anchor="mm")
    wins = sum(1 for o in ops if o["yp"] > o["op"])
    loss = sum(1 for o in ops if o["yp"] < o["op"])
    tie = sum(1 for o in ops if o["yp"] == o["op"])
    d.text((W / 2, 132), _ar(f"فوز {wins}  •  خسارة {loss}  •  تعادل {tie}"), font=_font(22, True), fill=GRAY, anchor="mm")
    d.line((40, 156, W - 40, 156), fill=DIV, width=2)
    y = 172
    for o in ops:
        you, opp, yp, op, mode = o["you"], o["opp"], o["yp"], o["op"], o.get("mode", "solo")
        d.rounded_rectangle((40, y, W - 40, y + rh), radius=14, fill=PANEL)
        vt, _, _, _, acc, _ = _verdict(yp, op)
        pf = GREEN if yp > op else RED if yp < op else GRAY
        pt = PILL_GTX if yp > op else PILL_RTX if yp < op else (25, 25, 25)
        d.rounded_rectangle((48, y + 14, 56, y + rh - 14), radius=4, fill=acc)
        d.text((W - 66, y + 34), _ar(f"الشعبية: {_short(you)} ضد {_short(opp)}"), font=_font(24, True), fill=LGRAY, anchor="rm")
        yf, of = _awarded(yp, op)
        d.text((W - 66, y + 70), _ar(f"النقاط: {yf} ضد {of}"), font=_font(23, True), fill=GRAY, anchor="rm")
        d.text((W - 66, y + 98), _ar("فردية" if mode == "solo" else "فريق"), font=_font(17), fill=(110, 120, 135), anchor="rm")
        pw, ph = 124, 48
        px, py = 70, y + (rh - ph) // 2
        d.rounded_rectangle((px, py, px + pw, py + ph), radius=24, fill=pf)
        d.text((px + pw / 2, py + ph / 2), _ar(vt), font=_font(25, True), fill=pt, anchor="mm")
        y += rh + gap
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
