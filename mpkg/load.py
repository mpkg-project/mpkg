#!/usr/bin/env python3
# coding: utf-8

import gettext
import importlib
import json

from .config import HOME, GetConfig, SetConfig
from .utils import Download, GetPage

_ = gettext.gettext


def LoadFile(path: str):
    spec = importlib.util.spec_from_file_location('Package', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Package()


def Configurate(path: str):
    pkg = LoadFile(path)
    if pkg.isMultiple:
        i = int(
            input(_('\ninput the number of profiles for {pkgname}: ').format(pkgname=pkg.id)))
        pkg.setconfig('i', i)
        for i in range(i):
            newpkg = LoadFile(path)
            newpkg.cfg += f'.{i}'
            newpkg.config()
    else:
        pkg.config()


def Save(source: str, sync=True):

    def download(url, filetype, sync=True):
        filename = url.split('/')[-1]
        abspath = HOME / filetype
        filepath = HOME / filetype / filename
        if sync:
            res = GetPage(url + '.ver', warn=False).replace(' ', '')
            ver = -1 if not res.isnumeric() else int(res)
            ver_ = GetConfig(filename, filename=filename +
                             '.ver.json', abspath=abspath)
            ver_ = -1 if not ver_ else int(ver_)
            if ver == -1 or ver > ver_:
                Download(url, directory=abspath, filename=filename)
                SetConfig(filename, ver, filename=filename +
                          '.ver.json', abspath=abspath)
        return filepath

    if source.startswith('http'):
        if source.endswith('.py'):
            filepath = download(source, 'py', sync)
        elif source.endswith('.json'):
            filepath = download(source, 'json', sync)
    else:
        filepath = source
    return filepath


def Load(source: str, installed=True, sync=True):
    if not installed:
        sync = True
    if source.endswith('.py'):
        filepath = Save(source, sync)
        pkg = LoadFile(filepath)
        if pkg.needConfig and not installed:
            Configurate(filepath)
        if pkg.isMultiple:
            pkgs = []
            for i in range(pkg.getconfig('i')):
                newpkg = LoadFile(filepath)
                newpkg.cfg += f'.{i}'
                newpkg.__init__()
                pkgs.append(newpkg)
        else:
            pkgs = [pkg]
        return pkgs
    elif source.endswith('.json'):
        filepath = Save(source, sync)
        with open(filepath, 'r', encoding="utf8") as f:
            return json.load(f)['packages']
    elif source.endswith('.sources'):
        pass
