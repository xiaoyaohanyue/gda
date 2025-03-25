import mysql.connector
import json
from src.conf.getenv import *

class GDA_SQL:
  def __init__(self):
    self.__mydb = mysql.connector.connect(
    host = DATABASE_HOST,       # 数据库主机地址
    port = DATABASE_PORT,       # 数据库端口
    user = DATABASE_USER,    # 数据库用户名
    passwd = DATABASE_PASSWORD,   # 数据库密码
    database = DATABASE_NAME
    )

  def query(self,cmd,is_all):
    mycursor = self.__mydb.cursor()
    mycursor.execute(cmd)
    if is_all:
      myresult = mycursor.fetchall()
    else:
      myresult = mycursor.fetchone()
    return myresult
  
  def exec(self,cmd,is_update,params=None):
    mycursor = self.__mydb.cursor()
    mycursor.execute(cmd,params)
    if is_update:
      self.__mydb.commit()

  def sync(self):
    self.__mydb.commit()
    

  def create_dw_database(self,tablename):
    if tablename == 'downloaded':
      sql_create = f'''CREATE TABLE {tablename}(
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT "序号",
            name TEXT NOT NULL COMMENT "仓库名",
            version TEXT NOT NULL COMMENT "稳定版版本",
            preversion TEXT NOT NULL COMMENT "预先版版本"
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;'''
      self.exec(sql_create,False)
    elif tablename == 'dwqueue':
      sql_create = f'''CREATE TABLE {tablename}(
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT "序号",
            name TEXT NOT NULL COMMENT "仓库名",
            version TEXT NOT NULL COMMENT "稳定版版本",
            preversion TEXT NOT NULL COMMENT "预先版版本",
            links TEXT NOT NULL COMMENT "稳定版链接",
            prelinks TEXT NOT NULL COMMENT "预先版链接",
            path TEXT NOT NULL COMMENT "稳定版存放路径",
            prepath TEXT NOT NULL COMMENT "预先版存放路径",
            dwsflag TEXT NOT NULL COMMENT "稳定版开始标记",
            presdwflag TEXT NOT NULL COMMENT "预先版开始标记",
            dwfflag TEXT NOT NULL COMMENT "稳定版完成标记",
            prefdwflag TEXT NOT NULL COMMENT "预先版完成标记",
            dwstime TEXT NOT NULL COMMENT "稳定版开始时间",
            prestime TEXT NOT NULL COMMENT "预先版开始时间"
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;'''
      self.exec(sql_create,False)

  def check_exists(self,tablename):
    sql_is_exist = f'SHOW TABLES LIKE "{tablename}"'
    res = self.query(sql_is_exist,False)
    if res is not None:
      return True
    else:
      return False
    
  def check_records(self,tablename,fillter):
    sql_is_exist = f'SELECT * FROM {tablename} WHERE {fillter}'
    res = self.query(sql_is_exist,False)
    if res is not None:
      return True
    else:
      return False
    
  def initial(self,tablename):
    if not self.check_exists(tablename):
      self.create_dw_database(tablename)
  
  def update_dw_database(self,name,flag,value):
    cmd = f'''UPDATE downloaded SET {flag} = "{value}" WHERE name = "{name}";'''
    self.exec(cmd,True)
  
  def updateflag(self,name,flag,value):
    cmd = f'''UPDATE dwqueue SET {flag} = "{value}" WHERE name = "{name}";'''
    self.exec(cmd,True)

  def update_link_dw(self,dict):
    name = dict['name']
    dict.pop('name')
    target = ''
    for key in dict.keys():
      target = target + f'''{key} = '{dict[key]}','''
    target = target[:-1]
    cmd = f'''UPDATE dwqueue SET {target} WHERE name = "{name}";'''
    self.exec(cmd,True)
  
  def query_dw_queue(self,name,fillter):
    cmd = f'SELECT {fillter} FROM dwqueue WHERE name = "{name}";'
    return self.query(cmd,False)
  
  def get_links_dw(self,name,series):
    if series == 'release':
      res = self.query_dw_queue(name,'links')[0]
      return json.loads(res)
    else:
      res = self.query_dw_queue(name,'prelinks')[0]
      return json.loads(res)

  
  def check_dw_free_status(self,name,series):
    if series == 'release':
      res = self.query_dw_queue(name,'dwfflag')[0]
    else:
      res = self.query_dw_queue(name,'prefdwflag')[0]
    if int(res) == 0:
      return True
    else:
      return False
  
  def check_dw_start_status(self,name,series):
    if series == 'release':
      res = self.query_dw_queue(name,'dwsflag')[0]
    else:
      res = self.query_dw_queue(name,'presdwflag')[0]
    if int(res) == 1:
      return True
    else:
      return False

  def get_version_record(self,name,series):
    if series == 'release':
      res = self.query_dw_fillter(name,'version')[0]
    else:
      res = self.query_dw_fillter(name,'preversion')[0]
    return res
  
  def get_version_queue(self,name,series):
    if series == 'release':
      res = self.query_dw_queue(name,'version')[0]
    else:
      res = self.query_dw_queue(name,'preversion')[0] 
    return res
  
  def update_time_dw(self,name,series,time):
    if series == 'release':
      cmd = f'UPDATE dwqueue SET dwstime = "{time}" WHERE name = "{name}";'
    else:
      cmd = f'UPDATE dwqueue SET prestime = "{time}" WHERE name = "{name}";'
    self.exec(cmd,True)
  
  def query_dw_fillter(self,name,fillter):
    cmd = f'SELECT {fillter} FROM downloaded WHERE name = "{name}";'
    return self.query(cmd,False)
  
  def insert_dw_database(self,data):
    key = ', '.join(data.keys())
    values = ', '.join(['%s' for _ in data.values()])
    cmd = f'INSERT INTO downloaded ({key}) VALUES ({values});'
    self.exec(cmd,True,tuple(data.values()))
  
  def insert_queue(self,data):
    key = ', '.join(data.keys())
    values = ', '.join(['%s' for _ in data.values()])
    cmd = f'INSERT INTO dwqueue ({key}) VALUES ({values});'
    self.exec(cmd,True,tuple(data.values()))


    
