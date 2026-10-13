"""External apps. Credentials never leave the internal model."""

import base64
import re
import time
from typing import Literal
from urllib.parse import urlsplit

from open_webui.internal.db import Base, get_async_db_context
from open_webui.models.access_grants import AccessGrants
from open_webui.models.channels import ChannelMember
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, field_validator, model_validator
from sqlalchemy import JSON, BigInteger, Boolean, Column, Text, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class App(Base):
    __tablename__ = 'app'

    id = Column(Text, primary_key=True)
    slug = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    user_id = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    data = Column(JSON, nullable=False)
    api_key = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class AppModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    user_id: str | None = None
    is_active: bool
    data: dict
    api_key: str | None = Field(default=None, exclude=True, repr=False)
    created_at: int
    updated_at: int


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class AppInvitation(StrictModel):
    app_id: str


Scope = Literal['channels:mentions:read', 'channels:messages:read', 'channels:messages:write', 'channels:read']


class Manifest(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=2000)
    profile_image_url: str | None = Field(default=None, max_length=196608)
    public_key: str = Field(max_length=2000)
    requested_scopes: list[Scope]

    @field_validator('profile_image_url')
    @classmethod
    def validate_profile_image_url(cls, value):
        if value is not None:
            if value.startswith('data:'):
                header, encoded = value.split(',', 1)
                if not re.fullmatch(r'data:image/(png|jpeg|gif|webp);base64', header):
                    raise ValueError('Expected a base64 PNG, JPEG, GIF or WebP data URL')
                if not base64.b64decode(encoded, validate=True):
                    raise ValueError('Profile image data must not be empty')
            else:
                url = HttpUrl(value)
                if len(value) > 2048 or url.username is not None or url.password is not None:
                    raise ValueError('Profile image URL must not contain credentials or exceed 2048 characters')
        return value

    @field_validator('public_key')
    @classmethod
    def validate_public_key(cls, value):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        key = serialization.load_pem_public_key(value.encode())
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError('An Ed25519 public key is required')
        return key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


class EmbedAuthor(StrictModel):
    name: str = Field(min_length=1, max_length=256)


class EmbedFooter(StrictModel):
    text: str = Field(min_length=1, max_length=2048)


class EmbedThumbnail(StrictModel):
    url: str = Field(max_length=2048)

    @field_validator('url')
    @classmethod
    def validate_url(cls, value):
        url = urlsplit(value)
        if (
            url.scheme not in ('http', 'https')
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or any(ord(c) <= 32 for c in value)
        ):
            raise ValueError('An HTTP(S) URL without credentials is required')
        return value


class EmbedField(StrictModel):
    name: str = Field(min_length=1, max_length=256)
    value: str = Field(min_length=1, max_length=1024)
    inline: bool = False


class Embed(StrictModel):
    title: str = Field(default='', max_length=256)
    description: str = Field(default='', max_length=4096)
    url: str | None = Field(default=None, max_length=2048)
    color: int | None = Field(default=None, strict=True, ge=0, le=0xFFFFFF)
    author: EmbedAuthor | None = None
    footer: EmbedFooter | None = None
    thumbnail: EmbedThumbnail | None = None
    fields: list[EmbedField] = Field(default_factory=list, max_length=25)

    @field_validator('url')
    @classmethod
    def validate_url(cls, value):
        return EmbedThumbnail.validate_url(value) if value is not None else None

    def add_field(self, *, name: str, value: str, inline: bool = False):
        self.fields = [*self.fields, EmbedField(name=name, value=value, inline=inline)]
        return self


class Action(StrictModel):
    action_id: str | None = Field(default=None, min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=2048)
    context: dict = Field(default_factory=dict)

    @field_validator('url')
    @classmethod
    def validate_url(cls, value):
        return EmbedThumbnail.validate_url(value) if value is not None else None

    @model_validator(mode='after')
    def check_action(self):
        if (self.action_id is None) == (self.url is None):
            raise ValueError('Provide exactly one of action_id or url')
        if self.url and self.context:
            raise ValueError('Link actions cannot have interaction context')
        return self


class AppChannelMessage(StrictModel):
    content: str = Field(default='', max_length=32000)
    actions: list[Action] = Field(default_factory=list, max_length=30)
    embeds: list[Embed] = Field(default_factory=list, max_length=10)
    reply_to_id: str | None = None
    parent_id: str | None = None

    @model_validator(mode='after')
    def check_embeds(self):
        total = sum(
            len(e.title)
            + len(e.description)
            + (len(e.author.name) if e.author else 0)
            + (len(e.footer.text) if e.footer else 0)
            + sum(len(f.name) + len(f.value) for f in e.fields)
            for e in self.embeds
        )
        if total > 6000:
            raise ValueError('Embeds must not exceed 6000 characters per message')
        return self


