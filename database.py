import json
import time
import uuid
import asyncio

import firebase_admin
from firebase_admin import credentials, firestore

import config


def _init():
    if not firebase_admin._apps:
        if config.FIREBASE_CREDENTIALS_JSON:
            cred = credentials.Certificate(json.loads(config.FIREBASE_CREDENTIALS_JSON))
        elif config.GOOGLE_APPLICATION_CREDENTIALS:
            cred = credentials.Certificate(config.GOOGLE_APPLICATION_CREDENTIALS)
        else:
            raise RuntimeError("لا توجد بيانات اعتماد Firestore.")
        firebase_admin.initialize_app(cred)
    return firestore.client()


_db = _init()

CACHE_TTL = 60
MAX_CACHE = 2000
FS_TIMEOUT = 15

_owner_cache = {}
_data_cache = {}
_ping_cache = {"ts": 0.0, "ok": False}


def _now():
    return time.monotonic()


def _cache_set(cache, key, value):
    if len(cache) >= MAX_CACHE and key not in cache:
        oldest = min(cache, key=lambda k: cache[k][1])
        cache.pop(oldest, None)
    cache[key] = value


def _invalidate(owner_id):
    _data_cache.pop(str(owner_id), None)


def _sub_active(data):
    exp = data.get("sub_expires") or 0
    return bool(exp) and time.time() < exp


def _greeting_of(data):
    return {
        "enabled": data.get("greeting_enabled", False),
        "text": data.get("greeting_text", ""),
        "hours": data.get("greeting_hours", 12),
        "activated_at": data.get("greeting_activated_at", 0),
    }


def _fs_read_owner_id(conn_id):
    doc = _db.collection("connections").document(conn_id).get(timeout=FS_TIMEOUT)
    return doc.to_dict().get("owner_id") if doc.exists else None


def _fs_read_business(owner_id):
    doc = _db.collection("businesses").document(str(owner_id)).get(timeout=FS_TIMEOUT)
    d = doc.to_dict() if doc.exists else {}
    return {
        "is_enabled": bool(d.get("is_enabled")),
        "rules": d.get("rules", []),
        "plan": d.get("plan"),
        "sub_expires": d.get("sub_expires") or 0,
        "greeting_enabled": bool(d.get("greeting_enabled")),
        "greeting_text": d.get("greeting_text") or "",
        "greeting_hours": d.get("greeting_hours") or 12,
        "greeting_activated_at": d.get("greeting_activated_at") or 0,
    }


def _fs_save_connection(owner_id, conn_id, enabled):
    _db.collection("businesses").document(str(owner_id)).set(
        {"connection_id": conn_id, "is_enabled": enabled}, merge=True, timeout=FS_TIMEOUT
    )
    _db.collection("connections").document(conn_id).set(
        {"owner_id": str(owner_id)}, timeout=FS_TIMEOUT
    )


def _fs_set_enabled(owner_id, enabled):
    _db.collection("businesses").document(str(owner_id)).set(
        {"is_enabled": enabled}, merge=True, timeout=FS_TIMEOUT
    )


def _fs_set_rules(owner_id, rules):
    _db.collection("businesses").document(str(owner_id)).set(
        {"rules": rules}, merge=True, timeout=FS_TIMEOUT
    )


def _fs_ensure_trial(owner_id, days):
    ref = _db.collection("businesses").document(str(owner_id))
    doc = ref.get(timeout=FS_TIMEOUT)
    d = doc.to_dict() if doc.exists else {}
    if not d.get("trial_used") and not d.get("sub_expires"):
        ref.set(
            {"plan": "trial", "sub_expires": time.time() + days * 86400, "trial_used": True},
            merge=True, timeout=FS_TIMEOUT,
        )
        return True
    return False


def _fs_set_subscription(owner_id, plan, days, admin_id=None):
    ref = _db.collection("businesses").document(str(owner_id))
    doc = ref.get(timeout=FS_TIMEOUT)
    d = doc.to_dict() if doc.exists else {}
    base = max(time.time(), d.get("sub_expires") or 0)
    new_exp = base + days * 86400
    ref.set({"plan": plan, "sub_expires": new_exp, "trial_used": True}, merge=True, timeout=FS_TIMEOUT)
    _db.collection("activations").add(
        {
            "owner_id": str(owner_id),
            "admin_id": str(admin_id) if admin_id else None,
            "plan": plan,
            "days": days,
            "ts": time.time(),
        },
        timeout=FS_TIMEOUT,
    )
    return new_exp


def _fs_update_rule_field(owner_id, rule_id, field, value):
    data = _fs_read_business(owner_id)
    rules = data["rules"]
    for r in rules:
        if r.get("id") == rule_id:
            r[field] = value
            break
    _fs_set_rules(owner_id, rules)


def _fs_set_greeting_field(owner_id, field, value):
    _db.collection("businesses").document(str(owner_id)).set(
        {field: value}, merge=True, timeout=FS_TIMEOUT
    )


