"""Private working views, independently owned by each user of a chat."""

import time
from typing import Annotated, Literal

from open_webui.internal.db import Base
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import JSON, BigInteger, Column, Text, update
from sqlalchemy.exc import IntegrityError


class ViewModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class PanelTab(ViewModel):
    id: str
    kind: Literal['chat', 'comments', 'files', 'file', 'terminal', 'browser', 'desktop', 'side']
    label: str
    terminalId: str | None = None
    terminalNumber: int | None = None
    chatId: str | None = None
    sideChatNumber: int | None = None
    path: str | None = None
    page: int | None = None
    sessionId: str | None = None
    directory: str | None = None


class PanelGroup(ViewModel):
    id: str
    tabIds: list[str]
    activeId: str


class GroupLayout(ViewModel):
    type: Literal['group']
    groupId: str


class SplitLayout(ViewModel):
    type: Literal['split']
    id: str
    direction: Literal['horizontal', 'vertical']
    ratio: float = Field(gt=0, lt=1, allow_inf_nan=False)
    first: 'Layout'
    second: 'Layout'


Layout = Annotated[GroupLayout | SplitLayout, Field(discriminator='type')]
SplitLayout.model_rebuild()


class PanelTabs(ViewModel):
    tabs: list[PanelTab]
    activeId: str
    history: list[str]
    groups: list[PanelGroup]
    activeGroupId: str
    layout: Layout

    @model_validator(mode='after')
    def valid_references(self):
        tabs = {tab.id for tab in self.tabs}
        groups = {group.id for group in self.groups}
        if len(tabs) != len(self.tabs) or len(groups) != len(self.groups) or not groups:
            raise ValueError('Duplicate tabs/groups or missing groups')
        if '' in tabs or '' in groups or self.activeGroupId not in groups:
            raise ValueError('Invalid identifier')
        assigned = []
        for group in self.groups:
            if group.activeId not in group.tabIds and (group.tabIds or group.activeId):
                raise ValueError('Invalid active tab')
            assigned.extend(group.tabIds)
        if len(assigned) != len(set(assigned)) or set(assigned) != tabs:
            raise ValueError('Tabs must belong to exactly one group')
        active = next(group for group in self.groups if group.id == self.activeGroupId)
        if self.activeId != active.activeId or not set(self.history) <= tabs:
            raise ValueError('Invalid active tab or history')
        self.validate_layout(groups)
        return self

    def validate_layout(self, groups):
        leaves, splits = [], set()
        stack = [self.layout]
        while stack:
            node = stack.pop()
            if isinstance(node, GroupLayout):
                leaves.append(node.groupId)
            else:
                if not node.id or node.id in splits:
                    raise ValueError('Duplicate split identifier')
                splits.add(node.id)
                stack.extend((node.first, node.second))
        if len(leaves) != len(set(leaves)) or set(leaves) != groups:
            raise ValueError('Layout must contain every group exactly once')


class ChatViewData(ViewModel):
    schemaVersion: Literal[1]
    selectedTerminalId: str | None
    panels: PanelTabs


class ChatViewStateForm(ViewModel):
    state: ChatViewData


class ChatViewState(Base):
    __tablename__ = 'chat_view_state'
    user_id = Column(Text, primary_key=True)
    chat_id = Column(Text, primary_key=True, index=True)
    state = Column(JSON, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class ChatViewStatesTable:
    async def get(self, user_id, chat_id, db):
        row = await db.get(ChatViewState, (user_id, chat_id))
        return row.state if row else None

    async def upsert(self, user_id, chat_id, state, db):
        now = int(time.time())
        conditions = (ChatViewState.user_id == user_id, ChatViewState.chat_id == chat_id)
        result = await db.execute(update(ChatViewState).where(*conditions).values(state=state, updated_at=now))
        if not result.rowcount:
            try:
                async with db.begin_nested():
                    db.add(ChatViewState(user_id=user_id, chat_id=chat_id, state=state, updated_at=now))
                    await db.flush()
            except IntegrityError:
                await db.execute(update(ChatViewState).where(*conditions).values(state=state, updated_at=now))
        await db.commit()
        return {'updated_at': now}


ChatViewStates = ChatViewStatesTable()
