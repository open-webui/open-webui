"""AI analysis of uploaded files for the knowledge base.

``analyze_file`` decides whether an extracted file's content is worth embedding
and produces a short description of what the file is about. ``describe_folder``
folds those per-file descriptions into a single folder-level summary.

Both run as internal task-model calls (mirroring the title/tags task helpers)
and are designed to run inside the sequential file-processing worker, so at most
one LLM call happens at a time regardless of how many files were uploaded.

Design notes:
  * Fail-open — an LLM/config/parse failure returns "eligible" so that a
    classifier outage never silently drops uploads.
  * Content is truncated before being sent to the model (cost/latency).
  * The per-file description is persisted to ``file.data['description']`` so the
    folder rollup can read it without re-reading file contents.
"""

import json
import logging

from open_webui.models.files import Files
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.task import get_task_model_id
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Truncation cap for the content handed to the classifier. Keeps a 200-page PDF
# from turning a cheap gate into an expensive, slow call.
MAX_CONTENT_CHARS = 8000

_FILE_ANALYSIS_PROMPT = """You are classifying a document for a knowledge base.

Given the file content below, respond with ONLY a JSON object, no prose:
{{"eligible": <true|false>, "description": "<summary>"}}

- "eligible": false only if the content is empty, corrupted, binary junk, or has
  no meaningful text worth retrieving; true otherwise.
- "description": {length_hint}, written in Ukrainian, summarizing what this file is
  about (key topics/purpose).

Content:
\"\"\"
{content}
\"\"\"
"""


def _description_length_hint(content_length: int) -> str:
    """Longer summaries for larger files."""
    if content_length < 2000:
        return 'one concise sentence (max 20 words)'
    if content_length < 6000:
        return 'two or three sentences (max 50 words)'
    return 'a short paragraph of 3-4 sentences (max 90 words)'

_FOLDER_SUMMARY_PROMPT = """You describe the contents of a folder in a knowledge base.

Given the short descriptions of the files it contains, respond with ONLY a
single sentence (max 30 words), written in Ukrainian, summarizing what the folder
is about.

File descriptions:
{descriptions}
"""


def _resolve_task_model_id(request) -> str | None:
    """Pick a model for the analysis call in a background (no-request) context.

    Prefers the configured task model, falling back to the first available
    model. Returns None when no model is usable.
    """
    models = request.app.state.MODELS
    base_model_id = request.app.state.config.TASK_MODEL or next(iter(models), None)
    if not base_model_id or base_model_id not in models:
        return None
    return get_task_model_id(
        base_model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )


def _extract_message_content(response) -> str:
    """Pull the assistant text out of a generate_chat_completion response."""
    return response['choices'][0]['message']['content']


def _parse_json_object(raw: str) -> dict:
    """Parse a JSON object out of a model response, tolerating code fences."""
    cleaned = raw.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    return json.loads(cleaned)


async def analyze_file(
    request,
    file_id: str,
    user,
    content: str | None = None,
    db: AsyncSession | None = None,
) -> tuple[bool, str]:
    """Return ``(eligible, description)`` for a file's extracted content.

    ``content`` may be passed by the caller (e.g. ``process_file`` already has
    the extracted text) to avoid a reload. Fails open — on any error the file is
    treated as eligible with an empty description.
    """
    file = await Files.get_file_by_id(file_id, db=db)
    if file is None:
        return False, ''

    if content is None:
        content = (file.data or {}).get('content') or ''
    content = content.strip()
    if not content:
        # Nothing was extracted — not an LLM decision, just not embeddable.
        return False, ''

    model_id = _resolve_task_model_id(request)
    if not model_id:
        log.warning('analyze_file: no usable task model; failing open')
        return True, ''

    payload = {
        'model': model_id,
        'messages': [
            {
                'role': 'user',
                'content': _FILE_ANALYSIS_PROMPT.format(
                    content=content[:MAX_CONTENT_CHARS],
                    length_hint=_description_length_hint(len(content)),
                ),
            }
        ],
        'stream': False,
        'metadata': {'task': 'file_ingestion_analysis'},
    }

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user)
        parsed = _parse_json_object(_extract_message_content(response))
        eligible = bool(parsed.get('eligible', True))
        description = str(parsed.get('description', '')).strip()
    except Exception as e:
        log.warning(f'analyze_file: analysis failed for {file_id}, failing open: {e}')
        return True, ''

    # Persist the description so folder-level rollups can read it later.
    await Files.update_file_data_by_id(file_id, {'description': description}, db=db)
    return eligible, description


async def describe_folder(
    request,
    file_ids: list[str],
    user,
    db: AsyncSession | None = None,
) -> str:
    """Summarize a folder from its files' stored descriptions.

    Reads the per-file descriptions produced by ``analyze_file`` (not the raw
    file contents) and folds them into a single sentence. Returns an empty
    string if there is nothing to summarize or the call fails.
    """
    files = await Files.get_files_by_ids(file_ids, db=db)
    descriptions = [(f.data or {}).get('description', '').strip() for f in files]
    descriptions = [d for d in descriptions if d]
    if not descriptions:
        return ''

    model_id = _resolve_task_model_id(request)
    if not model_id:
        log.warning('describe_folder: no usable task model')
        return ''

    joined = '\n'.join(f'- {d}' for d in descriptions)
    payload = {
        'model': model_id,
        'messages': [{'role': 'user', 'content': _FOLDER_SUMMARY_PROMPT.format(descriptions=joined)}],
        'stream': False,
        'metadata': {'task': 'folder_summary'},
    }

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user)
        return _extract_message_content(response).strip()
    except Exception as e:
        log.warning(f'describe_folder: summary failed, returning empty: {e}')
        return ''
