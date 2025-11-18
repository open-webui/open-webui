import time
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import BigInteger, Column, String

from open_webui.internal.db import Base, JSONField, get_db


class Tenant(Base):
    __tablename__ = "tenant"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    model_names = Column(JSONField, nullable=False)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class TenantModel(BaseModel):
    id: str
    name: str
    model_names: List[str] = Field(default_factory=list)
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class TenantForm(BaseModel):
    name: str
    model_names: List[str] = Field(default_factory=list)


class TenantUpdateForm(BaseModel):
    name: Optional[str] = None
    model_names: Optional[List[str]] = None


class TenantsTable:
    def create_tenant(self, form_data: TenantForm) -> TenantModel:
        with get_db() as db:
            tenant = TenantModel(
                **{
                    "id": str(uuid.uuid4()),
                    "name": form_data.name,
                    "model_names": form_data.model_names,
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            result = Tenant(**tenant.model_dump())
            db.add(result)
            db.commit()
            db.refresh(result)
            return TenantModel.model_validate(result)

    def get_tenant_by_id(self, tenant_id: str) -> Optional[TenantModel]:
        with get_db() as db:
            tenant = db.query(Tenant).filter_by(id=tenant_id).first()
            return TenantModel.model_validate(tenant) if tenant else None

    def get_tenant_by_name(self, name: str) -> Optional[TenantModel]:
        with get_db() as db:
            tenant = db.query(Tenant).filter_by(name=name).first()
            return TenantModel.model_validate(tenant) if tenant else None

    def get_tenants(self) -> list[TenantModel]:
        with get_db() as db:
            return [
                TenantModel.model_validate(tenant)
                for tenant in db.query(Tenant).order_by(Tenant.updated_at.desc()).all()
            ]

    def update_tenant(self, tenant_id: str, form_data: TenantUpdateForm) -> Optional[TenantModel]:
        with get_db() as db:
            update_payload = {}
            if form_data.name is not None:
                update_payload["name"] = form_data.name
            if form_data.model_names is not None:
                update_payload["model_names"] = form_data.model_names
            if not update_payload:
                return self.get_tenant_by_id(tenant_id)

            update_payload["updated_at"] = int(time.time())
            db.query(Tenant).filter_by(id=tenant_id).update(update_payload)
            db.commit()
            tenant = db.query(Tenant).filter_by(id=tenant_id).first()
            return TenantModel.model_validate(tenant) if tenant else None

    def delete_tenant(self, tenant_id: str) -> None:
        with get_db() as db:
            db.query(Tenant).filter_by(id=tenant_id).delete()
            db.commit()

    def get_model_names_for_tenant(self, tenant_id: str) -> list[str]:
        tenant = self.get_tenant_by_id(tenant_id)
        return tenant.model_names if tenant else []

    def get_all_model_names(self) -> list[str]:
        names: set[str] = set()
        for tenant in self.get_tenants():
            names.update(tenant.model_names or [])
        return sorted(names)


Tenants = TenantsTable()
