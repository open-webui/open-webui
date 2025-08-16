import logging
import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

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
    async def insert_new_model(
        self, form_data: ModelForm, user_id: str
    ) -> Optional[ModelModel]:
        model = ModelModel(
            **{
                **form_data.model_dump(),
                "user_id": user_id,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
            }
        )
        try:
            async with get_db() as db:
                result = Model(**model.model_dump())
                await db.add(result)
                await db.commit()
                await db.refresh(result)

                if result:
                    return ModelModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            log.exception(f"Failed to insert a new model: {e}")
            return None

    async def get_all_models(self) -> list[ModelModel]:
        async with get_db() as db:
            return [
                ModelModel.model_validate(model)
                for model in await db.query(Model).all()
            ]

    async def get_models(self) -> list[ModelUserResponse]:
        async with get_db() as db:
            models = []
            for model in (
                await db.query(Model).filter(Model.base_model_id != None).all()
            ):
                user = await Users.get_user_by_id(model.user_id)
                models.append(
                    ModelUserResponse.model_validate(
                        {
                            **ModelModel.model_validate(model).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return models

    async def get_base_models(self) -> list[ModelModel]:
        async with get_db() as db:
            return [
                ModelModel.model_validate(model)
                for model in await db.query(Model)
                .filter(Model.base_model_id == None)
                .all()
            ]

    async def get_models_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[ModelUserResponse]:
        models = await self.get_models()
        return [
            model
            for model in models
            if model.user_id == user_id
            or await has_access(user_id, permission, model.access_control)
        ]

    async def get_model_by_id(self, id: str) -> Optional[ModelModel]:
        try:
            async with get_db() as db:
                model = await db.get(Model, id)
                return ModelModel.model_validate(model)
        except Exception:
            return None

    async def toggle_model_by_id(self, id: str) -> Optional[ModelModel]:
        async with get_db() as db:
            try:
                is_active = (await db.query(Model).filter_by(id=id).first()).is_active

                await db.query(Model).filter_by(id=id).update(
                    {
                        "is_active": not is_active,
                        "updated_at": int(time.time()),
                    }
                )
                await db.commit()

                return await self.get_model_by_id(id)
            except Exception:
                return None

    async def update_model_by_id(
        self, id: str, model: ModelForm
    ) -> Optional[ModelModel]:
        try:
            async with get_db() as db:
                # update only the fields that are present in the model
                result = (
                    await db.query(Model)
                    .filter_by(id=id)
                    .update(model.model_dump(exclude={"id"}))
                )
                await db.commit()

                model = await db.get(Model, id)
                await db.refresh(model)
                return ModelModel.model_validate(model)
        except Exception as e:
            log.exception(f"Failed to update the model by id {id}: {e}")
            return None

    async def delete_model_by_id(self, id: str) -> bool:
        try:
            async with get_db() as db:
                await db.query(Model).filter_by(id=id).delete()
                await db.commit()

                return True
        except Exception:
            return False

    async def delete_all_models(self) -> bool:
        try:
            async with get_db() as db:
                await db.query(Model).delete()
                await db.commit()

                return True
        except Exception:
            return False

    async def sync_models(
        self, user_id: str, models: list[ModelModel]
    ) -> list[ModelModel]:
        try:
            async with get_db() as db:
                # Get existing models
                existing_models = await db.query(Model).all()
                existing_ids = {model.id for model in existing_models}

                # Prepare a set of new model IDs
                new_model_ids = {model.id for model in models}

                # Update or insert models
                for model in models:
                    if model.id in existing_ids:
                        await db.query(Model).filter_by(id=model.id).update(
                            {
                                **model.model_dump(),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                    else:
                        new_model = Model(
                            **{
                                **model.model_dump(),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                        await db.add(new_model)

                # Remove models that are no longer present
                for model in existing_models:
                    if model.id not in new_model_ids:
                        await db.delete(model)

                await db.commit()

                return [
                    ModelModel.model_validate(model)
                    for model in await db.query(Model).all()
                ]
        except Exception as e:
            log.exception(f"Error syncing models for user {user_id}: {e}")
            return []


Models = ModelsTable()
