import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String

from open_webui.internal.db import Base, get_db


class Tenant(Base):
    __tablename__ = "tenant"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    s3_bucket = Column(String, unique=True, nullable=False)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class TenantModel(BaseModel):
    id: str
    name: str
    s3_bucket: str
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class TenantForm(BaseModel):
    name: str
    s3_bucket: Optional[str] = None


class TenantUpdateForm(BaseModel):
    name: Optional[str] = None
    s3_bucket: Optional[str] = None


class TenantsTable:
    @staticmethod
    def _generate_bucket_name(name: str) -> str:
        return name.replace("/", " ").replace(" ", "_").lower()

    def create_tenant(self, form_data: TenantForm) -> TenantModel:
        with get_db() as db:
            bucket_name = form_data.s3_bucket or self._generate_bucket_name(
                form_data.name
            )
            tenant = TenantModel(
                **{
                    "id": str(uuid.uuid4()),
                    "name": form_data.name,
                    "s3_bucket": bucket_name,
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
            if form_data.s3_bucket is not None:
                update_payload["s3_bucket"] = form_data.s3_bucket
            if not update_payload:
                return self.get_tenant_by_id(tenant_id)

            update_payload["updated_at"] = int(time.time())
            db.query(Tenant).filter_by(id=tenant_id).update(update_payload)
            db.commit()
            tenant = db.query(Tenant).filter_by(id=tenant_id).first()
            return TenantModel.model_validate(tenant) if tenant else None

    def delete_tenant(self, tenant_id: str) -> None:
        from sqlalchemy import text
        with get_db() as db:
            db.query(Tenant).filter_by(id=tenant_id).delete()
            db.commit()
        try:
            with get_db() as db:
                db.execute(text("DELETE FROM tenant_rebuild_schedule WHERE tenant = :tenant"), {"tenant": tenant_id})
                db.commit()
        except Exception as e:
            print(f"Warning: failed to delete tenant_rebuild_schedule row for {tenant_id}: {e}")


Tenants = TenantsTable()
