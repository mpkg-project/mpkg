#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
from platform import architecture

from .config import GetConfig, SetConfig
from .utils import Download, Execute, InstallPortable, ToLink

_ = gettext.gettext
arch = architecture()[0]


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
        self.data = data

    def dry_run(self):
        SetConfig(self.data['name'], [self.data['ver'],
                                      self.data['date']], filename='installed.json')

    def download_prepare(self):
        if not self.data.get('link'):
            self.data['link'] = ToLink(self.data['links'])

    def download(self):
        self.download_prepare()
        if not arch in self.data['link']:
            print(f'warning: {self.data["name"]} has no link available')
            file = ''
        else:
            file = Download(self.data['link'][arch])
        self.file = file

    def install_prepare(self, args='', quiet=False):
        if not hasattr(self, 'file'):
            self.download()
        soft = self.data
        file = self.file
        tmp = GetConfig(soft['name'], filename='args.json')
        if tmp:
            soft['args'] = tmp
        if args:
            quiet = True
            soft['args'] = args
        if quiet:
            self.command = str(file)+' '+soft['args']
        else:
            self.command = str(file)

    def install(self, veryquiet=False, verify=False, force_verify=False, delete_tmp=False, delete_files=False):
        if not hasattr(self, 'command'):
            self.install_prepare()
        soft = self.data
        file = self.file
        command = self.command
        filename = file.name
        if force_verify:
            verify = True
        if veryquiet and not soft['args']:
            print(_('\nskip installing {name}').format(name=soft['name']))
            return
        if force_verify and not soft.get('valid'):
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
            else:
                print(f'warning: skip portable {filename}')
        else:
            if os.name == 'nt':
                if not file.name.split('.')[-1] in ['exe', 'msi', 'bat', 'vbs']:
                    print(f'warning: cannot install {file.name}')
                    return
            print(_('\ninstalling {name} using {command}').format(
                name=soft['name'], command=command))
            code = os.system(command)
            if soft['cmd'].get('end'):
                Execute(soft['cmd']['end'].format(file=str(file)))
            self.dry_run()
            passed = False
            if soft.get('valid'):
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
        if delete_tmp:
            file.unlink()

    def extract(self):
        pass
