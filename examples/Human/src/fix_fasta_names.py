#!/usr/bin/env python3

"""
Reformat Fasta files for EDTA usage
"""

__author__ = "Scott Teresi"

import argparse
import os
import logging
import coloredlogs

import Bio
from Bio import SeqIO


def reformat_seq_iq(input_fasta, genome_name, output_dir, logger):
    """
    Reformat a regular FASTA file to have shorter sequence ID names for EDTA

    Args:
        input_fasta (str): String path to input fasta file

        genome_name (str): String for genome name

        output_dir (str): Path to output dir

        logger (logging.Logger): Object to log information to

    Returns:
        None, just saves the edited FASTA file to disk. Also writes a
        conversion table to disk for the old names and their new name
        counterparts
    """
    # MAGIC file suffixes
    new_fasta = os.path.join(output_dir, (genome_name + "_NewNames.fasta"))
    name_key = os.path.join(output_dir, (genome_name + "_Seq_ID_Conversion.txt"))

    if os.path.exists(new_fasta):
        os.remove(new_fasta)  # remove the file because we are in append mode
    if os.path.exists(name_key):
        os.remove(name_key)
    pair_dict = {}  # NB this is used to write the conversion key later for
    # clarity
    # MAGIC we only want specific chromosomes
    chromosomes = ["chr1", "chr7"]
    count = 0

    with open(input_fasta, "r") as input_fasta:
        for s_record in SeqIO.parse(input_fasta, "fasta"):
            if s_record.id in chromosomes:
                # NB the s_record.id and s_record.description combined contain
                # all the information for each entry following the '>' character
                # in the fasta

                # NB In this case:
                # We just want the s_record.id which correctly points to the
                # first integer. E.g '1 dna:chromosome blah blah blah' we just want
                # 1.
                pair_dict[s_record.id] = "\t " + s_record.description
                s_record.description = ""  # NB edit the description so that when
                # we rewrite we don't have the extraneous info
                with open(new_fasta, "a") as output:
                    SeqIO.write(s_record, output, "fasta")
            else:
                s_record.id = "Auxiliary_" + str(count)
                pair_dict[s_record.id] = "\t " + s_record.description
                s_record.description = ""  # NB edit the description so that when
                # we rewrite we don't have the extraneous info
                with open(new_fasta, "a") as output:
                    SeqIO.write(s_record, output, "fasta")
                count += 1

    logger.info("Finished writing new fasta to: %s" % new_fasta)

    with open(name_key, "w") as output:
        for key, val in pair_dict.items():
            # Write the conversion table for record-keeping.
            output.write("%s\t%s\n" % (key, val))
    logger.info(
        "Finished writing name conversion table to: %s"
        % os.path.join(output_dir, name_key)
    )


if __name__ == "__main__":

    path_main = os.path.abspath(__file__)
    dir_main = os.path.dirname(path_main)
    parser = argparse.ArgumentParser(description="Reformat FASTA for EDTA")

    parser.add_argument("fasta_input_file", type=str, help="parent path of fasta file")
    parser.add_argument("genome_id", type=str, help="name of genome")
    output_default = os.path.join(
        dir_main, "../../../../", "TE_Density_Example_Data/Human"
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        type=str,
        default=output_default,
        help="Parent directory to output results",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="set debugging level to DEBUG"
    )
    args = parser.parse_args()
    args.fasta_input_file = os.path.abspath(args.fasta_input_file)
    args.output_dir = os.path.abspath(
        os.path.join(args.output_dir, "Processed_Sequences")
    )  # TODO move to data dir?

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = logging.getLogger(__name__)
    coloredlogs.install(level=log_level)

    print()
    print(args.output_dir)
    print()

    reformat_seq_iq(args.fasta_input_file, args.genome_id, args.output_dir, logger)
