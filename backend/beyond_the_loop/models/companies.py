import json
from pydantic import BaseModel, ConfigDict
from typing import Optional

from sqlalchemy.orm import relationship
from sqlalchemy import String, Column, Text

from open_webui.internal.db import get_db, Base

# Constants
NO_COMPANY = "NO_COMPANY"

####################
# Company DB Schema
####################

class Company(Base):
    __tablename__ = "company"

    id = Column(String, primary_key=True, unique=True)
    name = Column(String, nullable=False)
    profile_image_url = Column(Text, nullable=True)
    default_model = Column(String, default="GPT 4o")
    allowed_models = Column(Text, nullable=True)
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")

class CompanyModel(BaseModel):
    id: str
    name: str
    profile_image_url: Optional[str] = None
    default_model: Optional[str] = "GPT 4o"
    allowed_models: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

####################
# Forms
####################

class CompanyModelForm(BaseModel):
    id: str
    model_id: str

class CompanyForm(BaseModel):
    company: dict


class CompanyResponse(BaseModel):
    id: str
    name: str
    profile_image_url: str
    default_model: Optional[str] = "GPT 4o"
    allowed_models: Optional[str]


class CompanyTable:
    def get_company_by_id(self, company_id: str):
        try:
            with get_db() as db:
                company = db.query(Company).filter_by(id=company_id).first()
                return CompanyModel.model_validate(company)
        except Exception as e:
            print(f"Error getting company: {e}")
            return None
        
    def update_company_by_id(self, id: str, updated: dict) -> Optional[CompanyModel]:
        try:
            with get_db() as db:
                db.query(Company).filter_by(id=id).update(updated)
                db.commit()

                company = db.query(Company).filter_by(id=id).first()
                return CompanyModel.model_validate(company)
            
        except Exception as e:
            print(f"Error updating company", e)
            return None
        
        
    def add_model(self, company_id: str, model_id: str) -> bool:
        try:
            with get_db() as db:
                # Fetch the company by its ID
                company = db.query(Company).filter_by(id=company_id).first()
                print("Company: ", company.allowed_models)
                # If company doesn't exist, return False
                if not company:
                    return None
                
                company.allowed_models = '[]' if company.allowed_models is None else company.allowed_models
                # Load current members from JSON
                current_models = json.loads(company.allowed_models)

                # If model_id is not already in the list, add it
                if model_id not in current_models:
                    current_models.append(model_id)

                    payload = {"allowed_models": json.dumps(current_models)}
                    db.query(Company).filter_by(id=company_id).update(payload)
                    db.commit()

                    return True
                else:
                    # Model already exists in the company
                    return False
        except Exception as e:
            # Handle exceptions if any
            print("ERRRO::: ", e)
            return False

    def remove_model(self, company_id: str, model_id: str) -> bool:
        try:
            with get_db() as db:
                # Fetch the company by its ID
                company = db.query(Company).filter_by(id=company_id).first()
                
                # If company doesn't exist, return False
                if not company:
                    return None
                
                # Load current members from JSON
                current_models = json.loads(company.allowed_models)
                
                # If model_id is in the list, remove it
                if model_id in current_models:
                    current_models.remove(model_id)
                    
                    payload = {"allowed_models": json.dumps(current_models)}
                    db.query(Company).filter_by(id=company_id).update(payload)
                    db.commit()
                    return True
                else:
                    # Member not found in the company
                    return False
        except Exception as e:
            # Handle exceptions if any
            return False

        

Companies = CompanyTable()