#!/usr/bin/env python3
# coding: utf-8

import gettext
import hashlib
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote

import click
import requests
from loguru import logger
from tenacity import RetryCallState, Retrying, stop_after_attempt, wait_fixed

from .config import HOME, GetConfig, SetConfig

_ = gettext.gettext
proxy = GetConfig('proxy')
proxies = {'http': proxy, 'https': proxy} if proxy else {}

logger.remove()
level = 'DEBUG' if GetConfig('debug') == 'yes' else 'INFO'
logger.add(sys.stderr, colorize=True,
           format='<level>{level: <8}</level> | <cyan>{function}</cyan> - <level>{message}</level>', level=level)

DefaultUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101'
UA = GetConfig('UA', default=DefaultUA)

timeout = float(GetConfig('timeout', default='5'))
retry_attempts = int(GetConfig('retry_attempts', default='3'))


def retry(func_name='', attempts=retry_attempts):
    def after_log(func_name):
        def retry_log(retry_state: RetryCallState):
            fnname = func_name if func_name else retry_state.fn.__name__
            if retry_state.outcome.failed:
                logger.info(
                    f"Finished call to '{fnname}' (try: {retry_state.attempt_number}), {retry_state.outcome.exception()}")
        return retry_log
    return Retrying(after=after_log(func_name), stop=stop_after_attempt(attempts),
                    wait=wait_fixed(3)).wraps


def get_valid_name(text):
    # see also: https://stackoverflow.com/a/295146
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    result = ''
    for c in text:
        if not c.isascii() or c in valid_chars:
            result += c
        else:
            result += '_'
    return result


def Hash(filepath, algo='sha256'):
    if algo in hashlib.algorithms_available:
        h = eval(f'hashlib.{algo}()')
    blocksize = 2**20
    with open(filepath, 'rb') as f:
        data = f.read(blocksize)
        while data:
            h.update(data)
            data = f.read(blocksize)
        return h.hexdigest()


def Redirect(url: str) -> str:
    rules = GetConfig('redirect')
    if rules:
        for rule in rules:
            for pattern, to in rule.items():
                m = re.match(pattern, url)
                if m:
                    return to.format(*m.groups())
    return url


@retry('GetPage')
@lru_cache()
def GetPage(url: str, warn=True, UA=UA, timeout=timeout, redirect=True) -> str:
    url = Redirect(url) if redirect else url
    logger.debug(f'requesting {url}')
    res = requests.get(
        url, headers={'User-Agent': UA}, timeout=timeout, proxies=proxies)
    if warn and res.status_code != 200:
        logger.warning(f'{url} {res.status_code} error')
        return 'error'
    return res.text


@retry('MGet')
def MGet(url: str, redirect=True, **kwargs):
    url = Redirect(url) if redirect else url
    logger.debug(f'requesting {url}')
    if 'headers' not in kwargs:
        kwargs['headers'] = {'User-Agent': UA}
    elif not kwargs['headers'].get('User-Agent'):
        kwargs['headers']['User-Agent'] = UA
    if 'timeout' not in kwargs:
        kwargs['timeout'] = timeout
    if 'proxies' not in kwargs:
        kwargs['proxies'] = proxies
    valid_status = [200]
    if kwargs.get('allow_redirects') == False:
        valid_status += list(range(300, 400))
    res = requests.get(url, **kwargs)
    if res.status_code not in valid_status:
        logger.warning(f'{url} returned {res.status_code}')
    return res


