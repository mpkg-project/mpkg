#!/usr/bin/env python3
# coding: utf-8

import gettext
import os
from platform import architecture
from pprint import pformat, pprint

import click

from .common import Soft
from .config import HOME, GetConfig, SetConfig
from .load import GetSofts, Load
from .utils import Download, GetOutdated, Selected, ToLink

_ = gettext.gettext
arch = architecture()[0]


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def cli():
    pass


@cli.command()
@click.option('-j', '--jobs', default=10, help=_('threads'))
@click.option('--sync/--no-sync', default=True, help=_('sync source files'))
def sync(jobs, sync):
    softs = GetSofts(jobs, sync, use_cache=False)
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
            if soft.get('changelog'):
                print(f' changelog: {soft["changelog"]}')


@cli.command()
@click.option('-f', '--force', is_flag=True)
@click.option('--load/--no-load', default=True)
def config(force, load):
    if not force and GetConfig('sources'):
        print(_('pass'))
    else:
        SetConfig('downloader', 'wget -q -O "{filepath}" "{url}"')
        SetConfig('download_dir', str(HOME))
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


def set_():
    pass


@click.argument('packages', nargs=-1)
@click.option('-d', '--download', is_flag=True)
@click.option('-o', '--outdated', is_flag=True)
@click.option('--dry-run', is_flag=True)
def install(packages, download, outdated, dry_run):
    packages = [pkg.lower() for pkg in packages]
    softs_all = GetSofts()
    if packages:
        softs = [x for x in softs_all if x['name'].lower() in packages]
    elif outdated:
        softs = [x for x in softs_all if x['name']
                 in list(GetOutdated().keys())]
    else:
        print(install.get_help(click.core.Context(install)))
        return
    for soft in softs:
        if not soft.get('link') and not dry_run:
            soft['link'] = ToLink(soft['links'])
        if not soft.get('date'):
            soft['date'] = Soft.DefaultList
        if not soft.get('args'):
            soft['args'] = Soft.SilentArgs
    for soft in softs:
        SetConfig(soft['name'], [soft['ver'], soft['date']],
                  filename='installed.json')
        if dry_run:
            return
        file = Download(soft['link'][arch],
                        directory=GetConfig('download_dir'))
        command = str(file)+' '+soft['args']
        if download:
            if os.name == 'nt':
                script = file.parent / 'install.bat'
                os.system(f'echo {command} >> {script}')
        else:
            os.system(command)


@cli.command()
@click.argument('packages', nargs=-1)
def remove(packages):
    packages = [pkg.lower() for pkg in packages]
    softs_all = GetSofts()
    if packages:
        softs = [x for x in softs_all if x['name'].lower() in packages]
        for soft in softs:
            SetConfig(soft['name'], filename='installed.json', delete=True)
    else:
        print(remove.get_help(click.core.Context(remove)))
        return


@cli.command('list')
@click.argument('packages', nargs=-1)
@click.option('-o', '--outdated', is_flag=True)
@click.option('-i', '--installed', is_flag=True)
def list_(packages, outdated, installed):
    packages = [pkg.lower() for pkg in packages]
    softs = GetSofts()
    if installed:
        pkgs = GetConfig(filename='installed.json')
        pprint(list(pkgs.keys()))
    elif outdated:
        pprint(list(GetOutdated().keys()))
    elif packages:
        pprint([x for x in softs if x['name'].lower() in packages])
    else:
        pprint([x['name'] for x in softs])


if __name__ == "__main__":
    cli()
