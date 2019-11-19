#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/15 21:23
# @Author  : ghoskno
# @File    : brybt.py
# @Software: PyCharm

import time
import os
import re
import pickle
from io import BytesIO
import platform
from contextlib import ContextDecorator
from PIL import Image
import requests
from requests.cookies import RequestsCookieJar
from bs4 import BeautifulSoup

from decaptcha import DeCaptcha

# 判断平台
osName = platform.system()
if osName == 'Windows':
    osName = 'Windows'
elif osName == 'Linux':
    osName = 'Linux'
else:
    raise Exception('not support this system : {}'.format(osName))

# 常量
_BASE_URL = 'https://bt.byr.cn/'
_tag_map = {
    'free': '免费',
    'twoup': '2x上传',
    'twoupfree': '免费&2x上传',
    'halfdown': '50%下载',
    'twouphalfdown': '50%下载&2x上传',
    'thirtypercent': '30%下载',
}
_cat_map = {
    '电影': 'movie',
    '剧集': 'episode',
    '动漫': 'anime',
    '音乐': 'music',
    '综艺': 'show',
    '游戏': 'game',
    '软件': 'software',
    '资料': 'material',
    '体育': 'sport',
    '记录': 'documentary',
}
_username = '用户名'
_passwd = '密码'
_transmission_user_pw = 'user:pass'

# 全局变量
download_path = None

if osName == 'Windows':
    download_path = os.path.abspath('./torrent')
elif osName == 'Linux':
    download_path = os.path.abspath('/bt/torrents')
else:
    raise Exception('not support system! {}'.format(osName))

decaptcha = DeCaptcha()
decaptcha.load_model('captcha_classifier.pkl')
byrbt_cookies = None
max_torrent = 20
current_torrent = list()
old_torrent = list()
if os.path.exists('./torrent.pkl'):
    old_torrent, current_torrent = pickle.load(open('./torrent.pkl', 'rb'))


def get_url(url):
    return _BASE_URL + url

def login():
    url = get_url('login.php')
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'}

    session = requests.session()
    for i in range(5):
        login_content = session.get(url)
        login_soup = BeautifulSoup(login_content.text, 'lxml')

        img_url = _BASE_URL + login_soup.select('#nav_block > form > table > tr:nth-of-type(3) img')[0].attrs['src']
        img_file = Image.open(BytesIO(session.get(img_url).content))

        captcha_text = decaptcha.decode(img_file)

        login_res = session.post(get_url('takelogin.php'), headers=headers, data=dict(username=_username, password=_passwd, imagestring=captcha_text, imagehash=img_url.split('=')[-1]))
        if '最近消息' in login_res.text:
            cookies = {}
            for k, v in session.cookies.items():
                cookies[k] = v

            with open('ByrbtCookies.pickle', 'wb') as f:
                pickle.dump(cookies, f)
            return cookies

        time.sleep(1)

    raise Exception('Cat not get Cookies!')

def load_cookie():
    if os.path.exists('ByrbtCookies.pickle'):
        print('find ByrbtCookies.pickle, loading cookies')
        read_path = open('ByrbtCookies.pickle', 'rb')
        byrbt_cookies = pickle.load(read_path)
    else:
        print('not find ByrbtCookies.pickle, get cookies...')
        byrbt_cookies = login()

    return byrbt_cookies

def _get_tag(tag):
    try:
        if tag == '':
            return ''
        else:
            tag = tag.split('_')[0]

        return _tag_map[tag]
    except KeyError:
        return ''

