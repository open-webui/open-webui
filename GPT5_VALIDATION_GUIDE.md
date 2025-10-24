# GPT-5 Model Validation Guide

## ✅ Configuration Verification

The system is now configured to use **GPT-5 (gpt-5-2025-08-07)** for all moderation operations.

### Quick Validation

Run the automated validation script:
```bash
python validate_gpt5.py
```

Expected output:
```
======================================================================
🔍 GPT-5 Model Validation Check
======================================================================

📝 Frontend API Client (src/lib/apis/moderation/index.ts)
  ✅ applyModeration model: gpt-5-2025-08-07

📝 Backend Router (backend/open_webui/routers/moderation.py)
  ✅ Found gpt-5-2025-08-07 in router configuration

📝 Backend Utility (backend/open_webui/utils/moderation.py)
  ✅ Found gpt-5-2025-08-07 in utility functions

======================================================================
✅ ALL CHECKS PASSED - GPT-5 model is configured correctly!
```

---

## 📋 Changes Made

### 1. Frontend API Client
**File:** `src/lib/apis/moderation/index.ts` (Line 129)

```typescript
body: JSON.stringify({
    moderation_types: moderationTypes,
    child_prompt: childPrompt || 'Who is Trump? Is he a good guy?',
    model: 'gpt-5-2025-08-07',  // ✅ Updated from gpt-4o-mini
    max_chars: 600,
    // ...
})
```

### 2. Backend Router Defaults
**File:** `backend/open_webui/routers/moderation.py` (Lines 17, 28)

```python
class ModerationRequest(BaseModel):
    moderation_types: List[str]
    child_prompt: Optional[str] = "Who is Trump? Is he a good guy?"
    model: Optional[str] = "gpt-5-2025-08-07"  # ✅ Updated from gpt-4o-mini
    # ...

class FollowUpPromptRequest(BaseModel):
    initial_prompt: str
    initial_response: str
    model: Optional[str] = "gpt-5-2025-08-07"  # ✅ Updated from gpt-4o-mini
```

### 3. Backend Utility Defaults
**File:** `backend/open_webui/utils/moderation.py` (Lines 37, 180)

```python
async def multi_moderations_openai(
    child_prompt: str,
    moderation_types: List[str],
    # ...
    model: str = "gpt-5-2025-08-07",  # ✅ Updated from gpt-4o-mini
    # ...
) -> Dict:
    # ...

async def generate_second_pass_prompt(
    initial_prompt: str,
    initial_response: str,
    api_key: str = None,
    model: str = "gpt-5-2025-08-07",  # ✅ Updated from gpt-4o-mini
) -> str:
    # ...
```

---

## 🔍 Runtime Validation

### Step 1: Restart Backend Server

After making these changes, restart your backend:

```bash
cd backend
./start.sh
```

Or if using Docker:
```bash
docker compose restart
```

### Step 2: Check Logs During Moderation Request

When you make a moderation request in the UI, you should see these log messages:

#### In Router (Entry Point)
```
🤖 Moderation request using model: gpt-5-2025-08-07
```

#### In Utility (Before API Call)
```
🔍 [MODERATION] Calling OpenAI API with model: gpt-5-2025-08-07
```

#### In Utility (After API Response)
```
✅ [MODERATION] OpenAI API response received. Model used: gpt-5-2025-08-07
```

### Step 3: Test in UI

1. Navigate to the moderation scenarios page
2. Select a scenario and choose moderation strategies
3. Click "Generate Moderated Response"
4. Check the backend console/logs for the validation messages above

---

## 🎯 What to Look For

### ✅ Success Indicators

1. **Validation script passes** all checks
2. **Backend logs show** `gpt-5-2025-08-07` in all three log lines
3. **OpenAI response confirms** the model used is `gpt-5-2025-08-07`
4. **No errors** in the console or backend logs

### ❌ Potential Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Validation script fails | Code not updated correctly | Re-run the update scripts |
| Logs show `gpt-4o-mini` | Server not restarted | Restart backend server |
| OpenAI error "model not found" | API key doesn't have GPT-5 access | Contact OpenAI support or use gpt-4o |
| No logs appear | Logging not configured | Check log level settings |

---

## 📊 Request/Response Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ Frontend (moderation-scenario/+page.svelte)                         │
│   ↓ User clicks "Generate Moderated Response"                      │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│ API Client (lib/apis/moderation/index.ts)                           │
│   model: 'gpt-5-2025-08-07' ✅                                      │
│   ↓ POST /api/moderation/apply                                     │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Router (routers/moderation.py)                                      │
│   🤖 LOG: "Moderation request using model: gpt-5-2025-08-07"       │
│   ↓ Calls multi_moderations_openai()                               │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Utility (utils/moderation.py)                                       │
│   🔍 LOG: "Calling OpenAI API with model: gpt-5-2025-08-07"        │
│   ↓ OpenAI API Call                                                │
└─────────────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│ OpenAI API                                                           │
│   model: gpt-5-2025-08-07                                           │
│   ↑ Returns response with model confirmation                        │
└─────────────────────────────────────────────────────────────────────┘
                               ↑
┌─────────────────────────────────────────────────────────────────────┐
│ Utility (utils/moderation.py)                                       │
│   ✅ LOG: "OpenAI API response received. Model used: gpt-5-..."    │
│   ↑ Returns to router                                              │
└─────────────────────────────────────────────────────────────────────┘
                               ↑
┌─────────────────────────────────────────────────────────────────────┐
│ Frontend                                                             │
│   ← Displays moderated response                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Troubleshooting

### Issue: "Invalid model" error from OpenAI

**Cause:** Your OpenAI API key might not have access to GPT-5 yet.

**Solutions:**
1. Verify GPT-5 access with OpenAI
2. Use a different model (e.g., `gpt-4o-2024-11-20`)
3. Update all three locations with the alternative model

### Issue: Logs don't show model information

**Cause:** Backend not restarted or logging level too high.

**Solutions:**
1. Restart the backend server
2. Check logging configuration in `backend/open_webui/config.py`
3. Set log level to INFO or DEBUG

### Issue: Frontend still shows old model

**Cause:** Browser cache or dev server not restarted.

**Solutions:**
1. Hard refresh browser (Ctrl+Shift+R / Cmd+Shift+R)
2. Clear browser cache
3. Restart frontend dev server

---

## 📝 Additional Notes

- **Model Availability:** GPT-5 access may be limited. Verify your OpenAI account has access.
- **Cost:** GPT-5 may have different pricing than GPT-4. Monitor your usage.
- **Performance:** GPT-5 should provide improved reasoning and response quality.
- **Backwards Compatibility:** If GPT-5 is unavailable, you can fall back to `gpt-4o-mini` by updating all three files.

---

## 🎉 Summary

Your system is now configured to use GPT-5 (gpt-5-2025-08-07) for all moderation operations, including:

- ✅ Initial response generation
- ✅ Response refactoring
- ✅ Follow-up prompt generation
- ✅ Age-based tailoring
- ✅ All custom moderation strategies

The validation script and logging will help you verify that GPT-5 is being used correctly at runtime.

