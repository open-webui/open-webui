import time
from typing import List, Optional

from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text


####################
# Webhook Config DB Schema
####################


class WebhookConfig(Base):
    __tablename__ = "webhook_config"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    events = Column(
        JSONField, nullable=False
    )  # List of event types this webhook should trigger for
    user_id = Column(
        String, nullable=True
    )  # None for global/admin webhooks, user ID for user-specific

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Forms
####################


class WebhookConfigForm(BaseModel):
    name: str
    url: str
    enabled: bool = True
    events: List[str]


class WebhookConfigUpdateForm(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    enabled: Optional[bool] = None
    events: Optional[List[str]] = None


class WebhookConfigResponse(BaseModel):
    id: str
    name: str
    url: str
    enabled: bool
    events: List[str]
    user_id: Optional[str]
    created_at: int
    updated_at: int


####################
# WebhookConfigs
####################


class WebhookConfigs:
    def __init__(self, db):
        self.db = db

    def insert_new_webhook_config(
        self,
        id: str,
        name: str,
        url: str,
        events: List[str],
        user_id: Optional[str] = None,
        enabled: bool = True,
    ) -> Optional[WebhookConfigResponse]:
        webhook_config = WebhookConfigModel(
            **{
                "id": id,
                "name": name,
                "url": url,
                "enabled": enabled,
                "events": events,
                "user_id": user_id,
            }
        )
        try:
            result = self.insert_webhook_config(webhook_config)
            if result:
                return self.get_webhook_config_by_id(id)
            else:
                return None
        except Exception:
            return None

    def insert_webhook_config(
        self, webhook_config: "WebhookConfigModel"
    ) -> Optional[WebhookConfig]:
        try:
            webhook_config_item = WebhookConfig(**webhook_config.model_dump())
            self.db.add(webhook_config_item)
            self.db.commit()
            self.db.refresh(webhook_config_item)
            return webhook_config_item
        except Exception:
            return None

    def get_webhook_configs(self) -> List[WebhookConfigResponse]:
        return [
            WebhookConfigResponse(
                id=webhook_config.id,
                name=webhook_config.name,
                url=webhook_config.url,
                enabled=webhook_config.enabled,
                events=webhook_config.events,
                user_id=webhook_config.user_id,
                created_at=webhook_config.created_at,
                updated_at=webhook_config.updated_at,
            )
            for webhook_config in self.db.query(WebhookConfig).all()
        ]

    def get_webhook_configs_by_user_id(
        self, user_id: str
    ) -> List[WebhookConfigResponse]:
        return [
            WebhookConfigResponse(
                id=webhook_config.id,
                name=webhook_config.name,
                url=webhook_config.url,
                enabled=webhook_config.enabled,
                events=webhook_config.events,
                user_id=webhook_config.user_id,
                created_at=webhook_config.created_at,
                updated_at=webhook_config.updated_at,
            )
            for webhook_config in self.db.query(WebhookConfig)
            .filter_by(user_id=user_id)
            .all()
        ]

    def get_global_webhook_configs(self) -> List[WebhookConfigResponse]:
        return [
            WebhookConfigResponse(
                id=webhook_config.id,
                name=webhook_config.name,
                url=webhook_config.url,
                enabled=webhook_config.enabled,
                events=webhook_config.events,
                user_id=webhook_config.user_id,
                created_at=webhook_config.created_at,
                updated_at=webhook_config.updated_at,
            )
            for webhook_config in self.db.query(WebhookConfig)
            .filter(WebhookConfig.user_id.is_(None))
            .all()
        ]

    def get_webhook_configs_for_event(
        self, event_type: str, user_id: Optional[str] = None
    ) -> List[WebhookConfigResponse]:
        """Get all enabled webhook configs that should trigger for the given event"""
        query = self.db.query(WebhookConfig).filter(
            WebhookConfig.enabled == True, WebhookConfig.events.contains([event_type])
        )

        # Include global webhooks and user-specific webhooks if user_id provided
        if user_id:
            query = query.filter(
                (WebhookConfig.user_id.is_(None)) | (WebhookConfig.user_id == user_id)
            )
        else:
            query = query.filter(WebhookConfig.user_id.is_(None))

        return [
            WebhookConfigResponse(
                id=webhook_config.id,
                name=webhook_config.name,
                url=webhook_config.url,
                enabled=webhook_config.enabled,
                events=webhook_config.events,
                user_id=webhook_config.user_id,
                created_at=webhook_config.created_at,
                updated_at=webhook_config.updated_at,
            )
            for webhook_config in query.all()
        ]

    def get_webhook_config_by_id(self, id: str) -> Optional[WebhookConfigResponse]:
        try:
            webhook_config = self.db.query(WebhookConfig).filter_by(id=id).first()
            return (
                WebhookConfigResponse(
                    id=webhook_config.id,
                    name=webhook_config.name,
                    url=webhook_config.url,
                    enabled=webhook_config.enabled,
                    events=webhook_config.events,
                    user_id=webhook_config.user_id,
                    created_at=webhook_config.created_at,
                    updated_at=webhook_config.updated_at,
                )
                if webhook_config
                else None
            )
        except Exception:
            return None

    def update_webhook_config_by_id(
        self, id: str, updated: dict
    ) -> Optional[WebhookConfigResponse]:
        try:
            self.db.query(WebhookConfig).filter_by(id=id).update(
                {**updated, "updated_at": int(time.time())}
            )
            self.db.commit()
            return self.get_webhook_config_by_id(id)
        except Exception:
            return None

    def delete_webhook_config_by_id(self, id: str) -> bool:
        try:
            self.db.query(WebhookConfig).filter_by(id=id).delete()
            self.db.commit()
            return True
        except Exception:
            return False


class WebhookConfigModel(BaseModel):
    id: str
    name: str
    url: str
    enabled: bool = True
    events: List[str]
    user_id: Optional[str] = None
    created_at: int = int(time.time())
    updated_at: int = int(time.time())

    model_config = ConfigDict(from_attributes=True)
