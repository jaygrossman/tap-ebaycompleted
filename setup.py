#!/usr/bin/env python
from setuptools import setup

setup(
    name="tap-ebaycompleted",
    version="0.1.0",
    description="Singer.io tap for extracting data",
    author="Stitch",
    url="http://singer.io",
    classifiers=["Programming Language :: Python :: 3 :: Only"],
    py_modules=["tap_ebaycompleted"],
    install_requires=[
        # NB: Pin these to a more specific version for tap reliability
        "singer-python",
        "requests",
    ],
    entry_points="""
    [console_scripts]
    tap-ebaycompleted=tap_ebaycompleted:main
    """,
    packages=["tap_ebaycompleted"],
    package_data = {
        "schemas": ["tap_ebaycompleted/schemas/*.json"]
    },
    include_package_data=True,
    disable_collection=True,
)
