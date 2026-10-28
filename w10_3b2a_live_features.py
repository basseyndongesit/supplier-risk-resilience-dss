#!/usr/bin/env python3
"""W10.3B.2A: read-only, point-in-time three-scenario feature construction.
No training, target reads, model modification, or synthetic outcome substitution.
"""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np

from build_kpi_dataset_w10_2a import COMMON, COST

DB_HASH = '0c2bb19febb7f2a4ad9d2ab6a642450b1861021a283523eda44c5fec8e4f6573'

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()

def build(db_path, po_id, review_date):
    db=Path(db_path).resolve()
    if sha256(db)!=DB_HASH: raise ValueError('Database hash differs from accepted W10.2A source')
    day=pd.Timestamp(review_date).strftime('%Y-%m-%d')
    con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON')
    try:
        p=pd.read_sql_query('''SELECT p.PO_ID,p.Supplier_ID,p.Item_ID,p.Location_ID,p.PO_Date,
            p.Promised_Delivery_Date,p.Actual_Delivery_Date,p.Order_Quantity,
            p.Normal_Unit_Cost,p.Emergency_Unit_Cost,s.Supplier_Type,i.Item_Category,i.Item_Criticality
            FROM Purchase_Orders p JOIN Suppliers s ON p.Supplier_ID=s.Supplier_ID
            JOIN Items i ON p.Item_ID=i.Item_ID WHERE p.PO_ID=?''',con,params=(po_id,))
        if len(p)!=1: raise ValueError('PO not found or duplicated')
        r=p.iloc[0]
        lead=(pd.Timestamp(r.Promised_Delivery_Date)-pd.Timestamp(r.PO_Date)).days
        remaining=(pd.Timestamp(r.Promised_Delivery_Date)-pd.Timestamp(day)).days
        if not (str(r.PO_Date)<=day and 1<=remaining<=28 and
                (pd.isna(r.Actual_Delivery_Date) or str(r.Actual_Delivery_Date)>day)):
            raise ValueError('PO is not eligible for open-order review on selected date')
        inventory=pd.read_sql_query('''SELECT Available_Inventory,Safety_Stock_Level
            FROM Inventory_Snapshots WHERE Item_ID=? AND Location_ID=? AND Snapshot_Date=?''',
            con,params=(int(r.Item_ID),int(r.Location_ID),day))
        if len(inventory)!=1: raise ValueError('Missing or duplicate end-of-day inventory snapshot')
        start=(pd.Timestamp(day)-pd.Timedelta(days=29)).strftime('%Y-%m-%d')
        dem=pd.read_sql_query('''SELECT Demand_Date,Demand_Units FROM Demand_Observations
            WHERE Item_ID=? AND Location_ID=? AND Demand_Date BETWEEN ? AND ? ORDER BY Demand_Date''',
            con,params=(int(r.Item_ID),int(r.Location_ID),start,day))
        if len(dem)!=30 or dem.Demand_Date.nunique()!=30 or dem.Demand_Date.iloc[0]!=start or dem.Demand_Date.iloc[-1]!=day:
            raise ValueError('Incomplete trailing 30-day demand coverage')
        history=pd.read_sql_query('''SELECT COUNT(*) AS completed,
            SUM(CASE WHEN Actual_Delivery_Date > Promised_Delivery_Date THEN 1 ELSE 0 END) AS late
            FROM Purchase_Orders WHERE Supplier_ID=? AND Actual_Delivery_Date>? AND Actual_Delivery_Date<=?''',
            con,params=(int(r.Supplier_ID),(pd.Timestamp(day)-pd.Timedelta(days=90)).strftime('%Y-%m-%d'),day))
    finally: con.close()
    count=int(history.iloc[0]['completed']); late=int(history.iloc[0]['late'] or 0)
    normal=float(r.Normal_Unit_Cost); emergency=float(r.Emergency_Unit_Cost)
    if not (np.isfinite(normal) and np.isfinite(emergency) and emergency>=normal>=0):
        raise ValueError('Invalid emergency and normal unit costs')
    base={
        'Order_Quantity':float(r.Order_Quantity), 'Planned_Lead_Days':lead,
        'Days_To_Promise':remaining,'Supplier_Type':str(r.Supplier_Type),
        'Item_Category':str(r.Item_Category),'Item_Criticality':str(r.Item_Criticality),
        'Review_Month':int(pd.Timestamp(day).month),
        'Available_Inventory_at_review':float(inventory.iloc[0].Available_Inventory),
        'Safety_Stock_Level_at_review':float(inventory.iloc[0].Safety_Stock_Level),
        'Demand_SMA_30d':float(dem.Demand_Units.mean()),
        'Supplier_Completed_90d':count,
        'Supplier_Late_Rate_90d':float(late/count) if count else np.nan,
        'Supplier_History_Missing':int(count==0),
        'Normal_Unit_Cost':normal,'Emergency_Unit_Cost':emergency,
        'Unit_Cost_Premium':round(emergency-normal,6),
    }
    frames=[]
    for delay in (3,5,7):
        frames.append({'PO_ID':int(po_id),'Review_Date':day,**base,'Delay_Scenario_Days':delay})
    result=pd.DataFrame(frames)
    if not set(COST).issubset(result.columns):raise ValueError('Missing approved feature')
    if result[COMMON].drop(columns=['Supplier_Late_Rate_90d']).isna().any().any():
        raise ValueError('Missing required predictors')
    if sha256(db)!=DB_HASH:raise RuntimeError('Source database changed during read')
    return result[['PO_ID','Review_Date']+COST]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db',default='supplier_risk_output/supplier_risk.db')
    ap.add_argument('--po-id',type=int,required=True)
    ap.add_argument('--review-date',required=True)
    ap.add_argument('--validation-csv',default=None,help='Optional accepted W10.2A validation.csv for exact feature parity check')
    ap.add_argument('--output-dir',default='w10_3b2a_output')
    a=ap.parse_args()
    frame=build(a.db,a.po_id,a.review_date)
    result={'status':'FEATURES_GENERATED_PENDING_PARITY','po_id':a.po_id,'review_date':a.review_date,
            'source_db_sha256':DB_HASH,'scenarios':[3,5,7],
            'note':'End-of-review-day feature availability; no simulated targets read.'}
    if a.validation_csv:
        approved=pd.read_csv(a.validation_csv)
        subset=approved[(approved.PO_ID==a.po_id)&(approved.Review_Date.astype(str)==a.review_date)].sort_values('Delay_Scenario_Days')
        if len(subset)!=3:raise ValueError('PO/date not present in approved validation partition; select one that is')
        mismatches=[]
        for col in COST:
            for idx,(actual,expected) in enumerate(zip(frame[col],subset[col])):
                if pd.isna(actual) and pd.isna(expected):continue
                if isinstance(actual,(int,float,np.number)) and not isinstance(actual,(bool,np.bool_)):
                    equal=np.isclose(float(actual),float(expected),atol=1e-8,rtol=1e-8,equal_nan=True)
                else:equal=str(actual)==str(expected)
                if not equal:mismatches.append({'feature':col,'scenario':(3,5,7)[idx], 'live':str(actual),'approved':str(expected)})
        result['parity_mismatches']=mismatches
        result['status']='PASS' if not mismatches else 'FAIL_FEATURE_PARITY'
    out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
    frame.to_csv(out/'live_features.csv',index=False)
    (out/'feature_validation_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if result['status']=='FAIL_FEATURE_PARITY':raise SystemExit(1)

if __name__=='__main__':main()
