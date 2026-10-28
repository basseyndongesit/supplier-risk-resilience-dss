"""Supplier Risk DSS: five approved screens plus read-only predictive risk ranking."""
import os
import sqlite3
from pathlib import Path
from datetime import date as date_type
import pandas as pd
import streamlit as st
from dss_core import (review_dates,review_queue,po_details,scenario_rows,
                      supplier_history,inventory_demand,screening_check)
from predictive_risk_3c2 import load_locked_model, rank_review_queue
from predictive_whatif_3c3 import baseline_for_po, compare_hypothetical
from w10_3b_explainability import render_report
from w10_3b4_dashboard import render_dashboard, save_whatif

st.set_page_config(page_title="Supplier Risk DSS",page_icon="📦",layout="wide",initial_sidebar_state="expanded")
st.title("Supplier Risk & Resilience DSS")
st.caption("Synthetic healthcare procurement prototype • Human-in-the-loop • Frozen-model demonstration")
st.caption('Demonstration data only · Not validated against real healthcare operations · Predictive probabilities are uncalibrated')

DEFAULT_DB=os.environ.get('SUPPLIER_DSS_DB','supplier_risk_output/supplier_risk.db')
db=st.sidebar.text_input('Existing SQLite database path',value=DEFAULT_DB)
if not Path(db).is_file():
    st.error('Database file not found. Enter the path to your existing supplier_risk.db in the sidebar.')
    st.stop()
try:
    dates=review_dates(db)
except (sqlite3.Error, OSError) as exc:
    st.error(f'Cannot read database: {exc}')
    st.stop()
if not dates:
    st.info('No stored review dates found.');st.stop()
review_date=st.sidebar.selectbox('Historical review date',dates)
queue=review_queue(db,review_date)
if queue.empty:
    st.info('No eligible purchase orders on this review date.');st.stop()
po_ids=queue.PO_ID.astype(str).tolist()
selected=st.sidebar.selectbox('Purchase order',po_ids, index=po_ids.index('4952') if '4952' in po_ids else 0)
detail=po_details(db,selected)
scenarios=scenario_rows(db,selected,review_date)
screen=st.sidebar.radio('Screen',[
    '1. Weekly Risk Review','2. PO / Supplier Detail','3. Scenario Comparison',
    '4. Management Review','5. Predictive Risk Ranking',
    '6. Interactive What-If Prediction',
    '7. Model Validation & Explainability Evidence',
    '8. Integrated Decision Dashboard',
    '9. Options & Decision Record'])

if screen.startswith('1.'):
    st.subheader('Weekly Risk Review')
    st.caption('Review-date eligibility comes from stored point-in-time DSS assessments, not the final PO_Status.')
    c1,c2,c3=st.columns(3)
    c1.metric('POs for review',f'{len(queue):,}')
    c2.metric('Flagged for management review',f'{int((queue.Management_Review_Flag==1).sum()):,}')
    c3.metric('Unresolved screening',f'{int(queue.Management_Review_Flag.isna().sum()):,}')
    flagged=st.selectbox('Screening filter',['All','Flagged','Not flagged','Undetermined'])
    subset=queue if flagged=='All' else queue.loc[(queue.Management_Review_Flag==1) if flagged=='Flagged' else (queue.Management_Review_Flag==0) if flagged=='Not flagged' else queue.Management_Review_Flag.isna()]
    display_df=subset[['PO_ID','Supplier_Name','Item_Name','Location_Name','Promised_Delivery_Date','Item_Criticality','Management_Review_Flag','Max_Incremental_Shortage_Units','Max_Emergency_Premium']].copy()
    for name_col in ('Supplier_Name','Item_Name','Location_Name'):
        display_df[name_col]=display_df[name_col].str.replace(r'^Synthetic\s+', '',regex=True)
    display_df['Management_Review_Flag']=display_df['Management_Review_Flag'].map({1:'Yes',0:'No'}).fillna('Pending')
    display_df=display_df.rename(columns={'Management_Review_Flag':'Requires Management Review','Max_Incremental_Shortage_Units':'Maximum Additional Shortage (Units)','Max_Emergency_Premium':'Maximum Emergency Cost Premium'})
    st.dataframe(display_df,hide_index=True,width="stretch",column_config={
        'Maximum Additional Shortage (Units)':st.column_config.NumberColumn(format='%.2f'),
        'Maximum Emergency Cost Premium':st.column_config.NumberColumn(format='$%.2f'),
        'Requires Management Review':st.column_config.TextColumn(help='Yes: MR-01 or MR-02 triggered. No: neither triggered. Pending: insufficient evidence.'),
    })
    st.caption('Max exposure summarizes the three scenarios; it is not an expected loss or a priority score.')
