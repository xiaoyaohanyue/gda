# main.py
import asyncio
import signal

from lib.init import boot
from lib.schedule import scheduler
from lib.log import logger


async def main():
    # 1) 应用启动（数据库、配置等）
    await boot()

    # 2) 仅启动调度器（所有任务由 scheduler 统一调度，包括一次性的“开机初始化”）
    scheduler.start()
    logger.info("✅ Scheduler started")

    # 3) 优雅退出
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            # Windows 某些环境可能不支持信号处理
            pass

    await stop.wait()
    logger.info("🛑 Shutting down...")

    # APScheduler 3.x 的 AsyncIOScheduler.shutdown 是同步方法
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        logger.exception("Scheduler shutdown failed")


if __name__ == "__main__":
    asyncio.run(main())
