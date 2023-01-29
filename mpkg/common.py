#!/usr/bin/env python3
# coding: utf-8

import gettext
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .config import GetConfig, SetConfig

_ = gettext.gettext


def env_rpl(text, key, func):
    groups = text.split(f'%{key}:')
    if len(groups) == 0:
        return text
    else:
        for name in [t.split('%')[0] for t in groups[1:]]:
            text = text.replace(f'%{key}:{name}%', func(name))
        return text


@dataclass
class arch_data:
    links: List[str] = field(default_factory=list)
    sha256: List[str] = field(default_factory=list)
    bin: List[str] = field(default_factory=list)
    shortcuts: List[str] = field(default_factory=list)
    pre_install: List[str] = field(default_factory=list)
    post_install: List[str] = field(default_factory=list)

    def format(self):
        for i, v in enumerate(self.links):
            self.links[i] = v.format(ver=self.ver)
        for i, v in enumerate(self.pre_install):
            v = env_rpl(v, 'MPKG', GetConfig)
            self.pre_install[i] = env_rpl(v, 'ENV', os.getenv)
        for i, v in enumerate(self.post_install):
            v = env_rpl(v, 'MPKG', GetConfig)
            self.post_install[i] = env_rpl(v, 'ENV', os.getenv)

    def asdict(self, simplify=False):
        if simplify:
            return dict([(k, v) for k, v in asdict(self).items() if v])
        else:
            return asdict(self)


def dicts_to_dataclasses(instance):
    """See also: https://stackoverflow.com/q/51564841"""
    if not isinstance(instance.info, arch_data):
        instance.info = arch_data(**instance.info)
    for k, v in instance.arch_.items():
        if not isinstance(v, arch_data):
            instance.arch_[k] = arch_data(**v)


def get_bits(text):
    return {'32bit': '32bit', '64bit': '64bit',
            '386': '32bit', 'i386': '32bit', 'i686': '32bit', 'x86': '32bit',
            'amd64': '64bit', 'x86_64': '64bit',
            'arm': '32bit',  'armhf': '32bit',
            'arm6': '32bit', 'armv6': '32bit', 'arm-v6': '32bit',
            'arm7': '32bit', 'armv7': '32bit', 'arm-v7': '32bit',
            'arm64': '64bit'}[text]


@dataclass
class soft_data:
    id: str = ''
    license: str = ''
    categories: List[str] = field(default_factory=list)
    cfg: str = ''
    name: str = ''
    ver: str = ''
    ver_code: int = 0
    date: str = ''
    notes: str = ''
    info: arch_data = field(default_factory=arch_data)
    arch: Dict = field(default_factory=dict)
    arch_: Dict[str, arch_data] = field(default_factory=dict)
    sha256: Any = field(default_factory=dict)
    links: List[str] = field(default_factory=list)
    changelog: str = ''
    args: str = ''
    bin: Any = field(default_factory=dict)
    depends: List = field(default_factory=list)
    cmd: Dict = field(default_factory=dict)
    valid: List = field(default_factory=list)
    summary: str = ''
    description: str = ''
    homepage: str = ''
    src: str = ''
    bugs: str = ''
    i18n: str = ''
    build_log: str = ''
    build_meta: str = ''
    mpkg_src: str = ''
    mpkg_bugs: str = ''
    allowExtract: bool = False

    def __post_init__(self):
        dicts_to_dataclasses(self)

    def format(self):
        for k, v in self.arch.items():
            if not isinstance(v, list):
                self.arch[k] = v.format(ver=self.ver)
            else:
                for i, v_ in enumerate(v):
                    self.arch[k][i] = v_.format(ver=self.ver)
        for i, v in enumerate(self.links):
            self.links[i] = v.format(ver=self.ver)
        for k, v in self.cmd.items():
            v = env_rpl(v, 'MPKG', GetConfig)
            self.cmd[k] = env_rpl(v, 'MPKG', GetConfig)
        self.info.format()
        for k, v in self.arch_.items():
            v.format()

    def asdict(self, simplify=False):
        if simplify:
            D = dict([(k, v) for k, v in asdict(self).items() if v])
            D['info'] = self.info.asdict(simplify=True)
            if not D['info']:
                del D['info']
            if self.arch_:
                D['arch_'] = {}
                for k, v in self.arch_.items():
                    D['arch_'][k] = v.asdict(simplify=True)
            return D
        else:
            return asdict(self)

    def copyfrom(self, sdata):
        src_dict = sdata.asdict()
        new_dict = self.asdict()
        for k, v in new_dict.items():
            if not v:
                new_dict[k] = src_dict[k]
        return soft_data(**new_dict)

    def create_new(self, arch: dict, sha256='', bin=''):
        sdata = soft_data()
        for k, url in arch.items():
            bits = get_bits(k)
            sdata.arch[bits] = url
            if sha256:
                sdata.sha256[bits] = sha256.get(k)
            if bin:
                sdata.bin = bin
        return sdata.copyfrom(self)


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

    def check(self):
        for p in self.json_data['packages']:
            if not p.get('ver'):
                print(self.json_data)
                raise AssertionError('ver is not defined')

    def json(self) -> bytes:
        if not self.isPrepared:
            self.prepare()
        return json.dumps(self.json_data).encode('utf-8')

    def append_arch(self, tag_list: list, soft_data: soft_data):
        id_pre = 'MPKG-ARCH|'+'_'.join(tag_list)+'|'
        soft_data.id = id_pre+self.ID
        self.packages.append(soft_data.asdict(simplify=True))
        self.json_data = {'packages': self.packages}
        self.check()

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
        self.check()

    def cfg2json(self):
        self.__init__()
        return dict([(k, v) for k, v in GetConfig(path=self.ID, filename=self.cfg, default={}).items() if v])


class Driver(Soft):
    needConfig = True

    def __init__(self):
        super().__init__()
        self.url = self.getconfig('url')

    def config(self):
        super().config()
        self.setconfig('url', input(_('input your url(required): ')))
