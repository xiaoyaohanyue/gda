from lib.conf import check_yaml_exists, yaml_config_fillter, settings
from lib.db import init_db
from lib.db import ListItem, run_db_session, create_list_item, get_list_item_by_repository, update_list_item
from lib.log import logger
import os

async def init_config():
    if not check_yaml_exists():
        return None
    config = yaml_config_fillter('repositories')
    for repo in config:
        exist = await run_db_session(get_list_item_by_repository, repo['name'])
        if not exist:
            # repo['name'] libnyanpasu/clash-nyanpasu -> clash-nyanpasu
            name = repo['name'].strip('/').split('/')[-1]
            enabled = repo.get('enable', False)
            path = repo.get('folder', name)
            logger.info(f'初始化添加仓库：{name}')
            await run_db_session(create_list_item, ListItem(
                name=name,
                repository=repo['name'],
                path=path,
                enabled=enabled
            ))
        else:
            name = repo['name'].strip('/').split('/')[-1]
            enabled = repo.get('enable', False)
            path = repo['config'].get('folder', name)
            if exist.enabled != enabled:
                exist.enabled = enabled
                logger.info(f'更新仓库状态：{exist.name} -> {"启用" if enabled else "禁用"}')
                await run_db_session(update_list_item, repo['name'], enabled=enabled)
            if exist.path != path:
                logger.info(f'更新仓库路径：{exist.path} -> {path}')
                if os.path.exists(settings.download_root_path+exist.path):
                    os.rename(settings.download_root_path+exist.path, settings.download_root_path+path)
                await run_db_session(update_list_item, repo['name'], path=path)


def folder_init():
    os.makedirs(settings.session_path, exist_ok=True)
    os.makedirs(settings.download_root_path, exist_ok=True)

async def boot():
    folder_init()
    await init_db()
    await init_config()