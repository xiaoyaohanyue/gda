from telethon import TelegramClient, events
from lib.conf import settings
from lib.log import logger
from lib.telegram.command import *
import asyncio


client: TelegramClient | None = None
_client_lock = asyncio.Lock()

async def start_telegram_bot():
    global client

    async with _client_lock:
        if client and client.is_connected():
            logger.info("🤖 Telegram client 已在运行，跳过重复启动。")
            return client
        
    api_id = settings.telegram_api_id
    api_hash = settings.telegram_api_hash
        
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

    await client.run_until_disconnected()
    return client

def get_telegram_client() -> TelegramClient | None:
    global client
    return client

async def send_message(chat_id: int | str, text: str):
    global client
    if not client or not client.is_connected():
        logger.warning("⚠️ Telegram client 未连接，尝试启动。")
        await start_telegram_bot()
    try:
        await client.send_message(chat_id, text)
        logger.info(f"📤 Telegram 消息已发送到 {chat_id}")
    except Exception as e:
        logger.error(f"❌ 发送 Telegram 消息失败：{e}")

