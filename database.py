import json
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
            raise RuntimeError(
                "لا توجد بيانات اعتماد Firestore. عيّن FIREBASE_CREDENTIALS_JSON "
                "أو GOOGLE_APPLICATION_CREDENTIALS."
            )
        firebase_admin.initialize_app(cred)
    return firestore.client()


_db = _init()


# ============ الدوال المتزامنة (تُنفّذ في ثريد منفصل) ============

def _save_connection(owner_id, connection_id, enabled):
    _db.collection("businesses").document(str(owner_id)).set(
        {"connection_id": connection_id, "is_enabled": enabled},
        merge=True,
    )
    _db.collection("connections").document(connection_id).set(
        {"owner_id": str(owner_id)}
    )


def _get_owner(connection_id):
    doc = _db.collection("connections").document(connection_id).get()
    return doc.to_dict().get("owner_id") if doc.exists else None


def _set_enabled(owner_id, enabled):
    _db.collection("businesses").document(str(owner_id)).set(
        {"is_enabled": enabled}, merge=True
    )


def _is_enabled(owner_id):
    doc = _db.collection("businesses").document(str(owner_id)).get()
    return bool(doc.to_dict().get("is_enabled")) if doc.exists else False


def _add_rule(owner_id, keyword, reply, match_type):
    ref = (
        _db.collection("businesses")
        .document(str(owner_id))
        .collection("rules")
        .document()
    )
    ref.set({"keyword": keyword, "reply": reply, "match_type": match_type})
    return ref.id


def _get_rules(owner_id):
    docs = (
        _db.collection("businesses")
        .document(str(owner_id))
        .collection("rules")
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


def _delete_rule(owner_id, rule_id):
    (
        _db.collection("businesses")
        .document(str(owner_id))
        .collection("rules")
        .document(rule_id)
        .delete()
    )


# ============ أغلفة غير متزامنة (لمنع حجب حلقة الأحداث) ============

async def save_connection(owner_id, connection_id, enabled):
    return await asyncio.to_thread(_save_connection, owner_id, connection_id, enabled)


async def get_owner(connection_id):
    return await asyncio.to_thread(_get_owner, connection_id)


async def set_enabled(owner_id, enabled):
    return await asyncio.to_thread(_set_enabled, owner_id, enabled)


async def is_enabled(owner_id):
    return await asyncio.to_thread(_is_enabled, owner_id)


async def add_rule(owner_id, keyword, reply, match_type):
    return await asyncio.to_thread(_add_rule, owner_id, keyword, reply, match_type)


async def get_rules(owner_id):
    return await asyncio.to_thread(_get_rules, owner_id)


async def delete_rule(owner_id, rule_id):
    return await asyncio.to_thread(_delete_rule, owner_id, rule_id)
