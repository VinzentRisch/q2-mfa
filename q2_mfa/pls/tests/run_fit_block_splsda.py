import re
import subprocess
from datetime import datetime
from pathlib import Path

from rachis import Artifact, Metadata
from rachis.plugins import mfa


def build_output_path(output_dir, base_name):
    commit_message = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%s"],
        text=True,
    ).strip()
    commit_prefix = re.sub(r"[^A-Za-z0-9._-]+", "_", commit_message)[:10] or "no_commit"
    timestamp_prefix = datetime.now().strftime("%m.%d.%Y_%H.%M")
    return Path(output_dir) / f"{timestamp_prefix}_{commit_prefix}_{base_name}"


INPUT_DIRECTORY = Path("/Users/rischv/Documents/data/multiomics/bornsteinlab")
OUTPUT_DIRECTORY = Path("/Users/rischv/Documents/data/multiomics/pls/fit_block_splsda")


def main():
    """Fit DIABLO block sPLS-DA on the Bornsteinlab feature tables."""
    feature_table_metabolome = Artifact.load(
        INPUT_DIRECTORY / "mtb_T_unconstrained.qza"
    )
    feature_table_microbiome = Artifact.load(
        INPUT_DIRECTORY / "genera_T_clr_low_variance_filtered.qza"
    )
    metadata = Metadata.load(INPUT_DIRECTORY / "metadata.tsv")

    plsda_result = mfa.actions.fit_block_splsda(
        tables={
            "metabolome": feature_table_metabolome,
            "microbiome": feature_table_microbiome,
        },
        y=metadata.get_column("Study.Group"),
        design_weight=0.1,
        ncomp=2,
        keepx={"component-1": "5,5", "component-2": "10,10"},
        near_zero_var=True,
        folds=5,
        nrepeat=3,
        seed=42,
        threads=8,
    ).pls_results
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    output_path = build_output_path(OUTPUT_DIRECTORY, "fit_block_splsda_out.qza")
    plsda_result.save(str(output_path))
    # subprocess.run(["open", str(output_path.parent)])


if __name__ == "__main__":
    main()
