#!/usr/bin/env python3
# coding: utf-8

import argparse
import os
import re
import time
from functools import lru_cache
from multiprocessing.dummy import Pool
from pathlib import Path
from pprint import pformat, pprint
from typing import List, Tuple
from urllib.parse import unquote

import requests
from lxml import etree

downloader = r'wget -P "d:\Downloads"'

UA = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/601.4.4 (KHTML, like Gecko) Version/9.0.3 Safari/601.4.4'}
defaultList = [-1, -1, -1]
defaultLog = ''

parser = argparse.ArgumentParser(description='get latest software')
parser.add_argument('action', help='check|upgrade')
parser.add_argument('--bydate', default=False,
                    action='store_true', help='check version by date')
parser.add_argument('-s', '--skip', default=False,
                    action='store_true', help='skip latest software')
parser.add_argument('-j', '--jobs', default=10, type=int, help='threads')
parser.add_argument('-d', '--download', default=False, action='store_true')
#parser.add_argument('-i', '--install', default=False, action='store_true')
args = parser.parse_args()


def getPage(url: str, **kwargs) -> str:
    return requests.get(url, **kwargs).text


def selected(L: list, isSoft=False, msg='select (eg: 0,2-5):') -> list:
    cfg = []
    for i, x in enumerate(L):
        if isSoft:
            print(f'{i} -> {x.name}')
        else:
            print(f'{i} -> {x}')
    option = input(f' {msg} ').replace(' ', '').split(',')
    print()
    for i in option:
        if '-' in i:
            a, b = i.split('-')
            for j in range(int(a), int(b)+1):
                cfg.append(L[j])
        else:
            cfg.append(L[int(i)])
    return cfg


class Soft(object):
    isStatic = True
    allowExtract = False
    isPrepared = False
    isLatest = False
    info = ''

    def __init__(self, name: str, rem=''):
        self.name = name
        self.rem = rem
        self.bydate = args.bydate

    def _getInfo(self) -> Tuple[List[int], List[int]]:
        return defaultList, defaultList

    def _parse(self) -> Tuple[List[int], List[int], List[str], str]:
        return defaultList, defaultList, ['url'], defaultLog

    def check(self):
        if not self.isPrepared:
            self.prepare()
        print(self.info)

    def download(self):
        # -v print('使用缺省下载方案')
        if not self.isLatest:
            if len(self.links) != 1:
                link = selected(self.links, msg='select a url:')[0]
            else:
                link = self.links[0]
            os.system(f'{downloader} "{link}"')

    def prepare(self) -> str:
        self.isPrepared = True
        self.oldV, self.oldD = self._getInfo()
        self.ver, self.date, self.links, self.log = self._parse()
        if self.bydate:
            if self.date == self.oldD and self.date != defaultList:
                self.isLatest = True
        else:
            if self.ver == self.oldV and self.ver != defaultList:
                self.isLatest = True
        info = []
        if self.isLatest:
            if args.skip:
                return
            info.append(f'{self.name}, {self.ver}')
            info.append(' -> Already up to date.')
        else:
            if self.ver == defaultList:
                info.append(f'{self.name}')
            elif self.oldV == defaultList:
                info.append(f'{self.name} {self.ver}')
            else:
                info.append(f'{self.name} {self.oldV} -> {self.ver}')
            # indent=1
            if self.date != defaultList:
                info.append(f' {self.date}')
            info.append(' '+'\n '.join(pformat(self.links).splitlines()))
            if self.rem:
                info.append(f' rem: {self.rem}')
            if self.log:
                info.append(f' changelog: {self.log}')
        info.append('')
        self.info = '\n'.join(info)


def getDevconInfo(node: str) -> Tuple[List[int], List[int]]:
    cmd = 'devcon drivernodes @'+node.replace('&', '^&')
    with os.popen(cmd) as p:
        L = p.read().split('#')
    if len(L) < 2:
        print(f'wrong node\ncommand: {cmd}\nresult:{L}')
        return defaultList, defaultList
    else:
        L = L[1:]
    t = [(list(map(int, re.search('    Driver date is (.*)', t).group(1).split('/'))),
          list(map(int, re.search('    Driver version is (.*)', t).group(1).split('.')))) for t in L]
    t.sort(key=lambda x: x[1], reverse=True)
    ver, date = t[0][1], t[0][0]
    return ver, date


class Driver(Soft):
    isStatic = False

    def __init__(self, name: str, drivernode: str, url: str, rem=''):
        super().__init__(name, rem=rem)
        self.name = name
        self.node = drivernode
        self.rem = rem
        self.url = url

    def _getInfo(self) -> Tuple[List[int], List[int]]:
        return getDevconInfo(self.node)


