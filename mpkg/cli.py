#!/usr/bin/env python3
# coding: utf-8

import functools
import gettext
import os
from datetime import datetime
from pprint import pprint
from shutil import rmtree

import click

from . import __version__
from .app import App, Linking
from .commands import cmd_doctor
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
@click.option('-f', '-F', '--force', is_flag=True)
@click.option('--reverse', is_flag=True)
def sync(jobs, sync, changelog, use_cache, force, reverse):
    if proxy:
        print(f'using proxy: {proxy}\n')
    softs = GetSofts(jobs, sync, use_cache=use_cache, ignore_cache=force)
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
@click.option('--no-format', is_flag=True)
@click.option('-w', '--write', is_flag=True)
@click.option('--arch')
@click.option('--id')
def load(file, config, install, download, id, temporary, no_format, write, arch):
    if config:
        Load(file, installed=False, temporary=temporary)
        return
    loaded = Load(file, temporary=temporary)
    if loaded[1] == '.py':
        apps = []
        for pkg in loaded[0]:
            pkg.prepare()
            apps += [App(soft, no_format=no_format)
                     for soft in pkg.json_data['packages']]
    elif loaded[1] == '.json':
        apps = [App(soft, no_format=no_format) for soft in loaded[0]]
    if id:
        apps = [app for app in apps if app.data.id == id]
    if write:
        text = '\n'.join([str(app.data.asdict(simplify=True)) for app in apps])
        with open(file+'.loaded.txt', 'wb') as f:
            f.write(text.encode('utf-8'))
        return
    if arch:
        if str(arch).lower() == 'none':
            apps = [
                app for app in apps if not app.data.id.startswith('MPKG-ARCH|')]
        else:
            id_pre = f'MPKG-ARCH|{arch}|'
            apps = [app for app in apps if app.data.id.startswith(id_pre)]
            for app in apps:
                app.data.id = app.data.id[len(id_pre):]
                app.data.name = app.data.id
    for app in apps:
        if not app.data.ver:
            logger.warning('invalid ver')
        if no_format:
            pprint(app.data.asdict(simplify=True))
            return
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


def filename_params(func):
    @click.option('--filename')
    @click.option('--notes', is_flag=True)
    @click.option('--args', is_flag=True)
    @click.option('--root', is_flag=True)
    @click.option('--xroot', is_flag=True)
    @click.option('--name', is_flag=True)
    @click.option('--pflag', is_flag=True)
    @click.option('--pinfo', is_flag=True)
    @functools.wraps(func)
    def wrapper(filename, notes, args, root, xroot, name, pflag, pinfo, *args_, **kwargs):
        if notes:
            filename = 'notes.json'
        elif args:
            filename = 'args.json'
        elif root:
            filename = 'root.json'
        elif xroot:
            filename = 'xroot.json'
        elif name:
            filename = 'name.json'
        elif pflag:
            filename = 'pflag.json'
        elif pinfo:
            filename = 'pinfo.json'
        else:
            filename = filename if filename else 'config.json'
        kwargs['filename'] = filename
        return func(*args_, **kwargs)
    return wrapper


@cli.command('set')
@click.argument('key')
@click.argument('values', nargs=-1)
@click.option('islist', '--list', is_flag=True)
@click.option('isdict', '--dict', is_flag=True)
@click.option('--add', is_flag=True)
@click.option('--delete', is_flag=True)
@click.option('--test', is_flag=True)
@click.option('--disable', is_flag=True)
@click.option('--enable', is_flag=True)
@filename_params
def set_(key, values, islist, isdict, add, test, delete, filename, disable, enable):
    if filename == 'name.json':
        if not delete:
            values = [v.lower() for v in values]
            if values[0] in [soft['name'] for soft in GetSofts()] or values[0] in GetConfig(filename='name.json', default={}):
                logger.warning(f'name already exists')
                return
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
        value = None
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
@filename_params
def get(key, filename):
    if key:
        print(GetConfig(key, filename=filename))
    else:
        pprint(GetConfig(key, filename=filename))


