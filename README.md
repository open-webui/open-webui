# Fix: Responses API connections never send the model's reasoning back

**Repo:** [open-webui/open-webui](https://github.com/open-webui/open-webui) — 158,930 stars (verified via the GitHub API, Nov 17, 2026), MIT-style source-available project (Open WebUI License), last commit Nov 17, 2026.
**Issue:** [open-webui/open-webui#33956](https://github.com/open-webui/open-webui/issues/33956) — "Responses API connections never send the model's reasoning back, although the docs say they do" (open, label `bug`, filed Nov 8, 2026). No PR exists for it; one commenter (Nov 9) verified the root cause and offered to PR, but has not opened one.

**Note on the repo's license:** Open WebUI is source-available under the Open WebUI License (BSD-3-Clause plus a branding clause), not an OSI-approved open-source license. It is the most-starred LLM-platform repo and accepts external contributions. Flagging this so you can judge the EB1A framing; the contribution itself (a public, merged PR to a 159k-star project) is the same either way.

## What was wrong

On a connection set to the Responses API with a reasoning model, the reasoning
items the model returns (with their id and encrypted reasoning) are saved with
the reply but never sent back to the provider — not in the follow-up after a
tool result in the same reply, and not on later messages. The docs page for
reasoning models says "Stored reasoning items sent back" for this connection
type. Two root causes, both verified by reproducing them locally:

1. `backend/open_webui/utils/misc.py` — `convert_output_to_messages()` drops
   `type: 'reasoning'` items when `reasoning_format` is `None` (the default
   for OpenAI models; `get_reasoning_format()` only returns a format for
   Ollama / llama.cpp). The history rebuilt for a follow-up therefore has no
   reasoning in it at all.
2. `backend/open_webui/routers/openai.py` — `convert_to_responses_payload()`
   never replays reasoning into the Responses `input`, and
   `RESPONSES_ALLOWED_FIELDS['reasoning']` only permits `encrypted_content`,
   dropping Azure OpenAI's preview field `encrypted_reasoning`.

## What the fix does

- `backend/open_webui/utils/misc.py` — when `raw=True`,
  `convert_output_to_messages()` keeps raw reasoning items as
  `reasoning_items` on the flushed assistant message (existing
  `thinking` / `reasoning_content` / `reasoning_details` behaviour is
  unchanged; `raw=False` still drops reasoning, as before).
- `backend/open_webui/routers/openai.py` — `convert_to_responses_payload()`
  prepends the normalised reasoning items into `input` immediately before
  the `function_call` or assistant `message` they relate to (the order the
  Responses API requires); a turn that only carried reasoning emits no empty
  message. `RESPONSES_ALLOWED_FIELDS['reasoning']` now also permits
  `encrypted_reasoning`. New helper `_strip_reasoning_items()` removes the
  Responses-only key from Chat Completions payloads in
  `generate_chat_completion()`, so it never leaks to providers that reject
  unknown fields.
- `backend/open_webui/utils/middleware.py` — `strip_reasoning_details()`
  now also drops `type: 'reasoning'` items. It is only called when the
  assistant message's model differs from the current model, and encrypted
  reasoning is bound to the model that produced it — replaying it to a
  different model gets a 400 from the provider.

## Test outcome (honest)

12 tests in `test_reasoning_replay_33956.py`: **12 passed** against the
patched code. The same suite against the **unpatched** code: **9 failed,
3 passed** — the 3 passing are behaviour-preservation checks (reasoning still
dropped when `raw=False`, `reasoning_details` still attached, stored-`output`
replay which already worked). So the tests catch the bug and the fix resolves
it. The end-to-end test replays a stored tool-call turn (reasoning + text +
function call + tool result) through message reconstruction into a Responses
payload and asserts the reasoning item lands in `input` before the
`function_call`, with the follow-up user message last.

How it was run (no live server, no API key, no network calls to a provider):
the published `open-webui==0.13.3` package was installed in a venv, the three
patched `main` files were overlaid (plus `main`'s `utils/tether.py`, which
`main`'s `routers/openai.py` imports), and the suite was run with
`WEBUI_SECRET_KEY=<test value>` and `FRONTEND_BUILD_DIR=<venv>/.../open_webui`.
The three patched functions are identical between `main` and 0.13.3 except one
unrelated line in `misc.py` (message `content` is `None` vs `''` when a
tool-call turn has no text), so the results transfer to `main`. The
`middleware.py` test ran against the same patch text applied to the 0.13.3
file, because `main`'s `middleware.py` imports newer helpers that don't exist
in 0.13.3. Ruff format (repo config) and the CI pyflakes check
(`ruff check --select=F`) pass on all three patched files.

What was NOT verified live: no real Responses API call was made (that needs an
OpenAI key and a reasoning model), and the fix was not run inside the full app
— the PR should be checked against a real reasoning-model conversation with a
tool call before merging.

## Local test steps (for Bhavana)

These are the exact steps that produced the 12/12 result above (the repo has
no backend pytest suite — CI only runs Ruff — so the tests run against the
installed package with the patched files overlaid):

```bash
python -m venv .venv && source .venv/bin/activate
export TMPDIR=$PWD/tmp-pip        # /tmp is small on some machines; use a
                                  # directory with room if the install fails
pip install --no-cache-dir --no-deps open-webui==0.13.3 pytest
# install the import-time deps the backend modules need (iterate on
# ModuleNotFoundError if one is missing):
pip install --no-cache-dir typer uvicorn fastapi aiohttp aiocache aiofiles \
  "pydantic==2.13.4" "sqlalchemy[asyncio]==2.0.50" markdown redis \
  beautifulsoup4 requests cryptography authlib loguru tiktoken openai \
  anthropic chromadb langchain-core langchain-text-splitters langchain-classic \
  bcrypt argon2-cffi pyotp pydub soundfile boto3 azure-identity \
  azure-storage-blob azure-ai-documentintelligence google-cloud-storage \
  asgiref aiodns hiredis einops docx2txt pypandoc opensearch-py
# overlay the patched files from this folder's fix.patch onto the install
# (in a checkout of open-webui with the patch applied; SITE points at the
# scratch venv created above):
SITE=<scratch dir>/.venv/lib/python3.12/site-packages/open_webui
cp backend/open_webui/utils/misc.py       $SITE/utils/misc.py
cp backend/open_webui/routers/openai.py   $SITE/routers/openai.py
cp backend/open_webui/utils/tether.py     $SITE/utils/tether.py
# (middleware.py from main imports newer helpers, so for the test run use the
#  0.13.3 middleware.py with the same strip_reasoning_details change applied;
#  the function is identical between main and 0.13.3)
WEBUI_SECRET_KEY=<a long random value> \
FRONTEND_BUILD_DIR=$SITE \
python -m pytest test_reasoning_replay_33956.py -v
```

To see the tests catch the bug, restore the three pristine files from the
installed 0.13.3 package and re-run: expect 9 failed, 3 passed.

## PR rules

- Reference the open issue: fix for #33956 — do NOT open a new issue.
- Target the `dev` branch (the repo's contribution flow; `main` is the
  release branch).
- The PR description should carry the before/after evidence: the new tests
  fail 9/12 on unpatched code and pass 12/12 patched.
- Do not claim a live end-to-end verification — that still needs a real
  reasoning-model run; say so in the PR.
- Nothing here touches ADP work; this is a personal open-source contribution.
