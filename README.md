# byrbt_bot

[![byrbt](https://img.shields.io/static/v1?label=ByrBt&message=2.0&color=blue)](https://github.com/lipssmycode/byrbt_bot) [![Python](https://img.shields.io/badge/python-3.7-plastic?logo=python&logoColor=#3776AB&link=https://www.python.org/)](https://www.python.org/) [![Transmission](https://img.shields.io/static/v1?label=Transmission&message=3.00&color=red)](https://transmissionbt.com/)

**北邮人BT全自动（大概）下载~~刷流~~机器人**

> 目前byrbt_bot已经升级到2.0版本，代码进行了重构，同时添加了更多的功能，欢迎使用并提出建议，祝每个byrbter都能上传量4TB，账户永久保存！

本机器人可以利用校园里的服务器进行全自动做种（本人亲测已上传133TB）（如果家里支持ipv6并且使用代理访问byrbt，在家也是可以使用本项目的，需要修改请求byrbt网站的相关代码，添加代理）。本机器人采用transmission
作为下载器，可以从Web端查看种子下载情况。

byrbt_bot包含以下功能：
- [x] 支持自动识别验证码登录（感谢[**decaptcha**](https://github.com/bumzy/decaptcha)项目）
- [x] 支持自动下载种子(感谢[**byrbt_bot**](https://github.com/Jason2031/byrbt_bot)项目)
- [x] 支持自动寻找合适的免费种子进行下载并做种（默认条件：种子文件大于1GB小于1TB大小，下载人数比做种人数大于0.6）
- [x] 支持自动识别Free活动，提高下载种子的条件，择优选取，避免频繁更换下载种子（默认条件：种子文件大于20GB小于1TB大小，下载人数比做种人数大于20.0）
- [x] 支持自动队列管理，设置队列上限，达到队列上限按照一定策略删除旧种子
- [x] 支持磁盘空间管理，可以设置种子文件大小总量上限
- [x] 支持过滤种子文件大小，范围在1G-1024G
- [x] 支持磁盘剩余空间检测，磁盘空间少于5GB时启动清理种子文件
- [x] 支持使用Transmission Web管理种子

运行截图：

![byrbt-bot.png](https://github.com/lipssmycode/byrbt_bot/blob/master/images/byrbt-bot.png)

transmission 3.00 Web界面：

![transmission.png](https://github.com/lipssmycode/byrbt_bot/blob/master/images/transmission.png)

## 背景

北邮人BT只要上传量高于4TB，并且分享率大于3.05，就能成为**Veteran User**，账户永久保存！

![veteran-user.png](https://github.com/lipssmycode/byrbt_bot/blob/master/images/veteran-user.png)

平常手动下载免费种子并做种来提升等级是一件较为繁琐的事情，使用本机器人可以利用校园里的服务器进行全自动(~~刷流~~)做种，可以省去挑选种子和管理种子的麻烦，更快更轻松的实现4TB上传量！

## 配置

bot配置文件路径在config/config.ini

```ini
[ByrBTBot]
byrbt-url = https://byr.pt/				# byrbt网址，默认不用修改
username = <please input your username>	# byrbt账户名
passwd = <please input your passwd>		# byrbt账户密码
max-torrent = 20						# 种子队列上限
;all size in G
max-torrent-total-size = 1024			# 种子大小总量上限（单位G）
torrent-max-size = 512					# 单种子大小上限（单位G）
torrent-min-size = 1					# 单种子大小下限（单位G）

[Transmission]
transmission-host = 127.0.0.1			# transmission所在服务器地址
transmission-port = 9091				# transmission rpc端口
transmission-username = admin			# transmission账户名
transmission-password = admin			# transmission账户密码
transmission-download-path = /downloads	# transmission下载目录
```

**注意！！！**本机器人会自动删除种子，因此最好重新部署新的transmission服务，而不要将原本的transmission接入到本机器上，以防重要种子被删除！

## 部署及运行

### Docker Compose部署运行（推荐）

1. 确保已经安装了[docker](https://www.docker.com/)和[docker-compose](https://docs.docker.com/compose/)，本人用的版本是docker 19.03.15以及docker-compose 1.29.2。
2. 配置config/config.ini，只需要修改byrbt账户名称和密码，transmission相关配置如果修改了transmission的默认账户和密码就需要一同更改
3. 配置docker-compose.yml，可以修改transmission的下载目录以及账户密码，使用的transmission镜像的项目地址在[这里](https://hub.docker.com/r/linuxserver/transmission)

```yaml
version: "3"
services:
  transmission:
    image: linuxserver/transmission:3.00-r5-ls123
    container_name: transmission
    environment:
      - PUID=${CURRENT_PUID} # 当前用户的UID
      - PGID=${CURRENT_PGID} # 当前用户的GID
      - TZ=Asia/Shanghai
      - TRANSMISSION_WEB_HOME=/combustion-release/
      - USER=admin # transmission的访问账户名
      - PASS=admin # transmission的访问密码
    volumes:
      - ./transmission/data:/config			# ./transmission/data包含transmission的配置文件，可启动后自行修改
      - ./transmission/downloads:/downloads # ./transmission/downloads是transmission的下载目录，可以自行替换，注意需要当前用户有读写权限
      - ./transmission/watch:/watch
    restart: unless-stopped
    network_mode: host
  bot:
    build:
      context: .
    image: smyyan/byrbt-bot-transmission
    user: ${CURRENT_PUID}:${CURRENT_PGID} # 设置容器运行用户为当前用户
    environment:
      - TZ=Asia/Shanghai
    volumes:
      - ./config:/config
      - ./data:/data
    depends_on:
      - transmission
    restart: unless-stopped
    network_mode: host
```

4. 如果需要修改transmission本身的配置，可以修改transmission/data/settings.json文件
5. 运行脚本start_bot_by_docker.sh即可

```
# 在项目根目录下执行
# docker-compose启动byrbt-bot
bash start_bot_by_docker.sh

# 或者手动执行
export CURRENT_PUID=$(id -u)
export CURRENT_PGID=$(id -g)
docker-compose up -d --build
```

6. 启停byrbr-bot

```
# 在项目根目录下执行
# 停止byrbr-bot
docker-compose stop bot
# 停止transmission
docker-compose stop transmission
# 停止所有
docker-compose stop

```

7. 查看运行日志

```
# 在项目根目录下执行
# 查看byrbr-bot日志
docker-compose logs -f --tail=500 bot
# 查看transmission日志
docker-compose logs -f --tail=500 transmission
# 查看日志
docker-compose logs -f
```

8. 卸载

```
docker-compose down
```

9. 如果要修改transmission配置文件，路径在./transmission/data/setting.json，修改完成后运行docker-compose restart即可



### 手动部署运行

1. 确保安装transmission 3.00或者2.00以上版本，确保安装Python3.7以上版本

2. 配置transmission并运行transmission

   注意：尽量不要使用原有的transmission，因为本机器人会删除种子，如果原有的transmission有重要的种子数据，会导致数据丢失！

   以下是transmission部分配置说明，其他配置按自身需求设置，[配置文件地址](https://github.com/linuxserver/docker-transmission/blob/master/root/defaults/settings.json)

```json
{
	...
    "download-dir": "/downloads/complete", # 下载文件夹路径设置
    "download-queue-enabled": false, # 下载队列功能，建议直接关闭，或者将queue-size设置大一些
    "download-queue-size": 50,
    "incomplete-dir": "/downloads/incomplete", # 未完成种子文件夹路径设置，未完成种子文件夹如不需要可以关闭
    "incomplete-dir-enabled": true,
    "preallocation": 1, # 预分配下载文件空间，必须设置为1，否则影响磁盘相关功能
    "rpc-enabled": true, # rpc功能必须开启
    ...
}
```

3. 配置config/config.ini，需要修改byrbt账户名称和密码，同时需要修改transmission配置

4. 安装Python依赖

```bash
pip install -i https://mirrors.aliyun.com/pypi/simple -r requirements.txt
```

5. 启动byrbt-bot

```bash
python3 bot.py
```

## 维护者

[@lipssmycode](https://github.com/lipssmycode)

## 感谢

**[byrbt_bot(https://github.com/Jason2031/byrbt_bot)](https://github.com/Jason2031/byrbt_bot)**  
**[decaptcha(https://github.com/bumzy/decaptcha)](https://github.com/bumzy/decaptcha)**  
