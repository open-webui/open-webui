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
from open_webui.models.memories import Memories
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
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

    :return: JSON with current_timestamp (seconds), current_iso (UTC ISO format), and user_local_iso (user's local time)
    """
    try:
        import datetime
        from zoneinfo import ZoneInfo

        now = datetime.datetime.now(datetime.timezone.utc)
        result = {
            'current_timestamp': int(now.timestamp()),
            'current_iso': now.isoformat(),
        }

        # Include the user's local time if timezone is available
        tz_name = __user__.get('timezone') if __user__ else None
        if tz_name:
            try:
                user_tz = ZoneInfo(tz_name)
                user_now = now.astimezone(user_tz)
                result['user_local_iso'] = user_now.isoformat()
                result['user_timezone'] = tz_name
            except Exception:
                pass

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'get_current_timestamp error: {e}')
        return json.dumps({'error': str(e)})


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

        result = {
            'current_timestamp': current_ts,
            'current_iso': now.isoformat(),
            'calculated_timestamp': adjusted_ts,
            'calculated_iso': adjusted.isoformat(),
        }

        # Include the user's local time if timezone is available
        tz_name = __user__.get('timezone') if __user__ else None
        if tz_name:
            try:
                from zoneinfo import ZoneInfo

                user_tz = ZoneInfo(tz_name)
                result['user_local_iso'] = now.astimezone(user_tz).isoformat()
                result['calculated_local_iso'] = adjusted.astimezone(user_tz).isoformat()
                result['user_timezone'] = tz_name
            except Exception:
                pass

        return json.dumps(result, ensure_ascii=False)
    except ImportError:
        # Fallback without dateutil
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        current_ts = int(now.timestamp())
        total_days = days_ago + (weeks_ago * 7) + (months_ago * 30) + (years_ago * 365)
        adjusted = now - datetime.timedelta(days=total_days)
        adjusted_ts = int(adjusted.timestamp())
        result = {
            'current_timestamp': current_ts,
            'current_iso': now.isoformat(),
            'calculated_timestamp': adjusted_ts,
            'calculated_iso': adjusted.isoformat(),
        }

        tz_name = __user__.get('timezone') if __user__ else None
        if tz_name:
            try:
                from zoneinfo import ZoneInfo

                user_tz = ZoneInfo(tz_name)
                result['user_local_iso'] = now.astimezone(user_tz).isoformat()
                result['calculated_local_iso'] = adjusted.astimezone(user_tz).isoformat()
                result['user_timezone'] = tz_name
            except Exception:
                pass

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'calculate_timestamp error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# WEB SEARCH TOOLS
# =============================================================================


async def search_web(
    query: str,
    count: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the public web for information. Best for current events, external references,
    or topics not covered in internal documents.

    :param query: The search query to look up
    :param count: Number of results to return (default: admin-configured value)
    :return: JSON with search results containing title, link, and snippet for each result
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        engine = __request__.app.state.config.WEB_SEARCH_ENGINE
        user = UserModel(**__user__) if __user__ else None

        configured = __request__.app.state.config.WEB_SEARCH_RESULT_COUNT
        max_count = 5 if configured is None else configured
        count = max(1, min(count, max_count)) if count is not None else max_count

        results = await asyncio.to_thread(_search_web, __request__, engine, query, user)

        # Limit results
        results = results[:count] if results else []

        return json.dumps(
            [{'title': r.title, 'link': r.link, 'snippet': r.snippet} for r in results],
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'search_web error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    try:
        content, _ = await asyncio.to_thread(get_content_from_url, __request__, url)

        # Truncate if configured (WEB_FETCH_MAX_CONTENT_LENGTH)
        max_length = getattr(__request__.app.state.config, 'WEB_FETCH_MAX_CONTENT_LENGTH', None)
        if max_length and max_length > 0 and len(content) > max_length:
            content = content[:max_length] + '\n\n[Content truncated...]'

        return content
    except Exception as e:
        log.exception(f'fetch_url error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_generations(
            request=__request__,
            form_data=CreateImageForm(prompt=prompt),
            user=user,
        )

        # Prepare file entries for the images
        image_files = [{'type': 'image', 'url': img['url']} for img in images]

        # Persist files to DB if chat context is available
        if __chat_id__ and __message_id__ and images:
            db_files = await Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )
            if db_files is not None:
                image_files = db_files

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    'type': 'chat:message:files',
                    'data': {
                        'files': image_files,
                    },
                }
            )
            # Return a message indicating the image is already displayed
            return json.dumps(
                {
                    'status': 'success',
                    'message': 'The image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.',
                    'images': images,
                },
                ensure_ascii=False,
            )

        return json.dumps({'status': 'success', 'images': images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'generate_image error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_edits(
            request=__request__,
            form_data=EditImageForm(prompt=prompt, image=image_urls),
            user=user,
        )

        # Prepare file entries for the images
        image_files = [{'type': 'image', 'url': img['url']} for img in images]

        # Persist files to DB if chat context is available
        if __chat_id__ and __message_id__ and images:
            db_files = await Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )
            if db_files is not None:
                image_files = db_files

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    'type': 'chat:message:files',
                    'data': {
                        'files': image_files,
                    },
                }
            )
            # Return a message indicating the image is already displayed
            return json.dumps(
                {
                    'status': 'success',
                    'message': 'The edited image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.',
                    'images': images,
                },
                ensure_ascii=False,
            )

        return json.dumps({'status': 'success', 'images': images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'edit_image error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    try:
        # Sanitize code (strips ANSI codes and markdown fences)
        code = sanitize_code(code)

        # Import blocked modules from config (same as middleware)
        from open_webui.config import CODE_INTERPRETER_BLOCKED_MODULES

        # Add import blocking code if there are blocked modules
        if CODE_INTERPRETER_BLOCKED_MODULES:
            import textwrap

            blocking_code = textwrap.dedent(
                f"""
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
                """
            )
            code = blocking_code + '\n' + code

        engine = getattr(__request__.app.state.config, 'CODE_INTERPRETER_ENGINE', 'pyodide')
        if engine == 'pyodide':
            # Execute via frontend pyodide using bidirectional event call
            if __event_call__ is None:
                return json.dumps(
                    {'error': 'Event call not available. WebSocket connection required for pyodide execution.'}
                )

            output = await __event_call__(
                {
                    'type': 'execute:python',
                    'data': {
                        'id': str(uuid4()),
                        'code': code,
                        'session_id': (__metadata__.get('session_id') if __metadata__ else None),
                        'files': (__metadata__.get('files', []) if __metadata__ else []),
                    },
                }
            )

            # Parse the output - pyodide returns dict with stdout, stderr, result
            if isinstance(output, dict):
                stdout = output.get('stdout', '')
                stderr = output.get('stderr', '')
                result = output.get('result', '')
            else:
                stdout = ''
                stderr = ''
                result = str(output) if output else ''

        elif engine == 'jupyter':
            from open_webui.utils.code_interpreter import execute_code_jupyter

            output = await execute_code_jupyter(
                __request__.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
                code,
                (
                    __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
                    if __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH == 'token'
                    else None
                ),
                (
                    __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
                    if __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH == 'password'
                    else None
                ),
                __request__.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
            )

            stdout = output.get('stdout', '')
            stderr = output.get('stderr', '')
            result = output.get('result', '')

        else:
            return json.dumps({'error': f'Unknown code interpreter engine: {engine}'})

        # Handle image outputs (base64 encoded) - replace with uploaded URLs
        # Get actual user object for image upload (upload_image requires user.id attribute)
        if __user__ and __user__.get('id'):
            from open_webui.models.users import Users
            from open_webui.utils.files import get_image_url_from_base64

            user = await Users.get_user_by_id(__user__['id'])

            # Extract and upload images from stdout
            if stdout and isinstance(stdout, str):
                stdout_lines = stdout.split('\n')
                for idx, line in enumerate(stdout_lines):
                    if 'data:image/png;base64' in line:
                        image_url = await get_image_url_from_base64(
                            __request__,
                            line,
                            __metadata__ or {},
                            user,
                        )
                        if image_url:
                            stdout_lines[idx] = f'![Output Image]({image_url})'
                stdout = '\n'.join(stdout_lines)

            # Extract and upload images from result
            if result and isinstance(result, str):
                result_lines = result.split('\n')
                for idx, line in enumerate(result_lines):
                    if 'data:image/png;base64' in line:
                        image_url = await get_image_url_from_base64(
                            __request__,
                            line,
                            __metadata__ or {},
                            user,
                        )
                        if image_url:
                            result_lines[idx] = f'![Output Image]({image_url})'
                result = '\n'.join(result_lines)

        response = {
            'status': 'success',
            'stdout': stdout,
            'stderr': stderr,
            'result': result,
        }

        return json.dumps(response, ensure_ascii=False)
    except Exception as e:
        log.exception(f'execute_code error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        results = await query_memory(
            __request__,
            QueryMemoryForm(content=query, k=count),
            user,
        )

        if results and hasattr(results, 'documents') and results.documents:
            memories = []
            for doc_idx, doc in enumerate(results.documents[0]):
                memory_id = None
                if results.ids and results.ids[0]:
                    memory_id = results.ids[0][doc_idx]
                created_at = 'Unknown'
                if results.metadatas and results.metadatas[0][doc_idx].get('created_at'):
                    created_at = time.strftime(
                        '%Y-%m-%d',
                        time.localtime(results.metadatas[0][doc_idx]['created_at']),
                    )
                memories.append({'id': memory_id, 'date': created_at, 'content': doc})
            return json.dumps(memories, ensure_ascii=False)
        else:
            return json.dumps([])
    except Exception as e:
        log.exception(f'search_memories error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await _add_memory(
            __request__,
            AddMemoryForm(content=content),
            user,
        )

        return json.dumps({'status': 'success', 'id': memory.id}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'add_memory error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await update_memory_by_id(
            memory_id=memory_id,
            request=__request__,
            form_data=MemoryUpdateModel(content=content),
            user=user,
        )

        return json.dumps(
            {'status': 'success', 'id': memory.id, 'content': memory.content},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'replace_memory_content error: {e}')
        return json.dumps({'error': str(e)})


async def delete_memory(
    memory_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete a memory by its ID.

    :param memory_id: The ID of the memory to delete
    :return: Confirmation that the memory was deleted
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        result = await Memories.delete_memory_by_id_and_user_id(memory_id, user.id)

        if result:
            await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=f'user-memory-{user.id}', ids=[memory_id])
            return json.dumps(
                {'status': 'success', 'message': f'Memory {memory_id} deleted'},
                ensure_ascii=False,
            )
        else:
            return json.dumps({'error': 'Memory not found or access denied'})
    except Exception as e:
        log.exception(f'delete_memory error: {e}')
        return json.dumps({'error': str(e)})


async def list_memories(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List all stored memories for the user.

    :return: JSON list of all memories with id, content, and dates
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memories = await Memories.get_memories_by_user_id(user.id)

        if memories:
            result = [
                {
                    'id': m.id,
                    'content': m.content,
                    'created_at': time.strftime('%Y-%m-%d %H:%M', time.localtime(m.created_at)),
                    'updated_at': time.strftime('%Y-%m-%d %H:%M', time.localtime(m.updated_at)),
                }
                for m in memories
            ]
            return json.dumps(result, ensure_ascii=False)
        else:
            return json.dumps([])
    except Exception as e:
        log.exception(f'list_memories error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        result = await Notes.search_notes(
            user_id=user_id,
            filter={
                'query': query,
                'user_id': user_id,
                'group_ids': user_group_ids,
                'permission': 'read',
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
            content_snippet = ''
            if note.data and note.data.get('content', {}).get('md'):
                md_content = note.data['content']['md']
                content_lower = md_content.lower()

                # Find the first matching word to center the snippet around.
                search_words = query.lower().split()
                match_pos = -1
                match_len = len(query)
                for word in search_words:
                    found_pos = content_lower.find(word)
                    if found_pos != -1:
                        match_pos = found_pos
                        match_len = len(word)
                        break

                if match_pos != -1:
                    snippet_start = max(0, match_pos - 50)
                    snippet_end = min(len(md_content), match_pos + match_len + 100)
                    content_snippet = (
                        ('...' if snippet_start > 0 else '')
                        + md_content[snippet_start:snippet_end]
                        + ('...' if snippet_end < len(md_content) else '')
                    )
                else:
                    content_snippet = md_content[:150] + ('...' if len(md_content) > 150 else '')

            notes.append(
                {
                    'id': note.id,
                    'title': note.title,
                    'snippet': content_snippet,
                    'updated_at': note.updated_at,
                }
            )

            if len(notes) >= count:
                break

        return json.dumps(notes, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_notes error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        note = await Notes.get_note_by_id(note_id)

        if not note:
            return json.dumps({'error': 'Note not found'})

        # Check access permission
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        from open_webui.models.access_grants import AccessGrants

        if note.user_id != user_id and not await AccessGrants.has_access(
            user_id=user_id,
            resource_type='note',
            resource_id=note.id,
            permission='read',
            user_group_ids=set(user_group_ids),
        ):
            return json.dumps({'error': 'Access denied'})

        # Extract markdown content
        content = ''
        if note.data and note.data.get('content', {}).get('md'):
            content = note.data['content']['md']

        return json.dumps(
            {
                'id': note.id,
                'title': note.title,
                'content': content,
                'updated_at': note.updated_at,
                'created_at': note.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_note error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.notes import NoteForm

        user_id = __user__.get('id')

        form = NoteForm(
            title=title,
            data={'content': {'md': content}},
            access_grants=[],  # Private by default - only owner can access
        )

        new_note = await Notes.insert_new_note(user_id, form)

        if not new_note:
            return json.dumps({'error': 'Failed to create note'})

        return json.dumps(
            {
                'status': 'success',
                'id': new_note.id,
                'title': new_note.title,
                'created_at': new_note.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'write_note error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.notes import NoteUpdateForm

        note = await Notes.get_note_by_id(note_id)

        if not note:
            return json.dumps({'error': 'Note not found'})

        # Check write permission
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        from open_webui.models.access_grants import AccessGrants

        if note.user_id != user_id and not await AccessGrants.has_access(
            user_id=user_id,
            resource_type='note',
            resource_id=note.id,
            permission='write',
            user_group_ids=set(user_group_ids),
        ):
            return json.dumps({'error': 'Write access denied'})

        # Build update form
        update_data = {'data': {'content': {'md': content}}}
        if title:
            update_data['title'] = title

        form = NoteUpdateForm(**update_data)
        updated_note = await Notes.update_note_by_id(note_id, form)

        if not updated_note:
            return json.dumps({'error': 'Failed to update note'})

        return json.dumps(
            {
                'status': 'success',
                'id': updated_note.id,
                'title': updated_note.title,
                'updated_at': updated_note.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'replace_note_content error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        chats = await Chats.get_chats_by_user_id_and_search_text(
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
            snippet = ''
            messages = chat.chat.get('history', {}).get('messages', {})
            lower_query = query.lower()

            for msg_id, msg in messages.items():
                content = msg.get('content', '')
                if isinstance(content, str) and lower_query in content.lower():
                    idx = content.lower().find(lower_query)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 100)
                    snippet = ('...' if start > 0 else '') + content[start:end] + ('...' if end < len(content) else '')
                    break

            if not snippet and lower_query in chat.title.lower():
                snippet = f'Title match: {chat.title}'

            results.append(
                {
                    'id': chat.id,
                    'title': chat.title,
                    'snippet': snippet,
                    'updated_at': chat.updated_at,
                }
            )

            if len(results) >= count:
                break

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_chats error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id)

        if not chat:
            return json.dumps({'error': 'Chat not found or access denied'})

        # Extract messages from history
        messages = []
        history = chat.chat.get('history', {})
        msg_dict = history.get('messages', {})

        # Build message chain from currentId
        current_id = history.get('currentId')
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            msg = msg_dict.get(current_id)
            if msg:
                messages.append(
                    {
                        'role': msg.get('role', ''),
                        'content': msg.get('content', ''),
                    }
                )
            current_id = msg.get('parentId') if msg else None

        # Reverse to get chronological order
        messages.reverse()

        return json.dumps(
            {
                'id': chat.id,
                'title': chat.title,
                'messages': messages,
                'updated_at': chat.updated_at,
                'created_at': chat.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_chat error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        # Get all channels the user has access to
        all_channels = await Channels.get_channels_by_user_id(user_id)

        # Filter by query
        lower_query = query.lower()
        matching_channels = []

        for channel in all_channels:
            name_match = lower_query in channel.name.lower() if channel.name else False
            desc_match = lower_query in (channel.description or '').lower()

            if name_match or desc_match:
                matching_channels.append(
                    {
                        'id': channel.id,
                        'name': channel.name,
                        'description': channel.description or '',
                        'type': channel.type or 'public',
                    }
                )

            if len(matching_channels) >= count:
                break

        return json.dumps(matching_channels, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_channels error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        # Get all channels the user has access to
        user_channels = await Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]
        channel_map = {c.id: c for c in user_channels}

        if not channel_ids:
            return json.dumps([])

        # Convert timestamps to nanoseconds (Message.created_at is in nanoseconds)
        start_ts = start_timestamp * 1_000_000_000 if start_timestamp else None
        end_ts = end_timestamp * 1_000_000_000 if end_timestamp else None

        # Search messages using the model method
        matching_messages = await Messages.search_messages_by_channel_ids(
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
            content = msg.content or ''
            lower_query = query.lower()
            idx = content.lower().find(lower_query)
            if idx != -1:
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 100)
                snippet = ('...' if start > 0 else '') + content[start:end] + ('...' if end < len(content) else '')
            else:
                snippet = content[:150] + ('...' if len(content) > 150 else '')

            results.append(
                {
                    'channel_id': msg.channel_id,
                    'channel_name': channel.name if channel else 'Unknown',
                    'message_id': msg.id,
                    'content_snippet': snippet,
                    'is_thread_reply': msg.parent_id is not None,
                    'parent_id': msg.parent_id,
                    'created_at': msg.created_at,
                }
            )

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_channel_messages error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        message = await Messages.get_message_by_id(message_id)

        if not message:
            return json.dumps({'error': 'Message not found'})

        # Verify user has access to the channel
        channel = await Channels.get_channel_by_id(message.channel_id)
        if not channel:
            return json.dumps({'error': 'Channel not found'})

        # Check if user has access to the channel
        user_channels = await Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]

        if message.channel_id not in channel_ids:
            return json.dumps({'error': 'Access denied'})

        # Build response with thread information
        result = {
            'id': message.id,
            'channel_id': message.channel_id,
            'channel_name': channel.name,
            'content': message.content,
            'user_id': message.user_id,
            'is_thread_reply': message.parent_id is not None,
            'parent_id': message.parent_id,
            'reply_count': message.reply_count,
            'created_at': message.created_at,
            'updated_at': message.updated_at,
        }

        # Include user info if available
        if message.user:
            result['user_name'] = message.user.name

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'view_channel_message error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        # Get the parent message
        parent_message = await Messages.get_message_by_id(parent_message_id)

        if not parent_message:
            return json.dumps({'error': 'Message not found'})

        # Verify user has access to the channel
        channel = await Channels.get_channel_by_id(parent_message.channel_id)
        if not channel:
            return json.dumps({'error': 'Channel not found'})

        user_channels = await Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]

        if parent_message.channel_id not in channel_ids:
            return json.dumps({'error': 'Access denied'})

        # Get all thread replies
        thread_replies = await Messages.get_thread_replies_by_message_id(parent_message_id)

        # Build the response
        messages = []

        # Add parent message first
        messages.append(
            {
                'id': parent_message.id,
                'content': parent_message.content,
                'user_id': parent_message.user_id,
                'user_name': parent_message.user.name if parent_message.user else None,
                'is_parent': True,
                'created_at': parent_message.created_at,
            }
        )

        # Add thread replies (reverse to get chronological order)
        for reply in reversed(thread_replies):
            messages.append(
                {
                    'id': reply.id,
                    'content': reply.content,
                    'user_id': reply.user_id,
                    'user_name': reply.user.name if reply.user else None,
                    'is_parent': False,
                    'reply_to_id': reply.reply_to_id,
                    'created_at': reply.created_at,
                }
            )

        return json.dumps(
            {
                'channel_id': parent_message.channel_id,
                'channel_name': channel.name,
                'thread_id': parent_message_id,
                'message_count': len(messages),
                'messages': messages,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_channel_thread error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.knowledge import Knowledges

        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        result = await Knowledges.search_knowledge_bases(
            user_id,
            filter={
                'query': '',
                'user_id': user_id,
                'group_ids': user_group_ids,
            },
            skip=skip,
            limit=count,
        )

        knowledge_bases = []
        for knowledge_base in result.items:
            files = await Knowledges.get_files_by_id(knowledge_base.id)
            file_count = len(files) if files else 0

            knowledge_bases.append(
                {
                    'id': knowledge_base.id,
                    'name': knowledge_base.name,
                    'description': knowledge_base.description or '',
                    'file_count': file_count,
                    'updated_at': knowledge_base.updated_at,
                }
            )

        return json.dumps(knowledge_bases, ensure_ascii=False)
    except Exception as e:
        log.exception(f'list_knowledge_bases error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.knowledge import Knowledges

        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        result = await Knowledges.search_knowledge_bases(
            user_id,
            filter={
                'query': query,
                'user_id': user_id,
                'group_ids': user_group_ids,
            },
            skip=skip,
            limit=count,
        )

        knowledge_bases = []
        for knowledge_base in result.items:
            files = await Knowledges.get_files_by_id(knowledge_base.id)
            file_count = len(files) if files else 0

            knowledge_bases.append(
                {
                    'id': knowledge_base.id,
                    'name': knowledge_base.name,
                    'description': knowledge_base.description or '',
                    'file_count': file_count,
                    'updated_at': knowledge_base.updated_at,
                }
            )

        return json.dumps(knowledge_bases, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_knowledge_bases error: {e}')
        return json.dumps({'error': str(e)})


async def search_knowledge_files(
    query: str,
    knowledge_id: Optional[str] = None,
    count: int = 5,
    skip: int = 0,
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: Optional[list[dict]] = None,
) -> str:
    """
    Search files by filename across knowledge bases the user has access to.
    When the model has attached knowledge, searches only within attached KBs and files.

    :param query: The search query to find matching files by filename
    :param knowledge_id: Optional KB id to limit search to a specific knowledge base
    :param count: Maximum number of results to return (default: 5)
    :param skip: Number of results to skip for pagination (default: 0)
    :return: JSON with matching files containing id, filename, and updated_at
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.knowledge import Knowledges
        from open_webui.models.files import Files
        from open_webui.models.access_grants import AccessGrants

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        # When model has attached knowledge, scope to attached KBs/files only
        if __model_knowledge__:
            attached_kb_ids = set()
            attached_file_ids = set()

            for item in __model_knowledge__:
                item_type = item.get('type')
                item_id = item.get('id')
                if item_type == 'collection':
                    attached_kb_ids.add(item_id)
                elif item_type == 'file':
                    attached_file_ids.add(item_id)

            # If knowledge_id specified, verify it's in the attached set
            if knowledge_id:
                if knowledge_id not in attached_kb_ids:
                    return json.dumps({'error': f'Knowledge base {knowledge_id} is not attached to this model'})
                attached_kb_ids = {knowledge_id}

            all_files = []

            # Search within attached KBs
            for kb_id in attached_kb_ids:
                knowledge = await Knowledges.get_knowledge_by_id(kb_id)
                if not knowledge:
                    continue

                if not (
                    user_role == 'admin'
                    or knowledge.user_id == user_id
                    or await AccessGrants.has_access(
                        user_id=user_id,
                        resource_type='knowledge',
                        resource_id=knowledge.id,
                        permission='read',
                        user_group_ids=set(user_group_ids),
                    )
                ):
                    continue

                result = await Knowledges.search_files_by_id(
                    knowledge_id=kb_id,
                    user_id=user_id,
                    filter={'query': query},
                    skip=0,
                    limit=count + skip,
                )

                for file in result.items:
                    all_files.append(
                        {
                            'id': file.id,
                            'filename': file.filename,
                            'knowledge_id': knowledge.id,
                            'knowledge_name': knowledge.name,
                            'updated_at': file.updated_at,
                        }
                    )

            # Search within directly attached files (filename match)
            if not knowledge_id and attached_file_ids:
                query_lower = query.lower() if query else ''
                for file_id in attached_file_ids:
                    file = await Files.get_file_by_id(file_id)
                    if file and (not query_lower or query_lower in file.filename.lower()):
                        all_files.append(
                            {
                                'id': file.id,
                                'filename': file.filename,
                                'updated_at': file.updated_at,
                            }
                        )

            # Apply pagination across combined results
            all_files = all_files[skip : skip + count]
            return json.dumps(all_files, ensure_ascii=False)

        # No attached knowledge - search all accessible KBs
        if knowledge_id:
            result = await Knowledges.search_files_by_id(
                knowledge_id=knowledge_id,
                user_id=user_id,
                filter={'query': query},
                skip=skip,
                limit=count,
            )
        else:
            result = await Knowledges.search_knowledge_files(
                filter={
                    'query': query,
                    'user_id': user_id,
                    'group_ids': user_group_ids,
                },
                skip=skip,
                limit=count,
            )

        files = []
        for file in result.items:
            file_info = {
                'id': file.id,
                'filename': file.filename,
                'updated_at': file.updated_at,
            }
            if hasattr(file, 'collection') and file.collection:
                file_info['knowledge_id'] = file.collection.get('id', '')
                file_info['knowledge_name'] = file.collection.get('name', '')
            files.append(file_info)

        return json.dumps(files, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_knowledge_files error: {e}')
        return json.dumps({'error': str(e)})


# Hard cap for view_file / view_knowledge_file output
MAX_VIEW_FILE_CHARS = 100_000
DEFAULT_VIEW_FILE_MAX_CHARS = 10_000


async def view_file(
    file_id: str,
    offset: int = 0,
    max_chars: int = DEFAULT_VIEW_FILE_MAX_CHARS,
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: Optional[list[dict]] = None,
) -> str:
    """
    Get the content of a file by its ID. Supports pagination for large files.

    :param file_id: The ID of the file to retrieve
    :param offset: Character offset to start reading from (default: 0)
    :param max_chars: Maximum characters to return (default: 10000, hard cap: 100000)
    :return: JSON with the file's id, filename, content, and pagination metadata if truncated
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    # Coerce parameters from LLM tool calls (may come as strings)
    if isinstance(offset, str):
        try:
            offset = int(offset)
        except ValueError:
            offset = 0
    if isinstance(max_chars, str):
        try:
            max_chars = int(max_chars)
        except ValueError:
            max_chars = DEFAULT_VIEW_FILE_MAX_CHARS

    # Enforce hard cap
    max_chars = min(max(max_chars, 1), MAX_VIEW_FILE_CHARS)
    offset = max(offset, 0)

    try:
        from open_webui.models.files import Files
        from open_webui.utils.access_control.files import has_access_to_file

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')

        file = await Files.get_file_by_id(file_id)
        if not file:
            return json.dumps({'error': 'File not found'})

        if (
            file.user_id != user_id
            and user_role != 'admin'
            and not any(
                item.get('type') == 'file' and item.get('id') == file_id for item in (__model_knowledge__ or [])
            )
            and not await has_access_to_file(
                file_id=file_id,
                access_type='read',
                user=UserModel(**__user__),
            )
        ):
            return json.dumps({'error': 'File not found'})

        content = ''
        if file.data:
            content = file.data.get('content', '')

        total_chars = len(content)
        sliced = content[offset : offset + max_chars]
        is_truncated = (offset + len(sliced)) < total_chars

        result = {
            'id': file.id,
            'filename': file.filename,
            'content': sliced,
            'updated_at': file.updated_at,
            'created_at': file.created_at,
        }

        if is_truncated or offset > 0:
            result['truncated'] = is_truncated
            result['total_chars'] = total_chars
            result['returned_chars'] = len(sliced)
            result['offset'] = offset
            if is_truncated:
                result['next_offset'] = offset + len(sliced)

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'view_file error: {e}')
        return json.dumps({'error': str(e)})


async def view_knowledge_file(
    file_id: str,
    offset: int = 0,
    max_chars: int = DEFAULT_VIEW_FILE_MAX_CHARS,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the content of a file from a knowledge base. Supports pagination for large files.

    :param file_id: The ID of the file to retrieve
    :param offset: Character offset to start reading from (default: 0)
    :param max_chars: Maximum characters to return (default: 10000, hard cap: 100000)
    :return: JSON with the file's id, filename, content, and pagination metadata if truncated
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    # Coerce parameters from LLM tool calls (may come as strings)
    if isinstance(offset, str):
        try:
            offset = int(offset)
        except ValueError:
            offset = 0
    if isinstance(max_chars, str):
        try:
            max_chars = int(max_chars)
        except ValueError:
            max_chars = DEFAULT_VIEW_FILE_MAX_CHARS

    # Enforce hard cap
    max_chars = min(max(max_chars, 1), MAX_VIEW_FILE_CHARS)
    offset = max(offset, 0)

    try:
        from open_webui.models.files import Files
        from open_webui.models.knowledge import Knowledges
        from open_webui.models.access_grants import AccessGrants

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        file = await Files.get_file_by_id(file_id)
        if not file:
            return json.dumps({'error': 'File not found'})

        # Check access via any KB containing this file
        knowledges = await Knowledges.get_knowledges_by_file_id(file_id)
        has_knowledge_access = False
        knowledge_info = None

        for knowledge_base in knowledges:
            if (
                user_role == 'admin'
                or knowledge_base.user_id == user_id
                or await AccessGrants.has_access(
                    user_id=user_id,
                    resource_type='knowledge',
                    resource_id=knowledge_base.id,
                    permission='read',
                    user_group_ids=set(user_group_ids),
                )
            ):
                has_knowledge_access = True
                knowledge_info = {'id': knowledge_base.id, 'name': knowledge_base.name}
                break

        if not has_knowledge_access:
            if file.user_id != user_id and user_role != 'admin':
                return json.dumps({'error': 'Access denied'})

        content = ''
        if file.data:
            content = file.data.get('content', '')

        total_chars = len(content)
        sliced = content[offset : offset + max_chars]
        is_truncated = (offset + len(sliced)) < total_chars

        result = {
            'id': file.id,
            'filename': file.filename,
            'content': sliced,
            'updated_at': file.updated_at,
            'created_at': file.created_at,
        }
        if knowledge_info:
            result['knowledge_id'] = knowledge_info['id']
            result['knowledge_name'] = knowledge_info['name']

        if is_truncated or offset > 0:
            result['truncated'] = is_truncated
            result['total_chars'] = total_chars
            result['returned_chars'] = len(sliced)
            result['offset'] = offset
            if is_truncated:
                result['next_offset'] = offset + len(sliced)

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'view_knowledge_file error: {e}')
        return json.dumps({'error': str(e)})


async def list_knowledge(
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: Optional[list[dict]] = None,
) -> str:
    """
    List all knowledge bases, files, and notes attached to the current model.
    Use this first to discover what knowledge is available before querying or reading files.

    :return: JSON with knowledge_bases, files, and notes attached to this model
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    if not __model_knowledge__:
        return json.dumps({'knowledge_bases': [], 'files': [], 'notes': []})

    try:
        from open_webui.models.knowledge import Knowledges
        from open_webui.models.files import Files
        from open_webui.models.notes import Notes
        from open_webui.models.access_grants import AccessGrants

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        knowledge_bases = []
        files = []
        notes = []

        for item in __model_knowledge__:
            item_type = item.get('type')
            item_id = item.get('id')

            if item_type == 'collection':
                knowledge = await Knowledges.get_knowledge_by_id(item_id)
                if knowledge and (
                    user_role == 'admin'
                    or knowledge.user_id == user_id
                    or await AccessGrants.has_access(
                        user_id=user_id,
                        resource_type='knowledge',
                        resource_id=knowledge.id,
                        permission='read',
                        user_group_ids=set(user_group_ids),
                    )
                ):
                    kb_files = await Knowledges.get_files_by_id(knowledge.id)
                    file_count = len(kb_files) if kb_files else 0

                    kb_entry = {
                        'id': knowledge.id,
                        'name': knowledge.name,
                        'description': knowledge.description or '',
                        'file_count': file_count,
                    }

                    # Include file listing for each KB
                    if kb_files:
                        kb_entry['files'] = [{'id': f.id, 'filename': f.filename} for f in kb_files]

                    knowledge_bases.append(kb_entry)

            elif item_type == 'file':
                file = await Files.get_file_by_id(item_id)
                if file:
                    files.append(
                        {
                            'id': file.id,
                            'filename': file.filename,
                            'updated_at': file.updated_at,
                        }
                    )

            elif item_type == 'note':
                note = await Notes.get_note_by_id(item_id)
                if note and (
                    user_role == 'admin'
                    or note.user_id == user_id
                    or await AccessGrants.has_access(
                        user_id=user_id,
                        resource_type='note',
                        resource_id=note.id,
                        permission='read',
                    )
                ):
                    notes.append(
                        {
                            'id': note.id,
                            'title': note.title,
                        }
                    )

        return json.dumps(
            {
                'knowledge_bases': knowledge_bases,
                'files': files,
                'notes': notes,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'list_knowledge error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    # Coerce parameters from LLM tool calls (may come as strings)
    if isinstance(count, str):
        try:
            count = int(count)
        except ValueError:
            count = 5  # Default fallback

    # Handle knowledge_ids being string "None", "null", or empty
    if isinstance(knowledge_ids, str):
        if knowledge_ids.lower() in ('none', 'null', ''):
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

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        embedding_function = __request__.app.state.EMBEDDING_FUNCTION
        if not embedding_function:
            return json.dumps({'error': 'Embedding function not configured'})

        collection_names = []
        note_results = []  # Notes aren't vectorized, handle separately

        # If model has attached knowledge, use those
        if __model_knowledge__:
            for item in __model_knowledge__:
                item_type = item.get('type')
                item_id = item.get('id')

                if item_type == 'collection':
                    # Knowledge base - use KB ID as collection name
                    knowledge = await Knowledges.get_knowledge_by_id(item_id)
                    if knowledge and (
                        user_role == 'admin'
                        or knowledge.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='knowledge',
                            resource_id=knowledge.id,
                            permission='read',
                            user_group_ids=set(user_group_ids),
                        )
                    ):
                        collection_names.append(item_id)

                elif item_type == 'file':
                    # Individual file - use file-{id} as collection name
                    file = await Files.get_file_by_id(item_id)
                    if file:
                        collection_names.append(f'file-{item_id}')

                elif item_type == 'note':
                    # Note - always return full content as context
                    note = await Notes.get_note_by_id(item_id)
                    if note and (
                        user_role == 'admin'
                        or note.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='note',
                            resource_id=note.id,
                            permission='read',
                        )
                    ):
                        content = note.data.get('content', {}).get('md', '')
                        note_results.append(
                            {
                                'content': content,
                                'source': note.title,
                                'note_id': note.id,
                                'type': 'note',
                            }
                        )

        elif knowledge_ids:
            # User specified specific KBs
            for knowledge_id in knowledge_ids:
                knowledge = await Knowledges.get_knowledge_by_id(knowledge_id)
                if knowledge and (
                    user_role == 'admin'
                    or knowledge.user_id == user_id
                    or await AccessGrants.has_access(
                        user_id=user_id,
                        resource_type='knowledge',
                        resource_id=knowledge.id,
                        permission='read',
                        user_group_ids=set(user_group_ids),
                    )
                ):
                    collection_names.append(knowledge_id)
        else:
            # No model knowledge and no specific IDs - search all accessible KBs
            result = await Knowledges.search_knowledge_bases(
                user_id,
                filter={
                    'query': '',
                    'user_id': user_id,
                    'group_ids': user_group_ids,
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
                __request__,
                collection_names=collection_names,
                queries=[query],
                embedding_function=embedding_function,
                k=count,
            )

            if query_results and 'documents' in query_results:
                documents = query_results.get('documents', [[]])[0]
                metadatas = query_results.get('metadatas', [[]])[0]
                distances = query_results.get('distances', [[]])[0]

                for idx, doc in enumerate(documents):
                    chunk_info = {
                        'content': doc,
                        'source': metadatas[idx].get('source', metadatas[idx].get('name', 'Unknown')),
                        'file_id': metadatas[idx].get('file_id', ''),
                    }
                    if idx < len(distances):
                        chunk_info['distance'] = distances[idx]
                    chunks.append(chunk_info)

        # Limit to requested count
        chunks = chunks[:count]

        return json.dumps(chunks, ensure_ascii=False)
    except Exception as e:
        log.exception(f'query_knowledge_files error: {e}')
        return json.dumps({'error': str(e)})


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
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        import heapq
        from open_webui.models.knowledge import Knowledges
        from open_webui.routers.knowledge import KNOWLEDGE_BASES_COLLECTION
        from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT

        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]
        query_embedding = await __request__.app.state.EMBEDDING_FUNCTION(query)

        # Min-heap of (distance, knowledge_base_id) - only holds top `count` results
        top_results_heap = []
        seen_ids = set()
        page_offset = 0
        page_size = 100

        while True:
            accessible_knowledge_bases = await Knowledges.search_knowledge_bases(
                user_id,
                filter={'user_id': user_id, 'group_ids': user_group_ids},
                skip=page_offset,
                limit=page_size,
            )

            if not accessible_knowledge_bases.items:
                break

            accessible_ids = [kb.id for kb in accessible_knowledge_bases.items]

            search_results = await ASYNC_VECTOR_DB_CLIENT.search(
                collection_name=KNOWLEDGE_BASES_COLLECTION,
                vectors=[query_embedding],
                filter={'knowledge_base_id': {'$in': accessible_ids}},
                limit=count,
            )

            if search_results and search_results.ids and search_results.ids[0]:
                result_ids = search_results.ids[0]
                result_distances = search_results.distances[0] if search_results.distances else [0] * len(result_ids)

                for knowledge_base_id, distance in zip(result_ids, result_distances):
                    if knowledge_base_id in seen_ids:
                        continue
                    seen_ids.add(knowledge_base_id)

                    if len(top_results_heap) < count:
                        heapq.heappush(top_results_heap, (distance, knowledge_base_id))
                    elif distance > top_results_heap[0][0]:
                        heapq.heapreplace(top_results_heap, (distance, knowledge_base_id))

            page_offset += page_size
            if len(accessible_knowledge_bases.items) < page_size:
                break
            if page_offset >= MAX_KNOWLEDGE_BASE_SEARCH_ITEMS:
                break

        # Sort by distance descending (best first) and fetch KB details
        sorted_results = sorted(top_results_heap, key=lambda x: x[0], reverse=True)

        matching_knowledge_bases = []
        for distance, knowledge_base_id in sorted_results:
            knowledge_base = await Knowledges.get_knowledge_by_id(knowledge_base_id)
            if knowledge_base:
                matching_knowledge_bases.append(
                    {
                        'id': knowledge_base.id,
                        'name': knowledge_base.name,
                        'description': knowledge_base.description or '',
                        'similarity': round(distance, 4),
                    }
                )

        return json.dumps(matching_knowledge_bases, ensure_ascii=False)

    except Exception as e:
        log.exception(f'query_knowledge_bases error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# SKILLS TOOLS
# =============================================================================


async def view_skill(
    id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Load the full instructions of a skill by its id from the available skills manifest.
    Use this when you need detailed instructions for a skill listed in <available_skills>.

    :param id: The id of the skill to load (as shown in the manifest)
    :return: The full skill instructions as markdown content
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.skills import Skills
        from open_webui.models.access_grants import AccessGrants

        user_id = __user__.get('id')

        # Direct DB lookup by id (case-insensitive since IDs are stored lowercase)
        skill = await Skills.get_skill_by_id(id.lower())

        if not skill or not skill.is_active:
            return json.dumps({'error': f"Skill '{id}' not found"})

        # Check user access
        user_role = __user__.get('role', 'user')
        if user_role != 'admin' and skill.user_id != user_id:
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='skill',
                resource_id=skill.id,
                permission='read',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied'})

        return json.dumps(
            {
                'name': skill.name,
                'content': skill.content,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_skill error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# TASK MANAGEMENT TOOLS
# =============================================================================

from pydantic import BaseModel, Field
from typing import Literal

VALID_TASK_STATUSES = {'pending', 'in_progress', 'completed', 'cancelled'}


class TaskItem(BaseModel):
    id: Optional[str] = Field(None, description='Unique identifier for the task. Auto-generated if omitted.')
    content: str = Field(..., description='Task description.')
    status: Literal['pending', 'in_progress', 'completed', 'cancelled'] = Field('pending', description='Task status.')


def _task_summary(all_tasks: list[dict]) -> dict:
    """Build summary counts for a task list."""
    pending = sum(1 for t in all_tasks if t['status'] == 'pending')
    in_progress = sum(1 for t in all_tasks if t['status'] == 'in_progress')
    completed = sum(1 for t in all_tasks if t['status'] == 'completed')
    cancelled = sum(1 for t in all_tasks if t['status'] == 'cancelled')
    return {
        'total': len(all_tasks),
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
        'cancelled': cancelled,
    }


async def _emit_tasks(event_emitter, all_tasks: list[dict]):
    """Persist task state to the UI."""
    if event_emitter:
        await event_emitter(
            {
                'type': 'chat:message:tasks',
                'data': {
                    'tasks': all_tasks,
                },
            }
        )


async def create_tasks(
    tasks: list[TaskItem],
    __chat_id__: str = None,
    __message_id__: str = None,
    __event_emitter__: callable = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a task checklist to track progress on multi-step work.
    Call this once at the start to define all steps, then use
    update_task to mark each task as you complete it.

    :param tasks: List of task items. Each item: content (string, required), status (pending|in_progress|completed|cancelled, default pending), id (optional, auto-generated).
    :return: JSON with the full task list and summary counts
    """
    if __chat_id__ is None:
        return json.dumps({'error': 'Chat context not available'})

    try:
        all_tasks = []
        for idx, task in enumerate(tasks):
            if hasattr(task, 'model_dump'):
                d = task.model_dump(exclude_none=True)
            elif isinstance(task, dict):
                d = task
            else:
                d = dict(task)

            content = str(d.get('content', '')).strip()
            if not content:
                continue

            item_id = str(d.get('id', '') or '').strip() or str(idx + 1)
            status = str(d.get('status', 'pending')).strip().lower()
            if status not in VALID_TASK_STATUSES:
                status = 'pending'

            all_tasks.append({'id': item_id, 'content': content, 'status': status})

        await Chats.update_chat_tasks_by_id(__chat_id__, all_tasks)
        await _emit_tasks(__event_emitter__, all_tasks)

        return json.dumps(
            {'tasks': all_tasks, 'summary': _task_summary(all_tasks)},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'tasks error: {e}')
        return json.dumps({'error': str(e)})


async def update_task(
    id: str,
    status: str = 'completed',
    __chat_id__: str = None,
    __message_id__: str = None,
    __event_emitter__: callable = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Mark a single task as completed, in_progress, pending, or cancelled.
    Call this after finishing each step. You MUST call this for every
    task, including the very last one.

    :param id: The task ID to update
    :param status: New status: completed, in_progress, pending, or cancelled (default: completed)
    :return: JSON with the updated task list and summary counts
    """
    if __chat_id__ is None:
        return json.dumps({'error': 'Chat context not available'})

    try:
        status = status.strip().lower()
        if status not in VALID_TASK_STATUSES:
            return json.dumps(
                {'error': f'Invalid status: {status}. Must be one of: {", ".join(sorted(VALID_TASK_STATUSES))}'}
            )

        all_tasks = await Chats.get_chat_tasks_by_id(__chat_id__)

        found = False
        for task in all_tasks:
            if task['id'] == id:
                task['status'] = status
                found = True
                break

        if not found:
            return json.dumps({'error': f'Task with id "{id}" not found'})

        await Chats.update_chat_tasks_by_id(__chat_id__, all_tasks)
        await _emit_tasks(__event_emitter__, all_tasks)

        return json.dumps(
            {'tasks': all_tasks, 'summary': _task_summary(all_tasks)},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_task_status error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# AUTOMATION TOOLS
# =============================================================================


async def create_automation(
    name: str,
    prompt: str,
    rrule: str,
    __request__: Request = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Create a scheduled automation that runs a prompt on a recurring or one-time schedule.
    Use this when the user wants to schedule a task to run automatically.
    The automation will use the current chat model.

    The rrule parameter must be a valid iCalendar RRULE string. Common examples:
    - Every day at 9am: "DTSTART:20250101T090000\\nRRULE:FREQ=DAILY"
    - Every Monday at 8am: "DTSTART:20250106T080000\\nRRULE:FREQ=WEEKLY;BYDAY=MO"
    - Every hour: "RRULE:FREQ=HOURLY;INTERVAL=1"
    - Every 30 minutes: "RRULE:FREQ=MINUTELY;INTERVAL=30"
    - Once at a specific time: "DTSTART:20250415T140000\\nRRULE:FREQ=DAILY;COUNT=1"
    - First day of every month: "DTSTART:20250101T090000\\nRRULE:FREQ=MONTHLY;BYMONTHDAY=1"

    The DTSTART time should reflect the desired execution time. Use COUNT=1 for one-time automations.

    :param name: A short descriptive name for the automation
    :param prompt: The prompt/instructions to execute on each run
    :param rrule: An iCalendar RRULE string defining the schedule
    :return: JSON with the created automation details including id, next scheduled runs
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import Automations, AutomationForm, AutomationData
        from open_webui.models.users import Users
        from open_webui.utils.automations import validate_rrule, next_run_ns, next_n_runs_ns

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)
        if not user:
            return json.dumps({'error': 'User not found'})

        # Always use the calling model for the automation
        model_id = (__metadata__ or {}).get('model_id')
        if not model_id:
            return json.dumps({'error': 'Could not detect current model'})

        # Validate the RRULE
        try:
            validate_rrule(rrule, tz=user.timezone)
        except ValueError as e:
            return json.dumps({'error': f'Invalid schedule: {e}'})

        tz = user.timezone
        form = AutomationForm(
            name=name,
            data=AutomationData(
                prompt=prompt,
                model_id=model_id,
                rrule=rrule,
            ),
            is_active=True,
        )

        automation = await Automations.insert(user_id, form, next_run_ns(rrule, tz=tz))

        return json.dumps(
            {
                'status': 'success',
                'id': automation.id,
                'name': automation.name,
                'model_id': model_id,
                'is_active': automation.is_active,
                'next_runs': next_n_runs_ns(rrule, tz=tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'create_automation error: {e}')
        return json.dumps({'error': str(e)})


async def update_automation(
    automation_id: str,
    name: Optional[str] = None,
    prompt: Optional[str] = None,
    rrule: Optional[str] = None,
    model_id: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update an existing automation. Only the provided fields are changed; omitted fields stay the same.

    :param automation_id: The ID of the automation to update
    :param name: New name for the automation (optional)
    :param prompt: New prompt/instructions (optional)
    :param rrule: New iCalendar RRULE schedule string (optional). See create_automation for format examples.
    :param model_id: New model ID to use (optional)
    :return: JSON with the updated automation details
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import Automations, AutomationForm, AutomationData
        from open_webui.models.users import Users
        from open_webui.utils.automations import validate_rrule, next_run_ns, next_n_runs_ns

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)

        automation = await Automations.get_by_id(automation_id)
        if not automation:
            return json.dumps({'error': 'Automation not found'})
        if automation.user_id != user_id:
            return json.dumps({'error': 'Access denied'})

        # Merge provided fields with existing values
        new_name = name if name is not None else automation.name
        new_prompt = prompt if prompt is not None else automation.data.get('prompt', '')
        new_model_id = model_id if model_id is not None else automation.data.get('model_id', '')
        new_rrule = rrule if rrule is not None else automation.data.get('rrule', '')

        # Validate RRULE if changed
        if rrule is not None:
            try:
                validate_rrule(new_rrule, tz=user.timezone if user else None)
            except ValueError as e:
                return json.dumps({'error': f'Invalid schedule: {e}'})

        tz = user.timezone if user else None
        form = AutomationForm(
            name=new_name,
            data=AutomationData(
                prompt=new_prompt,
                model_id=new_model_id,
                rrule=new_rrule,
            ),
            is_active=automation.is_active,
        )

        updated = await Automations.update(automation_id, form, next_run_ns(new_rrule, tz=tz))

        return json.dumps(
            {
                'status': 'success',
                'id': updated.id,
                'name': updated.name,
                'model_id': new_model_id,
                'is_active': updated.is_active,
                'next_runs': next_n_runs_ns(new_rrule, tz=tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_automation error: {e}')
        return json.dumps({'error': str(e)})


async def list_automations(
    status: Optional[str] = None,
    count: int = 10,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List the user's scheduled automations.

    :param status: Filter by status: "active", "paused", or omit for all
    :param count: Maximum number of automations to return (default: 10)
    :return: JSON list of automations with id, name, prompt snippet, schedule, status, and next runs
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_n_runs_ns

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)

        result = await Automations.search_automations(
            user_id=user_id,
            status=status,
            skip=0,
            limit=count,
        )

        automations = []
        for item in result.items:
            rrule = item.data.get('rrule', '')
            prompt_text = item.data.get('prompt', '')
            snippet = prompt_text[:100] + ('...' if len(prompt_text) > 100 else '')

            automations.append(
                {
                    'id': item.id,
                    'name': item.name,
                    'prompt_snippet': snippet,
                    'model_id': item.data.get('model_id', ''),
                    'rrule': rrule,
                    'is_active': item.is_active,
                    'last_run_at': item.last_run_at,
                    'next_runs': next_n_runs_ns(rrule, tz=user.timezone if user else None),
                }
            )

        return json.dumps(
            {'automations': automations, 'total': result.total},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'list_automations error: {e}')
        return json.dumps({'error': str(e)})


async def toggle_automation(
    automation_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Pause or resume a scheduled automation. If active, it will be paused. If paused, it will be resumed.

    :param automation_id: The ID of the automation to toggle
    :return: JSON with the updated automation status
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_run_ns

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)

        automation = await Automations.get_by_id(automation_id)
        if not automation:
            return json.dumps({'error': 'Automation not found'})
        if automation.user_id != user_id:
            return json.dumps({'error': 'Access denied'})

        rrule = automation.data.get('rrule', '')
        toggled = await Automations.toggle(
            automation_id,
            next_run_ns(rrule, tz=user.timezone if user else None),
        )

        return json.dumps(
            {
                'status': 'success',
                'id': toggled.id,
                'name': toggled.name,
                'is_active': toggled.is_active,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'toggle_automation error: {e}')
        return json.dumps({'error': str(e)})


async def delete_automation(
    automation_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete a scheduled automation and all its run history.

    :param automation_id: The ID of the automation to delete
    :return: JSON confirming the automation was deleted
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import Automations, AutomationRuns

        user_id = __user__.get('id')

        automation = await Automations.get_by_id(automation_id)
        if not automation:
            return json.dumps({'error': 'Automation not found'})
        if automation.user_id != user_id:
            return json.dumps({'error': 'Access denied'})

        name = automation.name
        await AutomationRuns.delete_by_automation(automation_id)
        await Automations.delete(automation_id)

        return json.dumps(
            {
                'status': 'success',
                'message': f'Automation "{name}" deleted',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_automation error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# CALENDAR TOOLS
# =============================================================================


def _get_user_tz(user_dict: dict):
    """Get the user's timezone as a ZoneInfo, falling back to UTC."""
    from zoneinfo import ZoneInfo

    tz_name = None
    if user_dict:
        tz_name = user_dict.get('timezone')
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    return ZoneInfo('UTC')


def _dt_to_ns(dt_str: str, tz) -> int:
    """Convert a datetime string to nanoseconds since epoch, interpreting in the given timezone."""
    from datetime import datetime

    dt = datetime.fromisoformat(dt_str)
    # If naive (no timezone info), localize to user's timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return int(dt.timestamp() * 1_000) * 1_000_000


def _ns_to_dt(ns: int, tz) -> str:
    """Convert nanoseconds since epoch to a datetime string in the given timezone."""
    from datetime import datetime

    seconds = ns / 1_000_000_000
    dt = datetime.fromtimestamp(seconds, tz=tz)
    return dt.strftime('%Y-%m-%d %H:%M')


def _event_to_dict(event, tz) -> dict:
    """Convert a calendar event model to a human-friendly dict with local timestamps."""
    return {
        'id': event.id,
        'calendar_id': event.calendar_id,
        'title': event.title,
        'description': event.description or '',
        'start': _ns_to_dt(event.start_at, tz),
        'end': _ns_to_dt(event.end_at, tz) if event.end_at else None,
        'all_day': event.all_day,
        'location': event.location or '',
        'color': event.color,
        'is_cancelled': event.is_cancelled,
    }


async def search_calendar_events(
    query: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    count: int = 10,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search calendar events by text and/or date range.
    Returns matching events across all accessible calendars.

    :param query: Search text to match against event title, description, or location (optional)
    :param start: Only return events starting at or after this datetime, e.g. "2026-04-20 00:00" (optional)
    :param end: Only return events starting before this datetime, e.g. "2026-04-27 00:00" (optional)
    :param count: Maximum number of events to return (default: 10)
    :return: JSON list of matching events with id, title, description, start, end, calendar_id, location
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import CalendarEvents

        user_id = __user__.get('id')
        tz = _get_user_tz(__user__)

        if isinstance(count, str):
            try:
                count = int(count)
            except ValueError:
                count = 10

        if start or end:
            # Date range query — use get_events_by_range
            try:
                start_ns = _dt_to_ns(start, tz) if start else 0
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid start datetime: {e}'})

            try:
                end_ns = (
                    _dt_to_ns(end, tz)
                    if end
                    else int(time.time() * 1_000) * 1_000_000 + 365 * 86400 * 1_000_000_000_000
                )
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid end datetime: {e}'})

            items = await CalendarEvents.get_events_by_range(
                user_id=user_id,
                start=start_ns,
                end=end_ns,
            )

            # Apply text filter if query is also provided
            if query:
                q = query.lower()
                items = [
                    e
                    for e in items
                    if q in (e.title or '').lower()
                    or q in (e.description or '').lower()
                    or q in (e.location or '').lower()
                ]

            events = [_event_to_dict(item, tz) for item in items[:count]]
            return json.dumps(
                {'events': events, 'total': len(items)},
                ensure_ascii=False,
            )
        else:
            # Text-only search
            result = await CalendarEvents.search_events(
                user_id=user_id,
                query=query,
                skip=0,
                limit=count,
            )

            events = [_event_to_dict(item, tz) for item in result.items]
            return json.dumps(
                {'events': events, 'total': result.total},
                ensure_ascii=False,
            )
    except Exception as e:
        log.exception(f'search_calendar_events error: {e}')
        return json.dumps({'error': str(e)})


async def create_calendar_event(
    title: str,
    start: str,
    end: Optional[str] = None,
    description: Optional[str] = None,
    calendar_id: Optional[str] = None,
    all_day: bool = False,
    location: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a new calendar event. If no calendar_id is provided, the event is
    added to the user's default calendar.

    :param title: Event title
    :param start: Start datetime string in your local time (e.g. "2026-04-20 09:00" or "2026-04-20T09:00:00")
    :param end: End datetime string in your local time (optional, omit for point-in-time events)
    :param description: Event description (optional)
    :param calendar_id: Target calendar ID (optional, uses default calendar if omitted)
    :param all_day: Whether this is an all-day event (default: false)
    :param location: Event location (optional)
    :return: JSON with the created event details including id
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import Calendars, CalendarEvents, CalendarEventForm

        user_id = __user__.get('id')

        # Resolve calendar_id: use provided, or fall back to default
        if not calendar_id:
            calendars = await Calendars.get_calendars_by_user(user_id)
            default_cal = next((c for c in calendars if c.is_default), None)
            if not default_cal and calendars:
                default_cal = calendars[0]
            if not default_cal:
                return json.dumps({'error': 'No calendars found. Cannot create event.'})
            calendar_id = default_cal.id

        # Verify access
        cal = await Calendars.get_calendar_by_id(calendar_id)
        if not cal:
            return json.dumps({'error': 'Calendar not found'})
        if cal.user_id != user_id and __user__.get('role') != 'admin':
            from open_webui.models.access_grants import AccessGrants
            from open_webui.models.groups import Groups

            user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='calendar',
                resource_id=cal.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied to this calendar'})

        # Coerce boolean from LLM
        if isinstance(all_day, str):
            all_day = all_day.lower() in ('true', '1', 'yes')

        # Convert datetime strings to nanoseconds using user's timezone
        tz = _get_user_tz(__user__)
        try:
            start_ns = _dt_to_ns(start, tz)
        except (ValueError, TypeError) as e:
            return json.dumps({'error': f'Invalid start datetime: {e}. Use format like "2026-04-20 09:00"'})

        end_ns = None
        if end:
            try:
                end_ns = _dt_to_ns(end, tz)
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid end datetime: {e}. Use format like "2026-04-20 10:00"'})
        elif not all_day:
            # Default to 1 hour duration
            end_ns = start_ns + 3_600_000_000_000

        form = CalendarEventForm(
            calendar_id=calendar_id,
            title=title,
            description=description,
            start_at=start_ns,
            end_at=end_ns,
            all_day=all_day,
            location=location,
        )

        event = await CalendarEvents.insert_new_event(user_id, form)
        if not event:
            return json.dumps({'error': 'Failed to create event'})

        return json.dumps(
            {
                'status': 'success',
                **_event_to_dict(event, tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'create_calendar_event error: {e}')
        return json.dumps({'error': str(e)})


async def update_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    all_day: Optional[bool] = None,
    location: Optional[str] = None,
    is_cancelled: Optional[bool] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update an existing calendar event. Only provided fields are changed;
    omitted fields stay the same.

    :param event_id: The ID of the event to update
    :param title: New event title (optional)
    :param description: New event description (optional)
    :param start: New start datetime string in your local time, e.g. "2026-04-20 09:00" (optional)
    :param end: New end datetime string in your local time (optional)
    :param all_day: Whether this is an all-day event (optional)
    :param location: New event location (optional)
    :param is_cancelled: Set to true to cancel the event (optional)
    :return: JSON with the updated event details
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import Calendars, CalendarEvents, CalendarEventUpdateForm
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.groups import Groups

        user_id = __user__.get('id')

        event = await CalendarEvents.get_event_by_id(event_id)
        if not event:
            return json.dumps({'error': 'Event not found'})

        # Check write access to the event's calendar
        cal = await Calendars.get_calendar_by_id(event.calendar_id)
        if cal and cal.user_id != user_id and __user__.get('role') != 'admin':
            user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='calendar',
                resource_id=cal.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied'})

        # Coerce boolean strings from LLM
        if isinstance(all_day, str):
            all_day = all_day.lower() in ('true', '1', 'yes')
        if isinstance(is_cancelled, str):
            is_cancelled = is_cancelled.lower() in ('true', '1', 'yes')

        # Convert datetime strings to nanoseconds using user's timezone
        tz = _get_user_tz(__user__)
        start_ns = None
        if start is not None:
            try:
                start_ns = _dt_to_ns(start, tz)
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid start datetime: {e}'})

        end_ns = None
        if end is not None:
            try:
                end_ns = _dt_to_ns(end, tz)
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid end datetime: {e}'})

        form = CalendarEventUpdateForm(
            title=title,
            description=description,
            start_at=start_ns,
            end_at=end_ns,
            all_day=all_day,
            location=location,
            is_cancelled=is_cancelled,
        )

        updated = await CalendarEvents.update_event_by_id(event_id, form)
        if not updated:
            return json.dumps({'error': 'Failed to update event'})

        return json.dumps(
            {
                'status': 'success',
                **_event_to_dict(updated, tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_calendar_event error: {e}')
        return json.dumps({'error': str(e)})


async def delete_calendar_event(
    event_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete a calendar event permanently.

    :param event_id: The ID of the event to delete
    :return: JSON confirming the event was deleted
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import Calendars, CalendarEvents
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.groups import Groups

        user_id = __user__.get('id')

        event = await CalendarEvents.get_event_by_id(event_id)
        if not event:
            return json.dumps({'error': 'Event not found'})

        # Check write access
        cal = await Calendars.get_calendar_by_id(event.calendar_id)
        if cal and cal.user_id != user_id and __user__.get('role') != 'admin':
            user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='calendar',
                resource_id=cal.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied'})

        title = event.title
        result = await CalendarEvents.delete_event_by_id(event_id)
        if not result:
            return json.dumps({'error': 'Failed to delete event'})

        return json.dumps(
            {
                'status': 'success',
                'message': f'Event "{title}" deleted',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_calendar_event error: {e}')
        return json.dumps({'error': str(e)})
