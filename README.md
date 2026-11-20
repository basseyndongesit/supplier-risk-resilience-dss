# Supplier Risk & Resilience Decision Support System

**Current release: Week 12 three-screen Streamlit application**

**Research prototype | Synthetic healthcare procurement data | Human-in-the-loop decision support**

## 1. Project overview

The Supplier Risk & Resilience Decision Support System (DSS) is an academic research prototype designed to help supply and inventory managers review purchase-order risks, explore potential inventory shortages, compare delivery-delay scenarios, and document management decisions.

The system combines deterministic screening rules, stored operational scenarios, predictive models, and human decision records.

**Important:** The dataset is synthetic. The DSS and its predictions have not been independently validated for real-world healthcare procurement or clinical decision-making. Model predictions and scenario comparisons do not establish causal effects.

## 2. Current application

The current Week 12 application is:

`app_3screen_week12_filters.py`

It organizes the interface into three main screens.

### Screen 1 — Overview & Risk Monitoring

- Weekly Risk Review
- Supplier Details
- Integrated Dashboard

This screen supports review-date selection, purchase-order monitoring, supplier and item filtering, and operational risk summaries.

### Screen 2 — Predictive Analytics & What-If Scenarios

- Scenario Comparison
- Predictive Ranking
- Interactive What-If
- Model Evidence

This screen presents stored baseline and 3-, 5-, and 7-day delay scenarios, experimental predictive rankings, hypothetical input comparisons, and model-evaluation information.

### Screen 3 — Management Insights & Decision Records

- Management Review
- Decision Records

This screen presents management-oriented summaries and supports recording human-selected actions and supporting rationale.

## 3. Installation and launch

The Week 12 release was successfully tested in a fresh GitHub clone using Python 3.13.18 on Windows.

Clone the repository and select the current release branch:

```powershell
git clone https://github.com/basseyndongesit/supplier-risk-resilience-dss.git
cd supplier-risk-resilience-dss
git switch week12-validation
```

Create a virtual environment using an available Python 3.13 installation:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `py -3.13` is unavailable, substitute the full path to an installed Python 3.13 executable when creating the environment.

Launch the application:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app_3screen_week12_filters.py
```

The application requires the approved SQLite database and model assets to be present at their expected relative paths. Git LFS may be required to retrieve large tracked assets.

The successful clean-clone test does not establish complete functional regression coverage.

## 4. Dependencies

The Week 12 release uses the pinned dependencies in `requirements.txt`:

| Package | Version |
|---|---|
| Streamlit | 1.66.0 |
| pandas | 2.3.3 |
| NumPy | 2.5.4 |
| scikit-learn | 1.9.1 |
| joblib | 1.6.0 |
| SciPy | 1.18.1 |

The clean-environment verification used Python 3.13.18.

## 5. Core application modules

| Module | Responsibility |
|---|---|
| `app_3screen_week12_filters.py` | Current three-screen Streamlit entry point |
| `dss_core.py` | Review dates, review queue, purchase-order details, scenario data, and screening information |
| `predictive_risk_3c2.py` | Locked late-delivery model loading and predictive ranking |
| `predictive_whatif_3c3.py` | Baseline and hypothetical prediction comparisons |
| `w10_3b_explainability.py` | Model explanation reporting |
| `w11_model_evidence.py` | Model evaluation and selection evidence |
| `w11_dashboard.py` | Integrated dashboard and supporting decision functionality |

These are application and inference dependencies. They should not automatically be interpreted as the original model-training scripts.

Historical scripts and earlier application versions remain in the repository for research traceability.

## 6. Screening rules

The DSS uses deterministic management-review screening rules.

**MR-01 — Incremental exposure:** An order is flagged when at least one evaluated delay scenario produces additional shortage units greater than zero.

**MR-02 — Critical baseline shortage:** An order is flagged when its item has High criticality and the baseline scenario has unmet demand greater than zero.

These rules are distinct from predictive late-delivery risk scores. A management-review flag is not a model-estimated probability.

The screening rules reflect the research prototype's defined assumptions and have not been independently approved as real-world healthcare procurement policy.

## 7. Predictive KPIs and model evidence

The DSS includes three predictive KPI areas.

| KPI | Documented approach | Important qualification |
|---|---|---|
| KPI 1 — Late-delivery risk | Frozen Random Forest classifier | Experimental risk estimates; probabilities are not calibrated or approved for operational decisions |
| KPI 2 — Incremental shortage | Frozen Random Forest regression approach with documented scenario-order correction | Predictions are based on synthetic operational outcomes |
| KPI 3 — Emergency procurement premium | Documented direct-premium model and revised chained estimation approach using predicted shortage and a nonnegative unit-cost premium | The historical direct model and revised calculation must not be confused |

The Week 11 model-evaluation documentation reports the following development-validation results:

- KPI 1: ROC-AUC 0.6201; PR-AUC 0.3300. The calibration candidate was rejected.
- KPI 2: MAE 1.5778 units for the revised method; reported scenario-order violations reduced from 726 to zero.
- KPI 3: MAE 20.9233 currency units for the revised method; reported improvement of 55.14% over the original direct-model development-validation MAE.

These are **development-validation findings**, not independent real-world performance estimates.

For methodology, model selection, historical independent-test findings, and remaining limitations, see:

- [Week 11 Evaluation Report](WEEK_11_EVALUATION_REPORT.md)
- [Consolidated Model Evaluation and Selection Report](docs/MODEL_EVALUATION_REPORT.md)
- `evaluation/kpi1_validation_consolidated.json`
- `evaluation/kpi23_validation_selection.json`

The frozen model artifacts include:

- `predictive_model_output/random_forest.joblib`
- `w10_2b_model_output/kpi2_shortage_validation_selected.joblib`
- `w10_2b_model_output/kpi3_emergency_premium_validation_selected.joblib`

The existence of a frozen artifact does not by itself identify the original training script or prove that every historical model is invoked directly by the current interface.

## 8. Data and storage

The approved synthetic operational database is:

`supplier_risk_output/supplier_risk.db`

The application uses the `SUPPLIER_DSS_DB` environment variable when provided; otherwise, it defaults to the database path above.

Human decision records are stored separately in a local SQLite database:

`decision_records_local.db`

The `SUPPLIER_DSS_DECISIONS` environment variable can override this default path.

**Storage limitation:** Local decision