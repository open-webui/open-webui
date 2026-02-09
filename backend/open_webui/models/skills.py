import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from open_webui.internal.db import Base, JSONField, get_db_context
from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text, JSON

from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)


####################
# Skills DB Schema
####################


class Skill(Base):
    __tablename__ = "skill"

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)

    name = Column(Text)
    content = Column(Text)

    meta = Column(JSONField)
    activation = Column(JSONField)
    effects = Column(JSONField)

    is_active = Column(Boolean)
    priority = Column(Integer)

    access_control = Column(JSON, nullable=True)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class SkillModel(BaseModel):
    id: str
    user_id: str

    name: str
    content: str

    meta: Optional[dict] = {}
    activation: Optional[dict] = {}
    effects: Optional[dict] = {}

    is_active: bool = False
    priority: int = 0
    access_control: Optional[dict] = None

    updated_at: int
    created_at: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class SkillUserModel(SkillModel):
    user: Optional[UserResponse] = None


class SkillResponse(BaseModel):
    id: str
    user_id: str
    name: str
    meta: Optional[dict] = {}
    is_active: bool
    priority: int
    access_control: Optional[dict] = None
    updated_at: int
    created_at: int


class SkillUserResponse(SkillResponse):
    user: Optional[UserResponse] = None

    model_config = ConfigDict(extra="allow")


class SkillAccessResponse(SkillUserResponse):
    write_access: Optional[bool] = False


class SkillForm(BaseModel):
    id: str
    name: str
    content: str

    meta: Optional[dict] = {}
    activation: Optional[dict] = {}
    effects: Optional[dict] = {}

    is_active: bool = False
    priority: int = 0
    access_control: Optional[dict] = None


class SkillsTable:
    def insert_new_skill(
        self,
        user_id: str,
        form_data: SkillForm,
        db: Optional[Session] = None,
    ) -> Optional[SkillModel]:
        skill = SkillModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "updated_at": int(time.time()),
                "created_at": int(time.time()),
            }
        )

        try:
            with get_db_context(db) as db:
                result = Skill(**skill.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)

                if result:
                    return SkillModel.model_validate(result)
                return None
        except Exception as e:
            log.exception(f"Error creating new skill: {e}")
            return None

    def get_skill_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[SkillModel]:
        try:
            with get_db_context(db) as db:
                skill = db.get(Skill, id)
                return SkillModel.model_validate(skill)
        except Exception:
            return None

    def get_skills(self, db: Optional[Session] = None) -> list[SkillUserModel]:
        with get_db_context(db) as db:
            all_skills = db.query(Skill).order_by(Skill.updated_at.desc()).all()
            user_ids = list(set(skill.user_id for skill in all_skills))

            users = Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            skills = []
            for skill in all_skills:
                user = users_dict.get(skill.user_id)
                skills.append(
                    SkillUserModel.model_validate(
                        {
                            **SkillModel.model_validate(skill).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )

            return skills

    def get_skills_by_user_id(
        self,
        user_id: str,
        permission: str = "write",
        db: Optional[Session] = None,
    ) -> list[SkillUserModel]:
        skills = self.get_skills(db=db)
        user_group_ids = {
            group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
        }

        return [
            skill
            for skill in skills
            if skill.user_id == user_id
            or has_access(user_id, permission, skill.access_control, user_group_ids)
        ]

    def get_active_skills_by_user_id(
        self,
        user_id: str,
        db: Optional[Session] = None,
    ) -> list[SkillModel]:
        readable_skills = self.get_skills_by_user_id(user_id, "read", db=db)
        active_skills = [
            SkillModel.model_validate(skill.model_dump())
            for skill in readable_skills
            if skill.is_active
        ]

        return sorted(active_skills, key=lambda item: item.priority, reverse=True)

    def get_active_skills_by_ids_and_user_id(
        self,
        user_id: str,
        skill_ids: list[str],
        db: Optional[Session] = None,
    ) -> list[SkillModel]:
        skill_id_set = {skill_id for skill_id in skill_ids if isinstance(skill_id, str)}
        if not skill_id_set:
            return []

        readable_skills = self.get_skills_by_user_id(user_id, "read", db=db)
        active_skills = []

        for skill in readable_skills:
            if skill.id in skill_id_set and skill.is_active:
                active_skills.append(SkillModel.model_validate(skill.model_dump()))

        return sorted(active_skills, key=lambda item: item.priority, reverse=True)

    def update_skill_by_id(
        self,
        id: str,
        updated: dict,
        db: Optional[Session] = None,
    ) -> Optional[SkillModel]:
        try:
            with get_db_context(db) as db:
                db.query(Skill).filter_by(id=id).update(
                    {
                        **updated,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()

                skill = db.get(Skill, id)
                if skill:
                    db.refresh(skill)
                    return SkillModel.model_validate(skill)
                return None
        except Exception:
            return None

    def delete_skill_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Skill).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


Skills = SkillsTable()
