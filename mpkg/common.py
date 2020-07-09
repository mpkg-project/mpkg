#!/usr/bin/env python3
# coding: utf-8

import gettext
import json
from typing import List, Tuple

from .config import GetConfig, SetConfig
from .utils import Download, Selected

_ = gettext.gettext


class Soft(object):
    id = 'Soft'
    silentArgs = ''
    cfg = 'config.json'
    isMultiple = False
    allowExtract = False
    isPrepared = False
    needConfig = False
    DefaultList = [-1, -1, -1]
    DefaultLog = ''

    def __init__(self):
        self.rem = self.getconfig('rem')
        name = self.getconfig('name')
        if self.isMultiple:
            self.needConfig = True
        if name:
            self.name = name
        else:
            self.name = self.id

    def _parse(self) -> Tuple[List[int], List[int], List[str], str]:
        return self.DefaultList, self.DefaultList, ['url'], self.DefaultLog

    def config(self):
        print(_('\n configuring {0} (press enter to pass)').format(self.id))
        self.setconfig('name')
        self.setconfig('rem')

    def setconfig(self, key, value=False):
        if value == False:
            value = input(_('input {key}: '.format(key=key)))
        SetConfig(key, value, path=self.id, filename=self.cfg)

    def getconfig(self, key):
        return GetConfig(key, path=self.id, filename=self.cfg)

    def json(self) -> bytes:
        if not self.isPrepared:
            self.prepare()
        return json.dumps(self.data).encode('utf-8')

    def selectlink(self):
        if len(self.links) != 1:
            self.link = Selected(self.links, msg=_('select a link:'))[0]
        else:
            self.link = self.links[0]

    def prepare(self):
        self.isPrepared = True
        self.ver, self.date, self.links, self.log = self._parse()
        data = {}
        data['id'] = self.id
        data['ver'] = self.ver
        data['links'] = self.links
        if self.date != self.DefaultList:
            data['date'] = self.date
        if self.rem:
            data['rem'] = self.rem
        if self.log:
            data['changelog'] = self.log
        if self.name:
            data['name'] = self.name
        self.data = {'packages': [data]}


class Driver(Soft):
    needConfig = True

    def __init__(self):
        super().__init__()
        self.url = self.getconfig('url')

    def config(self):
        super().config()
        self.setconfig('url', input(_('input your url(required): ')))