def apps_params(func):
    def name_handler(names, outdated=False):
        softs = Names2Softs(names)
        if outdated:
            softs = Names2Softs(list(GetOutdated().keys()))
        apps = [App(soft) for soft in softs]
        return apps

    @click.argument('packages', nargs=-1)
    @click.option('-o', '--outdated', is_flag=True)
    @click.option('--url')
    @click.option('--ver')
    @click.option('--ignore-hash', is_flag=True)
    @click.option('--x86', '--32bit', is_flag=True)
    @click.option('--x64', '--32bit', is_flag=True)
    @functools.wraps(func)
    def wrapper(packages, outdated, url, ver, ignore_hash, x86, x64, *args_, **kwargs):
        apps = name_handler(packages, outdated)
        if not apps:
            print("Missing argument 'PACKAGES...'")
            exit()
        for app in apps:
            if url:
                ignore_hash = True
                app.data.arch = {}
                app.data.links = [url]
            if ver:
                app.data.ver = ver
                app.data.format()
            if ignore_hash:
                app.data.sha256 = None
            if x86 and app.data.arch:
                app.data.arch['64bit'] = app.data.arch.get('32bit')
                app.data.sha256['64bit'] = app.data.sha256.get('32bit')
            if x64 and app.data.arch:
                app.data.arch['32bit'] = app.data.arch.get('64bit')
                app.data.sha256['32bit'] = app.data.sha256.get('64bit')
        return func(apps, *args_, **kwargs)

    return wrapper


@cli.command()
@apps_params
@click.option('-i', '--install', is_flag=True)
@click.option('-O', '--root')
@click.option('-s', '--generate-scripts', is_flag=True)
def download(apps, install, root, generate_scripts):
    DownloadApps(apps, root)
    for app in apps:
        if generate_scripts:
            if app.file:
                app.install_prepare(quiet=True)
                if os.name == 'nt':
                    script = app.file.parent / 'install.bat'
                    os.system(f'echo {app.command} >> {script}')
        if install:
            app.dry_run()


@cli.command()
@apps_params
@click.option('--dry-run', is_flag=True)
@click.option('-del', '--delete-downloaded', is_flag=True)
@click.option('--delete-installed', is_flag=True)
@click.option('-q', '--quiet', is_flag=True)
@click.option('-qq', '--veryquiet', is_flag=True)
@click.option('--args')
@click.option('--verify', is_flag=True)
@click.option('--force-verify', is_flag=True)
def install(apps, dry_run, delete_downloaded, delete_installed, quiet, veryquiet, args, verify, force_verify):
    print('By installing you accept licenses for the packages.\n')
    if veryquiet:
        quiet = True
    if dry_run:
        for app in apps:
            app.dry_run()
    else:
        DownloadApps(apps)
        for app in apps:
            app.install_prepare(args, quiet)
            app.install(veryquiet, verify, force_verify,
                        delete_downloaded, delete_installed)


@cli.command()
@apps_params
@click.option('-O', '--root')
@click.option('--with-ver', is_flag=True)
@click.option('--no-install', is_flag=True)
@click.option('-del', '--delete-downloaded', is_flag=True)
def extract(apps, no_install, with_ver, root, delete_downloaded):
    DownloadApps(apps)
    for app in apps:
        if not no_install:
            app.dry_run()
        app.extract(with_ver, root, delete_downloaded)


@cli.command()
@click.argument('packages', nargs=-1)
def remove(packages):
    packages = [pkg for pkg in packages]
    if packages:
        installed = [k.lower()
                     for k in list(GetConfig(filename='installed.json').keys())]
        for name in packages:
            if name.lower() in installed:
                if name not in installed:
                    name = name.lower()
                SetConfig(name, filename='installed.json', delete=True)
                print(f'{name} removed')
            else:
                logger.warning(f'cannot find {name}')
    else:
        print(remove.get_help(click.core.Context(remove)))
        return


