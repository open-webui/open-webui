import logging
import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.env import SRC_LOG_LEVELS

from beyond_the_loop.models.users import UserResponse, Users

from pydantic import BaseModel, ConfigDict

from sqlalchemy import BigInteger, Column, Text, JSON, Boolean, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import select, delete, insert


from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

user_model_bookmark = Table(
    "user_model_bookmark",
    Base.metadata,
    Column("user_id", ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    Column("model_id", ForeignKey("model.id", ondelete="CASCADE"), primary_key=True),
)


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

    tags: Optional[list[dict]] = None

    capabilities: Optional[dict] = None

    model_config = ConfigDict(extra="allow")

    pass


class Model(Base):
    __tablename__ = "model"

    id = Column(Text, primary_key=True)
    """
        The model's id as used in the API. If set to an existing model, it will override the model.
    """

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

    user_id = Column(Text, nullable=True)

    company_id = Column(Text, nullable=True)

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

    bookmarking_users = relationship(
        "User",
        secondary="user_model_bookmark",
        back_populates="model_bookmarks"
    )


class ModelModel(BaseModel):
    id: str
    base_model_id: Optional[str] = None

    name: str
    params: ModelParams
    meta: ModelMeta

    access_control: Optional[dict] = None

    is_active: bool
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    user_id: Optional[str]
    company_id: str

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################

class ModelResponse(ModelModel):
    pass

class ModelUserResponse(ModelModel):
    user: Optional[UserResponse] = None
    bookmarked_by_user: Optional[bool] = False


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
        self, form_data: ModelForm, user_id: str, company_id: str
    ) -> Optional[ModelModel]:

        model = ModelModel(
            **{
                **form_data.model_dump(),
                "company_id": company_id,
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
            print(e)
            return None

    def get_all_models_by_company(self, company_id: str) -> list[ModelModel]:
        with get_db() as db:
            return [ModelModel.model_validate(model) for model in db.query(Model).filter_by(company_id=company_id).all()]

    def get_models(self) -> list[ModelUserResponse]:
        with get_db() as db:
            models = []
            for model in db.query(Model).filter(Model.base_model_id != None).all():
                user = Users.get_user_by_id(model.user_id)
                models.append(
                    ModelUserResponse.model_validate(
                        {
                            **ModelModel.model_validate(model).model_dump(),
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return models

    def get_base_models_by_comany_and_user(self, company_id: str, user_id: str, role: str) -> list[ModelModel]:
        with get_db() as db:
            models = db.query(Model).filter(Model.base_model_id == None, Model.company_id == company_id).all()
            return [
                ModelModel.model_validate(model)
                for model in models
                if has_access(user_id, "read", model.access_control) or role == "admin"
            ]

    def get_models_by_user_and_company(
        self, user_id: str, company_id: str, permission: str = "read"
    ) -> list[ModelUserResponse]:
        with get_db() as db:
            result = db.execute(
                select(user_model_bookmark.c.model_id).where(user_model_bookmark.c.user_id == user_id)
            )
            bookmarked_model_ids = {row.model_id for row in result.fetchall()}

            all_models = self.get_models()

            filtered_models = []
            for model in all_models:
                if (
                    model.user_id == user_id
                    or (model.company_id == company_id and has_access(user_id, permission, model.access_control))
                ):
                    model_dict = model.model_dump()
                    model_dict["bookmarked_by_user"] = model.id in bookmarked_model_ids
                    filtered_models.append(ModelUserResponse(**model_dict))

            filtered_models.sort(key=lambda m: not m.bookmarked_by_user)
            return filtered_models

    def get_models_by_company_id(self, company_id: str) -> list[ModelModel]:
        models = self.get_models()
        return [model for model in models if model.company_id == company_id]

    def get_model_by_id(self, id: str) -> Optional[ModelModel]:
        try:
            with get_db() as db:
                model = db.query(Model).filter_by(id=id).first()
                return ModelModel.model_validate(model)
        except Exception:
            return None

    def get_model_by_name_and_company(self, name: str, company_id: str) -> Optional[ModelModel]:
        try:
            with get_db() as db:
                model = db.query(Model).filter_by(name=name, company_id=company_id).first()
                return ModelModel.model_validate(model)
        except Exception:
            return None

    def toggle_model_by_id_and_company(self, id: str, company_id: str) -> Optional[ModelModel]:
        with get_db() as db:
            try:
                is_active = db.query(Model).filter_by(id=id, company_id=company_id).first().is_active

                db.query(Model).filter_by(id=id, company_id=company_id).update(
                    {
                        "is_active": not is_active,
                        "updated_at": int(time.time()),
                    }
                )
                db.commit()

                return self.get_model_by_id(id)
            except Exception:
                return None

    def update_model_by_id_and_company(self, id: str, model: ModelForm, company_id: str) -> Optional[ModelModel]:
        try:
            with get_db() as db:
                # update only the fields that are present in the model
                result = (
                    db.query(Model)
                    .filter_by(id=id, company_id=company_id)
                    .update(model.model_dump(exclude={"id"}))
                )
                db.commit()

                model = db.get(Model, id)
                db.refresh(model)
                return ModelModel.model_validate(model)
        except Exception as e:
            print(e)

            return None

    def get_model_by_name_and_company(self, name: str, company_id: str) -> Optional[ModelModel]:
        try:
            with get_db() as db:
                model = db.query(Model).filter_by(name=name, company_id=company_id).first()
                return ModelModel.model_validate(model)
        except Exception:
            return None

    def delete_model_by_id_and_company(self, id: str, company_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Model).filter_by(id=id, company_id=company_id).delete()
                db.commit()

                return True
        except Exception:
            return False
        
    def toggle_bookmark(self, model_id: str, user_id: str) -> bool:
        # Check if bookmark exists
        try:
            with get_db() as db:
                exists = db.execute(
                    select(user_model_bookmark).where(
                        (user_model_bookmark.c.user_id == user_id) &
                        (user_model_bookmark.c.model_id == model_id)
                    )
                ).fetchone()

                if exists:
                    db.execute(
                        delete(user_model_bookmark).where(
                            (user_model_bookmark.c.user_id == user_id) &
                            (user_model_bookmark.c.model_id == model_id)
                        )
                    )
                    db.commit()
                    return False  # Bookmark was removed
                else:
                    db.execute(
                        insert(user_model_bookmark).values(
                            user_id=user_id,
                            model_id=model_id
                        )
                    )
                    db.commit()
                    return True
        
        except Exception:
            return None


Models = ModelsTable()
