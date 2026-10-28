"""W10.4B frozen-model what-if UI. Read-only; no training or database writes."""
import os
import numpy as np
import pandas as pd
import streamlit as st
from w10_3b2a_live_features import build as live_features
from w10_3b2a_score_frozen import EXPECTED, KPI1_FEATURES
from w10_3b4_dashboard import frozen_models, save_whatif
from predictive_whatif_3c3 import baseline_for_po, compare_hypothetical

LABELS = {
 'Order_Quantity':'Order quantity (units)',
 'Planned_Lead_Days':'Planned lead time (days)',
 'Supplier_Completed_90d':'Completed supplier orders (previous 90 days)',
 'Supplier_Late_Rate_90d':'Supplier late rate (fraction)',
 'Available_Inventory_at_review':'Available inventory (units)',
 'Safety_Stock_Level_at_review':'Safety stock level (units)',
 'Demand_SMA_30d':'30-day average daily demand (units)',
 'Unit_Cost_Premium':'Emergency unit-price premium (currency units)',
 'Delay_Scenario_Days':'Assumed delivery delay (days)',
}
EDITABLE = {
 'kpi2':['Order_Quantity','Available_Inventory_at_review','Safety_Stock_Level_at_review','Demand_SMA_30d','Delay_Scenario_Days'],
 'kpi3':['Order_Quantity','Available_Inventory_at_review','Safety_Stock_Level_at_review','Demand_SMA_30d','Unit_Cost_Premium','Delay_Scenario_Days'],
}

def model_paths():
 return tuple((name,os.environ.get('SUPPLIER_DSS_'+name.upper()+'_MODEL',default),digest)
              for name,(digest,default) in EXPECTED.items())

def validated_changes(base, updates, features):
 """Only explicitly approved mutable predictors; retain all other baseline columns."""
 x=base.copy(deep=True)
 if len(x)!=1: raise ValueError('Expected one original feature row')
 if not set(updates).issubset(features): raise ValueError('Unapproved what-if input')
 for key,val in updates.items():
  if key not in x.columns: raise ValueError('Missing model input: '+key)
  v=float(val)
  if not np.isfinite(v) or v<0: raise ValueError('Invalid nonnegative input: '+key)
  if key in ('Order_Quantity','Planned_Lead_Days') and v<1: raise ValueError(key+' must be positive')
  if key=='Delay_Scenario_Days' and int(v) not in (3,5,7): raise ValueError('Delay must be 3, 5 or 7 days')
  if key=='Delay_Scenario_Days':v=int(v)
  x.loc[x.index[0],key]=v
 if 'Unit_Cost_Premium' in updates:
  # Cost variables are linked: preserve original normal price and update emergency price.
  x.loc[x.index[0],'Emergency_Unit_Cost']=float(x.iloc[0]['Normal_Unit_Cost'])+float(updates['Unit_Cost_Premium'])
 return x

def score(model, x, cols):
 y=float(np.asarray(model.predict(x[cols]),dtype=float)[0])
 if not np.isfinite(y):raise ValueError('Model produced a nonfinite prediction')
 return max(0.0,y)

def describe_changes(base, changed, keys):
 result=[]
 for key in keys:
  old=float(base.iloc[0][key]); new=float(changed.iloc[0][key])
  if not np.isclose(old,new,rtol=0,atol=1e-9):result.append(f'{LABELS[key]}: {old:,.2f} to {new:,.2f}')
 return result

def narrative(kpi, changes, baseline, updated, unit):
 delta=updated-baseline
 changed='; '.join(changes) if changes else 'No predictor values were changed'
 interpretation=('This model estimates additional unmet demand under a hypothetical delay. Compare stock and demand assumptions before deciding whether to investigate the PO.'
                 if kpi=='kpi2' else
                 'This direct model estimates the incremental emergency procurement premium, not total purchasing expenditure. Check the assumed emergency unit-price premium and stock exposure.')
 return (f'**Scenario inputs:** {changed}.\n\n'
         f'**Model result:** Baseline {baseline:,.2f} {unit}; updated {updated:,.2f} {unit}; '
         f'change {delta:+,.2f} {unit}.\n\n'
         f'**Decision context:** {interpretation} '
         '**Limitations:** The output is a model-based sensitivity scenario, not a causal estimate, guaranteed outcome, or recommendation to purchase. '
         'The model was trained on synthetic retrospective simulator targets, not observed future outcomes. '
         'The original PO, operational screening flags, and decision records are unchanged.')

def render(db, queue, review_date, selected):
 st.subheader('Interactive What-If Prediction')
 st.caption('Explore frozen-model sensitivity for the selected PO. Each KPI has a separate baseline and a generated summary. Input substitutions are not causal interventions.')
 choice=st.radio('Choose predictive model', ['KPI 1 — Late-delivery risk','KPI 2 — Incremental shortage','KPI 3 — Direct emergency premium'],horizontal=True)
 kpi=choice.split(' ')[1].lower()
 if kpi=='1':
  _render_kpi1(db,queue,review_date,selected)
 else:
  _render_regression(db,review_date,selected,'kpi'+kpi)

