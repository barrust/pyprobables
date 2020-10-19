""" utility functions """
from hashlib import md5


def calc_file_md5(filename):
    """ calc the md5 of a file """
    with open(filename, "rb") as filepointer:
        res = filepointer.read()
    return md5(res).hexdigest()


def different_hash(key, depth):
    """ the default fnv-1a hashing routine, but different """

    def __fnv_1a(key):
        """ 64 bit fnv-1a hash """
        hval = 14695981039346656074  # made minor change
        fnv_64_prime = 1099511628211
        uint64_max = 2 ** 64
        for tmp_s in key:
            hval = hval ^ ord(tmp_s)
            hval = (hval * fnv_64_prime) % uint64_max
        return hval

    res = list()
    tmp = key
    for _ in list(range(0, depth)):
        if tmp != key:
            tmp = __fnv_1a("{0:x}".format(tmp))
        else:
            tmp = __fnv_1a(key)
        res.append(tmp)
    return res
