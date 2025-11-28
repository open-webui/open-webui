import logging
import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse


from pydantic import BaseModel, ConfigDict

from sqlalchemy import or_, and_, func
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy import BigInteger, Column, Text, JSON, Boolean


from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Models DB Schema
####################


# ModelParams is a model for the data stored in the params field of the Model table
class ModelParams(BaseModel):
    model_config = ConfigDict(extra="allow")
    pass


# ModelMeta is a model for the data stored in the meta field of the Model table
class ModelMeta(BaseModel):
    profile_image_url: Optional[str] = "/static/favicon.png"

    description: Optional[str] = None
    """
        User-facing description of the model.
    """

    capabilities: Optional[dict] = None

    model_config = ConfigDict(extra="allow")

    pass


class Model(Base):
    __tablename__ = "model"

    id = Column(Text, primary_key=True)
    """
        The model's id as used in the API. If set to an existing model, it will override the model.
    """
    user_id = Column(Text)

    base_model_id = Column(Text, nullable=True)
    """
        An optional pointer to the actual model that should be used when proxying requests.
    """

    name = Column(Text)
    """
        The human-readable display name of the model.
    """

    params = Column(JSONField)
    """
        Holds a JSON encoded blob of parameters, see `ModelParams`.
    """

    meta = Column(JSONField)
    """
        Holds a JSON encoded blob of metadata, see `ModelMeta`.
    """

    access_control = Column(JSON, nullable=True)  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }

    is_active = Column(Boolean, default=True)

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class ModelModel(BaseModel):
    id: str
    user_id: str
    base_model_id: Optional[str] = None

    name: str
    params: ModelParams
    meta: ModelMeta

    access_control: Optional[dict] = None

    is_active: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ModelUserResponse(ModelModel):
    user: Optional[UserResponse] = None


class ModelResponse(ModelModel):
    pass


class ModelForm(BaseModel):
    id: str
    base_model_id: Optional[str] = None
    name: str
    meta: ModelMeta
    params: ModelParams
    access_control: Optional[dict] = None
    is_active: bool = True


