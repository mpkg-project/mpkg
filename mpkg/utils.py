#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
from pathlib import Path

import requests

from .config import HOME, GetConfig, SetConfig

_ = gettext.gettext

downloader = GetConfig('downloader')


def GetPage(url: str, warn=True, **kwargs) -> str:
    res = requests.get(url, **kwargs)
    if warn and res.status_code != 200:
        print(f'warning: {url} {res.status_code}')
        return 'error'
    return res.text


def Download(url: str, directory=HOME, filename=False):
    print(_('downloading {url}').format(url=url))
    directory = Path(directory)
    file = directory / filename
    if not directory.exists():
        directory.mkdir(parents=True)
    if not filename:
        filename = url.split('/')[-1]
    if '{file}' in downloader:
        command = downloader.format(url=url, file=file)
    else:
        command = downloader.format(
            url=url, directory=directory, filename=filename)
    os.system(command)
    file = directory / filename
    if not file.is_file():
        print(f'warning: no {file}')
        print(f'command: {command}')
    return str(file)


def Selected(L: list, isSoft=False, msg=_('select (eg: 0,2-5):')) -> list:
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


def Name(softs):
    names, ids = [], []
    multiple, named = [], []
    for soft in softs:
        cfg = soft.get('cfg')
        if cfg:
            multiple.append(soft)
        name = soft.get('name')
        if name:
            names.append(name)
            named.append(soft)
        ids.append(soft['id'])
    for soft in named:
        if soft['name'] in ids or names.count(soft['name']) > 1:
            soft['name'] = soft['name']+'-'+soft['id']
    for soft in multiple:
        if not soft.get('name'):
            soft['name'] = soft['id']+'.'+soft['name'].split('.')[-1]
    names = []
    for soft in softs:
        if not soft.get('name'):
            soft['name'] = soft['id']
        names.append(soft['name'])
    if len(names) != len(set(names)):
        print(f'warning: name conflict\n{names}')


def IsLatest(bydate=False):
    pass
