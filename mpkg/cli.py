#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
from pprint import pprint
from shutil import rmtree

import click

from . import __version__
from .app import App, Linking
from .config import HOME, GetConfig, SetConfig
from .load import ConfigSoft, GetOutdated, GetSofts, Load, Names2Softs
from .utils import DownloadApps, PreInstall, logger, proxy

_ = gettext.gettext


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(__version__, '-v', '--version')
def cli():
    pass


@cli.command()
@click.option('-j', '--jobs', default=10, help=_('threads'))
@click.option('--sync/--no-sync', default=True, help=_('sync source files'))
@click.option('-l', '--changelog', is_flag=True)
@click.option('--use-cache', is_flag=True)
def sync(jobs, sync, changelog, use_cache):
    if proxy:
        print(f'using proxy: {proxy}\n')
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
            if soft.get('notes'):
                print(f' notes: {soft["notes"]}')
            notes = GetConfig(soft['name'], filename='notes.json')
            if notes:
                print(f' notes: {notes}')
            if changelog and soft.get('changelog'):
                print(f' changelog: {soft["changelog"]}')


@cli.command()
@click.argument('file')
@click.option('--config', is_flag=True)
@click.option('-i', '--install', is_flag=True)
@click.option('-d', '--download', is_flag=True)
@click.option('--id')
def load(file, config, install, download, id):
    if config:
        Load(file, installed=False)
        return
    loaded = Load(file)
    if loaded[1] == '.py':
        apps = []
        for pkg in loaded[0]:
            pkg.prepare()
            apps += [App(soft) for soft in pkg.json_data['packages']]
    elif loaded[1] == '.json':
        apps = [App(soft) for soft in loaded[0]]
    if id:
        apps = [app for app in apps if app.data.id == id]
    for app in apps:
        if install:
            app.install()
        elif download:
            app.download()
        else:
            pprint(app.data.asdict(simplify=True))


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('-f', '--force', is_flag=True)
@click.option('--load/--no-load', default=True)
@click.option('--delete-all', is_flag=True)
@click.option('--url-redirect', is_flag=True)
@click.option('--pre-install', is_flag=True)
def config(packages, force, load, delete_all, url_redirect, pre_install):
    if pre_install:
        PreInstall()
        return
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
            rmtree(HOME)
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
@click.option('--notes', is_flag=True)
@click.option('--args', is_flag=True)
@click.option('--root', is_flag=True)
@click.option('--name', is_flag=True)
def set_(key, values, islist, isdict, add, test, delete, filename, disable, enable, notes, args, root, name):
    if notes:
        filename = 'notes.json'
    elif args:
        filename = 'args.json'
    elif root:
        filename = 'root.json'
    elif name:
        filename = 'name.json'
        if not delete:
            values[0] = values[0].lower()
            if values[0] in [soft['name'] for soft in GetSofts()] or values[0] in GetConfig(filename='name.json', default={}):
                logger.warning(f'name already exists')
                return
    else:
        filename = 'config.json'
    if not GetConfig('sources'):
        PreInstall()
    if delete:
        values = []
        if not GetConfig(key, filename=filename):
            logger.warning(f'invalid key')
    if isdict:
        values = [{values[i]: values[i+1]} for i in range(0, len(values), 2)]
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
            logger.warning(f'cannot find {key}')
            return
        if not test:
            SetConfig(key+'-disabled', value_, filename=filename)
        delete = True
    elif enable:
        value = GetConfig(key+'-disabled', filename=filename)
        if not value:
            logger.warning(f'cannot find {key}-disabled')
            return
        if not test:
            SetConfig(key+'-disabled', delete=True, filename=filename)
    print('set {key}={value}'.format(key=key, value=value))
    if not test:
        SetConfig(key, value, delete=delete, filename=filename)


@cli.command()
@click.argument('key', required=False)
@click.option('--filename')
@click.option('--notes', is_flag=True)
@click.option('--args', is_flag=True)
@click.option('--root', is_flag=True)
@click.option('--name', is_flag=True)
def get(key, filename, notes, args, root, name):
    if notes:
        filename = 'notes.json'
    elif args:
        filename = 'args.json'
    elif root:
        filename = 'root.json'
    elif name:
        filename = 'name.json'
    else:
        filename = 'config.json'
    pprint(GetConfig(key, filename=filename))


@cli.command()
@click.argument('packages', nargs=-1, required=True)
@click.option('-i', '--install', is_flag=True)
def download(packages, install):
    apps = [App(soft) for soft in Names2Softs(packages)]
    DownloadApps(apps)
    for app in apps:
        if install:
            app.dry_run()


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
@click.option('--portable', is_flag=True)
def install(packages, download, outdated, dry_run, delete_tmp, delete_files, quiet, veryquiet, args, verify, force_verify, portable):
    print('By installing you accept licenses for the packages.\n')
    if veryquiet:
        quiet = True
    if packages:
        softs = Names2Softs(packages)
    elif outdated:
        softs = Names2Softs(list(GetOutdated().keys()))
    else:
        print(install.get_help(click.core.Context(install)))
        return
    apps = [App(soft) for soft in softs]
    if dry_run:
        for app in apps:
            app.dry_run()
    else:
        DownloadApps(apps)
        for app in apps:
            app.install_prepare(args, quiet)
            if download:
                if app.file:
                    app.dry_run()
                    if os.name == 'nt':
                        script = app.file.parent / 'install.bat'
                        os.system(f'echo {app.command} >> {script}')
            else:
                app.install(veryquiet, verify, force_verify,
                            delete_tmp, delete_files, portable)


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('--set-root')
@click.option('--with-ver', is_flag=True)
@click.option('-i', '--install', is_flag=True)
@click.option('-A', '--all', is_flag=True)
def extract(packages, install, set_root, with_ver, all):
    if all:
        pprint(sorted([soft['name'] for soft in GetSofts()
                       if soft.get('allowExtract') or soft.get('bin')]), compact=True)
    elif packages:
        softs = Names2Softs(packages)
        if set_root:
            SetConfig(softs[0]['name'], set_root, filename='xroot.json')
            return
        apps = [App(soft) for soft in softs]
        DownloadApps(apps)
        for app in apps:
            if install:
                app.dry_run()
            app.extract(with_ver)


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


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('-o', '--outdated', is_flag=True)
@click.option('-i', '--installed', is_flag=True)
@click.option('-A', '--all', is_flag=True)
def show(packages, outdated, installed, all):
    if installed:
        pkgs = GetConfig(filename='installed.json')
        pprint(sorted(list(pkgs.keys())), compact=True)
    elif outdated:
        pprint(sorted(list(GetOutdated().keys())), compact=True)
    elif packages:
        pprint(sorted(Names2Softs(packages),
                      key=lambda x: x.get('name')), compact=True)
    elif all:
        pprint(sorted([soft['name'] for soft in GetSofts()]), compact=True)


@cli.command()
@click.argument('name')
@click.argument('value', required=False)
@click.option('-d', '--delete', is_flag=True)
def alias(name, value, delete):
    Linking(name, value, delete)


@cli.command()
@click.argument('strings', nargs=-1)
def search(strings):
    strings = [s.lower() for s in strings]
    for soft in GetSofts():
        result = [1 for string in strings if string in soft['name'].lower()
                  or string in soft.get('description', '').lower()]
        if sum(result) == len(strings):
            print(soft['name'])


if __name__ == "__main__":
    cli()
