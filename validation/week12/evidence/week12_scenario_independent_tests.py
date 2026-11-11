"""Week 12 independent arithmetic/guardrail tests for w11_scenario_scoring.py.
Run: python week12_scenario_independent_tests.py --repo PATH_TO_REPO
Uses deterministic test doubles, not trained model artifacts; does not test model accuracy.
"""
import argparse, json, sys
from datetime import datetime, timezone
import numpy as np
import pandas as pd

class FixedModel:
    def __init__(self, predictions): self.predictions = predictions
    def predict(self, frame): return np.asarray(self.predictions, dtype=float)

def main(repo):
    sys.path.insert(0, repo)
    from w11_scenario_scoring import score_scenarios
    data = pd.DataFrame({'PO_ID':[4952]*3,'Review_Date':['2026-10-09']*3,'Delay_Scenario_Days':[3,5,7], 'Unit_Cost_Premium':[12.5]*3,'dummy':[1,2,3]})
    def artifacts(k2=[8,4,11],k3=[110,90,180]):
        return ({'features':['dummy'],'model':FixedModel(k2)}, {'features':['dummy'],'model':FixedModel(k3)})
    outcomes=[]
    def check(name, action):
        try: action(); outcomes.append({'test':name,'status':'PASS'})
        except Exception as exc: outcomes.append({'test':name,'status':'FAIL','detail':str(exc)})
    def equal(actual, expected):
        np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-10)
    def expect_error(fn, fragment):
        try: fn()
        except (ValueError,TypeError) as exc:
            assert fragment.lower() in str(exc).lower(), f'Unexpected error: {exc}'
        else: raise AssertionError('Expected input rejection, but input was accepted')
    def arithmetic():
        result=score_scenarios(data,*artifacts())
        equal(result['Original_KPI2_Shortage'],[8,4,11])
        equal(result['Revised_KPI2_Shortage'],[8,8,11])
        equal(result['Original_KPI3_Chained_Cost'],[100,50,137.5])
        equal(result['Revised_KPI3_Chained_Cost'],[100,100,137.5])
        equal(result['Original_KPI3_Direct_Cost'],[110,90,180])
        equal(result['KPI2_Revision_Delta'],[0,4,0])
        equal(result['KPI3_Revision_vs_Direct_Delta'],[-10,10,-42.5])
    check('Independent arithmetic: monotonic correction, chained cost and deltas',arithmetic)
    def negative():
        result=score_scenarios(data,*artifacts([-2,3,-4],[-1,-2,5]))
        equal(result['Revised_KPI2_Shortage'],[0,3,3])
        equal(result['Revised_KPI3_Chained_Cost'],[0,37.5,37.5])
        equal(result['Original_KPI3_Direct_Cost'],[0,0,5])
    check('Negative predictions are floored at zero',negative)
    def unchanged():
        original=data.copy(deep=True)
        score_scenarios(data,*artifacts())
        pd.testing.assert_frame_equal(data,original)
    check('Input frame not mutated',unchanged)
    check('Reject incomplete scenario group',lambda:expect_error(lambda:score_scenarios(data.iloc[:2],*artifacts()),'three'))
    check('Reject incorrect delay set',lambda:expect_error(lambda:score_scenarios(data.assign(Delay_Scenario_Days=[3,4,7]),*artifacts()),'3, 5, and 7'))
    check('Reject mixed purchase orders',lambda:expect_error(lambda:score_scenarios(data.assign(PO_ID=[4952,4953,4952]),*artifacts()),'one PO'))
    check('Reject changing premium across scenarios',lambda:expect_error(lambda:score_scenarios(data.assign(Unit_Cost_Premium=[12.5,12.5,13]),*artifacts()),'constant'))
    check('Reject negative unit premium',lambda:expect_error(lambda:score_scenarios(data.assign(Unit_Cost_Premium=[-1]*3),*artifacts()),'nonnegative'))
    check('Reject nonfinite unit premium',lambda:expect_error(lambda:score_scenarios(data.assign(Unit_Cost_Premium=[float('nan')]*3),*artifacts()),'finite'))
    check('Reject missing feature',lambda:expect_error(lambda:score_scenarios(data.drop(columns=['dummy']),*artifacts()),'missing required'))
    check('Reject nonfinite predictions',lambda:expect_error(lambda:score_scenarios(data,*artifacts([1,float('nan'),2])), 'nonfinite'))
    check('Reject nonfinite direct cost predictions',lambda:expect_error(lambda:score_scenarios(data,*artifacts([1,2,3],[1,float('inf'),2])), 'nonfinite'))
    report={'scope':'Independent deterministic unit tests of Week 11 scenario scoring logic (NOT actual model performance, database reconciliation, or UI)', 'timestamp_utc':datetime.now(timezone.utc).isoformat(),'repository_path':repo,'tests':outcomes,'pass_count':sum(t['status']=='PASS' for t in outcomes),'fail_count':sum(t['status']=='FAIL' for t in outcomes)}
    with open('/mnt/data/Week12_Scenario_Arithmetic_Test_Report.json','w') as f:json.dump(report,f,indent=2)
    for o in outcomes:print(o['status'],o['test'],o.get('detail',''))
    print('TOTAL',report['pass_count'],'PASS,',report['fail_count'],'FAIL')
    if report['fail_count']:sys.exit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);args=p.parse_args();main(args.repo)
