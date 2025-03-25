## GDA
当前文档仅仅是简单介绍一下，后续有时间会详细补充，也欢迎大家补充说明。

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