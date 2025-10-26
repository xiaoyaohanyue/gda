from datetime import datetime
from zoneinfo import ZoneInfo
import os
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