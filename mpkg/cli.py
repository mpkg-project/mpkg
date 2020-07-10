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


@click.group()
def cli():
    pass


@cli.command()
@click.option('-j', '--jobs', default=10, help=_('threads'))
@click.option('--bydate', is_flag=True, help=_('check outdated packages by ver and date'))
@click.option('--sync/--no-sync', default=True, help=_('sync source files'))
# @click.option('-i', '--install', default=False, help=_('install packages'))
def sync(jobs, bydate, sync):
    softs = GetSofts(jobs, sync, use_cache=False)
    pprint(softs)

    '''soft_list = [soft for soft in soft_list if not soft.isLatest]

    if download:
        for soft in soft_list:
            soft.download()'''


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


@cli.command()
@click.argument('package')
@click.option('-d', '--download', is_flag=True)
@click.option('-o', '--outdated', is_flag=True)
@click.option('--dry-run', is_flag=True)
def install(package, download, outdated, dry_run):
    softs = GetSofts()
    if package:
        softs = [x for x in softs if x['name'] == package]
    elif outdated:
        pass
    for soft in softs:
        if not soft.get('link'):
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


@cli.command('list')
@click.argument('package', required=False)
@click.option('-o', '--outdated', is_flag=True)
@click.option('--bydate', is_flag=True, help=_('check outdated packages by ver and date'))
@click.option('-i', '--installed', is_flag=True)
def list_(package, outdated, installed, bydate):
    softs = GetSofts()
    if installed:
        pkgs = GetConfig(filename='installed.json')
        pprint(list(pkgs.keys()))
    elif outdated:
        pprint(GetOutdated(bydate))
    elif package:
        pprint([x for x in softs if x['name'] == package])
    else:
        pprint([x['name'] for x in softs])


if __name__ == "__main__":
    cli()
