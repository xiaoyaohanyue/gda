import os
import yaml
from lib.log import logger
from lib.conf import settings

def check_yaml_exists() -> bool:
    if not os.path.exists(settings.yaml_file):
        logger.error('仓库配置文件不存在！请检查后重试！')
        return False
    return True

def load_yaml_config() -> dict:
    try:
        with open(settings.yaml_file, 'r') as file:
            config = yaml.safe_load(file)
            return config
    except yaml.YAMLError as e:
        logger.error(f'yaml语法错误：{e}')
        return None
    
def yaml_config_fillter(fillter) -> dict:
    return load_yaml_config()[fillter]