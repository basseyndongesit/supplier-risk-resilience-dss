"""Independent database-level reconciliation of Week 12 DSS scenario evidence.
Run: python week12_end_to_end_data_checks.py /path/to/supplier_risk.db
Does not validate model accuracy, UI behavior, or real-world plausibility.
"""
import sqlite3, json, sys, csv, collections, pathlib
from datetime import date
DB=sys.argv[1] if len(sys.argv)>1 else '/mnt/data/supplier_risk.db'
out=pathlib.Path(__file__).resolve().parent
con=sqlite3.connect(f'file:{pathlib.Path(DB).resolve()}?mode=ro',uri=True)
con.row_factory=sqlite3.Row
q='''SELECT a.*,p.Normal_Unit_Cost,p.Emergency_Unit_Cost,p.Supplier_ID,p.Item_ID,p.Location_ID FROM DSS_Assessments a JOIN Purchase_Orders p ON p.PO_ID=a.PO_ID ORDER BY a.PO_ID,a.Review_Date,a.Delay_Scenario_Days'''
rows=con.execute(q)
checks=collections.Counter(); examples=collections.defaultdict(list); groups=collections.defaultdict(list)
def check(name,ok,row):
 checks[name+'_tested']+=1
 if not ok:
  checks[name+'_violations']+=1
  if len(examples[name])<5: examples[name].append({'PO_ID':row['PO_ID'],'Review_Date':row['Review_Date'],'Delay_Scenario_Days':row['Delay_Scenario_Days']})
for r in rows:
 checks['total_rows']+=1
 k=(r['PO_ID'],r['Review_Date']); groups[k].append(r)
 diff=max(0,r['Delayed_Unmet_Demand_Units']-r['Baseline_Unmet_Demand_Units'])
 check('shortage_arithmetic',abs(r['Incremental_Shortage_Units']-diff)<=0.0001,r)
 premium=r['Emergency_Unit_Cost']-r['Normal_Unit_Cost']
 expected=r['Incremental_Shortage_Units']*premium
 check('emergency_premium_arithmetic',abs(r['Estimated_Emergency_Procurement_Cost']-expected)<=0.02,r)
for k,rs in groups.items():
 a=rs[0]
 check('complete_scenario_group',len(rs)==3 and [x['Delay_Scenario_Days'] for x in rs]==[3,5,7],a)
 check('constant_baseline',max(x['Baseline_Unmet_Demand_Units'] for x in rs)-min(x['Baseline_Unmet_Demand_Units'] for x in rs)<0.0001,a)
 check('nondecreasing_simulated_shortage',all(rs[i]['Incremental_Shortage_Units']<=rs[i+1]['Incremental_Shortage_Units']+0.0001 for i in range(len(rs)-1)),a)
 check('consistent_flag_group',len(set(x['Management_Review_Flag'] for x in rs))==1,a)
 expected_flag=int(any(x['Incremental_Shortage_Units']>0 for x in rs) or (a['Criticality_Class']=='High' and a['Baseline_Unmet_Demand_Units']>0))
 for x in rs: check('screening_flag_group',x['Management_Review_Flag']==expected_flag,x)
# choose typical: moderate shortage and all positive; challenging: critical baseline shortage or no incremental change
chosen={}
for k,rs in groups.items():
 if len(rs)!=3:continue
 if 'typical' not in chosen and rs[0]['Incremental_Shortage_Units']>0 and rs[2]['Incremental_Shortage_Units']>rs[0]['Incremental_Shortage_Units'] and rs[0]['Estimated_Emergency_Procurement_Cost']>0:chosen['typical']=rs
 if 'challenging' not in chosen and rs[0]['Criticality_Class']=='High' and rs[0]['Baseline_Unmet_Demand_Units']>0:chosen['challenging']=rs
 if len(chosen)==2:break
scenarios=[]
for name,rs in chosen.items():
 a=rs[0]
 scenarios.append({'scenario':name,'PO_ID':a['PO_ID'],'Review_Date':a['Review_Date'],'Supplier_ID':a['Supplier_ID'],'Item_ID':a['Item_ID'],'Location_ID':a['Location_ID'],'Criticality_Class':a['Criticality_Class'],'Baseline_Unmet_Demand_Units':a['Baseline_Unmet_Demand_Units'],'Management_Review_Flag':a['Management_Review_Flag'],'delays':[{'days':r['Delay_Scenario_Days'],'delayed_unmet':r['Delayed_Unmet_Demand_Units'],'incremental_shortage':r['Incremental_Shortage_Units'],'emergency_premium':r['Estimated_Emergency_Procurement_Cost']} for r in rs]})
report={'source':'uploaded supplier_risk.db','scope':'synthetic simulator assessments only, not model predictions or UI','rows':checks['total_rows'],'groups':len(groups),'checks':{n:{'tested':checks[n+'_tested'],'violations':checks[n+'_violations'],'status':'PASS' if checks[n+'_violations']==0 else 'FAIL','examples':examples[n]} for n in ['shortage_arithmetic','emergency_premium_arithmetic','screening_flag_group','complete_scenario_group','constant_baseline','nondecreasing_simulated_shortage','consistent_flag_group']},'walkthrough_candidates':scenarios,'limitations':['Simulation-derived values do not establish predictive-model accuracy.','Database reconciliation does not establish displayed UI values or user comprehension.','Proposed actions are illustrative, not observed management decisions.']}
(out/'Week12_Database_Reconciliation.json').write_text(json.dumps(report,indent=2))
with (out/'Week12_Walkthrough_Candidates.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['scenario','PO_ID','Review_Date','Criticality','Baseline_Unmet_Units','Flag','Delay_Days','Incremental_Shortage_Units','Emergency_Premium'])
 for s in scenarios:
  for r in s['delays']:w.writerow([s['scenario'],s['PO_ID'],s['Review_Date'],s['Criticality_Class'],s['Baseline_Unmet_Demand_Units'],s['Management_Review_Flag'],r['days'],r['incremental_shortage'],r['emergency_premium']])
print(json.dumps({'rows':report['rows'],'groups':report['groups'],'checks':{k:v['violations'] for k,v in report['checks'].items()},'candidates':scenarios},indent=2))
