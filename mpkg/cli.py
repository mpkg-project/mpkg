#!/usr/bin/env python3
# coding: utf-8

import gettext
from pprint import pformat, pprint

import click

from .config import GetConfig, SetConfig
from .load import GetSofts, Load
from .utils import Selected

_ = gettext.gettext


@click.group()
def cli():
    pass


@cli.command()
@click.option('-j', '--jobs', default=10, help=_('threads'))
@click.option('-d', '--download', is_flag=True)
@click.option('--all', is_flag=True, help=_('check all packages'))
@click.option('--bydate', is_flag=True, help=_('check version by date'))
@click.option('--sync/--no-sync', default=True)
# @click.option('-v', default=False, help=_('show all packages'))
# @click.option('-i', '--install', default=False, help=_('install packages'))
def check(jobs, download, all, bydate, sync):
    SOFTS = GetSofts(jobs, sync)
    pprint(SOFTS)

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
        SetConfig('downloader', 'wget -q -O "{file}" "{url}"')
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
# @click.argument('package')
# database
def install():
    pass


if __name__ == "__main__":
    cli()
