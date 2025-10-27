import asyncio

_repo_locks: dict[str, asyncio.Lock] = {}
_global_lock = asyncio.Lock()

def repo_lock(repo: str) -> asyncio.Lock:
    lock = _repo_locks.get(repo)
    if lock is None:
        lock = asyncio.Lock()
        _repo_locks[repo] = lock
    return lock

def global_lock() -> asyncio.Lock:
    return _global_lock
