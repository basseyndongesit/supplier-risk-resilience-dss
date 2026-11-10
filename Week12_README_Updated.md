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
python -m streamlit run app_3screen.py
```

Python 3.13 was selected for the deployed three-screen Streamlit Community Cloud application, and the project owner reported that all three screens worked without application error logs. Earlier clean-environment installation and nine-screen runtime testing apply to the previous release, not as independent evidence for this version. If `py -3.13` is unavailable, install a compatible Python version before running these commands. Do not use the original project's virtual environment as proof of clean-install reproducibility.

## Required release assets
- `app_3screen.py`: current three-screen Streamlit entry point. `app_w11.py` remains the earlier nine-screen version for historical reproducibility. Supporting modules include `w11_whatif.py`, `w11_model_evidence.py`, `w11_scenario_scoring.py`, and `w11_dashboard.py`. The previous application entry point, `app_w10_4b.py`, is retained for historical reproducibility.
- `supplier_risk_output/supplier_risk.db`: approved synthetic SQLite database (approximately 159 MB).
- `predictive_model_output/random_forest.joblib`: KPI 1 frozen classifier.
- `w10_2b_model_output/kpi2_shortage_validation_selected.joblib`: KPI 2 frozen regressor.
- `w10_2b_model_output/kpi3_emergency_premium_validation_selected.joblib`: retained historical direct-premium regressor, not the selected current KPI 3 chained calculation.
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
1. **Overview & Risk Monitoring** — historical review queue, supplier/order risk, inventory context, and screening flags.
2. **Predictive Analytics & What-If Scenarios** — retrospective baseline and 3/5/7-day delay comparisons, predictive ranking, interactive what-if estimates, and model evidence.
3. **Management Insights & Decision Records** — MR-01/MR-02 explanations, management interpretation, human-selected actions, and local decision records.

The previous nine-screen interface is retained as `app_w11.py` for historical comparison. The current three-screen application is `app_3screen.py`.

**Live research prototype:** https://supplier-risk-resilience-dss-ggyvgndqgdskqcxlelmg4c.streamlit.app/

**Storage warning:** Decision records are saved in a separate SQLite file (`decision_records_local.db` by default, or `SUPPLIER_DSS_DECISIONS` when configured). On Streamlit Community Cloud the local filesystem is not durable storage; saved decisions can disappear after restarts or redeployment and may be shared across visitors using the same running instance. Do not enter confidential information or rely on the hosted app for permanent records. Use a controlled local test database for reproducible decision-record tests.

**Evidence scope:** Historical development-validation metrics and earlier release tests must not be presented as new independent final-test evidence for the current selected KPI2/KPI3 methods. External-user survey responses are self-reported usability evidence and do not establish independently observed task accuracy.

## Testing and verification evidence
- W10.4B manual functional tests FT-38 through FT-49: **12/12 PASS**, as reported by the project owner.
- W10.4C local automated verification: **17 PASS, 0 FAIL, 3 NOT_EVALUATED**, including 16 unit tests passing; the unevaluated items concerned manual UI, release publication, and report review.
- W10.5 release static checker: **29 PASS, 0 FAIL**, including four approved artifact SHA-256 matches, required file presence, and Python syntax checks.
- Staged application browser retest: project owner confirmed Screens 5, 6 (KPI 1 what-if), and 8 (on-demand explanation) worked after adding the model-lock manifest and validation reference CSV.
- Release hygiene scan: no local decision database, `__pycache__`, `.pyc`, or virtual-environment files detected at the time of the reported check.

The project owner previously confirmed a successful clean-environment installation and nine-screen runtime test for the earlier release. Public GitHub access, fresh-clone retrieval, and SHA-256 verification of all four Git LFS assets have been completed successfully. To rerun the included regression tests from the release root:

```powershell
python -m unittest -v test_w10_4b test_w10_3b4 test_w10_3b3b_on_demand
```

## Current application verification

The earlier nine-screen release passed reported compilation and developer-led review. The project owner has since confirmed that all three screens of the current deployed application work. A five-response external-user evaluation was collected in November 2026; this is self-reported task and usability evidence, not independently observed task completion. The revised KPI 2 and KPI 3 methods have not been evaluated on the independent final-test partition.

## Data, decisions, and interpretation limitations
- The database and operational scenarios are synthetic; results should not be used to direct actual clinical procurement without further validation.
- KPI 1 discrimination is modest and its probabilities are not calibrated.
- KPI 2/3 targets derive from retrospective simulation; they do not establish real-world generalizability.
- Importance and local contributions are noncausal and may vary with correlated features and the selected explanation reference.
- Previously documented limitations in receipt timing/attribution, feature provenance, and uncertainty coverage remain.
- Human decisions are recorded separately in a local companion database (`decision_records_local.db`) created at runtime. **Do not publish that database** or real decision records.
