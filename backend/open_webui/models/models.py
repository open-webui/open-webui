import logging
import time
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, JSONField, get_db, get_db_context

from open_webui.models.groups import Groups
from open_webui.models.users import User, UserModel, Users, UserResponse
from open_webui.models.access_grants import AccessGrantModel, AccessGrants


from pydantic import BaseModel, ConfigDict, Field

from sqlalchemy import String, cast, or_, and_, func
from sqlalchemy.dialects import postgresql, sqlite

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import BigInteger, Column, Text, Boolean

log = logging.getLogger(__name__)


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

    access_grants: list[AccessGrantModel] = Field(default_factory=list)

    is_active: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ModelUserResponse(ModelModel):
    user: Optional[UserResponse] = None


class ModelAccessResponse(ModelUserResponse):
    write_access: Optional[bool] = False


class ModelResponse(ModelModel):
    pass


class ModelListResponse(BaseModel):
    items: list[ModelUserResponse]
    total: int


class ModelAccessListResponse(BaseModel):
    items: list[ModelAccessResponse]
    total: int


class ModelForm(BaseModel):
    id: str
    base_model_id: Optional[str] = None
    name: str
    meta: ModelMeta
    params: ModelParams
    access_grants: Optional[list[dict]] = None
    is_active: bool = True


