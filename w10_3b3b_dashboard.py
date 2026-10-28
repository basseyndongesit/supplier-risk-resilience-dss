"""W10.3B.2B: read-only, baseline-first integrated PO decision dashboard.

Only the explicitly approved Screen 7 late-delivery feature substitutions can be
replayed here. Retrospective simulator outputs and KPI2/3 baseline model scores
are never recomputed from Screen 7 what-if inputs.
"""
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from w10_3b2a_live_features import build as build_live_features
from w10_3b2a_score_frozen import EXPECTED, KPI1_FEATURES, load_frozen
from predictive_whatif_3c3 import baseline_for_po, compare_hypothetical
from dss_core import connect
from w10_3b3b_live_ui import render_local_explanations


def scenario_key(db, review_date, po_id):
    """Unique per source database, historical date, and PO."""
    return f"w10_3b2b:{Path(db).resolve()}:{review_date}:{po_id}"


def save_whatif(db, review_date, po_id, outcome):
    """Persist only verified Screen 7 comparison in this Streamlit session."""
    key = scenario_key(db, review_date, po_id)
    st.session_state[key] = {
        'baseline_features': outcome['baseline_features'].copy(deep=True),
        'hypothetical_features': outcome['hypothetical_features'].copy(deep=True),
        'baseline_probability': float(outcome['baseline_probability']),
        'hypothetical_probability': float(outcome['hypothetical_probability']),
    }


def clear_whatif(db, review_date, po_id):
    st.session_state.pop(scenario_key(db, review_date, po_id), None)


@st.cache_resource(show_spinner=False)
def frozen_models(model_paths_and_hashes):
    """Load only hash-verified local model artifacts. No model training."""
    models = {}
    for name, path, expected_hash in model_paths_and_hashes:
        if EXPECTED[name][0] != expected_hash:
            raise ValueError(f'{name}: unexpected frozen model identity')
        artifact, model, observed_hash = load_frozen(name, path)
        models[name] = (artifact, model)
    return models


def score_live(frame, models):
    """Predict on approved 3/5/7-day feature rows, without writing files."""
    if len(frame) != 3 or sorted(frame.Delay_Scenario_Days.tolist()) != [3, 5, 7]:
        raise ValueError('Expected exactly three 3/5/7-day scenario rows')
    frame = frame.sort_values('Delay_Scenario_Days').reset_index(drop=True)
    a1, m1 = models['kpi1']
    a2, m2 = models['kpi2']
    a3, m3 = models['kpi3']
    f2, f3 = a2['features'], a3['features']
    for name, cols in [('KPI1', KPI1_FEATURES), ('KPI2', f2), ('KPI3', f3)]:
        if set(cols) - set(frame.columns):
            raise ValueError(f'{name}: missing approved features')
    x1 = frame.loc[[0], KPI1_FEATURES].copy()
    x1['Review_Month'] = x1['Review_Month'].astype(int).astype(str)
    p = float(m1.predict_proba(x1)[0, 1])
    shortage_raw = np.asarray(m2.predict(frame[f2]), dtype=float)
    premium_raw = np.asarray(m3.predict(frame[f3]), dtype=float)
    unit_premium = frame.Unit_Cost_Premium.to_numpy(dtype=float)
    if not np.isfinite(p) or not 0 <= p <= 1 or not np.isfinite(shortage_raw).all() or not np.isfinite(premium_raw).all():
        raise ValueError('Invalid model predictions')
    if not np.isfinite(unit_premium).all() or (unit_premium < 0).any():
        raise ValueError('Invalid unit-cost premium')
    shortage = np.maximum(shortage_raw, 0)
    direct = np.maximum(premium_raw, 0)
    result = pd.DataFrame({
        'Delay (days)': frame.Delay_Scenario_Days.astype(int),
        'Additional shortage (units)': shortage,
        'Direct premium (currency units)': direct,
        'Chained premium (currency units)': shortage * unit_premium,
    })
    return p, result, {'kpi2_clipped': int((shortage_raw < 0).sum()),
                       'kpi3_clipped': int((premium_raw < 0).sum()),
                       'kpi2_nondecreasing': bool(np.all(np.diff(shortage) >= -1e-10)),
                       'direct_nondecreasing': bool(np.all(np.diff(direct) >= -1e-10)),
                       'chained_nondecreasing': bool(np.all(np.diff(shortage * unit_premium) >= -1e-10))}


