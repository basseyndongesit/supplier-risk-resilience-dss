# GitHub Release Verification

## Completed local validation

- W10.4B functional testing: 12/12 PASS
- W10.4C verification: 17 PASS, 0 FAIL, 3 NOT_EVALUATED
- W10.5 static release checker: 29 PASS, 0 FAIL
- Clean-environment dependency installation: PASS
- Nine-screen Streamlit runtime testing: PASS
- Four approved core artifact SHA256 checks: PASS
- Release manifest verification: 37/37 PASS
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
GitHub publication completed successfully.
Repository: https://github.com/basseyndongesit/supplier-risk-resilience-dss
Published release commit: 82a8b5e0f2732d20eab43da556d69bb2aae1bbd7
Git LFS upload: 4/4 assets successful.
Fresh-clone retrieval: 4/4 assets successful.
SHA-256 verification: 4/4 assets PASS.
Fresh-clone working directory: clean.
Public access without signing in: confirmed.
The initial clone reported a security warning involving the standard Git LFS post-checkout hook. Subsequent working-tree and asset-integrity checks passed.