def _fs_toggle_greeting(owner_id):
    ref = _db.collection("businesses").document(str(owner_id))
    doc = ref.get(timeout=FS_TIMEOUT)
    d = doc.to_dict() if doc.exists else {}
    new_enabled = not bool(d.get("greeting_enabled"))
    upd = {"greeting_enabled": new_enabled}
    if new_enabled:
        upd["greeting_activated_at"] = time.time()
    ref.set(upd, merge=True, timeout=FS_TIMEOUT)
    return new_enabled


def _fs_get_last_seen(owner_id, cust):
    doc = _db.collection("seen").document(f"{owner_id}_{cust}").get(timeout=FS_TIMEOUT)
    return doc.to_dict().get("ts") if doc.exists else None


def _fs_set_last_seen(owner_id, cust, ts):
    _db.collection("seen").document(f"{owner_id}_{cust}").set({"ts": ts}, timeout=FS_TIMEOUT)


def _fs_ping():
    list(_db.collection("connections").limit(1).get(timeout=FS_TIMEOUT))
    return True


async def get_reply_context(conn_id):
    cached = _owner_cache.get(conn_id)
    if cached and _now() - cached[1] < CACHE_TTL:
        owner_id = cached[0]
    else:
        owner_id = await asyncio.to_thread(_fs_read_owner_id, conn_id)
        if owner_id:
            _cache_set(_owner_cache, conn_id, (owner_id, _now()))
    if not owner_id:
        return None, False, [], False, _greeting_of({})

    dcached = _data_cache.get(owner_id)
    if dcached and _now() - dcached[1] < CACHE_TTL:
        data = dcached[0]
    else:
        data = await asyncio.to_thread(_fs_read_business, owner_id)
        _cache_set(_data_cache, owner_id, (data, _now()))

    return owner_id, data["is_enabled"], data["rules"], _sub_active(data), _greeting_of(data)


async def save_connection(owner_id, conn_id, enabled):
    await asyncio.to_thread(_fs_save_connection, owner_id, conn_id, enabled)
    _cache_set(_owner_cache, conn_id, (str(owner_id), _now()))
    _invalidate(owner_id)


async def is_enabled(owner_id):
    data = await asyncio.to_thread(_fs_read_business, owner_id)
    return data["is_enabled"]


async def set_enabled(owner_id, enabled):
    await asyncio.to_thread(_fs_set_enabled, owner_id, enabled)
    _invalidate(owner_id)


async def get_rules(owner_id):
    data = await asyncio.to_thread(_fs_read_business, owner_id)
    return data["rules"]


async def add_rule(owner_id, keyword, reply, match_type, buttons=None):
    data = await asyncio.to_thread(_fs_read_business, owner_id)
    rules = data["rules"]
    rule = {
        "id": uuid.uuid4().hex[:8],
        "keyword": (keyword or "").strip(),
        "reply": (reply or "").strip(),
        "match_type": match_type,
        "buttons": buttons or [],
    }
    rules.append(rule)
    await asyncio.to_thread(_fs_set_rules, owner_id, rules)
    _invalidate(owner_id)
    return rule["id"]


async def update_rule_field(owner_id, rule_id, field, value):
    if isinstance(value, str):
        value = value.strip()
    await asyncio.to_thread(_fs_update_rule_field, owner_id, rule_id, field, value)
    _invalidate(owner_id)


async def delete_rule(owner_id, rule_id):
    data = await asyncio.to_thread(_fs_read_business, owner_id)
    rules = [r for r in data["rules"] if r.get("id") != rule_id]
    await asyncio.to_thread(_fs_set_rules, owner_id, rules)
    _invalidate(owner_id)


async def ensure_trial(owner_id, days):
    created = await asyncio.to_thread(_fs_ensure_trial, owner_id, days)
    if created:
        _invalidate(owner_id)
    return created


async def set_subscription(owner_id, plan, days, admin_id=None):
    exp = await asyncio.to_thread(_fs_set_subscription, owner_id, plan, days, admin_id)
    _invalidate(owner_id)
    return exp


async def get_subscription(owner_id):
    data = await asyncio.to_thread(_fs_read_business, owner_id)
    return data["plan"], data["sub_expires"], _sub_active(data)


async def get_greeting(owner_id):
    data = await asyncio.to_thread(_fs_read_business, owner_id)
    return _greeting_of(data)


async def set_greeting_text(owner_id, text):
    await asyncio.to_thread(_fs_set_greeting_field, owner_id, "greeting_text", text)
    _invalidate(owner_id)


async def set_greeting_hours(owner_id, hours):
    await asyncio.to_thread(_fs_set_greeting_field, owner_id, "greeting_hours", hours)
    _invalidate(owner_id)


async def toggle_greeting(owner_id):
    enabled = await asyncio.to_thread(_fs_toggle_greeting, owner_id)
    _invalidate(owner_id)
    return enabled


async def get_last_seen(owner_id, cust):
    return await asyncio.to_thread(_fs_get_last_seen, owner_id, cust)


async def set_last_seen(owner_id, cust, ts):
    await asyncio.to_thread(_fs_set_last_seen, owner_id, cust, ts)


async def ping():
    now = time.time()
    if now - _ping_cache["ts"] < 30:
        return _ping_cache["ok"]
    try:
        ok = await asyncio.to_thread(_fs_ping)
    except Exception:
        ok = False
    _ping_cache["ts"] = now
    _ping_cache["ok"] = ok
    return ok
