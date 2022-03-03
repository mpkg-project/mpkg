from typing import List

import semver


def parse_version(version: str):
    return semver.VersionInfo.parse(version)


def is_semver(version: str, ambiguous=False) -> bool:
    if ambiguous:
        try:
            semver.VersionInfo.parse(version)
            return True
        except ValueError:
            return False
    else:
        for char in version:
            if char not in "0123456789.-+":
                return False
        return True


def get_max_version(versions: List[str], is_semver=True) -> str:
    # example: 2.0.0-dev.15+2011262249.19338c93, 6.3.5-Release.11178701
    # V1.10 - Rev. 62712, 21.03 ZS v1.5.0 R2
    # 0.14.0-pre2, MPS-213.6777.846, stable-3.5.6-1eb645590
    # 10 2020-q4-major, 1.8 (build 814) stable
    if is_semver:
        return max(versions, key=semver.VersionInfo.parse)
    else:
        L = []
        for text in versions:
            result = ''
            for char in text:
                result += char if char.isdigit() else '.'
            while '..' in result:
                result = result.replace('..', '.')
            if result.startswith('.'):
                result = result[1:]
            if result.endswith('.'):
                result = result[:-1]
            L.append(result if result else '-1')
        value = max(L, key=lambda x: tuple(map(int, x.split('.'))))
        return versions[L.index(value)]
