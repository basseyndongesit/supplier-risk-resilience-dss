"""Week 11 what-if UI. Isolated copy for validation-selected improvements."""
import os
import numpy as np
import pandas as pd
import streamlit as st
from w10_3b2a_live_features import build as live_features
from w10_3b2a_score_frozen import EXPECTED, KPI1_FEATURES
from w10_3b4_dashboard import frozen_models, save_whatif
from w11_scenario_scoring import score_scenarios
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
         ''
         'The original PO, operational screening flags, and decision records are unchanged.')

def render(db, queue, review_date, selected):
 st.subheader('Interactive What-If Prediction')
 st.caption('Explore how changes to planning assumptions affect the predicted results for this purchase order.')
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


def score_week11_regression_scenarios(frame):
    """Score complete 3/5/7-day scenarios with frozen KPI 2/3 models.

    Returns the original and validation-selected revised predictions.
    Does not train models, access final-test data, or write to the database.
    """
    models = frozen_models(model_paths())

    kpi2_artifact, _ = models["kpi2"]
    kpi3_artifact, _ = models["kpi3"]

    return score_scenarios(
        frame,
        kpi2_artifact,
        kpi3_artifact,
    )




W11_TRAINING_P99 = {
    "Order_Quantity": 1023.0,
    "Available_Inventory_at_review": 1301.0,
    "Safety_Stock_Level_at_review": 458.0,
    "Demand_SMA_30d": 41.5,
    "Unit_Cost_Premium": 88.96,
}

W11_WHOLE_NUMBER_FIELDS = {
    "Order_Quantity",
    "Available_Inventory_at_review",
    "Safety_Stock_Level_at_review",
}


def validate_week11_inputs(updates, kpi):
    """Validate revised what-if inputs and identify extrapolation warnings."""
    if kpi not in ("kpi2", "kpi3"):
        raise ValueError("Unsupported regression KPI")

    if not isinstance(updates, dict):
        raise TypeError("Updates must be a dictionary")

    allowed = set(EDITABLE[kpi])

    if not set(updates).issubset(allowed):
        raise ValueError("Unapproved what-if input")

    clean = {}
    warnings = []

    for field, raw_value in updates.items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f"{field} must be numeric") from None

        if not np.isfinite(value):
            raise ValueError(f"{field} must be finite")

        if field == "Delay_Scenario_Days":
            if value not in (3.0, 5.0, 7.0):
                raise ValueError("Delay must be exactly 3, 5, or 7 days")
            clean[field] = int(value)
            continue

        if value < 0:
            raise ValueError(f"{field} cannot be negative")

        if field == "Order_Quantity" and value < 1:
            raise ValueError("Order quantity must be positive")

        if field in W11_WHOLE_NUMBER_FIELDS:
            if not value.is_integer():
                raise ValueError(f"{field} must be a whole number")
            clean[field] = int(value)
        else:
            clean[field] = value

        threshold = W11_TRAINING_P99.get(field)

        if threshold is not None and value > threshold:
            warnings.append(
                f"{field} exceeds the training-data 99th percentile "
                f"({threshold:g}). The prediction may be less reliable."
            )

    return clean, warnings

def calculate_week11_whatif(frame, updates, kpi):
    """Calculate revised hypothetical predictions for all delay scenarios."""
    clean_updates, advisory_warnings = validate_week11_inputs(
        updates, kpi
    )
    allowed = set(EDITABLE[kpi])

    if len(frame) != 3:
        raise ValueError("Expected three baseline scenarios")

    if sorted(frame["Delay_Scenario_Days"].tolist()) != [3, 5, 7]:
        raise ValueError("Expected delay scenarios 3, 5, and 7")

    original = score_week11_regression_scenarios(frame)

    changed = frame.copy(deep=True)
    scenario_delay = clean_updates.get("Delay_Scenario_Days")

    # The delay selection identifies which result to display.
    # All three scenarios must still be scored.
    feature_updates = {
        key: value
        for key, value in clean_updates.items()
        if key != "Delay_Scenario_Days"
    }

    for index in changed.index:
        row = changed.loc[[index]].copy()
        revised_row = validated_changes(
            row,
            feature_updates,
            allowed - {"Delay_Scenario_Days"},
        )
        for field in feature_updates:
            changed.loc[index, field] = revised_row.iloc[0][field]

        if "Unit_Cost_Premium" in feature_updates:
            changed.loc[index, "Emergency_Unit_Cost"] = (
                revised_row.iloc[0]["Emergency_Unit_Cost"]
            )

    revised = score_week11_regression_scenarios(changed)

    if scenario_delay is not None:
        delay = float(scenario_delay)
        if not np.isfinite(delay) or delay not in (3, 5, 7):
            raise ValueError("Delay must be exactly 3, 5, or 7 days")
        selected_delay = int(delay)
    else:
        selected_delay = 7

    return {
        "original": original,
        "updated": revised,
        "selected_delay": selected_delay,
        "changed_features": list(feature_updates),
        "advisory_warnings": advisory_warnings,
    }