elif screen.startswith('2.'):
    st.subheader('PO / Supplier Risk Detail')
    st.markdown('#### Purchase order information')
    def clean_name(value):
        return str(value).removeprefix('Synthetic ')
    info={
        'PO Number':str(detail['PO_ID']),
        'Supplier':clean_name(detail['Supplier_Name']),
        'Item':clean_name(detail['Item_Name']),
        'Location':clean_name(detail['Location_Name']),
        'Order date':str(detail['PO_Date']),
        'Promised delivery':str(detail['Promised_Delivery_Date']),
        'Order quantity (units)':f"{detail['Order_Quantity']:,.0f}",
        'Criticality':str(detail['Item_Criticality']),
        'Operational consequence':str(detail['Patient_Care_Operational_Consequence'])}
    st.dataframe(pd.DataFrame(list(info.items()),columns=['Field','Value']),hide_index=True,width='stretch')
    hist=supplier_history(db,detail['Supplier_ID'],review_date)
    inv=inventory_demand(db,detail['Item_ID'],detail['Location_ID'],review_date)
    c1,c2,c3=st.columns(3)
    c1.metric('Supplier completed POs (90 days)',hist['completed_last_90_days'])
    c2.metric('Supplier late rate (90 days)',f"{hist['late_rate_last_90_days']:.1%}" if hist['late_rate_last_90_days'] is not None else 'Unavailable')
    c3.metric('Available inventory at review',f"{inv['inventory']:,.0f}" if inv['inventory'] is not None else 'Unavailable')
    st.markdown('#### Inventory and demand at the review date')
    c4,c5,c6=st.columns(3)
    c4.metric('Safety stock (units)',f"{inv['safety_stock']:,.0f}" if inv['safety_stock'] is not None else 'Unavailable')
    c5.metric('30-day average daily demand',f"{inv['mean_daily_demand']:,.2f}" if inv['mean_daily_demand'] is not None else 'Insufficient history')
    c6.metric('Days of demand history',str(inv['demand_days']))
    st.caption('Supplier history includes only deliveries known by the selected historical review date. Full feature-lineage verification remains limited (VAL-24).')
    st.info('Predicted late-delivery probability: unavailable until a trained model is separately validated and deployed.')
elif screen.startswith('3.'):
    st.subheader('Scenario Comparison')
    st.caption('Stored retrospective what-if assessments: same horizon, baseline versus assumed 3/5/7-day delay. These are not forecasts of delay duration.')
    if scenarios.empty:
        st.warning('No stored scenarios for this PO and review date.')
    else:
        base=scenarios.iloc[0]
        st.markdown('#### On-time delivery baseline')
        x,y=st.columns(2)
        x.metric('Baseline stockout days',f"{base['Baseline_Stockout_Days']:.0f}")
        y.metric('Baseline unmet demand (units)',f"{base['Baseline_Unmet_Demand_Units']:,.2f}")
        st.markdown('#### Assumed delivery delays')
        table=scenarios[['Delay_Scenario_Days','Delayed_Stockout_Days','Incremental_Stockout_Days','Delayed_Unmet_Demand_Units','Incremental_Shortage_Units','Estimated_Emergency_Procurement_Cost']].copy()
        table.columns=['Delay (days)','Stockout days with delay','Additional stockout days','Unmet demand with delay (units)','Additional shortage (units)','Additional emergency premium ($)']
        st.dataframe(table,hide_index=True,width='stretch',column_config={
            'Unmet demand with delay (units)':st.column_config.NumberColumn(format='%.2f'),
            'Additional shortage (units)':st.column_config.NumberColumn(format='%.2f'),
            'Additional emergency premium ($)':st.column_config.NumberColumn(format='$%.2f')})
        st.markdown('#### Additional shortage units by delivery delay')
        st.bar_chart(scenarios.set_index('Delay_Scenario_Days')[['Incremental_Shortage_Units']],x_label='Assumed delay (days)',y_label='Additional unmet demand (units)')
        st.caption('Premium is the additional emergency unit-price cost, not total purchasing spend. All scenarios are retrospective what-if estimates.')