def _render_kpi1(db,queue,review_date,selected):
 from predictive_risk_3c2 import load_locked_model
 model=load_locked_model(os.environ.get('SUPPLIER_DSS_MODEL',EXPECTED['kpi1'][1]),
                         os.environ.get('SUPPLIER_DSS_MODEL_LOCK','predictive_model_lock/model_lock_manifest.json'))
 base=baseline_for_po(db,queue,review_date,selected)
 original=base.iloc[0]
 initial=float(model.predict_proba(base)[0,1])
 st.metric('Original baseline score',f'{initial:.1%}')
 st.caption('KPI 1 scores are uncalibrated. Supplier history is observed evidence, not an operational control.')
 key=f'w104b_kpi1_{review_date}_{selected}'
 with st.form(key):
  c1,c2=st.columns(2)
  with c1:
   qty=st.number_input('Order quantity (units)',min_value=1.,value=float(original.Order_Quantity),step=1.,key=key+'_qty')
   lead=st.number_input('Planned lead time (days)',min_value=max(1,int(original.Days_To_Promise)),max_value=365,value=int(original.Planned_Lead_Days),key=key+'_lead')
  with c2:
   completed=st.number_input('Completed supplier POs (previous 90 days)',min_value=0,value=int(original.Supplier_Completed_90d),key=key+'_count')
   rate=st.number_input('Supplier late rate (%)',min_value=0.,max_value=100.,value=float(original.Supplier_Late_Rate_90d)*100 if pd.notna(original.Supplier_Late_Rate_90d) else 0.,key=key+'_rate')
  submit=st.form_submit_button('Run KPI 1 what-if')
 if submit:
  try:
   out=compare_hypothetical(model,base,order_quantity=qty,planned_lead_days=lead,
        supplier_completed_90d=completed,supplier_late_rate_90d=rate/100 if completed else None)
   save_whatif(db,review_date,selected,out)
   st.session_state[key+'_result']={'out':out,'qty':qty,'lead':lead,'completed':completed,'rate':rate}
  except (ValueError,TypeError) as exc:st.error(str(exc))
 result=st.session_state.get(key+'_result')
 if result:
  out=result['out']; b=float(out['baseline_probability']); u=float(out['hypothetical_probability'])
  a,c,d=st.columns(3)
  a.metric('Baseline',f'{b:.1%}');c.metric('Updated',f'{u:.1%}');d.metric('Change',f'{(u-b)*100:+.2f} pp')
  before=out['baseline_features'].iloc[0];after=out['hypothetical_features'].iloc[0]
  changes=[]
  for field in ('Order_Quantity','Planned_Lead_Days','Supplier_Completed_90d','Supplier_Late_Rate_90d','Supplier_History_Missing'):
   x,y=before[field],after[field]
   if pd.isna(x) and pd.isna(y):continue
   if pd.isna(x) or pd.isna(y) or not np.isclose(float(x),float(y)):
    changes.append(f'{field}: {"missing" if pd.isna(x) else x} to {"missing" if pd.isna(y) else y}')
  st.markdown('**Automatically generated what-if summary**')
  st.write(f'**Scenario inputs:** {"; ".join(changes) if changes else "No predictors changed"}.\n\n'
           f'**Prediction:** Baseline {b:.2%}; updated {u:.2%}; change {(u-b)*100:+.2f} percentage points.\n\n'
           '**Implications and limitations:** This change indicates model sensitivity, not an established effect of changing procurement practice. '
           'Supplier history is not an operational lever. Scores are uncalibrated and do not authorize an automatic intervention. '
           'The original PO, retrospective scenarios, and management screening are unchanged.')
  st.caption('The KPI 1 scenario is also available in Screen 8 as a hypothetical comparison; KPI 2 and KPI 3 remain original there.')

def _render_regression(db,review_date,selected,kpi):
 from w10_3b4_dashboard import frozen_models
 frame=live_features(db,int(selected),str(review_date))
 models=frozen_models(model_paths())
 artifact,model=models[kpi]
 cols=artifact['features']
 keys=EDITABLE[kpi]
 scenario=st.selectbox('Original delay scenario', [3,5,7],index=2,key=f'w104b_delay_{kpi}_{review_date}_{selected}')
 base=frame.loc[frame.Delay_Scenario_Days==scenario].copy()
 if len(base)!=1:raise ValueError('Original scenario unavailable')
 original=score(model,base,cols)
 unit='shortage units' if kpi=='kpi2' else 'currency units of direct emergency premium'
 st.metric('Original baseline prediction',f'{original:,.2f} {unit}')
 st.caption('Inputs default to original PO values. Editing any value affects only this hypothetical model prediction.')
 key=f'w104b_{kpi}_{review_date}_{selected}_{scenario}'
 with st.form(key):
  updates={}
  left,right=st.columns(2)
  for i,field in enumerate(keys):
   container=left if i%2==0 else right
   with container:
    if field=='Delay_Scenario_Days':
     updates[field]=st.selectbox(LABELS[field],[3,5,7],index=[3,5,7].index(scenario),key=key+'_'+field)
    else:
     val=float(base.iloc[0][field]); step=1. if field=='Order_Quantity' else .1
     updates[field]=st.number_input(LABELS[field],min_value=1. if field=='Order_Quantity' else 0.,value=val,step=step,key=key+'_'+field)
  submitted=st.form_submit_button('Run '+kpi.upper()+' what-if')
 if submitted:
  try:
   changed=validated_changes(base,updates,keys)
   updated=score(model,changed,cols)
   st.session_state[key+'_result']={'baseline':original,'updated':updated,'changes':describe_changes(base,changed,keys)}
  except (ValueError,TypeError,KeyError) as exc:st.error('What-if input error: '+str(exc))
 result=st.session_state.get(key+'_result')
 if result:
  b,u=result['baseline'],result['updated']
  a,c,d=st.columns(3)
  a.metric('Original baseline',f'{b:,.2f}');c.metric('Updated prediction',f'{u:,.2f}');d.metric('Change',f'{u-b:+,.2f}')
  st.markdown('**Automatically generated what-if summary**')
  st.markdown(narrative(kpi,result['changes'],b,u,unit))
  st.info('These KPI 2/3 hypothetical outputs are intentionally isolated from Screen 8 original PO evidence and Screen 9 human decision records.')
