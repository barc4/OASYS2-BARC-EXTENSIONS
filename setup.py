#! /usr/bin/env python3

# coding: utf-8

import os
from setuptools import find_packages, setup

NAME = "OASYS2-BARC-EXTENSIONS"
VERSION = "0.0.1"

DESCRIPTION = "OASYS2 BARC extension widgets"
README_FILE = os.path.join(os.path.dirname(__file__), "README.md")
LONG_DESCRIPTION = open(README_FILE, encoding="utf-8").read()
AUTHOR = "BARC"
AUTHOR_EMAIL = ""
URL = "https://github.com/barc4/OASYS2-BARC-EXTENSIONS"
DOWNLOAD_URL = URL
LICENSE = "CeCILL Free Software License Agreement v2.1"

KEYWORDS = [
    "ray tracing",
    "x-ray optics",
    "oasys2",
    "shadow4",
]

CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "Environment :: X11 Applications :: Qt",
    "Environment :: Plugins",
    "Programming Language :: Python :: 3",
    "Intended Audience :: Science/Research",
]

INSTALL_REQUIRES = (
    "oasys2>=0.0.42",
    "OASYS2-SHADOW4>=0.0.44",
    "shadow4>=0.1.84",
    "barc4beams",
    "barc4shadow",
)

PACKAGES = find_packages(exclude=("*.tests", "*.tests.*", "tests.*", "tests"))

PACKAGE_DATA = {
    "orangecontrib.barc.oasys.widgets.extension": [
        "icons/*.png",
        "icons/*.jpg",
        "icons/*.svg",
    ],
    "orangecontrib.barc.shadow4.widgets.extension": [
        "icons/*.png",
        "icons/*.jpg",
        "icons/*.svg",
    ],
}

ENTRY_POINTS = {
    "oasys2.addons": (
        "BARC = orangecontrib.barc",
    ),
    "oasys2.widgets": (
        "BARC Shadow4 = orangecontrib.barc.shadow4.widgets.extension",
    ),
}


if __name__ == "__main__":
    setup(
        name=NAME,
        version=VERSION,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type="text/markdown",
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        url=URL,
        download_url=DOWNLOAD_URL,
        license=LICENSE,
        keywords=KEYWORDS,
        classifiers=CLASSIFIERS,
        packages=PACKAGES,
        package_data=PACKAGE_DATA,
        install_requires=INSTALL_REQUIRES,
        entry_points=ENTRY_POINTS,
        include_package_data=True,
        zip_safe=False,
    )
