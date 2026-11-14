# Supplier Risk & Resilience Decision Support System

## Evaluation Report

**[Week 11 Evaluation Report ? Model Validation and Application Testing](WEEK_11_EVALUATION_REPORT.md)**

This report documents the evaluation design, data-leakage checks, model performance and baseline comparisons, attempted improvements, final model-selection decisions, developer-led application testing, and remaining limitations.

**Three-screen research prototype | Synthetic healthcare procurement data | Human-in-the-loop**

## Research report and application demonstration

The following materials accompany the research prototype:

- **[Week 10 Progress Report](docs/Progress_Report.docx):** Documents the research purpose, predictive models, evaluation evidence, application functionality, and limitations.
- **[Application Demonstration Video](media/Demonstration_Video.mp4):** Recorded walkthrough of the earlier Streamlit release.
- **[Consolidated Model Evaluation and Selection Report](docs/MODEL_EVALUATION_REPORT.md):** Documents the current development-validation results and model-selection decisions.

These materials document a research prototype using synthetic data. The application and its predictions are not validated for real-world clinical or procurement decisions.

## Purpose and intended use
This three-screen Streamlit application helps a supply or inventory manager review supplier purchase-order risk, retrospective shortage scenarios, predictive KPI estimates, and human decisions. It is an academic prototype based on synthetic data, not a clinically or operationally validated decision system. Model predictions and what-if changes are not causal effects.

