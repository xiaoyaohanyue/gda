import asyncio
import signal

from lib.init import boot
from lib.schedule import scheduler
from lib.log import logger
from lib.telegram import start_telegram_bot  


async def run_bg(coro, name: str):
    """后台守护：避免任务异常把事件循环打崩。"""
    try:
        await coro
    except Exception:
        logger.exception(f"[BG] {name} crashed")


async def main():
    # 1) 应用启动（数据库、配置等）
    await boot()

    # 2) 启动 APScheduler
    scheduler.start()
    logger.info("✅ Scheduler started")

    # 3) 启动 Telegram 机器人（后台运行）
    telegram_started = False
    if not telegram_started:
        asyncio.create_task(run_bg(start_telegram_bot(), "telegram_bot"))
        telegram_started = True

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    await stop.wait()
    logger.info("🛑 Shutting down...")

    try:
        scheduler.shutdown(wait=False)
    except Exception:
        logger.exception("Scheduler shutdown failed")


if __name__ == "__main__":
    asyncio.run(main())
