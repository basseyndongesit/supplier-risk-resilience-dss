#!/usr/bin/env python3
"""W10.3B.3A: read-only, PO-specific local explanation, independently testable.

Uses only frozen models, original point-in-time live features, and a single
validation-partition reference observation. Never reads test data or targets.
Attributions are approximate permutation-path Shapley, not causal or TreeSHAP.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from w10_3b2a_live_features import build as build_live_features
from w10_3b2a_score_frozen import EXPECTED, KPI1_FEATURES, load_frozen

SEED = 84735


def normalize(frame, columns, name):
    out = frame.loc[:, columns].copy().reset_index(drop=True)
    if name == 'kpi1':
        out['Review_Month'] = pd.to_numeric(out['Review_Month'], errors='raise').astype(int).astype(str)
    return out


def model_output(model, frame, name):
    if name == 'kpi1':
        result = np.asarray(model.predict_proba(frame)[:, 1], dtype=float)
    else:
        result = np.maximum(0.0, np.asarray(model.predict(frame), dtype=float))
    if not np.isfinite(result).all():
        raise ValueError(f'{name}: nonfinite predictions')
    return result


def attribute(model, observed, reference, name, paths=16, seed=SEED):
    """Return contributions that reconstruct prediction relative to one reference row.

    Every permutation path telescopes exactly. Finite paths affect allocation
    across features, not the reconstruction identity.
    """
    if paths < 1:
        raise ValueError('paths must be >= 1')
    if len(observed) != 1 or len(reference) != 1:
        raise ValueError('Expected one observed and one reference row')
    if list(observed.columns) != list(reference.columns):
        raise ValueError('Observed/reference feature columns must match in order')
    cols = list(observed.columns)
    baseline = float(model_output(model, reference, name)[0])
    actual = float(model_output(model, observed, name)[0])
    rng = np.random.default_rng(seed)
    contributions = np.zeros(len(cols), dtype=float)
    for _ in range(paths):
        order = rng.permutation(len(cols))
        current = reference.copy()
        previous = baseline
        for j in order:
            column = cols[j]
            current.loc[0, column] = observed.loc[0, column]
            now = float(model_output(model, current, name)[0])
            contributions[j] += now - previous
            previous = now
    contributions /= paths
    error = baseline + float(contributions.sum()) - actual
    if abs(error) > 1e-7 * max(1.0, abs(actual)):
        raise ValueError(f'{name}: reconstruction failed ({error})')
    entries = [dict(feature=c, observed_value=str(observed.loc[0, c]),
                    reference_value=str(reference.loc[0, c]), contribution=float(v))
               for c, v in zip(cols, contributions)]
    entries.sort(key=lambda r: -abs(r['contribution']))
    return dict(reference_prediction=baseline, prediction=actual,
                contribution_sum=float(contributions.sum()), reconstruction_error=float(error),
                attribution_method='Monte Carlo permutation-path Shapley approximation against one validation reference row',
                paths=paths, contributions=entries)


def explain(db, po_id, review_date, validation_csv, paths=16, scenario=7):
    if scenario not in (3, 5, 7):
        raise ValueError('scenario must be 3, 5, or 7')
    validation_path = Path(validation_csv)
    if 'test' in validation_path.name.lower():
        raise ValueError('Independent test files must never be used as reference')
    validation = pd.read_csv(validation_path, low_memory=False)
    if validation.empty:
        raise ValueError('Validation reference CSV is empty')
    if 'partition' not in validation.columns or not validation['partition'].eq('validation').all():
        raise ValueError('Reference CSV must contain only rows marked partition=validation')
    if {'PO_ID', 'Review_Date'}.issubset(validation.columns):
        validation = validation.sort_values(['PO_ID', 'Review_Date'], kind='stable').reset_index(drop=True)
    live = build_live_features(db, int(po_id), str(review_date))
    observed_row = live.loc[live['Delay_Scenario_Days'] == scenario]
    if len(observed_row) != 1:
        raise ValueError('Expected exactly one live row for selected delay scenario')
    # The reference is the first deterministically sorted VALIDATION observation.
    # No observed future outcomes or validation targets are used in explanations.
    ref_row = validation.iloc[[0]]
    result = dict(status='ATTRIBUTIONS_GENERATED_PENDING_QA', po_id=int(po_id),
                  review_date=str(review_date), delay_scenario_days=scenario,
                  reference_partition='validation', reference_selection='first row sorted by PO_ID and Review_Date',
                  reference_po_id=str(ref_row.PO_ID.iloc[0]) if 'PO_ID' in ref_row else None,
                  data_scope='Original PO, point-in-time features; no test data, no targets, no retraining',
                  models={}, limitations=[
                      'Local contributions explain model behavior relative to ONE validation reference observation.',
                      'Attributions are not causal and may be sensitive to feature correlation and reference selection.',
                      'The KPI1 score is uncalibrated; do not interpret it as a verified event frequency.',
                      'KPI2 and KPI3 targets are retrospective synthetic simulator outputs, not observed future outcomes.',
                      'KPI3 direct model is explained; chained KPI3 is a deterministic product of predicted KPI2 shortage and unit premium.',
                      'Clipped model predictions are explained after clipping, matching dashboard outputs.',
                  ])
    for idx, name in enumerate(('kpi1', 'kpi2', 'kpi3')):
        artifact, model, digest = load_frozen(name, EXPECTED[name][1])
        cols = KPI1_FEATURES if name == 'kpi1' else artifact['features']
        if not set(cols).issubset(validation.columns) or not set(cols).issubset(observed_row.columns):
            raise ValueError(f'{name}: approved feature(s) missing from validation or live data')
        observed = normalize(observed_row, cols, name)
        reference = normalize(ref_row, cols, name)
        explanation = attribute(model, observed, reference, name, paths=paths, seed=SEED + idx)
        explanation['model_sha256'] = digest
        result['models'][name] = explanation
    result['chained_kpi3'] = {
        'predicted_shortage_units': result['models']['kpi2']['prediction'],
        'unit_cost_premium': float(observed_row.Unit_Cost_Premium.iloc[0]),
        'derived_premium': result['models']['kpi2']['prediction'] * float(observed_row.Unit_Cost_Premium.iloc[0]),
        'note': 'Derived quantity, not a separately attributed prediction. Direct KPI3 attribution is above.'
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--po-id', type=int, required=True)
    parser.add_argument('--review-date', required=True)
    parser.add_argument('--db', default='supplier_risk_output/supplier_risk.db')
    parser.add_argument('--validation-csv', default='w10_2a_dataset_output/validation.csv')
    parser.add_argument('--scenario', type=int, choices=(3, 5, 7), default=7)
    parser.add_argument('--paths', type=int, default=16)
    parser.add_argument('--output', default='w10_3b3_output/local_explanation.json')
    args = parser.parse_args()
    report = explain(args.db, args.po_id, args.review_date, args.validation_csv, args.paths, args.scenario)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print('Status:', report['status'])
    print('PO:', report['po_id'], 'Review:', report['review_date'], 'Delay:', report['delay_scenario_days'])
    for name, details in report['models'].items():
        print(f"{name}: reference={details['reference_prediction']:.8f} prediction={details['prediction']:.8f} "
              f"reconstruction_error={details['reconstruction_error']:.3g}")
        for row in details['contributions'][:5]:
            print(f"  {row['feature']}: {row['contribution']:+.6f}")
    print('Report:', path)


if __name__ == '__main__':
    main()
