"""Access and optional source context for comments; never returns resource contents."""

import hashlib
from types import SimpleNamespace

from fastapi import HTTPException
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.models.access_grants import AccessGrants
from open_webui.models.config import Config
from open_webui.utils.access_control import has_permission
from sqlalchemy import select


def resource_models():
    from open_webui.models.chats import Chat
    from open_webui.models.knowledge import Knowledge
    from open_webui.models.models import Model
    from open_webui.models.notes import Note
    from open_webui.models.prompts import Prompt
    from open_webui.models.skills import Skill
    from open_webui.models.tools import Tool

    return dict(
        model=Model,
        knowledge=Knowledge,
        prompt=Prompt,
        skill=Skill,
        tool=Tool,
        note=Note,
        chat=Chat,
    )


async def provider_comment_resource(resource_id, user, request):
    # Unconfigured provider models are visible only to admins, as in the catalog.
    if user.role != 'admin' or request is None:
        raise HTTPException(404, 'Resource not found')
    providers = getattr(request.app.state, 'BASE_MODELS', [])
    if not providers:
        from open_webui.utils.models import get_all_models

        await get_all_models(request, user=user)
        providers = getattr(request.app.state, 'BASE_MODELS', [])
    provider = next((item for item in providers if item.get('id') == resource_id), None)
    if provider is None:
        raise HTTPException(404, 'Resource not found')
    return SimpleNamespace(id=resource_id, name=provider.get('name') or resource_id, user_id=None)


async def comment_resource(resource_type, resource_id, user, db, *, lock=False, request=None):
    if not await Config.get('comments.enable'):
        raise HTTPException(403, 'Comments are disabled')
    model = resource_models().get(resource_type)
    if model is None or user.role not in {'user', 'admin'}:
        raise HTTPException(404, 'Resource not found')
    query = select(model).where(model.id == resource_id)
    resource = await db.scalar(query.with_for_update() if lock else query)
    if resource is None:
        if resource_type == 'model':
            return await provider_comment_resource(resource_id, user, request)
        raise HTTPException(404, 'Resource not found')
    allowed = resource.user_id == user.id
    if resource_type == 'chat':
        from open_webui.models.chats import Chats

        allowed = await Chats.get_accessible_chat_by_id(resource_id, user, db=db, chat=resource) is not None
    else:
        if resource_type == 'note':
            if not await Config.get('notes.enable') or (
                user.role != 'admin'
                and not await has_permission(user.id, 'features.notes', await Config.get('user.permissions'), db=db)
            ):
                raise HTTPException(404, 'Resource not found')
        allowed = (
            allowed
            or (user.role == 'admin' and (resource_type == 'note' or BYPASS_ADMIN_ACCESS_CONTROL))
            or await AccessGrants.has_access(user.id, resource_type, resource_id, 'read', db=db)
        )
    if not allowed:
        raise HTTPException(404, 'Resource not found')
    return resource


async def effective_comment_context(resource_type, resource_id, user, db, *, request=None):
    resource = await comment_resource(resource_type, resource_id, user, db, request=request)
    return {
        'resource_type': resource_type,
        'resource_id': resource_id,
        'title': getattr(resource, 'title', None) or getattr(resource, 'name', None) or resource_id,
    }


def note_comment_text(content):
    def text(node):
        if not isinstance(node, dict):
            return ''
        if node.get('type') == 'text':
            return node.get('text', '')
        return ''.join(text(child) for child in node.get('content', []))

    return text(content['json']) if isinstance(content.get('json'), dict) else content.get('md') or ''


def validate_comment_target(resource_type, resource, form):
    if bool(form.target_type) != bool(form.target_id) or (form.anchor and not form.target_id):
        raise HTTPException(422, 'A selection requires a target')
    if not form.target_id:
        return
    if resource_type == 'note' and form.target_type == 'note_page':
        from open_webui.models.notes import normalize_pages

        target = next((p for p in normalize_pages(resource.data)['pages'] if p['id'] == form.target_id), None)
    elif resource_type == 'chat' and form.target_type == 'chat_message':
        target = (resource.chat.get('history', {}).get('messages') or {}).get(form.target_id)
        if target and target.get('role') == 'assistant' and target.get('done') is False:
            raise HTTPException(409, 'Wait for the message to finish')
    else:
        target = None
    if target is None:
        raise HTTPException(404, 'Comment target not found')
    if form.anchor and (
        form.anchor.end <= form.anchor.start or form.anchor.end - form.anchor.start != len(form.anchor.quote)
    ):
        raise HTTPException(422, 'Invalid text selection')

    if form.anchor:
        source = comment_anchor_source(resource_type, target, form)
        if not isinstance(source, str) or hashlib.sha256(source.encode()).hexdigest() != form.anchor.content_hash:
            raise HTTPException(409, 'Content changed. Select the passage again or leave a general comment.')


def comment_anchor_source(resource_type, target, form):
    if resource_type == 'note':
        if form.anchor.surface_id != form.target_id:
            raise HTTPException(422, 'Invalid page selection')
        source = note_comment_text(target.get('content') or {})
    elif form.anchor.surface_id == 'content':
        source = target.get('content') or ''
    else:
        matches = [
            item
            for index, item in enumerate(target.get('output') or [])
            if form.anchor.surface_id
            == (item.get('id') or f'{"message" if item.get("type") == "message" else "output"}-{index}')
            and item.get('type')
            not in {
                'reasoning',
                'function_call',
                'open_webui:code_interpreter',
                'web_search_call',
                'file_search_call',
                'computer_call',
            }
        ]
        if len(matches) != 1:
            raise HTTPException(409, 'Message output changed. Select the passage again.')
        source = ''.join(
            part.get('text', '') for part in matches[0].get('content', []) if isinstance(part.get('text'), str)
        )
    return source