elif screen.startswith('4.'):
    st.subheader('Management Review')
    if scenarios.empty:st.warning('No assessment found.')
    else:
        flag=scenarios.Management_Review_Flag.iloc[0]
        st.metric('Management review flag','Undetermined' if pd.isna(flag) else 'Yes' if flag==1 else 'No')
        st.markdown('#### Why this order requires review')
        if (scenarios.Incremental_Shortage_Units>0).any():
            st.write(f"**MR-01 · Delivery-delay exposure:** Up to {scenarios.Incremental_Shortage_Units.max():,.2f} additional units of unmet demand across the assumed delays.")
        if detail['Item_Criticality']=='High' and (scenarios.Baseline_Unmet_Demand_Units>0).any():
            st.write(f"**MR-02 · Critical item already exposed:** High criticality and {scenarios.Baseline_Unmet_Demand_Units.max():,.2f} baseline unmet units.")
        with st.expander('Recorded technical rule evidence'):
            st.write(scenarios.Priority_Reason.iloc[0] or 'No recorded reason')
        expected=screening_check(scenarios,detail['Item_Criticality'])
        st.write('Independent on-screen MR-01/MR-02 consistency check:', 'Insufficient evidence' if expected is None else 'Consistent' if not pd.isna(flag) and bool(flag)==expected else 'Mismatch — investigate')
        st.caption('MR-01: any valid scenario has incremental shortage > 0. MR-02: high-criticality item and baseline unmet demand > 0. The flag is shared across the three scenarios.')
        st.info('The review flag requests human attention; it is not an automatic intervention decision.')
elif screen.startswith('9.'):
    st.subheader('Options & Decision Record')
    st.caption('Final step: review the evidence, choose an action, assign an owner and record the decision. This is a human decision, not an automated recommendation.')
    from w10_3b4_decision_summary import render_decision_evidence
    render_decision_evidence(db, queue, review_date, selected, detail, scenarios)
    st.write('Possible responses to consider:')
#    st.write('Contact supplier · Request expedited delivery · Review temporary safety stock · Redistribute stock · Explore alternate supplier · Increase monitoring')
    st.caption('The validated source database is read-only. Decisions are stored separately in a local companion database. Test entries must be labeled and cleaned up after QA.')
    owner=st.text_input('Decision owner (required to save)')
    action=st.selectbox('Human-selected action',['No action selected','Contact supplier','Request expedite','Temporary safety stock','Redistribute stock','Evaluate alternate supplier','Increase monitoring','Other'])
    rationale=st.text_area('Decision rationale')
    follow=st.date_input('Follow-up date (optional)',value=None)
    record_db=Path(os.environ.get('SUPPLIER_DSS_DECISIONS','decision_records_local.db')).resolve()
    if record_db == Path(db).resolve():
        st.error('Decision database must not be the source database.')
        st.stop()
    if st.button('Save decision'):
        if not owner.strip() or action=='No action selected' or not rationale.strip():
            st.error('Provide owner, selected action and rationale before saving.')
        else:
            try:
                with sqlite3.connect(record_db) as con:
                    con.execute('''CREATE TABLE IF NOT EXISTS Human_Decisions (PO_ID TEXT NOT NULL, Review_Date TEXT NOT NULL, Decision_Date TEXT NOT NULL, Selected_Action TEXT NOT NULL, Decision_Rationale TEXT NOT NULL, Follow_Up_Date TEXT, Decision_Owner TEXT NOT NULL, PRIMARY KEY (PO_ID,Review_Date))''')
                    existing=con.execute('SELECT 1 FROM Human_Decisions WHERE PO_ID=? AND Review_Date=?',(selected,review_date)).fetchone()
                    if existing:st.error('A decision already exists for this PO and review date. No record overwritten.')
                    else:
                        con.execute('INSERT INTO Human_Decisions VALUES (?,?,?,?,?,?,?)',(selected,review_date,date_type.today().isoformat(),action,rationale,str(follow) if follow else None,owner))
                        st.success(f'Decision recorded in {record_db.name}. The original dataset was not modified.')
            except sqlite3.Error as exc:st.error(f'Could not save decision: {exc}')
    if record_db.exists():
        with sqlite3.connect(record_db) as con:
            try:
                records=pd.read_sql_query('SELECT * FROM Human_Decisions WHERE PO_ID=? AND Review_Date=?',con,params=(selected,review_date))
                if not records.empty:st.dataframe(records,hide_index=True,width="stretch")
            except sqlite3.Error:pass
