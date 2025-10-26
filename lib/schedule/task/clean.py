# lib/schedule/task/clean.py
from lib.log import logger
from lib.db import run_db_session, ListItem, get_all_list_items, update_list_item
from lib.db.crud.list import promote_status, refresh_item
from lib.conf import settings
from lib.utils import get_bj_now, to_bj_aware
from lib.core.github.remote import check_download
from lib.schedule.locks import repo_lock
import os
import time
import glob
import shutil
from typing import Iterable

# 可配置的超时秒数，找不到就用 2000
DOWNLOAD_TIMEOUT_SECONDS = getattr(settings, "download_timeout_seconds", 2000)
# 默认 10 分钟，按需放到 settings 里供配置
STALE_TMP_GRACE_SECONDS = getattr(settings, "stale_tmp_grace_seconds", 1800)

def _safe_rmtree(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        # Windows 偶发文件句柄未释放，稍等再试一次
        time.sleep(0.2)
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            logger.warning(f"删除临时目录失败: {path} -> {e}")

async def cleanup_orphan_tmp_dirs() -> None:
    """
    清理断电/崩溃遗留的 *.tmp-* 临时目录；
    并把“卡在 DOWNLOADING 但临时目录不存在/为空”的仓库回退到 PENDING。
    """
    root = settings.download_root_path
    if not root or not os.path.exists(root):
        return

    now = time.time()

    # 1) 删除过期 *.tmp-* 目录（任何层级）
    removed = 0
    for tmp_dir in glob.iglob(os.path.join(root, "**", "*.tmp-*"), recursive=True):
        try:
            age = now - os.path.getmtime(tmp_dir)
        except FileNotFoundError:
            continue
        if age > STALE_TMP_GRACE_SECONDS:
            logger.info(f"清理过期临时目录: {tmp_dir} (age={int(age)}s)")
            _safe_rmtree(tmp_dir)
            removed += 1

    if removed:
        logger.info(f"本轮共清理临时目录 {removed} 个")

    # 2) 扫描 DB：若某仓库状态是 DOWNLOADING，但找不到对应 tmp 目录 → 回退为 PENDING
    items = await run_db_session(get_all_list_items)
    for item in items:
        if not item.enabled or item.status != "DOWNLOADING":
            continue

        # 临时目录前缀：<repo_dir>.tmp-
        repo_dir = os.path.join(root, item.path)
        tmp_glob = f"{repo_dir}.tmp-*"
        tmp_candidates = list(glob.iglob(tmp_glob))
        # 条件：没有任何 tmp 目录 或 所有 tmp 目录都是空/不存在
        all_empty_or_missing = True
        for d in tmp_candidates:
            if os.path.exists(d) and os.listdir(d):
                all_empty_or_missing = False
                break

        if all_empty_or_missing:
            # 加 per-repo 锁，避免和下载任务同时处理
            lock = repo_lock(item.repository)
            async with lock:
                fresh = await run_db_session(refresh_item, item.repository)
                if not fresh or fresh.status != "DOWNLOADING":
                    continue
                logger.warning(f"{item.name} 上次异常退出可能遗留，状态从 DOWNLOADING 回退为 PENDING")
                await run_db_session(
                    update_list_item,
                    item.repository,
                    status="PENDING",
                )

async def check_and_clean_downloads():
    items = await run_db_session(get_all_list_items)
    now = get_bj_now()  # aware

    for item in items:
        if not item.enabled:
            continue

        # === 处理下载超时：DOWNLOADING -> PENDING（CAS + 加锁）===
        if item.status == "DOWNLOADING":
            start_time = item.start_at
            if not start_time:
                continue

            elapsed = (now - to_bj_aware(start_time)).total_seconds()
            if elapsed <= DOWNLOAD_TIMEOUT_SECONDS:
                continue

            lock = repo_lock(item.repository)
            async with lock:
                # 锁内再读一次，确保状态未被别的任务改动
                fresh = await run_db_session(refresh_item, item.repository)
                if not fresh or fresh.status != "DOWNLOADING":
                    continue

                ok = await run_db_session(
                    promote_status,
                    item.repository,
                    "DOWNLOADING",
                    "PENDING",
                    start_at=get_bj_now(),  # 记录新一轮开始时间
                )
                if ok:
                    logger.warning(f"{item.name} 下载超时，已回退为 PENDING 等待重试")
                else:
                    logger.info(f"{item.name} 状态已被其他任务更新，跳过")

        # === 校验已完成的下载：DONE -> （FREE/回退）===
        elif item.status == "DONE":
            # check_download 内部已经加了 repo_lock
            await check_download(item)
