from lib.db.model import ListItem
from sqlmodel import select
from sqlalchemy import update
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional

async def get_all_list_items(session: AsyncSession) -> List[ListItem]:
    result = await session.exec(select(ListItem))
    return result.all()

async def get_list_item_by_id(session: AsyncSession, item_id: int) -> Optional[ListItem]:
    result = await session.exec(select(ListItem).where(ListItem.id == item_id))
    return result.first()

async def get_list_item_by_repository(session: AsyncSession, repository: str) -> Optional[ListItem]:
    result = await session.exec(select(ListItem).where(ListItem.repository == repository))
    return result.first()

async def create_list_item(session: AsyncSession, item: ListItem) -> ListItem:
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item

async def update_list_item(session: AsyncSession, repository: str, **kwargs) -> Optional[ListItem]:
    item = await get_list_item_by_repository(session, repository)
    if item:
        for key, value in kwargs.items():
            setattr(item, key, value)
        session.add(item)
        await session.commit()
        await session.refresh(item)
    return item

# === 新增：CAS（Compare-And-Swap）原子状态迁移 ===
async def promote_status(
    session: AsyncSession,
    repository: str,
    expect_status: str,
    next_status: str,
    **extra,
) -> bool:
    """
    只有当当前状态为 expect_status 时，才更新为 next_status。
    返回 True 表示本次迁移成功（抢到“所有权”）。
    """
    stmt = (
        update(ListItem)
        .where(ListItem.repository == repository, ListItem.status == expect_status)
        .values(status=next_status, **extra)
    )
    res = await session.exec(stmt)
    await session.commit()
    return res.rowcount == 1

async def refresh_item(session: AsyncSession, repository: str) -> Optional[ListItem]:
    """再读一次，拿到最新状态/字段"""
    return await get_list_item_by_repository(session, repository)