def _get_torrent_info(table):
    assert isinstance(table, list)
    torrent_infos = list()
    for item in table:
        torrent_info = dict()
        tds = item.select('td')
        cat = tds[0].select('img')[0].attrs['title']
        main_td = tds[1].select('table > tr > td')[0]
        href = main_td.select('a')[0].attrs['href']
        seed_id = re.findall(r'id=(\d+)&', href)[0]
        title = main_td.text
        title = title.split('\n')
        if len(title) == 2:
            sub_title = title[1]
            title = title[0]
        else:
            sub_title = ''
            title = title[0]

        tags = set([font.attrs['class'][0] for font in main_td.select('b > font') if 'class' in font.attrs.keys()])
        if '' in tags:
            tags.remove('')

        is_seeding = len(main_td.select('img[src="pic/seeding.png"]')) > 0
        is_finished = len(main_td.select('img[src="pic/finished.png"]')) > 0

        is_hot = False
        if 'hot' in tags:
            is_hot = True
            tags.remove('hot')
        is_new = False
        if 'new' in tags:
            is_new = True
            tags.remove('new')
        is_recommended = False
        if 'recommended' in tags:
            is_recommended = True
            tags.remove('recommended')

        if 'class' in tds[1].select('table > tr')[0].attrs.keys():
            tag = _get_tag(tds[1].select('table > tr')[0].attrs['class'][0])
        else:
            tag = ''

        file_size = tds[6].text.split('\n')

        seeding = int(tds[7].text) if tds[7].text.isdigit() else -1

        downloading = int(tds[8].text) if tds[8].text.isdigit() else -1

        finished = int(tds[9].text) if tds[9].text.isdigit() else -1

        torrent_info['cat'] = cat
        torrent_info['is_hot'] = is_hot
        torrent_info['tag'] = tag
        torrent_info['is_seeding'] = is_seeding
        torrent_info['is_finished'] = is_finished
        torrent_info['seed_id'] = seed_id
        torrent_info['title'] = title
        torrent_info['sub_title'] = sub_title
        torrent_info['seeding'] = seeding
        torrent_info['downloading'] = downloading
        torrent_info['finished'] = finished
        torrent_info['file_size'] = file_size
        torrent_info['is_new'] = is_new
        torrent_info['is_recommended'] = is_recommended
        torrent_infos.append(torrent_info)

    return torrent_infos

def get_torrent(torrent_infos, tags):
    free_infos = list()
    for torrent_info in torrent_infos:
        if torrent_info['tag'] in tags:
            free_infos.append(torrent_info)

    return free_infos

def get_ok_torrent(torrent_infos):
    def _get_torrent(infos, id):
        flag = False
        for info in infos:
            if id == info[0]:
                flag = True
                break
        return flag

    ok_infos = list()
    for torrent_info in torrent_infos:
        if torrent_info['seed_id'] in old_torrent or _get_torrent(current_torrent, torrent_info['seed_id']):
            continue
        if torrent_info['seeding'] <= 0 or torrent_info['downloading'] < 0:
            continue
        if torrent_info['seeding'] != 0 and float(torrent_info['downloading']) / float(torrent_info['seeding']) < \
                0.6:
            continue

        ok_infos.append(torrent_info)

    return ok_infos

def download_torrent(op_str):

    cookie_jar = RequestsCookieJar()
    for k, v in byrbt_cookies.items():
        cookie_jar[k] = v
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'}

    id_re = re.findall(r'dl (\d+)', op_str, re.I)
    if len(id_re) == 0:
        print('no such torrent')
        return
    torrent_id = id_re[0]

    download_url = 'download.php?id={}'.format(torrent_id)
    download_url = get_url(download_url)
    try:
        torrent = requests.get(download_url, cookies=cookie_jar, headers=headers)
        torrent_file_name = str(torrent.headers['Content-Disposition'].split(';')[1].strip().split('=')[-1][1:-1].encode('ascii', 'ignore').decode('ascii')).replace(' ', '#')
        with open(os.path.join(download_path, torrent_file_name), 'wb') as f:
            f.write(torrent.content)

    except:
        print('login failed!')
        return False

    index = 20
    while index > 0:
        if os.path.exists(os.path.join(download_path, torrent_file_name)):
            if osName == 'Linux':
                torrent_file_path = os.path.join(download_path, torrent_file_name)
                cmd_str = "transmission-remote -n '{}' -a {}".format(_transmission_user_pw, torrent_file_path)
                ret_val = os.system(cmd_str)
                if ret_val != 0:
                    print('script `{}` returns {}'.format(cmd_str, ret_val))
                    print('下载失败')
                else:
                    print('下载成功')
            else:
                print('下载成功')
            return
        else:
            time.sleep(0.5)
            index = index - 1
    print('下载失败')
    return

