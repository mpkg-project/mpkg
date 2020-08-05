#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
import re
import shutil
from functools import lru_cache
from pathlib import Path

import click
import requests

from .config import HOME, GetConfig, SetConfig

_ = gettext.gettext
proxy = GetConfig('proxy')
proxies = {'http': proxy, 'https': proxy} if proxy else {}


def Redirect(url: str) -> str:
    rules = GetConfig('redirect')
    if rules:
        for rule in rules:
            for pattern, to in rule.items():
                m = re.match(pattern, url)
                if m:
                    return to.format(*m.groups())
    return url


@lru_cache()
def GetPage(url: str, warn=True, UA='', timeout=0) -> str:
    url = Redirect(url)
    if not timeout:
        timeout = 3
        if GetConfig('timeout'):
            timeout = float(GetConfig('timeout'))
    if GetConfig('debug') == 'yes':
        print(f'debug: requesting {url}')
    if UA:
        res = requests.get(
            url, headers={'User-Agent': UA}, timeout=timeout, proxies=proxies)
    else:
        res = requests.get(url, timeout=timeout, proxies=proxies)
    if warn and res.status_code != 200:
        print(f'warning: {url} {res.status_code} error')
        return 'error'
    return res.text


def Download(url: str, directory='', filename='', output=True):
    if not url.startswith('http'):
        return Path(url)
    url = Redirect(url)
    if not directory:
        directory = GetConfig('download_dir')
    directory = Path(directory)
    if not directory.exists():
        directory.mkdir(parents=True)
    if not filename:
        filename = url.split('/')[-1]
    file = directory / filename
    cached = file.parent / (file.name+'.cached')
    if GetConfig('download_cache') == 'yes' and cached.exists():
        return file
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
        req = requests.get(url, stream=True, proxies=proxies)
        if req.status_code != 200:
            print(f'warning: {req.status_code} error')
            print(' try to download it with downloader')
            print('  if you have installed wget')
            print(r'  try: mpkg set downloader "wget -q -O {filepath} {url}"')
        chunk_size = 4096
        contents = req.iter_content(chunk_size=chunk_size)
        if 'content-length' in req.headers:
            length = int(req.headers['content-length'])/chunk_size
        else:
            print('warning: unknown content-length')
            length = 0
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


def PreInstall():
    SetConfig('download_dir', str(HOME), replace=False)
    SetConfig('bin_dir', str(HOME / 'bin'), replace=False)
    SetConfig('files_dir', str(HOME / 'files'), replace=False)
    SetConfig(
        '7z', r'"C:\Program Files\7-Zip\7z.exe" x {filepath} -o{root} -aoa > nul', replace=False)
    for folder in ['py', 'json', 'zip', 'bin', 'files']:
        directory = HOME / folder
        if not directory.exists():
            directory.mkdir(parents=True)


def DownloadApps(apps):
    for app in apps:
        app.download_prepare()
    for app in apps:
        app.download()


def ReplaceDir(root_src_dir, root_dst_dir):
    # https://stackoverflow.com/q/7420617
    for src_dir, _, files in os.walk(root_src_dir):
        dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for file_ in files:
            src_file = os.path.join(src_dir, file_)
            dst_file = os.path.join(dst_dir, file_)
            if os.path.exists(dst_file):
                os.remove(dst_file)
            shutil.move(src_file, dst_dir)
    if Path(root_src_dir).exists():
        shutil.rmtree(root_src_dir)


def Extract(filepath, root='', ver=''):
    filepath = Path(filepath)
    if not root:
        root = filepath.parent.absolute() / '.'.join(
            filepath.name.split('.')[:-1])
    ver = '-' + ver if ver else ''
    root = Path(str(root)+ver)
    extract_dir = root.parent/'mpkg-temp-dir'
    cmd = GetConfig('7z').format(filepath=str(filepath), root=extract_dir)
    print(_('extracting {filepath} to {root}').format(
        filepath=filepath, root=root))
    os.system(cmd)
    files, root_new = os.listdir(extract_dir), extract_dir
    while len(files) == 1:
        root_new = root_new/files[0]
        if root_new.is_dir():
            files = os.listdir(root_new)
        else:
            root_new = root_new.parent
            break
    ReplaceDir(str(root_new.absolute()), str(root.absolute()))
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    return root


def Search(url='', regex='', links='{ver}', ver='', reverse=False):
    if not ver:
        page = GetPage(url)
        i = -1 if reverse else 0
        ver = re.findall(regex, page)[i]
    if isinstance(links, dict):
        result = {}
        for key, value in links.items():
            result[key] = value.format(ver=ver)
        return result
    elif isinstance(links, list):
        result = []
        for item in links:
            result.append(item.format(ver=ver))
        return result
    else:
        return links.format(ver=ver)
