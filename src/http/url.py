import requests,logging
from src.conf.config import GDA_CONFIG
from src.conf.getenv import *
from src.http.header import GDAHeader
from src.http.download import GDADownloader
from src.sql.sql import GDA_SQL
from collections import defaultdict
import json,time,os,shutil
#Global Setting
logger = logging.getLogger(__name__)
class GDA_URL:
    def __init__(self) -> None:
        self.github_api = 'https://api.github.com/repos/'
        self.github_api_postfix = '/releases/latest'
        self.github_api_postfix_pre = '/releases'
        self.configcontoller = GDA_CONFIG()
        self.urlpre = GDAHeader()
        self.DW = GDADownloader()

        self.repositories_config = self.configcontoller.config_fillter('repositories')

        self.github_token = GITHUB_ACCESS_TOKEN
        self.dw_path = {
            'path': FILE_ROOT_PATH,
            'pathbak': FILE_ROOT_PATH_BACKUP
        }
        self.database = GDA_SQL()


    def get_remote_info(self,item,version) -> dict:
        infos = {}
        
        repositories = item['name']
        download_tag = item['config']['sp']
        flag = item['config']['flag']
        
        try:
            links = []
            github_http_header = self.urlpre.get_header(self.github_token)
            if version == 'release':
                api = self.github_api + repositories + self.github_api_postfix
                response = requests.get(api,headers=github_http_header).json()
            else:
                api = self.github_api + repositories + self.github_api_postfix_pre
                response = requests.get(api,headers=github_http_header).json()
            try:
                if version == 'release':
                    ver = response['tag_name']
                else:
                    for res in response:
                        if res['prerelease']:
                            ver = res['tag_name']
                            response = res
                            break
                for link_parents in response['assets']:
                    links.append(link_parents[download_tag])
                infos[flag] = {f'{version}': {
                    'version': ver,
                    'links': links
                }}
            except:
                if version == 'release':
                    logger.error(f'{repositories}稳定版数据处理出错！！！')
                else:
                    logger.warning(f'{repositories}未找到预览版！！！')
        except:
            if version == 'release':
                logger.error(f'{repositories}稳定版无法访问github API检查网络连接！！！')
            else:
                logger.warning(f'{repositories}预览版无法访问github API检查网络连接！！！')
        return infos
    
    def genarate_remote_info(self,item) -> dict:
        infos = defaultdict(dict)
        infos = self.get_remote_info(item,'release')
        infos[item['config']['flag']].update(self.get_remote_info(item,'prerelease')[item['config']['flag']])
        return infos
    
    def handle_info(self,name,info,series) -> bool:
        try:
            if info[series]['version']:
                old_version = self.database.get_version_record(name,series)
                if old_version != info[series]['version'] and self.database.check_dw_free_status(name,series) and self.database.check_dw_start_status(name,series) == False:
                    logger.info(f'旧版本：{old_version}, 新版本：{info[series]["version"]}')
                    self.database.update_link_dw(dict = {
                        'name': name,
                        f'{"version" if series == "release" else "preversion"}': info[series]['version'],
                        f'{"links" if series == "release" else "prelinks"}': json.dumps(info[series]['links']),
                        f'{"dwsflag" if series == "release" else "presdwflag"}': '1',
                    })
        except:
            logger.error(f'{name}{"稳定版" if series == "release" else "预先版"}数据处理出错！！！')

    def save_info(self) -> dict:

        for item in self.repositories_config:
            enable = item['enable']
            if not enable:
                continue
            logger.info(f'开始处理{item["name"]}的更新任务')
            remote = self.genarate_remote_info(item)
            flag = item['config']['flag']
            try:
                self.handle_info(item['name'],remote[flag],'release')
            except:
                logger.error(f'{item["name"]}稳定版数据处理出错！！！')
            try:
                self.handle_info(item['name'],remote[flag],'prerelease')
            except:
                logger.error(f'{item["name"]}预先版数据处理出错！！！')
        logger.info('所有下载任务已载入队列！')
        return True
    
    

    
                


            



        
