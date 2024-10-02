import json
import logging
import time
from typing import Optional
import uuid

from open_webui.apps.webui.internal.db import Base, get_db
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Projects DB Schema
####################


class Project(Base):
    __tablename__ = "project"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text)

    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ProjectModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: str

    data: Optional[dict] = None
    meta: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


class ProjectForm(BaseModel):
    name: str
    description: str
    data: Optional[dict] = None


class ProjectTable:
    def insert_new_project(
        self, user_id: str, form_data: ProjectForm
    ) -> Optional[ProjectModel]:
        with get_db() as db:
            project = ProjectModel(
                **{
                    **form_data.model_dump(),
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = Project(**project.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return ProjectModel.model_validate(result)
                else:
                    return None
            except Exception:
                return None

    def get_projects(self) -> list[ProjectModel]:
        with get_db() as db:
            return [
                ProjectModel.model_validate(project)
                for project in db.query(Project)
                .order_by(Project.updated_at.desc())
                .all()
            ]

    def get_project_by_id(self, id: str) -> Optional[ProjectModel]:
        try:
            with get_db() as db:
                project = db.query(Project).filter_by(id=id).first()
                return ProjectModel.model_validate(project) if project else None
        except Exception:
            return None

    def update_project_by_id(
        self, id: str, form_data: ProjectForm
    ) -> Optional[ProjectModel]:
        try:
            with get_db() as db:
                db.query(Project).filter_by(id=id).update(
                    {
                        "name": form_data.name,
                        "updated_id": int(time.time()),
                    }
                )
                db.commit()
                return self.get_project_by_id(id=form_data.id)
        except Exception as e:
            log.exception(e)
            return None

    def delete_project_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Project).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


Projects = ProjectTable()
