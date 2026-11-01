# Supplier Risk and Resilience Decision Support System
## Consolidated Model Evaluation and Selection Report

### 1. Executive summary

This report documents the development-validation assessment and model-selection decisions for three predictive indicators in the Supplier Risk and Resilience Decision Support System (DSS).

The DSS supports healthcare procurement and inventory managers by presenting late-delivery risk, potential additional inventory shortages, and potential emergency procurement premiums. It is a research prototype using synthetic procurement data. Its outputs support human review rather than automatic purchasing decisions.

The development-validation findings support retaining the original late-delivery model, applying a consistency correction to shortage predictions, and selecting a chained emergency-premium calculation. These decisions have not been re-evaluated on the independent final-test partition.

### 2. Evaluation scope and safeguards

- Evaluation basis: chronological development-validation partition.
- KPI 2 and KPI 3 validation observations: 27,198.
- KPI 2 and KPI 3 scenario groups: 9,066.
- Delivery-delay scenarios: 3, 5, and 7 days.
- Independent final-test partition: not accessed during this development-validation work.
- Model selection: based on development-validation evidence, not independent final-test outcomes.
- Operational decisions: remain the responsibility of the procurement or inventory manager.

The two machine-readable evidence files are:

- `evaluation/kpi1_validation_consolidated.json`
- `evaluation/kpi23_validation_selection.json`

### 3. KPI 1: Late-delivery risk

**Objective:** Estimate the probability that a purchase order will be delivered late.

**Selected model:** Original frozen random forest.

| Metric | Original frozen model | Calibration candidate |
|---|---:|---:|
| ROC-AUC | 0.6201 | 0.6155 |
| PR-AUC | 0.3300 | 0.3252 |
| Brier score | 0.1727 | 0.1735 |
| Log loss | 0.5259 | 0.5282 |

A sigmoid-calibration candidate was evaluated using development data. It did not improve ROC-AUC, PR-AUC, Brier score, or log loss relative to the original model. The candidate was therefore rejected.

The retained model shows limited ranking discrimination, and probability calibration remains imperfect, particularly in higher-risk groups. No operational classification threshold has been approved.

Supplier-history features use a missing value when no completed deliveries are available, rather than treating an undefined historical late rate as zero. Predictive reliability for missing-history cases could not be evaluated because such cases were absent from validation.

### 4. KPI 2: Incremental shortage

**Objective:** Estimate additional shortage units under assumed delivery delays.

**Selected method:** Frozen random forest with cumulative-maximum correction.

| Measure | Original | Revised |
|---|---:|---:|
| Validation MAE (units) | 1.5768 | 1.5778 |
| Scenario-order violations | 726 | 0 |

The cumulative-maximum correction ensures that the predicted additional shortage does not decrease when the assumed delivery delay increases from 3 to 5 to 7 days for the same scenario group.

This removed the observed scenario-order violations while producing a small increase in validation MAE of approximately 0.0010 units.

The revised method was selected because its scenario ordering is more consistent with the intended planning interpretation, despite the small accuracy trade-off.

### 5. KPI 3: Emergency procurement premium

**Objective:** Estimate the additional emergency purchasing premium associated with predicted shortages.

**Selected method:** Corrected predicted shortage multiplied by nonnegative unit-cost premium.

| Measure | Original direct model | Revised chained method |
|---|---:|---:|
| Validation MAE (currency units) | 46.6384 | 20.9233 |

**Validation MAE reduction:** 55.14%.

The revised method calculates the emergency premium by multiplying the corrected predicted shortage by a nonnegative unit-cost premium.

It achieved lower validation error than the original direct prediction method and produced no scenario-order violations under the evaluated fixed-premium setting.

However, the method reflects the synthetic simulator's shortage-times-premium cost structure. Historical availability of emergency replacement prices has not been independently verified using timestamps. The reported improvement should not be interpreted as proof of equivalent performance with real procurement costs.

### 6. Interpretation for decision-makers

The three indicators answer different questions:

1. **Late-delivery risk:** How likely is the supplier to deliver late?
2. **Incremental shortage:** How much additional inventory shortage might occur if delivery is delayed?
3. **Emergency procurement premium:** What additional emergency purchasing cost might arise from that shortage?

These outputs are separate forms of evidence. A high model score does not automatically trigger a purchase, supplier escalation, or management-review flag.

Operational screening rules and human decision records remain separate from model predictions.

What-If scenarios show how model predictions respond to changed assumptions. They do not establish that changing an operational input will cause the predicted outcome.

### 7. Validation limitations

The following limitations remain relevant:

- Synthetic outcomes do not establish predictive performance on real healthcare procurement data.
- Repeated reviews of the same purchase order create statistical dependence.
- Outcome-maturity filtering may introduce selection bias.
- KPI 1 has limited discrimination and imperfect probability calibration.
- KPI 1 reliability for missing supplier-history cases remains unverified.
- No approved operational late-delivery classification threshold exists.
- The KPI 3 chained calculation depends on the simulator's cost structure.
- Historical availability of emergency replacement prices is not independently timestamp-verified.
- The revised KPI 2 and KPI 3 methods have not been assessed on the independent final-test partition.
- Predictions are not causal estimates or automatic procurement instructions.

The earlier synthetic-data validation and acceptance documentation should be consulted separately for unresolved database-validation limitations.

### 8. Application verification and usability status

Developer-led checks have included source-code compilation, module integration, preservation of original release modules, and interactive review of the What-If, Model Performance and Selection, and Integrated Three-KPI Dashboard screens.

The application screens were reviewed interactively and reported to load correctly after presentation cleanup.

No independent participant usability study has been completed. Formal usability findings, task-completion rates, or participant satisfaction scores are therefore not claimed. Instructor evaluation after submission remains separate from the checks reported here.

### 9. Final model-selection decisions

| KPI | Decision | Rationale |
|---|---|---|
| KPI 1 | Retain original frozen random forest | Calibration candidate did not improve validation metrics |
| KPI 2 | Apply cumulative-maximum correction | Removes scenario-order violations with a small MAE increase |
| KPI 3 | Use corrected shortage multiplied by nonnegative unit-cost premium | Lower validation MAE and consistent scenario ordering |

These decisions are supported by development-validation results only. Additional independent testing and real-world validation would be required before operational deployment.

### 10. Evidence and reproducibility

Machine-readable evidence and associated hashes are retained in the evaluation JSON files. This report summarizes those records without replacing them.

The original historical release files remain preserved. The current application integrates the selected methods through separate modules.

**Report status:** Development-validation evaluation and selection documented; independent final-test evaluation of revised methods not performed.
