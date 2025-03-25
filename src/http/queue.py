import logging
import time
import json
import os
import shutil
from src.sql.sql import GDA_SQL
from src.conf.config import GDA_CONFIG
from src.http.download import GDADownloader


logger = logging.getLogger(__name__)
class GDA_QUEUE:
    def __init__(self):
        self.database = GDA_SQL()
        self.configcontoller = GDA_CONFIG()
        self.download = GDADownloader()
        self.repositories_config = self.configcontoller.config_fillter('repositories')

    def unlock(self,name,series) -> None:
        if series =='release':
            self.database.updateflag(name,'dwfflag','0')
            self.database.updateflag(name,'dwsflag','0')
            self.database.updateflag(name,'dwstime','0')
        else:
            self.database.updateflag(name,'presdwflag','0')
            self.database.updateflag(name,'prefdwflag','0')
            self.database.updateflag(name,'prestime','0')

    def lock_check(self) -> None:
        logger.info('开始检查队列状态...')
        for item in self.repositories_config:
            if item['enable']:
                if not self.database.check_dw_free_status(item['name'],'release'):
                    if int(time.time()) - int(self.database.query_dw_queue(item['name'],'dwstime')[0]) >= 1800:
                        self.unlock(item['name'],series='release')
                        logger.warning(f'{item["name"]} 稳定版队列已锁定，已自动解锁。')
                if not self.database.check_dw_free_status(item['name'],'prerelease'):
                    if int(time.time()) - int(self.database.query_dw_queue(item['name'],'prestime')[0]) >= 1800:
                        self.unlock(item['name'],series='prerelease')
                        logger.warning(f'{item["name"]} 预先版队列已锁定，已自动解锁。')

    def count_files(self,path) -> int:
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
        
    def delete_all_contents(self,directory_path) -> None:
        try:
            if os.path.exists(directory_path) and os.path.isdir(directory_path):
                shutil.rmtree(directory_path)  # 删除目录及其所有内容
                os.makedirs(directory_path)  # 删除后重建空目录
                logger.info(f"已删除 {directory_path} 中的所有内容。")
            else:
                logger.error("指定的路径不存在或不是一个目录。")
        except Exception as e:
            logger.error(f"发生错误: {e}")

    def checking(self) -> None:
        self.database.sync()
        for item in self.repositories_config:
            if item['enable']:
                datas = self.database.query(f'SELECT * from dwqueue WHERE name = "{item["name"]}"',True)
                if datas:
                    links = json.loads(datas[0][4])
                    prelinks = json.loads(datas[0][5])
                    if self.count_files(datas[0][6]) != len(links):
                        logger.info(f'{item["name"]} 稳定版文件数量不匹配，开始重新下载！')
                        logger.info(f'{item["name"]} 稳定版文件数量为 {len(links)}，实际文件数量为 {self.count_files(datas[0][6])}。')
                        self.database.updateflag(item['name'],'dwsflag','1')
                        self.delete_all_contents(datas[0][6])
                        self.download.prepare_download(item,series='release')
                    if self.count_files(datas[0][7]) != len(prelinks):
                        logger.info(f'{item["name"]} 预先版文件数量不匹配，开始重新下载！')
                        logger.info(f'{item["name"]} 预先版文件数量为 {len(prelinks)}，实际文件数量为 {self.count_files(datas[0][7])}。')
                        self.delete_all_contents(datas[0][7])
                        self.database.updateflag(item['name'],'presdwflag','1')
                        self.download.prepare_download(item,series='prerelease')
                    logger.info(f'{item["name"]} 队列检查完成。')
