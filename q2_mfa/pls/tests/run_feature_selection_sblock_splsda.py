import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from rachis import Artifact, Metadata  # noqa: E402

from q2_mfa.plugin_setup import plugin  # noqa: E402


def build_output_path(output_dir, base_name):
    """Builds a timestamped output path that includes the latest commit subject."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    commit_message = subprocess.check_output(
        ["git", "log", "-1", "--pretty=%s"], text=True
    ).strip()
    commit_prefix = re.sub(r"[^A-Za-z0-9._-]+", "_", commit_message)[:10] or "no_commit"
    timestamp_prefix = datetime.now().strftime("%m.%d.%Y_%H.%M")
    return output_dir / f"{timestamp_prefix}_{commit_prefix}_{base_name}"


INPUT_DIRECTORY = Path("/Users/rischv/Documents/data/multiomics/bornsteinlab")
OUTPUT_DIRECTORY = Path(
    "/Users/rischv/Documents/data/multiomics/pls/feature_selection_block_splsda"
)


def main():
    """Runs the DIABLO feature-selection pipeline and saves both outputs."""
    tables = {
        "metabolome": Artifact.load(INPUT_DIRECTORY / "mtb_T_unconstrained.qza"),
        "microbiome": Artifact.load(
            INPUT_DIRECTORY / "genera_T_clr_low_variance_filtered.qza"
        ),
    }
    tuned_ncomp = Artifact.load(
        "/Users/rischv/Documents/data/multiomics/pls/components_block_splsda/"
        "08.13.2026_14.47_Document_P_tune_components_block_splsda_out.qza"
    )
    metadata = Metadata.load(INPUT_DIRECTORY / "metadata.tsv")
    tuning, visualization = plugin.pipelines["feature_selection_block_splsda"](
        tables=tables,
        y=metadata.get_column("Study.Group"),
        design_weight=0.1,
        tuned_ncomp=tuned_ncomp,
        auto_keepx=True,
        min_keepx=5,
        max_keepx_fraction=0.2,
        grid_size=5,
        refinement_factor=2.0,
        selection_rule="one_se",
        ber_margin=0.0,
        se_multiplier=1.0,
        near_zero_var=True,
        validation="Mfold",
        folds=5,
        nrepeat=3,
        distance="centroids.dist",
        measure="BER",
        seed=42,
        threads=8,
    )
    artifact_path = build_output_path(
        OUTPUT_DIRECTORY, "feature_selection_block_splsda.qza"
    )
    visualization_path = build_output_path(
        OUTPUT_DIRECTORY, "feature_selection_block_splsda.qzv"
    )
    tuning.save(str(artifact_path))
    visualization.save(str(visualization_path))


if __name__ == "__main__":
    main()
