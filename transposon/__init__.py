"""
Sundry helper functions.
"""

# FUTURE according to best practices, move all this to it's own utils namespace?

import logging
import errno
from functools import partial
from os import sysconf, strerror
import h5py
import os
import numexpr  # used by numpy

MAX_SYSTEM_RAM_GB = sysconf("SC_PAGE_SIZE") * sysconf("SC_PHYS_PAGES") / (1024.0 ** 3)
FILE_DNE = partial(FileNotFoundError, errno.ENOENT, strerror(errno.ENOENT))


def set_numexpr_threads(n_threads=None):
    """Set number of threads for use in Numpy/Pandas NumExpr.

    NumExpr uses a default of the numexpr.detect_number_of_cores().
    This appears to be the number of hyperthreads.
    Calling this will prevent numexpr from making a log call at startup.
    """

    n_threads = n_threads or numexpr.detect_number_of_cores()
    numexpr.set_num_threads(n_threads)

def raise_if_no_file(filepath, logger=None, msg_fmt=None):

    logger = logger or logging.getLogger(__name__)
    msg_fmt = msg_fmt or "not a file:  %s"
    if not os.path.isfile(filepath):
        logger.critical(msg_fmt % filepath)
        raise FILE_DNE(filepath)


def raise_if_no_dir(filepath, logger=None, msg_fmt=None):

    logger = logger or logging.getLogger(__name__)
    msg_fmt = "not a directory:  %s"
    if not os.path.isdir(filepath):
        logger.critical(msg_fmt % filepath)
        raise FILE_DNE(filepath)


def check_ram(ram_bytes, logger):
    """Raise if the requested RAM is negative or greater than the system."""

    if ram_bytes < 0:
        logger.critical("cache %i bytes < 0" % ram_bytes)
        raise ValueError()
    elif ram_bytes / (1024.0 ** 3) > MAX_SYSTEM_RAM_GB:
        ram_gb = ram_bytes / (1024.0 ** 3)
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
    dset = h5file.create_dataset(dataset_key, (n_strings,), dtype=vlen)
    dset[:] = strings


def read_vlen_str_h5py(h5file, dataset_key):
    """Read from an H5 File an iterable of variable length unicode.

    Args:
        h5ile(h5py.File): opened source file
        dataset_key(str): name of data set to read
    """

    return h5file[dataset_key][:].tolist()


def check_nulls(my_df, logger):
    """
    Check for rows with an null values in the supplied Pandas DataFrame

    Args:
        my_df (Pandas DataFrame):

        logger ():

    """
    # NB check for NAN and report to user
    nas = my_df[my_df.isna().any(axis=1)]
    if not nas.empty:
        logger.warning("Rows where null exist: %s" % nas)
