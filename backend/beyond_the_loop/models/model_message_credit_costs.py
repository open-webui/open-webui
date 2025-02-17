import json
from pydantic import BaseModel, ConfigDict
from typing import Optional

from sqlalchemy.orm import relationship
from sqlalchemy import String, Column, Integer

from open_webui.internal.db import get_db, Base

############################
# ModelMessageCreditCost DB Schema
############################

class ModelMessageCreditCost(Base):
    __tablename__ = "model_message_credit_cost"

    model_name = Column(String, primary_key=True, unique=True, nullable=False)
    message_credit_cost = Column(Integer, nullable=False)

class ModelMessageCreditCostModel(BaseModel):
    model_name: str
    message_credit_cost: int

    model_config = ConfigDict(from_attributes=True)

############################
# ModelMessageCreditCost Table
############################

class ModelMessageCreditCostTable:
    def get_cost_by_model(self, model_name: str) -> Optional[int]:
        try:
            with get_db() as db:
                model = db.query(ModelMessageCreditCost).filter_by(model_name=model_name).first()
                return model.message_credit_cost if model else None
        except Exception as e:
            print(f"Error fetching model cost: {e}")
            return None

    def add_model_cost(self, model_name: str, cost: int) -> bool:
        try:
            with get_db() as db:
                model = ModelMessageCreditCost(model_name=model_name, message_credit_cost=cost)
                db.add(model)
                db.commit()
                return True
        except Exception as e:
            print(f"Error adding model cost: {e}")
            return False

    def update_model_cost(self, model_name: str, new_cost: int) -> bool:
        try:
            with get_db() as db:
                db.query(ModelMessageCreditCost).filter_by(model_name=model_name).update({"message_credit_cost": new_cost})
                db.commit()
                return True
        except Exception as e:
            print(f"Error updating model cost: {e}")
            return False

    def delete_model_cost(self, model_name: str) -> bool:
        try:
            with get_db() as db:
                db.query(ModelMessageCreditCost).filter_by(model_name=model_name).delete()
                db.commit()
                return True
        except Exception as e:
            print(f"Error deleting model cost: {e}")
            return False

ModelMessageCreditCosts = ModelMessageCreditCostTable()