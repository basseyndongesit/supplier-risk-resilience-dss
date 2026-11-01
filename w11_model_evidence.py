"""Week 11 validation evidence presentation. No model fitting or data access."""

import json
from pathlib import Path

import streamlit as st


REPORT_NAMES = (
    "kpi1_validation_consolidated.json",
    "kpi23_validation_selection.json",
)


def load_reports(workspace):
    folder = Path(workspace) / "evaluation"
    reports = []

    for filename in REPORT_NAMES:
        path = folder / filename

        if not path.is_file():
            raise FileNotFoundError(
                f"Missing validation report: {path}"
            )

        with path.open("r", encoding="utf-8-sig") as handle:
            reports.append(json.load(handle))

    kpi1, kpi23 = reports

    if (
        kpi1.get("status") != "KPI1_VALIDATION_CONSOLIDATED"
        or kpi23.get("status") != "VALIDATION_SELECTION_DOCUMENTED"
    ):
        raise ValueError("Unexpected validation report status")

    if (
        kpi1.get("final_test_accessed_in_week11") is not False
        or kpi23.get("final_test_accessed_in_week11") is not False
    ):
        raise ValueError("Unexpected final-test access declaration")

    if kpi23.get("evaluation_partition") != "validation":
        raise ValueError("Unexpected evaluation partition")

    return kpi1, kpi23


def render(workspace):
    st.subheader("Model Performance and Selection")
    st.caption(
        "Results below come from the chronological development "
        "validation partition, not the independent final test."
    )

    try:
        kpi1, kpi23 = load_reports(workspace)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        st.error(f"Validation evidence unavailable: {exc}")
        return

    with st.expander("KPI 1: Late-Delivery Risk", expanded=True):
        metrics = kpi1["original_validation_metrics"]

        a, b, c, d = st.columns(4)
        a.metric("ROC-AUC", f"{metrics['roc_auc']:.3f}")
        b.metric("PR-AUC", f"{metrics['pr_auc']:.3f}")
        c.metric("Brier score", f"{metrics['brier']:.3f}")
        d.metric("Log loss", f"{metrics['log_loss']:.3f}")

        st.write(
            "**Selected:** Original frozen random forest. "
            "The sigmoid-calibration candidate was rejected because "
            "it did not improve any of these four validation metrics."
        )
        st.caption(
            "Ranking discrimination is limited. Probabilities are "
            "not fully calibrated, and no operational decision "
            "threshold has been approved."
        )

    with st.expander("KPI 2: Incremental Shortage", expanded=True):
        result = kpi23["kpi2"]

        a, b, c = st.columns(3)
        a.metric("Original MAE", f"{result['original_mae']:.3f}")
        b.metric("Revised MAE", f"{result['revised_mae']:.3f}")
        c.metric(
            "Scenario-order violations",
            str(result["revised_monotonicity_violations"]),
            delta=(
                f"{result['revised_monotonicity_violations'] - result['original_monotonicity_violations']:+d}"
            ),
        )

        st.write(
            "**Selected:** Frozen random forest with a "
            "cumulative-maximum correction across the 3-, 5-, "
            "and 7-day delay scenarios."
        )
        st.caption(
            "The correction prevents predicted shortage from "
            "decreasing as the delay increases. Validation MAE "
            "increased slightly; the selection prioritizes "
            "scenario consistency."
        )

    with st.expander("KPI 3: Emergency Procurement Premium", expanded=True):
        result = kpi23["kpi3"]

        a, b, c = st.columns(3)
        a.metric(
            "Original direct-model MAE",
            f"{result['original_direct_mae']:.3f}",
        )
        b.metric(
            "Revised chained MAE",
            f"{result['revised_chained_monotonic_mae']:.3f}",
        )
        c.metric(
            "Validation MAE reduction",
            f"{result['validation_mae_reduction_percent']:.2f}%",
        )

        st.write(
            "**Selected:** Revised predicted shortage multiplied "
            "by nonnegative unit-cost premium."
        )
        st.code(
            "Predicted emergency premium = "
            "revised predicted shortage multiplied by unit-cost premium",
            language=None,
        )
        st.caption(
            "This calculation mirrors the synthetic simulator's "
            "cost structure. The validation improvement does not "
            "establish real-world procurement accuracy."
        )

    st.markdown("#### How to interpret model explanations")
    st.write(
        "The historical feature-importance charts and local "
        "attributions below describe the **original frozen models**. "
        "They do not explain the revised cumulative-maximum "
        "correction or chained emergency-premium calculation. "
        "Those revised steps are described explicitly above."
    )
    st.caption(
        "Historical local-attribution examples are not explanations "
        "of the currently selected purchase order. Feature "
        "importance indicates predictive association, not causation."
    )
