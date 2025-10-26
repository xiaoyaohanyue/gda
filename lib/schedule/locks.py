# lib/schedule/locks.py
import asyncio

_repo_locks: dict[str, asyncio.Lock] = {}
_global_lock = asyncio.Lock()

def repo_lock(repo: str) -> asyncio.Lock:
    # 针对仓库的互斥锁，防止同一仓库被多个任务同时处理
    lock = _repo_locks.get(repo)
    if lock is None:
        lock = asyncio.Lock()
        _repo_locks[repo] = lock
    return lock

def global_lock() -> asyncio.Lock:
    return _global_lock
