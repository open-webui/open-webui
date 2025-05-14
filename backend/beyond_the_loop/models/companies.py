import json
from pydantic import BaseModel, ConfigDict
from typing import Optional

from sqlalchemy.orm import relationship
from sqlalchemy import String, Column, Text, Boolean, Float

from open_webui.internal.db import get_db, Base

# Constants
NO_COMPANY = "NO_COMPANY"
EIGHTY_PERCENT_CREDIT_LIMIT = 1

####################
# Company DB Schema
####################

class Company(Base):
    __tablename__ = "company"

    id = Column(String, primary_key=True, unique=True)
    name = Column(String, nullable=False)
    profile_image_url = Column(Text, nullable=True)
    default_model = Column(String, nullable=True)
    allowed_models = Column(Text, nullable=True)
    credit_balance = Column(Float, default=0)
    flex_credit_balance = Column(Float, nullable=True)
    auto_recharge = Column(Boolean, default=False)
    credit_card_number = Column(String, nullable=True)
    size = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    team_function = Column(String, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    budget_mail_80_sent = Column(Boolean, nullable=True)
    budget_mail_100_sent = Column(Boolean, nullable=True)

    users = relationship("User", back_populates="company", cascade="all, delete-orphan")

class CompanyModel(BaseModel):
    id: str
    name: str
    profile_image_url: Optional[str] = None
    default_model: Optional[str] = "GPT 4o"
    allowed_models: Optional[str] = None
    credit_balance: Optional[float] = 0
    flex_credit_balance: Optional[float] = None
    auto_recharge: Optional[bool] = False
    credit_card_number: Optional[str] = None
    size: Optional[str] = None
    industry: Optional[str] = None
    team_function: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    budget_mail_80_sent: Optional[bool] = False
    budget_mail_100_sent: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)

####################
# Forms
####################

class CompanyModelForm(BaseModel):
    id: str
    model_id: str

class CompanyForm(BaseModel):
    company: dict


class UpdateCompanyForm(BaseModel):
    """Request model for updating company details"""
    name: Optional[str] = None
    profile_image_url: Optional[str] = None

class CompanyConfigResponse(BaseModel):
    """Response model for company configuration"""
    config: dict

class UpdateCompanyConfigRequest(BaseModel):
    """Request model for updating company configuration"""
    hide_model_logo_in_chat: Optional[bool] = None
    chat_retention_days: Optional[int] = None
    custom_user_notice: Optional[str] = None
    features_web_search: Optional[bool] = None
    features_image_generation: Optional[bool] = None

class CompanyResponse(BaseModel):
    id: str
    name: str
    profile_image_url: Optional[str] = None
    default_model: Optional[str] = "GPT 4o"
    allowed_models: Optional[str]
    auto_recharge: bool


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


    def update_auto_recharge(self, company_id: str, auto_recharge: bool) -> Optional[CompanyModel]:

        try:
            with get_db() as db:
                company = db.query(Company).filter_by(id=company_id).first()
                if not company:
                    print(f"Company with ID {company_id} not found.")
                    return None

                db.query(Company).filter_by(id=company_id).update({"auto_recharge": auto_recharge})
                db.commit()

                updated_company = db.query(Company).filter_by(id=company_id).first()
                return CompanyModel.model_validate(updated_company)

        except Exception as e:
            print(f"Error updating auto_recharge for company {company_id}: {e}")
            return None


    def get_auto_recharge(self, company_id: str) -> Optional[bool]:
        try:
            with get_db() as db:
                company = db.query(Company).filter_by(id=company_id).first()
                if not company:
                    print(f"Company with ID {company_id} not found.")
                    return None

                return company.auto_recharge

        except Exception as e:
            print(f"Error retrieving auto_recharge for company {company_id}: {e}")
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

    def add_flex_credit_balance(self, company_id: str, credits_to_add: int) -> bool:
        """Add credits to company's balance"""
        with get_db() as db:
            company = db.query(Company).filter(Company.id == company_id).first()
            if company:
                if company.flex_credit_balance is None:
                    company.flex_credit_balance = credits_to_add
                else:
                    company.flex_credit_balance += credits_to_add
                db.commit()
                return True
            return False

    def subtract_credit_balance(self, company_id: str, credits_to_subtract: int) -> bool:
        """Subtract credits from company's balance"""
        with get_db() as db:
            company = db.query(Company).filter(Company.id == company_id).first()
            if company:
                # Initialize available credits from both balances
                credit_balance = company.credit_balance or 0
                flex_credit_balance = company.flex_credit_balance or 0
                
                # First try to subtract from credit_balance
                if credit_balance >= credits_to_subtract:
                    company.credit_balance -= credits_to_subtract
                    db.commit()
                # If credit_balance is not enough, check if combined balance is sufficient
                elif (credit_balance + flex_credit_balance) >= credits_to_subtract:
                    # Subtract what we can from credit_balance
                    remaining_credits = credits_to_subtract - credit_balance
                    company.credit_balance = 0
                    company.flex_credit_balance -= remaining_credits
                    db.commit()
                else:
                    company.credit_balance = 0
                    company.flex_credit_balance = 0
                    db.commit()

    def get_credit_balance(self, company_id: str) -> Optional[int]:
        """Get company's current credit balance"""
        with get_db() as db:
            company = db.query(Company).filter(Company.id == company_id).first()
            return company.credit_balance + (company.flex_credit_balance or 0) if company else None

    def create_company(self, company_data: dict) -> Optional[CompanyModel]:
        """Create a new company"""
        try:
            with get_db() as db:
                company = Company(**company_data)
                db.add(company)
                db.commit()
                db.refresh(company)
                return CompanyModel.model_validate(company)
        except Exception as e:
            print(f"Error creating company: {e}")
            return None

    def get_company_by_stripe_customer_id(self, stripe_customer_id: str) -> Optional[CompanyModel]:
        try:
            with get_db() as db:
                company = db.query(Company).filter_by(stripe_customer_id=stripe_customer_id).first()
                return CompanyModel.model_validate(company)
        except Exception as e:
            print(f"Error getting company by stripe_customer_id: {e}")
            return None

Companies = CompanyTable()