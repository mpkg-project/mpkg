#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
import platform
import shutil
from pathlib import Path

import click

from .common import soft_data
from .config import GetConfig, SetConfig
from .lnktools import create_lnk
from .load import GetSofts
from .utils import Download, Extract, Selected, logger

_ = gettext.gettext
ARCH = platform.architecture()[0]
MACHINE = platform.machine().lower()
SYS = platform.system()
BIN_DIR = Path(GetConfig('bin_dir', default='.'))


def Linking(name, value='', delete=False):
    if not value and not delete:
        return
    batfile = BIN_DIR / (name+'.bat')
    cmd = GetConfig('alias_command')
    if delete:
        if cmd:
            cmd = GetConfig('alias_command_delete')
            if cmd:
                os.system(cmd.format(name=name))
            else:
                print('cannot delete '+name)
        elif os.name == 'nt':
            if batfile.exists():
                batfile.unlink()
            else:
                print(f"{name} dosen't exist")
    else:
        print(_('linking {0} => {1}').format(value, name))
        if cmd:
            os.system(cmd.format(name=name, value=value))
        elif os.name == 'nt':
            os.system('echo @echo off>{0}'.format(batfile))
            os.system('echo "{0}" %*>>{1}'.format(value, batfile))


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
    if isinstance(soft['bin'], dict):
        soft['bin'] = soft['bin'][ARCH]
    if 'MPKG-PORTABLE-EXE' in soft['bin']:
        soft['bin'].remove('MPKG-PORTABLE-EXE')
        if not root.exists():
            root.mkdir()
        filepath = shutil.move(filepath, root/filepath.name)
    elif 'MPKG-DEB' in soft['bin']:
        soft['bin'].remove('MPKG-DEB')
        cmd = f'sudo apt install {filepath}'  # TODO: custom commmand
        logger.debug(f'executing {cmd}')
        os.system(cmd)
    else:
        root = Extract(filepath, root)
    SetConfig(soft['name'], str(root), filename='root_installed.json')
    for file in [file for file in soft['bin'] if file != 'MPKG-PORTABLE']:
        if isinstance(file, list):
            args = ' ' + file[2] if len(file) == 3 else ''
            file, alias = file[0], file[1]
        else:
            args, alias = '', ''
        if file.startswith('MPKGLNK|'):
            desktop_dir = GetConfig('desktop_dir')
            desktop_dir = Path(desktop_dir) if desktop_dir else \
                Path.home() / 'Desktop'
            startmenu_dir = GetConfig('startmenu_dir')
            startmenu_dir = Path(startmenu_dir) if startmenu_dir else Path(
                os.getenv('APPDATA')) / 'Microsoft/Windows/Start Menu/Programs'
            root_dirs = [desktop_dir, startmenu_dir]
            if GetConfig('lnk_path') == 'desktop':
                root_dirs = [desktop_dir]
            elif GetConfig('lnk_path') == 'startmenu':
                root_dirs = [startmenu_dir]
            elif GetConfig('lnk_path') == 'none':
                root_dirs = []
            for lnk_root in root_dirs:
                strlist = file[8:].split('|')
                if len(strlist) == 2:
                    strlist.append('')
                target = root / strlist[1]
                args = '|'.join(strlist[2:])  # TODO
                if target.is_file():
                    lnk_name = strlist[0] if strlist[0] else \
                        target.name.split('.')[0]
                    lnk_path = lnk_root / (lnk_name+'.lnk')
                    print(_('creating lnk({0}) for {1}').format(
                        lnk_path.absolute(), target.absolute()))
                    create_lnk(target.absolute(), lnk_path.absolute())
            continue
        binfile = root / file
        if binfile.is_file():
            if SYS == 'Linux':
                cmd = f'ln -s "{str(binfile)}" "{str(BIN_DIR / name)}"'
                logger.debug(f'executing {cmd}')
                os.system(f'chmod +x "{str(binfile)}"')
                os.system(f'rm -f "{str(BIN_DIR / name)}"')
                os.system(cmd)
                continue
            shimexe = GetConfig('shimexe')
            cmd = GetConfig('link_command')
            name = alias if alias else binfile.name.split('.')[0]
            value = str(binfile)+' '+args if args else binfile
            if shimexe:
                print(_('creating shim for {0}').format(name))
                shutil.copy(shimexe, str(BIN_DIR / (name + '.exe')))
                with open(str(BIN_DIR / (name + '.shim')), 'wb') as f:
                    txt = f'path = {str(binfile.absolute())}\r\nargs = {args}'.encode(
                        'utf-8')
                    f.write(txt)
            elif cmd:
                os.system(cmd.format(name=name, value=value,
                                     binfile=binfile, args=args))
            else:
                Linking(name, value)
        else:
            logger.warning(f'{binfile} not found')
    return root