def decision_for_po(db, review_date, po_id):
    path = Path(os.environ.get('SUPPLIER_DSS_DECISIONS', 'decision_records_local.db')).resolve()
    if path == Path(db).resolve():
        raise ValueError('Decision record database must be separate from source database')
    if not path.is_file():
        return None
    with sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True) as con:
        exists = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='Human_Decisions'").fetchone()
        if not exists:
            return None
        record = pd.read_sql_query('SELECT * FROM Human_Decisions WHERE PO_ID=? AND Review_Date=?',
                                   con, params=(str(po_id), str(review_date)))
    return record.iloc[0].to_dict() if len(record) else None


def business_narrative(p, predictions, flag, criticality):
    max_shortage = float(predictions['Additional shortage (units)'].max())
    max_cost = float(predictions['Chained premium (currency units)'].max())
    risk = f'The late-delivery model assigns a score of {p:.1%}. This score is not a calibrated event probability.'
    if max_shortage < 0.5:
        consequence = 'The predicted additional shortage is below half a unit in all tested delay scenarios; modeled exposure is negligible at this scale.'
    else:
        consequence = (f'The highest modeled additional shortage across the three delays is {max_shortage:,.1f} units. '
                       'Check available stock and demand before deciding on mitigation.')
    financial = (f'The highest chained emergency purchasing premium is approximately {max_cost:,.2f} currency units. '
                 'This is an incremental premium estimate, not total purchasing cost.')
    if pd.isna(flag):
        screening = 'The stored management-review flag is undetermined; investigate missing screening evidence.'
    elif int(flag) == 1:
        screening = 'The stored operational screening rules request management review; this is not an automatic purchase instruction.'
    else:
        screening = 'The stored operational screening rules did not flag this PO; the model score is separate from that screening result.'
    if criticality == 'High':
        screening += ' The item is marked high criticality.'
    return risk, consequence, financial, screening


