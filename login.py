# -*- encoding: utf-8 -*-
"""
@File    : utils.py
@Time    : 2021/11/20 16:56
@Author  : smy
@Email   : smyyan@foxmail.com
@Software: PyCharm
"""
import atexit
import platform
import shutil
from DrissionPage import WebPage, ChromiumOptions
import os
from urllib.parse import urljoin


class LoginTool:

    def __init__(self, bot_config):
        self.config = bot_config
        self.try_count = 5
        self.base_url = str(self.config.get_bot_config("byrbt-url"))
        self.cookie_save_path = './data/ByrbtCookies.pickle'
        self.chromium_local_port = int(self.config.get_bot_config("chromium-local-port"))
        self.chromium_user_data_path = r'./data/cache/drission_page'
        self.chromium_cache_path = r'./data/cache/drission_page_cache'
        self.chromium_proxy = str(self.config.get_bot_config("chromium-proxy"))
        self.chromium_options = self.init_chromium_options()
        self.page = None

    def init_chromium_options(self):
        chromium_options = ChromiumOptions().set_paths(
            local_port=self.chromium_local_port,
            user_data_path=self.chromium_user_data_path,
            cache_path=self.chromium_cache_path,
        )
        chromium_options.no_imgs(True).mute(True)
        system = platform.system()
        if system == 'Windows' or system == 'Darwin':
            pass
        elif system == 'Linux':
            chromium_options = chromium_options.headless()
            chromium_options = chromium_options.set_argument('--test-type')
            chromium_options = chromium_options.set_argument('--disable-gpu')
            chromium_options = chromium_options.set_argument('--no-sandbox')
            chromium_options = chromium_options.set_argument('--no-zygote')
            chromium_options = chromium_options.set_argument("--disable-dev-shm-usage")
            chromium_options = chromium_options.set_argument("--disable-infobars")
            chromium_options = chromium_options.set_argument("--disable-extensions")
            chromium_options = chromium_options.set_argument("--disable-browser-side-navigation")
            chromium_options = chromium_options.set_argument("--window-position=0,0")
            chromium_options = chromium_options.set_argument("--window-size=1920,1080")
        else:
            print(f'not support platform {system}')
            exit(1)
        if len(self.chromium_proxy) > 0:
            chromium_options = chromium_options.set_proxy(self.chromium_proxy)
        return chromium_options

    def get_url(self, url_path):
        return urljoin(self.base_url, url_path)

    def clear_browser(self):
        if self.page is not None:
            atexit.unregister(self.page.close())
            self.page.close()
        self.page = None
        if os.path.exists(self.chromium_user_data_path):
            shutil.rmtree(self.chromium_user_data_path)
        os.makedirs(self.chromium_user_data_path, exist_ok=True)
        if os.path.exists(self.chromium_cache_path):
            shutil.rmtree(self.chromium_cache_path)
        os.makedirs(self.chromium_cache_path, exist_ok=True)
        print('clear browser done!')

    def login(self):
        self.page = WebPage(chromium_options=self.chromium_options)
        atexit.register(self.page.close)
        if self.page.get(self.base_url, retry=5) is False:
            print('failed to access the website!', self.base_url)
            return None
        if self.page.url.endswith('login'):
            self.page.ele('@autocomplete=username').input(str(config.get_bot_config("username")), clear=True)
            self.page.ele('@autocomplete=current-password').input(str(config.get_bot_config("passwd")), clear=True)
            self.page.ele('@text()=保持登录').click()
            self.page.ele('@text()= 登录 ').click()
            if self.page.wait.load_start(timeout=30) is False:
                print('login timeout!')
                return None
            if self.page.wait.doc_loaded(timeout=30) is False:
                print('login timeout!')
                return None
        if self.page.url != self.base_url and '最近消息' not in self.page.html:
            print('login failed!')
            return None
        print('login success!')
        return self.page


if __name__ == '__main__':
    from config import ReadConfig

    config = ReadConfig()
    loginTool = LoginTool(config)
    loginTool.login()
