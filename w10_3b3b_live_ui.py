"""W10.3B.3B: live, baseline-only local explanation section for Screen 9.

Explanations compare the selected original PO against one fixed validation row.
Never attributes Screen 7 hypothetical scores, and never modifies source data.
"""
from pathlib import Path
import math
import pandas as pd
import streamlit as st
from w10_3b3_local_explain import explain

LABELS = {
    'Supplier_Late_Rate_90d': 'Supplier late-delivery rate over 90 days',
    'Supplier_Completed_90d': 'Supplier completed orders over 90 days',
    'Demand_SMA_30d': 'Average daily demand over 30 days',
    'Delay_Scenario_Days': 'Assumed delivery delay',
    'Available_Inventory_at_review': 'Available inventory at review',
    'Safety_Stock_Level_at_review': 'Safety-stock level',
    'Unit_Cost_Premium': 'Emergency unit-price premium',
    'Order_Quantity': 'Purchase-order quantity',
    'Days_To_Promise': 'Days until promised delivery',
    'Planned_Lead_Days': 'Planned supplier lead time',
    'Item_Category': 'Item category',
    'Item_Criticality': 'Item criticality',
    'Supplier_Type': 'Supplier type',
    'Supplier_History_Missing': 'Missing supplier-history indicator',
    'Review_Month': 'Review month',
    'Normal_Unit_Cost': 'Normal unit cost',
    'Emergency_Unit_Cost': 'Emergency unit cost',
}
UNITS = {'kpi1': 'percentage points', 'kpi2': 'shortage units', 'kpi3': 'currency units'}
NAMES = {'kpi1': 'KPI 1 · Late-delivery score', 'kpi2': 'KPI 2 · Additional shortage',
         'kpi3': 'KPI 3 · Direct emergency premium'}


def display_amount(value, name):
    if name == 'kpi1':
        return f'{value * 100:+.2f} percentage points'
    return f'{value:+,.1f} {UNITS[name]}'


def narrative(name, model_result, max_features=3):
    """Noncausal, reference-relative English; deliberately avoids causal verbs."""
    if name not in NAMES:
        raise ValueError('Unknown KPI')
    contributions = [r for r in model_result['contributions'] if math.isfinite(float(r['contribution']))]
    contributions.sort(key=lambda r: abs(float(r['contribution'])), reverse=True)
    if name == 'kpi1':
        start = (f'The original PO has a model score of {model_result["prediction"]:.1%}, '
                 f'compared with {model_result["reference_prediction"]:.1%} for the validation reference.')
    else:
        start = (f'The original PO has a model estimate of {model_result["prediction"]:,.2f} '
                 f'{UNITS[name]}, compared with {model_result["reference_prediction"]:,.2f} '
                 f'for the validation reference.')
    selected = [r for r in contributions if abs(float(r['contribution'])) > 1e-8][:max_features]
    lines = [start]
    for r in selected:
        direction = 'higher' if float(r['contribution']) > 0 else 'lower'
        lines.append(f'{LABELS.get(r["feature"], r["feature"])} ({r["observed_value"]} versus '
                     f'{r["reference_value"]} in the reference) contributes '
                     f'{display_amount(abs(float(r["contribution"])), name).lstrip("+")} toward a {direction} model output '
                     'in this reference-relative explanation.')
    lines.append('These are approximate model contributions, not causal effects or recommendations to change these inputs.')
    return lines


@st.cache_data(show_spinner=False, max_entries=24)
def cached_explain(db, po_id, review_date, validation_csv, scenario, paths, db_mtime, validation_mtime, model_signatures):
    # File signatures are cache invalidation inputs. The independent engine
    # validates model hashes on every cache miss.
    return explain(db, po_id, review_date, validation_csv, paths=paths, scenario=scenario)