elif screen.startswith('5.'):
    st.subheader('Predictive Late-Delivery Risk Ranking')
    st.caption('Frozen 250-tree random forest. Scores estimate late delivery relative to the promised date, conditional on the PO being open at the selected historical review. Rankings are not MR-01/MR-02 flags.')
    model_path=os.environ.get('SUPPLIER_DSS_MODEL','predictive_model_output/random_forest.joblib')
    lock_path=os.environ.get('SUPPLIER_DSS_MODEL_LOCK','predictive_model_lock/model_lock_manifest.json')
    try:
        model=load_locked_model(model_path,lock_path)
        # The historical review queue contains only point-in-time eligible POs.
        ranked=rank_review_queue(model,db,queue,review_date)
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as exc:
        st.error(f'Predictive ranking unavailable: {exc}')
        st.stop()
    c1,c2,c3=st.columns(3)
    c1.metric('Eligible POs ranked',f'{len(ranked):,}')
    c2.metric('Highest predicted risk',f"{ranked.Model_Late_Probability.max():.1%}")
    c3.metric('Median predicted risk',f"{ranked.Model_Late_Probability.median():.1%}")
    show=ranked[['Model_Rank','PO_ID','Supplier_Name','Item_Name','Location_Name',
                 'Promised_Delivery_Date','Model_Late_Probability',
                 'Supplier_History_Missing','Management_Review_Flag']].copy()
    for col in ['Supplier_Name','Item_Name','Location_Name']:
        show[col]=show[col].astype(str).str.replace(r'^Synthetic\s+','',regex=True)
    show['Supplier_History_Missing']=show['Supplier_History_Missing'].map({1:'Missing (limited evidence)',0:'Available'})
    show['Management_Review_Flag']=show['Management_Review_Flag'].map({1:'Yes',0:'No'}).fillna('Pending')
    show=show.rename(columns={'Model_Rank':'Risk rank','PO_ID':'PO ID',
        'Supplier_Name':'Supplier','Item_Name':'Item','Location_Name':'Location',
        'Promised_Delivery_Date':'Promised delivery',
        'Model_Late_Probability':'Predicted late probability',
        'Supplier_History_Missing':'90-day supplier history',
        'Management_Review_Flag':'Management review (rules)'})
    show['Predicted late probability'] = show['Predicted late probability'] * 100
    st.dataframe(show,hide_index=True,width='stretch',column_config={
        'Predicted late probability':st.column_config.NumberColumn(format='%.1f%%')})
    if (ranked.Supplier_History_Missing==1).any():
        st.warning('Some orders lack 90-day supplier delivery history. Model behavior for genuinely missing-history cases was not independently validated.')
    chosen=ranked.loc[ranked.PO_ID.astype(str)==str(selected)]
    if not chosen.empty:
        st.info(f"Sidebar-selected PO {selected}: predicted late-delivery probability {chosen.Model_Late_Probability.iloc[0]:.1%}; rank {int(chosen.Model_Rank.iloc[0])} of {len(ranked)}.")
    st.caption('Independent test: ROC-AUC 0.608; PR-AUC 0.287; Brier score 0.163. Model is not calibrated; no automatic decision threshold or operational capacity is approved. Probability changes are not causal effects. Bootstrap intervals were not validated to provide 95% coverage and are intentionally not shown.')
    st.caption('Stockout exposure, 3/5/7-day scenario consequences, and MR-01/MR-02 screening remain separate and unchanged.')


elif screen.startswith('6.'):
    from w10_4b_whatif import render
    render(db,queue,review_date,selected)

if screen.startswith('7.'):
    st.info('This screen contains fixed, reproducible VALIDATION examples for technical model review. '
            'They are independent of the PO and review date selected in the sidebar. '
            'For explanations of the selected original PO, use Screen 8 and Generate explanations.')
    render_report(os.environ.get('SUPPLIER_DSS_EXPLAINABILITY_REPORT',
        'w10_3a_explainability_output/w10_3a_explainability_report.json'))

if screen.startswith('8.'):
    render_dashboard(db,queue,review_date,selected,detail,scenarios)

st.divider()
st.caption('Known validation evidence limitations: VAL-16 receipt attribution; VAL-19 receipt timing; VAL-24 feature provenance. Technical validation status remains INCOMPLETE under conditional acceptance.')
