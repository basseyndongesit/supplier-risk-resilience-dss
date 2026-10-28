#!/usr/bin/env python3
"""Read-only frozen three-KPI scorer for W10.3B.2A.

Input: approved live_features.csv (three rows for one PO/review).
No fitting, no targets, no model writes, no independent-test access.
"""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

EXPECTED = {
    'kpi1': ('99103fdf772ba131ad90d15b7d7e8bbee44c24e558acc252bdd9fd9efe020b88', 'predictive_model_output/random_forest.joblib'),
    'kpi2': ('014edabd936c91f67a842e34485b5ffb1ba09af2b522d0eef8eca2e8351e39ad', 'w10_2b_model_output/kpi2_shortage_validation_selected.joblib'),
    'kpi3': ('e8b86ead4bdc2040642a88a0eb0993f35d30438231d7bf222f3a3955d2400013', 'w10_2b_model_output/kpi3_emergency_premium_validation_selected.joblib'),
}
KPI1_FEATURES = ['Order_Quantity', 'Planned_Lead_Days', 'Days_To_Promise', 'Supplier_Completed_90d', 'Supplier_Late_Rate_90d', 'Supplier_History_Missing', 'Supplier_Type', 'Item_Category', 'Review_Month']


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_frozen(name, path):
    path = Path(path)
    observed = sha256(path)
    if observed != EXPECTED[name][0]:
        raise ValueError(f'{name}: frozen model hash mismatch: {observed}')
    artifact = joblib.load(path)  # Only load locally trusted frozen project artifacts.
    model = artifact['model'] if isinstance(artifact, dict) else artifact
    if not hasattr(model, 'predict'):
        raise TypeError(f'{name}: artifact has no predict method')
    return artifact, model, observed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--features-csv', default='w10_3b2a_output/live_features.csv')
    for name in EXPECTED:
        ap.add_argument('--' + name + '-model', default=EXPECTED[name][1])
    ap.add_argument('--output-dir', default='w10_3b2a_output')
    args = ap.parse_args()

    frame = pd.read_csv(args.features_csv)
    if len(frame) != 3 or sorted(frame['Delay_Scenario_Days'].tolist()) != [3, 5, 7]:
        raise ValueError('Expected exactly three scenario rows: 3, 5, 7 days')
    if frame[['PO_ID', 'Review_Date']].drop_duplicates().shape[0] != 1:
        raise ValueError('Expected exactly one PO/review-date combination')
    frame = frame.sort_values('Delay_Scenario_Days').reset_index(drop=True)
    if frame.isna().any().any():
        # A missing supplier late rate may be legitimate with Supplier_History_Missing=1.
        missing = frame.columns[frame.isna().any()].tolist()
        if missing != ['Supplier_Late_Rate_90d'] or not (frame['Supplier_History_Missing'] == 1).all():
            raise ValueError(f'Unexpected missing feature(s): {missing}')

    a1, m1, h1 = load_frozen('kpi1', args.kpi1_model)
    a2, m2, h2 = load_frozen('kpi2', args.kpi2_model)
    a3, m3, h3 = load_frozen('kpi3', args.kpi3_model)
    f2 = a2.get('features') if isinstance(a2, dict) else None
    f3 = a3.get('features') if isinstance(a3, dict) else None
    if not f2 or not f3:
        raise ValueError('Frozen KPI2/KPI3 artifacts must declare their approved features')
    for name, cols in [('KPI1', KPI1_FEATURES), ('KPI2', f2), ('KPI3', f3)]:
        missing = set(cols) - set(frame.columns)
        if missing:
            raise ValueError(f'{name} missing features: {sorted(missing)}')

    x1 = frame.loc[[0], KPI1_FEATURES].copy()
    x1['Review_Month'] = x1['Review_Month'].astype(int).astype(str)
    p1 = float(m1.predict_proba(x1)[0, 1])
    if not np.isfinite(p1) or not 0 <= p1 <= 1:
        raise ValueError('Invalid KPI1 probability score')
    x2 = frame[f2].copy()
    x3 = frame[f3].copy()
    raw2 = np.asarray(m2.predict(x2), dtype=float)
    raw3 = np.asarray(m3.predict(x3), dtype=float)
    if not np.isfinite(raw2).all() or not np.isfinite(raw3).all():
        raise ValueError('Nonfinite KPI2/KPI3 prediction')
    shortage = np.maximum(0.0, raw2)
    direct_cost = np.maximum(0.0, raw3)
    premium = frame['Unit_Cost_Premium'].to_numpy(dtype=float)
    if not np.isfinite(premium).all() or (premium < 0).any():
        raise ValueError('Invalid cost premium')
    chained_cost = shortage * premium

    out = pd.DataFrame({
        'PO_ID': frame.PO_ID,
        'Review_Date': frame.Review_Date,
        'Delay_Scenario_Days': frame.Delay_Scenario_Days,
        'Late_Delivery_Model_Score': [p1] * 3,
        'Predicted_Incremental_Shortage_Units': shortage,
        'KPI3_Direct_Predicted_Emergency_Premium': direct_cost,
        'KPI3_Chained_Predicted_Emergency_Premium': chained_cost,
        'Unit_Cost_Premium': premium,
    })
    result = {
        'status': 'PREDICTIONS_GENERATED_PENDING_QA',
        'po_id': int(frame.PO_ID.iloc[0]),
        'review_date': str(frame.Review_Date.iloc[0]),
        'source_feature_csv_sha256': sha256(args.features_csv),
        'frozen_model_sha256': {'kpi1': h1, 'kpi2': h2, 'kpi3': h3},
        'kpi1_review_month_cast_to_string': True,
        'kpi1_score_shared_across_delay_scenarios': True,
        'kpi2_negative_raw_clipped_count': int((raw2 < 0).sum()),
        'kpi3_negative_raw_clipped_count': int((raw3 < 0).sum()),
        'kpi2_scenario_monotonic': bool(np.all(np.diff(shortage) >= -1e-10)),
        'kpi3_direct_scenario_monotonic': bool(np.all(np.diff(direct_cost) >= -1e-10)),
        'kpi3_chained_scenario_monotonic': bool(np.all(np.diff(chained_cost) >= -1e-10)),
        'limitations': [
            'Synthetic simulator surrogate outcomes; not observed future results.',
            'KPI1 risk scores are uncalibrated; do not interpret as verified event frequencies.',
            'Direct and chained KPI3 estimates are distinct; chained uses predicted KPI2 shortage, not actual shortage.',
            'Three-scenario monotonicity is reported, not enforced.',
            'No attribution or business narrative is calculated in this scoring stage.',
        ],
    }
    folder = Path(args.output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    out.to_csv(folder / 'live_predictions.csv', index=False)
    (folder / 'live_prediction_report.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(out.to_string(index=False, float_format=lambda x: f'{x:.4f}'))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
