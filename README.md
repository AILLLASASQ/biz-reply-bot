# telegram-business-autoreply

بوت يُربط بحساب **Telegram Business** ويرد تلقائياً على رسائل الزبائن
حسب كلمات مفتاحية يضيفها كل عميل بنفسه. متعدد المستأجرين (Multi-tenant):
بوت واحد يخدم عدة حسابات Business، ولكل حساب ردوده الخاصة.

التقنيات: Python · aiogram 3.x · Firestore · Render (Webhook)

## بنية المشروع

```
telegram-business-autoreply/
├── bot.py              # نقطة الدخول + خادم الويبهوك (aiohttp)
├── config.py           # متغيرات البيئة
├── database.py         # طبقة Firestore (أغلفة async)
├── states.py           # حالات FSM
├── keyboards.py        # الأزرار
├── handlers/
│   ├── __init__.py
│   ├── business.py     # ربط Business + الرد التلقائي
│   └── panel.py        # لوحة العميل: إضافة/عرض/حذف الردود
├── requirements.txt
├── render.yaml
├── .gitignore
├── .env.example
└── README.md
```

## التشغيل المحلي

```bash
pip install -r requirements.txt
cp .env.example .env      # ثم عبّئ القيم
python bot.py
```

محلياً تحتاج رابطاً عاماً للويبهوك (مثل ngrok) وتضعه في BASE_WEBHOOK_URL.

## النشر على Render

1. ارفع المشروع إلى GitHub (تأكد أن ملف الخدمة غير مرفوع — محمي في .gitignore).
2. على Render: New ← Web Service ← اربط المستودع (أو استخدم render.yaml).
3. أضف متغيرات البيئة في Environment:
   - `BOT_TOKEN`
   - `BASE_WEBHOOK_URL` = رابط خدمتك على Render
   - `WEBHOOK_SECRET` = نص عشوائي
   - `FIREBASE_CREDENTIALS_JSON` = محتوى ملف الخدمة كاملاً
4. استخدم خطة Starter (المجانية تنام وتفقد الرسائل).

## تفعيل Firestore

1. Firebase Console ← إنشاء مشروع.
2. Build ← Firestore Database ← Create database (Production mode).
3. Project Settings ← Service accounts ← Generate new private key (ملف JSON).
4. انسخ محتوى الملف كاملاً إلى متغير `FIREBASE_CREDENTIALS_JSON` على Render.

## ربط البوت بحساب Business

على هاتف العميل (يتطلب Telegram Premium):
الإعدادات ← Telegram Business ← Chatbots ← الصق يوزر البوت ← فعّل صلاحية الرد.
