"""Read-only evidence recap for final human decision screen."""
import os
import sqlite3
import pandas as pd
import streamlit as st
from w10_3b4_dashboard import EXPECTED, frozen_models, score_live, build_live_features, scenario_key


def render_decision_evidence(db, queue, review_date, po_id, detail, scenarios):
    st.markdown('#### Decision evidence summary — original PO')
    st.write(f"**PO:** {po_id} | **Review date:** {review_date} | **Supplier:** {str(detail['Supplier_Name']).removeprefix('Synthetic ')}")
    if not scenarios.empty:
        flag = scenarios.Management_Review_Flag.iloc[0]
        st.write('**Management review:**', 'Undetermined' if pd.isna(flag) else 'Yes' if int(flag) else 'No')
        st.write(f"**Stored retrospective maximum additional shortage:** {scenarios.Incremental_Shortage_Units.max():,.2f} units")
        st.caption('Stored simulator outcomes are retrospective scenario assessments, not observed future losses.')
    try:
        features = build_live_features(db, int(po_id), review_date)
        paths = tuple((name, os.environ.get(f'SUPPLIER_DSS_{name.upper()}_MODEL', default), digest)
                      for name, (digest, default) in EXPECTED.items())
        models = frozen_models(paths)
        risk, predictions, _ = score_live(features, models)
        c1, c2, c3 = st.columns(3)
        c1.metric('Original late-delivery model score', f'{risk:.1%}')
        c2.metric('Maximum predicted additional shortage', f"{predictions['Additional shortage (units)'].max():,.2f} units")
        c3.metric('Maximum chained emergency premium', f"{predictions['Chained premium (currency units)'].max():,.2f}")
        st.caption('Predicted maximums across 3/5/7-day hypothetical delays; not expected losses. The KPI 1 score is uncalibrated.')
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, ImportError) as exc:
        st.warning(f'Predictive recap unavailable: {exc}. Review Screen 8 before deciding.')
    saved = st.session_state.get(scenario_key(db, review_date, po_id))
    if saved is not None:
        st.info('A Screen 6 hypothetical comparison exists for this PO/date. It is NOT applied to the original predictions above. Review Screen 8 to compare the hypothetical KPI 1 score.')
    st.caption('For full predictive evidence and on-demand local explanations, open Screen 8. Screen 7 contains independent validation examples.')
    st.divider()
