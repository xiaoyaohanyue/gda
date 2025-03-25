import os
import shutil
import requests
import time

from src.conf.getenv import *
from src.http.header import GDAHeader

class GDAUtils:
    def __init__(self):
        self.gdaheader = GDAHeader()
    
    @staticmethod
    def move(old,new):
        if old.endswith('/'):
            old = old[:-1]
        if new.endswith('/'):
            new = new[:-1]
        if os.path.exists(new):
            shutil.rmtree(new)
        if os.path.isdir(old):
            os.makedirs(new)
            filelist = os.listdir(old)
            for i in filelist:
                shutil.move(old+'/'+i,new+'/'+i)
            os.rmdir(old)
        else:
            shutil.move(old,new)

    def sendmessage(self,message):
        chatid = TG_NOTICES_CHAT_ID
        key = BOT_TOKEN
        url = "https://api.telegram.org/bot" + key + "/sendMessage"
        datas = []
        datas.append(('chat_id',chatid))
        datas.append(('text',message))
        headers = self.gdaheader.get_header_without_token()
        time.sleep(1)
        r = requests.post(url,data=datas,headers=headers)