def render_week11_scenario_panel(frame, kpi):
    """Display validation-selected 3/5/7-day predictions."""
    result = score_week11_regression_scenarios(frame)

    if kpi == "kpi2":
        original = "Original_KPI2_Shortage"
        revised = "Revised_KPI2_Shortage"
        unit = "shortage units"
        title = "Incremental Shortage Scenarios"
    elif kpi == "kpi3":
        original = "Original_KPI3_Direct_Cost"
        revised = "Revised_KPI3_Chained_Cost"
        unit = "currency units"
        title = "Emergency Procurement Premium Scenarios"
    else:
        raise ValueError("Unsupported KPI")

    display = result[
        ["Delay_Scenario_Days", original, revised]
    ].copy()

    display["Revision_Delta"] = (
        display[revised] - display[original]
    )

    display.columns = [
        "Assumed delay (days)",
        "Original prediction",
        "Revised prediction",
        "Difference",
    ]

    with st.expander(
        "Model Comparison: " + title,
        expanded=False,
    ):
        st.dataframe(
            display.round(2),
            hide_index=True,
            use_container_width=True,
        )

        revised_values = result[revised].to_numpy(dtype=float)
        difference = revised_values[-1] - revised_values[0]

        st.metric(
            "Revised prediction: 7-day minus 3-day delay",
            f"{difference:+,.2f} {unit}",
        )

        st.caption(
            "These are model-based scenario estimates, not causal effects. "
            "The revised KPI 2 method enforces nondecreasing shortage "
            "predictions across the three delays. Revised KPI 3 uses "
            "predicted shortage multiplied by the assumed unit-cost premium. "
            "Both methods were selected based on development-validation results."
        )

def _render_regression(db, review_date, selected, kpi):
    """Render revised KPI 2/3 scenario comparison and interactive what-if."""
    frame = live_features(db, int(selected), str(review_date))
    render_week11_scenario_panel(frame, kpi)

    st.divider()
    st.markdown("#### Explore Hypothetical Changes")
    st.caption(
        "Change the assumptions below to compare new predictions "
        "with the original purchase order. These are estimates, "
        "not guaranteed outcomes."
    )

    baseline_row = frame.loc[
        frame["Delay_Scenario_Days"] == 7
    ].iloc[0]

    key = f"w11_whatif_{kpi}_{review_date}_{selected}"

    with st.form(key):
        updates = {}
        left, right = st.columns(2)

        fields = EDITABLE[kpi]

        for index, field in enumerate(fields):
            container = left if index % 2 == 0 else right

            with container:
                if field == "Delay_Scenario_Days":
                    updates[field] = st.selectbox(
                        LABELS[field],
                        [3, 5, 7],
                        index=2,
                        key=key + "_" + field,
                    )
                else:
                    value = float(baseline_row[field])

                    if field in W11_WHOLE_NUMBER_FIELDS:
                        updates[field] = st.number_input(
                            LABELS[field],
                            min_value=1 if field == "Order_Quantity" else 0,
                            value=int(value),
                            step=1,
                            key=key + "_" + field,
                        )
                    else:
                        updates[field] = st.number_input(
                            LABELS[field],
                            min_value=0.0,
                            value=value,
                            step=0.1,
                            key=key + "_" + field,
                        )

        submitted = st.form_submit_button(
            "Calculate Scenario"
        )

    if submitted:
        try:
            result = calculate_week11_whatif(
                frame, updates, kpi
            )
            st.session_state[key + "_result"] = result
        except (ValueError, TypeError, KeyError) as exc:
            st.session_state.pop(key + "_result", None)
            st.error("What-if input error: " + str(exc))

    result = st.session_state.get(key + "_result")

    if result is None:
        return

    original = result["original"]
    updated = result["updated"]
    selected_delay = result["selected_delay"]

    if kpi == "kpi2":
        prediction_column = "Revised_KPI2_Shortage"
        unit = "shortage units"
    else:
        prediction_column = "Revised_KPI3_Chained_Cost"
        unit = "currency units"

    baseline_values = original[
        ["Delay_Scenario_Days", prediction_column]
    ].copy()

    hypothetical_values = updated[
        ["Delay_Scenario_Days", prediction_column]
    ].copy()

    comparison = baseline_values.merge(
        hypothetical_values,
        on="Delay_Scenario_Days",
        suffixes=("_baseline", "_hypothetical"),
        validate="one_to_one",
    )

    comparison["Difference"] = (
        comparison[prediction_column + "_hypothetical"]
        - comparison[prediction_column + "_baseline"]
    )

    comparison = comparison.sort_values(
        "Delay_Scenario_Days"
    )

    comparison.columns = [
        "Assumed delay (days)",
        "Baseline prediction",
        "Scenario prediction",
        "Difference",
    ]

    st.markdown("#### Baseline vs. Scenario Predictions")
    st.dataframe(
        comparison.round(2),
        hide_index=True,
        use_container_width=True,
    )

    selected_row = comparison.loc[
        comparison["Assumed delay (days)"] == selected_delay
    ].iloc[0]

    baseline_prediction = float(
        selected_row["Baseline prediction"]
    )
    hypothetical_prediction = float(
        selected_row["Scenario prediction"]
    )
    difference = float(
        selected_row["Difference"]
    )

    a, b, c = st.columns(3)

    a.metric(
        "Baseline prediction",
        f"{baseline_prediction:,.2f}",
    )
    b.metric(
        "Scenario prediction",
        f"{hypothetical_prediction:,.2f}",
    )
    c.metric(
        "Prediction difference",
        f"{difference:+,.2f}",
    )

    st.caption(
        f"Selected comparison: {selected_delay}-day assumed delay. "
        f"Values are expressed in {unit}."
    )

    warnings_list = result["advisory_warnings"]

    if warnings_list:
        st.caption(
            f"Prediction reliability: {len(warnings_list)} "
            "input(s) exceed the training-data 99th percentile."
        )

        with st.expander(
            "Prediction Reliability Details",
            expanded=False,
        ):
            for warning in warnings_list:
                st.write("- " + warning)

    st.caption(
        "These predictions are estimates, not guaranteed outcomes."
    )

    with st.expander(
        "Model Assumptions and Limitations",
        expanded=False,
    ):
        st.write(
            "Order quantity is a potential planning decision. "
            "Inventory, safety stock, demand, and unit-cost premium "
            "are hypothetical operating or procurement assumptions. "
            "Changing these assumptions does not automatically "
            "change the actual purchase order."
        )
