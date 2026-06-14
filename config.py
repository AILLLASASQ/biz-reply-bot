import os


def _parse_ids(raw):
    ids = set()
    for part in (raw or "").replace(" ", "").split(","):
        if part.lstrip("-").isdigit():
            ids.add(int(part))
    return ids


BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}" if WEBHOOK_SECRET else "/webhook"
WEBHOOK_URL = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}"

FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

ADMIN_IDS = _parse_ids(os.getenv("ADMIN_IDS", ""))
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS", "2"))

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "10000"))
