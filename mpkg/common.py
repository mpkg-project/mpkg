#!/usr/bin/env python3
# coding: utf-8

import gettext
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .config import GetConfig, SetConfig

_ = gettext.gettext


@dataclass
class soft_data:
    id: str = ''
    cfg: str = ''
    name: str = ''
    ver: str = ''
    date: str = ''
    notes: str = ''
    arch: Dict = field(default_factory=dict)
    sha256: Any = field(default_factory=dict)
    links: List = field(default_factory=list)
    changelog: str = ''
    args: str = ''
    bin: Any = field(default_factory=dict)
    depends: List = field(default_factory=list)
    cmd: Dict = field(default_factory=dict)
    valid: List = field(default_factory=list)
    description: str = ''
    homepage: str = ''
    allowExtract: bool = False

    def asdict(self, simplify=False):
        if simplify:
            return dict([(k, v) for k, v in asdict(self).items() if v])
        else:
            return asdict(self)


class Soft(object):
    api = 1
    cfg = 'config.json'
    isMultiple = False
    allowExtract = False
    isPrepared = False
    needConfig = False
    ID = ''

    def __init__(self):
        self.data = soft_data()
        self.notes = self.getconfig('notes')
        name = self.getconfig('name')
        if self.isMultiple:
            self.needConfig = True
        if name:
            self.name = name
        else:
            self.name = self.ID

    def _prepare(self):
        pass

    def config(self):
        print(_('\n configuring {0} (press enter to pass)').format(self.ID))
        self.setconfig('name')
        self.setconfig('notes')

    def setconfig(self, key, value=False):
        if value == False:
            value = input(_('input {key}: '.format(key=key)))
        SetConfig(key, value, path=self.ID, filename=self.cfg)

    def getconfig(self, key):
        return GetConfig(key, path=self.ID, filename=self.cfg)

    def json(self) -> bytes:
        if not self.isPrepared:
            self.prepare()
        return json.dumps(self.json_data).encode('utf-8')

    def prepare(self):
        self.isPrepared = True
        self.packages = []
        self._prepare()
        soft = self.data
        soft.id = self.ID
        if self.allowExtract:
            soft.allowExtract = True
        if self.name != self.ID:
            soft.name = self.name
        if self.isMultiple:
            soft.cfg = self.cfg
        self.packages.append(soft.asdict(simplify=True))
        self.json_data = {'packages': self.packages}
        self.json_data['api'] = self.api


class Driver(Soft):
    needConfig = True

    def __init__(self):
        super().__init__()
        self.url = self.getconfig('url')

    def config(self):
        super().config()
        self.setconfig('url', input(_('input your url(required): ')))
