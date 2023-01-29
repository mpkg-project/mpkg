#!/usr/bin/env python3
# coding: utf-8

import gettext
import importlib
import json
import os
import re
import tempfile
import time
import traceback
from multiprocessing.dummy import Pool
from pathlib import Path
from random import random
from shutil import rmtree
from zipfile import ZipFile

import yaml

from .config import HOME, GetConfig, SetConfig
from .utils import Download, GetPage, Name, ReplaceDir, logger

_ = gettext.gettext


def LoadFile(path: str):
    spec = importlib.util.spec_from_file_location('Package', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Package()


def Configure(path: str):
    pkg = LoadFile(path)
    if pkg.isMultiple:
        i = pkg.getconfig('i')
        if i:
            print(f'old profile count: {i}')
            for i in range(i):
                newpkg = LoadFile(path)
                newpkg.cfg += f'.{i}'
                print(newpkg.cfg2json())
        i = int(
            input(_('\ninput the number of profiles for {pkgname}: ').format(pkgname=pkg.ID)))
        pkg.setconfig('i', i)
        for i in range(i):
            newpkg = LoadFile(path)
            newpkg.cfg += f'.{i}'
            newpkg.config()
    else:
        pkg.config()


def Save(source: str, ver=-1, sync=True, check_ver=True, temporary=False):
    latest = False  # old source is not latest
    name = ''
    if '->' in source:
        source, name = source.split('->')

    def download(url, name, verattr, filetype, sync, check_ver, temporary):
        latest = False
        if temporary:
            check_ver = False
        filename = url.split('/')[-1] if not name else name
        home = Path(tempfile.mkdtemp()) if temporary else HOME
        abspath = home / filetype
        filepath = home / filetype / filename
        if sync:
            if not check_ver:
                Download(url, directory=abspath, filename=filename)
                return filepath, latest
            if verattr == -1:
                res = GetPage(
                    url + '.ver', warn=False).replace(' ', '').strip()
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
                source, name, ver, 'py', sync, check_ver, temporary)
        elif source.endswith('.json'):
            filepath, latest = download(
                source, name, ver, 'json', sync, check_ver, temporary)
        elif source.endswith('.yaml'):
            filepath, latest = download(
                source, name, ver, 'yaml', sync, check_ver, temporary)
        elif source.endswith('.zip'):
            filepath, latest = download(
                source, name, ver, 'zip', sync, check_ver, temporary)
    else:
        filepath = source
    return filepath, latest


def LoadZip(filepath, latest=False, installed=True):
    filepath = Path(filepath)
    dir = filepath.parent / filepath.name[:-4]
    pkgdir = dir / 'packages'
    if not latest:
        if pkgdir.exists():
            rmtree(pkgdir)
        with ZipFile(filepath, 'r') as myzip:
            files = [name for name in myzip.namelist() if 'packages/' in name]
            myzip.extractall(path=str(dir), members=files)
        ReplaceDir(str(dir / files[0]), str(pkgdir))
    files = [str((pkgdir/file).absolute()) for file in os.listdir(pkgdir)
             if file.endswith('.py') or file.endswith('.json') or file.endswith('.yaml')]
    return [Load(file, installed=installed) for file in files]


def Load(source: str, ver=-1, installed=True, sync=True, jobs=10, check_ver=True, temporary=False):
    logger.debug(f'loading {source}')
    if not GetConfig('unsafe') == 'yes' and not source.split('.')[-1] in ['latest', 'nightly', 'json']:
        logger.warning('skip unsafe source')
        return [], '.json'
    if not installed:
        sync = True
    if source.endswith('.py'):
        filepath = Save(source, ver, sync, check_ver, temporary)[0]
        pkg = LoadFile(filepath)
        if pkg.needConfig and not installed:
            Configure(filepath)
        if pkg.isMultiple:
            pkgs = []
            if not pkg.getconfig('i'):
                return [pkg], '.py'
            for i in range(pkg.getconfig('i')):
                newpkg = LoadFile(filepath)
                newpkg.cfg += f'.{i}'
                newpkg.__init__()
                pkgs.append(newpkg)
        else:
            pkgs = [pkg]
        return pkgs, '.py'
    elif source.endswith('.json'):
        filepath = Save(source, ver, sync, check_ver, temporary)[0]
        with open(filepath, 'r', encoding="utf8") as f:
            return json.load(f)['packages'], '.json'
    elif source.endswith('.yaml'):
        filepath = Save(source, ver, sync, check_ver, temporary)[0]
        with open(filepath, 'r', encoding="utf8") as f:
            return yaml.safe_load(f.read())['packages'], '.json'
    elif source.endswith('.zip'):
        filepath, latest = Save(source, ver, sync, check_ver, temporary)
        return LoadZip(filepath, latest, installed), '.zip'
    elif source.endswith('.sources'):
        if source.startswith('http'):
            sources = json.loads(GetPage(source))
        else:
            with open(source, 'r', encoding="utf8") as f:
                sources = json.load(f)
        parser = [key for key, value in sources.items() if value == 'parser']
        for url in parser:
            del sources[url]
            Load(url, installed=installed, sync=sync)
        with Pool(jobs) as p:
            score = [x for x in p.map(lambda x: Load(
                x[0], x[1], installed, sync), sources.items()) if x]
        return score, '.sources'
    elif source.endswith('.latest'):
        time.sleep(round(random(), 2))
        return Load(source[:-7], ver, installed, sync, jobs, False)
    elif source.endswith('.nightly'):
        time.sleep(round(random(), 2))
        return Load(source[:-8], int(time.strftime('%y%m%d')), installed, sync, jobs)


