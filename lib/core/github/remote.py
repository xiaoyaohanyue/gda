# lib/core/github/remote.py
import os
import time
import shutil
import asyncio
from uuid import uuid4
from typing import Dict, List

import aiohttp

from lib.log import logger
from lib.conf import settings
from lib.utils import (
    get_header,
    get_download_field,
    check_path_exists,
    count_files,
    get_bj_now,
    download_file_async,
)
from lib.db import run_db_session
from lib.db.crud.list import (
    get_all_list_items,
    update_list_item,
    refresh_item,
    promote_status,  # 需要在 crud/list.py 中新增（见之前实现）
)
from lib.schedule.locks import repo_lock  # 需要 lib/schedule/locks.py

__github_api = "https://api.github.com/repos/"
__github_api_postfix = "/releases/latest"


# ========== 工具函数 ==========
async def _safe_clear_dir(path: str) -> None:
    """安全清空目录：存在则删除，随后重建"""
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)


async def _move_all(src: str, dst: str) -> None:
    """把 src 内所有文件/子目录移动到 dst（dst 需已存在）"""
    for name in os.listdir(src):
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        shutil.move(s, d)


# ========== GitHub API ==========
async def get_remote_info(repo: str) -> Dict[str, List[str]]:
    """
    拉取 GitHub releases/latest 信息，返回：
    {
        "version": str,
        "links": List[str]
    }
    """
    infos: Dict[str, List[str] | str] = {}
    url = f"{__github_api}{repo}{__github_api_postfix}"

    try:
        github_http_header = get_header(settings.github_token)
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=github_http_header) as resp:
                resp.raise_for_status()
                # GitHub 基本会给 application/json，但保险起见：
                response = await resp.json(content_type=None)

        ver = response.get("tag_name")
        download_field = get_download_field("github")
        links = [asset[download_field] for asset in response.get("assets", []) if download_field in asset]

        infos = {
            "version": ver,
            "links": links,
        }

    except aiohttp.ClientResponseError as e:
        logger.error(f"GitHub API 请求失败 ({repo}): {e.status} {e.message}")
    except Exception as e:
        logger.error(f"获取 {repo} 仓库最新版本信息失败：{e}")

    return infos  # 失败则为空 dict


# ========== 定期检测新版本 ==========
async def fetch_github_remote_info() -> None:
    """
    遍历启用且 FREE 的条目，发现新版本则将其设为 PENDING 并写入 links/new_version。
    """
    items = await run_db_session(get_all_list_items)
    for item in items:
        if not item.enabled or item.status != "FREE":
            continue

        repo = item.repository
        info = await get_remote_info(repo)
        if not info:
            continue

        new_version = info.get("version")
        links = info.get("links", [])
        if not new_version:
            continue

        if item.version != new_version:
            logger.info(f"检测到 {item.name} 有新版本：{item.version} -> {new_version}")
            # 直接更新为 PENDING，等待下载任务处理
            await run_db_session(
                update_list_item,
                repo,
                new_version=new_version,
                links=links,
                status="PENDING",
                start_at=get_bj_now(),
            )


