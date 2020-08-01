#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
import shutil
from platform import architecture
from pprint import pformat, pprint

import click

from .common import Soft
from .config import HOME, GetConfig, SetConfig
from .load import ConfigSoft, GetOutdated, GetSofts, Load, Names2Softs
from .utils import DownloadSofts, Extract, InstallPortable, PreInstall

_ = gettext.gettext
arch = architecture()[0]


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def cli():
    pass


@cli.command()
@click.option('-j', '--jobs', default=10, help=_('threads'))
@click.option('--sync/--no-sync', default=True, help=_('sync source files'))
@click.option('-l', '--changelog', is_flag=True)
@click.option('--use-cache', is_flag=True)
def sync(jobs, sync, changelog, use_cache):
    softs = GetSofts(jobs, sync, use_cache=use_cache)
    names = [soft['name'] for soft in softs]
    outdated = sorted(list(GetOutdated().items()),
                      key=lambda x: x[1][0], reverse=True)
    if len(outdated) == 0:
        print(_('Already up to date.'))
    else:
        for name, value in outdated:
            soft = softs[names.index(name)]
            print()
            if value[0]:
                print(f'{name}|{value[0]}\t{value[1]}->{value[2]}')
            else:
                print(f'{name}\t{value[1]}->{value[2]}')
            if soft.get('rem'):
                print(f' rem: {soft["rem"]}')
            rem = GetConfig(soft['name'], filename='rem.json')
            if rem:
                print(f' rem: {rem}')
            if changelog and soft.get('changelog'):
                print(f' changelog: {soft["changelog"]}')


@cli.command()
@click.argument('pyfile')
@click.option('--config', is_flag=True)
def load(pyfile, config):
    if config:
        Load(pyfile, installed=False)
        return
    for pkg in Load(pyfile)[0]:
        pkg.prepare()
        pprint(pkg.data)


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('-f', '--force', is_flag=True)
@click.option('--load/--no-load', default=True)
@click.option('--delete-all', is_flag=True)
@click.option('--url-redirect', is_flag=True)
def config(packages, force, load, delete_all, url_redirect):
    if packages:
        for soft in Names2Softs(packages):
            ConfigSoft(soft)
        return
    if url_redirect:
        rules = []
        while True:
            r = input(_('\n input pattern(press enter to pass): '))
            if r:
                rules.append({r: input(_(' redirect to: '))})
            else:
                SetConfig('redirect', rules)
                return
    if not force and GetConfig('sources'):
        print(_('pass'))
    elif delete_all:
        if HOME.exists():
            shutil.rmtree(HOME)
    else:
        PreInstall()
        sources = []
        while True:
            s = input(_('\n input sources(press enter to pass): '))
            if s:
                sources.append(s)
                if load:
                    Load(s, installed=False)
            else:
                break
        SetConfig('sources', sources)


@cli.command('set')
@click.argument('key')
@click.argument('values', nargs=-1)
@click.option('islist', '--list', is_flag=True)
@click.option('isdict', '--dict', is_flag=True)
@click.option('--add', is_flag=True)
@click.option('--delete', is_flag=True)
@click.option('--test', is_flag=True)
@click.option('--filename')
@click.option('--disable', is_flag=True)
@click.option('--enable', is_flag=True)
@click.option('--rem', is_flag=True)
@click.option('--args', is_flag=True)
@click.option('--root', is_flag=True)
def set_(key, values, islist, isdict, add, test, delete, filename, disable, enable, rem, args, root):
    if rem:
        filename = 'rem.json'
    if args:
        filename = 'args.json'
    if root:
        filename = 'root.json'
    if not filename:
        filename = 'config.json'
    if not GetConfig('sources'):
        PreInstall()
    if isdict:
        values = [{values[0]: values[1]}]
    if add:
        islist = True
        old = GetConfig(key, filename=filename)
        old = old if old else []
        values = old + list(values)
    if len(values) > 1 or islist:
        value = list(values)
    elif len(values) == 1:
        value = values[0]
    else:
        value = ''
    if disable:
        value_ = GetConfig(key, filename=filename)
        if not value_:
            print(f'warning: cannot find {key}')
        if not test:
            SetConfig(key+'-disabled', value_, filename=filename)
        delete = True
    elif enable:
        value = GetConfig(key+'-disabled', filename=filename)
        if not value:
            print(f'warning: cannot find {key}-disabled')
        if not test:
            SetConfig(key+'-disabled', delete=True, filename=filename)
    print('set {key}={value}'.format(key=key, value=value))
    if not test:
        SetConfig(key, value, delete=delete, filename=filename)


