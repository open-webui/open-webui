# Open WebUI & Pipelines: Customizations, Architecture & Sync Guide

This document provides a comprehensive, easy-to-understand reference for all custom modifications made to **Open WebUI** and **Pipelines**, guidance on managing user limits (50-member limit), and step-by-step instructions for maintaining and syncing your forks with upstream repositories.

---

## 1. 50-Member User Limit Management

Open WebUI (Community Edition) does not inherently hard-cap registrations by default. To restrict your deployment to **50 members**, use the following configuration strategies:

### A. Admin Approval Mode (Recommended)
Instead of open registration, require an admin to manually approve accounts:
1. In `backend/open_webui/config.py` (or via Admin Web UI -> **Admin Panel** -> **Settings** -> **General**):
   - Set **Default User Role** to `pending` (or `user` with signup disabled).
   - Set **Enable New Signups** to `False` once your 50 users are created.
2. Environment variables (in `.env` or system environment):
   ```env
   DEFAULT_USER_ROLE=pending
   ENABLE_SIGNUP=True
   ```
3. When 50 active users are approved in the **Admin Panel -> Users** table, toggle **Enable New Signups** to `False` (`ENABLE_SIGNUP=False`).

### B. Whitelist / Email Domain Restriction
Restrict access to a corporate email domain or pre-approved list of emails:
```env
ENABLE_SIGNUP=True
ALLOWED_EMAIL_DOMAINS=yourcompany.com
```

### C. Direct Database Inspection
You can inspect the total active member count at any time via:
```sql
SELECT count(*) FROM "user" WHERE role != 'pending';
```

---

## 2. Features Added (New Capabilities)

### 🎙️ 1. Sarvam AI Text-to-Speech (TTS) Integration
- **Engine**: Fully integrated Sarvam AI's `bulbul:v3` model into the backend audio dispatcher (`backend/open_webui/routers/audio.py`).
- **Voices Supported**: 14 Indic voice profiles (`aditya`, `shubh`, `manan`, `rahul`, `rohan`, `amit`, `shreya`, `ishita`, `ritu`, `pooja`, `roopa`, `suhani`, `neha`, `mani`).
- **Automatic Fallback Voice Mapping**: Automatically intercepts default OpenAI voices (like `alloy`) sent by the frontend and redirects them to a valid Sarvam speaker (`aditya`).
- **Transcoding Pipeline**: Automatically converts raw 24kHz/44.1kHz WAV base64 streams from Sarvam into standardized MP3 files using `pydub` to guarantee cross-browser playback.

### 🎧 2. Indic Punctuation & Sentence Chunking (`।` Danda Support)
- **Problem Solved**: The frontend only split sentences on English punctuation (`.`, `!`, `?`), causing entire Hindi/Gujarati paragraphs to be sent as a single monolithic block that took 15+ seconds to synthesize.
- **Solution**: Enhanced sentence extraction regex in `src/lib/utils/index.ts` to include the Devanagari / Indic full stop (`।`).
- **Benefit**: Decreased Time-to-First-Byte (TTFB) from ~16 seconds down to ~3–4 seconds.

### ⚡ 3. Parallel TTS Chunk Fetching (Zero-Pause Streaming Playback)
- **Problem Solved**: Open WebUI originally fetched TTS chunks sequentially in a blocking `for` loop. When one sentence finished playing before the next was synthesized, the audio queue went empty and prematurely killed speech playback.
- **Solution**: Rewrote the playback dispatcher in `src/lib/components/chat/Messages/ResponseMessage.svelte` to trigger parallel `Promise` fetches across all sentences simultaneously while enqueuing them strictly in order.
- **Benefit**: Eliminated the 2–3 second gaps between sentences and fixed the issue where only the first line was spoken.

### 🌐 4. Gujarati (`gu-IN`) UI & Translation Support
- Added dedicated Gujarati localization support (`src/lib/i18n/locales/gu-IN/`) and registered Gujarati in language index tables.

### 🛠️ 5. Custom Pipelines
- **Gemini No-Context Pipeline** (`pipelines/pipelines/gemini_nocontext_pipeline.py`): Lightweight direct LLM pipeline bypassing heavy chat context trees for faster single-turn answers.
- **N8N Automation Pipeline** (`pipelines/pipelines/n8n_pipeline.py`): Direct webhook integration connecting Open WebUI chats to N8N workflows for external data lookups, industrial pump monitoring, and automated alerts.

### 🌐 6. Windows Async DNS Resolution Fix (`session_pool.py`)
- Configured `aiohttp.ThreadedResolver()` in `backend/open_webui/utils/session_pool.py` to fix the known Windows Python bug where async DNS lookups failed with `Cannot connect to host api.sarvam.ai:443 [Could not contact DNS servers]`.

---

## 3. Features Customized / Modified

