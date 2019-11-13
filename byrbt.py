#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/2 16:23
# @Author  : 邵明岩
# @File    : brybt.py
# @Software: PyCharm

import time
import os
import re
import pickle
from io import BytesIO
from urllib.request import urlopen
import platform
from contextlib import ContextDecorator
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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
_username = '账户'
_passwd = '密码'
_transmission_user_pw = 'user:password'

# 全局变量
options = Options()
chrome_driver = '/root/chromedriver'
download_path = None

if osName == 'Windows':
    # options.add_argument('--headless')
    # options.add_argument('--disable-gpu')
    options.add_argument('--user-agent="Magic Browser"')
    download_path = os.path.abspath('./torrent')
    prefs = {'profile.default_content_settings.popups': 0, 'download.default_directory': download_path}
    options.add_experimental_option('prefs', prefs)
    chrome_driver = 'D:\\workplace\\python\\crawler\\chromedriver.exe'
elif osName == 'Linux':
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--user-agent="Magic Browser"')
    download_path = os.path.abspath('/home/.bt/torrents')
    prefs = {'download.prompt_for_download': False, 'download.default_directory': download_path}
    options.add_experimental_option('prefs', prefs)
    # brower.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
    # params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_path}}
    # command_result = brower.execute("send_command", params)
    chrome_driver = '/root/chromedriver'
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
    index_url = get_url('index.php')
    browser = webdriver.Chrome(options=options, executable_path=chrome_driver)
    browser.get(url)
    wait_browser = WebDriverWait(browser, 1)

    while True:
        # login byrbt

        image = wait_browser.until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                                            '#nav_block > form:nth-child(6) > table > tbody > tr:nth-child(3) > td:nth-child(2) > img'))
        )
        image_url = image.get_attribute('src')
        image_file = Image.open(BytesIO(urlopen(image_url).read()))
        captcha_text = decaptcha.decode(image_file)

        username = wait_browser.until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                                            '#nav_block > form:nth-child(6) > table > tbody > tr:nth-child(1) > td.rowfollow > input[type=text]'))
        )
        username.clear()
        username.send_keys(_username)
        passwd = wait_browser.until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                                            '#nav_block > form:nth-child(6) > table > tbody > tr:nth-child(2) > td.rowfollow > input[type=password]'))
        )
        passwd.clear()
        passwd.send_keys(_passwd)
        captcha = wait_browser.until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                                            '#nav_block > form:nth-child(6) > table > tbody > tr:nth-child(4) > td:nth-child(2) > input[type=text]:nth-child(1)'))
        )
        captcha.clear()
        captcha.send_keys(captcha_text)

        ok_btn = wait_browser.until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                                            '#nav_block > form:nth-child(6) > table > tbody > tr:nth-child(9) > td > input:nth-child(1)'))
        )

        ok_btn.click()

        time.sleep(1)
        # if login in successfully, url  jump to byr.bt.cn/index.php
        try_nums = 5
        while True:
            if browser.current_url == index_url:
                byrbt_cookies = browser.get_cookies()
                browser.quit()
                cookies = {}
                for item in byrbt_cookies:
                    cookies[item['name']] = item['value']
                output_path = open('ByrbtCookies.pickle', 'wb')
                pickle.dump(cookies, output_path)
                output_path.close()

                del browser
                kill_chrome()

                return cookies
            else:
                try_nums = try_nums - 1
                time.sleep(1)

            if try_nums <= 0:
                browser.quit()
                del browser
                kill_chrome()

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
    for idx in range(1, len(table)):
        torrent_info = dict()
        item = table[idx]
        tds = item.find_elements_by_xpath('./td')

        cat = tds[0].find_element_by_xpath('./a/img').get_attribute('title')
        main_td = tds[1].find_element_by_xpath('./table/tbody/tr/td')
        href = main_td.find_element_by_xpath('./a').get_attribute('href')
        seed_id = re.findall(r'id=(\d+)&', href)[0]
        title = main_td.get_attribute('innerText')
        title = title.split('\n')
        if len(title) == 2:
            sub_title = title[1]
            title = title[0]
        else:
            sub_title = ''
            title = title[0]

        tags = set([
            font.get_attribute('class') for font in main_td.find_elements_by_xpath('./b/font')
        ])
        if '' in tags:
            tags.remove('')

        is_seeding = len(main_td.find_elements_by_xpath('./img[@src="pic/seeding.png"]')) > 0
        is_finished = len(main_td.find_elements_by_xpath('./img[@src="pic/finished.png"]')) > 0
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

        tag = _get_tag(tds[1].find_element_by_xpath('./table/tbody/tr').get_attribute('class'))

        file_size = tds[4].text.split('\n')

        seeding = int(tds[5].text) if tds[5].text.isdigit() else -1

        downloading = int(tds[6].text) if tds[6].text.isdigit() else -1

        finished = int(tds[7].text) if tds[7].text.isdigit() else -1

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
    id_re = re.findall(r'dl (\d+)', op_str, re.I)
    if len(id_re) == 0:
        print('no such torrent')
        return
    id_str = id_re[0]

    detail_url = 'details.php?id={}'.format(id_str)
    detail_url = get_url(detail_url)

    browser = webdriver.Chrome(options=options, executable_path=chrome_driver)
    if osName == 'Linux':
        browser.command_executor._commands["send_command"] = ("POST", '/session/$sessionId/chromium/send_command')
        params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_path}}
        command_result = browser.execute("send_command", params)

    browser.get(detail_url)
    for cookie in byrbt_cookies:
        browser.add_cookie({
            "domain": ".byr.cn",
            "name": cookie,
            "value": byrbt_cookies[cookie],
            "path": '/',
            "expires": None
        })
    browser.get(detail_url)
    wait_brower = WebDriverWait(browser, 3)
    name_element = browser.find_element_by_xpath('//td/a[@class="index"]')
    file_name = name_element.text
    download_btn = wait_brower.until(
        EC.presence_of_element_located((By.CSS_SELECTOR,
                                        '#outer > table:nth-child(6) > tbody > tr:nth-child(5) > td.rowfollow > a:nth-child(1) > b > font'))
    )
    download_btn.click()
    index = 20
    while index > 0:
        if os.path.exists(os.path.join(download_path, file_name)):
            browser.quit()
            if osName == 'Linux':
                torrent_file_path = os.path.join(download_path, file_name)
                cmd_str = "transmission-remote -n '{}' -a {}".format(_transmission_user_pw,torrent_file_path)
                ret_val = os.system(cmd_str)
                if ret_val != 0:
                    print('script `{}` returns {}'.format(cmd_str, ret_val))
                    print('下载失败')
                else:
                    print('下载成功')
            else:
                print('下载成功')
            del browser
            kill_chrome()
            return
        else:
            time.sleep(0.5)
            index = index - 1

    browser.quit()
    del browser
    kill_chrome()
    print('下载失败')