@cli.command()
@click.argument('packages', nargs=-1, required=True)
def download(packages):
    softs = Names2Softs(packages)
    DownloadSofts(softs)


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('-d', '--download', is_flag=True)
@click.option('-o', '--outdated', is_flag=True)
@click.option('--dry-run', is_flag=True)
@click.option('-del', '--delete-tmp', is_flag=True)
@click.option('--delete-files', is_flag=True)
@click.option('-q', '--quiet', is_flag=True)
@click.option('-qq', '--veryquiet', is_flag=True)
@click.option('--args')
@click.option('--verify', is_flag=True)
@click.option('--force-verify', is_flag=True)
def install(packages, download, outdated, dry_run, delete_tmp, delete_files, quiet, veryquiet, args, verify, force_verify):
    if veryquiet:
        quiet = True
    if packages:
        softs = Names2Softs(packages)
    elif outdated:
        softs = Names2Softs(list(GetOutdated().keys()))
    else:
        print(install.get_help(click.core.Context(install)))
        return
    for soft in softs:
        if not soft.get('date'):
            soft['date'] = []
        if not soft.get('args'):
            soft['args'] = ''
        tmp = GetConfig(soft['name'], filename='args.json')
        if tmp:
            soft['args'] = tmp
        if args:
            quiet = True
            soft['args'] = args
        if not verify:
            SetConfig(soft['name'], [soft['ver'], soft['date']],
                      filename='installed.json')
    if not dry_run:
        files, softs = DownloadSofts(softs)
        for i, file in enumerate(files):
            soft = softs[i]
            filename = file.name
            if quiet:
                command = str(file)+' '+soft['args']
            else:
                command = str(file)
            if veryquiet and not soft['args']:
                print(_('\nskip installing {name}').format(name=soft['name']))
                continue
            if force_verify and not soft['valid']:
                print(_('\nskip installing {name}').format(name=soft['name']))
                continue
            if download:
                if os.name == 'nt':
                    script = file.parent / 'install.bat'
                    if filename.split['.'][-1] in ['exe', 'msi', 'bat']:
                        os.system(f'echo {command} >> {script}')
            else:
                code = -1
                if os.name == 'nt':
                    if soft.get('bin'):
                        if GetConfig('portable') == 'yes':
                            InstallPortable(file, soft, delete_files)
                        else:
                            print(f'warning: skip portable {filename}')
                        if delete_tmp:
                            file.unlink()
                        continue
                    print(_('\ninstalling {name} using {command}').format(
                        name=soft['name'], command=command))
                    if filename.split['.'][-1] in ['exe', 'msi', 'bat']:
                        code = os.system(command)
                    else:
                        print(f'warning: cannot install {filename}')
                else:
                    code = os.system(command)
                if soft['valid']:
                    if len(soft['valid']) > 2:
                        valid = soft['valid']
                    else:
                        valid = range(soft['valid'][0], soft['valid'][1] + 1)
                    if not code in valid:
                        print(
                            _('warning: wrong returncode {code}').format(code=code))
                    elif verify:
                        SetConfig(soft['name'], [soft['ver'],
                                                 soft['date']], filename='installed.json')
                if delete_tmp:
                    file.unlink()


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('--set-root')
@click.option('--with-ver', is_flag=True)
@click.option('--install', is_flag=True)
def extract(packages, install, set_root, with_ver):
    if not packages:
        pprint([soft['name']
                for soft in GetSofts() if soft.get('allowExtract')])
    else:
        softs = Names2Softs(packages)
        if install:
            for soft in softs:
                if not soft.get('date'):
                    soft['date'] = []
                SetConfig(soft['name'], [soft['ver'], soft['date']],
                          filename='installed.json')
        if set_root:
            SetConfig(softs[0]['name'], set_root, filename='xroot.json')
            return
        files, softs = DownloadSofts(softs)
        for i, file in enumerate(files):
            root = GetConfig(softs[i]['name'], filename='xroot.json')
            if with_ver:
                Extract(file, root, ver=softs[i]['ver'])
            else:
                Extract(file, root)


@cli.command()
@click.argument('packages', nargs=-1)
def remove(packages):
    packages = [pkg.lower() for pkg in packages]
    if packages:
        pkgs = GetConfig(filename='installed.json')
        names = [x for x in list(pkgs.keys()) if x.lower() in packages]
        for name in names:
            SetConfig(name, filename='installed.json', delete=True)
    else:
        print(remove.get_help(click.core.Context(remove)))
        return


@cli.command('list')
@click.argument('packages', nargs=-1)
@click.option('-o', '--outdated', is_flag=True)
@click.option('-i', '--installed', is_flag=True)
def list_(packages, outdated, installed):
    if installed:
        pkgs = GetConfig(filename='installed.json')
        pprint(list(pkgs.keys()), compact=True)
    elif outdated:
        pprint(list(GetOutdated().keys()), compact=True)
    elif packages:
        pprint(Names2Softs(packages), compact=True)
    else:
        pprint([soft['name'] for soft in GetSofts()], compact=True)


if __name__ == "__main__":
    cli()
