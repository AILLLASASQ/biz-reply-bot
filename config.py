import os

# ===== Telegram =====
BOT_TOKEN = os.getenv("BOT_TOKEN")

# الرابط العام لتطبيقك على Render، مثال: https://your-app.onrender.com
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL", "")

# قيمة سرية تحمي مسار الويبهوك (أي نص عشوائي)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

WEBHOOK_PATH = f"/webhook/{WEBHOOK_SECRET}" if WEBHOOK_SECRET else "/webhook"
WEBHOOK_URL = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}"

# ===== Firestore =====
# على Render: ضع محتوى ملف الخدمة (JSON كاملاً) في هذا المتغير
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
# للتشغيل المحلي فقط: مسار ملف الخدمة على جهازك
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# ===== Server =====
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "10000"))
