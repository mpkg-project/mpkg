#!/usr/bin/env python3
# coding: utf-8

import gettext
import json
from typing import List, Tuple

from mpkg.utils import Download, GetConfig, Selected, SetConfig

DefaultList = [-1, -1, -1]
DefaultLog = ''

_ = gettext.gettext


class Soft(object):
    id = 'Soft'
    allowExtract = False
    isPrepared = False
    needConfig = False
    DefaultList = [-1, -1, -1]
    DefaultLog = ''

    def __init__(self, name='', rem=''):
        name_ = GetConfig('name', path=self.id)
        rem_ = GetConfig('rem', path=self.id)
        if name:
            self.name = name
        elif name_:
            self.name = name_
        else:
            self.name = self.id
        if rem:
            self.rem = rem
        else:
            self.rem = rem_

    @staticmethod
    def config(id):
        print(_('\n configuring {0} (press enter to skip)').format(id))
        SetConfig('name', input(_('input name: ')), path=id)
        SetConfig('rem', input(_('input rem: ')), path=id)

    def _parse(self) -> Tuple[List[int], List[int], List[str], str]:
        return self.DefaultList, self.DefaultList, ['url'], self.DefaultLog

    def json(self) -> bytes:
        if not self.isPrepared:
            self.prepare()
        return json.dumps(self.data).encode('utf-8')

    def download(self):
        # -v print(_('使用缺省下载方案'))
        if len(self.links) != 1:
            link = Selected(self.links, msg=_('select a url:'))[0]
        else:
            link = self.links[0]
        Download(link)

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
        self.data = data
