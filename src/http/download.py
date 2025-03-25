import os
import requests
import threadpool
import time
from tqdm import tqdm
from src.http.header import GDAHeader
from src.conf.getenv import *
from src.sql.sql import GDA_SQL
from src.utils.utils import GDAUtils


class GDADownloader:
    def __init__(self) -> None:
        self.urlpre = GDAHeader()
        self.github_token = GITHUB_ACCESS_TOKEN
        self.database = GDA_SQL()
        self.dw_path = {
            'path': FILE_ROOT_PATH,
            'pathbak': FILE_ROOT_PATH_BACKUP
        }
        self.utils = GDAUtils()

    def __download_chunk(self,url, start, end, filename, progress) -> None:
        headers = self.urlpre.get_header(self.github_token)
        headers.update({'Range': f'bytes={start}-{end}'})
        r = requests.get(url, headers=headers, stream=True)
        # chunk_size = end - start + 1
        with open(filename, "r+b") as fp:
            # fp.seek(start)
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    fp.write(chunk)
                    progress.update(len(chunk))



    def download_file(self,url, filename,path, num_threads=5) -> bool:
        filename = f"{path}/{filename}"
        
        session = requests.Session()
        r = session.head(url, allow_redirects=True)
        if r.status_code != 200:
            raise Exception(f"Cannot access URL, status code: {r.status_code}")
        total_size = int(r.headers['Content-Length'])
        chunk_size = total_size // num_threads

        with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename) as progress:
            pool = threadpool.ThreadPool(num_threads)
            threads = []

            for i in range(num_threads):
                start = i * chunk_size
                end = start + chunk_size - 1 if i != num_threads - 1 else total_size - 1
                part_file = f"{filename}.part{i}"
                if not os.path.exists(part_file):
                    open(part_file, 'wb').close()
                threads.append((None, {'url': url, 'start': start, 'end': end, 'filename': part_file, 'progress': progress}))

            request = threadpool.makeRequests(self.__download_chunk, threads)
            [pool.putRequest(req) for req in request]
            pool.wait()

        with open(filename, "wb") as fp:
            for i in range(num_threads):
                part_file = f"{filename}.part{i}"
                with open(part_file, "rb") as f:
                    fp.write(f.read())
                os.remove(part_file)

        return True
    
    def prepare_download(self,item,series) -> bool:
        name = item['name']
        if self.database.check_dw_free_status(name,series) and self.database.check_dw_start_status(name,series):
            self.database.updateflag(item["name"],f'{"dwfflag" if series == "release" else "prefdwflag"}','1')
            links = self.database.get_links_dw(name,series)
            version = self.database.get_version_queue(name,series)
            self.database.update_time_dw(name,series,int(time.time()))
            mid_folder = f'{"releases" if series == "release" else "prereleases"}'
            if not os.path.exists(self.dw_path['path'] + f'/{mid_folder}/' + item['config']['folder']):
                os.makedirs(self.dw_path['path'] + f'/{mid_folder}/' + item['config']['folder'])
            else:
                self.utils.move(self.dw_path['path'] + f'/{mid_folder}/' + item['config']['folder'],self.dw_path['pathbak'] + f'/{series}/' + item['config']['folder'])
                os.makedirs(self.dw_path['path'] + f'/{mid_folder}/' + item['config']['folder'])
            for link in links:
                try_times = 0
                while try_times <= 5:
                    try:
                       self.download_file(link,link.split('/')[-1],self.dw_path['path'] + f'/{mid_folder}/' + item['config']['folder'])
                       time.sleep(3)
                       break
                    except:
                       try_times = try_times + 1
                       time.sleep(3)
            self.database.updateflag(item["name"],f'{"dwsflag" if series == "release" else "presdwflag"}','0')
            self.database.updateflag(item["name"],f'{"dwfflag" if series == "release" else "prefdwflag"}','0')
            self.database.update_dw_database(item["name"],f'{"version" if series == "release" else "preversion"}',version)
            self.utils.sendmessage(f'{item["name"]} {"稳定版" if series == "release" else "预览版"}已更新到 {version} 请及时更新！')


