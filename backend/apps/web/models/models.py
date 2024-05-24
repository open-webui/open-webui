import json
import logging
from typing import Optional

import peewee as pw
from playhouse.shortcuts import model_to_dict
from pydantic import BaseModel

from apps.web.internal.db import DB, JSONField

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Models DB Schema
####################


# ModelParams is a model for the data stored in the params field of the Model table
# It isn't currently used in the backend, but it's here as a reference
class ModelParams(BaseModel):
    pass


# ModelMeta is a model for the data stored in the meta field of the Model table
# It isn't currently used in the backend, but it's here as a reference
class ModelMeta(BaseModel):
    description: str
    """
        User-facing description of the model.
    """

    vision_capable: bool
    """
        A flag indicating if the model is capable of vision and thus image inputs
    """


class Model(pw.Model):
    id = pw.TextField(unique=True)
    """
        The model's id as used in the API. If set to an existing model, it will override the model.
    """

    user_id = pw.TextField()

    base_model_id = pw.TextField(null=True)
    """
        An optional pointer to the actual model that should be used when proxying requests.
        Currently unused - but will be used to support Modelfile like behaviour in the future
    """

    name = pw.TextField()
    """
        The human-readable display name of the model.
    """

    params = JSONField()
    """
        Holds a JSON encoded blob of parameters, see `ModelParams`.
    """

    meta = JSONField()
    """
        Holds a JSON encoded blob of metadata, see `ModelMeta`.
    """

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    class Meta:
        database = DB


class ModelModel(BaseModel):
    id: str
    base_model_id: Optional[str] = None
    name: str
    params: ModelParams
    meta: ModelMeta


####################
# Forms
####################


class ModelsTable:

    def __init__(
        self,
        db: pw.SqliteDatabase | pw.PostgresqlDatabase,
    ):
        self.db = db
        self.db.create_tables([Model])

    def get_all_models(self) -> list[ModelModel]:
        return [ModelModel(**model_to_dict(model)) for model in Model.select()]

    def update_all_models(self, models: list[ModelModel]) -> bool:
        try:
            with self.db.atomic():
                # Fetch current models from the database
                current_models = self.get_all_models()
                current_model_dict = {model.id: model for model in current_models}

                # Create a set of model IDs from the current models and the new models
                current_model_keys = set(current_model_dict.keys())
                new_model_keys = set(model.id for model in models)

                # Determine which models need to be created, updated, or deleted
                models_to_create = [
                    model for model in models if model.id not in current_model_keys
                ]
                models_to_update = [
                    model for model in models if model.id in current_model_keys
                ]
                models_to_delete = current_model_keys - new_model_keys

                # Perform the necessary database operations
                for model in models_to_create:
                    Model.create(**model.model_dump())

                for model in models_to_update:
                    Model.update(**model.model_dump()).where(
                        Model.id == model.id
                    ).execute()

                for model_id, model_source in models_to_delete:
                    Model.delete().where(Model.id == model_id).execute()

            return True
        except Exception as e:
            log.exception(e)
            return False


Models = ModelsTable(DB)
