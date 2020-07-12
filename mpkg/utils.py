#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
import re
import time
from pathlib import Path
from platform import architecture

import click
import requests

from .config import HOME, GetConfig, SetConfig

_ = gettext.gettext
arch = architecture()[0]


def Redirect(url: str) -> str:
    rules = GetConfig('redirect')
    for rule in rules:
        for pattern, to in rule.items():
            m = re.match(pattern, url)
            if m:
                return to.format(*m.groups())
    return url


def GetPage(url: str, warn=True, **kwargs) -> str:
    url = Redirect(url)
    res = requests.get(url, **kwargs)
    if warn and res.status_code != 200:
        print(f'warning: {url} {res.status_code}')
        return 'error'
    return res.text


def Download(url: str, directory='', filename='', output=True):
    url = Redirect(url)
    if not directory:
        directory = GetConfig('download_dir')
    directory = Path(directory)
    if not directory.exists():
        directory.mkdir(parents=True)
    if not filename:
        filename = url.split('/')[-1]
    file = directory / filename
    if output:
        print(_('downloading {url}').format(url=url))
        print(_('saving to {path}').format(path=file))
    downloader = GetConfig('downloader')
    if downloader:
        filepath, directory, filename = f'"{file}"', f'"{directory}"', f'"{filename}"'
        if '{filepath}' in downloader:
            command = downloader.format(url=url, filepath=filepath)
        else:
            command = downloader.format(
                url=url, directory=directory, filename=filename)
        os.system(command)
    else:
        req = requests.get(url, stream=True)
        if req.status_code != 200:
            print(f'warning: {url} {req.status_code}')
            print(' try to download it with downloader')
            print('  if you have installed wget')
            print(r'  try mpkg set downloader "wget -q -O {filepath} {url}"')
        chunk_size = 4096
        contents = req.iter_content(chunk_size=chunk_size)
        length = int(req.headers['content-length'])/chunk_size
        with click.progressbar(contents, length=length) as bar:
            with open(str(file), 'wb') as f:
                for chunk in bar:
                    if chunk:
                        f.write(chunk)
    if not file.is_file():
        print(f'warning: no {file}')
        print(f'command: {command}')
    return file


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


def ToLink(links: list):
    if len(links) != 1:
        link = Selected(links, msg=_('select a link:'))[0]
        return {arch: link}
    else:
        return {arch: links[0]}


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


def GetOutdated():
    installed = GetConfig(filename='installed.json')
    latest = {}
    for soft in GetConfig('softs', filename='softs.json'):
        latest[soft['name']] = [soft['ver'], soft.get('date')]
    outdated = {}
    for name, value in installed.items():
        date = latest[name][1]
        if date:
            date = time.strftime(
                '%y%m%d', time.strptime(date, '%Y-%m-%d'))
        else:
            date = ''
        if value[0] != latest[name][0]:
            outdated[name] = [date, value[0], latest[name][0]]
        elif latest[name][1] and value[1] != latest[name][1]:
            outdated[name] = [date, value[0], latest[name][0]]
    return outdated


def PreInstall():
    SetConfig('download_dir', str(HOME))
    for ext in ['py', 'json', 'zip']:
        directory = HOME / ext
        if not directory.exists():
            directory.mkdir(parents=True)
