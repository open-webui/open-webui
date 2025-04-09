from typing import Optional

from pydantic import BaseModel, Field


class ItemPermissions(BaseModel):
    users: list[str] = Field(
        alias="user_ids",
        description="List of users who have access to the file",
        default=[],
    )
    groups: list[str] = Field(
        alias="group_ids",
        description="List of groups who have access to the file",
        default=[],
    )

    model_config = {"populate_by_name": True}


class ItemMetadata(BaseModel):
    title: str = Field(alias="itemTitle", description="Title of the item")
    url: str = Field(alias="itemUrl", description="URL of the item, direct link to it")
    context_url: Optional[str] = Field(
        alias="contextItemUrl",
        description="URL of the item's context, e.g. the page it is on",
        default=None,
    )
    date: str = Field(
        alias="itemDate",
        description="Date of the item, e.g. the date of a news article",
    )
    source: Optional[str] = Field(
        alias="itemSource",
        description="Source of the item (which workflow produced it)",
    )

    model_config = {"populate_by_name": True}


class ExtraMetadata(BaseModel):
    auth: ItemPermissions
    metadata: ItemMetadata