class AppChannelReply(AppChannelMessage):
    type: Literal['message', 'update', 'ack', 'download', 'error'] = 'message'
    visibility: Literal['private', 'channel'] = 'private'
    title: str = Field(default='', max_length=200)
    filename: str = Field(default='report.md', pattern=r'^[a-zA-Z0-9_.-]{1,100}\.md$')

    @model_validator(mode='after')
    def check_ack(self):
        if self.embeds and self.type not in ('message', 'update'):
            raise ValueError('Embeds require a message or update response')
        if self.type == 'ack' and (
            self.content or self.embeds or self.actions or self.title or self.parent_id or self.reply_to_id
        ):
            raise ValueError('Acknowledgements cannot contain a message')
        return self


class AppInteractionForm(StrictModel):
    message_id: str
    action_id: str = Field(min_length=1, max_length=100)


####################
# Forms
####################


class AppManifestForm(StrictModel):
    url: str = Field(max_length=2048)
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=4096)
    app_id: str | None = None


class AppForm(StrictModel):
    manifest: Manifest
    url: str = Field(max_length=2048)
    api_key: SecretStr = Field(min_length=1, max_length=4096)
    slug: str = Field(pattern=r'^[a-z][a-z0-9-]{0,39}$')
    granted_scopes: list[Scope]
    access_grants: list[dict] = Field(
        default_factory=lambda: [{'principal_type': 'user', 'principal_id': '*', 'permission': 'read'}]
    )


class AppUpdateForm(StrictModel):
    is_active: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    settings: dict | None = None
    manifest: Manifest | None = None
    granted_scopes: list[Scope] | None = None
    access_grants: list[dict] | None = None


class AppTokenForm(StrictModel):
    token: str = Field(max_length=1048576)


class AppConnectionForm(StrictModel):
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=4096)


####################
# Responses
####################


class AppResponse(BaseModel):
    connection_status: Literal['connecting', 'connected', 'disconnected'] = 'disconnected'
    id: str
    slug: str
    name: str
    is_active: bool
    configured: bool
    data: dict
    created_at: int
    updated_at: int


class AppAccessResponse(AppResponse):
    access_grants: list[dict] = Field(default_factory=list)


class AppsTable:
    async def get_app_by_id(self, id: str, db: AsyncSession | None = None) -> AppModel | None:
        async with get_async_db_context(db) as db:
            app = await db.scalar(select(App).where(App.id == id).execution_options(populate_existing=True))
            return AppModel.model_validate(app) if app else None

    async def get_app_ids_by_channel_id(
        self, channel_id: str, joined_before: int, db: AsyncSession | None = None
    ) -> list[str]:
        async with get_async_db_context(db) as db:
            return list(
                await db.scalars(
                    select(App.id)
                    .join(ChannelMember, ChannelMember.app_id == App.id)
                    .where(
                        App.is_active.is_(True),
                        ChannelMember.channel_id == channel_id,
                        ChannelMember.is_active.is_(True),
                        ChannelMember.joined_at <= joined_before,
                    )
                )
            )

    async def update_app_by_id(
        self,
        id: str,
        data: dict,
        access_grants: list[dict] | None = None,
        db: AsyncSession | None = None,
    ) -> AppModel | None:
        async with get_async_db_context(db) as db:
            await db.execute(update(App).where(App.id == id).values(**data))
            if access_grants is not None:
                await AccessGrants.replace_access_grants(db, 'app', id, access_grants)
            await db.commit()
            return await self.get_app_by_id(id, db=db)

    async def uninstall_app_by_id(self, id: str, db: AsyncSession | None = None) -> AppModel | None:
        async with get_async_db_context(db) as db:
            app = await db.get(App, id)
            if not app:
                return None
            app.is_active = False
            app.api_key = None
            app.data = {
                k: v for k, v in app.data.items() if k not in ('connection_token', 'installation_id', 'webui_url')
            }
            app.updated_at = max(time.time_ns(), app.updated_at + 1)
            await db.execute(
                update(ChannelMember).where(ChannelMember.app_id == id).values(is_active=False, left_at=time.time_ns())
            )
            await db.commit()
            return AppModel.model_validate(app)


Apps = AppsTable()
