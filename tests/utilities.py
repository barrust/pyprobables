''' utility functions '''
from hashlib import (md5)


def calc_file_md5(filename):
    with open(filename, 'rb') as filepointer:
        res = filepointer.read()
    return md5(res).hexdigest()
