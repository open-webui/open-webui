import json
from pydantic import BaseModel, ConfigDict
from typing import Optional

from sqlalchemy.orm import relationship
from sqlalchemy import String, Column, Float

from open_webui.internal.db import get_db, Base

############################
# ModelCost DB Schema
############################

class ModelCost(Base):
    __tablename__ = "model_cost"

    model_name = Column(String, primary_key=True, unique=True, nullable=False)
    cost_per_million_input_tokens = Column(Float, nullable=True)
    cost_per_million_output_tokens = Column(Float, nullable=True)
    cost_per_image = Column(Float, nullable=True)
    cost_per_minute = Column(Float, nullable=True)
    cost_per_million_characters = Column(Float, nullable=True)
    cost_per_million_reasoning_tokens = Column(Float, nullable=True)
    cost_per_thousand_search_queries = Column(Float, nullable=True)


class ModelCostModel(BaseModel):
    model_name: str
    cost_per_million_input_tokens: Optional[float]
    cost_per_million_output_tokens: Optional[float]
    cost_per_image: Optional[float]
    cost_per_minute: Optional[float]
    cost_per_million_characters: Optional[float]
    cost_per_million_reasoning_tokens: Optional[float]
    cost_per_thousand_search_queries: Optional[float]


############################
# ModelCost Table
############################

class ModelCostTable:

    def get_cost_per_million_input_tokens_by_model_name(self, model_name: str):
        with get_db() as db:
            model_cost = db.query(ModelCost).filter_by(model_name=model_name).first()

            return model_cost.cost_per_million_input_tokens


    def get_cost_per_million_output_tokens_by_model_name(self, model_name: str):
        with get_db() as db:
            model_cost = db.query(ModelCost).filter_by(model_name=model_name).first()

            return model_cost.cost_per_million_output_tokens

    def get_cost_per_million_reasoning_tokens_by_model_name(self, model_name: str):
        with get_db() as db:
            model_cost = db.query(ModelCost).filter_by(model_name=model_name).first()

            return model_cost.cost_per_million_reasoning_tokens

    def get_cost_per_thousand_search_queries_by_model_name(self, model_name: str):
        with get_db() as db:
            model_cost = db.query(ModelCost).filter_by(model_name=model_name).first()

            return model_cost.cost_per_thousand_search_queries

    def get_cost_per_image_by_model_name(self, model_name: str):
        with get_db() as db:
            model_cost = db.query(ModelCost).filter_by(model_name=model_name).first()

            return model_cost.cost_per_image

    def get_cost_per_minute_tts_by_model_name(self, model_name: str):
        with get_db() as db:
            model_cost = db.query(ModelCost).filter_by(model_name=model_name).first()

            return model_cost.cost_per_minute

    def get_cost_per_million_characters_stt_by_model_name(self, model_name: str):
        with get_db() as db:
            model_cost = db.query(ModelCost).filter_by(model_name=model_name).first()

            return model_cost.cost_per_million_characters

ModelCosts = ModelCostTable()