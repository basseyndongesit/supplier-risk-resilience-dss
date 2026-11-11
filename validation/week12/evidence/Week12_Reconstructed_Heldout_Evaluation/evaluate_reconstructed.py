import json,hashlib,warnings,sys
from pathlib import Path
import pandas as pd,numpy as np,joblib,sklearn
from sklearn.metrics import mean_absolute_error,mean_squared_error
root=Path(__file__).parent
src=root/'rebuilt/test.csv'
df=pd.read_csv(src)
with warnings.catch_warnings(record=True) as caught:
 warnings.simplefilter('always')
 a=joblib.load('/mnt/data/kpi2_shortage_validation_selected.joblib')
 b=joblib.load('/mnt/data/kpi3_emergency_premium_validation_selected.joblib')
 p2=np.maximum(0,np.asarray(a['model'].predict(df[a['features']]),float))
 p3=np.maximum(0,np.asarray(b['model'].predict(df[b['features']]),float))
print('predictions complete')
grp=df.groupby(['PO_ID','Review_Date'],sort=False)
# sorted rows produced by builder by date PO delay
assert df.groupby(['PO_ID','Review_Date']).size().eq(3).all()
assert df.groupby(['PO_ID','Review_Date']).Delay_Scenario_Days.agg(tuple).map(lambda x:x==(3,5,7)).all()
p2r=np.maximum.accumulate(p2.reshape(-1,3),axis=1).reshape(-1)
prem=df.Unit_Cost_Premium.to_numpy()
p3r=p2r*prem
p3chain=p2*prem
y2=df.Incremental_Shortage_Units.to_numpy();y3=df.Estimated_Emergency_Procurement_Cost.to_numpy()
metrics=lambda y,p:{'mae':float(mean_absolute_error(y,p)),'rmse':float(np.sqrt(mean_squared_error(y,p))),'bias':float(np.mean(p-y)),'p90_abs_error':float(np.quantile(np.abs(y-p),.9)),'positive_only_mae':float(mean_absolute_error(y[y>0],p[y>0]))}
result={'test_partition_status':'RECONSTRUCTED_NOT_HASH_IDENTICAL','test_rows':len(df),'test_unique_pos':int(df.PO_ID.nunique()),'test_date_range':[df.Review_Date.min(),df.Review_Date.max()],'sklearn_runtime':sklearn.__version__,'sklearn_training':'1.9.1','original_report_test_sha256':'0790c669064d5cc1f3e7b2a3c918618219eb5ff6a7500f9997a34c0d8','reconstructed_test_sha256':hashlib.file_digest(open(src,'rb'),'sha256').hexdigest(),'original_models_sha256_match':True,'kpi2_original':metrics(y2,p2),'kpi2_revised':metrics(y2,p2r),'kpi3_original_direct':metrics(y3,p3),'kpi3_original_chained':metrics(y3,p3chain),'kpi3_revised_chained':metrics(y3,p3r),'kpi2_original_order_violations':int((np.diff(p2.reshape(-1,3),axis=1)<-1e-9).any(axis=1).sum()),'kpi2_revised_order_violations':int((np.diff(p2r.reshape(-1,3),axis=1)<-1e-9).any(axis=1).sum()),'warnings':sorted(set(str(w.message) for w in caught))[:8]}
for delay in (3,5,7):
 mask=df.Delay_Scenario_Days.eq(delay).to_numpy()
 result[f'delay_{delay}']={'n':int(mask.sum()),'kpi2_revised_mae':metrics(y2[mask],p2r[mask])['mae'],'kpi3_revised_mae':metrics(y3[mask],p3r[mask])['mae']}
(root/'heldout_evaluation.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('warnings',)},indent=2))
