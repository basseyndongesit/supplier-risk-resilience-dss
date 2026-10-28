# Supplier Risk & Resilience Decision Support System

**Week 10 research prototype | Synthetic healthcare procurement data | Human-in-the-loop**

## Purpose and intended use
This nine-screen Streamlit application helps a supply or inventory manager review supplier purchase-order risk, retrospective shortage scenarios, predictive KPI estimates, and human decisions. It is an academic prototype based on synthetic data, not a clinically or operationally validated decision system. Model predictions and what-if changes are not causal effects.

## Quick start (Windows PowerShell)
Use Python 3.13 with a clean virtual environment. From the release folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app_w10_4b.py
```

The listed Python version reflects the previously tested local environment. **A separate clean-environment installation and nine-screen runtime test were completed successfully by the project owner.** If `py -3.13` is unavailable, install a compatible Python version before running these commands. Do not use the original project's virtual environment as proof of clean-install reproducibility.

## Required release assets
- `app_w10_4b.py`: final Streamlit entry point, with supporting `.py` modules in the release root.
- `supplier_risk_output/supplier_risk.db`: approved synthetic SQLite database (approximately 159 MB).
- `predictive_model_output/random_forest.joblib`: KPI 1 frozen classifier.
- `w10_2b_model_output/kpi2_shortage_validation_selected.joblib`: KPI 2 frozen regressor.
- `w10_2b_model_output/kpi3_emergency_premium_validation_selected.joblib`: KPI 3 frozen direct-premium regressor.
- `predictive_model_lock/model_lock_manifest.json`: model-lock metadata used by KPI 1.
- `w10_2a_dataset_output/validation.csv`: reference data needed for on-demand local explanation.
- `requirements.txt`: dependency specification; installation was tested in a separate clean Python environment.

Keep these relative paths unchanged. If a file is withheld for sharing reasons, supply authorized access instructions; a missing required asset prevents full functionality.

## Three KPIs and models
| KPI | Outcome and model | Independent test result | Decision relevance |
| --- | --- | --- | --- |
| 1. Late delivery | Random forest classifier estimating probability of delivery after the promised date | ROC-AUC 0.608; uncalibrated probability | Prioritize supplier follow-up |
| 2. Incremental shortage | Random forest regressor estimating additional unmet demand under delayed-receipt scenarios versus on-time baseline | MAE 1.6366 units | Evaluate potential service-continuity exposure |
| 3. Direct emergency premium | Histogram gradient boosting regressor estimating additional emergency procurement premium | MAE 38.06 currency units | Evaluate possible financial exposure |

A **separate chained KPI 3 estimate** multiplies predicted KPI 2 shortage by known unit-price premium (test MAE 19.33). It is not the direct trained KPI 3 model. KPI 2 and KPI 3 targets are synthetic retrospective simulator-derived outcomes, not observed future outcomes. Predictor lists and algorithm-selection evidence should be included in the final technical documentation before submission.

## Nine-screen workflow
1. Weekly Risk Review
2. PO / Supplier Detail
3. Scenario Comparison (stored retrospective operational simulations)
4. Management Review
5. Predictive Risk Ranking
6. Interactive What-If Prediction (three models)
7. Model Validation & Explainability Evidence
8. Integrated Decision Dashboard
9. Options & Decision Record

Each model's what-if interface compares a selected baseline with a hypothetical updated prediction, reports the difference, and generates a summary of the edited inputs, practical implications, and limitations. A prediction need not change for every edit. What-if results do not automatically update or save human decisions.

Global feature importance and local reference-based sampled feature contributions are separate forms of evidence. Local explanations on the integrated dashboard are computed on demand for the original selected PO, not for a hypothetical edited record. Attributions do not establish causation.

## Testing and verification evidence
- W10.4B manual functional tests FT-38 through FT-49: **12/12 PASS**, as reported by the project owner.
- W10.4C local automated verification: **17 PASS, 0 FAIL, 3 NOT_EVALUATED**, including 16 unit tests passing; the unevaluated items concerned manual UI, release publication, and report review.
- W10.5 release static checker: **29 PASS, 0 FAIL**, including four approved artifact SHA-256 matches, required file presence, and Python syntax checks.
- Staged application browser retest: project owner confirmed Screens 5, 6 (KPI 1 what-if), and 8 (on-demand explanation) worked after adding the model-lock manifest and validation reference CSV.
- Release hygiene scan: no local decision database, `__pycache__`, `.pyc`, or virtual-environment files detected at the time of the reported check.

The project owner subsequently confirmed a successful clean-environment installation and nine-screen runtime test. External GitHub access remains subject to publication verification. To rerun the included regression tests from the release root:

```powershell
python -m unittest -v test_w10_4b test_w10_3b4 test_w10_3b3b_on_demand
```

## Data, decisions, and interpretation limitations
- The database and operational scenarios are synthetic; results should not be used to direct actual clinical procurement without further validation.
- KPI 1 discrimination is modest and its probabilities are not calibrated.
- KPI 2/3 targets derive from retrospective simulation; they do not establish real-world generalizability.
- Importance and local contributions are noncausal and may vary with correlated features and the selected explanation reference.
- Previously documented limitations in receipt timing/attribution, feature provenance, and uncertainty coverage remain.
- Human decisions are recorded separately in a local companion database (`decision_records_local.db`) created at runtime. **Do not publish that database** or real decision records.