@cli.command()
@click.argument('packages', nargs=-1)
@click.option('-o', '--outdated', '--upgradeable', is_flag=True)
@click.option('-e', '--extractable', is_flag=True)
@click.option('-i', '-l', '--installed', '--local', is_flag=True)
@click.option('show_all', '-A', '--all', is_flag=True)
@click.option('-p', '--pretty', '--pprint', is_flag=True)
def show(packages, outdated, installed, show_all, pretty, extractable):
    names = []
    if installed:
        iDict = GetConfig(filename='installed.json')
        names = sorted(list(iDict.keys()))
    if packages:
        if installed:
            for soft in Names2Softs(packages, softs=[{'name': n} for n in names]):
                name = soft['name']
                print(f'{name}|{iDict[name]}')
        else:
            pprint(sorted(Names2Softs(packages),
                          key=lambda x: x.get('name')), compact=True)
        return
    else:
        if extractable:
            names = sorted([soft['name'] for soft in GetSofts()
                            if soft.get('allowExtract') or soft.get('bin')])
        elif outdated:
            names = sorted(list(GetOutdated().keys()))
        elif show_all:
            names = sorted([soft['name'] for soft in GetSofts()])
    if pretty:
        pprint(names, compact=True)
    elif names:
        for name in names:
            print(name)
    else:
        print(show.get_help(click.core.Context(show)))


@cli.command()
@click.argument('name')
@click.argument('value', required=False)
@click.option('-d', '--delete', is_flag=True)
def alias(name, value, delete):
    Linking(name, value, delete)


@cli.command()
@click.argument('words', nargs=-1, required=True)
@click.option('-n', '--name-only', is_flag=True)
@click.option('pretty', '-pp', '--pprint', is_flag=True)
def search(words, name_only, pretty):
    words = [w.lower() for w in words]
    result = []
    for soft in GetSofts():
        if name_only:
            score = [1 for w in words if w in soft['name'].lower()]
        else:
            score = [1 for w in words if w in soft['name'].lower()
                     or w in soft.get('summary', '').lower()
                     or w in soft.get('description', '').lower()]
        if sum(score) == len(words):
            if pretty:
                result.append(soft['name'])
            else:
                print(soft['name'])
    if pretty:
        pprint(result, compact=True)


@cli.command()
@click.option('--save', is_flag=True)
@click.option('--diff', is_flag=True)
def local(save, diff):
    home = HOME / 'history/full'
    dt = datetime.now()
    if save:
        ts = int(dt.timestamp())
        current = GetConfig(filename='installed.json')
        SetConfig('data', current,
                  filename=f'{ts}.json', abspath=home)
    elif diff:
        fn_old = list(home.iterdir())[-1].name
        time_old = datetime.fromtimestamp(
            int(fn_old[:-5])).strftime('%Y-%m-%d %H:%M')
        print(f"{time_old}  ->  {dt.strftime('%Y-%m-%d %H:%M')}")
        old = GetConfig('data', filename=fn_old, abspath=home)
        current = GetConfig(filename='installed.json')
        changed = {k: v for k, v in old.items()
                   if v != current.get(k) and k in current}
        if changed:
            print(f'\nChanged:')
            for k, v in changed.items():
                print(f'  {k}:    \t{v} -> {current.get(k)}')
        added = [k for k in current.keys() if k not in old.keys()]
        if added:
            print(f'\nAdded:')
            for k in added:
                print(f'  {k}:    \t{current.get(k)}')
        removed = [k for k in old.keys() if k not in current.keys()]
        if removed:
            print(f'\nRemoved:')
            for k in removed:
                print(f'  {k}:    \t{old.get(k)}')
    else:
        print(local.get_help(click.core.Context(local)))


cli.add_command(cmd_doctor.doctor)


if __name__ == "__main__":
    cli()
