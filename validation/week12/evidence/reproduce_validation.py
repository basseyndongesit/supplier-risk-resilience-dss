import zipfile,io,json,joblib,warnings,numpy as np,pandas as pd,sklearn
from sklearn.metrics import mean_absolute_error
z=zipfile.ZipFile('/mnt/data/supplier-risk-resilience-dss-week11-model-validation.zip')
n=next(x for x in z.namelist() if x.endswith('/validation.csv'))
d=pd.read_csv(io.BytesIO(z.read(n)))
print('rows',len(d),'groups',d.groupby(['PO_ID','Review_Date']).size().value_counts().head().to_dict())
a2=joblib.load('/mnt/data/kpi2_shortage_validation_selected.joblib');a3=joblib.load('/mnt/data/kpi3_emergency_premium_validation_selected.joblib')
p2=np.maximum(a2['model'].predict(d[a2['features']]),0)
p3=np.maximum(a3['model'].predict(d[a3['features']]),0)
d['p2']=p2;d['p3']=p3
d=d.sort_values(['PO_ID','Review_Date','Delay_Scenario_Days']).reset_index(drop=True)
d['revised2']=d.groupby(['PO_ID','Review_Date'])['p2'].cummax()
d['revised3']=d['revised2']*d['Unit_Cost_Premium']
print('kpi2 original/revised',mean_absolute_error(d['Incremental_Shortage_Units'],d['p2']),mean_absolute_error(d['Incremental_Shortage_Units'],d['revised2']))
print('kpi3 original/revised',mean_absolute_error(d['Estimated_Emergency_Procurement_Cost'],d['p3']),mean_absolute_error(d['Estimated_Emergency_Procurement_Cost'],d['revised3']))
print('groups invalid',int((d.groupby(['PO_ID','Review_Date']).size()!=3).sum()))
print('violations revised',int((d.groupby(['PO_ID','Review_Date'])['revised2'].diff().dropna() < -1e-10).sum()))
print('validation dates',d.Review_Date.min(),d.Review_Date.max())
print('sklearn',sklearn.__version__)
