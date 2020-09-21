#!/usr/bin/env python3

"""
Import and preprocess raw annotations and modify files for TE density calculation.
"""

import errno
import os
import logging

from transposon import raise_if_no_file, raise_if_no_dir
from transposon.gene_data import GeneData
from transposon.transposon_data import TransposonData

from transposon.replace_names import te_annot_renamer
from transposon.verify_cache import (
    verify_chromosome_h5_cache,
    verify_TE_cache,
    verify_gene_cache,
    revise_annotation,
)
from transposon.revise_annotation import Revise_Anno

# FUTURE add option to change the filtering implementation
class PreProcessor:
    """Processes input data into GeneData and TransposonData files.

    Ingests gene and transposon data from raw files into pandas.DataFrame.
    Filters gene and transposon data, such as representation conversions.
    Revises transposon data, to handle overlapping TEs.
    """

    CLEAN_PREFIX = "Cleaned_"
    REVISED_PREFIX = "Revised_"
    GCACHE_SUFFIX = "GeneData"
    TCACHE_SUFFIX = "TEData"
    EXT = "tsv"
    CACHE_EXT = "h5"

    # TODO SCOTT can you reduce the number of inputs here?
    # does filtered / revised have to be different?

    # From Scott: filtered and revised need to be different. I don't think it
    # is possible to reduce the number of inputs.
    def __init__(
        self,
        gene_file,
        transposon_file,
        filtered_dir,
        h5_cache_dir,
        revised_dir,
        reset_h5,
        genome_id,
        revise_transposons,
        contig_del,
        logger=None,
    ):
        """Initialize.

        Args:
            gene_file(str): filepath to genome input data
            transposon_file(str): filepath to transposon input file
            filtered_dir(str): directory path for the filtered files
            h5_cache_dir(str): directory path for the cached h5 files
            revised_dir(str): directory path for revised TE files
            reset_h5(bool): whether or not to force re-creation of h5 cache
            genome_id(str): user-defined string for the genome.
            revise_transposons(bool): whether or not to force creation of
                revised TE annotation (no overlapping TEs).
            contig_del(bool): whether or not to force deletion of genes or TEs
                that are located on contigs according to the original annotation.
            logger(logging.Logger): logger instance
        """

        self._logger = logger or logging.getLogger(self.__class__.__name__)
        raise_if_no_file(gene_file)
        raise_if_no_file(transposon_file)
        os.makedirs(filtered_dir, exist_ok=True)
        os.makedirs(h5_cache_dir, exist_ok=True)
        os.makedirs(revised_dir, exist_ok=True)

        self.filtered_dir = filtered_dir
        self.h5_cache_dir = h5_cache_dir
        self.revised_dir = revised_dir

        self.gene_in = str(gene_file)
        self.gene_out = self._processed_filename(
            self.gene_in, self.filtered_dir, self.CLEAN_PREFIX
        )
        self.te_in = str(transposon_file)
        self.te_out = self._processed_filename(
            self.te_in, self.filtered_dir, self.CLEAN_PREFIX
        )
        self.te_revised = self._processed_filename(
            self.te_in, self.revised_dir, self.REVISED_PREFIX
        )
        self.contiguous_delete = contig_del
        self.do_transposon_revisions = revise_transposons
        self.do_h5_cache_recreation = reset_h5

        self.gene_frame = None
        self.transposon_frame = None
        self.gene_files = None
        self.transposon_files = None

        self.genome_id = genome_id

    def process(self):
        """Helper to execute all preprocessing tasks.

        Mutates self.
        """

        # first preprocessing on the raw input
        self.gene_frame = self._filter_genes()
        self.transposon_frame = self._filter_transposons()

        # modify TE start/stops to account for overlapped TEs
        self.transposon_frame = self._revise_transposons(self.transposon_frame)

        self.split_frame_pairs = self._split_wrt_chromosome(
            self.gene_frame, self.transposon_frame
        )

        self.gene_files = list()
        self.transposon_files = list()

    def yield_input_files(self):
        """Yield the gene and TE pandaframes together one at a time"""
        gene_list, te_list = self.split_frame_pairs
        for gene_frame, te_frame in zip(gene_list, te_list):
            yield gene_frame, te_frame

    @classmethod
    def _processed_filename(cls, filepath, filtered_dir, prefix):
        """Preprocessed filepath given original.

        Args:
            filepath(str): path to input file (e.g. gene or transposon)
            filtered_dir(str): directory to output cleaned files
            prefix(str): prepend to filename
        Raises:
            ValueError: bad input filetype
        Returns:
            str: expected filepath
        """

        filename = os.path.basename(filepath)
        name, ext = os.path.splitext(filename)
        if ext != ".gff" or ".gtf":
            if os.path.isdir(filtered_dir):
                newname = prefix + name + "." + cls.EXT
            return os.path.join(filtered_dir, newname)

        else:
            raise ValueError("unknown genome file ext '%s' at %s" % (ext, filepath))

    def _filter_genes(self):
        """Updates filtered gene file if necessary.

        Returns:
            pandas.DataFrame: preprocessed gene frame
        """

        # NB this does not create any GeneData
        gene_data_unwrapped = verify_gene_cache(
            self.gene_in, self.gene_out, self.contiguous_delete, self._logger
        )
        return gene_data_unwrapped

    def _filter_transposons(self):
        """Updates filtered transposon file if necessary.

        Returns:
            pandas.DataFrame: preprocessed transposon frame
        """

        # NB this does not create any TransposonData
        te_data_unwrapped = verify_TE_cache(
            self.te_in,
            self.te_out,
            te_annot_renamer,
            self.contiguous_delete,
            self._logger,
        )
        return te_data_unwrapped

    def _revise_transposons(self, transposon_frame):

        te_data_unwrapped = revise_annotation(
            transposon_frame,
            self.do_transposon_revisions,
            self.te_revised,
            self.revised_dir,
            self._logger,
            self.genome_id,
        )
        return te_data_unwrapped

    def _split_wrt_chromosome(self, filtered_genes, filtered_tes):
        """Segment data with respect to chromosome.

        Data is split wrt chromosome as each chromosome is processed indepenently.

        Args:
            filtered_genes(pandas.DataFrame): preprocessed genes
            filtered_tes(pandas.DataFrame): preprocessed transposons
        Returns:
            list(pandas.DataFrame, pandas.DataFrame): genes, transposon frames
        """

        group_key = "Chromosome"
        gene_groups = filtered_genes.groupby(group_key)
        gene_list = [gene_groups.get_group(g) for g in gene_groups.groups]
        te_groups = filtered_tes.groupby(group_key)
        te_list = [te_groups.get_group(g) for g in te_groups.groups]
        self._validate_split(gene_list, te_list, self.genome_id)
        return (gene_list, te_list)

    def _validate_split(self, gene_frames, te_frames, genome_id):
        """Raises if the gene / te pairs haven't been grouped correctly.

        This is just to make sure that each pair of chromosomes are right.
        Correct subsetting would be managed by the custom split command.

        Args:
            gene_frames(list(pandas.DataFrame)): gene for each chromosome
            grouped_TEs (list(pandas.DataFrame))): transposon for each chromsome
            genome_id (str) a string of the genome name.
        """
        if len(gene_frames) != len(te_frames):
            msg = (
                """no. gene annotations split by chromosome %d != no. te annotations split by chromosome"""
                % len(gene_frames),
                len(te_frames),
            )
            self._logger.critical(msg)
            self._logger.critical(
                """Check that you do not have a chromosome absent of TE or gene annotations"""
            )
            raise ValueError(msg)

        for gene_frame, te_frame in zip(gene_frames, te_frames):
            # MAGIC NUMBER of 0 to index row and get the Chromosome
            # column's value. In this case get the string of the chromosome.
            gene_chromosome = gene_frame.Chromosome.iloc[:].values[0]
            te_chromosome = te_frame.Chromosome.iloc[:].values[0]
            if te_chromosome != gene_chromosome:
                msg = "mismatching chromosomes: %d != %d (gene vs te)" % (
                    gene_chromosome,
                    te_chromosome,
                )
                self._logger.critical(msg)
                raise ValueError(msg)
            try:
                gene_obj = GeneData(gene_frame, genome_id)
                gene_uid = gene_obj.chromosome_unique_id
            except RuntimeError as r_err:
                logging.critical("sub gene grouping not unique: {}".format(gene_obj))
                raise r_err

    def _frames_to_custom_format(self):

        pass  # convert the panda frames to the custom container

    @classmethod
    def _processed_cache_name(cls, chrom_id, cache_dir, suffix):
        """Preprocessed filepath given identifying information

        Save GeneData and TEData on chromosome-by-chromosome basis in H5 format
        to disk.

        Args:
            chrom_id (str): string representation of the chromosome
            cache_dir (str): directory to output h5 files
            suffix (str): append to filename
        Returns:
            str: expected filepath
        """

        return os.path.join(
            cache_dir, str(chrom_id + "_" + suffix + "." + cls.CACHE_EXT)
        )

    def _cache_data_files(self):
        """Update GeneData and TransposonData files on disk."""

        # TODO this code is never invoked anywhere

        for genes, tes in self.yield_input_files():
            # Wrap them
            wrapped_genedata_by_chrom = GeneData(genes.copy(deep=True))
            wrapped_genedata_by_chrom.add_genome_id(self.genome_id)
            wrapped_tedata_by_chrom = TransposonData(tes.copy(deep=True))
            wrapped_tedata_by_chrom.add_genome_id(self.genome_id)
            chrom_id = wrapped_genedata_by_chrom.chromosome_unique_id

            # Get filenames for new cache files
            h5_g_filename = self._processed_cache_name(
                chrom_id, self.h5_cache_dir, self.GCACHE_SUFFIX
            )
            h5_t_filename = self._processed_cache_name(
                chrom_id, self.h5_cache_dir, self.TCACHE_SUFFIX
            )

            verify_chromosome_h5_cache(
                wrapped_genedata_by_chrom,
                wrapped_tedata_by_chrom,
                h5_g_filename,
                h5_t_filename,
                self.do_h5_cache_recreation,
                self.h5_cache_dir,
                self.gene_in,
                self.te_in,
                chrom_id,
                self._logger,
            )

        # TODO candidate for deletion, I think I was able to refactor this
        # usage.

        # somethng like this?
        # grouped_genes = split(gene_data_unwrapped, "Chromosome")
        # grouped_TEs = split(te_data_unwrapped, "Chromosome")
        # # check docstring for my split func
        # check_groupings(grouped_genes, grouped_TEs, logger, genome_id)
        # for chromosome_of_gene_data, chromosome_of_te_data in zip(
        #     grouped_genes, grouped_TEs
        # ):
        # wrapped_genedata_by_chrom = GeneData(chromosome_of_gene_data.copy(deep=True))
        # wrapped_genedata_by_chrom.add_genome_id(genome_id)
        # wrapped_tedata_by_chrom = TransposonData(chromosome_of_te_data.copy(deep=True))
        # wrapped_tedata_by_chrom.add_genome_id(genome_id)
        # chrom_id = wrapped_genedata_by_chrom.chromosome_unique_id
        #
        # # NOTE
        # # MICHAEL, these are how the H5 files are saved
        # h5_g_filename = os.path.join(h5_cache_location, str(chrom_id + "_GeneData.h5"))
        # h5_t_filename = os.path.join(h5_cache_location, str(chrom_id + "_TEData.h5"))
        #
        # verify_chromosome_h5_cache(
        #     wrapped_genedata_by_chrom,
        #     wrapped_tedata_by_chrom,
        #     h5_g_filename,
        #     h5_t_filename,
        #     reset_h5,
        #     h5_cache_location,
        #     genes_input_file,
        #     tes_input_file,
        #     chrom_id,
        #     logger,
        # )
