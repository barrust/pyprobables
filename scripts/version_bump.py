""" Update all the different version variables
"""
import os
from datetime import datetime
from functools import wraps


def read_and_write(func):
    @wraps(func)
    def wrapper(**kwargs):
        path = kwargs["path"]

        with open(path, "r") as fobj:
            data = fobj.readlines()

        func(data, **kwargs)

        with open(path, "w") as fobj:
            fobj.writelines(data)

    return wrapper


@read_and_write
def update_file(data, **kwargs):
    """Parse a file based on the key (k) and update it's value with the provided value (v)

    Args:
        path (str):
        k (str):
        v (str):
    """
    for i, line in enumerate(data):
        if line.startswith(kwargs["k"]):
            data[i] = """{} = "{}"\n""".format(kwargs["k"], kwargs["v"])


@read_and_write
def update_citation_file(data, **kwargs):
    """Parse the citation file and update it's values with the provide file

    Args:
        path (str):
        v (str):
    """
    for i, line in enumerate(data):
        if line.startswith("version:"):
            data[i] = "version: {}\n".format(kwargs["v"])
        if line.startswith("date-released:"):
            data[i] = "date-released: '{}'".format(datetime.today().strftime("%Y-%m-%d"))


def _parse_args():
    import argparse

    parser = argparse.ArgumentParser(description="Automate the version bump of the pyprobables project")
    parser.add_argument("new_version", help="The new version of the package")

    return parser.parse_args()


if __name__ == "__main__":

    args = _parse_args()

    # get current path to find where the script is currently
    script_path = os.path.dirname(os.path.abspath(__file__))

    module_path = os.path.abspath("{}/../".format(script_path))

    # update pyproject.toml
    pyproject = "{}/pyproject.toml".format(module_path)
    update_file(path=pyproject, k="version", v=args.new_version)

    # update the package __init__ file
    init_file = "{}/probables/__init__.py".format(module_path)
    update_file(path=init_file, k="__version__", v=args.new_version)

    # update the citation file
    citation_file = "{}/CITATION.cff".format(module_path)
    update_citation_file(path=citation_file, v=args.new_version)
