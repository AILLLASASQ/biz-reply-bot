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

_owner_cache = {}
_data_cache = {}


def _now():
    return time.monotonic()


def _invalidate(owner_id):
    _data_cache.pop(str(owner_id), None)


def _fs_read_owner_id(conn_id):
    doc = _db.collection("connections").document(conn_id).get()
    return doc.to_dict().get("owner_id") if doc.exists else None


def _fs_read_business(owner_id):
    doc = _db.collection("businesses").document(str(owner_id)).get()
    if not doc.exists:
        return {"is_enabled": False, "rules": []}
    d = doc.to_dict()
    return {"is_enabled": bool(d.get("is_enabled")), "rules": d.get("rules", [])}


def _fs_save_connection(owner_id, conn_id, enabled):
    _db.collection("businesses").document(str(owner_id)).set(
        {"connection_id": conn_id, "is_enabled": enabled}, merge=True
    )
    _db.collection("connections").document(conn_id).set({"owner_id": str(owner_id)})


def _fs_set_enabled(owner_id, enabled):
    _db.collection("businesses").document(str(owner_id)).set(
        {"is_enabled": enabled}, merge=True
    )


def _fs_set_rules(owner_id, rules):
    _db.collection("businesses").document(str(owner_id)).set(
        {"rules": rules}, merge=True
    )


async def get_reply_context(conn_id):
    cached = _owner_cache.get(conn_id)
    if cached and _now() - cached[1] < CACHE_TTL:
        owner_id = cached[0]
    else:
        owner_id = await asyncio.to_thread(_fs_read_owner_id, conn_id)
        if owner_id:
            _owner_cache[conn_id] = (owner_id, _now())
    if not owner_id:
        return None, False, []

    dcached = _data_cache.get(owner_id)
    if dcached and _now() - dcached[1] < CACHE_TTL:
        data = dcached[0]
    else:
        data = await asyncio.to_thread(_fs_read_business, owner_id)
        _data_cache[owner_id] = (data, _now())

    return owner_id, data["is_enabled"], data["rules"]


async def save_connection(owner_id, conn_id, enabled):
    await asyncio.to_thread(_fs_save_connection, owner_id, conn_id, enabled)
    _owner_cache[conn_id] = (str(owner_id), _now())
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
        "keyword": keyword,
        "reply": reply,
        "match_type": match_type,
        "buttons": buttons or [],
    }
    rules.append(rule)
    await asyncio.to_thread(_fs_set_rules, owner_id, rules)
    _invalidate(owner_id)
    return rule["id"]


async def delete_rule(owner_id, rule_id):
    data = await asyncio.to_thread(_fs_read_business, owner_id)
    rules = [r for r in data["rules"] if r.get("id") != rule_id]
    await asyncio.to_thread(_fs_set_rules, owner_id, rules)
    _invalidate(owner_id)
