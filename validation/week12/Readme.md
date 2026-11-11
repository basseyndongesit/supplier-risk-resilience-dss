# Week 12 — Submission staging package

## Files
- `Week12_Validation_Matrix_Final_Update.xlsx`: updated 28-claim matrix, retaining conservative statuses.
- `Week12_Validation_Memo_Updated.docx`: updated validation memo.
- `Week12_Six_Minute_Demo_Script_Updated.md`: six-minute recording script (video itself not included).
- `evidence/`: reproducible scripts, JSON results, user survey, screenshots, and reconstructed held-out evaluation.

## New held-out evaluation
The revised KPI2 method achieved MAE 1.638142 units versus 1.636574 original and reduced 685 original scenario-order violations to zero. Revised chained KPI3 MAE was $19.352696 versus $38.062231 original direct model on 29,160 reconstructed held-out synthetic rows.

## Restrictions
The reconstructed CSV SHA-256 does not match the historical frozen manifest; runtime scikit-learn 1.8.0 differs from training 1.9.1. These are **reconstructed held-out results**, not byte-identical frozen-test reproducibility or real-world operational validation. Historical Week 11 materials should remain preserved.

## Before submission
1. Copy these materials to a `week12-validation` folder or branch in GitHub; retain Week 11 version.
2. Confirm evidence paths in the matrix relative to your final GitHub layout.
3. Record the required video and add it to `media/` or link it.
4. Review memo and spreadsheet for instructor expectations; verify repository permissions.
5. Group contribution summary is intentionally omitted at the user's request, although the assignment instructions list it as required.
