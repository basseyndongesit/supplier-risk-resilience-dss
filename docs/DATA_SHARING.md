# Public Data and Model Sharing

## Authorization

The project owner confirmed on October 27, 2026, that public
publication of the synthetic project database and three trained
predictive models is permitted.

## Included research assets

- Synthetic SQLite procurement database
- Three frozen predictive models
- Supporting validation and explainability evidence
- Streamlit application source code
- Academic progress report

## Restrictions

The repository must not contain real patient information,
personal decision records, credentials, or confidential data.

The local decision database, decision_records_local.db,
is excluded from publication.

The application may create a new local decision database
during use. Such records must not be committed to GitHub.


## Accessing the shared release assets

Current release branch:
https://github.com/basseyndongesit/supplier-risk-resilience-dss/tree/week11-model-validation

Install Git and Git LFS, then run:

    git lfs install
    git clone --branch week11-model-validation https://github.com/basseyndongesit/supplier-risk-resilience-dss.git
    cd supplier-risk-resilience-dss
    git lfs pull

Required assets (retain their relative paths):

- supplier_risk_output/supplier_risk.db
- predictive_model_output/random_forest.joblib
- w10_2b_model_output/kpi2_shortage_validation_selected.joblib
- w10_2b_model_output/kpi3_emergency_premium_validation_selected.joblib
- predictive_model_lock/model_lock_manifest.json
- w10_2a_dataset_output/validation.csv

The four database/model assets use Git LFS. Remote download
availability was verified on November 1, 2026.

For Python dependencies and application startup, follow README.md.
The current Streamlit entry point is app_w11.py.

The local decision_records_local.db must never be published.
The independent final-test partition is not required to run the
application and is not included in these access instructions.
The revised KPI 2 and KPI 3 methods have not been evaluated on
the independent final-test partition.
## Research limitations

The data are synthetic. The predictive models have not been
validated for real-world clinical procurement decisions.

Predictions and interactive what-if comparisons do not
establish causal effects.

## Publication

GitHub repository visibility: PUBLIC.

Public access must be verified after the initial push.
