import time
from typing import Optional
import uuid
from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, Integer, func

from open_webui.internal.db import get_db
from open_webui.models.base import Base
from logging import getLogger

logger = getLogger(__name__)


class ExportLog(Base):
    __tablename__ = "export_logs"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    email_domain = Column(Text)
    export_timestamp = Column(BigInteger)
    file_size = Column(BigInteger)
    row_count = Column(Integer)
    date_range_start = Column(BigInteger)
    date_range_end = Column(BigInteger)
    created_at = Column(BigInteger)


class ExportLogModel(BaseModel):
    id: str
    user_id: str
    email_domain: str
    export_timestamp: int
    file_size: int
    row_count: int
    date_range_start: int
    date_range_end: int
    created_at: int


class ExportLogForm(BaseModel):
    user_id: str
    email_domain: str
    file_size: int
    row_count: int
    date_range_start: int
    date_range_end: int


class ExportLogsTable:
    def insert_new_export_log(
        self, form_data: ExportLogForm
    ) -> Optional[ExportLogModel]:
        with get_db() as db:
            try:
                id = str(uuid.uuid4())
                export_timestamp = int(time.time())
                created_at = int(time.time())

                export_log = ExportLog(
                    id=id,
                    user_id=form_data.user_id,
                    email_domain=form_data.email_domain,
                    export_timestamp=export_timestamp,
                    file_size=form_data.file_size,
                    row_count=form_data.row_count,
                    date_range_start=form_data.date_range_start,
                    date_range_end=form_data.date_range_end,
                    created_at=created_at,
                )

                db.add(export_log)
                db.commit()
                db.refresh(export_log)

                return ExportLogModel(
                    id=export_log.id,
                    user_id=export_log.user_id,
                    email_domain=export_log.email_domain,
                    export_timestamp=export_log.export_timestamp,
                    file_size=export_log.file_size,
                    row_count=export_log.row_count,
                    date_range_start=export_log.date_range_start,
                    date_range_end=export_log.date_range_end,
                    created_at=export_log.created_at,
                )
            except Exception as e:
                logger.error(f"Error inserting export log: {e}")
                return None

    def get_export_logs_by_user(self, user_id: str) -> list[ExportLogModel]:
        with get_db() as db:
            try:
                export_logs = (
                    db.query(ExportLog).filter(ExportLog.user_id == user_id).all()
                )
                return [
                    ExportLogModel(
                        id=log.id,
                        user_id=log.user_id,
                        email_domain=log.email_domain,
                        export_timestamp=log.export_timestamp,
                        file_size=log.file_size,
                        row_count=log.row_count,
                        date_range_start=log.date_range_start,
                        date_range_end=log.date_range_end,
                        created_at=log.created_at,
                    )
                    for log in export_logs
                ]
            except Exception as e:
                logger.error(f"Error getting export logs for user {user_id}: {e}")
                return []

    def get_all_export_logs(self) -> list[ExportLogModel]:
        with get_db() as db:
            try:
                export_logs = db.query(ExportLog).all()
                return [
                    ExportLogModel(
                        id=log.id,
                        user_id=log.user_id,
                        email_domain=log.email_domain,
                        export_timestamp=log.export_timestamp,
                        file_size=log.file_size,
                        row_count=log.row_count,
                        date_range_start=log.date_range_start,
                        date_range_end=log.date_range_end,
                        created_at=log.created_at,
                    )
                    for log in export_logs
                ]
            except Exception as e:
                logger.error(f"Error getting all export logs: {e}")
                return []


ExportLogs = ExportLogsTable()