class ModelsTable:
    """
    模型数据访问层 - 管理 AI 模型的 CRUD 操作和权限控制

    核心功能：
    1. 模型管理：创建、查询、更新、删除模型配置
    2. 权限控制：基于用户/组的访问权限管理
    3. 模型同步：与外部模型源（如 Ollama、OpenAI）同步模型列表
    4. 模型分类：区分基础模型（base_model）和自定义模型

    模型类型：
    - 基础模型（base_model_id == None）：从外部 API 同步的原始模型（如 gpt-4, llama3）
    - 自定义模型（base_model_id != None）：用户创建的模型配置，指向基础模型
    """

    def insert_new_model(
        self, form_data: ModelForm, user_id: str
    ) -> Optional[ModelModel]:
        """
        插入新模型配置

        Args:
            form_data: 模型表单数据（包含 id、name、params、meta 等）
            user_id: 创建模型的用户 ID

        Returns:
            ModelModel: 创建成功返回模型对象，失败返回 None
        """
        model = ModelModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
        )
        try:
            with get_db() as db:
                result = Model(**model.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)

                if result:
                    return ModelModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            log.exception(f"Failed to insert a new model: {e}")
            return None

    def get_all_models(self) -> list[ModelModel]:
        """
        获取所有模型（包括基础模型和自定义模型）

        Returns:
            list[ModelModel]: 所有模型列表
        """
        with get_db() as db:
            return [ModelModel.model_validate(model) for model in db.query(Model).all()]

    def get_models(self) -> list[ModelUserResponse]:
        """
        获取自定义模型列表（仅 base_model_id != None 的模型）

        返回结果包含创建者的用户信息，用于前端显示模型来源

        Returns:
            list[ModelUserResponse]: 自定义模型列表（附带用户信息）
        """
        with get_db() as db:
            # 只查询自定义模型（base_model_id 不为 None）
            all_models = db.query(Model).filter(Model.base_model_id != None).all()

            # 批量获取用户信息，避免 N+1 查询问题
            user_ids = list(set(model.user_id for model in all_models))
            users = Users.get_users_by_user_ids(user_ids) if user_ids else []
            users_dict = {user.id: user for user in users}

            # 组装模型和用户信息
            models = []
            for model in all_models:
                user = users_dict.get(model.user_id)
                models.append(
                    ModelUserResponse.model_validate(
                        {
                            **ModelModel.model_validate(model).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return models

    def get_base_models(self) -> list[ModelModel]:
        """
        获取基础模型列表（仅 base_model_id == None 的模型）

        基础模型通常从外部 API（Ollama、OpenAI 等）同步而来

        Returns:
            list[ModelModel]: 基础模型列表
        """
        with get_db() as db:
            return [
                ModelModel.model_validate(model)
                for model in db.query(Model).filter(Model.base_model_id == None).all()
            ]

    def get_models_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[ModelUserResponse]:
        """
        获取用户有权限访问的模型列表

        权限判断逻辑：
        1. 用户创建的模型（user_id 匹配）
        2. 通过访问控制（access_control）授予权限的模型

        Args:
            user_id: 用户 ID
            permission: 权限类型（"read" 或 "write"，默认 "write"）

        Returns:
            list[ModelUserResponse]: 用户有权限访问的模型列表
        """
        models = self.get_models()
        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user_id)}
        return [
            model
            for model in models
            if model.user_id == user_id
            or has_access(user_id, permission, model.access_control, user_group_ids)
        ]

    def get_model_by_id(self, id: str) -> Optional[ModelModel]:
        """
        根据 ID 获取模型

        Args:
            id: 模型 ID

        Returns:
            ModelModel: 找到返回模型对象，未找到返回 None
        """
        try:
            with get_db() as db:
                model = db.get(Model, id)
                return ModelModel.model_validate(model)
        except Exception:
            return None

    def toggle_model_by_id(self, id: str) -> Optional[ModelModel]:
        """
        切换模型激活状态（启用/禁用）

        Args:
            id: 模型 ID

        Returns:
            ModelModel: 更新后的模型对象，失败返回 None
        """
        with get_db() as db:
            try:
                is_active = db.query(Model).filter_by(id=id).first().is_active

                db.query(Model).filter_by(id=id).update(
                    {
                        "is_active": not is_active,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()

                return self.get_model_by_id(id)
            except Exception:
                return None

    def update_model_by_id(self, id: str, model: ModelForm) -> Optional[ModelModel]:
        """
        更新模型配置

        Args:
            id: 模型 ID
            model: 更新后的模型数据

        Returns:
            ModelModel: 更新后的模型对象，失败返回 None
        """
        try:
            with get_db() as db:
                # 只更新 ModelForm 中包含的字段（排除 id）
                result = (
                    db.query(Model)
                    .filter_by(id=id)
                    .update(model.model_dump(exclude={"id"}))
                )
                db.commit()

                model = db.get(Model, id)
                db.refresh(model)
                return ModelModel.model_validate(model)
        except Exception as e:
            log.exception(f"Failed to update the model by id {id}: {e}")
            return None

    def delete_model_by_id(self, id: str) -> bool:
        """
        删除指定模型

        Args:
            id: 模型 ID

        Returns:
            bool: 删除成功返回 True，失败返回 False
        """
        try:
            with get_db() as db:
                db.query(Model).filter_by(id=id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_all_models(self) -> bool:
        """
        删除所有模型（危险操作，通常仅用于测试或重置）

        Returns:
            bool: 删除成功返回 True，失败返回 False
        """
        try:
            with get_db() as db:
                db.query(Model).delete()
                db.commit()

                return True
        except Exception:
            return False

    def sync_models(self, user_id: str, models: list[ModelModel]) -> list[ModelModel]:
        """
        同步模型列表 - 与外部模型源（Ollama、OpenAI 等）同步

        同步逻辑：
        1. 更新已存在的模型
        2. 插入新模型
        3. 删除不再存在的模型

        典型使用场景：
        - 从 Ollama API 获取模型列表后同步到数据库
        - 从 OpenAI API 获取模型列表后同步到数据库

        Args:
            user_id: 执行同步的用户 ID（作为模型创建者）
            models: 外部模型列表

        Returns:
            list[ModelModel]: 同步后的所有模型列表
        """
        try:
            with get_db() as db:
                # 获取现有模型
                existing_models = db.query(Model).all()
                existing_ids = {model.id for model in existing_models}

                # 准备新模型 ID 集合
                new_model_ids = {model.id for model in models}

                # 更新或插入模型
                for model in models:
                    if model.id in existing_ids:
                        # 更新已存在的模型
                        db.query(Model).filter_by(id=model.id).update(
                            {
                                **model.model_dump(),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                    else:
                        # 插入新模型
                        new_model = Model(
                            **{
                                **model.model_dump(),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                        db.add(new_model)

                # 删除不再存在的模型
                for model in existing_models:
                    if model.id not in new_model_ids:
                        db.delete(model)

                db.commit()

                return [
                    ModelModel.model_validate(model) for model in db.query(Model).all()
                ]
        except Exception as e:
            log.exception(f"Error syncing models for user {user_id}: {e}")
            return []


Models = ModelsTable()