def execCmd(cmd):
    r = os.popen(cmd)
    text = r.read()
    r.close()
    return text


def kill_all(pids):
    for pid in pids:
        os.system('sudo kill -9 {}'.format(pid))


def kill_chrome():
    time.sleep(1)
    kill_all(execCmd("sudo ps -ef | grep 'chrome' | grep -v grep | awk '{print $2}'").split('\n')[:-1])


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
    os.system('sudo transmission-remote -n "{}" -l'.format(_transmission_user_pw))


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

    text = execCmd('sudo transmission-remote -n "{}" -l'.format(_transmission_user_pw))
    text_s, sum_size = get_info(text)
    flag = False
    for to_info in text_s:
        if to_info['id'] == id_str:
            res = execCmd('sudo transmission-remote -n "{}" -t {} -r'.format(_transmission_user_pw,id_str))
            if "success" not in res:
                print('remove torrent fail:')
                for k, v in to_info.items():
                    print('{} : {}'.format(k, v))

            if os.path.exists(os.path.join(download_path, to_info['name'])):
                cmd_str = 'sudo rm -rf {}'.format(os.path.join(download_path, to_info['name']))
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

        self.browser = webdriver.Chrome(options=options, executable_path=chrome_driver)
        if osName == 'Linux':
            self.browser.command_executor._commands["send_command"] = (
                "POST", '/session/$sessionId/chromium/send_command')
            params = {'cmd': 'Page.setDownloadBehavior', 'params': {'behavior': 'allow', 'downloadPath': download_path}}
            command_result = self.browser.execute("send_command", params)

        self.wait_browser = WebDriverWait(self.browser, 5)
        self.tags = ['免费', '免费&2x上传']

    def __enter__(self):
        print('启动byrbt_bot!')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('退出')
        print('保存数据')
        pickle.dump((old_torrent, current_torrent), open('./torrent.pkl', 'wb'), protocol=2)
        print('清理chrome线程')
        kill_chrome()

    def clear_browse(self):

        self.browser.delete_all_cookies()
        self.browser.get(self.torrent_url)
        for cookie in byrbt_cookies:
            self.browser.add_cookie({
                "domain": ".byr.cn",
                "name": cookie,
                "value": byrbt_cookies[cookie],
                "path": '/',
                "expires": None
            })
        self.browser.get(self.torrent_url)

    def init(self, url=None):
        print('初始化...')
        self.browser.quit()
        del self.browser
        self.browser = None
        kill_chrome()
        print('清理完毕')
        while True:
            self.browser = webdriver.Chrome(options=options, executable_path=chrome_driver)
            if osName == 'Linux':
                self.browser.command_executor._commands["send_command"] = (
                    "POST", '/session/$sessionId/chromium/send_command')
                params = {'cmd': 'Page.setDownloadBehavior',
                          'params': {'behavior': 'allow', 'downloadPath': download_path}}
                command_result = self.browser.execute("send_command", params)
            self.browser.get(self.torrent_url)
            for cookie in byrbt_cookies:
                self.browser.add_cookie({
                    "domain": ".byr.cn",
                    "name": cookie,
                    "value": byrbt_cookies[cookie],
                    "path": '/',
                    "expires": None
                })

            self.wait_browser = WebDriverWait(self.browser, 5)
            print('初始化完毕！')
            if url is not None:
                try:
                    self.browser.get(url)
                    time.sleep(1)
                    if self.browser.current_url == url:
                        break

                except:
                    pass

    def remove(self):
        current_torrent.reverse()
        torrent = current_torrent.pop()
        current_torrent.reverse()
        old_torrent.append(torrent[0])
        torrent_file = torrent[1].strip('.torrent')
        text = execCmd('sudo transmission-remote -n "{}" -l'.format(_transmission_user_pw))
        text_s, sum_size = get_info(text)
        flag = False
        for to_info in text_s:
            if to_info['name'] == torrent_file:
                flag = True
                res = execCmd('sudo transmission-remote -n "{}" -t {} -r'.format(_transmission_user_pw,to_info['id']))
                if "success" not in res:
                    print('remove torrent fail:')
                    for k, v in to_info.items():
                        print('{} : {}'.format(k, v))

                if os.path.exists(os.path.join(download_path, to_info['name'])):
                    cmd_str = 'sudo rm -rf {}'.format(os.path.join(download_path, to_info['name']))
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
        detail_url = 'details.php?id={}'.format(torrent_id)
        detail_url = get_url(detail_url)
        try:
            self.browser.get(detail_url)
            name_element = self.wait_browser.until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                '#outer > table:nth-child(2) > tbody > tr:nth-child(1) > td.rowfollow > a.index'))
            )
            file_name = name_element.text
            download_btn = self.wait_browser.until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                '#outer > table:nth-child(2) > tbody > tr:nth-child(5) > td.rowfollow > a:nth-child(1) > b > font'))
            )
            download_btn.click()

        except:
            print('Error 3')
            return False

        index = 20
        while index > 0:
            if os.path.exists(os.path.join(download_path, file_name)):
                if osName == 'Linux':
                    torrent_file_path = os.path.join(download_path, file_name)
                    cmd_str = "transmission-remote -n '{}' -a {}".format(_transmission_user_pw,torrent_file_path)
                    ret_val = os.system(cmd_str)
                    if ret_val != 0:
                        print('script `{}` returns {}'.format(cmd_str, ret_val))
                        return True
                    else:
                        print('添加种子： {}'.format(file_name))

                    current_torrent.append((torrent_id, file_name))

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
        index = 12
        while True:
            self.init(url=self.torrent_url)
            print('扫描种子列表')
            try:
                time.sleep(1)
                self.browser.get(self.torrent_url)
                time.sleep(1)
                torrent_table = self.wait_browser.until(
                    EC.presence_of_all_elements_located((By.XPATH,
                                                         '//*[@id="outer"]/table/tbody/tr/td/table/tbody/tr'))
                )
            except:
                print('Error 1')
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
            flag = True
            for torrent in ok_torrent:
                if self.download(torrent['seed_id']) is False:
                    flag = False
                    break

            if flag is False:
                self.browser.quit()
                print('Error 2')
                continue

            time.sleep(300)
            index = index - 1
            self.browser.quit()


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
