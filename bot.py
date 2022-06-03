# -*- encoding: utf-8 -*-
"""
@File    : bot.py
@Time    : 2021/11/20 17:15
@Author  : smy
@Email   : smyyan@foxmail.com
@Software: PyCharm
"""

from config import ReadConfig
from login import LoginTool

import os
import pickle
import re
import time
import requests
from contextlib import ContextDecorator
from requests.cookies import RequestsCookieJar
from bs4 import BeautifulSoup

from utils.bit_torrent_utils import BitTorrent

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


class TorrentBot(ContextDecorator):
    def __init__(self, config, login, torrent_util):
        super(TorrentBot, self).__init__()
        self.config = config
        self.login = login
        self.torrent_util = torrent_util
        self.base_url = str(config.get_bot("byrbt-url"))
        self.torrent_url = self.get_url('torrents.php')
        self.cookie_jar = RequestsCookieJar()
        self.byrbt_cookies = login.load_cookie()
        for k, v in self.byrbt_cookies.items():
            self.cookie_jar[k] = v
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'}
        self.tags = ['免费', '免费&2x上传']
        self.old_torrent = list()
        self.max_torrent_count = int(config.get_bot("max-torrent"))
        # all size in Byte
        self.max_torrent_total_size = int(config.get_bot("max-torrent-total-size"))
        if self.max_torrent_total_size is None or self.max_torrent_total_size < 0:
            self.max_torrent_total_size = 0
        self.max_torrent_total_size = self.max_torrent_total_size * 1024 * 1024 * 1024
        self.torrent_max_size = int(config.get_bot("torrent-max-size"))
        if self.torrent_max_size is None:
            self.torrent_max_size = 1024
        self.torrent_max_size = self.torrent_max_size * 1024 * 1024 * 1024
        self.torrent_min_size = int(config.get_bot("torrent-min-size"))
        if self.torrent_min_size is None or self.torrent_min_size < 1:
            self.torrent_min_size = 1
        self.torrent_min_size = self.torrent_min_size * 1024 * 1024 * 1024

    def __enter__(self):
        print('启动byrbt_bot!')
        if os.path.exists('torrent.pkl'):
            self.old_torrent = pickle.load(open('torrent.pkl', 'rb'))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('退出')
        print('保存数据')
        pickle.dump(self.old_torrent, open('./torrent.pkl', 'wb'), protocol=2)

    @staticmethod
    def get_tag(tag):
        try:
            if tag == '':
                return ''
            else:
                tag = tag.split('_')[0]

            return _tag_map[tag]
        except KeyError:
            return ''

    @staticmethod
    def get_torrent_info(table):
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
                tag = TorrentBot.get_tag(tds[1].select('table > tr')[0].attrs['class'][0])
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

    @staticmethod
    def get_torrent(torrent_infos, tags):
        free_infos = list()
        for torrent_info in torrent_infos:
            if torrent_info['tag'] in tags:
                free_infos.append(torrent_info)

        return free_infos

    # 获取可用的种子的策略，可自行修改
    def get_ok_torrent(self, torrent_infos):
        ok_infos = list()
        if len(torrent_infos) >= 20:
            # 遇到free或者免费种子太过了，择优选取，标准是(下载数/上传数)>20，并且文件大小大于20GB
            print('符合要求的种子过多，可能开启Free活动了，提高种子获取标准')
            for torrent_info in torrent_infos:
                if torrent_info['seed_id'] in self.old_torrent:
                    continue
                # 下载1GB-1TB之间的种子（下载以GB大小结尾的种子，脚本需要不可修改）
                if 'GB' not in torrent_info['file_size'][0]:
                    continue
                if torrent_info['seeding'] <= 0 or torrent_info['downloading'] < 0:
                    continue
                if torrent_info['seeding'] != 0 and float(torrent_info['downloading']) / float(
                        torrent_info['seeding']) < 20:
                    continue
                file_size = torrent_info['file_size'][0]
                file_size = file_size.replace('GB', '')
                file_size = float(file_size.strip())
                if file_size < 20.0:
                    continue
                ok_infos.append(torrent_info)
        else:
            # 正常种子选择标准是免费种子并且(下载数/上传数)>0.6
            for torrent_info in torrent_infos:
                if torrent_info['seed_id'] in self.old_torrent:
                    continue
                # 下载1GB-1TB之间的种子（下载以GB大小结尾的种子，脚本需要不可修改）
                if 'GB' not in torrent_info['file_size'][0]:
                    continue
                if torrent_info['seeding'] <= 0 or torrent_info['downloading'] < 0:
                    continue
                if torrent_info['seeding'] != 0 and float(torrent_info['downloading']) / float(
                        torrent_info['seeding']) < 0.6:
                    continue
                ok_infos.append(torrent_info)
        return ok_infos

    def get_url(self, url):
        return self.base_url + url

    def check_remove(self):
        torrent_list = self.torrent_util.get_list()
        if torrent_list is None:
            print('get torrent list fail!')

        torrent_len = len(torrent_list)
        if torrent_len <= self.max_torrent_count:
            return
        torrent_list.sort(key=lambda x: x.date_added)
        while torrent_len > self.max_torrent_count:
            remove_torrent_info = torrent_list.pop(0)
            res = self.torrent_util.remove(remove_torrent_info.id, delete_data=True)
            if res:
                print('remove torrent success: ' + str(remove_torrent_info))
            else:
                print('remove torrent fail: ' + str(remove_torrent_info))
            torrent_len = torrent_len - 1

    def download(self, torrent_id):
        download_url = 'download.php?id={}'.format(torrent_id)
        download_url = self.get_url(download_url)
        flag = False
        r = None
        for i in range(5):
            try:
                r = requests.get(download_url, cookies=self.cookie_jar, headers=self.headers)
                flag = True
                break
            except Exception as e:
                print(repr(e))
                print('try login...')
                self.byrbt_cookies = self.login.load_cookie()
                time.sleep(1)

        if flag is False or r is None:
            print('login failed!')

        new_torrent = self.torrent_util.download_from_content(r.content, paused=True)
        if new_torrent is not None:
            new_torrent_size = new_torrent.total_size
            if new_torrent_size < self.torrent_min_size or new_torrent_size > self.torrent_max_size:
                print('add new torrent fail, name : {}, improper seed size: {} GB, download url: {}'.format(
                    new_torrent.name, new_torrent_size / 1000000000, download_url))
                self.old_torrent.append(torrent_id)
                self.torrent_util.remove(new_torrent.id, delete_data=True)
                return False
            res = self.check_free_space_to_download(new_torrent_size)
            if res is None:
                self.torrent_util.remove(new_torrent.id, delete_data=True)
                return False
            if res is False:
                self.torrent_util.remove(new_torrent.id, delete_data=True)
                print('add new torrent fail, not device space to download, name : {}, size: {} GB, '
                      'download url: {}'.format(new_torrent.name, new_torrent_size / 1000000000, download_url))
                return False
            else:
                if self.torrent_util.start_torrent(new_torrent.id):
                    print('add torrent: ' + str(res))
                else:
                    print('add new torrent fail, start torrent fail, name : {}, seed size: {} GB, '
                          'download url: {}'.format(new_torrent.name, new_torrent_size / 1000000000, download_url))
                self.old_torrent.append(torrent_id)
                return True
        else:
            print('add new torrent fail, download url: ' + download_url)
            self.old_torrent.append(torrent_id)
            return False

    def start(self):
        while True:
            print('scan torrent list...')
            flag = False
            torrent_table = None
            try:
                torrents_soup = BeautifulSoup(
                    requests.get(self.torrent_url, cookies=self.cookie_jar, headers=self.headers).content)
                torrent_table = torrents_soup.select('.torrents > form > tr')[1:]
                flag = True
            except Exception as e:
                print(repr(e))
                self.byrbt_cookies = self.login.load_cookie()

            if flag is False:
                print('login failed!')
                break
            torrent_infos = TorrentBot.get_torrent_info(torrent_table)
            free_infos = TorrentBot.get_torrent(torrent_infos, self.tags)
            print('free torrent list：')
            for i, info in enumerate(free_infos):
                print('{} : {} {} {}'.format(i, info['seed_id'], info['file_size'], info['title']))
            ok_torrent = self.get_ok_torrent(free_infos)
            print('available torrent list：')
            for i, info in enumerate(ok_torrent):
                print('{} : {} {} {}'.format(i, info['seed_id'], info['file_size'], info['title']))
            for torrent in ok_torrent:
                if self.download(torrent['seed_id']) is False:
                    print('{} download fail'.format(torrent['title']))
                    continue
            self.check_remove()
            time.sleep(60)

    def check_free_space_to_download(self, new_torrent_size):
        torrent_list = self.torrent_util.get_list()
        if torrent_list is None:
            print('get torrent list fail!')
            return None
        free_space = self.torrent_util.get_free_space()
        if free_space is None:
            print('get download path free space fail!')
            return None
        sum_size = 0
        for torrent in torrent_list:
            sum_size += torrent.total_size
        if sum_size + free_space <= new_torrent_size:
            return False

        torrent_list.sort(key=lambda x: x.date_added)
        while free_space <= new_torrent_size and len(torrent_list) > 0:
            remove_torrent_info = torrent_list.pop(0)
            res = self.torrent_util.remove(remove_torrent_info.id, delete_data=True)
            if res:
                print('remove torrent success: ' + str(remove_torrent_info))
            else:
                print('remove torrent fail: ' + str(remove_torrent_info))
                return None
            free_space += remove_torrent_info.total_size

        return self.torrent_util.get_free_space() > new_torrent_size


if __name__ == '__main__':
    config = ReadConfig(filepath='config.ini')
    login = LoginTool(config)
    bit_torrent = BitTorrent(config)
    with TorrentBot(config, login, bit_torrent) as byrbt_bot:
        byrbt_bot.start()