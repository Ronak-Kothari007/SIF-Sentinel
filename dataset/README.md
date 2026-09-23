# Dataset Directory

## Structure

```
dataset/
├── raw/        ← original, unmodified source files
├── processed/  ← cleaned, labelled, tokenized data ready for training
└── README.md   ← this file
```

## Data Policy

Per `AI_RULES.md` Rule AI-5:

- **No real OIL confidential data** is stored here without explicit authorization.
- All data used in the MVP is **public, synthetic, or anonymized**.
- Every dataset must be documented below with its source and license.

## Approved Data Sources (Phase 2 onwards)

| File | Source | License | Description |
|---|---|---|---|
| *(to be added)* | *(public safety reports)* | *(public domain)* | *(safety incident text)* |

## Label Schema

Binary classification label applied to each record:

| Label | Meaning |
|---|---|
| `SIF-Precursor` | Report describes a situation associated with serious injury or fatality risk |
| `Non-SIF` | Report describes a lower-severity safety concern |

## Labeling Rules

1. Labels assigned by minimum 2 team members
2. Uncertain cases default to `Non-SIF` and are excluded from training (conservative)
3. Each label has a `rationale` column explaining the decision
4. Labels stored in `processed/labels.csv`
