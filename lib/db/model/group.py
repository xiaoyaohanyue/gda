from typing import Optional
from sqlmodel import Field
from lib.db.base import ManagedBase

class GroupItem(ManagedBase, table=True):
    id: Optional[int] = Field(primary_key=True, description="ID", sa_column_kwargs={"comment": "ID"})
    chat_id: int = Field(index=True, unique=True, description="群组id", sa_column_kwargs={"comment": "会话ID"})
    enabled: bool = Field(default=True, description="是否启用", sa_column_kwargs={"comment": "是否启用"})
