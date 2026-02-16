"""
Built-in tools for Open WebUI.

These tools are automatically available when native function calling is enabled.

IMPORTANT: DO NOT IMPORT THIS MODULE DIRECTLY IN OTHER PARTS OF THE CODEBASE.
"""

import json
import logging
import time
import asyncio
from typing import Optional

from fastapi import Request

from open_webui.models.users import UserModel
from open_webui.routers.retrieval import search_web as _search_web
from open_webui.retrieval.utils import get_content_from_url
from open_webui.routers.images import (
    image_generations,
    image_edits,
    CreateImageForm,
    EditImageForm,
)
from open_webui.routers.memories import (
    query_memory,
    add_memory as _add_memory,
    update_memory_by_id,
    QueryMemoryForm,
    AddMemoryForm,
    MemoryUpdateModel,
)
from open_webui.models.notes import Notes
from open_webui.models.chats import Chats
from open_webui.models.channels import Channels, ChannelMember, Channel
from open_webui.models.messages import Messages, Message
from open_webui.models.groups import Groups
from open_webui.utils.sanitize import sanitize_code

log = logging.getLogger(__name__)

MAX_KNOWLEDGE_BASE_SEARCH_ITEMS = 10_000

# =============================================================================
# TIME UTILITIES
# =============================================================================