# ========== 下载准备与执行 ==========
async def _download_repo_links(repo_item) -> bool:
    """
    在持有 repo_lock 的前提下调用：
      - CAS: PENDING -> DOWNLOADING（抢占下载权）
      - 临时目录下载（写标记文件）
      - 校验数量
      - 替换为正式目录
      - 标记 DONE，随后交给 check_download 复核并回归 FREE/更新 version
    """
    repo = repo_item.repository
    repo_dir = os.path.join(settings.download_root_path, repo_item.path)
    tmp_dir = f"{repo_dir}.tmp-{uuid4().hex}"

    # 1) 抢占下载权（PENDING -> DOWNLOADING）
    ok = await run_db_session(
        promote_status,
        repo,
        "PENDING",
        "DOWNLOADING",
        start_at=get_bj_now(),
    )
    if not ok:
        logger.info(f"[{repo}] 已被其他任务处理，跳过")
        return False

    # 2) 读取最新数据（避免旧对象）
    fresh = await run_db_session(refresh_item, repo)
    if not fresh:
        logger.warning(f"[{repo}] 记录不存在，跳过")
        return False

    links = fresh.links or []
    if not links:
        logger.error(f"[{repo}] 下载链接不存在，重置为 FREE")
        await run_db_session(update_list_item, repo, status="FREE")
        return False

    # 3) 临时目录并发下载（写一个标记文件，方便崩溃后清理逻辑识别）
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        with open(os.path.join(tmp_dir, ".gda-started"), "w", encoding="utf-8") as f:
            f.write(str(time.time()))
    except Exception:
        pass

    # 同一仓库内控制下载并发
    sem = asyncio.Semaphore(3)

    async def _one(link: str) -> None:
        async with sem:
            filename = link.split("/")[-1]
            await download_file_async(link, filename, tmp_dir, num_threads=5)

    try:
        await asyncio.gather(*(_one(url) for url in links))
    except Exception as e:
        logger.exception(f"[{repo}] 下载出错，回滚为 PENDING：{e}")
        await run_db_session(update_list_item, repo, status="PENDING", start_at=get_bj_now())
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
        return False

    # 4) 校验数量
    downloaded_count = len(os.listdir(tmp_dir))
    if downloaded_count != len(links):
        logger.warning(f"[{repo}] 文件数不匹配({downloaded_count}/{len(links)})，设为 PENDING 等待下次补齐")
        await run_db_session(update_list_item, repo, status="PENDING", start_at=get_bj_now())
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    # 5) 切换到正式目录（清空后搬运）
    await _safe_clear_dir(repo_dir)  # 持有 repo 锁，不会并发
    await _move_all(tmp_dir, repo_dir)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # 6) 标记 DONE，由 check_download 复核并最终回归 FREE/更新 version
    await run_db_session(update_list_item, repo, status="DONE", end_at=get_bj_now())
    await check_download(fresh)  # 复用你现有的检查流程
    return True


async def prepare_github_download() -> None:
    """
    遍历启用且 PENDING 的条目：
      - 获取 per-repo 锁，确保同一仓库不会被并发处理
      - 调用 _download_repo_links 执行“CAS + 临时目录下载 + 切换 + DONE”
    """
    items = await run_db_session(get_all_list_items)
    for item in items:
        if not item.enabled or item.status != "PENDING":
            continue

        lock = repo_lock(item.repository)
        async with lock:
            # 锁内再读一次，避免锁外取到的旧状态
            fresh = await run_db_session(refresh_item, item.repository)
            if not fresh or fresh.status != "PENDING":
                continue
            logger.info(f"准备下载 {fresh.name} 新版本 {fresh.new_version}")
            await _download_repo_links(fresh)


# ========== 结果校验（保持你的原始逻辑，持锁防并发） ==========
async def check_download(item) -> None:
    """
    DONE 阶段检查：
      - 目录是否存在
      - 数量是否为 0
      - 数量是否与 links 数量一致
      - 最终回归 FREE 并更新 version
    """
    lock = repo_lock(item.repository)
    async with lock:
        download_path = os.path.join(settings.download_root_path, item.path)
        if item.status != "DONE":
            return
        if not check_path_exists(download_path):
            logger.warning(f'{item.name} 下载文件丢失，重置状态为 PENDING')
            await run_db_session(update_list_item, item.repository, status="PENDING", start_at=get_bj_now())
            return

        files_count = count_files(download_path)
        if files_count <= 0:
            logger.warning(f'{item.name} 下载文件为空，重置状态为 PENDING')
            await run_db_session(update_list_item, item.repository, status="PENDING", start_at=get_bj_now())
            return
        elif files_count != len(item.links or []):
            logger.warning(f'{item.name} 下载文件不完整，重置状态为 PENDING')
            await run_db_session(update_list_item, item.repository, status="PENDING", start_at=get_bj_now())
            return
        else:
            logger.info(f'{item.name} 下载文件完整，无需处理')
            await run_db_session(
                update_list_item,
                item.repository,
                status="FREE",
                version=item.new_version,
                end_at=get_bj_now(),
            )
            return
