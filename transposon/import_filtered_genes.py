import pandas as pd
from transposon import check_nulls


def import_filtered_genes(genes_input_path, logger):
    """
    Import the preprocessed gene annotation file

    genes_input_path (str): Path to cleaned input annotation file of genes

    logger (logging.Logger): Logging object

    Returns:
        gene_data (pandas.core.frame.DataFrame): A pandas dataframe
        representing the preprocessed gene annotation file
    """
    try:
        gene_data = pd.read_csv(
            genes_input_path,
            header="infer",
            sep="\t",
            index_col="Gene_Name",
            dtype={
                "Start": "float64",
                "Stop": "float64",
                "Length": "float64",
                "Chromosome": str,
                "Strand": str,
                "Feature": str,
            },
        )
    except:
        raise ValueError(
            """Error occurred while trying to read preprocessed gene
                         annotation file into a Pandas dataframe, please refer
                         to the README as to what information is expected"""
        )
    check_nulls(gene_data, logger)

    # Sort for legibility
    gene_data.sort_values(by=["Chromosome", "Start"], inplace=True)

    logger.info(
        """Successfully imported the preprocessed gene annotation
        information: %s """
        % genes_input_path
    )
    return gene_data
