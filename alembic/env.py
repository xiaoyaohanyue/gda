# migrations/env.py
from __future__ import annotations
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# ---- 读取 alembic.ini 配置 ----
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---- 应用内配置（按你的实际路径）----
from lib.conf import settings

# ---- 只迁移“受本项目管理”的 metadata ----
from lib.db.base import ManagedBase

# ⚠️ 必须 import 具体模型，确保注册到 ManagedBase.metadata
from lib.db import (
ListItem,
GroupItem,

)

target_metadata = ManagedBase.metadata

# 异步 DSN -> 同步 DSN（迁移必须用同步驱动）
def _sync_url() -> str:
    return settings.db_url.replace("asyncmy", "pymysql")

def run_migrations_offline() -> None:
    url = _sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,          # ✅ 离线分支传入
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = _sync_url()
    # 双覆盖
    config.set_main_option("sqlalchemy.url", url)
    config.set_section_option(config.config_ini_section, "sqlalchemy.url", url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