class ModelsTable:
    def _get_access_grants(
        self, model_id: str, db: Optional[Session] = None
    ) -> list[AccessGrantModel]:
        return AccessGrants.get_grants_by_resource("model", model_id, db=db)

    def _to_model_model(self, model: Model, db: Optional[Session] = None) -> ModelModel:
        model_data = ModelModel.model_validate(model).model_dump(
            exclude={"access_grants"}
        )
        model_data["access_grants"] = self._get_access_grants(model_data["id"], db=db)
        return ModelModel.model_validate(model_data)

    def insert_new_model(
        self, form_data: ModelForm, user_id: str, db: Optional[Session] = None
    ) -> Optional[ModelModel]:
        try:
            with get_db_context(db) as db:
                result = Model(
                    **{
                        **form_data.model_dump(exclude={"access_grants"}),
                        "user_id": user_id,
                        "created_at": int(time.time()),
                        "updated_at": int(time.time()),
                    }
                )
                db.add(result)
                db.commit()
                db.refresh(result)
                AccessGrants.set_access_grants(
                    "model", result.id, form_data.access_grants, db=db
                )

                if result:
                    return self._to_model_model(result, db=db)
                else:
                    return None
        except Exception as e:
            log.exception(f"Failed to insert a new model: {e}")
            return None

    def get_all_models(self, db: Optional[Session] = None) -> list[ModelModel]:
        with get_db_context(db) as db:
            return [
                self._to_model_model(model, db=db) for model in db.query(Model).all()
            ]

    def get_models(self, db: Optional[Session] = None) -> list[ModelUserResponse]:
        with get_db_context(db) as db:
            all_models = db.query(Model).filter(Model.base_model_id != None).all()

            user_ids = list(set(model.user_id for model in all_models))

            users = Users.get_users_by_user_ids(user_ids, db=db) if user_ids else []
            users_dict = {user.id: user for user in users}

            models = []
            for model in all_models:
                user = users_dict.get(model.user_id)
                models.append(
                    ModelUserResponse.model_validate(
                        {
                            **self._to_model_model(model, db=db).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return models

    def get_base_models(self, db: Optional[Session] = None) -> list[ModelModel]:
        with get_db_context(db) as db:
            return [
                self._to_model_model(model, db=db)
                for model in db.query(Model).filter(Model.base_model_id == None).all()
            ]

    def get_models_by_user_id(
        self, user_id: str, permission: str = "write", db: Optional[Session] = None
    ) -> list[ModelUserResponse]:
        models = self.get_models(db=db)
        user_group_ids = {
            group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
        }
        return [
            model
            for model in models
            if model.user_id == user_id
            or AccessGrants.has_access(
                user_id=user_id,
                resource_type="model",
                resource_id=model.id,
                permission=permission,
                user_group_ids=user_group_ids,
                db=db,
            )
        ]

    def _has_permission(self, db, query, filter: dict, permission: str = "read"):
        return AccessGrants.has_permission_filter(
            db=db,
            query=query,
            DocumentModel=Model,
            filter=filter,
            resource_type="model",
            permission=permission,
        )

    def search_models(
        self,
        user_id: str,
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> ModelListResponse:
        with get_db_context(db) as db:
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
                            User.name.ilike(f"%{query_key}%"),
                            User.email.ilike(f"%{query_key}%"),
                            User.username.ilike(f"%{query_key}%"),
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
                    permission="read",
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
                        **self._to_model_model(model, db=db).model_dump(),
                        user=(
                            UserResponse(**UserModel.model_validate(user).model_dump())
                            if user
                            else None
                        ),
                    )
                )

            return ModelListResponse(items=models, total=total)

    def get_model_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ModelModel]:
        try:
            with get_db_context(db) as db:
                model = db.get(Model, id)
                return self._to_model_model(model, db=db) if model else None
        except Exception:
            return None

    def get_models_by_ids(
        self, ids: list[str], db: Optional[Session] = None
    ) -> list[ModelModel]:
        try:
            with get_db_context(db) as db:
                models = db.query(Model).filter(Model.id.in_(ids)).all()
                return [self._to_model_model(model, db=db) for model in models]
        except Exception:
            return []

    def toggle_model_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ModelModel]:
        with get_db_context(db) as db:
            try:
                model = db.query(Model).filter_by(id=id).first()
                if not model:
                    return None

                model.is_active = not model.is_active
                model.updated_at = int(time.time())
                db.commit()
                db.refresh(model)

                return self._to_model_model(model, db=db)
            except Exception:
                return None

    def update_model_by_id(
        self, id: str, model: ModelForm, db: Optional[Session] = None
    ) -> Optional[ModelModel]:
        try:
            with get_db_context(db) as db:
                # update only the fields that are present in the model
                data = model.model_dump(exclude={"id", "access_grants"})
                result = db.query(Model).filter_by(id=id).update(data)

                db.commit()
                if model.access_grants is not None:
                    AccessGrants.set_access_grants(
                        "model", id, model.access_grants, db=db
                    )

                return self.get_model_by_id(id, db=db)
        except Exception as e:
            log.exception(f"Failed to update the model by id {id}: {e}")
            return None

    def delete_model_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                AccessGrants.revoke_all_access("model", id, db=db)
                db.query(Model).filter_by(id=id).delete()
                db.commit()

                return True
        except Exception:
            return False

    def delete_all_models(self, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                model_ids = [row[0] for row in db.query(Model.id).all()]
                for model_id in model_ids:
                    AccessGrants.revoke_all_access("model", model_id, db=db)
                db.query(Model).delete()
                db.commit()

                return True
        except Exception:
            return False

    def sync_models(
        self, user_id: str, models: list[ModelModel], db: Optional[Session] = None
    ) -> list[ModelModel]:
        try:
            with get_db_context(db) as db:
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
                                **model.model_dump(exclude={"access_grants"}),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                    else:
                        new_model = Model(
                            **{
                                **model.model_dump(exclude={"access_grants"}),
                                "user_id": user_id,
                                "updated_at": int(time.time()),
                            }
                        )
                        db.add(new_model)
                    AccessGrants.set_access_grants(
                        "model", model.id, model.access_grants, db=db
                    )

                # Remove models that are no longer present
                for model in existing_models:
                    if model.id not in new_model_ids:
                        AccessGrants.revoke_all_access("model", model.id, db=db)
                        db.delete(model)

                db.commit()

                return [
                    self._to_model_model(model, db=db)
                    for model in db.query(Model).all()
                ]
        except Exception as e:
            log.exception(f"Error syncing models for user {user_id}: {e}")
            return []


Models = ModelsTable()
