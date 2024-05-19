import json
import logging
from typing import Optional

import peewee as pw
from playhouse.shortcuts import model_to_dict
from pydantic import BaseModel

from apps.web.internal.db import DB

from config import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Models DB Schema
####################


# ModelParams is a model for the data stored in the params field of the Model table
# It isn't currently used in the backend, but it's here as a reference
class ModelParams(BaseModel):
    description: str
    """
        User-facing description of the model.
    """

    vision_capable: bool
    """
        A flag indicating if the model is capable of vision and thus image inputs
    """


class Model(pw.Model):
    id = pw.TextField()
    """
        The model's id as used in the API. If set to an existing model, it will override the model.
    """

    source = pw.TextField()
    """
    The source of the model, e.g., ollama, openai, or litellm.
    """

    base_model = pw.TextField(null=True)
    """
    An optional pointer to the actual model that should be used when proxying requests.
    Currently unused - but will be used to support Modelfile like behaviour in the future
    """

    name = pw.TextField()
    """
    The human-readable display name of the model.
    """

    params = pw.TextField()
    """
    Holds a JSON encoded blob of parameters, see `ModelParams`.
    """

    class Meta:
        database = DB

        indexes = (
            # Create a unique index on the id, source columns
            (("id", "source"), True),
        )


class ModelModel(BaseModel):
    id: str
    source: str
    base_model: Optional[str] = None
    name: str
    params: str

    def to_form(self) -> "ModelForm":
        return ModelForm(**{**self.model_dump(), "params": json.loads(self.params)})


####################
# Forms
####################


class ModelForm(BaseModel):
    id: str
    source: str
    base_model: Optional[str] = None
    name: str
    params: dict

    def to_db_model(self) -> ModelModel:
        return ModelModel(**{**self.model_dump(), "params": json.dumps(self.params)})


class ModelsTable:

    def __init__(
        self,
        db: pw.SqliteDatabase | pw.PostgresqlDatabase,
    ):
        self.db = db
        self.db.create_tables([Model])

    def get_all_models(self) -> list[ModelModel]:
        return [ModelModel(**model_to_dict(model)) for model in Model.select()]

    def get_all_models_by_source(self, source: str) -> list[ModelModel]:
        return [
            ModelModel(**model_to_dict(model))
            for model in Model.select().where(Model.source == source)
        ]

    def update_all_models(self, models: list[ModelForm]) -> bool:
        try:
            with self.db.atomic():
                # Fetch current models from the database
                current_models = self.get_all_models()
                current_model_dict = {
                    (model.id, model.source): model for model in current_models
                }

                # Create a set of model IDs and sources from the current models and the new models
                current_model_keys = set(current_model_dict.keys())
                new_model_keys = set((model.id, model.source) for model in models)

                # Determine which models need to be created, updated, or deleted
                models_to_create = [
                    model
                    for model in models
                    if (model.id, model.source) not in current_model_keys
                ]
                models_to_update = [
                    model
                    for model in models
                    if (model.id, model.source) in current_model_keys
                ]
                models_to_delete = current_model_keys - new_model_keys

                # Perform the necessary database operations
                for model in models_to_create:
                    Model.create(**model.to_db_model().model_dump())

                for model in models_to_update:
                    Model.update(**model.to_db_model().model_dump()).where(
                        (Model.id == model.id) & (Model.source == model.source)
                    ).execute()

                for model_id, model_source in models_to_delete:
                    Model.delete().where(
                        (Model.id == model_id) & (Model.source == model_source)
                    ).execute()

            return True
        except Exception as e:
            log.exception(e)
            return False


Models = ModelsTable(DB)