def render_local_explanations(db, po_id, review_date, baseline_p, predictions, mode='Original PO',
                              validation_csv='w10_2a_dataset_output/validation.csv'):
    with st.expander('Why did the models produce these predictions? (Original PO)', expanded=False):
        st.caption('Local explanations use ORIGINAL PO inputs only. Screen 7 hypothetical KPI 1 changes are not attributed here.')
        if mode != 'Original PO':
            st.info('Hypothetical view is active above. The explanations below still describe the ORIGINAL PO baseline, not the hypothetical score.')
        scenario = st.selectbox('Assumed delay to explain (days)', [3, 5, 7], index=2,
                                key=f'w10_3b3b_delay:{Path(db).resolve()}:{review_date}:{po_id}')
        st.caption('Method: 64 sampled permutation paths against one fixed validation observation. Results depend on that reference and may vary with path count.')
        request_key = f'w10_3b3b_requested:{Path(db).resolve()}:{review_date}:{int(po_id)}'
        requested = st.session_state.get(request_key)
        if requested != scenario:
            st.info('Detailed attributions are calculated only when requested. The baseline dashboard above remains available.')
            if not st.button('Generate explanations for this PO and delay',
                             key=f'w10_3b3b_generate:{Path(db).resolve()}:{review_date}:{int(po_id)}:{scenario}'):
                return
            st.session_state[request_key] = scenario
        if not Path(validation_csv).is_file():
            st.error(f'Validation-only reference file not found: {validation_csv}')
            return
        try:
            from w10_3b2a_score_frozen import EXPECTED
            import os
            signatures = []
            for name, (digest, default) in EXPECTED.items():
                path = Path(os.environ.get(f'SUPPLIER_DSS_{name.upper()}_MODEL', default))
                signatures.append((name, str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size))
            with st.spinner('Generating local explanations for the selected original PO. This may take a while on the first request...'):
                report = cached_explain(str(Path(db).resolve()), int(po_id), str(review_date),
                                        str(Path(validation_csv).resolve()), scenario, 64,
                                        Path(db).stat().st_mtime_ns, Path(validation_csv).stat().st_mtime_ns,
                                        tuple(signatures))
            model_data = report['models']
            row = predictions.loc[predictions['Delay (days)'] == scenario]
            if len(row) != 1:
                raise ValueError('Selected delay not found in Screen 9 predictions')
            expected = {'kpi1': float(baseline_p),
                        'kpi2': float(row.iloc[0]['Additional shortage (units)']),
                        'kpi3': float(row.iloc[0]['Direct premium (currency units)'])}
            for name in ('kpi1', 'kpi2', 'kpi3'):
                got = float(model_data[name]['prediction'])
                if not math.isclose(got, expected[name], rel_tol=1e-8, abs_tol=1e-7):
                    raise ValueError(f'{name}: explanation prediction does not match Screen 9 baseline ({got} vs {expected[name]})')
                err = float(model_data[name]['reconstruction_error'])
                if abs(err) > 1e-7 * max(1, abs(got)):
                    raise ValueError(f'{name}: attribution reconstruction check failed')
            st.success(f'Baseline prediction parity and attribution reconstruction verified for the {scenario}-day scenario.')
            st.caption(f'Validation reference: PO {report.get("reference_po_id", "unspecified")}; one reference observation, not an average or representative benchmark.')
            for name in ('kpi1', 'kpi2', 'kpi3'):
                result = model_data[name]
                st.markdown(f'##### {NAMES[name]}')
                for sentence in narrative(name, result):
                    st.write(sentence)
                top = [r for r in result['contributions'] if abs(float(r['contribution'])) > 1e-8][:8]
                if top:
                    chart = pd.DataFrame([{'Feature': LABELS.get(r['feature'], r['feature']),
                                           'Contribution': float(r['contribution']) * (100 if name == 'kpi1' else 1)}
                                          for r in top]).set_index('Feature')
                    st.bar_chart(chart, horizontal=True, x_label=('Percentage points' if name == 'kpi1' else UNITS[name]))
                with st.expander(f'Technical feature contributions — {name}'):
                    table = pd.DataFrame(result['contributions'])
                    table['feature'] = table['feature'].map(lambda x: LABELS.get(x, x))
                    if name == 'kpi1':
                        table['contribution'] *= 100
                    st.dataframe(table.rename(columns={'feature':'Feature','observed_value':'Original PO',
                                                        'reference_value':'Validation reference',
                                                        'contribution':'Contribution (' + ('pp' if name == 'kpi1' else UNITS[name]) + ')'}),
                                 hide_index=True, width='stretch')
            chained = report['chained_kpi3']
            st.markdown('##### Preferred chained emergency-premium estimate')
            st.write(f'Predicted shortage ({chained["predicted_shortage_units"]:,.2f} units) × '
                     f'known emergency unit-price premium ({chained["unit_cost_premium"]:,.2f} currency units/unit) '
                     f'= **{chained["derived_premium"]:,.2f} currency units**.')
            st.caption('The KPI 3 feature chart explains the separately trained DIRECT model, not the chained calculation. No direct attribution is claimed for the chained value.')
            st.caption('Synthetic retrospective simulator targets; uncalibrated KPI 1 score. Explanations are reference-relative, approximate, and noncausal. No automatic action is taken.')
        except Exception as exc:
            st.session_state.pop(request_key, None)
            st.error(f'Live local explanation unavailable or failed QA: {exc}')
