import time
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Text, BigInteger

from open_webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    # 用户主动反馈建议，带 4 小时限流。仅存最基本的信息，方便前端直接插入查看。
    id = Column(Text, primary_key=True)
    user_id = Column(Text, index=True, nullable=False)
    content = Column(Text, nullable=False)  # 反馈正文
    contact = Column(Text, nullable=True)  # 可选联系方式
    status = Column(Text, default="pending")  # pending/resolved
    created_at = Column(BigInteger, nullable=False)  # 秒级时间戳
    updated_at = Column(BigInteger, nullable=False)


class UserFeedbackModel(BaseModel):
    id: str
    user_id: str
    content: str
    contact: Optional[str] = None
    status: str
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class UserFeedbackForm(BaseModel):
    content: str
    contact: Optional[str] = None


class UserFeedbacksTable:
    def create(
        self, user_id: str, content: str, contact: Optional[str] = None
    ) -> Optional[UserFeedbackModel]:
        """创建用户反馈，默认状态 pending。"""
        now_ts = int(time.time())
        record = UserFeedbackModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=content,
            contact=contact,
            status="pending",
            created_at=now_ts,
            updated_at=now_ts,
        )
        try:
            with get_db() as db:
                db_item = UserFeedback(**record.model_dump())
                db.add(db_item)
                db.commit()
                db.refresh(db_item)
                return UserFeedbackModel.model_validate(db_item)
        except Exception as e:
            log.exception(f"Error creating user feedback: {e}")
            return None

    def get_recent_within(self, user_id: str, seconds: int) -> Optional[UserFeedbackModel]:
        """查询指定时间窗口内最新一条反馈，用于冷却期检查。"""
        try:
            with get_db() as db:
                cutoff = int(time.time()) - seconds
                item = (
                    db.query(UserFeedback)
                    .filter(UserFeedback.user_id == user_id, UserFeedback.created_at >= cutoff)
                    .order_by(UserFeedback.created_at.desc())
                    .first()
                )
                if not item:
                    return None
                return UserFeedbackModel.model_validate(item)
        except Exception as e:
            log.exception(f"Error reading recent user feedback: {e}")
            return None

    def list_by_user(self, user_id: str) -> List[UserFeedbackModel]:
        """按用户列出反馈，按时间倒序。"""
        with get_db() as db:
            items = (
                db.query(UserFeedback)
                .filter(UserFeedback.user_id == user_id)
                .order_by(UserFeedback.created_at.desc())
                .all()
            )
            return [UserFeedbackModel.model_validate(x) for x in items]

    def list_all(self) -> List[UserFeedbackModel]:
        """管理员查看全部反馈。"""
        with get_db() as db:
            items = db.query(UserFeedback).order_by(UserFeedback.created_at.desc()).all()
            return [UserFeedbackModel.model_validate(x) for x in items]

    def update_status(self, id: str, status: str) -> Optional[UserFeedbackModel]:
        """更新状态（例如管理员处理后标记 resolved）。"""
        with get_db() as db:
            item = db.query(UserFeedback).filter_by(id=id).first()
            if not item:
                return None
            item.status = status
            item.updated_at = int(time.time())
            db.commit()
            db.refresh(item)
            return UserFeedbackModel.model_validate(item)

    def delete_by_id(self, id: str) -> bool:
        """删除单条反馈。"""
        with get_db() as db:
            item = db.query(UserFeedback).filter_by(id=id).first()
            if not item:
                return False
            db.delete(item)
            db.commit()
            return True


UserFeedbacks = UserFeedbacksTable()
