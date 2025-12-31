import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.prompts import Prompts, PromptModel
from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, Integer, ForeignKey
from open_webui.utils.access_control import has_access

####################
# PromptGroup DB Schema
####################


class PromptGroup(Base):
    __tablename__ = "prompt_group"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    name = Column(String)
    description = Column(Text, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    access_control = Column(JSON, nullable=True)  # Same pattern as prompts


class PromptGroupMapping(Base):
    __tablename__ = "prompt_group_mapping"

    id = Column(String, primary_key=True)
    group_id = Column(String)  # No FK constraint for SQLite compatibility
    prompt_command = Column(String)  # No FK constraint for SQLite compatibility
    order = Column(Integer, default=0)  # 0=base, 10=proficiency, 20=style


####################
# Pydantic Models
####################


class PromptGroupModel(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    created_at: int
    updated_at: int
    access_control: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class PromptGroupMappingModel(BaseModel):
    id: str
    group_id: str
    prompt_command: str
    order: int

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class PromptGroupForm(BaseModel):
    name: str
    description: Optional[str] = None
    access_control: Optional[dict] = None


class PromptGroupMappingForm(BaseModel):
    prompt_command: str
    order: int


class PromptGroupUserResponse(PromptGroupModel):
    user: Optional[UserResponse] = None


class PromptGroupWithPromptsResponse(PromptGroupModel):
    prompts: list[PromptModel] = []
    user: Optional[UserResponse] = None


class PromptGroupListResponse(PromptGroupModel):
    """Response for list endpoint - includes prompts but excludes user"""
    prompts: list[PromptModel] = []


####################
# PromptGroup Table
####################


class PromptGroupTable:
    def insert_new_group(
        self, user_id: str, form_data: PromptGroupForm
    ) -> Optional[PromptGroupModel]:
        """Create a new prompt group"""
        with get_db() as db:
            id = str(uuid.uuid4())
            group = PromptGroupModel(
                **{
                    "id": id,
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )

            try:
                result = PromptGroup(**group.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return PromptGroupModel.model_validate(result) if result else None
            except Exception as e:
                print(f"Error creating prompt group: {e}")
                return None

    def get_group_by_id(self, id: str) -> Optional[PromptGroupModel]:
        """Get a prompt group by ID"""
        try:
            with get_db() as db:
                group = db.query(PromptGroup).filter_by(id=id).first()
                return PromptGroupModel.model_validate(group) if group else None
        except Exception:
            return None

    def get_all_groups(self) -> list[PromptGroupUserResponse]:
        """Get all prompt groups with user info"""
        with get_db() as db:
            all_groups = (
                db.query(PromptGroup).order_by(PromptGroup.updated_at.desc()).all()
            )

            user_ids = list(set(group.user_id for group in all_groups))
            users = Users.get_users_by_user_ids(user_ids) if user_ids else []
            users_dict = {user.id: user for user in users}

            groups = []
            for group in all_groups:
                user = users_dict.get(group.user_id)
                groups.append(
                    PromptGroupUserResponse.model_validate(
                        {
                            **PromptGroupModel.model_validate(group).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )

            return groups

    def get_groups_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[PromptGroupUserResponse]:
        """Get groups accessible by user"""
        groups = self.get_all_groups()
        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user_id)}

        return [
            group
            for group in groups
            if group.user_id == user_id
            or has_access(user_id, permission, group.access_control, user_group_ids)
        ]

    def update_group_by_id(
        self, id: str, form_data: PromptGroupForm
    ) -> Optional[PromptGroupModel]:
        """Update a prompt group"""
        try:
            with get_db() as db:
                group = db.query(PromptGroup).filter_by(id=id).first()
                if not group:
                    return None

                group.name = form_data.name
                if form_data.description is not None:
                    group.description = form_data.description
                if form_data.access_control is not None:
                    group.access_control = form_data.access_control
                group.updated_at = int(time.time())

                db.commit()
                return PromptGroupModel.model_validate(group)
        except Exception:
            return None

    def delete_group_by_id(self, id: str) -> bool:
        """Delete a prompt group and its mappings"""
        try:
            with get_db() as db:
                # Delete mappings first
                db.query(PromptGroupMapping).filter_by(group_id=id).delete()
                # Delete group
                db.query(PromptGroup).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


####################
# PromptGroupMapping Table
####################


class PromptGroupMappingTable:
    def add_prompt_to_group(
        self, group_id: str, form_data: PromptGroupMappingForm
    ) -> Optional[PromptGroupMappingModel]:
        """Add a prompt to a group"""
        with get_db() as db:
            # Check if mapping already exists
            existing = (
                db.query(PromptGroupMapping)
                .filter_by(group_id=group_id, prompt_command=form_data.prompt_command)
                .first()
            )

            if existing:
                # Update order if already exists
                existing.order = form_data.order
                db.commit()
                return PromptGroupMappingModel.model_validate(existing)

            # Create new mapping
            id = str(uuid.uuid4())
            mapping = PromptGroupMappingModel(
                id=id,
                group_id=group_id,
                prompt_command=form_data.prompt_command,
                order=form_data.order,
            )

            try:
                result = PromptGroupMapping(**mapping.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return PromptGroupMappingModel.model_validate(result) if result else None
            except Exception as e:
                print(f"Error adding prompt to group: {e}")
                return None

    def get_mappings_by_group_id(
        self, group_id: str
    ) -> list[PromptGroupMappingModel]:
        """Get all prompt mappings for a group, ordered by order field"""
        try:
            with get_db() as db:
                mappings = (
                    db.query(PromptGroupMapping)
                    .filter_by(group_id=group_id)
                    .order_by(PromptGroupMapping.order.asc())
                    .all()
                )
                return [PromptGroupMappingModel.model_validate(m) for m in mappings]
        except Exception:
            return []

    def get_prompts_by_group_id(self, group_id: str) -> list[PromptModel]:
        """Get all prompts in a group, ordered by order field"""
        mappings = self.get_mappings_by_group_id(group_id)
        prompts = []

        for mapping in mappings:
            prompt = Prompts.get_prompt_by_command(mapping.prompt_command)
            if prompt:
                prompts.append(prompt)

        return prompts

    def remove_prompt_from_group(self, group_id: str, prompt_command: str) -> bool:
        """Remove a prompt from a group"""
        try:
            with get_db() as db:
                db.query(PromptGroupMapping).filter_by(
                    group_id=group_id, prompt_command=prompt_command
                ).delete()
                db.commit()
                return True
        except Exception:
            return False

    def reorder_prompts(
        self, group_id: str, mappings: list[PromptGroupMappingForm]
    ) -> bool:
        """Reorder prompts in a group"""
        try:
            with get_db() as db:
                for form_data in mappings:
                    mapping = (
                        db.query(PromptGroupMapping)
                        .filter_by(
                            group_id=group_id, prompt_command=form_data.prompt_command
                        )
                        .first()
                    )
                    if mapping:
                        mapping.order = form_data.order

                db.commit()
                return True
        except Exception:
            return False


PromptGroups = PromptGroupTable()
PromptGroupMappings = PromptGroupMappingTable()
