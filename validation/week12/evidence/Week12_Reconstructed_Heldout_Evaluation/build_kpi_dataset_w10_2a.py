#!/usr/bin/env python3
"""W10.2A: construct point-in-time synthetic-scenario surrogate datasets.
Read-only SQLite; no model fitting. Requires pandas and numpy.
The assessment labels are simulated outcomes, NOT observed future shortages/costs.
"""
import argparse, hashlib, json, sqlite3
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd

SEED=84735
CUT_TRAIN='2026-01-01'
CUT_VALID='2026-05-21'
TARGETS=['Incremental_Shortage_Units','Estimated_Emergency_Procurement_Cost']
COMMON=['Order_Quantity','Planned_Lead_Days','Days_To_Promise','Supplier_Type','Item_Category','Item_Criticality','Review_Month','Delay_Scenario_Days','Available_Inventory_at_review','Safety_Stock_Level_at_review','Demand_SMA_30d','Supplier_Completed_90d','Supplier_Late_Rate_90d','Supplier_History_Missing']
COST=COMMON+['Normal_Unit_Cost','Emergency_Unit_Cost','Unit_Cost_Premium']
FORBIDDEN=['Actual_Delivery_Date','Baseline_Unmet_Demand_Units','Delayed_Unmet_Demand_Units','Management_Review_Flag','Priority_Reason','Projected_Stockout_Days','Delayed_Stockout_Days','Incremental_Stockout_Days','Predicted_Late_Probability']

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--db',default='supplier_risk_output/supplier_risk.db')
 p.add_argument('--output-dir',default='w10_2a_dataset_output')
 p.add_argument('--train-end',default=CUT_TRAIN,help='Last train review date (inclusive), YYYY-MM-DD')
 p.add_argument('--validation-end',default=CUT_VALID,help='Last validation review date (inclusive), YYYY-MM-DD')
 a=p.parse_args()
 db=Path(a.db).resolve(); out=Path(a.output_dir).resolve()
 if not db.is_file():p.error('Database not found: '+str(db))
 try:
  if not (pd.Timestamp(a.train_end)<pd.Timestamp(a.validation_end)):p.error('train-end must precede validation-end')
 except ValueError:p.error('Invalid cut dates')
 out.mkdir(parents=True,exist_ok=True)
 before=sha(db)
 conn=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
 conn.execute('PRAGMA query_only=ON')
 # Only explicit approved columns: never SELECT * into the feature dataset.
 base=pd.read_sql_query('''SELECT a.PO_ID,a.Review_Date,a.Delay_Scenario_Days,
 a.Incremental_Shortage_Units,a.Estimated_Emergency_Procurement_Cost,
 p.PO_Date,p.Promised_Delivery_Date,p.Actual_Delivery_Date,p.Supplier_ID,p.Item_ID,p.Location_ID,
 p.Order_Quantity,p.Normal_Unit_Cost,p.Emergency_Unit_Cost,
 s.Supplier_Type,i.Item_Category,i.Item_Criticality
 FROM DSS_Assessments a JOIN Purchase_Orders p ON p.PO_ID=a.PO_ID
 JOIN Suppliers s ON s.Supplier_ID=p.Supplier_ID JOIN Items i ON i.Item_ID=p.Item_ID''',conn)
 pos=pd.read_sql_query('''SELECT PO_ID,Supplier_ID,Item_ID,Location_ID,PO_Date,Promised_Delivery_Date,Actual_Delivery_Date,Order_Quantity
 FROM Purchase_Orders''',conn)
 inv=pd.read_sql_query('''SELECT Item_ID,Location_ID,Snapshot_Date,Available_Inventory,Safety_Stock_Level
 FROM Inventory_Snapshots''',conn)
 demand=pd.read_sql_query('''SELECT Item_ID,Location_ID,Demand_Date,Demand_Units FROM Demand_Observations''',conn)
 conn.close()
 n0=len(base)
 # Validate source uniqueness and triplets before any transformation.
 if base.duplicated(['PO_ID','Review_Date','Delay_Scenario_Days']).any():raise RuntimeError('Duplicate assessment keys')
 trip=base.groupby(['PO_ID','Review_Date']).Delay_Scenario_Days.agg(lambda s:tuple(sorted(s)))
 if not trip.map(lambda x:x==(3,5,7)).all():raise RuntimeError('Missing or unexpected scenario triplets')
 if base[TARGETS].isna().any().any() or (base[TARGETS]<0).any().any():raise RuntimeError('Invalid targets')
 base['Days_To_Promise']=(pd.to_datetime(base.Promised_Delivery_Date)-pd.to_datetime(base.Review_Date)).dt.days
 base['Planned_Lead_Days']=(pd.to_datetime(base.Promised_Delivery_Date)-pd.to_datetime(base.PO_Date)).dt.days
 base['Review_Month']=pd.to_datetime(base.Review_Date).dt.month
 base['Unit_Cost_Premium']=(base.Emergency_Unit_Cost-base.Normal_Unit_Cost).round(6)
 if ((base.PO_Date>base.Review_Date)|(base.Days_To_Promise<=0)|(base.Days_To_Promise>28)|((base.Actual_Delivery_Date.notna())&(base.Actual_Delivery_Date<=base.Review_Date))).any():raise RuntimeError('PO review eligibility failed')
 # The actual date is used only for this eligibility audit and supplier *completed* history,
 # then removed from the training dataset.
 base=base.drop(columns=['Actual_Delivery_Date','PO_Date','Promised_Delivery_Date'])
 # Inventory at review date (end-of-day convention).
 inv=inv.rename(columns={'Snapshot_Date':'Review_Date','Available_Inventory':'Available_Inventory_at_review','Safety_Stock_Level':'Safety_Stock_Level_at_review'})
 if inv.duplicated(['Item_ID','Location_ID','Review_Date']).any():raise RuntimeError('Duplicate inventory snapshots')
 base=base.merge(inv,on=['Item_ID','Location_ID','Review_Date'],how='left',validate='many_to_one')
 if base[['Available_Inventory_at_review','Safety_Stock_Level_at_review']].isna().any().any():raise RuntimeError('Missing inventory at review')
 # Trailing 30 calendar days inclusive; strict 30-day coverage check.
 demand=demand.sort_values(['Item_ID','Location_ID','Demand_Date'])
 g=demand.groupby(['Item_ID','Location_ID'],sort=False)
 demand['Demand_SMA_30d']=g.Demand_Units.transform(lambda x:x.rolling(30,min_periods=30).mean())
 demand['days30']=g.Demand_Date.transform(lambda x:pd.Series(pd.to_datetime(x).to_numpy(),index=x.index).diff(29).dt.days)
 demand=demand.rename(columns={'Demand_Date':'Review_Date'})
 demand=demand[['Item_ID','Location_ID','Review_Date','Demand_SMA_30d','days30']]
 base=base.merge(demand,on=['Item_ID','Location_ID','Review_Date'],how='left',validate='many_to_one')
 if base.Demand_SMA_30d.isna().any() or not base.days30.eq(29).all():raise RuntimeError('Incomplete 30 calendar-day demand window')
 base=base.drop(columns='days30')
 # Supplier history is computed from *known completed* POs as of each review.
 # No current/future actual delivery date is exposed to features.
 history=pos[pos.Actual_Delivery_Date.notna()].copy()
 history['late']=(history.Actual_Delivery_Date>history.Promised_Delivery_Date).astype(int)
 history['delivered_day']=pd.to_datetime(history.Actual_Delivery_Date).to_numpy(dtype='datetime64[D]').astype('int64')
 reviews=base[['Supplier_ID','Review_Date']].drop_duplicates().copy()
 reviews['review_day']=pd.to_datetime(reviews.Review_Date).to_numpy(dtype='datetime64[D]').astype('int64')
 supplier_arrays={}
 for sid, group in history.groupby('Supplier_ID'):
  group=group.sort_values('delivered_day')
  supplier_arrays[sid]=(group.delivered_day.to_numpy(),np.r_[0,group.late.to_numpy().cumsum()])
 completed=np.zeros(len(reviews),dtype=np.int32); late=np.zeros(len(reviews),dtype=np.int32)
 for sid, idx in reviews.groupby('Supplier_ID').groups.items():
  if sid not in supplier_arrays:continue
  days,cs=supplier_arrays[sid]; days_at=reviews.loc[idx,'review_day'].to_numpy()
  # Strict 90-day lookback: (review-90, review], consistent with dss_core.supplier_history.
  left=np.searchsorted(days,days_at-90,side='right');right=np.searchsorted(days,days_at,side='right')
  completed[reviews.index.get_indexer(idx)]=right-left
  late[reviews.index.get_indexer(idx)]=cs[right]-cs[left]
 reviews['Supplier_Completed_90d']=completed
 reviews['Supplier_Late_Rate_90d']=np.divide(late,completed,out=np.full(len(reviews),np.nan),where=completed>0)
 reviews['Supplier_History_Missing']=(completed==0).astype(int)
 base=base.merge(reviews.drop(columns='review_day'),on=['Supplier_ID','Review_Date'],how='left',validate='many_to_one')
 if base.Supplier_Completed_90d.isna().any():raise RuntimeError('Supplier history missing')
 # Split by chronological review windows. Embargo all POs spanning more than one window.
 dates=base.Review_Date
 base['partition']=np.select([dates<=a.train_end,(dates>a.train_end)&(dates<=a.validation_end),dates>a.validation_end],['train','validation','test'],default='unknown')
 cross=base.groupby('PO_ID').partition.nunique()
 embargo_ids=set(cross[cross>1].index)
 embargo=base[base.PO_ID.isin(embargo_ids)]
 data=base[~base.PO_ID.isin(embargo_ids)].copy()
 if data.empty:raise RuntimeError('All rows embargoed')
 if data.groupby('PO_ID').partition.nunique().max()!=1:raise RuntimeError('PO split leakage')
 if any((data.partition==k).sum()==0 for k in ('train','validation','test')):raise RuntimeError('Empty partition')
 if len(data)+len(embargo)!=n0:raise RuntimeError('Row conservation failed')
 if data.duplicated(['PO_ID','Review_Date','Delay_Scenario_Days']).any():raise RuntimeError('Duplicate output keys')
 if any(c in data.columns for c in FORBIDDEN):raise RuntimeError('Forbidden source feature persisted')
 # Identifiers are for grouping/auditing only, not model inputs.
 keep=['PO_ID','Review_Date','partition']+list(dict.fromkeys(COMMON+['Normal_Unit_Cost','Emergency_Unit_Cost','Unit_Cost_Premium']+TARGETS))
 data=data[keep].sort_values(['Review_Date','PO_ID','Delay_Scenario_Days']).reset_index(drop=True)
 # Verify no target or identifier is in model input allowlists.
 assert not (set(COMMON)&set(TARGETS+['PO_ID','Review_Date','partition']))
 assert not (set(COST)&set(TARGETS+['PO_ID','Review_Date','partition']))
 files={}
 for part in ('train','validation','test'):
  dest=out/f'{part}.csv';data[data.partition==part].to_csv(dest,index=False,float_format='%.12g');files[part]={'file':dest.name,'sha256':sha(dest)}
 # Keep dataset row-level but no source DB copy. Manifest contains reproducibility controls.
 counts={}
 for part in ('train','validation','test'):
  x=data[data.partition==part]
  counts[part]={'rows':len(x),'unique_pos':int(x.PO_ID.nunique()),'po_review_groups':int(x.groupby(['PO_ID','Review_Date']).ngroups),'review_min':x.Review_Date.min(),'review_max':x.Review_Date.max(),'shortage_positive':int((x[TARGETS[0]]>0).sum()),'cost_positive':int((x[TARGETS[1]]>0).sum())}
 manifest={'version':'W10.2A-1.0','status':'PASS','dataset_semantics':'Synthetic retrospective 3/5/7-day scenario-surrogate targets; not realized future outcomes','source_db_sha256':before,'cut_dates':{'train_end_inclusive':a.train_end,'validation_end_inclusive':a.validation_end},'partition_policy':'Chronological review windows; embargo every PO appearing in more than one window; all reviews/scenarios of retained POs in exactly one partition','input_feature_allowlists':{'kpi2_shortage':COMMON,'kpi3_emergency_premium':COST},'target_columns':{'kpi2_shortage':TARGETS[0],'kpi3_emergency_premium':TARGETS[1]},'identifier_columns_not_for_training':['PO_ID','Review_Date','partition'],'explicit_exclusions':FORBIDDEN+['Other_Open_PO_Quantity_at_review (deferred pending point-in-time implementation)'],'row_accounting':{'input_rows':n0,'embargoed_rows':len(embargo),'embargoed_pos':len(embargo_ids),'retained_rows':len(data)},'partition_counts':counts,'files':files,'limitations':['Review-date end-of-day inventory and demand may not be available before an earlier same-day operational decision; interpret prediction time as after day close.','Simulation targets may depend on future synthetic assumptions unavailable at review date; trained models emulate simulator outputs, not observed outcomes.','Supplier history uses deliveries known by end of review date; excludes deliveries after review.','Cost model must be benchmarked against the known shortage-times-premium formula; no simulated shortage feature allowed.','Full independent feature and target lineage review required during W10.2B before model approval.']}
 after=sha(db)
 if before!=after:raise RuntimeError('Source DB hash changed')
 manifest['source_db_unchanged']=True
 dest=out/'w10_2a_manifest.json';dest.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print(json.dumps({'status':manifest['status'],'partition_counts':counts,'row_accounting':manifest['row_accounting'],'manifest':str(dest)},indent=2))

if __name__=='__main__':main()
