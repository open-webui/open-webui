# Mini WebUI — a lightweight, single-file cloud LLM chat

`index.html` is a complete, dependency-free chat interface (one HTML file, no build step)
that calls **any OpenAI-compatible cloud API** directly from the browser.

## Features

| Area | What it does |
|---|---|
| 🌩️ Cloud LLMs | Works with OpenAI, OpenRouter, Groq, Together, vLLM, local Ollama — anything speaking `/v1/chat/completions` |
| 📡 Pull models | "Pull models" button fetches `GET /models` with your key and fills the model picker |
| 📄 PDF | Text extracted fully client-side with pdf.js (up to 60 pages / ~200k chars) and added to context |
| 🖼️ Images | Sent as vision input (`image_url` parts) to multimodal models, auto-downscaled to 1024px |
| 🎬 Video | N frames captured evenly across the video via canvas and sent as images for VLM analysis |
| 📃 Text/code | 40+ text/code extensions read and embedded as fenced code blocks |
| ⚡ Streaming | SSE streaming with stop button, regenerate, copy, markdown + code blocks |
| 💾 Local-only | Chats & settings (incl. API key) live in `localStorage` — no server, no telemetry |
| 🌗 UI | Dark/light theme, mobile responsive, drag & drop, clipboard paste, chat export |

## Run it

Just open `index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 8080
# → http://localhost:8080
```

Then: **Settings → pick a provider preset → paste your API key → Pull models → Save.**

> **CORS note:** the browser calls the provider directly, so the API must allow browser
> requests. OpenAI, OpenRouter, Groq and Together do. For local Ollama set
> `OLLAMA_ORIGINS=*`. Anything else needs a small proxy in front.

## Deploy on Render (free Static Site)

1. Push this folder to your GitHub repo.
2. Render Dashboard → **New + → Static Site** → connect the repo.
3. Set **Root Directory**: `lightweight-webui`, and **Publish Directory**: `.` (leave build command empty).
4. Deploy — done. Visitors bring their **own API key** (stored only in their browser).

> ⚠️ Don't ship a shared API key inside this page: anyone using the site can read it
> from DevTools. For a public deployment with a shared key, put a tiny server-side
> proxy that holds the key and points `API base URL` at it instead.
