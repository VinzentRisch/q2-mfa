# ----------------------------------------------------------------------------
# Copyright (c) 2026, Bokulich Laboratories.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd
from q2_types.feature_table import FeatureTable, Unconstrained
from rachis import Artifact, Metadata, ResultCollection
from rachis.sdk.usage import ExecutionUsage
from rpy2.robjects import conversion, default_converter, pandas2ri
from rpy2.robjects.conversion import localconverter
from rpy2.robjects.packages import importr

base = importr("base")
mixomics = importr("mixOmics")


def _load_nutrimouse():
    return mixomics.__rdata__.fetch("nutrimouse")["nutrimouse"]


def _nutrimouse_table(block):
    data_frame = base.as_data_frame(_load_nutrimouse().rx2(block))
    with localconverter(default_converter + pandas2ri.converter):
        table = conversion.get_conversion().rpy2py(data_frame)
    table.index = pd.Index(table.index.astype(str), name="sample-id")
    return Artifact.import_data(FeatureTable[Unconstrained], table)


def nutrimouse_tables_factory():
    return ResultCollection(
        {"gene": _nutrimouse_table("gene"), "lipid": _nutrimouse_table("lipid")}
    )


def nutrimouse_metadata_factory():
    data = _load_nutrimouse()
    sample_ids = list(base.rownames(data.rx2("gene")))
    diets = list(base.as_character(data.rx2("diet")))
    return Metadata(
        pd.DataFrame({"diet": diets}, index=pd.Index(sample_ids, name="sample-id"))
    )


def feature_selection_block_splsda_nutrimouse(use):
    use.comment(
        "Load the nutrimouse dataset bundled with mixOmics: 40 mice, 120 "
        "gene-expression features, and 21 lipid features. The small grid and three "
        "repeats keep this demonstration short; use more repeats for a thorough "
        "analysis."
    )
    tables = use.init_artifact_collection(
        "nutrimouse_tables", nutrimouse_tables_factory
    )
    metadata = use.init_metadata("nutrimouse_metadata", nutrimouse_metadata_factory)
    diet = use.get_metadata_column("diet", "diet", metadata)
    ExecutionUsage
    use.action(
        use.UsageAction(plugin_id="mfa", action_id="feature_selection_block_splsda"),
        use.UsageInputs(
            tables=tables,
            y=diet,
            keepx={"gene": "5,10,15", "lipid": "5,10,15"},
            ncomp=2,
            design_weight=0.1,
            folds=3,
            nrepeat=3,
            measure="BER",
            seed=42,
            threads=2,
        ),
        use.UsageOutputNames(
            feature_selection="feature_selection_nutrimouse",
            visualization="feature_selection_report",
        ),
    )
