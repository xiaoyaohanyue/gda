import os, math, asyncio, aiohttp, aiofiles, sys
from typing import Optional, Tuple
from tqdm.auto import tqdm
from lib.conf import settings
from lib.utils import get_header

def _part_path(filename: str, idx: int) -> str:
    return f"{filename}.part{idx}"

async def _merge_parts(filename: str, num_parts: int) -> None:
    async with aiofiles.open(filename, "wb") as out_f:
        for i in range(num_parts):
            part_file = _part_path(filename, i)
            async with aiofiles.open(part_file, "rb") as in_f:
                while True:
                    chunk = await in_f.read(1024 * 64)
                    if not chunk:
                        break
                    await out_f.write(chunk)
            try:
                os.remove(part_file)
            except FileNotFoundError:
                pass

async def _resolve_total_and_range(session: aiohttp.ClientSession, url: str, base_headers: dict) -> Tuple[Optional[int], bool]:
    """
    优先 HEAD -> 拿不到再用 Range GET(0-0) 解析 Content-Range。
    返回: (total_size, supports_range)
    """
    try:
        async with session.head(url, allow_redirects=True, headers=base_headers) as resp:
            if resp.status == 200:
                cl = resp.headers.get("Content-Length")
                total = int(cl) if cl and cl.isdigit() else None
                supports_range = "bytes" in resp.headers.get("Accept-Ranges", "").lower()
                if total is not None:
                    return total, supports_range
    except Exception:
        pass

    headers = dict(base_headers)
    headers["Range"] = "bytes=0-0"
    try:
        async with session.get(url, headers=headers, allow_redirects=True) as resp:
            if resp.status in (200, 206):
                cr = resp.headers.get("Content-Range")  # e.g. "bytes 0-0/12345"
                total = None
                if cr and "/" in cr:
                    try:
                        total = int(cr.split("/")[-1])
                    except ValueError:
                        total = None
                return total, True  # 能走到这里基本说明支持 Range
    except Exception:
        pass

    return None, False

async def __download_chunk_async(
    session: aiohttp.ClientSession,
    url: str,
    start: int,
    end: int,
    filename: str,
    progress: Optional[tqdm],
    progress_lock: asyncio.Lock,
    base_headers: dict,
    chunk_bytes: int = 1024 * 64,
    max_retries: int = 3,
    retry_backoff: float = 0.8,
) -> None:
    headers = dict(base_headers)
    headers["Range"] = f"bytes={start}-{end}"

    # 确保分片文件存在
    if not os.path.exists(filename):
        open(filename, "wb").close()

    attempt = 0
    while True:
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status not in (200, 206):
                    raise aiohttp.ClientResponseError(
                        request_info=resp.request_info,
                        history=resp.history,
                        status=resp.status,
                        message=f"Unexpected status {resp.status} for range {start}-{end}",
                        headers=resp.headers,
                    )

                async with aiofiles.open(filename, "r+b") as fp:
                    await fp.seek(0)
                    async for chunk in resp.content.iter_chunked(chunk_bytes):
                        if not chunk:
                            continue
                        await fp.write(chunk)
                        if progress is not None:
                            # 在异步下，update 后最好 refresh 一下
                            async with progress_lock:
                                progress.update(len(chunk))
                                progress.refresh()
                break
        except (aiohttp.ClientError, asyncio.TimeoutError):
            attempt += 1
            if attempt > max_retries:
                raise
            await asyncio.sleep(retry_backoff * (2 ** (attempt - 1)))

async def download_file_async(
    url: str,
    filename: str,
    path: str,
    num_threads: int = 5,
    *,
    timeout_s: int = 60,
    chunk_bytes: int = 1024 * 64,
) -> bool:
    fullpath = os.path.join(path, filename)
    os.makedirs(path, exist_ok=True)

    base_headers = get_header(settings.github_token)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=timeout_s, sock_read=timeout_s)
    connector = aiohttp.TCPConnector(ssl=False)  # 若需严格校验证书改 True

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        total_size, supports_range = await _resolve_total_and_range(session, url, base_headers)

        # 建立进度条（total 可能为 None，先给 0；拿到后动态 reset）
        progress = tqdm(
            total=total_size or 0,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=fullpath,
            dynamic_ncols=True,
            leave=True,
            disable=not sys.stdout.isatty(),  # 若非 TTY，自动禁用
        )
        progress_lock = asyncio.Lock()

        try:
            if not supports_range:
                # 单流下载（Fallback）
                async with session.get(url, headers=base_headers) as resp:
                    resp.raise_for_status()
                    # 尝试从响应里再取一次总大小（有些服务此时给 Content-Length）
                    if total_size is None:
                        cl = resp.headers.get("Content-Length")
                        if cl and cl.isdigit():
                            total_size = int(cl)
                            progress.reset(total=total_size)
                            progress.refresh()

                    async with aiofiles.open(fullpath, "wb") as fp:
                        async for chunk in resp.content.iter_chunked(chunk_bytes):
                            if not chunk:
                                continue
                            await fp.write(chunk)
                            async with progress_lock:
                                progress.update(len(chunk))
                                progress.refresh()
                return True

            # 支持分片：如果 total 仍未知，先用一个最小 Range 再探测
            if total_size is None:
                probe_headers = dict(base_headers)
                probe_headers["Range"] = "bytes=0-0"
                async with session.get(url, headers=probe_headers) as resp:
                    cr = resp.headers.get("Content-Range")
                    if cr and "/" in cr:
                        try:
                            total_size = int(cr.split("/")[-1])
                            progress.reset(total=total_size)
                            progress.refresh()
                        except ValueError:
                            pass

            # 分片调度
            if total_size is None:
                # 保险兜底：如果还拿不到总大小，就降级为单流
                async with session.get(url, headers=base_headers) as resp:
                    resp.raise_for_status()
                    async with aiofiles.open(fullpath, "wb") as fp:
                        async for chunk in resp.content.iter_chunked(chunk_bytes):
                            if not chunk:
                                continue
                            await fp.write(chunk)
                            async with progress_lock:
                                progress.update(len(chunk))
                                progress.refresh()
                return True

            part_size = math.ceil(total_size / num_threads)
            tasks = []
            for i in range(num_threads):
                start = i * part_size
                end = min(start + part_size - 1, total_size - 1)
                part_file = _part_path(fullpath, i)
                if not os.path.exists(part_file):
                    open(part_file, "wb").close()

                tasks.append(
                    __download_chunk_async(
                        session=session,
                        url=url,
                        start=start,
                        end=end,
                        filename=part_file,
                        progress=progress,
                        progress_lock=progress_lock,
                        base_headers=base_headers,
                        chunk_bytes=chunk_bytes,
                    )
                )

            await asyncio.gather(*tasks)
            await _merge_parts(fullpath, num_threads)
            return True
        finally:
            progress.close()
