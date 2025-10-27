from .registry import command_list, register  

import pkgutil, importlib

for m in pkgutil.iter_modules(__path__):
    if m.ispkg:
        continue
    if m.name in {"registry", "__init__"}:
        continue
    importlib.import_module(f"{__name__}.{m.name}")

__all__ = ["command_list", "register"]
