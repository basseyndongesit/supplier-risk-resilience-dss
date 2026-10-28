"""Read-only W10.4C local release verification. Run from Supplier Risk DSS project root."""
from pathlib import Path
import ast, hashlib, json, os, subprocess, sys
ROOT=Path.cwd()
ARTIFACTS={
 'source_db':('SUPPLIER_DSS_DB','supplier_risk_output/supplier_risk.db','0c2bb19febb7f2a4ad9d2ab6a642450b1861021a283523eda44c5fec8e4f6573'),
 'kpi1':('SUPPLIER_DSS_MODEL','predictive_model_output/random_forest.joblib','99103fdf772ba131ad90d15b7d7e8bbee44c24e558acc252bdd9fd9efe020b88'),
 'kpi2':('SUPPLIER_DSS_KPI2_MODEL','w10_2b_model_output/kpi2_shortage_validation_selected.joblib','014edabd936c91f67a842e34485b5ffb1ba09af2b522d0eef8eca2e8351e39ad'),
 'kpi3':('SUPPLIER_DSS_KPI3_MODEL','w10_2b_model_output/kpi3_emergency_premium_validation_selected.joblib','e8b86ead4bdc2040642a88a0eb0993f35d30438231d7bf222f3a3955d2400013')}
results=[]
def add(name,status,detail):
 results.append({'check':name,'status':status,'detail':detail});print(f'[{status}] {name}: {detail}')
for name,(env,default,expected) in ARTIFACTS.items():
 p=Path(os.environ.get(env,default)).expanduser()
 if not p.is_file():add(name,'FAIL',f'missing {p}');continue
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 got=h.hexdigest();add(name,'PASS' if got==expected else 'FAIL',f'{p} SHA256 {got}'+(' (expected '+expected+')' if got!=expected else ''))
for name in ['app_w10_4b.py','w10_4b_whatif.py','w10_3b4_dashboard.py','w10_3b4_decision_summary.py','w10_3b3b_live_ui.py','w10_3b2a_live_features.py','w10_3b2a_score_frozen.py','dss_core.py','predictive_risk_3c2.py','predictive_whatif_3c3.py','w10_3b_explainability.py']:
 p=ROOT/name
 if not p.is_file():add('module '+name,'FAIL','missing');continue
 try:ast.parse(p.read_text(encoding='utf-8-sig'));add('module '+name,'PASS','present, syntax valid')
 except (SyntaxError,UnicodeError) as e:add('module '+name,'FAIL',str(e))
try:
 app=(ROOT/'app_w10_4b.py').read_text(encoding='utf-8-sig')
 labels=['1. Weekly Risk Review','2. PO / Supplier Detail','3. Scenario Comparison','4. Management Review','5. Predictive Risk Ranking','6. Interactive What-If Prediction','7. Model Validation & Explainability Evidence','8. Integrated Decision Dashboard','9. Options & Decision Record']
 pos=[app.index(repr(label)) for label in labels]
 add('screen order','PASS' if pos==sorted(pos) else 'FAIL','nine labels in approved order')
except (OSError,ValueError) as e:add('screen order','FAIL',str(e))
tests=['test_w10_4b.py','test_w10_3b4.py','test_w10_3b3b_on_demand.py']
existing=[x[:-3] for x in tests if (ROOT/x).is_file()]
if len(existing)!=len(tests):add('unit test files','NOT_EVALUATED','missing '+', '.join(x for x in tests if not (ROOT/x).is_file()))
else:
 run=subprocess.run([sys.executable,'-m','unittest','-v',*existing],capture_output=True,text=True)
 add('unit tests','PASS' if run.returncode==0 else 'FAIL',(run.stderr or run.stdout)[-1800:])
add('manual UI','NOT_EVALUATED','requires Streamlit interaction, confirm FT-38 through FT-49 locally')
add('GitHub or OneDrive release','NOT_EVALUATED','requires actual repository/folder inspection')
add('progress report','NOT_EVALUATED','requires final updated report review')
summary={'overall':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL' if any(x['status']=='FAIL' for x in results) else 'INCOMPLETE','counts':{s:sum(x['status']==s for x in results) for s in ['PASS','FAIL','NOT_EVALUATED']},'results':results}
output=ROOT/'w10_4c_local_verification.json'
output.write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('\nOVERALL',summary['overall'],'COUNTS',summary['counts'],'\nReport:',output)
sys.exit(1 if summary['overall']=='FAIL' else 0)
