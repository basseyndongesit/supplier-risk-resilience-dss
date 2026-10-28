
"""Read-only W10.3A explanation presentation; no model training or data writes."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st


LABELS = {
    "kpi1_late_delivery": (
        "Late-delivery probability",
        "percentage points",
        100.0,
    ),
    "kpi2_shortage": (
        "Incremental shortage exposure",
        "units",
        1.0,
    ),
    "kpi3_emergency_premium": (
        "Emergency procurement premium",
        "currency units",
        1.0,
    ),
}


@st.cache_data(show_spinner=False)
def read_report(path, mtime_ns):
    with Path(path).open("r", encoding="utf-8") as fh:
        report = json.load(fh)

    if report.get("data_scope") != "validation only; independent test not read":
        raise ValueError("Unexpected explanation data scope")

    if not all(
        report.get("models", {}).get(k, {}).get("status") == "PASS"
        for k in LABELS
    ):
        raise ValueError(
            "Report does not contain three completed KPI explanations"
        )

    return report


def render_report(path):
    st.subheader("Model Explainability | Validation Evidence")

    st.caption(
        "Read-only W10.3A explanations. Historical validation cases "
        "are not the sidebar-selected PO."
    )

    file = Path(path)

    if not file.is_file():
        st.error(
            f"Explainability report missing: {file}. Run W10.3A first."
        )
        return

    try:
        report = read_report(str(file), file.stat().st_mtime_ns)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"Cannot load validated explanation report: {exc}")
        return

    kpi = st.selectbox(
        "KPI model",
        list(LABELS),
        format_func=lambda x: LABELS[x][0],
    )

    name, units, scale = LABELS[kpi]
    result = report["models"][kpi]

    st.markdown("#### Global predictor importance")

    st.caption(
        "Increase in validation mean absolute error when a feature "
        "is shuffled. Larger positive values indicate greater "
        "predictive usefulness; negative values do not imply "
        "a protective causal effect."
    )

    importance = pd.DataFrame(result["global_importance"])

    importance = importance.rename(
        columns={
            "feature": "Predictor",
            "mean_increase_in_mae": "MAE increase",
            "std_increase_in_mae": "Std. deviation",
        }
    )

    st.bar_chart(
        importance.head(10).set_index("Predictor")["MAE increase"],
        horizontal=True,
    )

    st.dataframe(
        importance,
        hide_index=True,
        width="stretch",
    )

    st.markdown("#### Individual validation-case attribution")

    cases = result["local_explanations"]

    choice = st.selectbox(
        "Historical validation example",
        range(len(cases)),
        index=1 if len(cases) > 1 else 0,
        format_func=lambda i: (
            f"Example {i+1} · "
            f"PO {cases[i].get('PO_ID', 'unknown')} · "
            f"{cases[i].get('Review_Date', 'date unavailable')}"
        ),
    )

    case = cases[choice]

    base = float(case["baseline_reference_prediction"]) * scale
    pred = float(case["prediction"]) * scale

    a, b, c = st.columns(3)

    a.metric(
        f"Reference ({units})",
        f"{base:,.2f}",
    )

    b.metric(
        f"Prediction ({units})",
        f"{pred:,.2f}",
    )

    c.metric(
        f"Difference ({units})",
        f"{pred-base:+,.2f}",
    )

    contrib = pd.DataFrame(case["contributions"])

    contrib["contribution"] = (
        pd.to_numeric(contrib["contribution"]) * scale
    )

    contrib = contrib.sort_values(
        "contribution",
        key=lambda s: s.abs(),
        ascending=False,
    )

    if contrib["contribution"].abs().max() > 1e-8:
        st.bar_chart(
            contrib.set_index("feature")["contribution"],
            horizontal=True,
        )
    else:
        st.info(
            "This is the reference observation. "
            "All feature contributions are approximately zero."
        )
    contrib["contribution"] = (
        contrib["contribution"]
        .mask(contrib["contribution"].abs() < 1e-8, 0.0)
        .round(4)
    )
    st.dataframe(
        contrib.rename(
            columns={
                "feature": "Predictor",
                "observed_value": "Observed",
                "reference_value": "Reference",
                "contribution": f"Contribution ({units})",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    st.caption(
        f"Numerical reconstruction error: "
        f"{float(case['reconstruction_error'])*scale:.3g} {units}. "
        "Monte Carlo permutation-path attribution against ONE fixed "
        "reference observation; not TreeSHAP or causal inference."
    )

    nonzero = contrib.loc[
        contrib["contribution"].abs() > 1e-8
    ]

    if nonzero.empty:
        st.info(
            "This example is the reference observation; all feature "
            "contributions are approximately zero. Choose another "
            "example for an informative comparison."
        )
    else:
        main = nonzero.iloc[0]

        direction = (
            "higher"
            if main["contribution"] > 0
            else "lower"
        )

        comparison = (
            "higher"
            if pred >= base
            else "lower"
        )

        st.info(
            f"Explanation: Compared with the selected reference case, "
            f"the model's {name.lower()} estimate is "
            f"{abs(pred-base):,.2f} {units} {comparison}. "
            f"The largest absolute attributed driver is "
            f"{main['feature']}, contributing "
            f"{abs(main['contribution']):,.2f} {units} "
            f"toward a {direction} estimate. "
            "Other features offset or reinforce this effect."
        )

    st.warning(
        "Synthetic-data demonstration. KPI 1 probabilities are not "
        "calibrated. KPI 2 and KPI 3 targets are simulated outcomes, "
        "not realized future outcomes. Attributions are model-relative, "
        "not causal. Historical validation examples are NOT "
        "explanations for the currently selected sidebar PO."
    )
