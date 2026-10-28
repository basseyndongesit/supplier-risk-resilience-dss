"""Read-only frozen-model inference for historical Supplier Risk DSS review queues."""
from pathlib import Path
import hashlib
import json
import joblib
import numpy as np
import pandas as pd
from dss_core import supplier_history, connect

FEATURES = ['Order_Quantity','Planned_Lead_Days','Days_To_Promise',
            'Supplier_Completed_90d','Supplier_Late_Rate_90d','Supplier_History_Missing',
            'Supplier_Type','Item_Category','Review_Month']
MODEL_HASH = '99103fdf772ba131ad90d15b7d7e8bbee44c24e558acc252bdd9fd9efe020b88'

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def load_locked_model(model_path='predictive_model_output/random_forest.joblib',
                      lock_path='predictive_model_lock/model_lock_manifest.json'):
    """Only load trusted locally produced joblib artifacts after SHA-256 verification."""
    model_path, lock_path = Path(model_path), Path(lock_path)
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    if lock.get('selected_model') != 'random_forest' or lock.get('model_features') != FEATURES:
        raise ValueError('Unexpected frozen model or feature schema in lock manifest')
    if lock.get('status') != 'MODEL_ARTIFACT_LOCKED_TEST_NOT_EVALUATED':
        raise ValueError('Unexpected model-lock status')
    expected = lock.get('source_files_sha256', {})
    matching = [v for k, v in expected.items() if Path(k.replace('\\', '/')).name == model_path.name]
    if len(matching) != 1 or matching[0] != MODEL_HASH:
        raise ValueError('Model hash missing or inconsistent in lock manifest')
    if sha256(model_path) != MODEL_HASH:
        raise ValueError('Frozen model SHA-256 mismatch; refusing to load')
    model = joblib.load(model_path)
    if list(getattr(model, 'feature_names_in_', [])) != FEATURES:
        raise ValueError('Loaded model does not expect the approved feature order')
    if not hasattr(model, 'predict_proba'):
        raise ValueError('Loaded model lacks probability inference')
    return model

def build_features(db_path, queue, review_date):
    """Build point-in-time predictors from queue and date-limited supplier history."""
    if queue.empty:
        return pd.DataFrame(columns=FEATURES, index=queue.index)
    needed = {'PO_ID','Supplier_ID','PO_Date','Promised_Delivery_Date',
              'Order_Quantity','Item_ID'}
    if needed - set(queue.columns):
        raise ValueError(f'Missing queue fields: {sorted(needed-set(queue.columns))}')
    review = pd.Timestamp(review_date)
    orders = pd.to_datetime(queue['PO_Date'], errors='raise')
    promises = pd.to_datetime(queue['Promised_Delivery_Date'], errors='raise')
    if not ((orders <= review) & (review < promises) & (promises <= review + pd.Timedelta(days=28))).all():
        raise ValueError('Queue contains orders outside the approved 28-day review window')
    supplier_ids = queue['Supplier_ID'].astype(int).unique().tolist()
    histories = {sid: supplier_history(db_path, sid, review_date) for sid in supplier_ids}
    counts = queue['Supplier_ID'].astype(int).map(lambda sid: histories[sid]['completed_last_90_days'])
    rates = queue['Supplier_ID'].astype(int).map(lambda sid: histories[sid]['late_rate_last_90_days'])
    frame = pd.DataFrame(index=queue.index)
    frame['Order_Quantity'] = pd.to_numeric(queue['Order_Quantity'], errors='raise')
    frame['Planned_Lead_Days'] = (promises - orders).dt.days
    frame['Days_To_Promise'] = (promises - review).dt.days
    frame['Supplier_Completed_90d'] = counts
    frame['Supplier_Late_Rate_90d'] = rates
    frame['Supplier_History_Missing'] = (counts == 0).astype(int)
    # Existing five-screen review_queue does not expose these two attributes.
    # Fetch approved static attributes read-only rather than changing dss_core.
    with connect(db_path) as con:
        suppliers = pd.read_sql_query('SELECT Supplier_ID, Supplier_Type FROM Suppliers', con)
        items = pd.read_sql_query('SELECT Item_ID, Item_Category FROM Items', con)
    supplier_types = suppliers.set_index('Supplier_ID')['Supplier_Type']
    item_categories = items.set_index('Item_ID')['Item_Category']
    frame['Supplier_Type'] = queue['Supplier_ID'].astype(int).map(supplier_types).astype('string').fillna('UNKNOWN').astype(str)
    frame['Item_Category'] = queue['Item_ID'].astype(int).map(item_categories).astype('string').fillna('UNKNOWN').astype(str)
    frame['Review_Month'] = str(review.month)
    if frame['Order_Quantity'].isna().any() or (frame['Order_Quantity'] <= 0).any():
        raise ValueError('Invalid order quantities')
    return frame[FEATURES]

def rank_review_queue(model, db_path, queue, review_date):
    x = build_features(db_path, queue, review_date)
    if x.empty:
        return queue.copy()
    p = np.asarray(model.predict_proba(x)[:, 1], dtype=float)
    if len(p) != len(queue) or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError('Invalid model probabilities')
    result = queue.copy()
    result['Model_Late_Probability'] = p
    result['Supplier_History_Missing'] = x['Supplier_History_Missing'].to_numpy()
    result = result.sort_values(['Model_Late_Probability', 'PO_ID'], ascending=[False, True]).reset_index(drop=True)
    result.insert(0, 'Model_Rank', np.arange(1, len(result) + 1))
    return result
