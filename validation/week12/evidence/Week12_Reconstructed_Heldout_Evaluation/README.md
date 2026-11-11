# Week 12 — Reconstructed held-out KPI2/KPI3 evaluation

## Findings
- Reconstructed the chronological test partition using `build_kpi_dataset_w10_2a.py` and the original synthetic SQLite database.
- Reconstructed test: 29,160 records, 5,392 unique purchase orders, May 28–October 9, 2026. Train/validation counts also match historical reports.
- Replayed the saved original KPI2/KPI3 models and applied the Week 11 correction: groupwise cumulative maximum of shortage predictions across 3/5/7-day delays, followed by multiplication by the known unit-cost premium.
- Results in `heldout_evaluation.json`.

## Limitations
1. Reconstructed CSV SHA-256 (`f968e7e6...`) differs from historical expected test SHA-256 (`0790c669...`). Thus this is NOT a byte-identical reproduction of the original frozen test file. Historical original-model MAEs match to reported precision and rebuilt validation rows match the repository validation.csv numerically.
2. Evaluation runtime scikit-learn 1.8.0 differs from the original model version 1.9.1. Inference succeeded but warnings were generated.
3. The target outcomes are synthetic simulator-derived values, not measured real-world procurement outcomes.
4. The test data were not used here for retraining or tuning. However, the Week 11 corrections were previously selected using development-validation evidence.

## Reproduce
1. Supply the source `supplier_risk.db` and the two trusted `.joblib` files.
2. Use the original builder to generate `train.csv`, `validation.csv`, `test.csv` and the manifest, with default cut dates 2026-01-01 and 2026-05-21.
3. Run `evaluate_reconstructed.py` after updating the three input file paths for your local machine. No model fitting or database writes are performed.
4. Prefer the original scikit-learn 1.9.1 environment and compare dataset hashes before claiming an exact frozen replay.

## Interpret carefully
This supports performance of the final corrections on a reconstructed, temporally held-out *synthetic* partition, not deployment readiness. Retain the hash/environment qualifications in the Week 12 validation matrix and memo.
