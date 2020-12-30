""" Update all the different version variables
"""
import os


def update_file(path, k, v):
    """Parse a file based on the key (k) and update it's value with the
    provided value (v)

    Args:
        path (str):
        k (str):
        v (str):
    """
    with open(path, "r") as fobj:
        data = fobj.readlines()
    for i, line in enumerate(data):
        if line.startswith(k):
            data[i] = """{} = "{}"\n""".format(k, v)
    with open(path, "w") as fobj:
        fobj.writelines(data)


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
    update_file(pyproject, "version", args.new_version)

    # update the package __init__ file
    init_file = "{}/probables/__init__.py".format(module_path)
    update_file(init_file, "__version__", args.new_version)
