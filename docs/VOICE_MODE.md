# Voice mode

Open WebUI includes voice input and response playback without requiring a
cloud API key. The recommended baseline is:

- **STT:** local `faster-whisper` (`AUDIO_STT_ENGINE=''`)
- **TTS:** the browser Web Speech API (`AUDIO_TTS_ENGINE=''`)

Audio is still sent to the configured Open WebUI server for local Whisper
transcription. Browser TTS runs in the user's browser. Browser speech
recognition (`Web API` in the UI) is an optional alternative, but browser
support and its privacy behavior depend on the browser vendor.

## Quick start

1. Copy the example environment file and adjust only the values you need:

   ```bash
   cp .env.example .env
   ```

   On Windows PowerShell, use:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Start Open WebUI using the normal installation method. For a local Python
   installation:

   ```bash
   open-webui serve
   ```

   For Docker, keep the data volume so the Whisper model is retained:

   ```bash
   docker run -d -p 3000:8080 --env-file .env `
     -v open-webui:/app/backend/data `
     --name open-webui --restart always `
     ghcr.io/open-webui/open-webui:main
   ```

3. Open `http://localhost:3000` (Docker) or `http://localhost:8080` (Python),
   sign in as an administrator, and open **Admin Settings → Audio**.

4. Confirm **Speech-to-Text Engine** is **Whisper (Local)** and
   **Text-to-Speech Engine** is **Web API**, then save. The first local
   transcription downloads the configured Whisper model; subsequent requests
   use the cached model.

5. In **Settings → Audio**, choose a microphone, optionally set the language,
   and enable **Instant Auto-Send After Voice Transcription** or response
   auto-playback as desired. Allow microphone access when the browser asks.

## Local Whisper options

`WHISPER_MODEL='base'` is a balanced default. Smaller models use less memory
and are faster; larger models can improve accuracy but require more CPU/GPU
memory. Set `WHISPER_LANGUAGE` to an ISO-639-1 code such as `ru` or `en` when
the language is known; leave it empty for automatic detection.

`WHISPER_MODEL_AUTO_UPDATE='true'` permits downloading the model when it is
not cached. For an offline deployment, pre-populate `WHISPER_MODEL_DIR` in the
persistent data volume and set `WHISPER_MODEL_AUTO_UPDATE='false'`.
`WHISPER_COMPUTE_TYPE='int8'` is a CPU-friendly default. CUDA deployments may
need a different compute type supported by the installed runtime.

## Optional browser/local TTS

The default Web Speech API uses voices supplied by the browser or operating
system and needs no secret. Users can select a voice in **Settings → Audio**.
For fully local browser synthesis, users can select **Kokoro.js (Browser)**;
the model is downloaded and executed in the browser and is cached there.

## Optional online providers

OpenAI-compatible, Azure, ElevenLabs, Deepgram, and Mistral providers can be
selected in **Admin Settings → Audio**. Configure their credentials only via
deployment secrets or the admin UI; never commit real keys to `.env.example`,
documentation, or source control. If an online provider is required, use
placeholders in deployment configuration, for example:

```dotenv
AUDIO_STT_ENGINE='openai'
AUDIO_STT_OPENAI_API_BASE_URL='https://api.example.invalid/v1'
AUDIO_STT_OPENAI_API_KEY='<set-in-your-secret-store>'
AUDIO_STT_MODEL='<provider-model>'
```

Replace the placeholders with provider-specific values outside the repository.
