import time
import uuid
from functools import lru_cache
from typing import Optional

from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text
from sqlalchemy.dialects.mysql import MEDIUMTEXT

from open_webui.internal.db import Base, get_db
from open_webui.config import S3_PROMPT_BUCKET_NAME, DEFAULT_HELP_S3_KEY
from open_webui.services.s3 import get_s3_client


class Tenant(Base):
    __tablename__ = "tenant"

    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    s3_bucket = Column(String, unique=True, nullable=False)
    table_name = Column(String(255), nullable=True)
    system_config_client_name = Column(String(255), nullable=True)
    logo_image_url = Column(Text().with_variant(MEDIUMTEXT, "mysql"), nullable=True)
    help_text = Column(
        Text().with_variant(MEDIUMTEXT, "mysql"),
        nullable=False,
    )

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class TenantModel(BaseModel):
    id: str
    name: str
    s3_bucket: str
    table_name: Optional[str] = None
    system_config_client_name: Optional[str] = None
    logo_image_url: Optional[str] = None
    help_text: str
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class TenantForm(BaseModel):
    name: str
    s3_bucket: Optional[str] = None
    table_name: Optional[str] = None
    system_config_client_name: Optional[str] = None
    logo_image_url: Optional[str] = None
    help_text: Optional[str] = None


class TenantUpdateForm(BaseModel):
    name: Optional[str] = None
    s3_bucket: Optional[str] = None
    table_name: Optional[str] = None
    system_config_client_name: Optional[str] = None
    logo_image_url: Optional[str] = None
    help_text: Optional[str] = None


@lru_cache(maxsize=1)
def _get_default_help_text() -> str:
    bucket = S3_PROMPT_BUCKET_NAME
    key = DEFAULT_HELP_S3_KEY

    if not bucket or not key:
        raise RuntimeError(
            "S3_PROMPT_BUCKET_NAME and DEFAULT_HELP_S3_KEY must be configured."
        )

    client = get_s3_client()
    try:
        obj = client.get_object(Bucket=bucket, Key=key)
    except (ClientError, BotoCoreError) as exc:
        raise RuntimeError(
            f"Failed to load default help markdown from s3://{bucket}/{key}"
        ) from exc

    body = obj.get("Body")
    if not body:
        raise RuntimeError(
            f"Empty response body when loading s3://{bucket}/{key}"
        )

    return body.read().decode("utf-8")


def get_default_help_text() -> str:
    return _get_default_help_text()


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
                    "table_name": form_data.table_name,
                    "system_config_client_name": form_data.system_config_client_name,
                    "logo_image_url": form_data.logo_image_url,
                    "help_text": form_data.help_text
                    if form_data.help_text is not None
                    else _get_default_help_text(),
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

    def update_tenant(
        self, tenant_id: str, form_data: TenantUpdateForm
    ) -> Optional[TenantModel]:
        with get_db() as db:
            update_payload = {}
            if form_data.name is not None:
                update_payload["name"] = form_data.name
            if form_data.s3_bucket is not None:
                update_payload["s3_bucket"] = form_data.s3_bucket
            if form_data.table_name is not None:
                update_payload["table_name"] = form_data.table_name
            if form_data.system_config_client_name is not None:
                update_payload["system_config_client_name"] = (
                    form_data.system_config_client_name
                )
            if form_data.logo_image_url is not None:
                update_payload["logo_image_url"] = form_data.logo_image_url
            if form_data.help_text is not None:
                update_payload["help_text"] = form_data.help_text

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


Tenants = TenantsTable()
