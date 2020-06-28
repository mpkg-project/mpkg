from setuptools import setup

setup(
    name="mpkg",
    version="0.0.1",
    author="zpcc",
    author_email="zp.c@outlook.com",
    description="A simple package manager.",
    url="https://github.com/mpkg-project/mpkg",
    packages=["mpkg"],
    python_requires=">=3.7",
    install_requires=[
        "lxml>=4.5.0",
        "requests>=2.23.0",
    ],
    entry_points={
        "console_scripts": [
            "mpkg=mpkg.mpkg:main",
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        'License :: OSI Approved :: Apache Software License',
    ],
)
