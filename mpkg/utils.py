#!/usr/bin/env python3
# coding: utf-8

import gettext
import importlib
import os
from pathlib import Path

import requests

from .config import HOME, GetConfig

_ = gettext.gettext

downloader = GetConfig('downloader')


def GetPage(url: str, **kwargs) -> str:
    return requests.get(url, **kwargs).text


def Download(url: str, directory=HOME, filename=False):
    directory = Path(directory)
    if not filename:
        filename = url.split('/')[-1]
    os.system(downloader.format(
        url=url, directory=directory, filename=filename))
    file = directory / filename
    if not file.is_file():
        print(f'warning: no {file}')
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


def IsLatest(bydate=False):
    pass


def Sync(url):
    pass


def LoadFile(path):
    spec = importlib.util.spec_from_file_location('Package', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Package()


def Load(source: str, installed=True):
    # zip/json/py
    if source.endswith('.py'):
        if source.startswith('http'):
            pass
        else:
            pkg = LoadFile(source)
            if pkg.needConfig and not installed:
                pkg.config()
            return pkg
