from telethon import TelegramClient, events
from lib.conf import settings
from lib.log import logger
from lib.telegram.command import *

api_id = settings.telegram_api_id
api_hash = settings.telegram_api_hash

async def start_telegram_bot():
    client = TelegramClient(f"{settings.session_path}/bot", api_id, api_hash)
    await client.start(bot_token=settings.telegram_bot_token)

    @client.on(events.NewMessage(pattern=r'^/'))
    async def handler(event):
        text = event.message.message
        command = text.split()[0][1:]  # 去掉前面的斜杠
        if not event.is_private:
             command = command.split('@')[0]  # 处理群组中的命令
        args = text.split()[1:]  # 获取命令参数
        if command in command_list:
            command_func = command_list[command]
            await command_func(event, args, client)
        else:
            await event.respond(f"Command '{command}' not found. Available commands are: {', '.join(command_list.keys())}")

