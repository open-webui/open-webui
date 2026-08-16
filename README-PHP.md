# Open WebUI — PHP Edition

نسخه PHP از [Open WebUI](https://github.com/open-webui/open-webui) که روی **هر هاست سی‌پنلی** با PHP قابل اجراست.

## ✨ ویژگی‌ها

- 🤖 **رابط چت مشابه Open WebUI** — طراحی مدرن، تاریک، RTL
- 🔗 **اتصال مستقیم به OpenAI** — GPT-4o, GPT-3.5, DeepSeek, Claude, Gemini و ...
- 🏠 **پشتیبانی Ollama** — اتصال به مدل‌های محلی
- 💾 **تاریخچه گفتگوها** — ذخیره خودکار در SQLite
- 👤 **ورود/ثبت‌نام** — مدیریت کاربران با رمز هش‌شده
- ⚙️ **تنظیمات** — API Key, Base URL, نام مدل قابل تغییر
- 📱 **واکنش‌گرا** — سازگار با موبایل و تبلت
- 🚀 **بدون نیاز به Node.js یا Python** — فقط PHP + SQLite

## 📦 نصب روی هاست

1. **فایل‌ها رو آپلود کنید** — محتویات این پوشه رو در روت یا ساب‌پوشه هاست آپلود کنید
2. **پوشه `data` رو قابل نوشتن کنید** — `chmod 755 data/`
3. **فایل `api/auth.php` رو باز کنید** و حساب ادمین بسازید
4. **وارد شوید** — ایمیل و رمز خود را وارد کنید
5. **از بخش تنظیمات (⚙️)** کلید API و Base URL رو تنظیم کنید

## 🗂 ساختار فایل‌ها

```
├── index.php              # صفحه اصلی
├── api/
│   ├── config.php         # تنظیمات + دیتابیس + helperها
│   ├── auth.php           # API احراز هویت
│   ├── chat.php           # API مدیریت چت‌ها
│   ├── proxy.php          # پروکسی اتصال به OpenAI/Ollama
│   └── models.php         # لیست مدل‌ها
├── assets/
│   ├── css/app.css        # استایل‌ها (Material Dark)
│   └── js/app.js          # رابط کاربری
├── data/                  # SQLite database (قابل نوشتن)
│   └── openwebui.db       # خودکار ساخته می‌شود
└── .htaccess              # امنیت Apache
```

## 🔧 پیکربندی

### OpenAI / سازگار
در بخش تنظیمات (⚙️):
- **API Key**: کلید API خود را وارد کنید
- **Base URL**: آدرس API سرور (پیش‌فرض: `https://api.openai.com/v1`)
  - برای DeepSeek: `https://api.deepseek.com/v1`
  - برای OpenRouter: `https://openrouter.ai/api/v1`
  - برای Azure: آدرس endpoint خود

### Ollama (مدل محلی)
- **Ollama URL**: معمولاً `http://localhost:11434`
- از صفحه Ollama مدل‌ها دانلود و اجرا کنید

## 📋 نکات

- نیاز PHP >= 8.0 با پشتیبانی SQLite3
- اکثر هاست‌های ایرانی (ایده هاست، پارس‌هاست و ...) ساپورت می‌کنند
- برای دسترسی مستقیم: `.htaccess` موجود است
- دیتابیس SQLite در پوشه `data/` ذخیره می‌شود

## 📝 لایسنس

MIT — بر اساس [Open WebUI](https://github.com/open-webui/open-webui)
