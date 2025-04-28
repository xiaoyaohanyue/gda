## GDA
当前文档仅仅是简单介绍一下，后续有时间会详细补充，也欢迎大家补充说明。



## 配置文件说明

### .env文件
这个文件里大多数是关于本程序的基础配置信息。主要有以下可配置参数
- LOG_PATH
  用来填写程序日志文件的存放目录，如果路径为一个不存在的路径则会自动创建该路径，参数值不可为空，可以保持默认值 `/gda/logs`
- FILE_ROOT_PATH
  用来填写被下载文件的存放路径，如果路径为一个不存在的路径则会自动创建该路径，参数值不可为空，可以保持默认值 `/gda/alist/app`
- FILE_ROOT_PATH_BACKUP
  用于填写上一次被下载的文件的存放路径（每次下载新一次的文件时会自动将上一次下载的内容备份到本路径下），如果路径为一个不存在的路径则会自动创建该路径，参数值不可为空，可以保持默认值`/gda/alist/backup/app`
- CONFIG_FILE
  用于填写需要下载的项目列表的配置文件地址，该文件用于详细配置需要定期下载哪些项目文件，该值不可为空，可以保持默认值`./config/config.yaml`
- DATABASE_HOST
  用于填写数据库的连接地址（本程序使用mysql 8.x），该值不可为空，可以保持默认值`db`
- DATABASE_PORT
  用于填写数据库的连接端口，不可为空，可以保持默认值`3306`
- DATABASE_NAME
  用于填写数据库名称，不可为空，可以保持默认值`gda`
- DATABASE_USER
  数据库用户名，不可为空，可保持默认值`root`
- DATABASE_PASSWORD
  数据库连接密码，不可为空，可以保持默认值`defaultpassword`
- BOT_TOKEN
  Telegram Bot的token，可前往@BotFather进行申请，不可为空，没有默认值
- TG_NOTICES_CHAT_ID
  Telegram的通知对话的ID，不可为空，没有默认值
- GITHUB_ACCESS_TOKEN
  Github的全局访问Token，不可为空，没有默认值，需要自行前往Github进行申请创建
- GITHUB_USERNAME
  Github用户名

### config.yaml
该配置文件用于填写待下载的项目列表，目前仅支持github项目。
基础结构如下：
```yaml
repositories:
  - name: "2dust/v2rayNG" #仓库地址
    config:
      sp: "browser_download_url" #保持不变
      flag: "v2rayng" #下载链接的标记，确保其在整个文件中的唯一性，不可重复
      folder: "v2rayNG" #下载后的保存文件夹名称，可在alist中看到
    enable: True #是否要启用该项目的下载

  - name: "2dust/v2rayN"
    config:
      sp: "browser_download_url"
      flag: "v2rayn"
      folder: "v2rayN"
    enable: True
```

## Docker Compose方式部署
当前项目中提供的docker-compose.yaml中默认集成了alist以及mysql，如果你需要单独部署他们则需要自行编写，需要做的变动很小。

首先将本项目克隆到本地
```shell
mkdir /opt/gda
cd /opt/gda
git clone https://github.com/xiaoyaohanyue/gda.git .
```
然后编辑配置文件，这里有两个配置文件，其中`.env`是用于配置一些基础信息
```shell
BOT_TOKEN: 这里填写机器人的token，用于发送版本更新通知
TG_NOTICES_CHAT_ID: 这里填写需要将tg消息发往的目的聊天ID
GITHUB_ACCESS_TOKEN: 这里填写github的token，自行在账号里申请，用于防止api限制读取版本信息
GITHUB_USERNAME: 可以不用填
```
可以只修改上面的几个参数，并且是必须修改，然后修改`config.yaml`，这是你想要监测更新的项目列表，严格按照模版编写。

```yaml
- name: "2dust/v2rayN" #项目名
    config:
      sp: "browser_download_url" #过滤字段可以不用管，照搬就行
      flag: "v2rayn" #整理下载链接用的，可以随便定义，但是需要确保整个配置文件中该字段值不重复。
      folder: "v2rayN" #存放路径的名称，具体体现在alist的页面展示中
    enable: True #是否启用该项目的监听
```

完成上面的操作之后就可按顺序执行下面的指令进行部署
```shell
docker network create GDA
docker volume create GDA_DATA
docker compose up -d
```
最后再使用alist的官方重置密码的指令进行管理员密码创建
```shell
# 手动设置一个密码,`NEW_PASSWORD`是指你需要设置的密码
docker exec -it alist ./alist admin set NEW_PASSWORD
```
到这里就可以访问 http://127.0.0.1:5244 来查看了。

演示站：[缥缈墟-文件站](https://file.pmxu.xyz)

---

## 💡 赞助声明

本项目由 [VTEXS](https://console.vtexs.com/?affid=1551) 的「开源项目免费 VPS 计划」提供算力支持。  
感谢 VTEXS 对开源社区的支持！

Todo:
- 增加更加细化的目录结构
- 增加对其他下载源的支持
- 增强TG Bot的功能


Update Log:
- 2025-4-14: 增加当项目release不可读取时处理方式，修改默认监听的项目列表

