from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import requests
from .http_made import get_header
from lib.conf import settings
from tqdm import tqdm
import os
import threadpool
from lib.log import logger

BJ = ZoneInfo("Asia/Shanghai")

def get_bj_now():
    return datetime.now(BJ)

def to_bj_aware(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=BJ)
    return dt.astimezone(BJ)

def get_download_field(filter: str="github") -> str:
    mapping = {
        "github": "browser_download_url",
    }
    return mapping.get(filter.lower(), "browser_download_url")

def delete_file(filepath: str) -> None:
    '''删除指定路径下所有内容，包括子文件夹，无论是否为空'''
    if os.path.isfile(filepath):
        os.remove(filepath)
    elif os.path.isdir(filepath):
        for item in os.listdir(filepath):
            item_path = os.path.join(filepath, item)
            delete_file(item_path)
        os.rmdir(filepath)

def check_path_exists(path: str) -> bool:
    return os.path.exists(path)

def __download_chunk(url, start, end, filename, progress) -> None:
        headers = get_header(settings.github_token)
        headers.update({'Range': f'bytes={start}-{end}'})
        r = requests.get(url, headers=headers, stream=True)
        # chunk_size = end - start + 1
        with open(filename, "r+b") as fp:
            # fp.seek(start)
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    fp.write(chunk)
                    progress.update(len(chunk))

def count_files(path: str) -> int:
    try:
        all_items = os.listdir(path)
        file_count = sum(1 for item in all_items if os.path.isfile(os.path.join(path, item)))
        return file_count
    except FileNotFoundError:
        logger.error(f'{path}路径不存在！！！')
        return 0
    except Exception as e:
        logger.error(f'发生错误！！！{e}')
        return 0

def download_file(url, filename, path, num_threads=5) -> bool:
    filename = f"{path}/{filename}"
    
    session = requests.Session()
    r = session.head(url, allow_redirects=True)
    if r.status_code != 200:
        raise Exception(f"Cannot access URL, status code: {r.status_code}")
    total_size = int(r.headers['Content-Length'])
    chunk_size = total_size // num_threads
    with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename) as progress:
        pool = threadpool.ThreadPool(num_threads)
        threads = []
        for i in range(num_threads):
            start = i * chunk_size
            end = start + chunk_size - 1 if i != num_threads - 1 else total_size - 1
            part_file = f"{filename}.part{i}"
            if not os.path.exists(part_file):
                open(part_file, 'wb').close()
            threads.append((None, {'url': url, 'start': start, 'end': end, 'filename': part_file, 'progress': progress}))
        request = threadpool.makeRequests(__download_chunk, threads)
        [pool.putRequest(req) for req in request]
        pool.wait()
    with open(filename, "wb") as fp:
        for i in range(num_threads):
            part_file = f"{filename}.part{i}"
            with open(part_file, "rb") as f:
                fp.write(f.read())
            os.remove(part_file)
    return True