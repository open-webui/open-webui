import logging
import time
from typing import Optional

from fastapi import HTTPException
from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.access_grants import AccessGrant, AccessGrantModel, AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.skill_history import SkillHistories, SkillHistory
from open_webui.models.users import User, UserModel, UserResponse, Users
from open_webui.utils.skill_files import SkillFile, SkillFileOperation, apply_operations, validate_files
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, BigInteger, Boolean, Column, String, Text, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

####################
# Skills DB Schema
####################


class Skill(Base):
    __tablename__ = 'skill'

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)
    name = Column(Text, unique=True)
    description = Column(Text, nullable=True)
    content = Column(Text)
    data = Column(JSON, nullable=True)
    version_id = Column(Text, nullable=True)
    meta = Column(JSON)
    is_active = Column(Boolean, default=True)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class SkillMeta(BaseModel):
    i18n: dict[str, dict[str, str]] | None = None
    tags: Optional[list[str]] = []


class SkillModel(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    content: str
    data: dict
    version_id: str | None = None
    meta: SkillMeta
    is_active: bool = True
    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class SkillUserModel(SkillModel):
    user: Optional[UserResponse] = None


class SkillResponse(BaseModel):
    version_id: str | None = None
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    meta: SkillMeta
    is_active: bool = True
    access_grants: list[AccessGrantModel] = Field(default_factory=list)
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class SkillUserResponse(SkillResponse):
    user: Optional[UserResponse] = None

    model_config = ConfigDict(extra='ignore')


class SkillAccessResponse(SkillUserResponse):
    write_access: Optional[bool] = False


class SkillDetailResponse(SkillAccessResponse):
    content: str


class SkillData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    files: list[SkillFile]


class SkillForm(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    content: str | None = None
    files: list[SkillFile] | None = None
    data: SkillData | None = None
    operations: list[SkillFileOperation] | None = None
    expected_version_id: str | None = None
    commit_message: str | None = None
    meta: SkillMeta = Field(default_factory=SkillMeta)
    is_active: bool = True
    access_grants: Optional[list[dict]] = None


class SkillListResponse(BaseModel):
    items: list[SkillUserResponse] = []
    total: int = 0


class SkillAccessListResponse(BaseModel):
    items: list[SkillAccessResponse] = []
    total: int = 0


def skill_snapshot(skill) -> dict:
    return {
        'name': skill.name,
        'description': skill.description,
        'content': skill.content,
        'data': skill.data,
        'meta': SkillMeta.model_validate(skill.meta or {}).model_dump(),
    }


async def get_skill_snapshot(skill, version_id=None, db=None) -> dict:
    if not version_id or version_id == skill.version_id:
        return skill_snapshot(skill)
    entry = await SkillHistories.get_history_by_id(skill.id, version_id, db=db)
    if not entry:
        raise HTTPException(404, 'Skill version not found')
    return entry.snapshot


class SkillsTable:
    async def _get_access_grants(self, skill_id: str, db: Optional[AsyncSession] = None) -> list[AccessGrantModel]:
        return await AccessGrants.get_grants_by_resource('skill', skill_id, db=db)

    async def _to_skill_model(
        self,
        skill: Skill,
        access_grants: Optional[list[AccessGrantModel]] = None,
        db: Optional[AsyncSession] = None,
    ) -> SkillModel:
        skill_model = SkillModel.model_validate(skill)
        skill_model.access_grants = (
            access_grants if access_grants is not None else await self._get_access_grants(skill_model.id, db=db)
        )
        return skill_model

    async def insert_new_skill(
        self,
        user_id: str,
        form_data: SkillForm,
        db: Optional[AsyncSession] = None,
    ) -> Optional[SkillModel]:
        data = form_data.model_dump(exclude_none=True)
        if data.get('data') is not None and data.get('files') is not None:
            raise ValueError('Provide data or files, not both')
        files = (
            data['data']['files']
            if data.get('data') is not None
            else data.get('files', [{'path': 'SKILL.md', 'content': data.get('content', '')}])
        )
        files = validate_files(files)
        snapshot = {
            'name': form_data.name,
            'description': form_data.description,
            'meta': form_data.meta.model_dump(),
            'content': next(f['content'] for f in files if f['path'] == 'SKILL.md'),
            'data': {'files': files},
        }
        entry = SkillHistories.new_entry(form_data.id, snapshot, user_id, commit_message=form_data.commit_message)
        async with get_async_db_context(db) as session:
            try:
                result = Skill(
                    id=form_data.id,
                    user_id=user_id,
                    name=form_data.name,
                    description=form_data.description,
                    meta=snapshot['meta'],
                    content=snapshot['content'],
                    data=snapshot['data'],
                    is_active=form_data.is_active,
                    version_id=entry.id,
                    created_at=int(time.time()),
                    updated_at=int(time.time()),
                )
                session.add_all([result, entry])
                grants = await AccessGrants.replace_access_grants(session, 'skill', result.id, form_data.access_grants)
                await session.commit()
                return await self._to_skill_model(result, [AccessGrantModel.model_validate(g) for g in grants])
            except Exception:
                await session.rollback()
                raise

    async def get_skill_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[SkillModel]:
        try:
            async with get_async_db_context(db) as db:
                skill = await db.get(Skill, id)
                return await self._to_skill_model(skill, db=db) if skill else None
        except Exception:
            return None

    async def get_skill_by_name(self, name: str, db: Optional[AsyncSession] = None) -> Optional[SkillModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Skill).filter_by(name=name))
                skill = result.scalars().first()
                return await self._to_skill_model(skill, db=db) if skill else None
        except Exception:
            return None

    async def get_skills(
        self,
        user_id: str | None = None,
        ids: list[str] | None = None,
        db: AsyncSession | None = None,
    ) -> list[SkillUserModel]:
        async with get_async_db_context(db) as db:
            stmt = select(Skill).order_by(Skill.updated_at.desc())

            if ids is not None:
                stmt = stmt.filter(Skill.id.in_(ids))

            if user_id is not None:
                user_group_ids = {
                    group.id for group in await Groups.get_groups_by_member_id(user_id, db=db, include_inherited=True)
                }
                stmt = AccessGrants.has_permission_filter(
                    db=db,
                    query=stmt,
                    DocumentModel=Skill,
                    filter={'user_id': user_id, 'group_ids': user_group_ids},
                    resource_type='skill',
                    permission='read',
                )

            result = await db.execute(stmt)
            all_skills = result.scalars().all()

            user_ids = list(set(skill.user_id for skill in all_skills))
            skill_ids = [skill.id for skill in all_skills]

            users = await Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}
            grants_map = await AccessGrants.get_grants_by_resources('skill', skill_ids, db=db)

            skills = []
            for skill in all_skills:
                user = users_dict.get(skill.user_id)
                skills.append(
                    SkillUserModel.model_validate(
                        {
                            **(
                                await self._to_skill_model(
                                    skill,
                                    access_grants=grants_map.get(skill.id, []),
                                    db=db,
                                )
                            ).model_dump(),
                            'user': user.model_dump() if user else None,
                        }
                    )
                )
            return skills

    async def search_skills(
        self,
        user_id: str,
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: Optional[AsyncSession] = None,
    ) -> SkillListResponse:
        try:
            async with get_async_db_context(db) as db:
                # Join with User table for user filtering
                stmt = select(Skill, User).outerjoin(User, User.id == Skill.user_id)

                if filter:
                    query_key = filter.get('query')
                    if query_key:
                        stmt = stmt.filter(
                            or_(
                                Skill.name.ilike(f'%{query_key}%'),
                                Skill.description.ilike(f'%{query_key}%'),
                                Skill.id.ilike(f'%{query_key}%'),
                                User.name.ilike(f'%{query_key}%'),
                                User.email.ilike(f'%{query_key}%'),
                            )
                        )

                    view_option = filter.get('view_option')
                    if view_option == 'created':
                        stmt = stmt.filter(Skill.user_id == user_id)
                    elif view_option == 'shared':
                        stmt = stmt.filter(Skill.user_id != user_id)

                    # Apply access grant filtering
                    stmt = AccessGrants.has_permission_filter(
                        db=db,
                        query=stmt,
                        DocumentModel=Skill,
                        filter=filter,
                        resource_type='skill',
                        permission='read',
                    )

                order_by = filter.get('order_by')
                direction = filter.get('direction')

                if order_by == 'name':
                    if direction == 'asc':
                        stmt = stmt.order_by(Skill.name.asc())
                    else:
                        stmt = stmt.order_by(Skill.name.desc())
                elif order_by == 'created_at':
                    if direction == 'asc':
                        stmt = stmt.order_by(Skill.created_at.asc())
                    else:
                        stmt = stmt.order_by(Skill.created_at.desc())
                elif order_by == 'updated_at':
                    if direction == 'asc':
                        stmt = stmt.order_by(Skill.updated_at.asc())
                    else:
                        stmt = stmt.order_by(Skill.updated_at.desc())
                else:
                    stmt = stmt.order_by(Skill.updated_at.desc())

                # Count BEFORE pagination
                count_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
                total = count_result.scalar()

                if skip:
                    stmt = stmt.offset(skip)
                if limit:
                    stmt = stmt.limit(limit)

                result = await db.execute(stmt)
                items = result.all()

                skill_ids = [skill.id for skill, _ in items]
                grants_map = await AccessGrants.get_grants_by_resources('skill', skill_ids, db=db)

                skills = []
                for skill, user in items:
                    skills.append(
                        SkillUserResponse(
                            **(
                                await self._to_skill_model(
                                    skill,
                                    access_grants=grants_map.get(skill.id, []),
                                    db=db,
                                )
                            ).model_dump(),
                            user=(UserResponse(**UserModel.model_validate(user).model_dump()) if user else None),
                        )
                    )

                return SkillListResponse(items=skills, total=total)
        except Exception as e:
            log.exception(f'Error searching skills: {e}')
            return SkillListResponse(items=[], total=0)

    async def update_skill_by_id(self, id: str, updated: dict, db=None, user_id=None) -> Optional[SkillModel]:
        async with get_async_db_context(db) as session:
            try:
                skill = await session.get(Skill, id, populate_existing=True)
                if not skill:
                    return None
                expected = updated.get('expected_version_id')
                if expected is not None and expected != skill.version_id:
                    raise HTTPException(409, {'code': 'version_conflict', 'current_version_id': skill.version_id})
                if any(updated.get(key) is not None for key in ('files', 'data', 'operations')) and expected is None:
                    raise HTTPException(400, 'expected_version_id is required for file updates')
                old = skill_snapshot(skill)
                if sum(updated.get(key) is not None for key in ('files', 'data', 'operations')) > 1:
                    raise ValueError('Provide data, files, or operations, not more than one')
                files = (
                    SkillData.model_validate(updated['data']).model_dump(exclude_none=True)['files']
                    if updated.get('data') is not None
                    else updated.get('files')
                )
                files = files if files is not None else skill.data['files']
                if updated.get('operations') is not None:
                    files = apply_operations(files, updated['operations'])
                if updated.get('content') is not None:
                    files = [f for f in files if f['path'] != 'SKILL.md'] + [
                        {'path': 'SKILL.md', 'content': updated['content']}
                    ]
                files = validate_files(files, skill.data['files'])
                snapshot = {key: updated.get(key, old.get(key)) for key in ('name', 'description', 'meta')}
                snapshot['meta'] = SkillMeta.model_validate(snapshot['meta'] or {}).model_dump()
                snapshot['data'] = {'files': files}
                snapshot['content'] = next(f['content'] for f in files if f['path'] == 'SKILL.md')
                values = {'is_active': updated.get('is_active', skill.is_active)}
                if snapshot != old:
                    entry = SkillHistories.new_entry(
                        id, snapshot, user_id or skill.user_id, skill.version_id, updated.get('commit_message')
                    )
                    session.add(entry)
                    values.update(snapshot, version_id=entry.id)
                values['updated_at'] = int(time.time())
                result = await session.execute(
                    update(Skill)
                    .where(Skill.id == id, Skill.version_id == skill.version_id)
                    .values(**values)
                    .execution_options(synchronize_session=False)
                )
                if result.rowcount != 1:
                    raise HTTPException(409, {'code': 'version_conflict'})
                if updated.get('access_grants') is not None:
                    await AccessGrants.replace_access_grants(session, 'skill', id, updated['access_grants'])
                await session.commit()
                await session.refresh(skill)
                grants = (
                    (await session.execute(select(AccessGrant).filter_by(resource_type='skill', resource_id=id)))
                    .scalars()
                    .all()
                )
                return await self._to_skill_model(skill, [AccessGrantModel.model_validate(g) for g in grants])
            except Exception:
                await session.rollback()
                raise

    async def update_skill_version(
        self, id: str, version_id: str, expected_version_id: str, db=None
    ) -> Optional[SkillModel]:
        async with get_async_db_context(db) as session:
            try:
                # Lock before reading the target revision so deletion cannot race promotion.
                await session.execute(update(Skill).where(Skill.id == id).values(version_id=Skill.version_id))
                skill = await session.get(Skill, id, populate_existing=True)
                if not skill:
                    return None
                if expected_version_id != skill.version_id:
                    raise HTTPException(409, {'code': 'version_conflict', 'current_version_id': skill.version_id})
                entry = await SkillHistories.get_history_by_id(id, version_id, db=session)
                if not entry:
                    raise HTTPException(404, 'Skill version not found')
                snapshot = entry.snapshot
                result = await session.execute(
                    update(Skill)
                    .where(Skill.id == id, Skill.version_id == expected_version_id)
                    .values(
                        **{key: snapshot[key] for key in ('name', 'description', 'content', 'data', 'meta')},
                        version_id=version_id,
                        updated_at=int(time.time()),
                    )
                    .execution_options(synchronize_session=False)
                )
                if result.rowcount != 1:
                    raise HTTPException(409, {'code': 'version_conflict'})
                await session.commit()
                await session.refresh(skill)
                return await self._to_skill_model(skill, db=session)
            except Exception:
                await session.rollback()
                raise

    async def toggle_skill_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[SkillModel]:
        async with get_async_db_context(db) as db:
            try:
                result = await db.execute(select(Skill).filter_by(id=id))
                skill = result.scalars().first()
                if not skill:
                    return None

                skill.is_active = not skill.is_active
                skill.updated_at = int(time.time())
                await db.commit()

                return await self._to_skill_model(skill, db=db)
            except Exception:
                return None

    async def delete_skill_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(AccessGrant).filter_by(resource_type='skill', resource_id=id))
                await db.execute(delete(SkillHistory).filter_by(skill_id=id))
                await db.execute(delete(Skill).filter_by(id=id))
                await db.commit()

                return True
        except Exception:
            return False


Skills = SkillsTable()
