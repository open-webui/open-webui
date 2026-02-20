"""
Tenant OAuth Configuration Models

Per-tenant OAuth credentials for multi-tenant deployments.
Each row maps a domain + provider to OAuth client credentials,
replacing the previous approach of storing these in the branding JSON blob.
"""

import logging
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import BigInteger, Column, Text, Index

from open_webui.internal.db import Base, get_db_context
from pydantic import BaseModel, ConfigDict

log = logging.getLogger(__name__)


####################
# TenantOAuthConfig DB Schema
####################


class TenantOAuthConfig(Base):
    """
    Per-tenant OAuth credentials.

    Each row maps a (domain, provider) pair to OAuth client credentials.
    The unique constraint on (domain, provider) allows a single domain
    to have configs for multiple providers in the future.
    """

    __tablename__ = "tenant_oauth_config"

    id = Column(Text, primary_key=True)
    domain = Column(Text, nullable=False)  # e.g. "chat.fiwealth.com"
    provider = Column(Text, nullable=False, default="microsoft")
    client_id = Column(Text, nullable=False)
    client_secret = Column(Text, nullable=False)
    tenant_id = Column(Text, nullable=False)  # Azure AD tenant ID
    redirect_uri = Column(Text, nullable=True)  # optional override
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("tenant_oauth_config_domain_idx", "domain"),
        Index("tenant_oauth_config_provider_idx", "provider"),
        Index(
            "tenant_oauth_config_domain_provider_unique_idx",
            "domain",
            "provider",
            unique=True,
        ),
    )


####################
# Pydantic Models
####################


class TenantOAuthConfigModel(BaseModel):
    """Internal Pydantic model for TenantOAuthConfig (includes secret)."""

    id: str
    domain: str
    provider: str
    client_id: str
    client_secret: str
    tenant_id: str
    redirect_uri: Optional[str] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class TenantOAuthConfigResponse(BaseModel):
    """API response model — NEVER exposes full client_secret."""

    id: str
    domain: str
    provider: str
    client_id: str
    client_secret_masked: str  # first 8 chars + "..."
    tenant_id: str
    redirect_uri: Optional[str] = None
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: TenantOAuthConfigModel) -> "TenantOAuthConfigResponse":
        secret = model.client_secret or ""
        masked = secret[:8] + "..." if len(secret) > 8 else "***"
        return cls(
            id=model.id,
            domain=model.domain,
            provider=model.provider,
            client_id=model.client_id,
            client_secret_masked=masked,
            tenant_id=model.tenant_id,
            redirect_uri=model.redirect_uri,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


####################
# Forms
####################


class TenantOAuthConfigForm(BaseModel):
    """Form for creating/updating a tenant OAuth config."""

    domain: str
    provider: str = "microsoft"
    client_id: str
    client_secret: str
    tenant_id: str
    redirect_uri: Optional[str] = None


####################
# Table Operations
####################


class TenantOAuthConfigTable:
    """Table operations for TenantOAuthConfig model."""

    def get_all(self, db: Optional[Session] = None) -> list[TenantOAuthConfigModel]:
        """List all tenant OAuth configs."""
        with get_db_context(db) as db:
            rows = db.query(TenantOAuthConfig).order_by(TenantOAuthConfig.domain).all()
            return [TenantOAuthConfigModel.model_validate(r) for r in rows]

    def get_by_domain(
        self, domain: str, db: Optional[Session] = None
    ) -> Optional[TenantOAuthConfigModel]:
        """Get first config matching a domain (any provider)."""
        with get_db_context(db) as db:
            row = db.query(TenantOAuthConfig).filter_by(domain=domain).first()
            return TenantOAuthConfigModel.model_validate(row) if row else None

    def get_by_domain_and_provider(
        self, domain: str, provider: str, db: Optional[Session] = None
    ) -> Optional[TenantOAuthConfigModel]:
        """Get config for a specific domain + provider pair."""
        with get_db_context(db) as db:
            row = (
                db.query(TenantOAuthConfig)
                .filter_by(domain=domain, provider=provider)
                .first()
            )
            return TenantOAuthConfigModel.model_validate(row) if row else None

    def create(
        self,
        form_data: TenantOAuthConfigForm,
        db: Optional[Session] = None,
    ) -> Optional[TenantOAuthConfigModel]:
        """Create a new tenant OAuth config."""
        with get_db_context(db) as db:
            try:
                now = int(time.time())
                row = TenantOAuthConfig(
                    id=str(uuid.uuid4()),
                    domain=form_data.domain,
                    provider=form_data.provider,
                    client_id=form_data.client_id,
                    client_secret=form_data.client_secret,
                    tenant_id=form_data.tenant_id,
                    redirect_uri=form_data.redirect_uri,
                    created_at=now,
                    updated_at=now,
                )
                db.add(row)
                db.commit()
                db.refresh(row)
                return TenantOAuthConfigModel.model_validate(row)
            except Exception as e:
                log.exception(f"Failed to create tenant OAuth config: {e}")
                db.rollback()
                return None

    def update_by_id(
        self,
        id: str,
        form_data: TenantOAuthConfigForm,
        db: Optional[Session] = None,
    ) -> Optional[TenantOAuthConfigModel]:
        """Update an existing tenant OAuth config by ID."""
        with get_db_context(db) as db:
            try:
                row = db.query(TenantOAuthConfig).filter_by(id=id).first()
                if not row:
                    return None

                row.domain = form_data.domain
                row.provider = form_data.provider
                row.client_id = form_data.client_id
                row.client_secret = form_data.client_secret
                row.tenant_id = form_data.tenant_id
                row.redirect_uri = form_data.redirect_uri
                row.updated_at = int(time.time())

                db.commit()
                db.refresh(row)
                return TenantOAuthConfigModel.model_validate(row)
            except Exception as e:
                log.exception(f"Failed to update tenant OAuth config: {e}")
                db.rollback()
                return None

    def delete_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        """Delete a tenant OAuth config by ID."""
        with get_db_context(db) as db:
            try:
                row = db.query(TenantOAuthConfig).filter_by(id=id).first()
                if not row:
                    return False

                db.delete(row)
                db.commit()
                return True
            except Exception as e:
                log.exception(f"Failed to delete tenant OAuth config: {e}")
                db.rollback()
                return False


# Singleton instance
TenantOAuthConfigs = TenantOAuthConfigTable()
