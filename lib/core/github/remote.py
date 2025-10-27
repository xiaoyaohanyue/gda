
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
from lib.db import (
    run_db_session,
    get_all_list_items,
    update_list_item,
    refresh_item,
    promote_status,  
    get_all_group_items
)
from lib.telegram.core import send_message  
from lib.schedule.locks import repo_lock  

__github_api = "https://api.github.com/repos/"
__github_api_postfix = "/releases/latest"


async def _safe_clear_dir(path: str) -> None:
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)


async def _move_all(src: str, dst: str) -> None:
    for name in os.listdir(src):
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        shutil.move(s, d)


async def get_remote_info(repo: str) -> Dict[str, List[str]]:
    infos: Dict[str, List[str] | str] = {}
    url = f"{__github_api}{repo}{__github_api_postfix}"

    try:
        github_http_header = get_header(settings.github_token)
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=github_http_header) as resp:
                resp.raise_for_status()
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

    return infos 


async def fetch_github_remote_info() -> None:
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
            await run_db_session(
                update_list_item,
                repo,
                new_version=new_version,
                links=links,
                status="PENDING",
                start_at=get_bj_now(),
            )


async def _download_repo_links(repo_item) -> bool:
    repo = repo_item.repository
    repo_dir = os.path.join(settings.download_root_path, repo_item.path)
    tmp_dir = f"{repo_dir}.tmp-{uuid4().hex}"

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

    fresh = await run_db_session(refresh_item, repo)
    if not fresh:
        logger.warning(f"[{repo}] 记录不存在，跳过")
        return False

    links = fresh.links or []
    if not links:
        logger.error(f"[{repo}] 下载链接不存在，重置为 FREE")
        await run_db_session(update_list_item, repo, status="FREE")
        return False

    os.makedirs(tmp_dir, exist_ok=True)
    try:
        with open(os.path.join(tmp_dir, ".gda-started"), "w", encoding="utf-8") as f:
            f.write(str(time.time()))
    except Exception:
        pass

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

    downloaded_count = len(os.listdir(tmp_dir))
    if check_path_exists(os.path.join(tmp_dir, ".gda-started")):
        downloaded_count -= 1
    if downloaded_count != len(links):
        logger.warning(f"[{repo}] 文件数不匹配({downloaded_count}/{len(links)})，设为 PENDING 等待下次补齐")
        await run_db_session(update_list_item, repo, status="PENDING", start_at=get_bj_now())
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return False

    await _safe_clear_dir(repo_dir) 
    await _move_all(tmp_dir, repo_dir)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    await run_db_session(update_list_item, repo, status="DONE", end_at=get_bj_now())
    return True


async def prepare_github_download() -> None:
    items = await run_db_session(get_all_list_items)
    for item in items:
        if not item.enabled or item.status != "PENDING":
            continue

        lock = repo_lock(item.repository)
        async with lock:
            fresh = await run_db_session(refresh_item, item.repository)
            if not fresh or fresh.status != "PENDING":
                continue
            logger.info(f"准备下载 {fresh.name} 新版本 {fresh.new_version}")
            ok = await _download_repo_links(fresh)
        
        if ok:
            await check_download(fresh)


async def check_download(item) -> None:
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
        if check_path_exists(os.path.join(download_path, ".gda-started")):
            files_count -= 1 
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
            chats = await run_db_session(get_all_group_items)
            for group in chats:
                if group.enabled:
                    await send_message(
                        group.chat_id,
                        f'{item.name} 下载完成，版本 {item.version} -> {item.new_version}'
                    )   
            await run_db_session(
                update_list_item,
                item.repository,
                status="FREE",
                version=item.new_version,
                end_at=get_bj_now(),
            )
            return
