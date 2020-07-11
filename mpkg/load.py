#!/usr/bin/env python3
# coding: utf-8

import gettext
import importlib
import json
import os
from multiprocessing.dummy import Pool
from pathlib import Path
from zipfile import ZipFile

from .config import HOME, GetConfig, SetConfig
from .utils import Download, GetPage, Name

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


def Save(source: str, ver=-1, sync=True, check_ver=True):
    latest = False  # old source is not latest
    name = ''
    if '->' in source:
        source, name = source.split('->')

    def download(url, name, verattr, filetype, sync, check_ver):
        latest = False
        filename = url.split('/')[-1] if not name else name
        abspath = HOME / filetype
        filepath = HOME / filetype / filename
        if sync:
            if not check_ver:
                Download(url, directory=abspath, filename=filename)
                return filepath, latest
            if verattr == -1:
                res = GetPage(url + '.ver', warn=False).replace(' ', '')
                ver = -1 if not res.isnumeric() else int(res)
            else:
                ver = verattr
            ver_ = GetConfig(filename, filename=filename +
                             '.ver.json', abspath=abspath)
            ver_ = -1 if not ver_ else int(ver_)
            if ver == -1 or ver > ver_:
                Download(url, directory=abspath, filename=filename)
                SetConfig(filename, ver, filename=filename +
                          '.ver.json', abspath=abspath)
            else:
                latest = True
        return filepath, latest

    if source.startswith('http'):
        if source.endswith('.py'):
            filepath, latest = download(
                source, name, ver, 'py', sync, check_ver)
        elif source.endswith('.json'):
            filepath, latest = download(
                source, name, ver, 'json', sync, check_ver)
        elif source.endswith('.zip'):
            filepath, latest = download(
                source, name, ver, 'zip', sync, check_ver)
    else:
        filepath = source
    return filepath, latest


def LoadZip(filepath, latest=False, installed=True):
    filepath = Path(filepath)
    dir = filepath.parent / filepath.name[:-4]
    pkgdir = dir / 'packages'
    if not latest:
        with ZipFile(filepath, 'r') as myzip:
            files = [name for name in myzip.namelist() if 'packages/' in name]
            myzip.extractall(path=str(dir), members=files)
        if not pkgdir.exists():
            (dir / files[0]).rename(str(pkgdir))
    files = [str((pkgdir/file).absolute()) for file in os.listdir(pkgdir)
             if file.endswith('.py') or file.endswith('.json')]
    return [Load(file, installed=installed) for file in files]


def Load(source: str, ver=-1, installed=True, sync=True):
    if not installed:
        sync = True
    if source.endswith('.py'):
        filepath = Save(source, ver, sync)[0]
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
        return pkgs, '.py'
    elif source.endswith('.json'):
        filepath = Save(source, ver, sync)[0]
        with open(filepath, 'r', encoding="utf8") as f:
            return json.load(f)['packages'], '.json'
    elif source.endswith('.zip'):
        filepath, latest = Save(source, ver, sync)
        return LoadZip(filepath, latest, installed), '.zip'
    elif source.endswith('.sources') and source.startswith('http'):
        sources = json.loads(GetPage(source))
        with Pool(10) as p:
            score = [x for x in p.map(lambda x: Load(
                x[0], x[1], installed, sync), sources.items()) if x]
        return score, '.sources'


def HasConflict(softs, pkgs) -> list:
    ids = []
    for item in pkgs:
        if item.isMultiple and item.id in ids:
            pass
        else:
            ids.append(item.id)
    [ids.append(item['id']) for item in softs]
    return [id for id in ids if ids.count(id) > 1]


def Sorted(items):
    softs, pkgs, sources = [], [], []
    a = [x for x, ext in items if ext == '.json']
    b = [x for x, ext in items if ext == '.py']
    c = [x for x, ext in items if ext == '.sources']
    d = [x for x, ext in items if ext == '.zip']
    # a=[[soft1, soft2]]
    # b=[[pkg1, pkg2]]
    # c=[[(x1,ext),(x2,ext)]], x1=a/b/d[0]
    # d=[[(x1,ext),(x2,ext)]], x1=a/b[0]
    for x in c:
        sources += x
    for x, ext in sources:
        if ext == '.json':
            a.append(x)
        elif ext == '.py':
            b.append(x)
        elif ext == '.zip':
            d.append(x)
    for x in d:
        for y, ext in x:
            if ext == '.json':
                a.append(y)
            elif ext == '.py':
                b.append(y)
    for soft in a:
        softs += soft
    for pkg in b:
        pkgs += pkg
    pkgs = [pkg for pkg in pkgs if pkg.id]
    return softs, pkgs


def GetSofts(jobs=10, sync=True, use_cache=True) -> list:
    softs_ = GetConfig('softs', filename='softs.json')
    if softs_ and use_cache:
        return softs_

    with Pool(jobs) as p:
        items = [x for x in p.map(lambda x:Load(
            x, sync=sync), GetConfig('sources')) if x]
    softs, pkgs = Sorted(items)

    score = HasConflict(softs, pkgs)
    if score:
        print(f'warning(id conflict): {set(score)}')

    with Pool(jobs) as p:
        p.map(lambda x: x.prepare(), pkgs)
    for soft in [pkg.data['packages'] for pkg in pkgs]:
        softs += soft

    if not softs == softs_:
        SetConfig('softs', softs, filename='softs.json')

    Name(softs)
    return softs
