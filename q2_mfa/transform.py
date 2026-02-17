# ----------------------------------------------------------------------------
# Copyright (c) 2026, QIIME 2 development team..
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import numpy as np
import pandas as pd
import rachis


def transform_clr(
    table: pd.DataFrame,
    pseudocount: float = None,
) -> pd.DataFrame:
    """
    Adds a pseudocount to a feature table and applies a centered log-ratio (CLR)
    transformation.  The pseudocount can be provided explicitly or computed as the
    minimum non-zero value in the table.

    Args:
        table (pd.DataFrame): feature table with samples as rows and features as
            columns containing non-negative values
        pseudocount (float): value added to all entries prior to transformation. If
            it is set to None, the pseudocount is computed as the minimum non-zero
            value.

    Output:
        pd.DataFrame: CLR-transformed feature table where each sample sums to zero
            and values are real-valued log-ratios
    """

    if not pseudocount:
        pseudocount = table[table > 0].min().min()

    table = np.log(table + pseudocount)
    table = table.sub(table.mean(axis=1), axis=0)
    return table


def normalize_pqn(
    table: pd.DataFrame,
    method: str = "median",
    ref_samples: rachis.CategoricalMetadataColumn = None,
    ref_label: str = None,
) -> pd.DataFrame:
    """
    Applies Probabilistic Quotient Normalization (PQN) to a metabolomics
    feature table.

    PQN corrects for sample dilution effects by:
        1. Computing a reference spectrum (median or mean across samples).
        2. Computing per-sample quotients to the reference.
        3. Dividing each sample by its median quotient.

    Parameters:
        table (pd.DataFrame):
            Feature table (samples x features) with non-negative values.
        method (str):
            Method to compute reference spectrum. Either "median" or "mean".
        ref_samples (rachis.CategoricalMetadataColumn):
            Categorical metadata column to filter samples for reference calculation.
        ref_label (str):
            Label value in ref_samples to identify which samples to use for reference.

    Returns:
        pd.DataFrame:
            PQN-normalized table.

    Raises:
        ValueError:
            If input contains negative values or normalization fails.
    """

    if (table < 0).any().any():
        raise ValueError("PQN requires non-negative intensities.")

    X = table.astype(float).copy()

    # Filter reference samples if metadata provided
    if ref_samples is not None and ref_label is not None:
        ref_series = ref_samples.to_series()
        ref_sample_indices = ref_series[ref_series == ref_label].index.tolist()
        if not ref_sample_indices:
            raise ValueError(
                f"Reference label '{ref_label}' not found in metadata column."
            )
        X_ref = X.loc[ref_sample_indices]
    else:
        X_ref = X

    # Reference spectrum (per feature)
    ref = X_ref.median(axis=0) if method == "median" else X_ref.mean(axis=0)

    # Avoid division by zero in reference
    ref_safe = ref.replace(0.0, np.nan)

    # Compute quotients per sample
    quotients = X.div(ref_safe, axis=1)

    # Median quotient per sample = dilution factor
    factors = quotients.apply(lambda row: np.nanmedian(row.to_numpy()), axis=1)

    if factors.isna().any():
        raise ValueError(
            "PQN failed: could not compute dilution factor "
            "(sample may contain only zeros)."
        )

    if (factors <= 0).any():
        raise ValueError("PQN failed: non-positive dilution factor detected.")

    # Normalize samples
    X = X.div(factors, axis=0)

    return X


def pretreat_metabolome(
    table: pd.DataFrame,
    sample_normalization: str | None = None,
    pqn_method: str = "median",
    pqn_ref_samples: rachis.CategoricalMetadataColumn = None,
    pqn_ref_label: str = None,
    transform: str | None = None,
    pseudocount: float | None = None,
    center: bool = False,
    scale: str | None = None,
) -> pd.DataFrame:
    """
    Applies metabolomics-friendly preprocessing to a feature table.

    Steps (in order):
        1) Sample normalization: PQN
        2) Transform (log, log10 or sqrt)
        3) Centering (per feature / column)
        4) Scaling (per feature / column): autoscale, pareto, or range

    Parameters:
        table (pd.DataFrame):
            Feature table (samples x features). Values should be numeric.
        sample_normalization (str):
            "none" or "pqn" (Probabilistic Quotient Normalization).
        pqn_method (str):
            How to build the PQN reference spectrum: "median" or "mean".
        pqn_ref_samples (rachis.CategoricalMetadataColumn):
            Categorical metadata column used to select samples for building the PQN
            reference spectrum.
        pqn_ref_label (str):
            Label value in `pqn_ref_samples` indicating which samples to use for the
            PQN reference. Required when `pqn_ref_samples` is provided.
        transform (str):
            Transformation to apply: "log", "sqrt", or "none".
        pseudocount (float | None):
            Offset added before log transform. If None and transform="log",
            uses the minimum non-zero value in the table. Must be > 0.
        center (bool):
            If True, mean-center each feature (column).
        scale (str):
            Scaling method: "none", "autoscale" (unit variance), "pareto"
            (divide by sqrt(std)), or "range" (divide by max-min).

    Returns:
        pd.DataFrame:
            Transformed table with the same shape and index/columns as input.

    Raises:
        ValueError:
            If inputs are invalid or options are unknown.
    """

    X = table.astype(float).copy()

    # 1) Sample normalization (PQN)

    if sample_normalization == "pqn":
        X = normalize_pqn(
            table=X,
            method=pqn_method,
            ref_samples=pqn_ref_samples,
            ref_label=pqn_ref_label,
        )

    # 2) Transform

    if transform == "log" or "log10":
        if (X < 0).any().any():
            raise ValueError("Log transform requires non-negative values.")
        if pseudocount is None:
            min_nonzero = X.where(X > 0).min().min()
            if pd.isna(min_nonzero):
                raise ValueError(
                    "Cannot infer pseudocount: table has no positive values. "
                    "Provide `pseudocount` explicitly."
                )
            pseudocount = float(min_nonzero)
        if transform == "log":
            X = np.log(X + pseudocount)
        elif transform == "log10":
            X = np.log10(X + pseudocount)

    elif transform == "sqrt":
        if (X < 0).any().any():
            raise ValueError("Sqrt transform requires non-negative values.")
        X = np.sqrt(X)

    # 3) Center per feature (column)
    if center:
        X = X - X.mean(axis=0)

    # 4) Scale per feature (column)

    if scale == "autoscale":
        sd = X.std(axis=0, ddof=0)
        if (sd == 0).any():
            raise ValueError(
                "Autoscaling not possible: at least one feature has zero variance."
            )
        X = X / sd

    elif scale == "pareto":
        sd = X.std(axis=0, ddof=0)
        if (sd == 0).any():
            raise ValueError(
                "Pareto scaling not possible: at least one feature has zero variance."
            )
        X = X / np.sqrt(sd)

    elif scale == "range":
        rng = X.max(axis=0) - X.min(axis=0)
        if (rng == 0).any():
            raise ValueError(
                "Range scaling not possible: at least one feature has zero range."
            )
        X = X / rng

    return pd.DataFrame(X, index=table.index, columns=table.columns)