| Feature / File | Default Open WebUI Behavior | Customized Behavior |
| :--- | :--- | :--- |
| **Default TTS Engine** (`config.py`) | Empty / OpenAI (`tts-1` / `alloy`) | Set to `sarvam` (`bulbul:v3` / `aditya`) |
| **Whisper STT Model** (`config.py`) | `base` model (low Hindi accuracy) | Upgraded to `small` with `WHISPER_MULTILINGUAL=True` |
| **Default Suggestions** (`config.py`) | Generic college/art suggestions | Customized to industrial prompts: *Staging Analysis*, *Current Status*, *Anomaly Alerts* |
| **Language List** (`languages.json`) | 50+ international languages | Cleaned and pruned to essential languages (English, Gujarati, Hindi) |
| **Browser TTS Fallback** (`ResponseMessage.svelte`) | Defaulted unknown local engines to `browser-kokoro` | Removed Kokoro forced override; routes cleanly to backend Sarvam |
| **Audio API Transcoding** (`audio.py`) | Direct byte writing | Automatic WAV to MP3 format conversion with fallback |

---

## 4. Features Completely Removed / Cleaned Up

1. **Sidebar User Menu Bloat**:
   - Removed `src/lib/components/layout/Sidebar/UserMenu.svelte` to streamline the navigation experience and prevent unauthorized configuration edits.
2. **Complex Attachment Menus**:
   - Pruned bloated options in `src/lib/components/chat/MessageInput/InputMenu.svelte` to keep the input interface clean and focused.
3. **Generic Stock Prompt Cards**:
   - Replaced generic OpenAI demo prompts with domain-specific plant operations prompts.
4. **Redundant Locale Bundles**:
   - Removed unused international language translation packs to reduce frontend bundle size and build time.

---

## 5. Fork & Sync Guide (GitHub Step-by-Step)

Because your local folders are already complete Git repositories, you can connect them to your personal GitHub forks in minutes without losing any changes.

### Repositories Overview
1. **Main UI**: `c:\Users\om.raval\Downloads\om\openwebui\open-webui`
2. **Pipelines**: `c:\Users\om.raval\Downloads\om\openwebui\pipelines`

---

### Step 1: Fork on GitHub
1. Open your browser and log in to GitHub.
2. Fork the official Open WebUI repo: [github.com/open-webui/open-webui](https://github.com/open-webui/open-webui) -> Click **Fork**.
3. Fork the official Pipelines repo: [github.com/open-webui/pipelines](https://github.com/open-webui/pipelines) -> Click **Fork**.

---

### Step 2: Connect Local `open-webui` to Your Fork

Open PowerShell in `c:\Users\om.raval\Downloads\om\openwebui\open-webui`:

```bash
# 1. Rename the official repository remote to 'upstream'
git remote rename origin upstream

# 2. Add your GitHub fork as 'origin' (replace <your-github-username>)
git remote add origin https://github.com/<your-github-username>/open-webui.git

# 3. Create a dedicated branch for your custom work
git checkout -b custom-sarvam-build

# 4. Stage and commit all your local modifications
git add .
git commit -m "Add Sarvam TTS/STT, parallel audio streaming, Gujarati locale, and UI cleanup"

# 5. Push the branch to your GitHub fork
git push -u origin custom-sarvam-build
```

---

### Step 3: Connect Local `pipelines` to Your Fork

Open PowerShell in `c:\Users\om.raval\Downloads\om\openwebui\pipelines`:

```bash
# 1. Rename the official remote to 'upstream'
git remote rename origin upstream

# 2. Add your GitHub fork as 'origin' (replace <your-github-username>)
git remote add origin https://github.com/<your-github-username>/pipelines.git

# 3. Create a custom branch
git checkout -b custom-pipelines-build

# 4. Stage and commit changes
git add .
git commit -m "Add Gemini no-context and N8N automation pipelines"

# 5. Push to your GitHub fork
git push -u origin custom-pipelines-build
```

---

### Step 4: How to Pull Future Updates from Official Open WebUI

Whenever the official Open WebUI project releases new features or bug fixes:

```bash
# 1. Fetch latest changes from the official repo
git fetch upstream

# 2. Merge official updates into your custom branch
git checkout custom-sarvam-build
git merge upstream/main

# 3. If there are conflicts, resolve them, then push back to your fork:
git push origin custom-sarvam-build
```

---

## 6. Naive / Plain-Language Explanations

### *Why did Sarvam TTS take 15 seconds originally?*
> Sarvam’s API is like ordering food at a restaurant without a buffet — the chef has to cook the entire 5-course meal before bringing out any plate. If you send a huge paragraph, Sarvam waits until the entire paragraph is voiced before giving back any audio. 
> By splitting sentences on full stops (`.` and `।`), we ask for one dish at a time. The first dish arrives in 3 seconds, you start eating (listening), while the chef cooks the remaining dishes in the background.

### *Why did we need parallel fetching?*
> If you order 3 dishes one after another (sequentially), you finish eating dish #1, and then sit in silence for 4 seconds waiting for dish #2. 
> With parallel fetching, all 3 dishes are ordered at the exact same moment. Dish #1 arrives at second 3, dish #2 arrives at second 4, and dish #3 arrives at second 5. There are zero pauses between sentences.

### *What does `git remote rename origin upstream` actually do?*
> Think of `upstream` as the official factory (Open WebUI's main creators) and `origin` as your personal garage (your GitHub account). 
> Renaming the factory to `upstream` allows you to receive new parts from the factory whenever they release an update, while pushing your custom modifications safely to your personal garage (`origin`).
