import difflib
import json
import logging
import mimetypes
import re
import zipfile
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.skill_history import SkillHistories
from open_webui.models.skills import (
    SkillAccessListResponse,
    SkillAccessResponse,
    SkillDetailResponse,
    SkillForm,
    SkillModel,
    SkillResponse,
    Skills,
    SkillUserResponse,
    get_skill_snapshot,
)
from open_webui.utils.access_control import filter_allowed_access_grants, has_permission
from open_webui.utils.auth import get_verified_user
from open_webui.utils.skill_files import (
    MAX_IMPORT_BYTES,
    file_bytes,
    file_summaries,
    parse_import,
    zip_export,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

PAGE_ITEM_COUNT = 30

router = APIRouter()


############################
# GetSkills
############################


@router.get('/', response_model=list[SkillUserResponse])
async def get_skills(
    request: Request,
    query: Optional[str] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL:
        skills = await Skills.get_skills(db=db)
    else:
        skills = await Skills.get_skills(db=db, user_id=user.id)

    if query:
        q = query.casefold()
        skills = [skill for skill in skills if q in (skill.name or '').casefold()]

    return skills


############################
# GetSkillList
############################


@router.get('/list', response_model=SkillAccessListResponse)
async def get_skill_list(
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if view_option:
        filter['view_option'] = view_option
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction

    is_bypass_admin = user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL
    user_group_ids = {
        group.id for group in await Groups.get_groups_by_member_id(user.id, db=db, include_inherited=True)
    }

    if not is_bypass_admin:
        filter['group_ids'] = user_group_ids
        filter['user_id'] = user.id

    result = await Skills.search_skills(user.id, filter=filter, skip=skip, limit=limit, db=db)

    writable_skill_ids = await AccessGrants.get_accessible_resource_ids(
        user_id=user.id,
        resource_type='skill',
        resource_ids=[skill.id for skill in result.items],
        permission='write',
        user_group_ids=user_group_ids,
        db=db,
    )

    return SkillAccessListResponse(
        items=[
            SkillAccessResponse(
                **skill.model_dump(),
                write_access=(is_bypass_admin or user.id == skill.user_id or skill.id in writable_skill_ids),
            )
            for skill in result.items
        ],
        total=result.total,
    )


############################
# ExportSkills
############################


async def authorized_skill(id, user, permission='read', db=None):
    skill = await Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(404, 'Skill not found')
    if not (
        (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
        or skill.user_id == user.id
        or await AccessGrants.has_access(
            user_id=user.id, resource_type='skill', resource_id=id, permission=permission, db=db
        )
    ):
        raise HTTPException(403, 'Access denied')
    return skill


async def selected_history(skill, version_id=None, db=None):
    entry = await SkillHistories.get_history_by_id(skill.id, version_id or skill.version_id, db=db)
    if not entry:
        raise HTTPException(404, 'Skill version not found')
    return entry


@router.get('/export')
async def export_skills(
    request: Request,
    format: str = 'json',
    ids: list[str] | None = Query(None),
    version_id: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'workspace.skills_export', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(403, 'Export permission required')
    if version_id and (not ids or len(ids) != 1):
        raise HTTPException(400, 'Select one skill to export a historical version')
    skills = (
        [await authorized_skill(id, user, db=db) for id in ids]
        if ids is not None
        else await Skills.get_skills(
            user_id=None if user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL else user.id, db=db
        )
    )
    packages = []
    for skill in skills:
        snapshot = await get_skill_snapshot(skill, version_id, db)
        packages.append(
            {
                'id': skill.id,
                **{key: snapshot[key] for key in ('name', 'description', 'meta')},
                'files': snapshot['data']['files'],
                'is_active': skill.is_active,
            }
        )
    try:
        if format == 'zip':
            return Response(
                zip_export(packages),
                media_type='application/zip',
                headers={'Content-Disposition': 'attachment; filename="skills.zip"'},
            )
        if format != 'json':
            raise ValueError('Export format must be json or zip')
        return packages[0] if ids and len(ids) == 1 else packages
    except ValueError as error:
        raise HTTPException(400, str(error))


############################
# CreateNewSkill
############################


@router.post('/create', response_model=Optional[SkillResponse])
async def create_new_skill(
    request: Request,
    form_data: SkillForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not (
        await has_permission(user.id, 'workspace.skills', await Config.get('user.permissions'), db=db)
        or await has_permission(user.id, 'workspace.skills_import', await Config.get('user.permissions'), db=db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    form_data.id = form_data.id.lower().replace(' ', '-')

    # The id goes into /id/{id}/... paths, so anything outside the slug charset is unreachable once stored.
    if not re.fullmatch(r'[a-z0-9_-]+', form_data.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Invalid skill ID'),
        )

    existing = await Skills.get_skill_by_id(form_data.id, db=db)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )

    if await Skills.get_skill_by_name(form_data.name, db=db):
        raise HTTPException(409, 'A skill with this name already exists')

    # Strip public/user grants the requesting user is not permitted to assign
    # (matches the channel/notes/calendar pattern). Without this, a user with
    # workspace.skills permission could attach principal_id='*' read/write
    # grants in the create payload, bypassing the sharing.public_skills gate
    # that the dedicated /access/update endpoint already enforces.
    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_skills',
    )

    try:
        skill = await Skills.insert_new_skill(user.id, form_data, db=db)
        if skill:
            await publish_event(
                request,
                EVENTS.SKILL_CREATED,
                actor=user,
                subject_id=skill.id,
                data={'name': skill.name},
            )
            return skill
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error creating skill'),
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f'Failed to create skill: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error creating skill'),
        )


############################
# GetSkillById
############################


@router.get('/id/{id}', response_model=Optional[SkillDetailResponse])
async def get_skill_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    skill = await Skills.get_skill_by_id(id, db=db)

    if skill:
        if (
            (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
            or skill.user_id == user.id
            or await AccessGrants.has_access(
                user_id=user.id,
                resource_type='skill',
                resource_id=skill.id,
                permission='read',
                db=db,
            )
        ):
            return SkillDetailResponse(
                **skill.model_dump(),
                write_access=(
                    (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
                    or user.id == skill.user_id
                    or await AccessGrants.has_access(
                        user_id=user.id,
                        resource_type='skill',
                        resource_id=skill.id,
                        permission='write',
                        db=db,
                    )
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateSkillById
############################


@router.post('/id/{id}/update', response_model=Optional[SkillModel])
async def update_skill_by_id(
    request: Request,
    id: str,
    form_data: SkillForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        skill.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='skill',
            resource_id=skill.id,
            permission='write',
            db=db,
        )
        and not (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    # Strip public/user grants the requesting user is not permitted to assign
    # (matches the channel/notes/calendar pattern). The access check above only
    # restricts WHO can write to the skill; this filter restricts WHICH grants
    # they may set, so a non-admin owner cannot make their own skill publicly
    # readable/writable without sharing.public_skills permission.
    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_skills',
    )

    try:
        updated = {
            **form_data.model_dump(exclude={'id'}, exclude_unset=True),
        }

        skill = await Skills.update_skill_by_id(id, updated, db=db, user_id=user.id)

        if skill:
            await publish_event(
                request,
                EVENTS.SKILL_UPDATED,
                actor=user,
                subject_id=skill.id,
                data={'name': skill.name},
            )
            return skill
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating skill'),
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating skill'),
        )


############################
# UpdateSkillAccessById
############################


class SkillAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/id/{id}/access/update', response_model=Optional[SkillModel])
async def update_skill_access_by_id(
    request: Request,
    id: str,
    form_data: SkillAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        skill.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='skill',
            resource_id=skill.id,
            permission='write',
            db=db,
        )
        and not (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_skills',
    )

    await AccessGrants.set_access_grants('skill', id, form_data.access_grants, db=db)

    skill = await Skills.get_skill_by_id(id, db=db)
    await publish_event(
        request,
        EVENTS.SKILL_UPDATED,
        actor=user,
        subject_id=id,
        data={'access_updated': True, 'name': skill.name if skill else None},
    )
    return skill


############################
# ToggleSkillById
############################


@router.post('/id/{id}/toggle', response_model=Optional[SkillModel])
async def toggle_skill_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await Skills.get_skill_by_id(id, db=db)
    if skill:
        if (
            (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
            or skill.user_id == user.id
            or await AccessGrants.has_access(
                user_id=user.id,
                resource_type='skill',
                resource_id=skill.id,
                permission='write',
                db=db,
            )
        ):
            skill = await Skills.toggle_skill_by_id(id, db=db)

            if skill:
                await publish_event(
                    request,
                    EVENTS.SKILL_ENABLED if skill.is_active else EVENTS.SKILL_DISABLED,
                    actor=user,
                    subject_id=skill.id,
                    data={'name': skill.name},
                )
                return skill
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error toggling skill'),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# DeleteSkillById
############################


@router.delete('/id/{id}/delete', response_model=bool)
async def delete_skill_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        skill.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='skill',
            resource_id=skill.id,
            permission='write',
            db=db,
        )
        and not (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = await Skills.delete_skill_by_id(id, db=db)
    if result:
        await publish_event(
            request,
            EVENTS.SKILL_DELETED,
            actor=user,
            subject_id=id,
            data={'name': skill.name},
        )
    return result


@router.get('/id/{id}/files')
async def get_skill_files(
    id: str,
    version_id: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await authorized_skill(id, user, db=db)
    snapshot = await get_skill_snapshot(skill, version_id, db)
    return {
        'version_id': version_id or skill.version_id,
        'files': file_summaries(snapshot['data']['files']),
    }


@router.get('/id/{id}/files/content')
async def get_skill_file(
    id: str, path: str, version_id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    skill = await authorized_skill(id, user, db=db)
    snapshot = await get_skill_snapshot(skill, version_id, db)
    file = next((f for f in snapshot['data']['files'] if f['path'] == path), None)
    if not file:
        raise HTTPException(404, 'File not found')
    return Response(
        file_bytes(file),
        media_type=mimetypes.guess_type(path)[0] or 'application/octet-stream',
        headers={
            'Content-Disposition': "attachment; filename*=UTF-8''" + quote(path.rsplit('/', 1)[-1], safe=''),
            'X-Content-Type-Options': 'nosniff',
            'Content-Security-Policy': "default-src 'none'; sandbox",
            'Cache-Control': 'private, no-store',
        },
    )


@router.get('/id/{id}/history')
async def get_skill_history(
    id: str, page: int = 1, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await authorized_skill(id, user, db=db)
    return await SkillHistories.get_history_by_skill_id(id, page, db)


@router.get('/id/{id}/history/diff')
async def diff_skill_history(
    id: str, from_id: str, to_id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    skill = await authorized_skill(id, user, db=db)
    before, after = (
        (await selected_history(skill, from_id, db)).snapshot,
        (await selected_history(skill, to_id, db)).snapshot,
    )
    a, b = ({f['path']: f for f in snapshot['data']['files']} for snapshot in (before, after))
    return {
        'metadata': {
            k: {'before': before.get(k), 'after': after.get(k)}
            for k in ('name', 'description', 'meta')
            if before.get(k) != after.get(k)
        },
        'files': [
            {
                'path': p,
                'status': 'added' if p not in a else 'deleted' if p not in b else 'modified',
                'binary': bool(a.get(p, {}).get('encoding') or b.get(p, {}).get('encoding')),
            }
            for p in sorted(a.keys() | b.keys())
            if a.get(p) != b.get(p)
        ],
    }


@router.get('/id/{id}/history/diff/file')
async def diff_skill_file(
    id: str,
    from_id: str,
    to_id: str,
    path: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await authorized_skill(id, user, db=db)
    entries = [await selected_history(skill, version, db) for version in (from_id, to_id)]
    files = [next((f for f in entry.snapshot['data']['files'] if f['path'] == path), None) for entry in entries]
    if not any(files):
        raise HTTPException(404, 'File not found')
    if any(f and f.get('encoding') for f in files):
        return {'binary': True}
    before, after = ((file or {}).get('content', '') for file in files)
    diff = '\n'.join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile=f'{from_id[:7]}/{path}',
            tofile=f'{to_id[:7]}/{path}',
            lineterm='',
        )
    )
    return {
        'binary': False,
        'diff': diff,
        'line_endings_only': not diff and before != after,
    }


@router.get('/id/{id}/history/{history_id}')
async def get_skill_history_entry(
    id: str, history_id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    skill = await authorized_skill(id, user, db=db)
    entry = await selected_history(skill, history_id, db)
    snapshot = entry.snapshot
    return {
        **entry.model_dump(exclude={'snapshot'}),
        'snapshot': {
            **{k: v for k, v in snapshot.items() if k != 'data'},
            'data': {'files': file_summaries(snapshot['data']['files'])},
        },
    }


class RestoreSkillForm(BaseModel):
    expected_version_id: str
    commit_message: str | None = None


@router.post('/id/{id}/history/{history_id}/restore')
async def restore_skill(
    id: str,
    history_id: str,
    request: Request,
    form_data: RestoreSkillForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await authorized_skill(id, user, 'write', db)
    entry = await selected_history(skill, history_id, db)
    result = await Skills.update_skill_by_id(
        id, {**entry.snapshot, **form_data.model_dump(), '_restore': True}, db=db, user_id=user.id
    )
    await publish_event(request, EVENTS.SKILL_UPDATED, actor=user, subject_id=id, data={'name': result.name})
    return result


class CloneSkillForm(BaseModel):
    id: str
    name: str
    version_id: str | None = None


@router.post('/id/{id}/clone')
async def clone_skill(
    id: str,
    request: Request,
    form_data: CloneSkillForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await authorized_skill(id, user, db=db)
    snapshot = await get_skill_snapshot(skill, form_data.version_id, db)
    data = {
        **snapshot,
        'id': form_data.id,
        'name': form_data.name,
        'is_active': skill.is_active,
        'access_grants': [],
    }
    return await create_new_skill(request, SkillForm(**data), user, db)


async def read_import(files: list[UploadFile]):
    packages, total = [], 0
    try:
        if len(files) > 10000:
            raise ValueError('Too many uploaded files')
        folder_files = []
        for file in files:
            data = await file.read(MAX_IMPORT_BYTES - total + 1)
            total += len(data)
            if total > MAX_IMPORT_BYTES:
                raise ValueError('Import exceeds 200 MiB')
            if '/' in (file.filename or ''):
                from open_webui.utils.skill_files import encode_file, validate_path

                folder_files.append(encode_file(validate_path(file.filename), data))
            else:
                packages.extend(parse_import(data, file.filename or ''))
        if folder_files:
            roots = sorted(f['path'][: -len('SKILL.md')] for f in folder_files if f['path'].endswith('/SKILL.md'))
            roots = [root for root in roots if not any(root != parent and root.startswith(parent) for parent in roots)]
            if not roots:
                raise ValueError('Select a folder containing one or more non-nested skills')
            if any(not any(f['path'].startswith(root) for root in roots) for f in folder_files):
                raise ValueError('Files outside skill directories')
            for root in roots:
                package = {
                    'files': [{**f, 'path': f['path'][len(root) :]} for f in folder_files if f['path'].startswith(root)]
                }
                packages.extend(parse_import(json.dumps(package).encode(), 'skill.json'))
        if sum(len(file_bytes(f)) for p in packages for f in p['files']) > MAX_IMPORT_BYTES:
            raise ValueError('Import exceeds 200 MiB decoded')
        return packages
    except (ValueError, KeyError, TypeError, UnicodeError, zipfile.BadZipFile) as error:
        raise HTTPException(400, str(error))


async def require_import(user, db):
    if user.role != 'admin' and not await has_permission(
        user.id, 'workspace.skills_import', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(403, 'Import permission required')


@router.post('/import/preview')
async def preview_skill_import(
    files: list[UploadFile] = File(...), user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await require_import(user, db)
    packages = await read_import(files)
    results = []
    for index, package in enumerate(packages):
        existing = await Skills.get_skill_by_id(package['id'], db=db)
        writable = False
        if existing:
            try:
                await authorized_skill(existing.id, user, 'write', db)
                writable = True
            except HTTPException:
                pass
        results.append(
            {
                'index': index,
                **{k: v for k, v in package.items() if k != 'files'},
                'files': file_summaries(package['files']),
                'id_taken': existing is not None,
                'name_taken': await Skills.get_skill_by_name(package['name'], db=db) is not None,
                'can_replace': writable,
                'expected_version_id': existing.version_id if writable else None,
            }
        )
    return results


@router.post('/import')
async def import_skills(
    request: Request,
    files: list[UploadFile] = File(...),
    decisions: str = Form(...),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await require_import(user, db)
    packages = await read_import(files)
    try:
        choices = json.loads(decisions)
        if (
            not isinstance(choices, list)
            or len(choices) != len(packages)
            or any(not isinstance(choice, dict) for choice in choices)
        ):
            raise ValueError('One decision is required per skill')
    except (ValueError, TypeError) as error:
        raise HTTPException(400, str(error))
    results = []
    for package, choice in zip(packages, choices):
        try:
            action = choice.get('action', 'skip')
            if action == 'skip':
                results.append({'status': 'skipped', 'id': package['id']})
                continue
            data = {**package, 'id': choice.get('id', package['id']), 'name': choice.get('name', package['name'])}
            if action == 'replace':
                await authorized_skill(data['id'], user, 'write', db)
                if not choice.get('expected_version_id'):
                    raise HTTPException(400, 'Replacement requires expected_version_id')
                result = await update_skill_by_id(
                    request, data['id'], SkillForm(**data, expected_version_id=choice['expected_version_id']), user, db
                )
            elif action in ('create', 'copy'):
                result = await create_new_skill(request, SkillForm(**data, access_grants=[]), user, db)
            else:
                raise HTTPException(400, 'Unknown import action')
            results.append({'status': 'saved', 'id': result.id})
        except (HTTPException, ValueError) as error:
            results.append(
                {
                    'status': 'error',
                    'id': package['id'],
                    'error': error.detail if isinstance(error, HTTPException) else str(error),
                }
            )
    return results
