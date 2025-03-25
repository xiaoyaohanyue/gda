from src.http.url import GDA_URL
import schedule,time
from src.http.queue import GDA_QUEUE
from src.init.init import GDA_INIT

URL = GDA_URL()
QUEUE = GDA_QUEUE()
INIT = GDA_INIT()


def job():
    INIT.init()
    URL.save_info()

def unlock():
    QUEUE.lock_check()

def checking():
    QUEUE.checking()

def start():
    job()
    checking()

print(__name__)
if __name__ == '__main__':
    start()
    schedule.every().day.at("06:00").do(job)
    schedule.every().day.at("18:00").do(job)
    schedule.every(1).hours.do(unlock)
    # schedule.every(3).minutes.do(checking)
    schedule.every(2).hours.do(checking)
    while True:
        schedule.run_pending()
        time.sleep(1)   

