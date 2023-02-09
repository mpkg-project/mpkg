import os

from setuptools import setup

from mpkg import __version__

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), 'rb') as f:
    readme = f.read().decode('utf-8')

setup(
    name="mpkg",
    version=__version__,
    author="zpcc",
    author_email="zp.c@outlook.com",
    description="A simple package manager.",
    long_description=readme,
    long_description_content_type='text/markdown',
    url="https://github.com/mpkg-project/mpkg",
    packages=["mpkg", "mpkg.commands"],
    python_requires=">=3.7",
    install_requires=[
        "lxml>=4.5.0",
        "beautifulsoup4>=4.6.3",
        "requests>=2.23.0",
        "click>=7.0.0",
        "loguru>=0.5.1",
        "tenacity>=6.0.0",
        "semver>=2.8.0",
        "pyyaml>=5.3.1",
    ],
    entry_points={
        "console_scripts": [
            "mpkg=mpkg.cli:cli",
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        'License :: OSI Approved :: Apache Software License',
    ],
)
