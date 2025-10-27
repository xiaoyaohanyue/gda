from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional
from lib.db.model import GroupItem
from sqlmodel import select

async def get_all_group_items(session: AsyncSession) -> List[GroupItem]:
    result = await session.exec(select(GroupItem))
    return result.all()

async def get_group_item_by_id(session: AsyncSession, item_id: int) -> Optional[GroupItem]:
    result = await session.exec(select(GroupItem).where(GroupItem.id == item_id))
    return result.first()

async def get_group_item_by_chat_id(session: AsyncSession, chat_id: str) -> Optional[GroupItem]:
    result = await session.exec(select(GroupItem).where(GroupItem.chat_id == chat_id))
    return result.first()

async def create_group_item(session: AsyncSession, item: GroupItem) -> GroupItem:
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item

async def update_group_item(session: AsyncSession, item_id: int, **kwargs) -> Optional[GroupItem]:
    item = await get_group_item_by_id(session, item_id)
    if item:
        for key, value in kwargs.items():
            setattr(item, key, value)
        session.add(item)
        await session.commit()
        await session.refresh(item)
    return item

async def update_group_item_by_chat_id(session: AsyncSession, chat_id: str, **kwargs) -> Optional[GroupItem]:
    item = await get_group_item_by_chat_id(session, chat_id)
    if item:
        for key, value in kwargs.items():
            setattr(item, key, value)
        session.add(item)
        await session.commit()
        await session.refresh(item)
    return item