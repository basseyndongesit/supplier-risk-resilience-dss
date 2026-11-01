"""Week 11 validation-selected KPI 2/3 scenario scoring.

Uses locally trusted frozen model objects. No fitting, database writes,
or independent-test access. Requires complete 3/5/7 scenario groups.
"""

import numpy as np
import pandas as pd


DELAYS = (3, 5, 7)


def score_scenarios(frame, kpi2_artifact, kpi3_artifact):
    """Return original and revised predictions for one PO/review.

    The original direct KPI3 model is retained for comparison.
    The revised KPI3 estimate uses corrected predicted shortage,
    not observed shortage or simulator target values.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Scenario input must be a DataFrame")

    required = {
        "PO_ID",
        "Review_Date",
        "Delay_Scenario_Days",
        "Unit_Cost_Premium",
    }

    for artifact in (kpi2_artifact, kpi3_artifact):
        if not isinstance(artifact, dict):
            raise TypeError("Expected a frozen model artifact dictionary")
        if "features" not in artifact or "model" not in artifact:
            raise ValueError("Frozen artifact missing features or model")
        required.update(artifact["features"])

    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing required features: {sorted(missing)}")

    if len(frame) != 3:
        raise ValueError("Exactly three scenario rows are required")

    if frame[["PO_ID", "Review_Date"]].drop_duplicates().shape[0] != 1:
        raise ValueError("Expected one PO and review-date combination")

    data = frame.sort_values("Delay_Scenario_Days").reset_index(drop=True).copy()

    delays = pd.to_numeric(
        data["Delay_Scenario_Days"], errors="coerce"
    ).to_numpy(dtype=float)

    if not np.array_equal(delays, np.array(DELAYS, dtype=float)):
        raise ValueError("Scenarios must be exactly 3, 5, and 7 days")

    premium = pd.to_numeric(
        data["Unit_Cost_Premium"], errors="coerce"
    ).to_numpy(dtype=float)

    if not np.isfinite(premium).all() or (premium < 0).any():
        raise ValueError("Unit-cost premiums must be finite and nonnegative")

    if not np.allclose(premium, premium[0], rtol=0, atol=1e-8):
        raise ValueError(
            "Unit-cost premium must be constant across the three delays"
        )

    features2 = list(kpi2_artifact["features"])
    features3 = list(kpi3_artifact["features"])

    raw2 = np.asarray(
        kpi2_artifact["model"].predict(data[features2]),
        dtype=float,
    ).reshape(-1)

    raw3 = np.asarray(
        kpi3_artifact["model"].predict(data[features3]),
        dtype=float,
    ).reshape(-1)

    if raw2.shape != (3,) or raw3.shape != (3,):
        raise ValueError("Each model must return exactly three predictions")

    if not np.isfinite(raw2).all() or not np.isfinite(raw3).all():
        raise ValueError("Nonfinite model prediction")

    original_shortage = np.maximum(raw2, 0.0)
    original_direct_cost = np.maximum(raw3, 0.0)
    original_chained_cost = original_shortage * premium

    revised_shortage = np.maximum.accumulate(original_shortage)
    revised_chained_cost = revised_shortage * premium

    result = data[
        ["PO_ID", "Review_Date", "Delay_Scenario_Days", "Unit_Cost_Premium"]
    ].copy()

    result["Original_KPI2_Shortage"] = original_shortage
    result["Revised_KPI2_Shortage"] = revised_shortage
    result["Original_KPI3_Direct_Cost"] = original_direct_cost
    result["Original_KPI3_Chained_Cost"] = original_chained_cost
    result["Revised_KPI3_Chained_Cost"] = revised_chained_cost

    result["KPI2_Revision_Delta"] = (
        revised_shortage - original_shortage
    )
    result["KPI3_Revision_vs_Direct_Delta"] = (
        revised_chained_cost - original_direct_cost
    )

    assert np.all(np.diff(revised_shortage) >= -1e-10)
    assert np.all(np.diff(revised_chained_cost) >= -1e-10)
    assert np.all(revised_shortage >= 0)
    assert np.all(revised_chained_cost >= 0)

    return result
