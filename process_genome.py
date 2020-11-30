#!/usr/bin/env python3

"""
Calculate transposable element density.
"""

__author__ = "Scott Teresi, Michael Teresi"

import argparse
import os

import logging
import coloredlogs
import numpy as np
import pandas as pd
from tqdm import tqdm
from configparser import ConfigParser
import sys
import time

from transposon import FILE_DNE, set_numexpr_threads
from transposon import raise_if_no_file, raise_if_no_dir
from transposon.gene_data import GeneData
from transposon.transposon_data import TransposonData
from transposon.preprocess import PreProcessor
from transposon.overlap_manager import OverlapManager


def validate_args(args, logger):
    """Raise if an input argument is invalid."""

    raise_if_no_file(
        args.genes_input_file,
        logger=logger,
        msg_fmt="arg 'genes_input_file' not a file: %s",
    )
    raise_if_no_file(
        args.tes_input_file,
        logger=logger,
        msg_fmt="arg 'tes_input_file' not a file: %s",
    )
    raise_if_no_dir(
        args.output_dir, logger=logger, msg_fmt="arg 'output_dir' not a dir: %s"
    )


def parse_algorithm_config(config_path):
    """Return parameters for running density calculations."""

    raise_if_no_file(config_path)
    parser = ConfigParser()
    parser.read(config_path)
    window_start = parser.getint("density_parameters", "first_window_size")
    window_step = parser.getint("density_parameters", "window_delta")
    window_stop = parser.getint("density_parameters", "last_window_size")
    alg_param = {
        "window_range": range(window_start, window_stop, window_step)
    }
    return alg_param


if __name__ == "__main__":
    """Command line interface to calculate density."""

    path_main = os.path.abspath(__file__)

    parser = argparse.ArgumentParser(description="calculate TE density")

    parser.add_argument("genes_input_file", type=str, help="parent path of gene file")

    parser.add_argument(
        "tes_input_file", type=str, help="parent path of transposon file"
    )

    parser.add_argument("genome_id", type=str, help="name of genome")

    parser.add_argument(
        "--config_file",
        "-c",
        type=str,
        default=os.path.join(path_main, "../", "config/test_run_config.ini"),
        help="parent path of config file",
    )

    parser.add_argument(
        "--reset_h5",
        action="store_true",
        help="Rewrite h5 intermediate files for gene & TEs",
    )

    parser.add_argument(
        "--contig_del",
        action="store_false",
        help="""Deletes
                        entries (rows) in the gene annotation and TE annotation
                        files that are labelled with any variation of contig*
                        in the chromosome field (case insensitive).""",
    )

    parser.add_argument(
        "--revise_anno",
        action="store_true",
        help="""Forces the
                        recreation of a revised TE annotation file. Desirable if
                        you have previously created a revised TE annotation but
                        you want the pipeline to create a new one from scratch
                        and overwrite the cache. This is especially useful if
                        you have modified the input TE annotation but have not
                        changed the filename.""",
    )

    parser.add_argument(
        "--output_dir",
        "-o",
        type=str,
        default=os.path.join(path_main, "../..", "TE_Data"),
        help="parent directory to output results",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="set debugging level to DEBUG"
    )

    args = parser.parse_args()
    args.genes_input_file = os.path.abspath(args.genes_input_file)
    args.tes_input_file = os.path.abspath(args.tes_input_file)
    args.config_file = os.path.abspath(args.config_file)
    args.output_dir = os.path.abspath(args.output_dir)

    filtered_input_data_loc = os.path.abspath(
        os.path.join(args.output_dir, "filtered_input_data")
    )
    input_h5_cache_loc = os.path.abspath(
        os.path.join(args.output_dir, filtered_input_data_loc, "input_h5_cache")
    )

    revised_input_data_loc = os.path.abspath(
        os.path.join(args.output_dir, filtered_input_data_loc, "revised_input_data")
    )

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = logging.getLogger(__name__)
    coloredlogs.install(level=log_level)
    for argname, argval in vars(args).items():
        logger.debug("%-18s: %s" % (argname, argval))
    validate_args(args, logger)
    alg_parameters = parse_algorithm_config(args.config_file)

    set_numexpr_threads()  # prevents an unenecessary log call from numexpr

    logger.info("preprocessing...")
    preprocessor = PreProcessor(
        args.genes_input_file,
        args.tes_input_file,
        filtered_input_data_loc,
        input_h5_cache_loc,
        revised_input_data_loc,
        args.reset_h5,
        args.genome_id,
        args.revise_anno,
        args.contig_del,
    )
    preprocessor.process()
    n_data_files = sum(1 for _ in preprocessor.data_filepaths())
    rel_preproc = os.path.relpath(input_h5_cache_loc)
    logger.info("preprocessed %d files to %s" % (n_data_files, rel_preproc))
    logger.info("preprocessing... complete")

    logger.info("process overlap...")
    filepaths = list(preprocessor.data_filepaths())
    overlap_mgr = OverlapManager(
            filepaths,
            args.output_dir,
            alg_parameters["window_range"]
            )
    overlap_results = overlap_mgr.calculate_overlap()
    logger.info("processed %d overlap jobs" % len(overlap_results))
    logger.info("process overlap... complete")

    
    raise NotImplementedError()