async def get_current_timestamp(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the current Unix timestamp in seconds.

    :return: JSON with current_timestamp (seconds) and current_iso (ISO format)
    """
    try:
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        return json.dumps(
            {
                "current_timestamp": int(now.timestamp()),
                "current_iso": now.isoformat(),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"get_current_timestamp error: {e}")
        return json.dumps({"error": str(e)})


async def calculate_timestamp(
    days_ago: int = 0,
    weeks_ago: int = 0,
    months_ago: int = 0,
    years_ago: int = 0,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the current Unix timestamp, optionally adjusted by days, weeks, months, or years.
    Use this to calculate timestamps for date filtering in search functions.
    Examples: "last week" = weeks_ago=1, "3 days ago" = days_ago=3, "a year ago" = years_ago=1

    :param days_ago: Number of days to subtract from current time (default: 0)
    :param weeks_ago: Number of weeks to subtract from current time (default: 0)
    :param months_ago: Number of months to subtract from current time (default: 0)
    :param years_ago: Number of years to subtract from current time (default: 0)
    :return: JSON with current_timestamp and calculated_timestamp (both in seconds)
    """
    try:
        import datetime
        from dateutil.relativedelta import relativedelta

        now = datetime.datetime.now(datetime.timezone.utc)
        current_ts = int(now.timestamp())

        # Calculate the adjusted time
        total_days = days_ago + (weeks_ago * 7)
        adjusted = now - datetime.timedelta(days=total_days)

        # Handle months and years separately (variable length)
        if months_ago > 0 or years_ago > 0:
            adjusted = adjusted - relativedelta(months=months_ago, years=years_ago)

        adjusted_ts = int(adjusted.timestamp())

        return json.dumps(
            {
                "current_timestamp": current_ts,
                "current_iso": now.isoformat(),
                "calculated_timestamp": adjusted_ts,
                "calculated_iso": adjusted.isoformat(),
            },
            ensure_ascii=False,
        )
    except ImportError:
        # Fallback without dateutil
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        current_ts = int(now.timestamp())
        total_days = days_ago + (weeks_ago * 7) + (months_ago * 30) + (years_ago * 365)
        adjusted = now - datetime.timedelta(days=total_days)
        adjusted_ts = int(adjusted.timestamp())
        return json.dumps(
            {
                "current_timestamp": current_ts,
                "current_iso": now.isoformat(),
                "calculated_timestamp": adjusted_ts,
                "calculated_iso": adjusted.isoformat(),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"calculate_timestamp error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# WEB SEARCH TOOLS
# =============================================================================


async def search_web(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the public web for information. Best for current events, external references,
    or topics not covered in internal documents. If knowledge base tools are available,
    consider checking those first for internal information.

    :param query: The search query to look up
    :param count: Number of results to return (default: 5)
    :return: JSON with search results containing title, link, and snippet for each result
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        engine = __request__.app.state.config.WEB_SEARCH_ENGINE
        user = UserModel(**__user__) if __user__ else None

        # Use admin-configured result count if configured, falling back to model-provided count of provided, else default to 5
        count = __request__.app.state.config.WEB_SEARCH_RESULT_COUNT or count

        results = await asyncio.to_thread(_search_web, __request__, engine, query, user)

        # Limit results
        results = results[:count] if results else []

        return json.dumps(
            [{"title": r.title, "link": r.link, "snippet": r.snippet} for r in results],
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"search_web error: {e}")
        return json.dumps({"error": str(e)})


async def fetch_url(
    url: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Fetch and extract the main text content from a web page URL.

    :param url: The URL to fetch content from
    :return: The extracted text content from the page
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        content, _ = await asyncio.to_thread(get_content_from_url, __request__, url)

        # Truncate if too long (avoid overwhelming context)
        max_length = 50000
        if len(content) > max_length:
            content = content[:max_length] + "\n\n[Content truncated...]"

        return content
    except Exception as e:
        log.exception(f"fetch_url error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# IMAGE GENERATION TOOLS
# =============================================================================


async def generate_image(
    prompt: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Generate an image based on a text prompt.

    :param prompt: A detailed description of the image to generate
    :return: Confirmation that the image was generated, or an error message
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_generations(
            request=__request__,
            form_data=CreateImageForm(prompt=prompt),
            user=user,
        )

        # Prepare file entries for the images
        image_files = [{"type": "image", "url": img["url"]} for img in images]

        # Persist files to DB if chat context is available
        if __chat_id__ and __message_id__ and images:
            image_files = Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    "type": "chat:message:files",
                    "data": {
                        "files": image_files,
                    },
                }
            )
            # Return a message indicating the image is already displayed
            return json.dumps(
                {
                    "status": "success",
                    "message": "The image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.",
                    "images": images,
                },
                ensure_ascii=False,
            )

        return json.dumps({"status": "success", "images": images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f"generate_image error: {e}")
        return json.dumps({"error": str(e)})


async def edit_image(
    prompt: str,
    image_urls: list[str],
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Edit existing images based on a text prompt.

    :param prompt: A description of the changes to make to the images
    :param image_urls: A list of URLs of the images to edit
    :return: Confirmation that the images were edited, or an error message
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_edits(
            request=__request__,
            form_data=EditImageForm(prompt=prompt, image=image_urls),
            user=user,
        )

        # Prepare file entries for the images
        image_files = [{"type": "image", "url": img["url"]} for img in images]

        # Persist files to DB if chat context is available
        if __chat_id__ and __message_id__ and images:
            image_files = Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    "type": "chat:message:files",
                    "data": {
                        "files": image_files,
                    },
                }
            )
            # Return a message indicating the image is already displayed
            return json.dumps(
                {
                    "status": "success",
                    "message": "The edited image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.",
                    "images": images,
                },
                ensure_ascii=False,
            )

        return json.dumps({"status": "success", "images": images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f"edit_image error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# CODE INTERPRETER TOOLS
# =============================================================================


async def execute_code(
    code: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __event_call__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
    __metadata__: dict = None,
) -> str:
    """
    Execute Python code in a sandboxed environment and return the output.
    Use this to perform calculations, data analysis, generate visualizations,
    or run any Python code that would help answer the user's question.

    :param code: The Python code to execute
    :return: JSON with stdout, stderr, and result from execution
    """
    from uuid import uuid4

    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        # Sanitize code (strips ANSI codes and markdown fences)
        code = sanitize_code(code)

        # Import blocked modules from config (same as middleware)
        from open_webui.config import CODE_INTERPRETER_BLOCKED_MODULES

        # Add import blocking code if there are blocked modules
        if CODE_INTERPRETER_BLOCKED_MODULES:
            import textwrap

            blocking_code = textwrap.dedent(f"""
                import builtins

                BLOCKED_MODULES = {CODE_INTERPRETER_BLOCKED_MODULES}

                _real_import = builtins.__import__
                def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
                    if name.split('.')[0] in BLOCKED_MODULES:
                        importer_name = globals.get('__name__') if globals else None
                        if importer_name == '__main__':
                            raise ImportError(
                                f"Direct import of module {{name}} is restricted."
                            )
                    return _real_import(name, globals, locals, fromlist, level)

                builtins.__import__ = restricted_import
                """)
            code = blocking_code + "\n" + code

        engine = getattr(
            __request__.app.state.config, "CODE_INTERPRETER_ENGINE", "pyodide"
        )
        if engine == "pyodide":
            # Execute via frontend pyodide using bidirectional event call
            if __event_call__ is None:
                return json.dumps(
                    {
                        "error": "Event call not available. WebSocket connection required for pyodide execution."
                    }
                )

            output = await __event_call__(
                {
                    "type": "execute:python",
                    "data": {
                        "id": str(uuid4()),
                        "code": code,
                        "session_id": (
                            __metadata__.get("session_id") if __metadata__ else None
                        ),
                    },
                }
            )

            # Parse the output - pyodide returns dict with stdout, stderr, result
            if isinstance(output, dict):
                stdout = output.get("stdout", "")
                stderr = output.get("stderr", "")
                result = output.get("result", "")
            else:
                stdout = ""
                stderr = ""
                result = str(output) if output else ""

        elif engine == "jupyter":
            from open_webui.utils.code_interpreter import execute_code_jupyter

            output = await execute_code_jupyter(
                __request__.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
                code,
                (
                    __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
                    if __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH
                    == "token"
                    else None
                ),
                (
                    __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
                    if __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH
                    == "password"
                    else None
                ),
                __request__.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
            )

            stdout = output.get("stdout", "")
            stderr = output.get("stderr", "")
            result = output.get("result", "")

        else:
            return json.dumps({"error": f"Unknown code interpreter engine: {engine}"})

        # Handle image outputs (base64 encoded) - replace with uploaded URLs
        # Get actual user object for image upload (upload_image requires user.id attribute)
        if __user__ and __user__.get("id"):
            from open_webui.models.users import Users
            from open_webui.utils.files import get_image_url_from_base64

            user = Users.get_user_by_id(__user__["id"])

            # Extract and upload images from stdout
            if stdout and isinstance(stdout, str):
                stdout_lines = stdout.split("\n")
                for idx, line in enumerate(stdout_lines):
                    if "data:image/png;base64" in line:
                        image_url = get_image_url_from_base64(
                            __request__,
                            line,
                            __metadata__ or {},
                            user,
                        )
                        if image_url:
                            stdout_lines[idx] = f"![Output Image]({image_url})"
                stdout = "\n".join(stdout_lines)

            # Extract and upload images from result
            if result and isinstance(result, str):
                result_lines = result.split("\n")
                for idx, line in enumerate(result_lines):
                    if "data:image/png;base64" in line:
                        image_url = get_image_url_from_base64(
                            __request__,
                            line,
                            __metadata__ or {},
                            user,
                        )
                        if image_url:
                            result_lines[idx] = f"![Output Image]({image_url})"
                result = "\n".join(result_lines)

        response = {
            "status": "success",
            "stdout": stdout,
            "stderr": stderr,
            "result": result,
        }

        return json.dumps(response, ensure_ascii=False)
    except Exception as e:
        log.exception(f"execute_code error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# MEMORY TOOLS
# =============================================================================


async def search_memories(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's stored memories for relevant information.

    :param query: The search query to find relevant memories
    :param count: Number of memories to return (default 5)
    :return: JSON with matching memories and their dates
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        user = UserModel(**__user__) if __user__ else None

        results = await query_memory(
            __request__,
            QueryMemoryForm(content=query, k=count),
            user,
        )

        if results and hasattr(results, "documents") and results.documents:
            memories = []
            for doc_idx, doc in enumerate(results.documents[0]):
                memory_id = None
                if results.ids and results.ids[0]:
                    memory_id = results.ids[0][doc_idx]
                created_at = "Unknown"
                if results.metadatas and results.metadatas[0][doc_idx].get(
                    "created_at"
                ):
                    created_at = time.strftime(
                        "%Y-%m-%d",
                        time.localtime(results.metadatas[0][doc_idx]["created_at"]),
                    )
                memories.append({"id": memory_id, "date": created_at, "content": doc})
            return json.dumps(memories, ensure_ascii=False)
        else:
            return json.dumps([])
    except Exception as e:
        log.exception(f"search_memories error: {e}")
        return json.dumps({"error": str(e)})


async def add_memory(
    content: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Store a new memory for the user.

    :param content: The memory content to store
    :return: Confirmation that the memory was stored
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await _add_memory(
            __request__,
            AddMemoryForm(content=content),
            user,
        )

        return json.dumps({"status": "success", "id": memory.id}, ensure_ascii=False)
    except Exception as e:
        log.exception(f"add_memory error: {e}")
        return json.dumps({"error": str(e)})


async def replace_memory_content(
    memory_id: str,
    content: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update the content of an existing memory by its ID.

    :param memory_id: The ID of the memory to update
    :param content: The new content for the memory
    :return: Confirmation that the memory was updated
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await update_memory_by_id(
            memory_id=memory_id,
            request=__request__,
            form_data=MemoryUpdateModel(content=content),
            user=user,
        )

        return json.dumps(
            {"status": "success", "id": memory.id, "content": memory.content},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"replace_memory_content error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# NOTES TOOLS
# =============================================================================


async def search_notes(
    query: str,
    count: int = 5,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's notes by title and content.

    :param query: The search query to find matching notes
    :param count: Maximum number of results to return (default: 5)
    :param start_timestamp: Only include notes updated after this Unix timestamp (seconds)
    :param end_timestamp: Only include notes updated before this Unix timestamp (seconds)
    :return: JSON with matching notes containing id, title, and content snippet
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        user_id = __user__.get("id")
        user_group_ids = [group.id for group in Groups.get_groups_by_member_id(user_id)]

        result = Notes.search_notes(
            user_id=user_id,
            filter={
                "query": query,
                "user_id": user_id,
                "group_ids": user_group_ids,
                "permission": "read",
            },
            skip=0,
            limit=count * 3,  # Fetch more for filtering
        )

        # Convert timestamps to nanoseconds for comparison
        start_ts = start_timestamp * 1_000_000_000 if start_timestamp else None
        end_ts = end_timestamp * 1_000_000_000 if end_timestamp else None

        notes = []
        for note in result.items:
            # Apply date filters (updated_at is in nanoseconds)
            if start_ts and note.updated_at < start_ts:
                continue
            if end_ts and note.updated_at > end_ts:
                continue

            # Extract a snippet from the markdown content
            content_snippet = ""
            if note.data and note.data.get("content", {}).get("md"):
                md_content = note.data["content"]["md"]
                lower_content = md_content.lower()
                lower_query = query.lower()
                idx = lower_content.find(lower_query)
                if idx != -1:
                    start = max(0, idx - 50)
                    end = min(len(md_content), idx + len(query) + 100)
                    content_snippet = (
                        ("..." if start > 0 else "")
                        + md_content[start:end]
                        + ("..." if end < len(md_content) else "")
                    )
                else:
                    content_snippet = md_content[:150] + (
                        "..." if len(md_content) > 150 else ""
                    )

            notes.append(
                {
                    "id": note.id,
                    "title": note.title,
                    "snippet": content_snippet,
                    "updated_at": note.updated_at,
                }
            )

            if len(notes) >= count:
                break

        return json.dumps(notes, ensure_ascii=False)
    except Exception as e:
        log.exception(f"search_notes error: {e}")
        return json.dumps({"error": str(e)})


async def view_note(
    note_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the full content of a note by its ID.

    :param note_id: The ID of the note to retrieve
    :return: JSON with the note's id, title, and full markdown content
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        note = Notes.get_note_by_id(note_id)

        if not note:
            return json.dumps({"error": "Note not found"})

        # Check access permission
        user_id = __user__.get("id")
        user_group_ids = [group.id for group in Groups.get_groups_by_member_id(user_id)]

        from open_webui.models.access_grants import AccessGrants

        if note.user_id != user_id and not AccessGrants.has_access(
            user_id=user_id,
            resource_type="note",
            resource_id=note.id,
            permission="read",
            user_group_ids=set(user_group_ids),
        ):
            return json.dumps({"error": "Access denied"})

        # Extract markdown content
        content = ""
        if note.data and note.data.get("content", {}).get("md"):
            content = note.data["content"]["md"]

        return json.dumps(
            {
                "id": note.id,
                "title": note.title,
                "content": content,
                "updated_at": note.updated_at,
                "created_at": note.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"view_note error: {e}")
        return json.dumps({"error": str(e)})


async def write_note(
    title: str,
    content: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a new note with the given title and content.

    :param title: The title of the new note
    :param content: The markdown content for the note
    :return: JSON with success status and new note id
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        from open_webui.models.notes import NoteForm

        user_id = __user__.get("id")

        form = NoteForm(
            title=title,
            data={"content": {"md": content}},
            access_grants=[],  # Private by default - only owner can access
        )

        new_note = Notes.insert_new_note(user_id, form)

        if not new_note:
            return json.dumps({"error": "Failed to create note"})

        return json.dumps(
            {
                "status": "success",
                "id": new_note.id,
                "title": new_note.title,
                "created_at": new_note.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"write_note error: {e}")
        return json.dumps({"error": str(e)})


async def replace_note_content(
    note_id: str,
    content: str,
    title: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update the content of a note. Use this to modify task lists, add notes, or update content.

    :param note_id: The ID of the note to update
    :param content: The new markdown content for the note
    :param title: Optional new title for the note
    :return: JSON with success status and updated note info
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        from open_webui.models.notes import NoteUpdateForm

        note = Notes.get_note_by_id(note_id)

        if not note:
            return json.dumps({"error": "Note not found"})

        # Check write permission
        user_id = __user__.get("id")
        user_group_ids = [group.id for group in Groups.get_groups_by_member_id(user_id)]

        from open_webui.models.access_grants import AccessGrants

        if note.user_id != user_id and not AccessGrants.has_access(
            user_id=user_id,
            resource_type="note",
            resource_id=note.id,
            permission="write",
            user_group_ids=set(user_group_ids),
        ):
            return json.dumps({"error": "Write access denied"})

        # Build update form
        update_data = {"data": {"content": {"md": content}}}
        if title:
            update_data["title"] = title

        form = NoteUpdateForm(**update_data)
        updated_note = Notes.update_note_by_id(note_id, form)

        if not updated_note:
            return json.dumps({"error": "Failed to update note"})

        return json.dumps(
            {
                "status": "success",
                "id": updated_note.id,
                "title": updated_note.title,
                "updated_at": updated_note.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"replace_note_content error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# CHATS TOOLS
# =============================================================================


async def search_chats(
    query: str,
    count: int = 5,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
    __chat_id__: str = None,
) -> str:
    """
    Search the user's previous chat conversations by title and message content.

    :param query: The search query to find matching chats
    :param count: Maximum number of results to return (default: 5)
    :param start_timestamp: Only include chats updated after this Unix timestamp (seconds)
    :param end_timestamp: Only include chats updated before this Unix timestamp (seconds)
    :return: JSON with matching chats containing id, title, updated_at, and content snippet
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        user_id = __user__.get("id")

        chats = Chats.get_chats_by_user_id_and_search_text(
            user_id=user_id,
            search_text=query,
            include_archived=False,
            skip=0,
            limit=count * 3,  # Fetch more for filtering
        )

        results = []
        for chat in chats:
            # Skip the current chat to avoid showing it in search results
            if __chat_id__ and chat.id == __chat_id__:
                continue

            # Apply date filters (updated_at is in seconds)
            if start_timestamp and chat.updated_at < start_timestamp:
                continue
            if end_timestamp and chat.updated_at > end_timestamp:
                continue

            # Find a matching message snippet
            snippet = ""
            messages = chat.chat.get("history", {}).get("messages", {})
            lower_query = query.lower()

            for msg_id, msg in messages.items():
                content = msg.get("content", "")
                if isinstance(content, str) and lower_query in content.lower():
                    idx = content.lower().find(lower_query)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 100)
                    snippet = (
                        ("..." if start > 0 else "")
                        + content[start:end]
                        + ("..." if end < len(content) else "")
                    )
                    break

            if not snippet and lower_query in chat.title.lower():
                snippet = f"Title match: {chat.title}"

            results.append(
                {
                    "id": chat.id,
                    "title": chat.title,
                    "snippet": snippet,
                    "updated_at": chat.updated_at,
                }
            )

            if len(results) >= count:
                break

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f"search_chats error: {e}")
        return json.dumps({"error": str(e)})


async def view_chat(
    chat_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the full conversation history of a chat by its ID.

    :param chat_id: The ID of the chat to retrieve
    :return: JSON with the chat's id, title, and messages
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        user_id = __user__.get("id")

        chat = Chats.get_chat_by_id_and_user_id(chat_id, user_id)

        if not chat:
            return json.dumps({"error": "Chat not found or access denied"})

        # Extract messages from history
        messages = []
        history = chat.chat.get("history", {})
        msg_dict = history.get("messages", {})

        # Build message chain from currentId
        current_id = history.get("currentId")
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            msg = msg_dict.get(current_id)
            if msg:
                messages.append(
                    {
                        "role": msg.get("role", ""),
                        "content": msg.get("content", ""),
                    }
                )
            current_id = msg.get("parentId") if msg else None

        # Reverse to get chronological order
        messages.reverse()

        return json.dumps(
            {
                "id": chat.id,
                "title": chat.title,
                "messages": messages,
                "updated_at": chat.updated_at,
                "created_at": chat.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"view_chat error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# CHANNELS TOOLS
# =============================================================================


async def search_channels(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search for channels by name and description that the user has access to.

    :param query: The search query to find matching channels
    :param count: Maximum number of results to return (default: 5)
    :return: JSON with matching channels containing id, name, description, and type
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        user_id = __user__.get("id")

        # Get all channels the user has access to
        all_channels = Channels.get_channels_by_user_id(user_id)

        # Filter by query
        lower_query = query.lower()
        matching_channels = []

        for channel in all_channels:
            name_match = lower_query in channel.name.lower() if channel.name else False
            desc_match = lower_query in (channel.description or "").lower()

            if name_match or desc_match:
                matching_channels.append(
                    {
                        "id": channel.id,
                        "name": channel.name,
                        "description": channel.description or "",
                        "type": channel.type or "public",
                    }
                )

            if len(matching_channels) >= count:
                break

        return json.dumps(matching_channels, ensure_ascii=False)
    except Exception as e:
        log.exception(f"search_channels error: {e}")
        return json.dumps({"error": str(e)})


async def search_channel_messages(
    query: str,
    count: int = 10,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search for messages in channels the user is a member of, including thread replies.

    :param query: The search query to find matching messages
    :param count: Maximum number of results to return (default: 10)
    :param start_timestamp: Only include messages created after this Unix timestamp (seconds)
    :param end_timestamp: Only include messages created before this Unix timestamp (seconds)
    :return: JSON with matching messages containing channel info, message content, and thread context
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        user_id = __user__.get("id")

        # Get all channels the user has access to
        user_channels = Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]
        channel_map = {c.id: c for c in user_channels}

        if not channel_ids:
            return json.dumps([])

        # Convert timestamps to nanoseconds (Message.created_at is in nanoseconds)
        start_ts = start_timestamp * 1_000_000_000 if start_timestamp else None
        end_ts = end_timestamp * 1_000_000_000 if end_timestamp else None

        # Search messages using the model method
        matching_messages = Messages.search_messages_by_channel_ids(
            channel_ids=channel_ids,
            query=query,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            limit=count,
        )

        results = []
        for msg in matching_messages:
            channel = channel_map.get(msg.channel_id)

            # Extract snippet around the match
            content = msg.content or ""
            lower_query = query.lower()
            idx = content.lower().find(lower_query)
            if idx != -1:
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 100)
                snippet = (
                    ("..." if start > 0 else "")
                    + content[start:end]
                    + ("..." if end < len(content) else "")
                )
            else:
                snippet = content[:150] + ("..." if len(content) > 150 else "")

            results.append(
                {
                    "channel_id": msg.channel_id,
                    "channel_name": channel.name if channel else "Unknown",
                    "message_id": msg.id,
                    "content_snippet": snippet,
                    "is_thread_reply": msg.parent_id is not None,
                    "parent_id": msg.parent_id,
                    "created_at": msg.created_at,
                }
            )

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f"search_channel_messages error: {e}")
        return json.dumps({"error": str(e)})


async def view_channel_message(
    message_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the full content of a channel message by its ID, including thread replies.

    :param message_id: The ID of the message to retrieve
    :return: JSON with the message content, channel info, and thread replies if any
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        user_id = __user__.get("id")

        message = Messages.get_message_by_id(message_id)

        if not message:
            return json.dumps({"error": "Message not found"})

        # Verify user has access to the channel
        channel = Channels.get_channel_by_id(message.channel_id)
        if not channel:
            return json.dumps({"error": "Channel not found"})

        # Check if user has access to the channel
        user_channels = Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]

        if message.channel_id not in channel_ids:
            return json.dumps({"error": "Access denied"})

        # Build response with thread information
        result = {
            "id": message.id,
            "channel_id": message.channel_id,
            "channel_name": channel.name,
            "content": message.content,
            "user_id": message.user_id,
            "is_thread_reply": message.parent_id is not None,
            "parent_id": message.parent_id,
            "reply_count": message.reply_count,
            "created_at": message.created_at,
            "updated_at": message.updated_at,
        }

        # Include user info if available
        if message.user:
            result["user_name"] = message.user.name

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f"view_channel_message error: {e}")
        return json.dumps({"error": str(e)})


async def view_channel_thread(
    parent_message_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get all messages in a channel thread, including the parent message and all replies.

    :param parent_message_id: The ID of the parent message that started the thread
    :return: JSON with the parent message and all thread replies in chronological order
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        user_id = __user__.get("id")

        # Get the parent message
        parent_message = Messages.get_message_by_id(parent_message_id)

        if not parent_message:
            return json.dumps({"error": "Message not found"})

        # Verify user has access to the channel
        channel = Channels.get_channel_by_id(parent_message.channel_id)
        if not channel:
            return json.dumps({"error": "Channel not found"})

        user_channels = Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]

        if parent_message.channel_id not in channel_ids:
            return json.dumps({"error": "Access denied"})

        # Get all thread replies
        thread_replies = Messages.get_thread_replies_by_message_id(parent_message_id)

        # Build the response
        messages = []

        # Add parent message first
        messages.append(
            {
                "id": parent_message.id,
                "content": parent_message.content,
                "user_id": parent_message.user_id,
                "user_name": parent_message.user.name if parent_message.user else None,
                "is_parent": True,
                "created_at": parent_message.created_at,
            }
        )

        # Add thread replies (reverse to get chronological order)
        for reply in reversed(thread_replies):
            messages.append(
                {
                    "id": reply.id,
                    "content": reply.content,
                    "user_id": reply.user_id,
                    "user_name": reply.user.name if reply.user else None,
                    "is_parent": False,
                    "reply_to_id": reply.reply_to_id,
                    "created_at": reply.created_at,
                }
            )

        return json.dumps(
            {
                "channel_id": parent_message.channel_id,
                "channel_name": channel.name,
                "thread_id": parent_message_id,
                "message_count": len(messages),
                "messages": messages,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"view_channel_thread error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# KNOWLEDGE BASE TOOLS
# =============================================================================


async def list_knowledge_bases(
    count: int = 10,
    skip: int = 0,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List the user's accessible knowledge bases.

    :param count: Maximum number of KBs to return (default: 10)
    :param skip: Number of results to skip for pagination (default: 0)
    :return: JSON with KBs containing id, name, description, and file_count
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        from open_webui.models.knowledge import Knowledges

        user_id = __user__.get("id")
        user_group_ids = [group.id for group in Groups.get_groups_by_member_id(user_id)]

        result = Knowledges.search_knowledge_bases(
            user_id,
            filter={
                "query": "",
                "user_id": user_id,
                "group_ids": user_group_ids,
            },
            skip=skip,
            limit=count,
        )

        knowledge_bases = []
        for knowledge_base in result.items:
            files = Knowledges.get_files_by_id(knowledge_base.id)
            file_count = len(files) if files else 0

            knowledge_bases.append(
                {
                    "id": knowledge_base.id,
                    "name": knowledge_base.name,
                    "description": knowledge_base.description or "",
                    "file_count": file_count,
                    "updated_at": knowledge_base.updated_at,
                }
            )

        return json.dumps(knowledge_bases, ensure_ascii=False)
    except Exception as e:
        log.exception(f"list_knowledge_bases error: {e}")
        return json.dumps({"error": str(e)})


async def search_knowledge_bases(
    query: str,
    count: int = 5,
    skip: int = 0,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's accessible knowledge bases by name and description.

    :param query: The search query to find matching knowledge bases
    :param count: Maximum number of results to return (default: 5)
    :param skip: Number of results to skip for pagination (default: 0)
    :return: JSON with matching KBs containing id, name, description, and file_count
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        from open_webui.models.knowledge import Knowledges

        user_id = __user__.get("id")
        user_group_ids = [group.id for group in Groups.get_groups_by_member_id(user_id)]

        result = Knowledges.search_knowledge_bases(
            user_id,
            filter={
                "query": query,
                "user_id": user_id,
                "group_ids": user_group_ids,
            },
            skip=skip,
            limit=count,
        )

        knowledge_bases = []
        for knowledge_base in result.items:
            files = Knowledges.get_files_by_id(knowledge_base.id)
            file_count = len(files) if files else 0

            knowledge_bases.append(
                {
                    "id": knowledge_base.id,
                    "name": knowledge_base.name,
                    "description": knowledge_base.description or "",
                    "file_count": file_count,
                    "updated_at": knowledge_base.updated_at,
                }
            )

        return json.dumps(knowledge_bases, ensure_ascii=False)
    except Exception as e:
        log.exception(f"search_knowledge_bases error: {e}")
        return json.dumps({"error": str(e)})


async def search_knowledge_files(
    query: str,
    knowledge_id: Optional[str] = None,
    count: int = 5,
    skip: int = 0,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search files across knowledge bases the user has access to.

    :param query: The search query to find matching files by filename
    :param knowledge_id: Optional KB id to limit search to a specific knowledge base
    :param count: Maximum number of results to return (default: 5)
    :param skip: Number of results to skip for pagination (default: 0)
    :return: JSON with matching files containing id, filename, and updated_at
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        from open_webui.models.knowledge import Knowledges

        user_id = __user__.get("id")
        user_group_ids = [group.id for group in Groups.get_groups_by_member_id(user_id)]

        if knowledge_id:
            result = Knowledges.search_files_by_id(
                knowledge_id=knowledge_id,
                user_id=user_id,
                filter={"query": query},
                skip=skip,
                limit=count,
            )
        else:
            result = Knowledges.search_knowledge_files(
                filter={
                    "query": query,
                    "user_id": user_id,
                    "group_ids": user_group_ids,
                },
                skip=skip,
                limit=count,
            )

        files = []
        for file in result.items:
            file_info = {
                "id": file.id,
                "filename": file.filename,
                "updated_at": file.updated_at,
            }
            if hasattr(file, "collection") and file.collection:
                file_info["knowledge_id"] = file.collection.get("id", "")
                file_info["knowledge_name"] = file.collection.get("name", "")
            files.append(file_info)

        return json.dumps(files, ensure_ascii=False)
    except Exception as e:
        log.exception(f"search_knowledge_files error: {e}")
        return json.dumps({"error": str(e)})


async def view_knowledge_file(
    file_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the full content of a file from a knowledge base.

    :param file_id: The ID of the file to retrieve
    :return: JSON with the file's id, filename, and full text content
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        from open_webui.models.files import Files
        from open_webui.models.knowledge import Knowledges
        from open_webui.models.access_grants import AccessGrants

        user_id = __user__.get("id")
        user_role = __user__.get("role", "user")
        user_group_ids = [group.id for group in Groups.get_groups_by_member_id(user_id)]

        file = Files.get_file_by_id(file_id)
        if not file:
            return json.dumps({"error": "File not found"})

        # Check access via any KB containing this file
        knowledges = Knowledges.get_knowledges_by_file_id(file_id)
        has_knowledge_access = False
        knowledge_info = None

        for knowledge_base in knowledges:
            if (
                user_role == "admin"
                or knowledge_base.user_id == user_id
                or AccessGrants.has_access(
                    user_id=user_id,
                    resource_type="knowledge",
                    resource_id=knowledge_base.id,
                    permission="read",
                    user_group_ids=set(user_group_ids),
                )
            ):
                has_knowledge_access = True
                knowledge_info = {"id": knowledge_base.id, "name": knowledge_base.name}
                break

        if not has_knowledge_access:
            if file.user_id != user_id and user_role != "admin":
                return json.dumps({"error": "Access denied"})

        content = ""
        if file.data:
            content = file.data.get("content", "")

        result = {
            "id": file.id,
            "filename": file.filename,
            "content": content,
            "updated_at": file.updated_at,
            "created_at": file.created_at,
        }
        if knowledge_info:
            result["knowledge_id"] = knowledge_info["id"]
            result["knowledge_name"] = knowledge_info["name"]

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f"view_knowledge_file error: {e}")
        return json.dumps({"error": str(e)})


async def query_knowledge_files(
    query: str,
    knowledge_ids: Optional[list[str]] = None,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: list[dict] = None,
) -> str:
    """
    Search knowledge base files using semantic/vector search. Searches across collections (KBs),
    individual files, and notes that the user has access to.

    :param query: The search query to find semantically relevant content
    :param knowledge_ids: Optional list of KB ids to limit search to specific knowledge bases
    :param count: Maximum number of results to return (default: 5)
    :return: JSON with relevant chunks containing content, source filename, and relevance score
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    # Coerce parameters from LLM tool calls (may come as strings)
    if isinstance(count, str):
        try:
            count = int(count)
        except ValueError:
            count = 5  # Default fallback

    # Handle knowledge_ids being string "None", "null", or empty
    if isinstance(knowledge_ids, str):
        if knowledge_ids.lower() in ("none", "null", ""):
            knowledge_ids = None
        else:
            # Try to parse as JSON array if it looks like one
            try:
                knowledge_ids = json.loads(knowledge_ids)
            except json.JSONDecodeError:
                # Treat as single ID
                knowledge_ids = [knowledge_ids]

    try:
        from open_webui.models.knowledge import Knowledges
        from open_webui.models.files import Files
        from open_webui.models.notes import Notes
        from open_webui.retrieval.utils import query_collection
        from open_webui.models.access_grants import AccessGrants

        user_id = __user__.get("id")
        user_role = __user__.get("role", "user")
        user_group_ids = [group.id for group in Groups.get_groups_by_member_id(user_id)]

        embedding_function = __request__.app.state.EMBEDDING_FUNCTION
        if not embedding_function:
            return json.dumps({"error": "Embedding function not configured"})

        collection_names = []
        note_results = []  # Notes aren't vectorized, handle separately

        # If model has attached knowledge, use those
        if __model_knowledge__:
            for item in __model_knowledge__:
                item_type = item.get("type")
                item_id = item.get("id")

                if item_type == "collection":
                    # Knowledge base - use KB ID as collection name
                    knowledge = Knowledges.get_knowledge_by_id(item_id)
                    if knowledge and (
                        user_role == "admin"
                        or knowledge.user_id == user_id
                        or AccessGrants.has_access(
                            user_id=user_id,
                            resource_type="knowledge",
                            resource_id=knowledge.id,
                            permission="read",
                            user_group_ids=set(user_group_ids),
                        )
                    ):
                        collection_names.append(item_id)

                elif item_type == "file":
                    # Individual file - use file-{id} as collection name
                    file = Files.get_file_by_id(item_id)
                    if file and (user_role == "admin" or file.user_id == user_id):
                        collection_names.append(f"file-{item_id}")

                elif item_type == "note":
                    # Note - always return full content as context
                    note = Notes.get_note_by_id(item_id)
                    if note and (
                        user_role == "admin"
                        or note.user_id == user_id
                        or AccessGrants.has_access(
                            user_id=user_id,
                            resource_type="note",
                            resource_id=note.id,
                            permission="read",
                        )
                    ):
                        content = note.data.get("content", {}).get("md", "")
                        note_results.append(
                            {
                                "content": content,
                                "source": note.title,
                                "note_id": note.id,
                                "type": "note",
                            }
                        )

        elif knowledge_ids:
            # User specified specific KBs
            for knowledge_id in knowledge_ids:
                knowledge = Knowledges.get_knowledge_by_id(knowledge_id)
                if knowledge and (
                    user_role == "admin"
                    or knowledge.user_id == user_id
                    or AccessGrants.has_access(
                        user_id=user_id,
                        resource_type="knowledge",
                        resource_id=knowledge.id,
                        permission="read",
                        user_group_ids=set(user_group_ids),
                    )
                ):
                    collection_names.append(knowledge_id)
        else:
            # No model knowledge and no specific IDs - search all accessible KBs
            result = Knowledges.search_knowledge_bases(
                user_id,
                filter={
                    "query": "",
                    "user_id": user_id,
                    "group_ids": user_group_ids,
                },
                skip=0,
                limit=50,
            )
            collection_names = [knowledge_base.id for knowledge_base in result.items]

        chunks = []

        # Add note results first
        chunks.extend(note_results)

        # Query vector collections if any
        if collection_names:
            query_results = await query_collection(
                collection_names=collection_names,
                queries=[query],
                embedding_function=embedding_function,
                k=count,
            )

            if query_results and "documents" in query_results:
                documents = query_results.get("documents", [[]])[0]
                metadatas = query_results.get("metadatas", [[]])[0]
                distances = query_results.get("distances", [[]])[0]

                for idx, doc in enumerate(documents):
                    chunk_info = {
                        "content": doc,
                        "source": metadatas[idx].get(
                            "source", metadatas[idx].get("name", "Unknown")
                        ),
                        "file_id": metadatas[idx].get("file_id", ""),
                    }
                    if idx < len(distances):
                        chunk_info["distance"] = distances[idx]
                    chunks.append(chunk_info)

        # Limit to requested count
        chunks = chunks[:count]

        return json.dumps(chunks, ensure_ascii=False)
    except Exception as e:
        log.exception(f"query_knowledge_files error: {e}")
        return json.dumps({"error": str(e)})


async def query_knowledge_bases(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search knowledge bases by semantic similarity to query.
    Finds KBs whose name/description match the meaning of your query.
    Use this to discover relevant knowledge bases before querying their files.

    :param query: Natural language query describing what you're looking for
    :param count: Maximum results (default: 5)
    :return: JSON with matching KBs (id, name, description, similarity)
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        import heapq
        from open_webui.models.knowledge import Knowledges
        from open_webui.routers.knowledge import KNOWLEDGE_BASES_COLLECTION
        from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

        user_id = __user__.get("id")
        user_group_ids = [group.id for group in Groups.get_groups_by_member_id(user_id)]
        query_embedding = await __request__.app.state.EMBEDDING_FUNCTION(query)

        # Min-heap of (distance, knowledge_base_id) - only holds top `count` results
        top_results_heap = []
        seen_ids = set()
        page_offset = 0
        page_size = 100

        while True:
            accessible_knowledge_bases = Knowledges.search_knowledge_bases(
                user_id,
                filter={"user_id": user_id, "group_ids": user_group_ids},
                skip=page_offset,
                limit=page_size,
            )

            if not accessible_knowledge_bases.items:
                break

            accessible_ids = [kb.id for kb in accessible_knowledge_bases.items]

            search_results = VECTOR_DB_CLIENT.search(
                collection_name=KNOWLEDGE_BASES_COLLECTION,
                vectors=[query_embedding],
                filter={"knowledge_base_id": {"$in": accessible_ids}},
                limit=count,
            )

            if search_results and search_results.ids and search_results.ids[0]:
                result_ids = search_results.ids[0]
                result_distances = (
                    search_results.distances[0]
                    if search_results.distances
                    else [0] * len(result_ids)
                )

                for knowledge_base_id, distance in zip(result_ids, result_distances):
                    if knowledge_base_id in seen_ids:
                        continue
                    seen_ids.add(knowledge_base_id)

                    if len(top_results_heap) < count:
                        heapq.heappush(top_results_heap, (distance, knowledge_base_id))
                    elif distance > top_results_heap[0][0]:
                        heapq.heapreplace(
                            top_results_heap, (distance, knowledge_base_id)
                        )

            page_offset += page_size
            if len(accessible_knowledge_bases.items) < page_size:
                break
            if page_offset >= MAX_KNOWLEDGE_BASE_SEARCH_ITEMS:
                break

        # Sort by distance descending (best first) and fetch KB details
        sorted_results = sorted(top_results_heap, key=lambda x: x[0], reverse=True)

        matching_knowledge_bases = []
        for distance, knowledge_base_id in sorted_results:
            knowledge_base = Knowledges.get_knowledge_by_id(knowledge_base_id)
            if knowledge_base:
                matching_knowledge_bases.append(
                    {
                        "id": knowledge_base.id,
                        "name": knowledge_base.name,
                        "description": knowledge_base.description or "",
                        "similarity": round(distance, 4),
                    }
                )

        return json.dumps(matching_knowledge_bases, ensure_ascii=False)

    except Exception as e:
        log.exception(f"query_knowledge_bases error: {e}")
        return json.dumps({"error": str(e)})


# =============================================================================
# SKILLS TOOLS
# =============================================================================


async def view_skill(
    name: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Load the full instructions of a skill by its name from the available skills manifest.
    Use this when you need detailed instructions for a skill listed in <available_skills>.

    :param name: The name of the skill to load (as shown in the manifest)
    :return: The full skill instructions as markdown content
    """
    if __request__ is None:
        return json.dumps({"error": "Request context not available"})

    if not __user__:
        return json.dumps({"error": "User context not available"})

    try:
        from open_webui.models.skills import Skills
        from open_webui.models.access_grants import AccessGrants

        user_id = __user__.get("id")

        # Direct DB lookup by unique name
        skill = Skills.get_skill_by_name(name)

        if not skill or not skill.is_active:
            return json.dumps({"error": f"Skill '{name}' not found"})

        # Check user access
        user_role = __user__.get("role", "user")
        if user_role != "admin" and skill.user_id != user_id:
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id)
            ]
            if not AccessGrants.has_access(
                user_id=user_id,
                resource_type="skill",
                resource_id=skill.id,
                permission="read",
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({"error": "Access denied"})

        return json.dumps(
            {
                "name": skill.name,
                "content": skill.content,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f"view_skill error: {e}")
        return json.dumps({"error": str(e)})
