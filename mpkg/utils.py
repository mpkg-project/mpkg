#!/usr/bin/env python3
# coding: utf-8

import gettext
import os

import requests

_ = gettext.gettext

downloader = r'wget -P "d:\Downloads"'


def GetPage(url: str, **kwargs) -> str:
    return requests.get(url, **kwargs).text


def Download(url: str):
    os.system(f'{downloader} "{url}"')


def Selected(L: list, isSoft=False, msg=_('select (eg: 0,2-5):')) -> list:
    cfg = []
    for i, x in enumerate(L):
        if isSoft:
            print(f'{i} -> {x.id}')
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


def IsLatest(bydate=False):
    pass
