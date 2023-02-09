import ctypes
import os
from pathlib import Path, WindowsPath

import click

from .. import __version__
from ..app import ARCH, MACHINE, SYS
from ..config import GetConfig, SetConfig
from ..utils import Get7zPath, PreInstall, logger, test_cmd

REPOS = ['main', 'extras', 'scoop', 'winget',
         'main_linux', 'main_linux_deb', 'main_linux_arm', 'main_linux_arm_deb']

if ARCH == 'Windows':
    import winreg

    def get_reg(name='PATH', sub_key='Environment', key=winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(key, sub_key) as k:
                return winreg.QueryValueEx(k, name)
        except FileNotFoundError:
            return '', -1

    def set_reg(name, value, reg_type=winreg.REG_EXPAND_SZ, sub_key='Environment', key=winreg.HKEY_CURRENT_USER):
        with winreg.OpenKey(key, sub_key, 0, winreg.KEY_WRITE) as k:
            winreg.SetValueEx(k, name, 0, reg_type, value)


def add_to_hkcu_path(inp, test=True):
    # ref: https://stackoverflow.com/a/41379378
    # https://serverfault.com/questions/8855
    # https://stackoverflow.com/questions/21138014
    value = get_reg()[0]
    logger.debug(f'old HKCU PATH value: {value}')
    value = value[:-1] if value.endswith(';') else value
    path = WindowsPath(inp)
    if not path.exists():
        logger.warning(f'{inp} not exists')
    if str(path).rstrip('\\') in [p.rstrip('\\') for p in value.split(';')]:
        logger.warning(f'{inp} already added, returned.')
        return
    value += f';{str(path)}'
    logger.debug(f'new HKCU PATH value: {value}')
    if not test:
        set_reg('PATH', value)
        SendMessage = ctypes.windll.user32.SendMessageW
        SendMessage(0xFFFF, 0x1A, 0, 'Environment')
        logger.warning(
            f'{str(path)} added, please restart your terminal or computer.')
    else:
        logger.debug('Test passed.')


def add_to_bash_startup(inp, profile_path):
    filepath = Path(profile_path)
    script = f'\nif [ -d "{inp}" ] ; then PATH="$PATH:{inp}" ; fi # added by mpkg\n'
    if not filepath.exists():
        logger.warning(f'{profile_path} not exists')
    else:
        with open(filepath, 'r') as f:
            content = f.read()
        if script in content:
            logger.warning(f'{inp} already added to {profile_path}, returned.')
            return
    logger.warning(f'{inp} added, please restart your terminal or computer.')
    with open(filepath, 'a') as f:
        f = f.write(script)


def add_repo(repo_name):
    repos = GetConfig('sources', default=[])
    repos += [
        f'https://github.com/mpkg-bot/mpkg-history/raw/master/{repo_name}.json']
    SetConfig('sources', repos)


def guess_repos():
    repos = []
    if SYS == 'Windows':
        repos = ['main', 'extras', 'scoop', 'winget']
    elif SYS == 'Linux':
        if MACHINE.startswith('armv') or MACHINE.startswith('aarch') or MACHINE in ['arm', 'arm64']:
            repos += ['main_linux_arm']
            if test_cmd('apt --version') == 0:
                repos += ['main_linux_arm_deb']
        elif MACHINE in ['x86', 'i386', 'i686', 'x86_64', 'x64', 'amd64']:
            repos += ['main_linux']
            if test_cmd('apt --version') == 0:
                repos += ['main_linux_deb']
    return repos


def print_repos():
    repos = guess_repos()
    print(f'available repos: {repos}')
    print(' - usage: mpkg doctor --add-repo repo_name')


def print_data():
    bin_available = GetConfig('bin_dir') in os.environ.get('PATH')
    sevenzip_cmd = GetConfig('7z')
    print(f'mpkg version: {__version__}')
    print(f'SYS, MACHINE, ARCH: {SYS}, {MACHINE}, {ARCH}')
    print(f'\nbin_dir in PATH: {bin_available}')
    if not bin_available:
        print(' - try: mpkg doctor --fix-bin-env')
    print(f"\n7z_command: {sevenzip_cmd}")
    if sevenzip_cmd.lstrip('"').startswith('7z_not_found'):
        print(
            ' - 7zip not found, try `mpkg doctor --fix-7z-path` if you have installed it')
        print(' - try `mpkg install 7zip` to install it')
    if SYS == 'Windows':
        print(f"\nshimexe: {GetConfig('shimexe')}")
        if not GetConfig('shimexe'):
            print(' - try: mpkg install shimexe_kiennq')
    print()
    print_repos()


@click.command()
@click.option('new_winpath', '--add-to-hkcu-path')
@click.option('new_test_winpath', '--add-to-hkcu-path-test')
@click.option('repo', '--add-repo')
@click.option('--fix-bin-env', is_flag=True)
@click.option('--fix-7z-path', is_flag=True)
def doctor(repo, fix_bin_env, fix_7z_path, new_winpath, new_test_winpath):
    if not GetConfig('sources'):
        PreInstall()
    if repo:
        add_repo(repo)
    elif fix_bin_env:
        bin_dir = GetConfig('bin_dir')
        if SYS == 'Windows':
            add_to_hkcu_path(bin_dir)
        elif SYS == 'Linux':
            for filepath in [Path.home()/fn for fn in ['.profile', '.bashrc']]:
                if not filepath.exists():
                    filepath.touch()
            for filepath in [Path.home()/fn for fn in ['.profile', '.bash_profile', '.bash_login', '.bashrc']]:
                if filepath.exists():
                    add_to_bash_startup(bin_dir, filepath)
    elif fix_7z_path:
        SetConfig('7z', f'"{Get7zPath()}"' +
                  r' x {filepath} -o{root} -aoa > '+os.devnull)
    elif new_test_winpath:
        add_to_hkcu_path(new_test_winpath)
    elif new_winpath:
        add_to_hkcu_path(new_winpath, test=False)
    else:
        print_data()