def HasConflict(softs, pkgs) -> list:
    ids = []
    for item in pkgs:
        if item.isMultiple and item.ID in ids:
            pass
        else:
            ids.append(item.ID)
    [ids.append(item['id']) for item in softs]
    return [id for id in ids if ids.count(id) > 1]


def Sorted(items):
    softs, pkgs, sources = [], [], []
    a, b, c, d = [], [], [], []
    for x, ext in items:
        if ext == '.json':
            a.append(x)
        elif ext == '.py':
            b.append(x)
        elif ext == '.sources':
            c.append(x)
        elif ext == '.zip':
            d.append(x)
    # a=[[soft1, soft2]]
    # b=[[pkg1, pkg2]]
    # c=[[(x1,ext),(x2,ext)]], x1=a/b/d[0]
    # d=[[(x1,ext),(x2,ext)]], x1=a/b[0]
    for L in c:
        sources += L
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
    for softlist in a:
        softs += softlist
    for pkglist in b:
        pkgs += pkglist
    pkgs = [pkg for pkg in pkgs if pkg.ID]
    softs = [soft for soft in softs if soft.get('id')]
    return softs, pkgs


def ConfigSoft(soft):
    with Pool(10) as p:
        items = [x for x in p.map(Load, GetConfig('sources')) if x]
    pkgs = Sorted(items)[1]
    pkg = [pkg for pkg in pkgs if pkg.name == soft['name']]
    if pkg:
        pkg[0].config()


def Prepare(pkg):
    try:
        pkg.prepare()
        if not hasattr(pkg, 'json_data') or 'packages' not in pkg.json_data:
            logger.warning(f'no data for {pkg.ID}')
            return pkg
    except Exception as err:
        logger.error(f'{pkg.ID}: {err}')
        logger.debug(traceback.print_exc())
        return pkg


def GetSofts(jobs=10, sync=True, use_cache=True, ignore_cache=False) -> list:
    softs_ = GetConfig('softs', filename='softs.json')
    if softs_ and use_cache:
        return softs_
    if not GetConfig('sources'):
        return []

    with Pool(jobs) as p:
        items = [x for x in p.map(lambda x:Load(
            x, sync=sync, jobs=jobs, check_ver=not ignore_cache), GetConfig('sources')) if x]
    softs, pkgs = Sorted(items)

    score = HasConflict(softs, pkgs)
    if score:
        logger.warning(f'id conflict: {set(score)}')

    with Pool(jobs) as p:
        err = [result for result in p.map(Prepare, pkgs) if result]
    for soft in [pkg.json_data['packages'] for pkg in pkgs if pkg not in err]:
        softs += soft

    Name(softs)
    names = [soft['name'] for soft in softs]
    for name, new in GetConfig(filename='name.json', default={}).items():
        if new not in names and name in names:
            softs[names.index(name)]['name'] = new
    if not softs == softs_:
        SetConfig('softs', softs, filename='softs.json')

    return softs


def GetOutdated():
    installed = GetConfig(filename='installed.json')
    installed = installed if installed else {}
    latest = {}
    for soft in GetSofts():
        ver = soft.get('ver')
        if ver:
            latest[soft['name']] = [ver, soft.get('date')]
        else:
            logger.warning(f'no ver for {soft["name"]}')
    outdated = {}
    for name, value in installed.items():
        if not name in latest:
            logger.warning(f'cannot find {name}')
            continue
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


def Names2Softs(names: list, softs=None):
    names = [name.lower() for name in names]
    patterns = [re.compile('^{0}$'.format(name.replace('*', '.*')))
                for name in names if '*' in name]

    def match(name):
        for p in patterns:
            if p.match(name):
                return True
        if name in names:
            return True

    if not softs:
        softs = GetSofts()
    return [soft for soft in softs if match(soft['name'].lower())]
