import json
import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, Column, BigInteger
from sqlalchemy.orm import Session

from apps.webui.internal.db import Base, JSONField, get_session

from typing import List, Union, Optional
from config import SRC_LOG_LEVELS

import time

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
    profile_image_url: Optional[str] = "/favicon.png"

    description: Optional[str] = None
    """
        User-facing description of the model.
    """

    capabilities: Optional[dict] = None

    model_config = ConfigDict(extra="allow")

    pass


class Model(Base):
    __tablename__ = "model"

    id = Column(String, primary_key=True)
    """
        The model's id as used in the API. If set to an existing model, it will override the model.
    """
    user_id = Column(String)

    base_model_id = Column(String, nullable=True)
    """
        An optional pointer to the actual model that should be used when proxying requests.
    """

    name = Column(String)
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

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class ModelModel(BaseModel):
    id: str
    user_id: str
    base_model_id: Optional[str] = None

    name: str
    params: ModelParams
    meta: ModelMeta

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ModelResponse(BaseModel):
    id: str
    name: str
    meta: ModelMeta
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class ModelForm(BaseModel):
    id: str
    base_model_id: Optional[str] = None
    name: str
    meta: ModelMeta
    params: ModelParams


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
            with get_session() as db:
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

    def get_all_models(self) -> List[ModelModel]:
        with get_session() as db:
            return [ModelModel.model_validate(model) for model in db.query(Model).all()]

    def get_model_by_id(self, id: str) -> Optional[ModelModel]:
        try:
            with get_session() as db:
                model = db.get(Model, id)
                return ModelModel.model_validate(model)
        except:
            return None

    def update_model_by_id(
        self, id: str, model: ModelForm
    ) -> Optional[ModelModel]:
        try:
            # update only the fields that are present in the model
            with get_session() as db:
                model = db.query(Model).get(id)
                model.update(**model.model_dump())
                db.commit()
                db.refresh(model)
                return ModelModel.model_validate(model)
        except Exception as e:
            print(e)

            return None

    def delete_model_by_id(self, id: str) -> bool:
        try:
            with get_session() as db:
                db.query(Model).filter_by(id=id).delete()
            return True
        except:
            return False


Models = ModelsTable()