def execCmd(cmd):
    r = os.popen(cmd)
    text = r.read()
    r.close()
    return text

def op_help():
    return """
    byrbt bot: a bot that handles basic usage of bt.byr.cn
    usage:
        1. main - run main program

        2. download - download and start torrent file
            i.e. dl $id
                $id - torrent id, acquired by `ls` or `se`

        3. list torrent status - list the torrent files status, merely call `transmission-remote -l`
            i.e. tls

        4. remove torrent - remove specific torrent job, merely call `transmission-remote -t $id -r`
            i.e. trm $torrent_id

        5. refresh - refresh cookies
        6. help - print this message
        7. exit
    """

def list_torrent():
    os.system('transmission-remote -n "{}" -l'.format(_transmission_user_pw))

def get_info(text):
    text = text.split('\n')
    sum_to = text[-2]
    text = text[1:-2]
    text_s = list()
    for t in text:
        ts = t.split()
        torrent = dict()
        torrent['id'] = ts[0]
        torrent['done'] = ts[1]
        torrent['size'] = ts[2] + ts[3]
        if 'GB' not in torrent['size']:
            torrent['size'] = '1GB'
        torrent['name'] = ts[-1]
        text_s.append(torrent)
    sum_to = sum_to.split()
    sum_size = sum_to[1] + sum_to[2]
    if 'GB' not in sum_size:
        sum_size['size'] = '1GB'

    return text_s, sum_size

def remove_torrent(op_str):
    id_re = re.findall(r'trm (\d+)', op_str, re.I)
    if len(id_re) == 0:
        print('no such torrent id')
        return
    id_str = id_re[0]
    id_str = str(id_str)

    text = execCmd('transmission-remote -n "{}" -l'.format(_transmission_user_pw))
    text_s, sum_size = get_info(text)
    flag = False
    for to_info in text_s:
        if to_info['id'] == id_str:
            res = execCmd('transmission-remote -n "{}" -t {} -r'.format(_transmission_user_pw,id_str))
            if "success" not in res:
                print('remove torrent fail:')
                for k, v in to_info.items():
                    print('{} : {}'.format(k, v))

            if os.path.exists(os.path.join(download_path, to_info['name'])):
                cmd_str = 'rm -rf {}'.format(os.path.join(download_path, to_info['name']))
                ret_val = os.system(cmd_str)
                if ret_val != 0:
                    print('script `{}` returns {}'.format(cmd_str, ret_val))
                    print(
                        'remove torrent from transmission-daemon success, but cat not remove it from disk!')
            else:
                print(
                    'remove torrent from transmission-daemon success, but not find torrent files! Not remove it from disk!')
            flag = True
            break

    if flag is False:
        print('cat find this torrent id in torrent list, please use cmd "tls" ')

