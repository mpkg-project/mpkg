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
@click.option('-c', '--use-cache', is_flag=True)
@click.option('--reverse', is_flag=True)
def sync(jobs, sync, changelog, use_cache, reverse):
    if proxy:
        print(f'using proxy: {proxy}\n')
    softs = GetSofts(jobs, sync, use_cache=use_cache)
    names = [soft['name'] for soft in softs]
    outdated = sorted(list(GetOutdated().items()),
                      key=lambda x: x[1][0], reverse=reverse)
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
@click.option('-t', '--temporary', is_flag=True)
@click.option('--id')
def load(file, config, install, download, id, temporary):
    if config:
        Load(file, installed=False, temporary=temporary)
        return
    loaded = Load(file, temporary=temporary)
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
        if not app.data.ver:
            logger.warning('invalid ver')
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
@click.option('--pinfo', is_flag=True)
def set_(key, values, islist, isdict, add, test, delete, filename, disable, enable, notes, args, root, name, pinfo):
    if notes:
        filename = 'notes.json'
    elif args:
        filename = 'args.json'
    elif root:
        filename = 'root.json'
    elif name:
        filename = 'name.json'
        if not delete:
            values = [v.lower() for v in values]
            if values[0] in [soft['name'] for soft in GetSofts()] or values[0] in GetConfig(filename='name.json', default={}):
                logger.warning(f'name already exists')
                return
    elif pinfo:
        filename = 'pinfo.json'
    else:
        filename = filename if filename else 'config.json'
    if not GetConfig('sources'):
        PreInstall()
    if delete:
        values = []
        if not GetConfig(key, filename=filename):
            logger.warning('invalid key')
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
        filename = filename if filename else 'config.json'
    pprint(GetConfig(key, filename=filename))


@cli.command()
@click.argument('packages', nargs=-1, required=True)
@click.option('-i', '--install', is_flag=True)
@click.option('-O', '--root')
def download(packages, install, root):
    apps = [App(soft) for soft in Names2Softs(packages)]
    DownloadApps(apps, root)
    for app in apps:
        if install:
            app.dry_run()


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('-d', '--download', is_flag=True)
@click.option('-o', '--outdated', is_flag=True)
@click.option('--dry-run', is_flag=True)
@click.option('-del', '--delete-downloaded', is_flag=True)
@click.option('--delete-installed', is_flag=True)
@click.option('-q', '--quiet', is_flag=True)
@click.option('-qq', '--veryquiet', is_flag=True)
@click.option('--args')
@click.option('--verify', is_flag=True)
@click.option('--force-verify', is_flag=True)
def install(packages, download, outdated, dry_run, delete_downloaded, delete_installed, quiet, veryquiet, args, verify, force_verify):
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
                            delete_downloaded, delete_installed)


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('--set-pflag', is_flag=True)
@click.option('--set-root')
@click.option('-O', '--root')
@click.option('--with-ver', is_flag=True)
@click.option('-i', '--install', is_flag=True)
@click.option('-A', '--show-all', is_flag=True)
@click.option('-del', '--delete-downloaded', is_flag=True)
def extract(packages, install, set_root, with_ver, show_all, root, set_pflag, delete_downloaded):
    if show_all:
        pprint(sorted([soft['name'] for soft in GetSofts()
                       if soft.get('allowExtract') or soft.get('bin')]), compact=True)
    elif packages:
        softs = Names2Softs(packages)
        if set_root:
            SetConfig(softs[0]['name'], set_root, filename='xroot.json')
            return
        if set_pflag:
            for soft in softs:
                SetConfig(soft['name'], 1, filename='pflag.json')
            return
        apps = [App(soft) for soft in softs]
        DownloadApps(apps)
        for app in apps:
            if install:
                app.dry_run()
            app.extract(with_ver, root, delete_downloaded)


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
@click.option('-i', '-l', '--installed', '--local', is_flag=True)
@click.option('Aflag', '-A', '--all', is_flag=True)
@click.option('pflag', '-pp', '--pprint', is_flag=True)
def show(packages, outdated, installed, Aflag, pflag):
    if packages and not installed:
        pprint(sorted(Names2Softs(packages),
                      key=lambda x: x.get('name')), compact=True)
    else:
        if installed:
            iDict = GetConfig(filename='installed.json')
            names = sorted(list(iDict.keys()))
            if packages:
                for soft in Names2Softs(packages, softs=[{'name': n} for n in names]):
                    name = soft['name']
                    print(f'{name}|{iDict[name]}')
                return
        elif outdated:
            names = sorted(list(GetOutdated().keys()))
        elif Aflag:
            names = sorted([soft['name'] for soft in GetSofts()])
        if pflag:
            pprint(names, compact=True)
        else:
            for name in names:
                print(name)


@cli.command()
@click.argument('name')
@click.argument('value', required=False)
@click.option('-d', '--delete', is_flag=True)
def alias(name, value, delete):
    Linking(name, value, delete)


@cli.command()
@click.argument('strings', nargs=-1)
@click.option('-n', '--name', is_flag=True)
@click.option('pflag', '-pp', '--pprint', is_flag=True)
def search(strings, name, pflag):
    strings = [s.lower() for s in strings]
    names = []
    for soft in GetSofts():
        if name:
            score = [1 for string in strings if string in soft['name'].lower()]
        else:
            score = [1 for string in strings if string in soft['name'].lower()
                     or string in soft.get('description', '').lower()]
        if sum(score) == len(strings):
            if pflag:
                names.append(soft['name'])
            else:
                print(soft['name'])
    if pflag:
        pprint(names, compact=True)


if __name__ == "__main__":
    cli()