class App(object):
    def __init__(self, data, no_format=False):
        if not data.get('name'):
            data['name'] = data['id']
        self.apps = [App(soft) for soft in GetSofts()
                     if soft['id'] in data['depends']] if data.get('depends') else []
        self.data = soft_data(**data)
        if not no_format:
            self.data.format()

    def dry_run(self):
        logger.debug(f'installed: {self.data.name}|{self.data.ver}')
        SetConfig(self.data.name, [self.data.ver,
                                   self.data.date], filename='installed.json')

    def download_prepare(self):
        if not self.data.arch:
            self.data.arch = ToLink(self.data.links)

    def download(self, root=None):
        self.download_prepare()
        data = self.data
        if self.apps:
            for app in self.apps:
                app.download()
        if ARCH == '64bit' and not data.arch.get('64bit') and data.arch.get('32bit'):
            logger.debug('using 32bit...')
            data.arch['64bit'] = data.arch['32bit']
            if isinstance(data.sha256, dict) and data.sha256.get('32bit'):
                data.sha256['64bit'] = data.sha256['32bit']
        if not ARCH in data.arch:
            if not self.apps:
                logger.warning(f'{data.name} has no link available')
                exit()
            file = ''
        else:
            if isinstance(data.sha256, list):
                i = data.links.index(data.arch[ARCH])
                data.sha256 = {ARCH: data.sha256[i]}
            sha256 = data.sha256.get(ARCH) if data.sha256 else ''
            filename = data.name+'_'+data.arch[ARCH].split('/')[-1]
            file = Download(data.arch[ARCH], directory=root,
                            sha256=sha256, filename=filename)
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
        if GetConfig(data.name, filename='pflag.json') == "yes":
            pinfo = GetConfig(data.name, filename='pinfo.json')
            data.bin = pinfo if pinfo else ['MPKG-PORTABLE']
        if tmp:
            data.args = tmp
        if args:
            quiet = True
            data.args = args
        if not file:
            self.command = ''
        elif quiet:
            self.command = f'"{file}" {data.args}'
        else:
            self.command = f'"{file}"'

    def install(self, veryquiet=False, verify=False, force_verify=False, delete_downloaded=False, delete_installed=False):
        if not hasattr(self, 'command'):
            self.install_prepare()
        data = self.data
        file = self.file
        command = self.command
        filename = file.name if file else ''
        if self.apps:
            for app in self.apps:
                app.install(veryquiet, verify, force_verify,
                            delete_downloaded, delete_installed)
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
        if data.bin:
            if GetConfig('allow_portable') == 'yes':
                root = InstallPortable(
                    file, data.asdict(), delete_installed)
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
            logger.debug(f'returned {code}')
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
        if GetConfig('delete_after_install') == 'yes':
            delete_downloaded = True
        for rule in GetConfig('saveto', default=[]):
            ext, dir_ = list(rule.items())[0]
            if str(file).endswith(ext):
                if dir_ == 'TEMPDIR-D':
                    delete_downloaded = True
        if delete_downloaded and file and code == 0:
            logger.debug(f'delete {file}')
            file.unlink()

    def extract(self, with_ver=False, root=None, delete=False):
        xroot = GetConfig(
            self.data.name, filename='xroot.json') if not root else root
        if with_ver:
            Extract(self.file, xroot, ver=self.data.ver, delete=delete)
        else:
            Extract(self.file, xroot, delete=delete)
