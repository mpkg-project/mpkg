#!/usr/bin/env python3
# coding: utf-8

import gettext
import importlib
import json
import os
from pathlib import Path

import requests

p = Path.home() / '.config/mpkg'
fn = 'config.json'

if not p.exists():
    p.mkdir(parents=True)

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


def SetConfig(key: str, value=True, path='', filename=fn):
    path_ = p / path
    file = p / path / filename
    if not path_.exists():
        path_.mkdir(parents=True)
    if not file.exists():
        with file.open('w') as f:
            f.write('{}')
    with file.open('r') as f:
        data = json.loads(f.read())
    data[key] = value
    with file.open('w') as f:
        f.write(json.dumps(data))


def GetConfig(key: str, path='', filename=fn):
    file = p / path / filename
    if not file.exists():
        return
    with file.open('r') as f:
        data = json.loads(f.read())
    return data.get(key)


def Load(file):
    spec = importlib.util.spec_from_file_location('Package', file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Package()


def IsLatest(bydate=False):
    pass
