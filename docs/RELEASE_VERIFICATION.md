# GitHub Release Verification

## Completed local validation

- W10.4B functional testing: 12/12 PASS
- W10.4C verification: 17 PASS, 0 FAIL, 3 NOT_EVALUATED
- W10.5 static release checker: 29 PASS, 0 FAIL
- Clean-environment dependency installation: PASS
- Nine-screen Streamlit runtime testing: PASS
- Four approved core artifact SHA256 checks: PASS
- Release manifest verification: 35/35 PASS
- Decision_Records table: 0 rows
- Git LFS configured for the SQLite database and three models

These results were reported from local project-owner testing.

## GitHub publication requirements

1. Confirm public data and model sharing authorization.
2. Exclude private decision records and credentials.
3. Verify approved release file hashes.
4. Update documentation for GitHub.
5. Verify Git LFS tracking.
6. Review the files staged for commit.
7. Push to a public GitHub repository.
8. Confirm that Git LFS objects uploaded successfully.
9. Verify public repository access.
10. Verify that a fresh clone retrieves the required assets.

## Application startup

Use Python 3.13 from the repository root.

    py -3.13 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python -m streamlit run app_w10_4b.py

## Research limitations

This academic prototype uses synthetic procurement data.
It is not validated for operational clinical procurement.
Predictions and what-if scenarios do not establish causation.

Do not publish decision_records_local.db or human decision records.

## Publication status

Local validation completed.
GitHub publication and external access verification pending.
