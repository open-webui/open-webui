# Chat Encryption (At-Rest)

Open WebUI can encrypt chat storage **in the browser** so the backend/database only ever stores ciphertext. This protects chat history from server-side disclosure (for example, database admins).

This feature does **not** encrypt the plaintext prompts sent to the backend for model inference.

## User Behavior

- When enabled, chats are saved as an encrypted `{ enc, meta }` wrapper.
- Existing plaintext chats remain readable. You can migrate them using **Settings → Data Controls → Encrypt All Chats**.
- A per-user encryption key is generated automatically and stored in the browser (IndexedDB).

### Recovery Key

Because the key is stored in the browser, clearing browser storage can make encrypted chats unreadable.

- **Export Recovery Key** copies the key so you can store it in a password manager.
- **Import Recovery Key** restores the key on a new browser/device.

## Sharing

Shared chat links include a decryption key in the URL fragment (`#k=...`). The fragment is not sent to the server, so the backend cannot decrypt the shared chat.

Anyone with the **full** link can read the chat.

## Server Configuration

These environment variables control encryption behavior:

- `WEBUI_CHAT_ENCRYPTION_DEFAULT` (default `false`): enable encryption by default for new users/sessions.
- `WEBUI_CHAT_ENCRYPTION_REQUIRED` (default `false`): reject plaintext chat writes (clients must encrypt before saving).
- `WEBUI_CHAT_ENCRYPTION_ALLOW_LEGACY_READ` (default `true`): when `REQUIRED=true`, allow reading old plaintext chats (writes still require migration).
