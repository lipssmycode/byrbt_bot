# -*- encoding: utf-8 -*-
"""
@File    : config.py
@Time    : 2021/11/20 17:17
@Author  : smy
@Email   : smyyan@foxmail.com
@Software: PyCharm
"""

import configparser


class ReadConfig:

    def __init__(self, filepath=None):
        if filepath:
            config_path = filepath
        else:
            config_path = "config.ini"

        self.cf = configparser.ConfigParser()
        print(config_path)
        self.cf.read(config_path, encoding='utf8')

    def get_bot(self, param):
        value = self.cf.get("ByrBTBot", param, fallback=None)
        return value

    def get_bit_torrent(self, param):
        value = self.cf.get("BitTorrent", param, fallback=None)
        return value


if __name__ == '__main__':
    test = ReadConfig()
    t = test.get_bot("byrbt-url")
    print(t)