class TorrentBot(ContextDecorator):
    def __init__(self):
        super(TorrentBot, self).__init__()
        self.torrent_url = get_url('torrents.php')
        self.cookie_jar = RequestsCookieJar()
        for k, v in byrbt_cookies.items():
            self.cookie_jar[k] = v
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'}
        self.tags = ['免费', '免费&2x上传']

    def __enter__(self):
        print('启动byrbt_bot!')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('退出')
        print('保存数据')
        pickle.dump((old_torrent, current_torrent), open('./torrent.pkl', 'wb'), protocol=2)

    def remove(self):
        current_torrent.reverse()
        torrent = current_torrent.pop()
        current_torrent.reverse()
        old_torrent.append(torrent[0])
        torrent_file = torrent[1].strip('.torrent')
        text = execCmd('transmission-remote -n "{}" -l'.format(_transmission_user_pw))
        text_s, sum_size = get_info(text)
        flag = False
        for to_info in text_s:
            if to_info['name'] == torrent_file:
                flag = True
                res = execCmd('transmission-remote -n "{}" -t {} -r'.format(_transmission_user_pw,to_info['id']))
                if "success" not in res:
                    print('remove torrent fail:')
                    for k, v in to_info.items():
                        print('{} : {}'.format(k, v))

                if os.path.exists(os.path.join(download_path, to_info['name'])):
                    cmd_str = 'rm -rf {}'.format(os.path.join(download_path, to_info['name']))
                    ret_val = os.system(cmd_str)
                    if ret_val != 0:
                        print('script `{}` returns {}'.format(cmd_str, ret_val))
                        print(
                            'remove torrent from transmission-daemon success, but cat not remove it from disk!')
                else:
                    print(
                        'remove torrent from transmission-daemon success, but not find torrent files! Not remove it from disk!')

                break

        if flag is False:
            print('cat find this torrent id in torrent list, please use cmd "tls" ')

    def download(self, torrent_id):
        download_url = 'download.php?id={}'.format(torrent_id)
        download_url = get_url(download_url)
        for i in range(5):
            try:
                torrent = requests.get(download_url, cookies=self.cookie_jar, headers=self.headers)
                torrent_file_name = str(torrent.headers['Content-Disposition'].split(';')[1].strip().split('=')[-1][1:-1].encode('ascii', 'ignore').decode('ascii')).replace(' ', '#')
                print(torrent_file_name)
                with open(os.path.join(download_path, torrent_file_name), 'wb') as f:
                    f.write(torrent.content)
                break

            except:
                print('login failed')
                byrbt_cookies = load_cookie()
                self.__init__()
                continue

        index = 20
        while index > 0:
            if os.path.exists(os.path.join(download_path, torrent_file_name)):
                if osName == 'Linux':
                    torrent_file_path = os.path.join(download_path, torrent_file_name)
                    cmd_str = "transmission-remote -n '{}' -a {}".format(_transmission_user_pw,torrent_file_path)
                    ret_val = os.system(cmd_str)
                    if ret_val != 0:
                        print('script `{}` returns {}'.format(cmd_str, ret_val))
                        return True
                    else:
                        print('添加种子： {}'.format(torrent_file_name))

                    current_torrent.append((torrent_id, torrent_file_name))

                    if len(current_torrent) > max_torrent:
                        self.remove()

                else:
                    pass
                return True
            else:
                time.sleep(0.5)
                index = index - 1

        return True

    def start(self):
        while True:
            print('扫描种子列表')
            try:
                torrents_soup = BeautifulSoup(requests.get(self.torrent_url, cookies=self.cookie_jar, headers=self.headers).content)
                torrent_table = torrents_soup.select('.torrents > form > tr')[1:]
                pass
            except:
                byrbt_cookies = load_cookie()
                self.__init__()
                continue
            torrent_infos = _get_torrent_info(torrent_table)

            free_infos = get_torrent(torrent_infos, self.tags)
            print('种子列表：')
            for i, info in enumerate(free_infos):
                print('{} : {}'.format(i, info))
            ok_torrent = get_ok_torrent(free_infos)
            print('可用种子：')
            for i, info in enumerate(ok_torrent):
                print('{} : {}'.format(i, info))
            for torrent in ok_torrent:
                if self.download(torrent['seed_id']) is False:
                    print('{} download fail'.format(torrent['title']))
                    continue

            time.sleep(300)

def main():
    with TorrentBot() as byrbt_bot:
        byrbt_bot.start()

if __name__ == '__main__':
    byrbt_cookies = load_cookie()

    print(op_help())
    while True:
        action_str = input()
        if action_str == 'refresh':
            print('refresh cookie by login!')
            byrbt_cookies = login()
        elif action_str == 'exit':
            break
        elif action_str == 'help':
            print(op_help())
        elif action_str == 'main':
            main()
        elif action_str.startswith('dl'):
            download_torrent(action_str)
        elif action_str.startswith('tls'):
            list_torrent()
        elif action_str.startswith('trm'):
            remove_torrent(action_str)
        else:
            print('invalid operation')
            print(op_help())
