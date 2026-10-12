# TracexGPT Local Testing Checklist

## Prerequisites

| Service     | Status Check                                            |
| ----------- | ------------------------------------------------------- |
| Backend     | `curl http://localhost:8080/health` → `{"status":true}` |
| Frontend    | `curl http://localhost:5173` → HTML response            |
| Presenton   | `curl http://localhost:5000` → 200 OK                   |
| Python 3.11 | `python --version` → `Python 3.11.x`                    |
| Node 20     | `node --version` → `v20.x.x`                            |

---

## 1. Core Chat Functionality

- [ ] Open WebUI loads at http://localhost:5173
- [ ] User can log in (create account if first run)
- [ ] Basic chat with OpenAI model responds correctly
- [ ] Chat history persists after page refresh
- [ ] Multiple conversations work (new chat, switch, delete)

---

## 2. Presenton PPT Generation Tool

### Basic Generation

- [ ] Ask "Generate a PPT about artificial intelligence"
- [ ] File appears as attachment in chat message
- [ ] Click to download the `.pptx` file
- [ ] File opens correctly in PowerPoint/Keynote

### Extended Parameters

- [ ] Test `slide_count`: "Generate a 12-slide PPT"
- [ ] Test `tone`: "Generate a casual/funny PPT about cats"
- [ ] Test `verbosity`: "Generate a detailed/verbose PPT"
- [ ] Test `template`: "Generate a PPT using the business template"

### Export Formats

- [ ] Test PDF export: "Generate a PDF presentation about blockchain"
- [ ] Downloaded file has `.pdf` extension
- [ ] PDF opens correctly in browser/PDF viewer

### Web Search Integration

- [ ] Test `web_search: true`: "Generate a PPT about latest AI news with web search"
- [ ] Verify content includes recent information

### File Upload Integration

- [ ] Upload a `.txt` or `.pdf` file to chat
- [ ] Ask "Generate a PPT from the uploaded file"
- [ ] PPT content reflects uploaded file material

### Edit URL

- [ ] After generation, click "Edit Presentation" link
- [ ] Opens Presenton editor at http://localhost:5000
- [ ] Can edit slides and re-export

---

## 3. Knowledge Base Integration

- [ ] Upload documents to Knowledge Base
- [ ] Ask "Generate a PPT using knowledge base about [topic]"
- [ ] Verify KB content is incorporated into slides
- [ ] Test `knowledge_query` parameter specifically

---

## 4. File TTL & Cleanup

### Configuration

- [ ] Check `FILE_TTL_DAYS=120` is loaded in environment
- [ ] Verify config appears in admin settings

### Metadata

- [ ] Generated PPT files have `expires_at` metadata
- [ ] SQLite database shows `meta` JSON with TTL

### Cleanup Task

- [ ] Check backend logs show `periodic_file_cleanup` running
- [ ] Verify task executes every 24 hours
- [ ] Create test: manually set `expires_at` to past date
- [ ] Verify file is removed by cleanup task

---

## 5. File System & Storage

- [ ] Files saved to `backend/data/uploads/`
- [ ] File names are unique (UUID-based)
- [ ] File metadata stored in SQLite `files` table
- [ ] File download works via API endpoint
- [ ] File deletion removes both DB record and filesystem

---

## 6. Chat UI File Display

- [ ] Generated file shows with correct icon (PPT/PDF)
- [ ] File size displayed in chat message
- [ ] Download button clickable
- [ ] File preview/thumbnail works (if implemented)
- [ ] Multiple files in same chat handled correctly

---

## 7. Presenton Microservice

- [ ] Service health check at http://localhost:5000
- [ ] OpenAI API key properly configured
- [ ] Can generate PPT via Presenton API directly (test via curl)
- [ ] Presenton logs show successful generation
- [ ] Error handling: Presenton down → graceful fallback message

---

## 8. Environment Variables

| Variable         | Value                 | Verified |
| ---------------- | --------------------- | -------- |
| `PRESENTON_URL`  | http://localhost:5000 | [ ]      |
| `PRESENTON_USER` | admin                 | [ ]      |
| `PRESENTON_PASS` | changeme              | [ ]      |
| `FILE_TTL_DAYS`  | 120                   | [ ]      |
| `OPENAI_API_KEY` | sk-proj-...           | [ ]      |

---

## 9. Error Handling

- [ ] Presenton unreachable → user-friendly error in chat
- [ ] Invalid OpenAI key → clear error message
- [ ] File upload too large → handled gracefully
- [ ] Network timeout during generation → retry or error
- [ ] Malformed PPT request → validation error

---

## 10. Frontend Changes (Your Customizations)

- [ ] Any Svelte UI modifications render correctly
- [ ] Admin dashboard changes visible
- [ ] Workspace tools page functions
- [ ] Sidebar/navigation modifications work
- [ ] Mobile responsive layout intact
- [ ] Theme/branding (logos, favicons) applied

---

## 11. Performance

- [ ] PPT generation completes under 30 seconds (simple topic)
- [ ] Frontend loads under 3 seconds
- [ ] Chat responses are snappy
- [ ] No memory leaks after extended use
- [ ] Cleanup task doesn't impact performance

---

## 12. Backend Logs Check

Watch for these in Terminal 1:

```
# Healthy signs:
INFO:     Uvicorn running on http://0.0.0.0:8080
INFO  [open_webui.tools.builtin] PPT generation started
INFO  [open_webui.tools.builtin] Uploaded file to Presenton
INFO  [open_webui.tools.builtin] Downloaded PPT file
INFO  [open_webui.tasks] periodic_file_cleanup running

# Warning signs:
ERROR [open_webui.tools.builtin] Presenton API error
ERROR [open_webui.tasks] Cleanup task failed
```

---

## Quick Test Commands

```bash
# Health checks
curl http://localhost:8080/health
curl http://localhost:5000
curl http://localhost:5173

# Check Presenton directly
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic":"test","slides":5}'

# Check file in DB
sqlite3 backend/data/webui.db "SELECT * FROM files LIMIT 5;"
```

---

## Sign-off

| Tester | Date | Result      |
| ------ | ---- | ----------- |
|        |      | Pass / Fail |
