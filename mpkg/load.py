#!/usr/bin/env python3
# coding: utf-8

import gettext
import importlib

from .config import HOME, GetConfig, SetConfig
from .utils import Download, GetPage

_ = gettext.gettext


def LoadFile(path):
    spec = importlib.util.spec_from_file_location('Package', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Package()


def Configurate(path):
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


def Load(source: str, installed=True, sync=True):
    # json/py
    if not installed:
        sync = True
    if source.endswith('.py'):
        if source.startswith('http'):
            name = source.split('/')[-1]
            abspath = HOME / 'py'
            filepath = HOME / 'py' / name
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
            filepath = source
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
