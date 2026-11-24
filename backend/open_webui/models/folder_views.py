"""Private working views, independently owned by each user of a folder."""

import time

from open_webui.internal.db import Base
from open_webui.models.chat_views import ChatViewData, ViewModel
from sqlalchemy import JSON, BigInteger, Column, Text, delete, select, update
from sqlalchemy.exc import IntegrityError


class FolderViewStateForm(ViewModel):
    state: ChatViewData
    revision: int


class FolderViewState(Base):
    __tablename__ = 'folder_view_state'
    user_id = Column(Text, primary_key=True)
    folder_id = Column(Text, primary_key=True, index=True)
    state = Column(JSON, nullable=False)
    revision = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class FolderViewStatesTable:
    async def get(self, user_id, folder_id, db):
        row = await db.get(FolderViewState, (user_id, folder_id), populate_existing=True)
        return {'state': row.state, 'revision': row.revision} if row else {'state': None, 'revision': 0}

    async def get_by_folder_ids(self, user_id, folder_ids, db):
        result = await db.execute(
            select(FolderViewState).where(FolderViewState.user_id == user_id, FolderViewState.folder_id.in_(folder_ids))
        )
        return {row.folder_id: row for row in result.scalars().all()}

    async def save(self, user_id, folder_id, state, revision, db):
        """Save over the given revision; None when another window saved first."""
        values = {'state': state, 'revision': revision + 1, 'updated_at': int(time.time())}
        if revision == 0:
            try:
                db.add(FolderViewState(user_id=user_id, folder_id=folder_id, **values))
                await db.commit()
                return {'revision': 1}
            except IntegrityError:
                await db.rollback()
                return None
        result = await db.execute(
            update(FolderViewState)
            .where(
                FolderViewState.user_id == user_id,
                FolderViewState.folder_id == folder_id,
                FolderViewState.revision == revision,
            )
            .values(**values)
        )
        await db.commit()
        return {'revision': revision + 1} if result.rowcount else None

    async def delete_by_folder_ids(self, folder_ids, db):
        await db.execute(delete(FolderViewState).where(FolderViewState.folder_id.in_(folder_ids)))
        await db.commit()


FolderViewStates = FolderViewStatesTable()
