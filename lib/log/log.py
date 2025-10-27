import logging
from logging.handlers import TimedRotatingFileHandler
import os
from lib.conf import settings



def setup_logging():
    os.makedirs(settings.log_path, exist_ok=True)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(settings.log_path, 'app.log'),
        when='midnight',         # 每天切割一次
        interval=1,
        backupCount=7,           # 保留7天的日志
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    # 关闭 SQLAlchemy SQL 输出
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

    # 可自定义主日志器
    app_logger = logging.getLogger("GDA")
    app_logger.info("✅ Logging initialized successfully.")
    return app_logger

    
