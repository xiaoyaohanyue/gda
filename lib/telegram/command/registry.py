from typing import Callable, Dict

command_list: Dict[str, Callable] = {}

def register(name: str, *, permission=None, args=None, hidden=False, desc=None):
    def deco(func: Callable):
        func.permission = permission
        func.args = args or []
        func.hidden = hidden
        func.desc = desc
        command_list[name] = func
        return func
    return deco
