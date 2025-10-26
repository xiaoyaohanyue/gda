from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.base import JobLookupError
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED, EVENT_JOB_EXECUTED
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from lib.log import logger
from uuid import uuid4
import os

from .task.repo import handle_github_repo, handle_github_download
from .task.clean import check_and_clean_downloads, cleanup_orphan_tmp_dirs


async def daily_task():
    logger.info("🧹 每日定时任务开始执行")
    logger.info("✅ 每日定时任务执行完毕")


async def min_twenty_task():
    logger.info("⏰ 每二十分钟定时任务开始执行")
    await handle_github_download()
    logger.info("✅ 每二十分钟定时任务执行完毕")


async def hourly_task():
    logger.info("⏰ 每小时定时任务开始执行")
    await handle_github_repo()
    logger.info("✅ 每小时定时任务执行完毕")


async def minutely_task():
    logger.info("⏰ 每分钟定时任务开始执行")
    logger.info("✅ 每分钟定时任务执行完毕")

async def startup_task():
    logger.info("🚀 启动后初始化任务开始执行")
    await check_and_clean_downloads()
    await handle_github_repo()
    await handle_github_download()
    logger.info("✅ 启动后初始化任务执行完毕")


def schedule_one_off(scheduler: AsyncIOScheduler, func, run_at: datetime, *,
                     args=None, kwargs=None, job_id: str | None = None) -> str:
    """
    在 run_at 执行一次 func。执行后会被监听器自动删除（id 以 'temp_' 开头）。
    返回 job_id 以便调用方追踪/取消。
    """
    tz = scheduler.timezone
    # 统一为 scheduler 的时区
    if run_at.tzinfo is None:
        try:
            run_at = tz.localize(run_at)  # 兼容 pytz
        except AttributeError:
            run_at = run_at.replace(tzinfo=tz)  # 兼容 zoneinfo
    else:
        run_at = run_at.astimezone(tz)

    jid = job_id or f"temp_{uuid4().hex}"

    scheduler.add_job(
        func,
        trigger=DateTrigger(run_date=run_at),
        id=jid,
        name=f"临时一次性任务：{func.__name__}",
        replace_existing=False,
        args=args or [],
        kwargs=kwargs or {},
    )
    return jid


def setup_scheduler():
    timezone = "Asia/Shanghai"

    # 初始化 sqlite 路径
    os.makedirs('schedule/db', exist_ok=True)
    jobstores = {
        'default': SQLAlchemyJobStore(url='sqlite:///schedule/db/jobs.sqlite')
    }

    # === 防抖与并发控制 ===
    job_defaults = {
        "coalesce": True,        # 合并错过的执行，只跑一次（比如重启后）
        "max_instances": 1,      # 同一任务仅允许一个实例，避免重入
        "misfire_grace_time": 300  # 允许错过一定时间窗口内的补跑（单位秒）
    }

    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        timezone=timezone,
        job_defaults=job_defaults,
    )

    # === 周期任务 ===
    # scheduler.add_job(daily_task, CronTrigger(hour=0, minute=0, second=0), id='normal_daily_task', name="每日定时任务", replace_existing=True)
    scheduler.add_job(hourly_task, CronTrigger(minute=0, second=0),
                      id='normal_hourly_task', name="每小时定时任务", replace_existing=True)
    
    scheduler.add_job(cleanup_orphan_tmp_dirs, IntervalTrigger(hours=1),
                      id='cleanup_tmp_periodic', name='周期清理临时目录', replace_existing=True)

    scheduler.add_job(min_twenty_task, IntervalTrigger(minutes=20),
                      id='normal_twenty_minutes_task', name="每二十分钟定时任务", replace_existing=True)

    # scheduler.add_job(minutely_task, CronTrigger(second=0), id='normal_minutely_task', name='每分钟定时任务', replace_existing=True)

    scheduler.add_job(check_and_clean_downloads, IntervalTrigger(minutes=30),
                      id='normal_clean_downloads_task', name='清理下载超时任务', replace_existing=True)
    
    boot_time = datetime.now(ZoneInfo(timezone)) + timedelta(seconds=5)
    scheduler.add_job(cleanup_orphan_tmp_dirs, DateTrigger(run_date=boot_time),
                      id='cleanup_tmp_once', name='启动后清理临时目录', replace_existing=True)


    # === 启动后一锤子“引导任务” ===
    # 把原先 main.py 里启动就跑的两件事，交给调度器一次性执行：
    boot_time = datetime.now(ZoneInfo(timezone)) + timedelta(seconds=2)
    scheduler.add_job(startup_task, DateTrigger(run_date=boot_time),
                      id='bootstrap_once', name='启动后一次性初始化', replace_existing=True)

    # === 监听错误/错过执行，便于排障 ===
    def _on_event(event):
        if event.code == EVENT_JOB_ERROR:
            logger.error(f"❌ 任务执行出错: job_id={event.job_id}")
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"⚠️ 任务错过执行: job_id={event.job_id}")

    def _auto_remove_temp_jobs(event):
        # 只清理我们定义的“临时任务”
        if event.job_id and event.job_id.startswith("temp_"):
            try:
                scheduler.remove_job(event.job_id)
            except JobLookupError:
                pass

    def _cleanup_stale_temp_jobs():
        now_tz = datetime.now(ZoneInfo(timezone))
        for job in scheduler.get_jobs():
            if job.id.startswith("temp_"):
                # DateTrigger 跑过/过期后通常 next_run_time 为 None
                if job.next_run_time is None or job.next_run_time < now_tz - timedelta(days=1):
                    try:
                        scheduler.remove_job(job.id)
                    except JobLookupError:
                        pass

    scheduler.add_listener(_on_event, EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    scheduler.add_listener(_auto_remove_temp_jobs, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    logger.info("✅ 定时任务调度器已初始化")
    _cleanup_stale_temp_jobs()
    return scheduler


# 单例调度器（供外部 import 使用）
scheduler = setup_scheduler()
