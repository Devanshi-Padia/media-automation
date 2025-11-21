from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema


class PostBase(BaseModel):
    title: Annotated[str, Field(min_length=2, max_length=30, examples=["This is my post"])]
    texts: dict  # {"twitter": "...", ...}
    images: dict  # {"twitter": "image_path", ...}


class Post(TimestampSchema, PostBase, UUIDSchema, PersistentDeletion):
    media_url: Annotated[
        str | None,
        Field(pattern=r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", examples=["https://www.postimageurl.com"], default=None),
    ]
    created_by_user_id: int


class PostRead(BaseModel):
    id: int
    title: Annotated[str, Field(min_length=2, max_length=30, examples=["This is my post"])]
    texts: dict
    images: dict
    media_url: Annotated[
        str | None,
        Field(examples=["https://www.postimageurl.com"], default=None),
    ]
    created_by_user_id: int
    created_at: datetime


class PostCreate(PostBase):
    model_config = ConfigDict(extra="forbid")

    media_url: Annotated[
        str | None,
        Field(pattern=r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", examples=["https://www.postimageurl.com"], default=None),
    ]


class PostCreateInternal(PostCreate):
    created_by_user_id: int


class PostUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str | None, Field(min_length=2, max_length=30, examples=["This is my updated post"], default=None)]
    texts: dict | None = None
    images: dict | None = None
    media_url: Annotated[
        str | None,
        Field(pattern=r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", examples=["https://www.postimageurl.com"], default=None),
    ]


class PostUpdateInternal(PostUpdate):
    updated_at: datetime


class PostDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime
