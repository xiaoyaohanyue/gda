import logging,os
from src.conf.getenv import *
from src.sql.sql import GDA_SQL
from src.conf.config import GDA_CONFIG

class GDA_INIT:

    def __init__(self):
        self.database = GDA_SQL()
        self.configcontoller = GDA_CONFIG()
        self.repositories_config = self.configcontoller.config_fillter('repositories')

    def setup_logging(self) -> None:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(LOG_PATH + '/app.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)  # 设置全局日志级别为DEBUG
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)    
    
    def check_path(self):
        os.makedirs(FILE_ROOT_PATH, exist_ok=True)
        os.makedirs(LOG_PATH, exist_ok=True)
        os.makedirs(FILE_ROOT_PATH_BACKUP, exist_ok=True)
    
    def init_database(self) -> None:
        self.database.initial('downloaded')
        self.database.initial('dwqueue')
        for item in self.repositories_config:
            if item['enable']:
                if not self.database.check_records('downloaded',f'name = "{item["name"]}"'):
                    self.database.insert_dw_database(data = {
                        'name': item["name"],
                        'version': '00',
                        'preversion': '00'
                    })
                if not self.database.check_records('dwqueue',f'name = "{item["name"]}"'):

                    self.database.insert_queue(data = {
                        'name': item["name"],
                        'version': '00',
                        'preversion': '00',
                        'links': 'none',
                        'prelinks': 'none',
                        'path': FILE_ROOT_PATH + '/releases/' + item['config']['folder'],
                        'prepath': FILE_ROOT_PATH + '/prereleases/' + item['config']['folder'],
                        'dwsflag': '0',
                        'presdwflag': '0',
                        'dwfflag': '0',
                        'prefdwflag': '0',
                        'dwstime': '0',
                        'prestime': '0'
                    })
    
    def init(self) -> None:
        self.check_path()
        self.setup_logging()
        self.init_database()