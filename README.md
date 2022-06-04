# brybt_bot
**北邮人BT全自动（大概）下载~~刷流~~机器人**

脚本很早以前写的，欢迎自行修改完善

北邮人BT只要上传量高于4TB，并且分享率大于3.05，就能成为**Veteran User**，账户永久保存

![image-20200330161046856](https://github.com/lipssmycode/byrbt_bot/blob/master/images/image-20200330161046856.png)

本机器人可以利用校园里的服务器进行全自动做种（本人亲测已上传96TB），采用transmission作为下载器，可以从Web端查看种子下载情况

![image-20200330163255569](https://github.com/lipssmycode/byrbt_bot/blob/master/images/image-20200330163255569.png)

（疫情期间，免费种子较少）

![image-20200330163105285](https://github.com/lipssmycode/byrbt_bot/blob/master/images/image-20200330163105285.png)

- [x] 支持识别验证码登录（感谢**[decaptcha](https://github.com/bumzy/decaptcha)**项目）
- [x] 支持下载种子(感谢**[byrbt_bot](https://github.com/Jason2031/byrbt_bot)**项目)
- [x] 支持自动寻找合适的免费种子（默认条件：种子文件大于1G小于1TB大小，下载人数比做种人数大于0.6）
- [x] 支持识别Free，提高下载种子的条件，择优选取，避免频繁更换下载种子
- [x] 支持自动删除旧种子，下载新种子
- [x] 支持使用Transmission Web管理种子

### Usage

1. #### 用户权限问题

   由于需要使用Transmission，在root用户下配置会比较方便，一般用户可以采用docker实现，将下载数据的文件夹挂载到docker上即可。

2. #### 安装Python3

   安装相应依赖包

   ```shell
   pip install -r requirements.txt
   ```
   sklearn版本为0.22.1可以使用captcha_classifier_sklearn0.22.1.pkl模型，改名为captcha_classifier.pkl即可

3. #### 安装Transmission

   安装Transmission教程如下

   https://www.jianshu.com/p/bbd4f6832268?nomobile=yes

   https://blog.csdn.net/jiyuanyi1992/article/details/44250943

   https://blog.csdn.net/zhaiyingchen/article/details/88049113

   [https://wiki.archlinux.org/index.php/Transmission_(%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87)#%E9%80%89%E6%8B%A9%E4%B8%80%E4%B8%AA%E7%94%A8%E6%88%B7](https://wiki.archlinux.org/index.php/Transmission_(简体中文)#选择一个用户)

   启动配置一般在~/.config/transmission-daemon/settings.json，这里放一个可行的配置

   ```json
   {
       "alt-speed-down": 50,
       "alt-speed-enabled": false,
       "alt-speed-time-begin": 540,
       "alt-speed-time-day": 127,
       "alt-speed-time-enabled": false,
       "alt-speed-time-end": 1020,
       "alt-speed-up": 50,
       "bind-address-ipv4": "0.0.0.0",  //修改
       "bind-address-ipv6": "::", //修改
       "blocklist-enabled": false,//修改
       "blocklist-url": "http://www.example.com/blocklist",
       "cache-size-mb": 4,
       "dht-enabled": true,
       "download-dir": "/home/.bt", //修改为种子文件下载路径（需新建一个空文件夹）
       "download-queue-enabled": true,
       "download-queue-size": 5,
       "encryption": 1,
       "idle-seeding-limit": 30,
       "idle-seeding-limit-enabled": false,
       "incomplete-dir": "/home/.bt", //修改为种子文件下载路径（需新建一个空文件夹）
       "incomplete-dir-enabled": false,
       "lpd-enabled": false,
       "message-level": 1,
       "peer-congestion-algorithm": "",
       "peer-id-ttl-hours": 6,
       "peer-limit-global": 200,
       "peer-limit-per-torrent": 50,
       "peer-port": 51413,
       "peer-port-random-high": 65535,
       "peer-port-random-low": 49152,
       "peer-port-random-on-start": false,
       "peer-socket-tos": "default",
       "pex-enabled": true,
       "port-forwarding-enabled": true,
       "preallocation": 1,
       "prefetch-enabled": 1,
       "queue-stalled-enabled": true,
       "queue-stalled-minutes": 30,
       "ratio-limit": 2,
       "ratio-limit-enabled": false,
       "rename-partial-files": true,
       "rpc-authentication-required": true,//修改
       "rpc-bind-address": "0.0.0.0", //修改
       "rpc-enabled": true, //修改
       "rpc-host-whitelist": "",//修改
       "rpc-host-whitelist-enabled": true,//修改
       "rpc-password": "pw",//密码
       "rpc-port": 9091,//web访问端口
       "rpc-url": "/transmission/",//修改
       "rpc-username": "smy", //用户
       "rpc-whitelist": "*.*.*.*",//修改
       "rpc-whitelist-enabled": true,//修改
       "scrape-paused-torrents-enabled": true,
       "script-torrent-done-enabled": false,
       "script-torrent-done-filename": "",
       "seed-queue-enabled": false,
       "seed-queue-size": 10,
       "speed-limit-down": 100,
       "speed-limit-down-enabled": false,
       "speed-limit-up": 100,
       "speed-limit-up-enabled": false,
       "start-added-torrents": true,
       "trash-original-torrent-files": false,
       "umask": 18,
       "upload-slots-per-torrent": 14,
       "utp-enabled": true
   }
   ```

   启动不成功可以在保证service transmission-daemon是关闭的情况下运行

   ```shell
   transmission-daemon -g <配置所在的文件夹路径>
   ```

   访问ip:9091登录web端，出现红种需自行删除，尚未解决自动删除红种的问题

4. #### 在byrbt.py配置信息

   主要配置如下信息

   ```python
   _username = '用户名'
   _passwd = '密码'
   _transmission_user_pw = 'user:passwd'  # transmission的用户名和密码，按照格式填入
   _windows_download_path = './torrent'  # windows测试下载种子路径
   _linux_download_path = '<path_to_download_dir>'  # linux服务器下载种子的路径
   _torrent_infos = './torrent.pkl'  # 种子信息保存文件路径
   max_torrent = 20  # 最大种子数
   search_time = 120  # 轮询种子时间，默认120秒
   ```

5. #### 启动

   ```shell
   python byrbt.py
   ```

### Acknowledgements

**[byrbt_bot](https://github.com/Jason2031/byrbt_bot)**  
**[decaptcha](https://github.com/bumzy/decaptcha)**  
