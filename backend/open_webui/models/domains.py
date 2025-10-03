import logging
import time
from typing import List, Optional
import uuid
import re

from open_webui.internal.db import get_db
from open_webui.models.base import Base
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, ConfigDict, validator
from sqlalchemy import BigInteger, Column, String, Text, JSON, func


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# Domain DB Schema
####################


class Domain(Base):
    __tablename__ = "domain"

    id = Column(String, primary_key=True)
    domain = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class DomainModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    domain: str
    description: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class DomainForm(BaseModel):
    domain: str
    description: Optional[str] = None

    @validator("domain")
    def validate_domain(cls, v):
        """Validate domain format"""
        if not v or not isinstance(v, str):
            raise ValueError("Domain cannot be empty")

        v = v.strip().lower()

        # Basic domain regex pattern
        domain_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"

        if not re.match(domain_pattern, v):
            raise ValueError("Invalid domain format")

        if len(v) > 253:  # Max domain length
            raise ValueError("Domain too long")

        if ".." in v:
            raise ValueError("Domain cannot contain consecutive dots")

        return v


####################
# Domain Table
####################


class DomainTable:
    def insert_new_domain(self, form_data: DomainForm) -> Optional[DomainModel]:
        with get_db() as db:
            domain_id = str(uuid.uuid4())
            timestamp = int(time.time())
            domain = Domain(
                **{
                    "id": domain_id,
                    "domain": form_data.domain,
                    "description": form_data.description,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }
            )

            try:
                db.add(domain)
                db.commit()
                db.refresh(domain)
                return DomainModel.model_validate(domain)
            except Exception as e:
                log.error(f"Error creating domain: {e}")
                db.rollback()
                return None

    def get_domains(self) -> list[DomainModel]:
        with get_db() as db:
            return [
                DomainModel.model_validate(domain)
                for domain in db.query(Domain)
                .order_by(Domain.description, Domain.domain)
                .all()
            ]

    def get_domain_by_id(self, domain_id: str) -> Optional[DomainModel]:
        with get_db() as db:
            domain = db.query(Domain).filter_by(id=domain_id).first()
            return DomainModel.model_validate(domain) if domain else None

    def get_domain_by_domain(self, domain_name: str) -> Optional[DomainModel]:
        with get_db() as db:
            domain = db.query(Domain).filter_by(domain=domain_name).first()
            return DomainModel.model_validate(domain) if domain else None

    def update_domain_by_id(
        self, domain_id: str, form_data: DomainForm
    ) -> Optional[DomainModel]:
        with get_db() as db:
            domain = db.query(Domain).filter_by(id=domain_id).first()
            if not domain:
                return None

            domain.domain = form_data.domain
            domain.description = form_data.description
            domain.updated_at = int(time.time())

            try:
                db.commit()
                db.refresh(domain)
                return DomainModel.model_validate(domain)
            except Exception as e:
                log.error(f"Error updating domain: {e}")
                db.rollback()
                return None

    def delete_domain_by_id(self, domain_id: str) -> bool:
        with get_db() as db:
            domain = db.query(Domain).filter_by(id=domain_id).first()
            if not domain:
                return False

            try:
                db.delete(domain)
                db.commit()
                return True
            except Exception as e:
                log.error(f"Error deleting domain: {e}")
                db.rollback()
                return False

    def get_available_domains(self) -> List[DomainModel]:
        """Get list of all available domains from the domains table only"""
        # Get domains from domains table only
        return self.get_domains()

    def get_available_domains_list(self) -> List[str]:
        """Get list of all available domain names as strings from domains table only"""
        return [domain.domain for domain in self.get_domains()]

    def get_available_domains_list(self) -> list[str]:
        """Get list of all available domain names as strings"""
        return [domain.domain for domain in self.get_available_domains()]


Domains = DomainTable()
