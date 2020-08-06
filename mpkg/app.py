#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
from pathlib import Path
from platform import architecture
from shutil import rmtree

import click

from .config import GetConfig, SetConfig
from .load import GetSofts
from .utils import Download, Extract, Selected

_ = gettext.gettext
arch = architecture()[0]


def ToLink(links: list):
    if not links:
        return {}
    elif len(links) > 1:
        link = Selected(links, msg=_('select a link to download:'))[0]
        return {arch: link}
    else:
        return {arch: links[0]}


def Execute(string):
    if not GetConfig('allow_cmd') == 'yes':
        print(f'skip command({string})')
        return
    for cmd in string.strip().split('\n'):
        print(f'executing {cmd}')
        if GetConfig('skip_confirm') == 'yes' or click.confirm(' confirmed ?'):
            code = os.system(cmd)
            if code:
                print(f'warning: returned {code}')


def InstallPortable(filepath, soft, delete):
    if delete:
        old = Path(GetConfig(soft['name'], filename='root_installed.json'))
        if old.exists():
            rmtree(old)
    root = GetConfig(soft['name'], filename='root.json')
    if not root:
        name = soft['name']
        root = Path(GetConfig('files_dir')) / name
    root = Extract(filepath, root)
    SetConfig(soft['name'], str(root), filename='root_installed.json')
    bin = Path(GetConfig('bin_dir'))
    if isinstance(soft['bin'], dict):
        soft['bin'] = soft['bin'][arch]
    for file in [file for file in soft['bin'] if file != 'PORTABLE']:
        binfile = root / file
        if binfile.exists() and binfile.is_file():
            batfile = bin / (binfile.name.split('.')[0]+'.bat')
            print(_('linking {0} => {1}').format(binfile, batfile))
            os.system('echo @echo off>{0}'.format(batfile))
            os.system('echo {0} %*>>{1}'.format(binfile, batfile))
    return root


class App(object):
    def __init__(self, data):
        if not data.get('name'):
            data['name'] = data['id']
        if not data.get('date'):
            data['date'] = []
        if not data.get('args'):
            data['args'] = ''
        if not data.get('cmd'):
            data['cmd'] = {}
        if not data.get('valid'):
            data['valid'] = {}
        self.apps = [App(soft) for soft in GetSofts()
                     if soft['id'] in data['depends']] if data.get('depends') else []
        self.data = data

    def dry_run(self):
        SetConfig(self.data['name'], [self.data['ver'],
                                      self.data['date']], filename='installed.json')

    def download_prepare(self):
        if not self.data.get('link'):
            self.data['link'] = ToLink(self.data.get('links'))

    def download(self):
        self.download_prepare()
        if self.apps:
            for app in self.apps:
                app.download()
        if not arch in self.data['link']:
            if not self.apps:
                print(f'warning: {self.data["name"]} has no link available')
            file = ''
        else:
            file = Download(self.data['link'][arch])
        self.file = file

    def install_prepare(self, args='', quiet=False):
        if not hasattr(self, 'file'):
            self.download()
        if self.apps:
            for app in self.apps:
                app.install_prepare(args, quiet)
        soft = self.data
        file = self.file
        tmp = GetConfig(soft['name'], filename='args.json')
        if tmp:
            soft['args'] = tmp
        if args:
            quiet = True
            soft['args'] = args
        if not file:
            self.command = ''
        elif quiet:
            self.command = str(file)+' '+soft['args']
        else:
            self.command = str(file)

    def install(self, veryquiet=False, verify=False, force_verify=False, delete_tmp=False, delete_files=False):
        if not hasattr(self, 'command'):
            self.install_prepare()
        soft = self.data
        file = self.file
        command = self.command
        filename = file.name if file else ''
        if self.apps:
            for app in self.apps:
                app.install(veryquiet, verify, force_verify,
                            delete_tmp, delete_files)
        if force_verify:
            verify = True
        if veryquiet and not soft['args']:
            print(_('\nskip installing {name}').format(name=soft['name']))
            return
        if force_verify and not soft['valid']:
            print(_('\nskip installing {name}').format(name=soft['name']))
            return
        code = -1
        if soft['cmd'].get('start'):
            Execute(soft['cmd']['start'].format(file=str(file)))
        if soft.get('bin'):
            if GetConfig('allow_portable') == 'yes':
                root = InstallPortable(file, soft, delete_files)
                if soft['cmd'].get('end'):
                    Execute(soft['cmd']['end'].format(
                        root=root, file=str(file)))
                self.dry_run()
            else:
                print(f'warning: skip portable {filename}')
        else:
            if command:
                print(_('\ninstalling {name} using {command}').format(
                    name=soft['name'], command=command))
            code = os.system(command)
            if soft['cmd'].get('end'):
                Execute(soft['cmd']['end'].format(file=str(file)))
            self.dry_run()
            passed = False
            if soft['valid']:
                if len(soft['valid']) > 2:
                    valid = soft['valid']
                else:
                    valid = range(soft['valid'][0], soft['valid'][1] + 1)
                if not code in valid:
                    print(
                        _('warning: wrong returncode {code}').format(code=code))
                else:
                    passed = True
            if verify and not passed:
                print(_('verification failed'))
        if delete_tmp and file:
            file.unlink()

    def extract(self, with_ver=False):
        root = GetConfig(self.data['name'], filename='xroot.json')
        if with_ver:
            Extract(self.file, root, ver=self.data['ver'])
        else:
            Extract(self.file, root)
