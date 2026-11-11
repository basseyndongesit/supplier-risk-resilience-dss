"""Independent Week 12 UI-data reconciliation against frozen synthetic SQLite database.
Run: python Week12_UI_Data_Reconciliation.py /path/to/supplier_risk.db
Requires pandas; dss_core.py next to this script or in PYTHONPATH.
Does not interact with browser or write to source DB.
"""
import json, sys, sqlite3, importlib.util
from pathlib import Path

DB=Path(sys.argv[1]) if len(sys.argv)>1 else Path('supplier_risk.db')
CORE=Path(sys.argv[2]) if len(sys.argv)>2 else Path('dss_core.py')
spec=importlib.util.spec_from_file_location('dss_core',CORE)
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
results=[]
def check(test,condition,observed,expected):
    results.append(dict(test=test,status='PASS' if condition else 'FAIL',observed=observed,expected=expected))

with sqlite3.connect(f'file:{DB.resolve().as_posix()}?mode=ro',uri=True) as conn:
    check('Database read-only integrity',conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok','integrity_check','ok')
    for tag,po,dt in [('typical','4','2024-12-26'),('challenging','913','2024-11-28')]:
        rows=core.scenario_rows(DB,po,dt)
        detail=core.po_details(DB,po)
        queue=core.review_queue(DB,dt)
        item=queue.loc[queue.PO_ID.astype(str)==po]
        check(f'{tag}: queue includes PO',len(item)==1,len(item),1)
        check(f'{tag}: scenario delays',rows.Delay_Scenario_Days.tolist()==[3,5,7],rows.Delay_Scenario_Days.tolist(),[3,5,7])
        if len(rows)!=3 or len(item)!=1:continue
        flag=core.screening_check(rows,detail['Item_Criticality'])
        displayed=int(item.Management_Review_Flag.iloc[0])
        check(f'{tag}: review flag',flag==bool(displayed),displayed,int(flag))
        check(f'{tag}: queue max shortage',abs(float(item.Max_Incremental_Shortage_Units.iloc[0])-float(rows.Incremental_Shortage_Units.max()))<1e-6,float(item.Max_Incremental_Shortage_Units.iloc[0]),float(rows.Incremental_Shortage_Units.max()))
        check(f'{tag}: queue max premium',abs(float(item.Max_Emergency_Premium.iloc[0])-float(rows.Estimated_Emergency_Procurement_Cost.max()))<1e-6,float(item.Max_Emergency_Premium.iloc[0]),float(rows.Estimated_Emergency_Procurement_Cost.max()))
        for _,r in rows.iterrows():
            delay=int(r.Delay_Scenario_Days)
            independent=conn.execute('SELECT Incremental_Shortage_Units,Estimated_Emergency_Procurement_Cost FROM DSS_Assessments WHERE PO_ID=? AND Review_Date=? AND Delay_Scenario_Days=?',(int(po),dt,delay)).fetchone()
            check(f'{tag}: {delay}d shortage displayed-data',abs(float(r.Incremental_Shortage_Units)-independent[0])<1e-8,float(r.Incremental_Shortage_Units),independent[0])
            check(f'{tag}: {delay}d premium displayed-data',abs(float(r.Estimated_Emergency_Procurement_Cost)-independent[1])<1e-8,float(r.Estimated_Emergency_Procurement_Cost),independent[1])

out={'scope':'DSS core read-path versus SQLite, not a live browser/UI test','database':str(DB),'tests':len(results),'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results),'results':results}
Path('Week12_UI_Data_Reconciliation_Result.json').write_text(json.dumps(out,indent=2))
print(json.dumps({k:out[k] for k in ('scope','tests','passed','failed')},indent=2))
