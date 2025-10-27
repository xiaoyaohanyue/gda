from .registry import register
from lib.conf import settings
from lib.db import run_db_session, create_group_item, get_group_item_by_chat_id, update_group_item_by_chat_id

@register("notice", desc="启用或关闭通知", permission="admin")
async def notice(event, args, client):
    """
    启用或关闭通知
    /notice on - 启用通知
    /notice off - 关闭通知
    """
    if event.is_private:
        await event.respond("此命令只能在群组中使用。")
        return
    if len(args) != 1 or args[0] not in ["on", "off"]:
        await event.respond("用法错误，请使用 /notice on 或 /notice off 来启用或关闭通知。")
        return
    tg_id = event.message.sender_id
    if tg_id != settings.admin_telegram_id:
        await event.respond("只有管理员才能使用此命令。")
        return
    chat_id = event.chat_id
    action = args[0]

    group_item = await run_db_session(get_group_item_by_chat_id, chat_id)
    if action == "on":
        if group_item is None:
            group_item = await run_db_session(create_group_item, chat_id=chat_id)
        else:
            group_item = await run_db_session(update_group_item_by_chat_id, chat_id, enabled=True)
        await event.respond("已启用通知。")
    else:  
        if group_item is None:
            await event.respond("通知处于关闭状态。")
        else:
            group_item = await run_db_session(update_group_item_by_chat_id, chat_id, enabled=False)
            await event.respond("已关闭通知。")
    
    



