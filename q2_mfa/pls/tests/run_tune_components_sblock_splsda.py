import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rachis import Artifact, Metadata

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from q2_mfa.plugin_setup import plugin  # noqa: E402


def build_output_path(output_dir, base_name):
    commit_message = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%s"],
        text=True,
    ).strip()
    commit_prefix = re.sub(r"[^A-Za-z0-9._-]+", "_", commit_message)[:10] or "no_commit"
    timestamp_prefix = datetime.now().strftime("%m.%d.%Y_%H.%M")
    return Path(output_dir) / f"{timestamp_prefix}_{commit_prefix}_{base_name}"


INPUT_DIRECTORY = Path("/Users/rischv/Documents/data/multiomics/bornsteinlab")
OUTPUT_DIRECTORY = Path(
    "/Users/rischv/Documents/data/multiomics/pls/components_block_splsda"
)


def main():
    """Run DIABLO component tuning on the Bornsteinlab tables."""
    feature_table_metabolome = Artifact.load(
        INPUT_DIRECTORY / "mtb_T_unconstrained.qza"
    )
    feature_table_microbiome = Artifact.load(
        INPUT_DIRECTORY / "genera_T_clr_low_variance_filtered.qza"
    )
    metadata = Metadata.load(INPUT_DIRECTORY / "metadata.tsv")

    tuning_result = plugin.methods["tune_components_block_splsda"](
        tables={
            "metabolome": feature_table_metabolome,
            "microbiome": feature_table_microbiome,
        },
        y=metadata.get_column("Study.Group"),
        design_matrix=None,
        design_weight=0.1,
        ncomp=2,
        scale=True,
        tol=1e-6,
        max_iter=100,
        near_zero_var=True,
        validation="Mfold",
        folds=5,
        nrepeat=3,
        signif_threshold=0.01,
        seed=42,
        threads=1,
    ).tuning
    output_path = build_output_path(
        OUTPUT_DIRECTORY, "tune_components_block_splsda_out.qza"
    )
    tuning_result.save(str(output_path))
    # subprocess.run(["open", str(output_path.parent)])


if __name__ == "__main__":
    main()