def render_dashboard(db, queue, review_date, po_id, detail, stored_scenarios):
    st.subheader('Integrated Three-KPI Decision Dashboard')
    st.caption('Original PO baseline by default • Read-only historical review • Synthetic demonstration data')
    st.write(f"**Purchase order:** {po_id}  |  **Review date:** {review_date}  |  "
             f"**Supplier:** {str(detail['Supplier_Name']).removeprefix('Synthetic ')}")
    if len(queue.loc[queue.PO_ID.astype(str) == str(po_id)]) != 1:
        st.error('Selected PO is not unique in the historical review queue.')
        return
    try:
        # Hash-verified point-in-time extraction; no stored outcome targets are used.
        features = build_live_features(db, int(po_id), review_date)
        paths = tuple((name, os.environ.get(f'SUPPLIER_DSS_{name.upper()}_MODEL', default), digest)
                      for name, (digest, default) in EXPECTED.items())
        models = frozen_models(paths)
        baseline_p, predictions, qa = score_live(features, models)
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, ImportError) as exc:
        st.error(f'Live three-KPI inference unavailable: {exc}')
        return

    key = scenario_key(db, review_date, po_id)
    scenario = st.session_state.get(key)
    if scenario is None:
        st.info('No Screen 7 hypothetical scenario is saved for this PO and review date. Showing original values.')
        mode = 'Original PO'
    else:
        mode = st.radio('Prediction view', ['Original PO', 'Screen 7 hypothetical'], horizontal=True,
                        key=f'view:{key}')
        if st.button('Reset saved hypothetical inputs for this PO', key=f'reset:{key}'):
            clear_whatif(db, review_date, po_id)
            st.rerun()

    displayed_p = baseline_p
    if mode == 'Screen 7 hypothetical' and scenario is not None:
        try:
            baseline = baseline_for_po(db, queue, review_date, po_id)
            saved_original = scenario['baseline_features'][KPI1_FEATURES].reset_index(drop=True)
            current_original = baseline[KPI1_FEATURES].reset_index(drop=True)
            if not saved_original.equals(current_original):
                raise ValueError('Saved baseline no longer matches selected PO; reset scenario on Screen 7')
            modified = scenario['hypothetical_features'][KPI1_FEATURES].copy()
            model = models['kpi1'][1]
            displayed_p = float(model.predict_proba(modified)[0, 1])
            if not np.isfinite(displayed_p) or not 0 <= displayed_p <= 1:
                raise ValueError('Invalid hypothetical late-delivery score')
            st.warning('HYPOTHETICAL KPI 1 ONLY. KPI 2/3 below remain ORIGINAL PO predictions. No causal effect is implied.')
            changed = []
            for col in KPI1_FEATURES:
                old, new = baseline.iloc[0][col], modified.iloc[0][col]
                if not ((pd.isna(old) and pd.isna(new)) or old == new):
                    changed.append({'Input': col, 'Original': str(old), 'Hypothetical': str(new)})
            if changed:
                st.dataframe(pd.DataFrame(changed), hide_index=True, width='stretch')
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            st.error(f'Saved what-if scenario cannot be applied: {exc}')
            return

    c1, c2, c3 = st.columns(3)
    c1.metric('Late-delivery model score', f'{displayed_p:.1%}',
              delta=f'{(displayed_p-baseline_p)*100:+.1f} pp' if mode != 'Original PO' else None)
    c2.metric('Largest predicted additional shortage', f"{predictions['Additional shortage (units)'].max():,.2f} units")
    c3.metric('Largest chained emergency premium', f"{predictions['Chained premium (currency units)'].max():,.2f}")
    st.caption('The maximum is taken across 3/5/7-day delays; it is not an expected loss. Currency units are unspecified.')

    st.markdown('#### Predicted consequences of assumed delivery delays — original PO')
    st.dataframe(predictions, hide_index=True, width='stretch', column_config={
        'Additional shortage (units)': st.column_config.NumberColumn(format='%.4f'),
        'Direct premium (currency units)': st.column_config.NumberColumn(format='%.2f'),
        'Chained premium (currency units)': st.column_config.NumberColumn(format='%.2f'),
    })
    st.caption('Direct premium uses the separately trained KPI 3 model. Chained premium = predicted KPI 2 shortage × known unit-price premium; it had lower independent-test error. Negative raw model outputs are clipped to zero.')
    if not all((qa['kpi2_nondecreasing'], qa['direct_nondecreasing'], qa['chained_nondecreasing'])):
        st.warning('At least one predicted consequence decreases for a longer delay. Monotonicity is not enforced.')
    if qa['kpi2_clipped'] or qa['kpi3_clipped']:
        st.caption(f"Technical QA: {qa['kpi2_clipped']} KPI 2 and {qa['kpi3_clipped']} direct KPI 3 raw negative outputs clipped to zero.")

    st.markdown('#### Historical operational evidence (not model predictions)')
    flag = stored_scenarios.Management_Review_Flag.iloc[0] if not stored_scenarios.empty else np.nan
    st.write('**Management-review screening:**', 'Undetermined' if pd.isna(flag) else 'Yes' if int(flag) else 'No')
    if not stored_scenarios.empty:
        st.write(f"**Stored maximum incremental shortage:** {stored_scenarios.Incremental_Shortage_Units.max():,.2f} units")
        st.caption('Stored values are retrospective simulator assessments, not realized future outcomes. They are separate from frozen-model predictions.')

    st.markdown('#### What this means for your decision')
    for message in business_narrative(displayed_p, predictions, flag, detail['Item_Criticality']):
        st.write(message)
    if mode != 'Original PO':
        st.info(f'The hypothetical KPI 1 score differs from the original by {(displayed_p-baseline_p)*100:+.1f} percentage points. This is model sensitivity to substituted inputs, not a predicted effect of an operational intervention.')
    st.write('**Suggested human review:** Confirm supplier delivery status, inventory availability, item criticality, and feasible alternatives before recording an action.')

    render_local_explanations(db, po_id, review_date, baseline_p, predictions, mode=mode)

    st.markdown('#### Human decision record')
    try:
        record = decision_for_po(db, review_date, po_id)
    except (OSError, sqlite3.Error, ValueError) as exc:
        st.warning(f'Unable to read companion decision record: {exc}')
        record = None
    if record:
        st.dataframe(pd.DataFrame([record]), hide_index=True, width='stretch')
    else:
        st.caption('No human decision is recorded for this PO/review date. Use Screen 5 to record one.')
    st.caption('Screen 8 uses historical validation examples; the live explanation above is calculated independently for this selected original PO.')
    st.caption('Model outputs are based on synthetic simulator targets, not observed future shortages or costs. No automatic procurement decision is made.')
