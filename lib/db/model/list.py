from typing import Optional, Dict, Any
from sqlmodel import Field
from sqlalchemy.dialects.mysql import JSON
from datetime import datetime
from sqlalchemy import Column
from lib.db.base import ManagedBase
from lib.utils.tools import get_bj_now

class ListItem(ManagedBase, table=True):
    id: Optional[int] = Field(primary_key=True, description="ID", sa_column_kwargs={"comment": "ID"})
    name: str = Field(index=True, description="名称", sa_column_kwargs={"comment": "名称"})
    version: str = Field(default='0', description="版本号", sa_column_kwargs={"comment": "版本号"})
    new_version: str = Field(default='0', description="最新版本号", sa_column_kwargs={"comment": "最新版本号"})
    repository: str = Field(unique=True, description="仓库地址", sa_column_kwargs={"comment": "仓库地址"})
    path: str = Field(description="存放子路径", sa_column_kwargs={"comment": "存放子路径"})
    status: str = Field(default="FREE", description="状态", sa_column_kwargs={"comment": "状态"})
    links: Optional[Dict[str, Any]] = Field(default=None, description="下载链接", sa_column=Column(JSON, comment="下载链接"))
    start_at: datetime = Field(default_factory=get_bj_now, description="开始时间", sa_column_kwargs={"comment": "开始时间"})
    end_at: datetime = Field(default_factory=get_bj_now, description="结束时间", sa_column_kwargs={"comment": "结束时间"})
    enabled: bool = Field(default=True, description="是否启用", sa_column_kwargs={"comment": "是否启用"})
