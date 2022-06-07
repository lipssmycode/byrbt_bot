# -*- encoding: utf-8 -*-
"""
@File    : bit_torrent_utils.py
@Time    : 2022/5/8 19:01
@Author  : smy
@Email   : smyyan@foxmail.com
@Software: PyCharm
"""

from config import ReadConfig
from transmission_rpc import Client
import time


class BitTorrent:
    def __init__(self, config):
        self.host = config.get_transmission_config('transmission-host')
        self.port = config.get_transmission_config('transmission-port')
        self.username = config.get_transmission_config('transmission-username')
        self.password = config.get_transmission_config('transmission-password')
        self.download_path = config.get_transmission_config('transmission-download-path')

    def download_from_file(self, filepath, paused=False):
        try:
            c = Client(host=self.host, port=self.port, username=self.username, password=self.password)
            with open(filepath, 'rb') as f:
                res = c.add_torrent(f, paused=paused, timeout=(60, 120))
                if res is None:
                    return None
                time.sleep(1)  # wait 1s for torrent add to transmission
                return c.get_torrent(res.id)
        except Exception as e:
            print('[ERROR] ' + repr(e))
            return None

    def download_from_content(self, content, paused=False):
        try:
            c = Client(host=self.host, port=self.port, username=self.username, password=self.password)
            res = c.add_torrent(content, paused=paused, timeout=(60, 120))
            if res is None:
                return None
            time.sleep(1)  # wait 1s for torrent add to transmission
            return c.get_torrent(res.id)
        except Exception as e:
            print('[ERROR] ' + repr(e))
            return None

    def remove(self, ids, delete_data=False):
        try:
            c = Client(host=self.host, port=self.port, username=self.username, password=self.password)
            c.remove_torrent(ids, delete_data=delete_data, timeout=(60, 120))
            return True
        except Exception as e:
            print('[ERROR] ' + repr(e))
            return False

    def start_torrent(self, ids):
        try:
            c = Client(host=self.host, port=self.port, username=self.username, password=self.password)
            c.start_torrent(ids, timeout=(60, 120))
            return True
        except Exception as e:
            print('[ERROR] ' + repr(e))
            return False

    def get_list(self):
        try:
            c = Client(host=self.host, port=self.port, username=self.username, password=self.password)
            return c.get_torrents(timeout=(60, 120))
        except Exception as e:
            print('[ERROR] ' + repr(e))
            return None

    def get_free_space(self):
        try:
            c = Client(host=self.host, port=self.port, username=self.username, password=self.password)
            return c.free_space(self.download_path, timeout=(60, 120))
        except Exception as e:
            print('[ERROR] ' + repr(e))
            return None


if __name__ == '__main__':
    config = ReadConfig(filepath='../config/config.ini')
    bit_torrent = BitTorrent(config)
    torrents = bit_torrent.get_list()
