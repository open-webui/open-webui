# Deepgram speech-to-text

Open WebUI supports Deepgram and Deepgram-compatible speech-to-text services.

In **Admin Panel → Settings → Audio**, select **Deepgram** as the speech-to-text
engine, then configure the **API URL** and **API Key**.

## Environment variables

| Variable           | Default                              | Description                                       |
| ------------------ | ------------------------------------ | ------------------------------------------------- |
| `AUDIO_STT_ENGINE` | Empty (local Whisper)                | Set to `deepgram` to use Deepgram speech-to-text. |
| `DEEPGRAM_API_URL` | `https://api.deepgram.com/v1/listen` | Full transcription endpoint URL.                  |
| `DEEPGRAM_API_KEY` | Empty                                | Deepgram API key.                                 |

For a self-hosted Deepgram-compatible service:

```env
AUDIO_STT_ENGINE=deepgram
DEEPGRAM_API_URL=http://owhisper:8080/v1/listen
DEEPGRAM_API_KEY=your-api-key
```

Use an endpoint reachable from the Open WebUI backend. The service must support
Deepgram's authentication, transcription request parameters, and response format.

With persistent configuration enabled, saved admin settings take precedence over
environment variables. Update existing settings in the admin Audio section.
