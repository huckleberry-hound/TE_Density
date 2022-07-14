#!/usr/bin/env/python

"""
Barebones initialization of DensityData class intended for demonstration
purposes.
"""

__author__ = "Scott Teresi"

import argparse
import pandas as pd
import os
import logging
import coloredlogs

from transposon.gene_data import GeneData
from transposon.density_data import DensityData
from transposon.import_filtered_genes import import_filtered_genes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="generate graphs")

    parser.add_argument(
        "cleaned_gene_annotation",
        type=str,
        help="""parent path to the cleaned gene data file that was derived from
        preprocessing""",
    )

    parser.add_argument(
        "density_data_folder",
        type=str,
        help="Parent path of folder containing TE Density results",
    )

    parser.add_argument(
        "hdf5_string",
        type=str,
        help="""Regex string rule for extracting the genome name and chromosome
        ID from the h5 file. Please refer to the
        from_list_gene_data_and_hdf5_dir method of DensityData for more
        documentation""",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="set debugging level to DEBUG"
    )
    args = parser.parse_args()
    args.cleaned_gene_annotation = os.path.abspath(args.cleaned_gene_annotation)
    args.density_data_folder = os.path.abspath(args.density_data_folder)

    # NB just for logging arguments to import_filtered command and DensityData
    # initialization
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = logging.getLogger(__name__)
    coloredlogs.install(level=log_level)

    cleaned_genes = import_filtered_genes(args.cleaned_gene_annotation, logger)

    gene_dataframe_list = [
        dataframe for k, dataframe in cleaned_genes.groupby("Chromosome")
    ]

    # NB this is how I get a list of GeneData objects so that I may
    # initialize DensityData further on
    # NB MAGIC int to get chromosome ID
    gene_data_list = [
        GeneData(dataframe, dataframe["Chromosome"].unique()[0])
        for dataframe in gene_dataframe_list
    ]

    # NOTE this object is a list of DensityData instances
    # Each instance corresponds to one pseudmolecule of TE Density data.
    # If you are having trouble, please examine the documentation of the
    # classmethod 'from_list_gene_data_and_hdf5_dir'.
    processed_dd_data = DensityData.from_list_gene_data_and_hdf5_dir(
        gene_data_list, args.density_data_folder, args.hdf5_string, logger
    )

    # ------------------------------------------------------------
    # NOTE now the user may begin analyzing their data. For more examples
    # please examine the code used for the Arabidopsis, Blueberry, Human, and
    # Rice datasets. But here are some select ones:

    # TODO give more explicit examples so the users don't have to go digging as
    # much through the example code.
