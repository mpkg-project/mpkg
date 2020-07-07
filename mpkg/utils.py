#!/usr/bin/env python3
# coding: utf-8

import gettext
import importlib
import os
from pathlib import Path

import requests

from .config import HOME, GetConfig, SetConfig

_ = gettext.gettext

downloader = GetConfig('downloader')


def GetPage(url: str, **kwargs) -> str:
    return requests.get(url, **kwargs).text


def Download(url: str, directory=HOME, filename=False):
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


def IsLatest(bydate=False):
    pass


def LoadFile(path):
    spec = importlib.util.spec_from_file_location('Package', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Package()


def Load(source: str, installed=True, sync=True):
    # json/py
    if not installed:
        sync = True
    if source.endswith('.py'):
        if source.startswith('http'):
            name = source.split('/')[-1]
            abspath = HOME / 'py'
            file = HOME / 'py' / name
            if sync:
                ver = int(GetPage(source + '.ver').replace(' ', ''))
                ver_ = GetConfig(name, filename=name +
                                 '.ver.json', abspath=abspath)
                ver_ = -1 if not ver_ else int(ver_)
                if ver > ver_:
                    Download(source, directory=HOME / 'py', filename=name)
                    SetConfig(name, ver, filename=name +
                              '.ver.json', abspath=abspath)
        else:
            file = source
        pkg = LoadFile(file)
        if pkg.isMultiple:
            if not installed:
                i = int(
                    input(_('\ninput the number of profiles for {pkgname}: ').format(pkgname=pkg.id)))
                pkg.setconfig('i', i)
            pkgs = []
            for i in range(pkg.getconfig('i')):
                newpkg = LoadFile(file)
                newpkg.cfg += f'.{i}'
                newpkg.__init__()
                pkgs.append(newpkg)
        else:
            pkgs = [pkg]
        if pkg.needConfig and not installed:
            [pkg.config() for pkg in pkgs]
        return pkgs
