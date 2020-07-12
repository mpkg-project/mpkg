#!/usr/bin/env python3
# coding: utf-8

import gettext
import json

from .config import GetConfig, SetConfig
from .utils import Download, Selected, ToLink

_ = gettext.gettext


class Soft(object):
    cfg = 'config.json'
    api = 1
    DefaultList, DefaultStr, DefaultDict = [], '', {}
    isMultiple = False
    allowExtract = False
    isPrepared = False
    needConfig = False
    ID = ''
    SilentArgs = ''
    Description = ''

    def __init__(self):
        self.rem = self.getconfig('rem')
        name = self.getconfig('name')
        if self.isMultiple:
            self.needConfig = True
        if name:
            self.name = name
        else:
            self.name = self.ID
        self.ver,  self.links, self.link = self.DefaultStr, self.DefaultList, self.DefaultDict
        self.date, self.log = self.DefaultList, self.DefaultStr

    def _prepare(self):
        pass

    def config(self):
        print(_('\n configuring {0} (press enter to pass)').format(self.ID))
        self.setconfig('name')
        self.setconfig('rem')

    def setconfig(self, key, value=False):
        if value == False:
            value = input(_('input {key}: '.format(key=key)))
        SetConfig(key, value, path=self.ID, filename=self.cfg)

    def getconfig(self, key):
        return GetConfig(key, path=self.ID, filename=self.cfg)

    def json(self) -> bytes:
        if not self.isPrepared:
            self.prepare()
        return json.dumps(self.data).encode('utf-8')

    def prepare(self):
        self.isPrepared = True
        self._prepare()
        data = {}
        data['id'] = self.ID
        data['ver'] = self.ver
        if self.links != self.DefaultList:
            data['links'] = self.links
        if self.link != self.DefaultDict:
            data['link'] = self.link
        if self.date != self.DefaultList:
            data['date'] = self.date
        if self.name != self.ID:
            data['name'] = self.name
        if self.isMultiple:
            data['cfg'] = self.cfg
        if self.SilentArgs:
            data['args'] = self.SilentArgs
        if self.rem:
            data['rem'] = self.rem
        if self.log:
            data['changelog'] = self.log
        if self.Description:
            data['description'] = self.Description
        self.data = {'packages': [data]}
        self.data['api'] = self.api


class Driver(Soft):
    needConfig = True

    def __init__(self):
        super().__init__()
        self.url = self.getconfig('url')

    def config(self):
        super().config()
        self.setconfig('url', input(_('input your url(required): ')))
