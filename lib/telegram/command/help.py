import textwrap

from .registry import register, command_list
from lib.conf import settings


@register("help", desc="显示帮助信息")
async def help(event, args, client):
    """
    显示帮助信息
    /help - 显示所有命令
    /help <command> - 显示指定命令的帮助信息
    """
    if len(args) > 1:
        await event.respond("用法错误，请使用 /help 或 /help <command> 查看帮助信息。")
        return
    
    if len(args) == 1:
        cmd_name = args[0].lower()
        if cmd_name in command_list:
            cmd_func = command_list[cmd_name]
            doc = cmd_func.__doc__
            if doc:
                doc = textwrap.dedent(doc).strip()
                await event.respond(f"命令 /{cmd_name} 的帮助信息：\n\n{doc}")
            else:
                await event.respond(f"命令 /{cmd_name} 没有帮助信息。")
        else:
            await event.respond(f"未找到命令 /{cmd_name}，请检查命令名称是否正确。")
    else:
        tg_id = event.message.sender_id
        message = "可用的命令列表：\n\n"
        for name, func in command_list.items():
            if not getattr(func, 'hidden', False):
                permission = getattr(func, 'permission', None)
                desc = getattr(func, 'desc', None)
                if permission == 'admin':
                    if settings.admin_telegram_id != tg_id:
                        continue
                    message += f"/{name} - {desc}(管理员命令)\n"
                else:
                    message += f"/{name} - {desc}\n"
        message += "\n使用 /help <command> 查看指定命令的帮助信息。"
        await event.respond(message)