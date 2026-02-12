import logging
import time
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context
from open_webui.models.users import Users, UserResponse
from open_webui.models.groups import Groups
from open_webui.models.access_grants import AccessGrantModel, AccessGrants

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String, Text

log = logging.getLogger(__name__)

####################
# Tools DB Schema
####################


class Tool(Base):
    __tablename__ = "tool"

    id = Column(String, primary_key=True, unique=True)
    user_id = Column(String)
    name = Column(Text)
    content = Column(Text)
    specs = Column(JSONField)
    meta = Column(JSONField)
    valves = Column(JSONField)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class ToolMeta(BaseModel):
    description: Optional[str] = None
    manifest: Optional[dict] = {}


class ToolModel(BaseModel):
    id: str
    user_id: str
    name: str
    content: str
    specs: list[dict]
    meta: ToolMeta
    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ToolUserModel(ToolModel):
    user: Optional[UserResponse] = None


class ToolResponse(BaseModel):
    id: str
    user_id: str
    name: str
    meta: ToolMeta
    access_grants: list[AccessGrantModel] = Field(default_factory=list)
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class ToolUserResponse(ToolResponse):
    user: Optional[UserResponse] = None

    model_config = ConfigDict(extra="allow")


class ToolAccessResponse(ToolUserResponse):
    write_access: Optional[bool] = False


class ToolForm(BaseModel):
    id: str
    name: str
    content: str
    meta: ToolMeta
    access_grants: Optional[list[dict]] = None


class ToolValves(BaseModel):
    valves: Optional[dict] = None


class ToolsTable:
    def _get_access_grants(
        self, tool_id: str, db: Optional[Session] = None
    ) -> list[AccessGrantModel]:
        return AccessGrants.get_grants_by_resource("tool", tool_id, db=db)

    def _to_tool_model(self, tool: Tool, db: Optional[Session] = None) -> ToolModel:
        tool_data = ToolModel.model_validate(tool).model_dump(exclude={"access_grants"})
        tool_data["access_grants"] = self._get_access_grants(tool_data["id"], db=db)
        return ToolModel.model_validate(tool_data)

    def insert_new_tool(
        self,
        user_id: str,
        form_data: ToolForm,
        specs: list[dict],
        db: Optional[Session] = None,
    ) -> Optional[ToolModel]:
        with get_db_context(db) as db:
            try:
                result = Tool(
                    **{
                        **form_data.model_dump(exclude={"access_grants"}),
                        "specs": specs,
                        "user_id": user_id,
                        "updated_at": int(time.time()),
                        "created_at": int(time.time()),
                    }
                )
                db.add(result)
                db.commit()
                db.refresh(result)
                AccessGrants.set_access_grants(
                    "tool", result.id, form_data.access_grants, db=db
                )
                if result:
                    return self._to_tool_model(result, db=db)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error creating a new tool: {e}")
                return None

    def get_tool_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ToolModel]:
        try:
            with get_db_context(db) as db:
                tool = db.get(Tool, id)
                return self._to_tool_model(tool, db=db) if tool else None
        except Exception:
            return None

    def get_tools(self, db: Optional[Session] = None) -> list[ToolUserModel]:
        with get_db_context(db) as db:
            all_tools = db.query(Tool).order_by(Tool.updated_at.desc()).all()

            user_ids = list(set(tool.user_id for tool in all_tools))

            users = Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            tools = []
            for tool in all_tools:
                user = users_dict.get(tool.user_id)
                tools.append(
                    ToolUserModel.model_validate(
                        {
                            **self._to_tool_model(tool, db=db).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return tools

    def get_tools_by_user_id(
        self, user_id: str, permission: str = "write", db: Optional[Session] = None
    ) -> list[ToolUserModel]:
        tools = self.get_tools(db=db)
        user_group_ids = {
            group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
        }

        return [
            tool
            for tool in tools
            if tool.user_id == user_id
            or AccessGrants.has_access(
                user_id=user_id,
                resource_type="tool",
                resource_id=tool.id,
                permission=permission,
                user_group_ids=user_group_ids,
                db=db,
            )
        ]

    def get_tool_valves_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[dict]:
        try:
            with get_db_context(db) as db:
                tool = db.get(Tool, id)
                return tool.valves if tool.valves else {}
        except Exception as e:
            log.exception(f"Error getting tool valves by id {id}")
            return None

    def update_tool_valves_by_id(
        self, id: str, valves: dict, db: Optional[Session] = None
    ) -> Optional[ToolValves]:
        try:
            with get_db_context(db) as db:
                db.query(Tool).filter_by(id=id).update(
                    {"valves": valves, "updated_at": int(time.time())}
                )
                db.commit()
                return self.get_tool_by_id(id, db=db)
        except Exception:
            return None

    def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[Session] = None
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id, db=db)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "tools" and "valves" settings
            if "tools" not in user_settings:
                user_settings["tools"] = {}
            if "valves" not in user_settings["tools"]:
                user_settings["tools"]["valves"] = {}

            return user_settings["tools"]["valves"].get(id, {})
        except Exception as e:
            log.exception(
                f"Error getting user values by id {id} and user_id {user_id}: {e}"
            )
            return None

    def update_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, valves: dict, db: Optional[Session] = None
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id, db=db)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "tools" and "valves" settings
            if "tools" not in user_settings:
                user_settings["tools"] = {}
            if "valves" not in user_settings["tools"]:
                user_settings["tools"]["valves"] = {}

            user_settings["tools"]["valves"][id] = valves

            # Update the user settings in the database
            Users.update_user_by_id(user_id, {"settings": user_settings}, db=db)

            return user_settings["tools"]["valves"][id]
        except Exception as e:
            log.exception(
                f"Error updating user valves by id {id} and user_id {user_id}: {e}"
            )
            return None

    def update_tool_by_id(
        self, id: str, updated: dict, db: Optional[Session] = None
    ) -> Optional[ToolModel]:
        try:
            with get_db_context(db) as db:
                access_grants = updated.pop("access_grants", None)
                db.query(Tool).filter_by(id=id).update(
                    {**updated, "updated_at": int(time.time())}
                )
                db.commit()
                if access_grants is not None:
                    AccessGrants.set_access_grants("tool", id, access_grants, db=db)

                tool = db.query(Tool).get(id)
                db.refresh(tool)
                return self._to_tool_model(tool, db=db)
        except Exception:
            return None

    def delete_tool_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                AccessGrants.revoke_all_access("tool", id, db=db)
                db.query(Tool).filter_by(id=id).delete()
                db.commit()

                return True
        except Exception:
            return False


Tools = ToolsTable()
