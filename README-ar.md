# Open WebUI — Arabic Localization & RTL Support

# Open WebUI — التعريب والدعم الكامل للغة العربية

> **Pull Request documentation** — ترويسة طلب السحب
>
> This document describes the Arabic improvements contributed to Open WebUI. It is written in Arabic and English, and accompanies the Pull Request for review. — يوثّق هذا المستند التحسينات العربية المضافة إلى Open WebUI، وهو مكتوب بالعربية والإنجليزية، ويُرافق طلب السحب للمراجعة.

---

## Table of Contents | فهرس المحتويات

1. [Overview | نظرة عامة](#overview)
2. [The 5 Major Features | الميزات الخمس الرئيسية](#features)
3. [Screenshots | لقطات الشاشة](#screenshots)
4. [Installation Guide | دليل التثبيت](#installation)
5. [Verification | التحقق](#verification)
6. [Files Changed | الملفات المعدَّلة](#files-changed)
7. [Notes for Reviewers | ملاحظات للمراجعين](#reviewers)

---

<a name="overview"></a>

## 1. Overview | نظرة عامة

**EN —** This contribution turns Open WebUI into a fully Arabic-ready product. Arabic is the world's 4th most-spoken language (~400M native speakers), yet open-source LLM chat UIs are almost universally built left-to-right with English-first interfaces. This PR closes that gap by adding: a complete **RTL (right-to-left)** layout, **100% Arabic localization**, **Arabic-aware search**, **automatic Arabic text-to-speech**, and a **Hijri (Islamic) calendar view**. As a by-product, RTL also benefits Hebrew, Persian, Urdu, Uyghur and Kurdish speakers.

**عربي —** يحوّل هذا العمل Open WebUI إلى منتج عربي متكامل. اللغة العربية هي رابع أكثر اللغات انتشارًا في العالم (نحو 400 مليون ناطق أصلي)، ومع ذلك فإن واجهات محادثات نماذج اللغة مفتوحة المصدر مبنية شبه دائمًا باتجاه من اليسار إلى اليمين وبتعامل إنجليزي أولًا. يسدّ هذا الطلب تلك الفجوة عبر إضافة: **واجهة كاملة من اليمين إلى اليسار (RTL)**، و**تعريب بنسبة 100%**، و**بحث مدرِك للعربية**، و**نطق عربي تلقائي**، و**عرض تقويم هجري**. وكمنفعة إضافية، يستفيد من دعم RTL أيضًا متحدثو العبرية والفارسية والأردية والأويغورية والكردية.

---

<a name="features"></a>

## 2. The 5 Major Features | الميزات الخمس الرئيسية

### Feature 1 — Full Right-to-Left (RTL) Support | دعم كامل لاتجاه النص من اليمين إلى اليسار

|          |                                                                                                                                                                                                            |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **EN**   | The `dir="rtl"` attribute is now applied automatically to `<html>` whenever the active locale is RTL (Arabic, Hebrew, Persian, Urdu, Uyghur, Kurdish). It switches live on language change with no reload. |
| **عربي** | يُضبط `dir="rtl"` تلقائيًا على `<html>` كلما كانت اللغة النشطة من لغات RTL (العربية، العبرية، الفارسية، الأردية، الأويغورية، الكردية)، ويتحول فورًا عند تغيير اللغة دون إعادة تحميل.                       |

Key changes | أبرز التعديلات:

- **`src/lib/i18n/index.ts`** — `applyDirection()` sets `document.documentElement.dir` on `initialized`/`languageChanged`; `RTL_LOCALES` list drives detection. A `dir`/`lang`-aware store keeps the whole app reactive.
- **`src/app.html`** — a tiny inline script sets `lang`/`dir` before first paint, eliminating the "LTR flash" on load.
- **`src/lib/rtl.css`** — a dedicated RTL stylesheet mirrors layouts that rely on physical `margin-left`/`margin-right` utilities (e.g. `ml-auto`), so navigation bars, headers and popovers flip correctly.
- **`src/lib/components/layout/Sidebar.svelte`** — the drag-resize handler uses `dir === 'rtl' ? -e.clientX : e.clientX`, so dragging the sidebar works naturally in both directions.
- RTL is **additive**: every rule is scoped under `[dir="rtl"]` or applies only to RTL locales, so LTR users see zero change.

---

### Feature 2 — Arabic Search Normalization | تطبيع البحث العربي

|          |                                                                                                                                                                                                                                                                                             |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **EN**   | Arabic has multiple written forms of the same letter: hamza variants (أ إ آ), the two yāʾ forms (ي / ى), tāʾ marbūṭah (ة / ه), and optional diacritics. Searching "موسى" would fail against "موسي". A new normalization layer unifies these forms so searches match regardless of spelling. |
| **عربي** | تمتلك العربية أكثر من صورة كتابية للحرف نفسه: أشكال الهمزة (أ إ آ)، وصورتا الياء (ي / ى)، والتاء المربوطة (ة / ه)، والتشكيل الاختياري. كان البحث عن «موسى» يفشل إذا كانت النصوص المخزنة «موسي». يوحّد هذا التعديل الجديد تلك الأشكال فيطابق البحث أي تهجئة.                                 |

Key changes | أبرز التعديلات:

- **`backend/open_webui/utils/arabic_text.py`** — new helper: `normalize_arabic_text()` (hamza → ا, ى → ي, ة → ه, diacritics removed) and `is_arabic_text()`.
- **Retrieval / RAG** (`backend/open_webui/routers/retrieval.py`): stored document text **and** every query (`/retrieval/query/doc`, `/retrieval/query/collection`, hybrid search, rerankers) are normalized on the same canonical form, so retrieval is consistent.
- **Web search**: user queries are normalized before being sent to search engines.
- **Chat search** (`backend/open_webui/models/chats.py`): the search matches the **raw** query OR its **normalized** form — a strict superset, so results can only improve, never regress. Works for both SQLite and PostgreSQL.

---

### Feature 3 — Automatic Arabic TTS Voice | نطق عربي تلقائي

|          |                                                                                                                                                                      |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **EN**   | When the message text is Arabic and no explicit voice was chosen, the system now automatically selects an Arabic-capable voice instead of a generic English default. |
| **عربي** | عندما يكون نص الرسالة عربيًا ولم يُختر صوت صريح، يختار النظام تلقائيًا صوتًا عربيًا بدلًا من الصوت الإنجليزي الافتراضي.                                              |

Key changes | أبرز التعديلات:

- **`backend/open_webui/routers/audio.py`** — new `resolve_tts_voice(engine, payload)`:
  - **Azure TTS** → `ar-SA-ZariyahNeural` for Arabic input when the resolved voice is a generic default.
  - **OpenAI-compatible** → keeps `alloy` (already speaks Arabic well).
  - An **explicitly configured voice is always respected** — auto-selection only replaces generic defaults.
- The Azure voice list endpoint already enumerates Arabic voices, so `ar-*` options appear in the frontend voice picker.

---

### Feature 4 — Hijri (Islamic) Calendar View | عرض التقويم الهجري

|          |                                                                                                                               |
| -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **EN**   | The calendar now offers a Hijri view based on the Umm al-Qura calendar, showing the Islamic date alongside the Gregorian one. |
| **عربي** | يوفّر التقويم الآن عرضًا هجريًا استنادًا إلى تقويم أم القرى، يعرض التاريخ الإسلامي إلى جانب التاريخ الميلادي.                 |

Key changes | أبرز التعديلات:

- **`src/lib/utils/hijri.ts`** — new helper using the standard `Intl.DateTimeFormat` `islamic-umalqura` calendar (`formatHijri`, `formatHijriShort`, `isHijriPreferredLocale`).
- **`src/routes/(app)/calendar/+page.svelte`** — new **"Hijri | الهجري"** toggle button; the header shows the Hijri date, and it is **auto-enabled for Arabic-script locales** (configurable via the toggle).
- **`src/lib/components/calendar/CalendarView.svelte`** — each month-cell shows the compact Hijri day (`١٢ محرم`) below the Gregorian day when enabled.
- **`CalendarSidebar.svelte`** — the mini-month header is now localized (month/day names in the active language via `Intl`).
- Month/day names across the calendar are now rendered in the **active locale** (Arabic months in Arabic, etc.), no more hard-coded English.

---

### Feature 5 — 100% Arabic Localization | تعريب بنسبة 100%

|          |                                                                                                                                                                                     |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **EN**   | The Arabic locale previously had **1,947 empty keys** that silently fell back to English. All of them are now translated, giving **full coverage**: 0 missing keys, 0 empty values. |
| **عربي** | كان ملف العربية يحتوي سابقًا على **1,947 مفتاحًا فارغًا** تعود تلقائيًا إلى الإنجليزية. تُرجمت جميعها الآن، فبلغت التغطية **100%**: صفر مفاتيح مفقودة وصفر قيم فارغة.               |

Key changes | أبرز التعديلات:

- **`src/lib/i18n/locales/ar/translation.json`** — 1,947 new professional Modern Standard Arabic translations (admin panel, settings, calendar, channels, automations, RAG, voice, and more).
- **Placeholder-safe**: `{{variables}}`, plural suffixes (`_zero/_one/_two/_few/_many/_other`), `**markdown**`, newlines and date-format tokens are all preserved and verified programmatically.
- **55 technical entries** (product names, protocols, URLs, format tokens: `Azure`, `OpenAI`, `OAuth`, `JSON`, `DD/MM/YYYY`…) are intentionally kept in Latin script per translation convention.
- New keys such as `Hijri | الهجري` were added to both `en-US` and `ar` locales.
- Reproducible tooling added under `scripts/` (`fill-arabic-translations.mjs`, `merge-arabic-translations.mjs`) with a shared terminology glossary, so future UI strings can be translated consistently.

---

<a name="screenshots"></a>

## 3. Screenshots | لقطات الشاشة

> The screenshots below are to be captured from a running build with **Arabic (العربية)** selected as the interface language.
> — تُلتقط اللقطات التالية من نسخة قيد التشغيل مع اختيار **العربية** كلغة للواجهة.

| Screenshot                  | Placeholder path                          | What it shows                                                                                                                    | ما تعرضه                                                                                                        |
| --------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 1. RTL Chat                 | `docs/screenshots/01-rtl-chat.png`        | The chat workspace fully mirrored: sidebar on the right, message bubbles right-aligned, RTL input box, RTL title bar.            | مساحة المحادثة معكوسة بالكامل: الشريط الجانبي يمينًا، ورسائل تبدأ من اليمين، وحقل إدخال RTL، وشريط العنوان RTL. |
| 2. Arabic Settings          | `docs/screenshots/02-arabic-settings.png` | Settings panel rendered entirely in Arabic with RTL layout.                                                                      | لوحة الإعدادات معروضة كاملة بالعربية بتخطيط RTL.                                                                |
| 3. Hijri Calendar           | `docs/screenshots/03-hijri-calendar.png`  | Calendar month view with the Hijri toggle active: Hijri dates (e.g. ١٢ محرم) under each Gregorian day, Hijri date in the header. | عرض شهر التقويم مع تفعيل خيار الهجري: التاريخ الهجري (مثل ١٢ محرم) تحت كل يوم ميلادي، والتاريخ الهجري في الرأس. |
| 4. Normalized Arabic Search | `docs/screenshots/04-arabic-search.png`   | A RAG query using a hamza/yaa variant (e.g. «موسى» vs «موسي») returning the same results.                                        | استعلام RAG بصيغة مختلفة للهمزة/الياء (مثل «موسى» مقابل «موسي») يعيد النتائج نفسها.                             |
| 5. Arabic Voice (TTS)       | `docs/screenshots/05-arabic-tts.png`      | Audio settings showing the automatic Arabic voice selection (e.g. `ar-SA-ZariyahNeural`) for Arabic text.                        | إعدادات الصوت مع اختيار الصوت العربي تلقائيًا (مثل `ar-SA-ZariyahNeural`) للنص العربي.                          |
| 6. Arabic Admin Panel       | `docs/screenshots/06-arabic-admin.png`    | Admin panel (users, settings, permissions) fully localized in Arabic.                                                            | لوحة المسؤول (المستخدمون، الإعدادات، الأذونات) معرّبة بالكامل.                                                  |

---

<a name="installation"></a>

## 4. Installation Guide | دليل التثبيت

### A. Run from source (dev) | التشغيل من المصدر (تطوير)

**Backend | الواجهة الخلفية** — Python 3.11+ recommended:

```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate   |   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
# Optional performance packages:
pip install --upgrade torch torchvision torchaudio
cp .env.example .env
uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

**Frontend | الواجهة الأمامية** — Node.js 18–22:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

Open | افتح: `http://localhost:5173` → **Settings → General → Language → العربية (العربية)** to switch the interface. | اختر **العربية** من الإعدادات لتغيير لغة الواجهة.

### B. Docker | عبر دوكر

```bash
docker build -t open-webui-ar .
docker run -d -p 3000:8080 \
  -v open-webui:/app/backend/data \
  --name open-webui-ar \
  open-webui-ar
```

Or mount the patched source over the official image | أو اربط المصدر المعدَّل فوق الصورة الرسمية:

```bash
docker run -d -p 3000:8080 \
  -v ./open-webui-ar:/app \
  -v open-webui:/app/backend/data \
  --name open-webui-ar \
  ghcr.io/open-webui/open-webui:main
```

### C. Recommended env vars for Arabic | متغيرات بيئة مقترحة للعربية

| Variable                   | Purpose           | الغرض                   | Suggested                              | المقترح                    |
| -------------------------- | ----------------- | ----------------------- | -------------------------------------- | -------------------------- |
| `AUDIO_TTS_VOICE`          | Default TTS voice | الصوت الافتراضي للنطق   | `alloy` (auto Arabic override enabled) | (يُستبدل تلقائيًا بالعربي) |
| `WHISPER_MODEL`            | STT model         | نموذج التعرف على الكلام | `large-v3`                             | دقة أعلى للعربية           |
| `AUDIO_STT_ENGINE`         | STT engine        | محرك التعرف             | `whisper`                              | —                          |
| `ENABLE_RAG_HYBRID_SEARCH` | Hybrid retrieval  | البحث الهجين            | `true`                                 | مع الميزة رقم 2            |

---

<a name="verification"></a>

## 5. Verification | التحقق

| Check                                | التحقق                    | Result                                                              | النتيجة                              |
| ------------------------------------ | ------------------------- | ------------------------------------------------------------------- | ------------------------------------ |
| Frontend type-check (`svelte-check`) | فحص الأنواع               | **0 new errors** in changed files (only pre-existing issues remain) | صفر أخطاء جديدة في الملفات المعدَّلة |
| Prettier                             | التنسيق                   | Clean on all changed files                                          | نظيف على جميع الملفات المعدَّلة      |
| Locale JSON validity                 | سلامة ملفات الترجمة       | Valid JSON, 0 empty, 0 missing keys                                 | صحيح، صفر فراغات، صفر مفقود          |
| Placeholder interpolation            | عناصر الاستيفاء `{{...}}` | Programmatically verified for all translated keys                   | تحقق آلي لكل المفاتيح                |
| `svelte-kit sync`                    | مزامنة SvelteKit          | Passes                                                              | ناجح                                 |

Manual test checklist | قائمة اختبار يدوي:

- [ ] Switch language to العربية — whole UI mirrors instantly, no reload needed. | تبديل اللغة إلى العربية يعكس الواجهة فورًا دون إعادة تحميل.
- [ ] Chat search and RAG query with variants (أ/إ/آ، ى/ي، ة/ه) return consistent results. | بحث المحادثات واستعلام RAG بصيغ مختلفة.
- [ ] Arabic TTS produces Arabic speech on Azure engine. | النطق العربي يعمل على محرك Azure.
- [ ] Calendar shows Hijri dates with the toggle. | التقويم يعرض التواريخ الهجرية.
- [ ] Admin panel and settings are fully in Arabic. | لوحة المسؤول والإعدادات معرّبة بالكامل.

---

<a name="files-changed"></a>

## 6. Files Changed | الملفات المعدَّلة

| File                                                 | الملف | Purpose                                      | الغرض                       |
| ---------------------------------------------------- | ----- | -------------------------------------------- | --------------------------- |
| `src/lib/i18n/index.ts`                              |       | RTL `dir` handling                           | معالجة اتجاه RTL            |
| `src/app.html`                                       |       | Early `lang`/`dir` (no LTR flash)            | ضبط `lang`/`dir` مبكرًا     |
| `src/lib/rtl.css`                                    |       | RTL mirroring stylesheet                     | أنماط عكس RTL               |
| `src/routes/+layout.svelte`                          |       | Import RTL stylesheet                        | استيراد أنماط RTL           |
| `src/lib/components/layout/Sidebar.svelte`           |       | RTL-aware drag resize                        | سحب جانبي مدرِك لـ RTL      |
| `backend/open_webui/utils/arabic_text.py`            |       | Arabic normalization helpers                 | دوال التطبيع العربي         |
| `backend/open_webui/routers/retrieval.py`            |       | RAG + web-search normalization               | تطبيع RAG والبحث الإلكتروني |
| `backend/open_webui/models/chats.py`                 |       | Chat search raw+normalized (SQLite/Postgres) | بحث المحادثات بالصيغتين     |
| `backend/open_webui/routers/audio.py`                |       | Arabic TTS auto voice                        | الصوت العربي التلقائي       |
| `src/lib/utils/hijri.ts`                             |       | Hijri (Umm al-Qura) helpers                  | دوال التقويم الهجري         |
| `src/routes/(app)/calendar/+page.svelte`             |       | Hijri toggle + localized header              | زر الهجري ورأس ملوَّن       |
| `src/lib/components/calendar/CalendarView.svelte`    |       | Hijri day cells + localized strings          | خلايا هجرية ونصوص ملوّنة    |
| `src/lib/components/calendar/CalendarSidebar.svelte` |       | Localized mini-calendar                      | تقويم مصغر ملوَّن           |
| `src/lib/i18n/locales/ar/translation.json`           |       | 1,947 new Arabic translations                | 1,947 ترجمة عربية جديدة     |
| `src/lib/i18n/locales/en-US/translation.json`        |       | New `Hijri` key                              | مفتاح «الهجري» الجديد       |
| `scripts/fill-arabic-translations.mjs`               |       | Translation tooling                          | أدوات الترجمة               |
| `scripts/merge-arabic-translations.mjs`              |       | Translation merge/verify                     | دمج الترجمات والتحقق        |

---

<a name="reviewers"></a>

## 7. Notes for Reviewers | ملاحظات للمراجعين

**EN —**

1. **RTL scope** — This PR lays the RTL foundation (global `dir` + a scoped RTL stylesheet). A few deeply-nested components may still use physical CSS properties that need case-by-case logical-property tweaks; these are tracked as follow-ups and do not block the core direction flip.
2. **Search behavior** — Chat search matches _raw + normalized_ queries (a superset), so no existing English/Latin results change. RAG stores canonical text from the moment of this change onward; re-indexing older collections makes them fully consistent.
3. **TTS** — Auto-voice selection only overrides _generic_ defaults; any voice the user explicitly chooses is always respected.
4. **Translation** — 55 technical/proper-noun keys are intentionally kept in Latin script. Plural forms follow the CLDR Arabic categories (`_zero/_one/_two/_few/_many/_other`), all verified programmatically.
5. **LTR users** — All RTL behavior is gated behind RTL locales/`[dir="rtl"]`, so the default English experience is byte-for-byte unchanged.

**عربي —**

1. **نطاق RTL** — يضع هذا الطلب الأساس الكامل لاتجاه RTL؛ بعض المكونات العميقة قد تستخدم خصائص CSS فيزيائية تحتاج تعديلات صغيرة تُعالج في متابعات لاحقة.
2. **سلوك البحث** — بحث المحادثات يطابق الصيغة _الخام والمطبَّعة_ (مجموعة شاملة)، فلا تتغير أي نتائج إنجليزية/لاتينية قائمة. يخزّن RAG النص المطبَّع من هذا التغيير فصاعدًا؛ وإعادة فهرسة المجموعات القديمة تجعلها متسقة تمامًا.
3. **النطق** — الاختيار التلقائي للصوت لا يتجاوز إلا الصوت الافتراضي العام؛ أي صوت يختاره المستخدم صراحةً يُحترم دائمًا.
4. **الترجمة** — 55 مدخلًا تقنيًا/اسم علم أُبقي عليها بالأحرف اللاتينية عمدًا، وصيغ الجمع تتبع فئات CLDR العربية وقد تحققت آليًا.
5. **مستخدمو LTR** — كل سلوك RTL مشروط بلغات RTL أو `[dir="rtl"]`، فلا تتغير تجربة الإنجليزية الافتراضية إطلاقًا.

---

## License | الرخصة

This contribution follows the project's license. This document is provided for review purposes with the Pull Request. — يتبع هذا المساهمة ترخيص المشروع، ويُقدَّم هذا المستند لأغراض المراجعة مع طلب السحب.

<p align="center"><i>Made with care for the Arabic-speaking Open WebUI community — صُنع باهتمام لمجتمع العربية في Open WebUI</i></p>
