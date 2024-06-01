import ctypes
import os
from pathlib import Path, WindowsPath

import click

from .. import __version__
from ..app import ARCH, MACHINE, SYS
from ..config import GetConfig, SetConfig, HOME
from ..utils import Get7zPath, PreInstall, logger, test_cmd

REPOS = ['main', 'extras', 'scoop', 'winget',
         'main_linux', 'main_linux_deb', 'main_linux_arm', 'main_linux_arm_deb']

if SYS == 'Windows':
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


def add_to_hkcu_path(inp, test=True, force=False):
    # ref: https://stackoverflow.com/a/41379378
    # https://serverfault.com/questions/8855
    # https://stackoverflow.com/questions/21138014
    value = get_reg()[0]
    logger.info(f'old HKCU PATH value: {value}')
    value = value[:-1] if value.endswith(';') else value
    path = WindowsPath(inp)
    if not path.exists() and not force:
        logger.warning(f'{inp} not exists, returned.')
        return
    if str(path).rstrip('\\') in [p.rstrip('\\') for p in value.split(';')]:
        logger.warning(f'{inp} already added, returned.')
        return
    value += f';{str(path)}'
    logger.info(f'new HKCU PATH value: {value}')
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


def add_repo(repo_name, test=False):
    sources = GetConfig('sources', default=[])
    repo_url = f'https://github.com/mpkg-bot/mpkg-history/raw/master/{repo_name}.json'  # noqa: E501
    if repo_url not in sources:
        if test:
            return 'passed'
        sources += [repo_url]
    else:
        if test:
            return 'failed'
        logger.info(f'repo `{repo_name}` already in sources. ')
    SetConfig('sources', sources)


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


def print_repos(print_all=False):
    repos = guess_repos()
    if print_all:
        print(f'available repos: {repos}')
        return
    repos = [r for r in repos if add_repo(r, test=True) == 'passed']
    if repos:
        print()
        print(f'available repos: {repos}')
        print(' - usage: mpkg doctor -A name1 -A name2')


def print_data():
    bin_available = GetConfig('bin_dir') in os.environ.get('PATH')
    sevenzip_cmd = GetConfig('7z')
    download_dir = GetConfig('download_dir')
    print(f'mpkg version: {__version__}')
    print(f'SYS, MACHINE, ARCH: {SYS}, {MACHINE}, {ARCH}')
    print(f'\nbin_dir in PATH: {bin_available}')
    if not bin_available:
        print(' - try: mpkg doctor --fix-bin-env')
    print(f"\ndownload_dir: {download_dir}")
    if not Path(download_dir).exists:
        print(' - path not exists, try `mpkg doctor --reset-download-dir`')
    print(f"\n7z_command: {sevenzip_cmd}")
    if sevenzip_cmd.lstrip('"').startswith('7z_not_found'):
        print(
            ' - 7zip not found, try `mpkg doctor --fix-7z-path` if you have installed it')
        print(' - try `mpkg install 7zip` to install it')
    if SYS == 'Windows':
        print(f"\nshimexe: {GetConfig('shimexe')}")
        if not GetConfig('shimexe'):
            print(' - try: mpkg install shimexe_kiennq')
    print_repos()


@click.command()
@click.option('new_winpath', '--add-to-hkcu-path')
@click.option('force_winpath', '--add-to-hkcu-path-force')
@click.option('new_test_winpath', '--add-to-hkcu-path-test')
@click.option('repos', '-A', '--add-repo', multiple=True)
@click.option('print_all_repos', '--print-repos', is_flag=True)
@click.option('--fix-bin-env', is_flag=True)
@click.option('--fix-7z-path', is_flag=True)
@click.option('--reset-download-dir', is_flag=True)
def doctor(repos, print_all_repos, fix_bin_env, fix_7z_path, reset_download_dir,
           new_winpath, force_winpath, new_test_winpath):
    if not GetConfig('sources'):
        PreInstall()
    if repos:
        for repo in repos:
            add_repo(repo)
    elif fix_bin_env:
        bin_dir = GetConfig('bin_dir')
        if SYS == 'Windows':
            add_to_hkcu_path(bin_dir, test=False)
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
    elif reset_download_dir:
        print('resetting download_dir to default path, try `mpkg set download_dir --enable` to revert')
        if GetConfig('download_dir-disabled'):
            logger.error(
                'failed to reset, try `mpkg set --delete download_dir-disabled` first')
            return
        SetConfig('download_dir-disabled',
                  GetConfig('download_dir'), replace=False)
        SetConfig('download_dir', str(HOME / 'Downloads'), replace=True)
    elif new_test_winpath:
        add_to_hkcu_path(new_test_winpath)
    elif force_winpath:
        add_to_hkcu_path(force_winpath, test=False, force=True)
    elif new_winpath:
        add_to_hkcu_path(new_winpath, test=False)
    elif print_all_repos:
        print_repos(print_all=True)
    else:
        print_data()
