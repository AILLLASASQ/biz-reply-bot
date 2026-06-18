# منطق حاسبة الشعبية — دوال خالصة بلا قاعدة بيانات (وضعان: فردية + فريق)

_ARABIC = str.maketrans("٠١٢٣٤٥٦٧٨٩،", "0123456789,")

_TABLE_SOLO = [
    (2000, 6),
    (4000, 10),
    (8000, 14),
    (15000, 16),
    (50000, 20),
    (120000, 24),
    (260000, 28),
    (500000, 32),
    (900000, 36),
    (2000000, 40),
    (8000000, 42),
]
_MAX_SOLO = 44

_TABLE_TEAM = [
    (5000, 6),
    (12000, 10),
    (26000, 14),
    (48000, 16),
    (120000, 20),
    (200000, 24),
    (400000, 28),
    (560000, 32),
    (800000, 34),
    (1600000, 36),
    (3200000, 38),
    (6000000, 40),
]
_MAX_TEAM = 42

_MODES = {
    "solo": {"table": _TABLE_SOLO, "max": _MAX_SOLO, "name": "المعركة الفردية", "kw": "حاسبة"},
    "team": {"table": _TABLE_TEAM, "max": _MAX_TEAM, "name": "معركة الفريق", "kw": "نقاط فريق"},
}


def _m(mode):
    return _MODES.get(mode, _MODES["solo"])


def parse_number(s):
    s = (s or "").translate(_ARABIC).strip().lower()
    s = s.replace(",", "").replace(" ", "")
    mult = 1
    if s.endswith("k"):
        mult, s = 1000, s[:-1]
    elif s.endswith("m"):
        mult, s = 1_000_000, s[:-1]
    try:
        val = float(s) * mult
    except ValueError:
        return None
    if val < 0:
        return None
    return int(val)


def points_for(value, mode="solo"):
    cfg = _m(mode)
    for upper, pts in cfg["table"]:
        if value <= upper:
            return pts
    return cfg["max"]


def compute(you, opp, mode="solo"):
    yp = points_for(you, mode)
    op = points_for(opp, mode)
    win = yp + op // 2
    loss = yp // 2
    return yp, op, win, loss


def _tier_info(value, mode="solo"):
    cfg = _m(mode)
    table = cfg["table"]
    lower = 0
    for i, (upper, pts) in enumerate(table):
        if value <= upper:
            next_pts = table[i + 1][1] if i + 1 < len(table) else cfg["max"]
            return lower, upper, pts, next_pts
        lower = upper + 1
    return table[-1][0] + 1, None, cfg["max"], None


def progress_fraction(value, mode="solo"):
    lower, upper, pts, next_pts = _tier_info(value, mode)
    if upper is None:
        return 1.0
    span = upper - lower
    return max(0.0, min(1.0, (value - lower) / span if span > 0 else 1.0))


def progress_bar(value, mode="solo", segments=10):
    cfg = _m(mode)
    lower, upper, pts, next_pts = _tier_info(value, mode)
    if upper is None:
        return f"🔝 أنت في أعلى شريحة ({cfg['max']} نقطة)."
    span = upper - lower
    frac = (value - lower) / span if span > 0 else 1.0
    frac = max(0.0, min(1.0, frac))
    filled = round(frac * segments)
    bar = "▓" * filled + "░" * (segments - filled)
    remaining = upper + 1 - value
    return (
        f"📊 تقدّمك للشريحة التالية ({next_pts} نقطة):\n"
        f"{bar} {int(frac * 100)}%\n"
        f"متبقّي {remaining:,} شعبية"
    )


def format_result(you, opp, mode="solo"):
    cfg = _m(mode)
    yp, op, win, loss = compute(you, opp, mode)
    return (
        f"🧮 حاسبة الشعبية ({cfg['name']})\n\n"
        f"🟢 شعبيتك: {you:,} ⟵ ({yp} نقطة)\n"
        f"🔴 الخصم: {opp:,} ⟵ ({op} نقطة)\n\n"
        f"✅ فوزك يعطيك: +{win} نقطة\n"
        f"❌ خسارتك تخصم: −{loss} نقطة\n\n"
        f"{progress_bar(you, mode)}\n\n"
        f"اكتب «{cfg['kw']}» لحساب آخر، أو «سجلي» لعملياتك."
    )


def format_history(ops):
    if not ops:
        return "📋 ما عندك عمليات بعد. اكتب «حاسبة» أو «نقاط فريق» لتبدأ."
    lines = ["📋 آخر عملياتك:\n"]
    for i, o in enumerate(ops, 1):
        tag = "👥" if o.get("mode") == "team" else "🧮"
        lines.append(
            f"{i}) {tag} {o['you']:,} ({o['yp']}) ضد {o['opp']:,} ({o['op']}) "
            f"← فوز +{o['win']} / خسارة −{o['loss']}"
        )
    return "\n".join(lines)


def format_table(mode="solo"):
    cfg = _m(mode)
    lines = [f"📊 جدول نقاط {cfg['name']}:\n"]
    lower = 0
    for upper, pts in cfg["table"]:
        lines.append(f"{lower:,} – {upper:,} = {pts} نقطة")
        lower = upper + 1
    lines.append(f"{lower:,} – ∞ = {cfg['max']} نقطة")
    lines.append("\nفوز: نقاطك + نصف نقاط الخصم")
    lines.append("خسارة: نصف نقاطك فقط")
    return "\n".join(lines)


def format_tables_all():
    return format_table("solo") + "\n\n" + ("─" * 12) + "\n\n" + format_table("team")