class NvidiaDriver(Driver):
    def __init__(self, name, drivernode, url, rem='', isStudio=False):
        super().__init__(name, drivernode, url, rem=rem)
        self.isStudio = isStudio

    def _getInfo(self):
        oldv, oldD = getDevconInfo(self.node)
        with os.popen('nvidia-smi') as p:
            oldV = list(map(int, p.read().split('Driver Version: ')
                            [1].split(' ')[0].split('.')))
        strV = ''.join(map(str, oldV))
        if not ''.join(map(str, oldv))[-len(strV):] == strV:
            print(f'warning: oldV conflict\ndevcon:{oldv}\nsmi:{oldV}')
        return oldV, oldD

    def _parse(self):
        r = requests.get(self.url, headers=UA).text
        L = etree.HTML(r).xpath('//*[@id="driverList"]')
        if self.isStudio:
            L = [x for x in L if x.xpath(
                './/a')[0].text == 'NVIDIA Studio Driver']
        else:
            L = [x for x in L if x.xpath(
                './/a')[0].text != 'NVIDIA Studio Driver']
        r = L[0].xpath('.//td')
        date = time.strptime(r[3].text, '%B %d, %Y')[0:3]
        v = r[2].text
        u = [
            f'https://us.download.nvidia.com/Windows/{v}/{v}-notebook-win10-64bit-international-dch-whql.exe']
        log = f'https://us.download.nvidia.com/Windows/{v}/{v}-win10-win8-win7-release-notes.pdf'
        return list(map(int, v.split('.'))), date, u, log


@lru_cache
def getIntelList(URL) -> list:
    # ['英特尔®显卡-Windows® 10 DCH 驱动程序', '驱动程序', ['Windows 10，64 位*'], '27.20.100.8280', '05-29-2020', '/zh-cn/download/29616/-Windows-10-DCH-']
    u = URL.split('/product/')
    u = u[0] + '/json/pageresults?pageNumber=2&productId=' + u[1]
    # u = u[0] + '/json/pageresults?productId=' + u[1]
    r = requests.get(u).json()
    return [[x['Title'], x['DownloadType'], x['OperatingSystemSet'], x['Version'], x['PublishDateMMDDYYYY'], x['FullDescriptionUrl']] for x in r['ResultsForDisplay']]


def getIntelDrivers(u) -> list:
    r = requests.get(u).text
    u = [x.xpath('.//a')[0].values()[1]
         for x in etree.HTML(r).xpath('//*[@class="download-file"]')]
    drivers = [unquote(x).split('httpDown=')[::-1][0] for x in u]
    return drivers


class IntelWifi(Soft):
    def __init__(self, name, node, rem=''):
        super().__init__(name, rem=rem)
        self.node = node

    def _getInfo(self):
        oldv, oldD = getDevconInfo(self.node)
        return oldv[:3], oldD

    def _parse(self):
        page = getPage(
            'https://www.intel.cn/content/www/cn/zh/support/articles/000017246/network-and-i-o/wireless-networking.html')
        a = [x for x in etree.HTML(page).xpath(
            '//a') if b'&#229;&#156;&#168;&#230;&#173;&#164;&#229;&#164;&#132;&#228;&#184;&#139;&#232;&#189;&#189;' in etree.tostring(x)]
        if len(a) == 1:
            links = sorted(getIntelDrivers(a[0].values()[0]), reverse=True)[:3]
        else:
            print('IntelWifi(Soft) parsing error')
        return defaultList, defaultList, links, defaultLog


class IntelDriver(Driver):
    def __init__(self, name, drivernode, url, driverKeyword, rem='', verLen=0):
        super().__init__(name, drivernode, url, rem=rem)
        self.verLen = verLen
        self.kw = driverKeyword

    def _getInfo(self):
        oldv, oldD = getDevconInfo(self.node)
        if self.verLen == 0:
            self.verLen = len(oldv)
        return oldv[:self.verLen], oldD

    def _parse(self):
        L = getIntelList(self.url)
        item = sorted([x for x in L if self.kw in x[0]],
                      key=lambda x: x[3], reverse=True)[0]
        date = item[4].split('-')
        date = [date[-1]]+date[:-1]
        ver = item[3]
        url = 'https://downloadcenter.intel.com'+item[-1]
        drivers = getIntelDrivers(url)
        return list(map(int, ver.split('.'))), list(map(int, date)), drivers, defaultLog


def prepare(soft):
    soft.prepare()


def main():
    SOFTS = [NvidiaDriver('rtx', '',
                          'https://www.nvidia.com/Download/processFind.aspx?psid=111&pfid=888&osid=57&lid=1&whql=&lang=en-us&ctk=0&dtcid=1'),
             IntelDriver('uhd', '',
                         'https://downloadcenter.intel.com/zh-cn/product/134906', driverKeyword='英特尔®显卡-Windows® 10 DCH 驱动程序'),
             IntelDriver('wifi', '',
                         'https://downloadcenter.intel.com/product/125192', driverKeyword='Windows® 10 Wi-Fi Drivers for Intel® Wireless Adapters', verLen=3),
             ]

    if args.action == 'check':
        soft_list = selected(SOFTS, True)
    elif args.action == 'upgrade':
        soft_list = SOFTS

    with Pool(args.jobs) as p:
        p.map(prepare, soft_list)

    for soft in soft_list:
        soft.check()

    soft_list = [soft for soft in soft_list if not soft.isLatest]

    if args.download:
        for soft in soft_list:
            soft.download()


if __name__ == "__main__":
    main()
