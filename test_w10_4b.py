import ast
import unittest
from pathlib import Path
from unittest.mock import Mock
import pandas as pd
import sys
import types
# Pure-function unit tests run without Streamlit or the user's project modules.
for module in ('streamlit','w10_3b2a_live_features','w10_3b2a_score_frozen','w10_3b4_dashboard','predictive_whatif_3c3'):
 sys.modules.setdefault(module,types.ModuleType(module))
sys.modules['w10_3b2a_live_features'].build=lambda *a:None
sys.modules['w10_3b2a_score_frozen'].EXPECTED={}
sys.modules['w10_3b2a_score_frozen'].KPI1_FEATURES=[]
sys.modules['w10_3b4_dashboard'].frozen_models=lambda *a:None
sys.modules['w10_3b4_dashboard'].save_whatif=lambda *a:None
sys.modules['predictive_whatif_3c3'].baseline_for_po=lambda *a:None
sys.modules['predictive_whatif_3c3'].compare_hypothetical=lambda *a:None
from w10_4b_whatif import validated_changes, describe_changes, narrative, EDITABLE, score

class W104BTests(unittest.TestCase):
 def setUp(self):
  self.base=pd.DataFrame([{'Order_Quantity':100.,'Available_Inventory_at_review':20.,'Safety_Stock_Level_at_review':10.,'Demand_SMA_30d':4.,'Delay_Scenario_Days':7,'Unit_Cost_Premium':2.,'Normal_Unit_Cost':8.,'Emergency_Unit_Cost':10.}])
 def test_source_unchanged(self):
  new=validated_changes(self.base,{'Order_Quantity':150},EDITABLE['kpi2'])
  self.assertEqual(float(self.base.Order_Quantity.iloc[0]),100)
  self.assertEqual(float(new.Order_Quantity.iloc[0]),150)
 def test_unapproved_rejected(self):
  with self.assertRaises(ValueError):validated_changes(self.base,{'Normal_Unit_Cost':4},EDITABLE['kpi3'])
 def test_negative_rejected(self):
  with self.assertRaises(ValueError):validated_changes(self.base,{'Demand_SMA_30d':-1},EDITABLE['kpi2'])
 def test_cost_link(self):
  new=validated_changes(self.base,{'Unit_Cost_Premium':5},EDITABLE['kpi3'])
  self.assertEqual(float(new.Emergency_Unit_Cost.iloc[0]),13)
 def test_model_scoring_and_clipping(self):
  model=Mock();model.predict.return_value=[-2.]
  self.assertEqual(score(model,self.base,['Order_Quantity']),0.)
 def test_summary_has_all_four_elements(self):
  s=narrative('kpi2',['Demand: 4 to 5'],10,12,'units')
  for x in ('Scenario inputs','Baseline','updated','change','limitations'):
   self.assertIn(x.lower(),s.lower())
 def test_screens_preserved(self):
  app=Path(__file__).with_name('app_w10_4b.py').read_text()
  self.assertIn('9. Options & Decision Record',app)
  self.assertIn("render(db,queue,review_date,selected)",app)

if __name__=='__main__':unittest.main()
