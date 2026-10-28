"""Pure, read-only feature-substitution analysis for the frozen Supplier Risk DSS model.

These are associations learned by the model, NOT causal intervention estimates.
"""
import numpy as np
import pandas as pd
from predictive_risk_3c2 import FEATURES, build_features


def baseline_for_po(db_path, queue, review_date, po_id):
    matches = queue.loc[queue['PO_ID'].astype(str) == str(po_id)]
    if len(matches) != 1:
        raise ValueError('Selected PO must appear exactly once in the eligible review queue')
    return build_features(db_path, matches, review_date).iloc[[0]].copy()


def compare_hypothetical(model, baseline, *, order_quantity, planned_lead_days,
                         supplier_completed_90d, supplier_late_rate_90d):
    """Return baseline and counterfactual scores; never write or refit anything."""
    if len(baseline) != 1 or list(baseline.columns) != FEATURES:
        raise ValueError('Expected one observation with the approved nine feature columns')
    quantity = float(order_quantity)
    lead = int(planned_lead_days)
    completed = int(supplier_completed_90d)
    rate = None if supplier_late_rate_90d is None else float(supplier_late_rate_90d)
    if not np.isfinite(quantity) or quantity <= 0:
        raise ValueError('Order quantity must be finite and greater than zero')
    if lead < 1 or lead > 365:
        raise ValueError('Planned lead days must be between 1 and 365')
    if lead < int(baseline.iloc[0]['Days_To_Promise']):
        raise ValueError('Planned lead days cannot be shorter than remaining days to promise while the review and promise dates stay fixed')
    if completed < 0 or completed > 100000:
        raise ValueError('Completed supplier POs must be between 0 and 100,000')
    if completed == 0:
        if rate is not None and not np.isnan(rate):
            raise ValueError('Late rate must be missing when there are zero completed supplier POs')
        rate = np.nan
    elif rate is None or not np.isfinite(rate) or not 0 <= rate <= 1:
        raise ValueError('Late rate must be between zero and one when supplier history exists')
    changed = baseline.copy(deep=True)
    ix = changed.index[0]
    changed.at[ix, 'Order_Quantity'] = quantity
    changed.at[ix, 'Planned_Lead_Days'] = lead
    changed.at[ix, 'Supplier_Completed_90d'] = completed
    changed.at[ix, 'Supplier_Late_Rate_90d'] = rate
    changed.at[ix, 'Supplier_History_Missing'] = int(completed == 0)
    both = pd.concat([baseline, changed], ignore_index=True)[FEATURES]
    probs = np.asarray(model.predict_proba(both), dtype=float)
    if probs.shape != (2, 2) or not np.isfinite(probs).all() or ((probs < 0) | (probs > 1)).any():
        raise ValueError('Model produced invalid probabilities')
    base, alternative = map(float, probs[:, 1])
    return {'baseline_probability': base,
            'hypothetical_probability': alternative,
            'change_percentage_points': (alternative - base) * 100,
            'baseline_features': baseline.copy(),
            'hypothetical_features': changed}
