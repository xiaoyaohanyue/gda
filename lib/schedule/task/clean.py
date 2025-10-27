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

DOWNLOAD_TIMEOUT_SECONDS = getattr(settings, "download_timeout_seconds", 2000)
STALE_TMP_GRACE_SECONDS = getattr(settings, "stale_tmp_grace_seconds", 1800)

def _safe_rmtree(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        time.sleep(0.2)
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            logger.warning(f"删除临时目录失败: {path} -> {e}")

async def cleanup_orphan_tmp_dirs() -> None:
    root = settings.download_root_path
    if not root or not os.path.exists(root):
        return

    now = time.time()

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

    items = await run_db_session(get_all_list_items)
    for item in items:
        if not item.enabled or item.status != "DOWNLOADING":
            continue

        repo_dir = os.path.join(root, item.path)
        tmp_glob = f"{repo_dir}.tmp-*"
        tmp_candidates = list(glob.iglob(tmp_glob))
        all_empty_or_missing = True
        for d in tmp_candidates:
            if os.path.exists(d) and os.listdir(d):
                all_empty_or_missing = False
                break

        if all_empty_or_missing:
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
    now = get_bj_now()  

    for item in items:
        if not item.enabled:
            continue

        if item.status == "DOWNLOADING":
            start_time = item.start_at
            if not start_time:
                continue

            elapsed = (now - to_bj_aware(start_time)).total_seconds()
            if elapsed <= DOWNLOAD_TIMEOUT_SECONDS:
                continue

            lock = repo_lock(item.repository)
            async with lock:
                fresh = await run_db_session(refresh_item, item.repository)
                if not fresh or fresh.status != "DOWNLOADING":
                    continue

                ok = await run_db_session(
                    promote_status,
                    item.repository,
                    "DOWNLOADING",
                    "PENDING",
                    start_at=get_bj_now(),  
                )
                if ok:
                    logger.warning(f"{item.name} 下载超时，已回退为 PENDING 等待重试")
                else:
                    logger.info(f"{item.name} 状态已被其他任务更新，跳过")

        elif item.status == "DONE":
            await check_download(item)
