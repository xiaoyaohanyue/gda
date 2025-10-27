from .registry import register
from lib.conf import settings
from lib.db import run_db_session, get_all_list_items, update_list_item, delete_list_item

@register("item", desc="调整监听的仓库", permission="admin")
async def item(event, args, client):
    """
    调整监听的仓库
    /item list - 列出所有监听的仓库
    /item enable <repository> - 启用指定仓库的监听
    /item disable <repository> - 禁用指定仓库的监听
    /item delete <repository> - 删除指定仓库的监听
    """
    if not event.is_private:
        await event.respond("此命令只能在私聊中使用。")
        return
    if len(args) == 0:
        await event.respond("用法错误，请使用 /help item 查看说明。")
        return

    tg_id = event.message.sender_id
    if tg_id != settings.admin_telegram_id:
        await event.respond("只有管理员才能使用此命令。")
        return

    action = args[0].lower()
    if action == "list":
        list_items = await run_db_session(get_all_list_items)
        if not list_items:
            await event.respond("当前没有监听的仓库。")
            return
        message = "当前监听的仓库列表：\n\n"
        for item in list_items:
            status = "启用" if item.enabled else "禁用"
            message += f"- `{item.repository}` [{status}]\n"
        await event.respond(message)
    elif action in ["enable", "disable", "delete"]:
        if len(args) != 2:
            await event.respond(f"用法错误，请使用 /item {action} <repository>。")
            return
        repository = args[1]
        if action == "delete":
            success = await run_db_session(delete_list_item, repository)
            if success:
                await event.respond(f"已删除对仓库 {repository} 的监听。")
            else:
                await event.respond(f"未找到仓库 {repository}，请检查名称是否正确。")
            return
        elif action == "enable":
            enabled = True
        else:
            enabled = False
        updated_item = await run_db_session(update_list_item, repository, enabled=enabled)
        if updated_item:
            status = "启用" if enabled else "禁用"
            await event.respond(f"已{status}对仓库 {repository} 的监听。")
        else:
            await event.respond(f"未找到仓库 {repository}，请检查名称是否正确。")
    else:
        await event.respond("用法错误，请使用 /help item 查看说明。")