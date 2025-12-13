import logging
import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, Users, UserResponse


from pydantic import BaseModel, ConfigDict

from sqlalchemy import String, cast, or_, and_, func
from sqlalchemy.dialects import postgresql, sqlite

from sqlalchemy.dialects.postgresql import JSONB
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

    id = Column(Text, primary_key=True, unique=True)
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


class ModelListResponse(BaseModel):
    items: list[ModelUserResponse]
    total: int


class ModelForm(BaseModel):
    id: str
    base_model_id: Optional[str] = None
    name: str
    meta: ModelMeta
    params: ModelParams
    access_control: Optional[dict] = None
    is_active: bool = True


class ModelsTable:
    def insert_new_model(
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
        with get_db() as db:
            return [ModelModel.model_validate(model) for model in db.query(Model).all()]

    def get_models(self) -> list[ModelUserResponse]:
        with get_db() as db:
            all_models = db.query(Model).filter(Model.base_model_id != None).all()

            user_ids = list(set(model.user_id for model in all_models))

            users = Users.get_users_by_user_ids(user_ids) if user_ids else []
            users_dict = {user.id: user for user in users}

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
        with get_db() as db:
            return [
                ModelModel.model_validate(model)
                for model in db.query(Model).filter(Model.base_model_id == None).all()
            ]

    def get_models_by_user_id(
        self, user_id: str, permission: str = "write"
    ) -> list[ModelUserResponse]:
        models = self.get_models()
        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user_id)}
        return [
            model
            for model in models
            if model.user_id == user_id
            or has_access(user_id, permission, model.access_control, user_group_ids)
        ]

    def _has_permission(self, db, query, filter: dict, permission: str = "read"):
        group_ids = filter.get("group_ids", [])
        user_id = filter.get("user_id")

        dialect_name = db.bind.dialect.name

        # Public access
        conditions = []
        if group_ids or user_id:
            conditions.extend(
                [
                    Model.access_control.is_(None),
                    cast(Model.access_control, String) == "null",
                ]
            )

        # User-level permission
        if user_id:
            conditions.append(Model.user_id == user_id)

        # Group-level permission
        if group_ids:
            group_conditions = []
            for gid in group_ids:
                if dialect_name == "sqlite":
                    group_conditions.append(
                        Model.access_control[permission]["group_ids"].contains([gid])
                    )
                elif dialect_name == "postgresql":
                    group_conditions.append(
                        cast(
                            Model.access_control[permission]["group_ids"],
                            JSONB,
                        ).contains([gid])
                    )
            conditions.append(or_(*group_conditions))

        if conditions:
            query = query.filter(or_(*conditions))

        return query

    def search_models(
        self, user_id: str, filter: dict = {}, skip: int = 0, limit: int = 30
    ) -> ModelListResponse:
        with get_db() as db:
            # Join GroupMember so we can order by group_id when requested
            query = db.query(Model, User).outerjoin(User, User.id == Model.user_id)
            query = query.filter(Model.base_model_id != None)

            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(
                        or_(
                            Model.name.ilike(f"%{query_key}%"),
                            Model.base_model_id.ilike(f"%{query_key}%"),
                        )
                    )

                view_option = filter.get("view_option")
                if view_option == "created":
                    query = query.filter(Model.user_id == user_id)
                elif view_option == "shared":
                    query = query.filter(Model.user_id != user_id)

                # Apply access control filtering
                query = self._has_permission(
                    db,
                    query,
                    filter,
                    permission="write",
                )

                tag = filter.get("tag")
                if tag:
                    # TODO: This is a simple implementation and should be improved for performance
                    like_pattern = f'%"{tag.lower()}"%'  # `"tag"` inside JSON array
                    meta_text = func.lower(cast(Model.meta, String))

                    query = query.filter(meta_text.like(like_pattern))

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by == "name":
                    if direction == "asc":
                        query = query.order_by(Model.name.asc())
                    else:
                        query = query.order_by(Model.name.desc())
                elif order_by == "created_at":
                    if direction == "asc":
                        query = query.order_by(Model.created_at.asc())
                    else:
                        query = query.order_by(Model.created_at.desc())
                elif order_by == "updated_at":
                    if direction == "asc":
                        query = query.order_by(Model.updated_at.asc())
                    else:
                        query = query.order_by(Model.updated_at.desc())

            else:
                query = query.order_by(Model.created_at.desc())

            # Count BEFORE pagination
            total = query.count()

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            items = query.all()

            models = []
            for model, user in items:
                models.append(
                    ModelUserResponse(
                        **ModelModel.model_validate(model).model_dump(),
                        user=(
                            UserResponse(**UserModel.model_validate(user).model_dump())
                            if user
                            else None
                        ),
                    )
                )

            return ModelListResponse(items=models, total=total)

    def get_model_by_id(self, id: str) -> Optional[ModelModel]:
        try:
            with get_db() as db:
                model = db.get(Model, id)
                return ModelModel.model_validate(model)
        except Exception:
            return None

    def toggle_model_by_id(self, id: str) -> Optional[ModelModel]:
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
        try:
            with get_db() as db:
                # update only the fields that are present in the model
                data = model.model_dump(exclude={"id"})
                result = db.query(Model).filter_by(id=id).update(data)

                db.commit()

                model = db.get(Model, id)
                db.refresh(model)
                return ModelModel.model_validate(model)
        except Exception as e:
            log.exception(f"Failed to update the model by id {id}: {e}")
            return None

    def delete_model_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Model).filter_by(id=id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_all_models(self) -> bool:
        try:
            with get_db() as db:
                db.query(Model).delete()
                db.commit()

                return True
        except Exception:
            return False

    def sync_models(self, user_id: str, models: list[ModelModel]) -> list[ModelModel]:
        try:
            with get_db() as db:
                # Get existing models
                existing_models = db.query(Model).all()
                existing_ids = {model.id for model in existing_models}

                # Prepare a set of new model IDs
                new_model_ids = {model.id for model in models}

                # Update or insert models
                for model in models:
                    if model.id in existing_ids:
                        db.query(Model).filter_by(id=model.id).update(
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
                        db.add(new_model)

                # Remove models that are no longer present
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