## Quick start (Windows PowerShell)
Use Python 3.13 with a clean virtual environment. From the release folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app_3screen_week12_filters.py
```

The listed Python version reflects the previously tested local environment. **A separate clean-environment installation and nine-screen runtime test were completed for an earlier release; a fresh-install test of the updated three-screen entry point is not yet documented.** If `py -3.13` is unavailable, install a compatible Python version before running these commands. Do not use the original project's virtual environment as proof of clean-install reproducibility.

## Required release assets
- `app_3screen_week12_filters.py`: updated three-screen Streamlit entry point with supplier/item filters (ensure this file is committed to the repository). `app_3screen.py` is the earlier three-screen version. `app_w11.py` is the historical nine-screen entry point. Supporting modules include `w11_whatif.py`, `w11_model_evidence.py`, `w11_scenario_scoring.py`, and `w11_dashboard.py`. The previous application entry point, `app_w10_4b.py`, is retained for historical reproducibility.
- `supplier_risk_output/supplier_risk.db`: approved synthetic SQLite database (approximately 159 MB).
- `predictive_model_output/random_forest.joblib`: KPI 1 frozen classifier.
- `w10_2b_model_output/kpi2_shortage_validation_selected.joblib`: KPI 2 frozen regressor.
- `w10_2b_model_output/kpi3_emergency_premium_validation_selected.joblib`: KPI 3 frozen direct-premium regressor.
- `predictive_model_lock/model_lock_manifest.json`: model-lock metadata used by KPI 1.
- `w10_2a_dataset_output/validation.csv`: reference data needed for on-demand local explanation.
- `requirements.txt`: dependency specification; installation was tested in a separate clean Python environment.

Keep these relative paths unchanged. If a file is withheld for sharing reasons, supply authorized access instructions; a missing required asset prevents full functionality.

## Three KPIs and models

The current application presents three complementary indicators:

| KPI | Selected approach | Development-validation finding | Decision relevance |
| --- | --- | --- | --- |
| 1. Late-delivery risk | Original frozen random forest classifier | ROC-AUC 0.6201; PR-AUC 0.3300; calibration candidate rejected | Prioritize supplier follow-up |
| 2. Incremental shortage | Frozen random forest with cumulative-maximum correction | MAE 1.5778 units; scenario-order violations reduced from 726 to 0 | Assess potential inventory exposure |
| 3. Emergency procurement premium | Corrected predicted shortage multiplied by nonnegative unit-cost premium | MAE 20.9233 currency units; 55.14% lower than original direct-model validation MAE | Assess potential additional purchasing cost |

These are **development-validation results**, not new independent final-test results.

The earlier release reported independent-test results of ROC-AUC 0.608 for KPI 1, MAE 1.6366 units for KPI 2, and MAE 38.06 currency units for the direct KPI 3 model. It also reported MAE 19.33 currency units for a separate chained KPI 3 estimate. Those historical results do not constitute independent-test evaluation of the current revised methods.

For the evaluation methodology, model-selection rationale, comparison metrics, and limitations, see the **[Consolidated Model Evaluation and Selection Report](docs/MODEL_EVALUATION_REPORT.md)**.

The underlying machine-readable development-validation evidence is retained in:

- `evaluation/kpi1_validation_consolidated.json`
- `evaluation/kpi23_validation_selection.json`

## Current three-screen workflow
1. **Overview & Risk Monitoring:** Weekly Risk Review (management-review screening, supplier and item filters), Supplier Details, and Integrated Dashboard.
2. **Predictive Analytics & What-If Scenarios:** Stored 3/5/7-day scenario comparison, predictive ranking, interactive what-if analysis, and model evidence.
3. **Management Insights & Decision Records:** Management Review and a human-entered decision record. Decisions are saved separately from the synthetic source database.

The system supports three decisions: DR-01 identify purchase orders for management review; DR-02 compare delivery-delay scenarios; and DR-03 record a management response. Rule-based management-review flags and model-estimated late-delivery probabilities are different signals. Stored retrospective simulator outcomes are not observed losses or causal forecasts.

## Week 12–13 validation and submission evidence
The November 2026 validation matrix contains **28 tests: 4 Pass, 22 Partial Pass, and 2 Not Tested**. Partial Pass denotes incomplete acceptance-criterion evidence, not necessarily a software failure. A targeted script reported **28/28 checks passed**; that result does **not** mean all 28 matrix tests passed.

The updated supplier/item filters were demonstrated in Streamlit on 2026-10-09: Supplier 004 + Pharmacy Supplies Item 054 returned one matching PO (8138). The targeted database audit reported 60/60 SQL filter comparisons and 10/10 sampled screening reconciliations; full independent user-task accuracy and all browser combinations have not been established.

The revised KPI2/KPI3 held-out evaluation used a **reconstructed partition**, not a hash-identical replay of the original frozen test file. The revised KPI2 MAE was 1.6381 units versus 1.6366 for the original, with decreasing-shortage scenario groups reduced from 685 to zero. The revised chained KPI3 MAE was 19.3527 currency units versus 38.0622 for the original direct model. These results do not establish real-world generalizability.

**Submission documents:** The updated validation matrix and memo were added to the repository after the ZIP snapshot used for this README update. Insert their verified relative GitHub paths here before committing this README:

- Validation matrix: `REPLACE_WITH_ACTUAL_REPOSITORY_PATH/Validation_Matrix_Week12_Updated.xlsx`
- Validation memo: `REPLACE_WITH_ACTUAL_REPOSITORY_PATH/Week12_Validation_Memo_Submission_Update.docx`
- Demonstration recording: add a link after recording and uploading it.

**Release conclusion:** Suitable for classroom demonstration with disclosed limitations; not validated for live healthcare procurement or clinical operations.

## Testing and verification evidence
- W10.4B manual functional tests FT-38 through FT-49: **12/12 PASS**, as reported by the project owner.
- W10.4C local automated verification: **17 PASS, 0 FAIL, 3 NOT_EVALUATED**, including 16 unit tests passing; the unevaluated items concerned manual UI, release publication, and report review.
- W10.5 release static checker: **29 PASS, 0 FAIL**, including four approved artifact SHA-256 matches, required file presence, and Python syntax checks.
- Staged application browser retest: project owner confirmed Screens 5, 6 (KPI 1 what-if), and 8 (on-demand explanation) worked after adding the model-lock manifest and validation reference CSV.
- Release hygiene scan: no local decision database, `__pycache__`, `.pyc`, or virtual-environment files detected at the time of the reported check.

The project owner previously confirmed a successful clean-environment installation and nine-screen runtime test for the earlier release; this does not independently verify the new three-screen entry point. Public GitHub access, fresh-clone retrieval, and SHA-256 verification of all four Git LFS assets have been completed successfully. To rerun the included regression tests from the release root:

```powershell
python -m unittest -v test_w10_4b test_w10_3b4 test_w10_3b3b_on_demand
```

## Current application verification

The updated three-screen application has passed syntax checks and targeted developer-led tests. Five external questionnaire responses provide self-reported usability feedback, not independently observed task accuracy. Revised KPI 2 and KPI 3 methods were evaluated on a reconstructed held-out partition; the original frozen-file replay has not been established.

## Data, decisions, and interpretation limitations
- The database and operational scenarios are synthetic; results should not be used to direct actual clinical procurement without further validation.
- KPI 1 discrimination is modest and its probabilities are not calibrated.
- KPI 2/3 targets derive from retrospective simulation; they do not establish real-world generalizability.
- Importance and local contributions are noncausal and may vary with correlated features and the selected explanation reference.
- Previously documented limitations in receipt timing/attribution, feature provenance, and uncertainty coverage remain.
- Human decisions are recorded separately in a local companion database (`decision_records_local.db`) created at runtime. **Do not publish that database** or real decision records.