@retry()
def Download(url: str, directory='', filename='', output=True, UA=UA, sha256='', redirect=True, timeout=timeout):
    UA = 'Wget/1.20.3 (mingw32)' if UA == DefaultUA else UA
    resume = True if GetConfig('download_resuming') == 'yes' else False
    if not url.startswith('http'):
        return Path(url)
    if redirect:
        url = Redirect(url)
    if not directory:
        directory = GetConfig('download_dir')
    if not filename:
        filename = url.split('/')[-1]
    filename = get_valid_name(unquote(filename))
    for rule in GetConfig('saveto', default=[]):
        ext, dir_ = list(rule.items())[0]
        if filename.endswith(ext):
            if directory == GetConfig('download_dir'):
                dir_ = 'TEMPDIR' if dir_ == 'TEMPDIR-D' else dir_
                directory = dir_ if dir_ != 'TEMPDIR' else tempfile.mkdtemp()
    directory = Path(directory)
    if not directory.exists():
        directory.mkdir(parents=True)
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
        headers = {'User-Agent': UA}
        fmode = 'wb'
        file_size = 0
        unfinished = file.parent / (file.name+'.unfinished')
        if resume and unfinished.exists() and file.exists():
            fmode = 'ab'
            file_size = file.stat().st_size
            logger.debug(f'resuming from {file_size}')
            headers['Range'] = f'bytes={file_size}-'
        req = requests.get(url, stream=True, proxies=proxies,
                           headers=headers, timeout=timeout)
        chunk_size = 2**20
        contents = req.iter_content(chunk_size=chunk_size)
        if 'content-length' in req.headers:
            length = int(req.headers['content-length'])/chunk_size
            resume_gt = float(GetConfig('resume_gt', default='20'))
            if resume and length > resume_gt and not unfinished.exists():
                logger.debug('enable resuming')
                unfinished.touch()
        else:
            logger.debug('unknown content-length')
            length = 0
        if not length < 1:
            if length > 1024:
                label = str(round(length/1024, 1))+'GB'
            else:
                label = str(round(length, 1))+'MB'
        else:
            label = ''
        if not req.status_code in [200, 206]:
            if req.status_code == 416:
                logger.debug(
                    f"content-length: {req.headers['content-length']}")
                req2 = requests.get(url, stream=True, proxies=proxies,
                                    headers={'User-Agent': UA}, timeout=timeout)
                if int(req2.headers['content-length']) == file_size:
                    logger.info(
                        "The file is already fully retrieved. If there isn't any hash mistake, delete the unfinished flag file (example.exe.unfinished) manually.")
                else:
                    logger.warning(
                        '416 error, try to delete the unfinished file')
            else:
                logger.warning(f'{req.status_code} error')
                print('\n Try to download it with downloader:')
                print('  if you have installed wget,')
                print(
                    r'  try: mpkg set downloader "wget -q -O {filepath} {url}"')
                print(
                    '\n If you have enabled resuming, try to delete the unfinished file')
        else:
            with click.progressbar(contents, length=length, label=label) as bar:
                with open(str(file), fmode) as f:
                    for chunk in bar:
                        if chunk:
                            f.write(chunk)
            if unfinished.exists():
                unfinished.unlink()
    if not file.is_file():
        logger.warning(f'no {file}({command})')
    if sha256:
        sha256 = sha256.lower()
        algo, sha256 = sha256.split(
            ':') if ':' in sha256 else ('sha256', sha256)
        print(_('checking {hash}').format(hash=algo))
        if sha256 != Hash(file, algo):
            logger.warning(f'wrong {algo}')
            exit(1)
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
        soft['name'] = soft['name'].lower()
        names.append(soft['name'])
    if len(names) != len(set(names)):
        logger.warning(
            f'name conflict\n{[n for n in names if names.count(n)!=1]}')


def test_cmd(cmd):
    return subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)


def Get7zPath():
    for path in [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]:
        if Path(path).exists():
            return path
    return '7z' if test_cmd('7z') == 0 else '7z_not_found'


def PreInstall():
    SetConfig('download_dir', str(HOME / 'Downloads'), replace=False)
    SetConfig('bin_dir', str(HOME / 'bin'), replace=False)
    SetConfig('files_dir', str(HOME / 'files'), replace=False)
    SetConfig('7z', f'"{Get7zPath()}"' +
              r' x {filepath} -o{root} -aoa > '+os.devnull, replace=False)
    for folder in ['py', 'json', 'zip', 'bin', 'files']:
        directory = HOME / folder
        if not directory.exists():
            directory.mkdir(parents=True)


def DownloadApps(apps, root=None):
    for app in apps:
        app.download_prepare()
    for app in apps:
        app.download(root)


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


def Extract(filepath, root='', ver='', delete=False):
    filepath = Path(filepath)
    if not root:
        root = filepath.parent.absolute() / '.'.join(
            filepath.name.split('.')[:-1])
    ver = '_' + ver if ver else ''
    root = Path(str(root)+ver)
    extract_dir = root.parent/'mpkg-temp-dir'
    cmd = GetConfig('7z').format(filepath=str(filepath), root=extract_dir)
    print(_('extracting {filepath} to {root}').format(
        filepath=filepath, root=root))
    os.system(cmd)
    files = os.listdir(extract_dir)
    if len(files) == 1 and files[0].endswith('.tar'):
        Extract((extract_dir/files[0]), delete=True)
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
    if delete:
        logger.debug(f'unlink {filepath}')
        filepath.unlink()
    return root


def Search(url='', regex='', links='{ver}', ver='', sort=False, reverse=False, UA=UA, sumurl='', findall=False, redirect=True):
    if sumurl:
        return SearchSum(url, sumurl, UA, redirect=redirect)
    if not ver:
        page = GetPage(url, UA=UA, redirect=redirect)
        i = -1 if reverse else 0
        result = re.findall(regex, page)
        if sort:
            result = sorted(result)
        if findall:
            return result
        ver = result[i]
    if isinstance(links, dict):
        return dict([(k, v.format(ver=ver)) for k, v in links.items()])
    elif isinstance(links, list):
        return [item.format(ver=ver) for item in links]
    else:
        return links.format(ver=ver)


def SearchSum(links, sumurl, UA=UA, redirect=True):
    page = GetPage(sumurl, UA=UA, redirect=redirect)

    def search(url):
        name = unquote(url.split('/')[-1])
        return re.search('(\\w+)\\s+\\*?'+name, page).groups()[0]

    if isinstance(links, dict):
        return dict([(k, search(v)) for k, v in links.items()])
    elif isinstance(links, list):
        return [search(item) for item in links]
    else:
        return search(links)
