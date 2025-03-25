import yaml
import os
import logging
from src.conf.getenv import CONFIG_FILE

loggers = logging.getLogger(__name__)

class GDA_CONFIG:
    
    def __init__(self) -> None:
        self.config_file = CONFIG_FILE
        
    

    def check(self) -> bool:
        if not os.path.exists(self.config_file):
            loggers.error('配置文件不存在！请检查后重试！')
            return False
        return True
        
    def load_config(self) -> dict:
        if self.check():
            try:
                with open(self.config_file, 'r') as file:
                    config = yaml.safe_load(file)
                    return config
            except yaml.YAMLError as e:
                loggers.error(f'yaml语法错误：{e}')
                return None
        return None
    
    def config_fillter(self,fillter) -> dict:
        return self.load_config()[fillter]



