#!/usr/bin/env python3
# coding: utf-8

import gettext
from multiprocessing.dummy import Pool
from pprint import pformat, pprint

import click

from .config import GetConfig, SetConfig
from .load import Load
from .utils import Selected

_ = gettext.gettext


def prepare(soft):
    soft.prepare()


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
    SOFTS = []
    for item in GetConfig('sources'):
        SOFTS += Load(item, sync=sync)
    if all:
        soft_list = SOFTS
    else:
        soft_list = Selected(SOFTS, isSoft=True)

    with Pool(jobs) as p:
        p.map(prepare, soft_list)

    for soft in soft_list:
        pprint(soft.data)

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
        SetConfig('downloader', 'wget -O "{file}" "{url}"')
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
