# Stage 9 Step 3.1 — Sample Profile Categorical Repair Report

## 1. Document Control

| Field | Value |
| --- | --- |
| Project | Credit Risk Scoring + Fairness Audit |
| Classification | `PORTFOLIO_DEMO_ONLY` |
| Target baseline | `541c4ff8c2a847aa7ffd1fdae751cd6e0a66d414` |
| Repair policy | `PURPOSE_FIXED_ALLOWED_CATEGORY_V1` |
| Status | `IMPLEMENTED_PENDING_HUMAN_AUDIT` |
| Generated at (UTC) | `2026-07-15T14:42:16Z` |

## 2. Scope

This gate repairs only the five synthetic `purpose` fixture values, their direct payload-map materializations, and the two Cell Group 7 export manifests. It does not change application code, model artifacts, thresholds, other profile features, runtime behavior, or deployment state.

## 3. Stage 4 Failure Context

Stage 4 stopped before inference because the ready sample profiles contained numeric `purpose` fixtures that were incompatible with the verified model categories. The previous values were contract fixtures, not valid purpose categories. The failed run rolled back completely.

## 4. Repository Preconditions

The target was clean on `phase8-public-demo-source` at `541c4ff8c2a847aa7ffd1fdae751cd6e0a66d414` with 51 tracked files. `app/src/demo_inference.py` matched its 37,054-byte baseline and SHA-256 `61edf7dca124d6cee04bcc65d1ee4a564d299d104052e8cc06a6bbed39dd27bf`. The development repository was clean at its expected branch and commit.

## 5. Model Categorical Metadata

After model hash verification, metadata-only `joblib.load` inspection confirmed a LightGBM `Booster`, 49 features, `purpose` at zero-based index 40, and these 14 categories: `car`, `credit_card`, `debt_consolidation`, `educational`, `home_improvement`, `house`, `major_purchase`, `medical`, `moving`, `other`, `renewable_energy`, `small_business`, `vacation`, `wedding`.

## 6. Invalid Sample Profile Evidence

Exactly one `purpose` row per profile existed in both direct tables. The obsolete invalid values were: `SP_LOW_RISK_SIGNAL=20`, `SP_MEDIUM_RISK_SIGNAL=50`, `SP_HIGHER_RISK_SIGNAL=80`, `SP_MIXED_SIGNAL=35`, and `SP_LIMITATION_TRANSPARENCY=60`. No authoritative numeric-to-category mapping existed, and no additional tracked artifact directly materialized these profile-purpose pairs.

## 7. Repair Policy

All five profiles now use the fixed allowed category `other`. `FIXED_ALLOWED_CATEGORY_REPAIR` is the fixture-generation lineage stored in the CSV `synthetic_value_source` field; it is not a canonical runtime provenance label. For every repaired sample-profile `purpose` value, canonical runtime provenance remains `value_source = SYNTHETIC_BASELINE`. No fourth canonical value-source label was introduced, and the frozen taxonomy remains `USER_SUPPLIED`, `SYNTHETIC_BASELINE`, and `DERIVED`.

No numeric-to-category mapping was inferred. The category is not historical, model-derived, user-supplied, or ordinally encoded. Using one category for every profile avoids introducing a profile-specific purpose pattern; it does not prove that `other` is neutral to the model.

## 8. Profile-Level Repairs

| Profile | Previous invalid value | Repaired value |
| --- | ---: | --- |
| `SP_LOW_RISK_SIGNAL` | 20 | `other` |
| `SP_MEDIUM_RISK_SIGNAL` | 50 | `other` |
| `SP_HIGHER_RISK_SIGNAL` | 80 | `other` |
| `SP_MIXED_SIGNAL` | 35 | `other` |
| `SP_LIMITATION_TRANSPARENCY` | 60 | `other` |

Each repaired value has `fixture_source = FIXED_ALLOWED_CATEGORY_REPAIR` for contract-repair lineage and `canonical_value_source = SYNTHETIC_BASELINE` for runtime provenance. These dimensions are semantically independent.

## 9. Direct Contract Changes

Only `synthetic_value` and `synthetic_value_source` changed on the ten authorized rows across `sample_profile_feature_matrix.csv` and `demo_payload_profile_payload_map.csv`. The CSV `synthetic_value_source` column records contract-fixture lineage and is semantically distinct from the frozen runtime `value_source` field. Row counts, column schemas, row order, all 240 non-purpose rows per table, and all unrelated purpose-row columns remained unchanged.

## 10. Manifest Updates

Only the matching size, SHA-256, readback size, and readback SHA-256 fields were updated in the CSV and JSON export manifests. Both manifests retain 23 entries; every entry validates against its current target file, and unrelated entries remain unchanged.

## 11. Categorical Compatibility Validation

Each repaired value is the string `other`, belongs to the exact model category list, and is accepted by `pandas.Categorical` without becoming missing. Unknown-category count, categorical-NaN count, and remaining numeric-purpose count are all zero. No model matrix or ordinal encoding was created.

## 12. Unchanged Contract Validation

The unchanged artifacts remain substantively valid: five profiles, 49 canonical features per profile, five complete profile payloads, zero sample-profile mapping gaps, unchanged readiness statuses, and unchanged limitation-aware features `grade_encoded` and `credit_age_months`. Historic Stage 8 identity statements were not rewritten.

## 13. Runtime Non-Execution Evidence

No model or calibrator prediction method was called, `predict_proba` was not called, no inference or probability was generated, Streamlit was not started, and no public deployment occurred. Application code, model bytes, and threshold bytes remain unchanged.

## 14. Limitations

This repair establishes categorical compatibility only. `FIXED_ALLOWED_CATEGORY_REPAIR` must not be interpreted as canonical runtime provenance; canonical `value_source` remains `SYNTHETIC_BASELINE`. It does not validate probabilities, establish risk ordering, prove category neutrality, or show that Stage 4 passes.

## 15. Step 3.1 Completion Criteria

Completion requires exact cell scope, valid categorical values, preserved table invariants, fully valid manifests, unchanged dependent contracts, no runtime execution, and exactly eight changed paths.

## 16. Authorization for Stage 4 Rerun

Stage 4 rerun is not authorized now. Human audit, Git scope review, a repair commit, and a post-commit audit must all pass first. Only human audit and Git scope review are currently authorized.
