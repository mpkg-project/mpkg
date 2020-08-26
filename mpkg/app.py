#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
import shutil
from pathlib import Path
from platform import architecture

import click

from .common import soft_data
from .config import GetConfig, SetConfig
from .load import GetSofts
from .utils import Download, Extract, Selected, logger

_ = gettext.gettext
ARCH = architecture()[0]


def Linking(name, value='', delete=False):
    bin_dir = Path(GetConfig('bin_dir'))
    if os.name == 'nt':
        batfile = bin_dir / (name+'.bat')
        if delete:
            if batfile.exists():
                batfile.unlink()
            return
        elif not value:
            return
        print(_('linking {0} => {1}').format(value, name))
        os.system('echo @echo off>{0}'.format(batfile))
        os.system('echo {0} %*>>{1}'.format(value, batfile))


def ToLink(links: list):
    if not links:
        return {}
    elif len(links) > 1:
        link = Selected(links, msg=_('select a link to download:'))[0]
        return {ARCH: link}
    else:
        return {ARCH: links[0]}


def Execute(string):
    if not string:
        return
    if not GetConfig('allow_cmd') == 'yes':
        print(f'skip command({string})')
        return
    for cmd in string.strip().split('\n'):
        print(f'executing {cmd}')
        if GetConfig('no_confirmation') == 'yes' or click.confirm(' confirmed ?'):
            code = os.system(cmd)
            if code:
                logger.warning(f'returned {code}')


def InstallPortable(filepath, soft, delete):
    if delete:
        old = Path(GetConfig(soft['name'], filename='root_installed.json'))
        if old.exists():
            shutil.rmtree(old)
    root = GetConfig(soft['name'], filename='root.json',
                     default='').format(ver=soft['ver'])
    if not root:
        name = soft['name']
        root = Path(GetConfig('files_dir')) / name
    if 'MPKG-PORTABLE-EXE' in soft['bin']:
        soft['bin'].remove('MPKG-PORTABLE-EXE')
        if not root.exists():
            root.mkdir()
        filepath = shutil.move(filepath, root/filepath.name)
    else:
        root = Extract(filepath, root)
    SetConfig(soft['name'], str(root), filename='root_installed.json')
    if isinstance(soft['bin'], dict):
        soft['bin'] = soft['bin'][ARCH]
    for file in [file for file in soft['bin'] if file != 'MPKG-PORTABLE']:
        if isinstance(file, list):
            args = ' ' + file[2] if len(file) == 3 else ''
            file, alias = file[0], file[1]
        else:
            args, alias = '', ''
        if file.startswith('MPKGLNK|'):
            strlist = file[8:].split('|')
            if len(strlist) == 2:
                strlist.append('')
            target = root / strlist[1]
            args = '|'.join(strlist[2:])
            args = ' '+args if args else ''
            cmd = GetConfig('shortcut_command')
            if cmd and target.is_file():
                name = strlist[0] if strlist[0] else target.name.split('.')[0]
                os.system(cmd.format(
                    name=name, target=target.absolute(), root=target.parent.absolute(), args=args))
            else:
                logger.warning(f'no shortcut for {target.absolute()}')
            continue
        binfile = root / file
        if binfile.is_file():
            cmd = GetConfig('link_command')
            if not cmd:
                name = alias if alias else binfile.name.split('.')[0]
                value = str(binfile)+args if args else binfile
                Linking(name, value)
            else:
                os.system(cmd.format(name=name, binfile=binfile))
    return root


class App(object):
    def __init__(self, data):
        if not data.get('name'):
            data['name'] = data['id']
        self.apps = [App(soft) for soft in GetSofts()
                     if soft['id'] in data['depends']] if data.get('depends') else []
        self.data = soft_data(**data)

    def dry_run(self):
        SetConfig(self.data.name, [self.data.ver,
                                   self.data.date], filename='installed.json')

    def download_prepare(self):
        if not self.data.arch:
            self.data.arch = ToLink(self.data.links)

    def download(self):
        self.download_prepare()
        data = self.data
        if self.apps:
            for app in self.apps:
                app.download()
        if not ARCH in data.arch:
            if not self.apps:
                logger.warning(f'{data.name} has no link available')
            file = ''
        else:
            if isinstance(data.sha256, list):
                i = data.links.index(data.arch[ARCH])
                data.sha256 = {ARCH: data.sha256[i]}
            sha256 = data.sha256.get(ARCH) if data.sha256 else ''
            filename = data.name+'_'+data.arch[ARCH].split('/')[-1]
            file = Download(data.arch[ARCH], sha256=sha256, filename=filename)
        self.file = file

    def install_prepare(self, args='', quiet=False):
        if not hasattr(self, 'file'):
            self.download()
        if self.apps:
            for app in self.apps:
                app.install_prepare(args, quiet)
        data = self.data
        file = self.file
        tmp = GetConfig(data.name, filename='args.json')
        if tmp:
            data.args = tmp
        if args:
            quiet = True
            data.args = args
        if not file:
            self.command = ''
        elif quiet:
            self.command = str(file)+' '+data.args
        else:
            self.command = str(file)

    def install(self, veryquiet=False, verify=False, force_verify=False, delete_tmp=False, delete_files=False, portable=False):
        if not hasattr(self, 'command'):
            self.install_prepare()
        data = self.data
        file = self.file
        command = self.command
        filename = file.name if file else ''
        if self.apps:
            for app in self.apps:
                app.install(veryquiet, verify, force_verify,
                            delete_tmp, delete_files)
        if force_verify:
            verify = True
        if veryquiet and not data.args:
            print(_('\nskip installing {name}').format(name=data.name))
            return
        if force_verify and not data.valid:
            print(_('\nskip installing {name}').format(name=data.name))
            return
        code = -1
        if data.cmd.get('start'):
            Execute(data.cmd['start'].format(file=str(file)))
        if portable:
            data.bin = ['MPKG-PORTABLE']
        if data.bin:
            if GetConfig('allow_portable') == 'yes':
                root = InstallPortable(
                    file, data.asdict(), delete_files)
                if data.cmd.get('end'):
                    Execute(data.cmd['end'].format(root=root, file=str(file)))
                self.dry_run()
            else:
                logger.warning(f'skip portable {filename}')
        else:
            if command:
                print(_('\ninstalling {name} using {command}').format(
                    name=data.name, command=command))
            code = os.system(command)
            if data.cmd.get('end'):
                Execute(data.cmd['end'].format(file=str(file)))
            self.dry_run()
            passed = False
            if data.valid:
                if len(data.valid) > 2:
                    valid = data.valid
                else:
                    valid = range(data.valid[0], data.valid[1] + 1)
                if not code in valid:
                    logger.warning(f'wrong returncode {code}')
                else:
                    passed = True
            if verify and not passed:
                print(_('verification failed'))
        if delete_tmp and file:
            file.unlink()

    def extract(self, with_ver=False):
        root = GetConfig(self.data.name, filename='xroot.json')
        if with_ver:
            Extract(self.file, root, ver=self.data.ver)
        else:
            Extract(self.file, root)
