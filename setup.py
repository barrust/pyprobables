""" Module Installation script """
import io

import setuptools

from probables import (
    __author__,
    __bugtrack_url__,
    __email__,
    __license__,
    __url__,
    __version__,
)


def read_file(filepath):
    """ read the file """
    with io.open(filepath, "r") as filepointer:
        res = filepointer.read()
    return res


KEYWORDS = [
    "python",
    "probabilistic",
    "data-structure",
    "bloom",
    "filter",
    "count-min",
    "sketch",
    "bloom-filter",
    "count-min-sketch",
    "cuckoo-filter",
]

setuptools.setup(
    name="pyprobables",
    version=__version__,
    author=__author__,
    author_email=__email__,
    description="Probabilistic data structures in python",
    license=__license__,
    keywords=" ".join(KEYWORDS),
    url=__url__,
    download_url="{0}/tarball/v{1}".format(__url__, __version__),
    bugtrack_url=__bugtrack_url__,
    install_requires=read_file("requirements.txt").splitlines(),
    packages=setuptools.find_packages(include=["probables", "probables.*"]),
    long_description=read_file("README.rst"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "License :: OSI Approved",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    test_suite="tests",
)
