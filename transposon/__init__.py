
"""
Sundry helper functions.
"""


import errno
from functools import partial
from os import sysconf, strerror
import h5py

MAX_SYSTEM_RAM_GB = sysconf('SC_PAGE_SIZE') * sysconf('SC_PHYS_PAGES')/(1024.**3)
FILE_DNE = partial(FileNotFoundError, errno.ENOENT, strerror(errno.ENOENT))


def check_ram(ram_bytes, logger):
    """Raise if the requested RAM is negative or greater than the system."""

    if ram_bytes < 0:
        logger.critical("cache %i bytes < 0" % ram_bytes)
        raise ValueError()
    elif ram_bytes/(1024.**3) > MAX_SYSTEM_RAM_GB:
        ram_gb = ram_bytes/(1024.**3)
        msg = "cache %i GB > system %i GB" % ram_gb
        logger.critical(msg)
        raise ValueError(msg)


def write_vlen_str_h5py(h5file, strings, dataset_key):
    """Write to an H5 File an iterable of variable length unicode.

    Args:
        h5file(h5py.File): opened destination file
        strings(iterable(str)): string list
        dataset_key(str): name of data set to write
    """

    vlen = h5py.special_dtype(vlen=str)
    n_strings = sum(1 for s in strings)
    dset = h5file.create_dataset(
        dataset_key, (n_strings,), dtype=vlen)
    dset[:] = strings


def read_vlen_str_h5py(h5file, dataset_key):
    """Read from an H5 File an iterable of variable length unicode.

    Args:
        h5ile(h5py.File): opened source file
        dataset_key(str): name of data set to read
    """

    return h5file[dataset_key][:].tolist()
