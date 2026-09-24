# SIF Sentinel — System Architecture

**Project:** SIF Sentinel
**Team:** 6Bits
**Problem Statement ID:** SIH26165
**Theme:** Smart Automation — Smart India Hackathon 2026

---

## 1. Purpose

SIF Sentinel is an AI-assisted safety intelligence platform for **Oil India Limited (OIL)**.
It processes Unsafe-Act / Unsafe-Condition (UA/UC) reports and Near-Miss reports, identifies potential **Serious Injury & Fatality (SIF) precursor signals**, and routes high-priority items for Human Safety Expert (HSE) review.

> **Core principle: AI assists; HSE validates.**
> No safety decision is ever taken autonomously. All AI outputs are advisory.

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React + Vite)                     │
│                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────────┐   │
│  │  Report      │   │  HSE Review  │   │  Analytics Dashboard   │   │
│  │  Submission  │   │  Queue       │   │  (Trends & Patterns)   │   │
│  └──────┬───────┘   └──────┬───────┘   └────────────┬───────────┘   │
└─────────┼─────────────────┼────────────────────────┼───────────────┘
          │  REST / JSON   │                        │
          ▼                ▼                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        BACKEND (Python + FastAPI)                    │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  API Gateway │  │  Auth Layer  │  │  Report Ingestion Router │   │
│  └──────┬───────┘  └──────────────┘  └────────────┬─────────────┘   │
│         │                                          │                 │
│         ▼                                          ▼                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    NLP / AI PIPELINE                         │   │
│  │                                                              │   │
│  │  [1] Text Preprocessor                                       │   │
│  │       └─ Cleaning, normalization, tokenization               │   │
│  │  [2] NLP Entity Extractor (Regex / gazetteers)               │   │
│  │       └─ Activity, Hazard, Location, Barrier, Equipment      │   │
│  │  [3] SIF Classifier (DistilBERT fine-tuned)                  │   │
│  │       └─ Binary: SIF-Precursor | Non-SIF                     │   │
│  │  [4] Deterministic Safety Rule Engine                        │   │
│  │       └─ OIL-specific SIF trigger rules                      │   │
│  │  [5] Priority Scorer                                         │   │
│  │       └─ Composite score (model + rules + severity)          │   │
│  │  [6] Explanation Generator (Deterministic attribution)       │   │
│  │  [7] Similarity Engine (Sentence Transformers + NumPy)       │   │
│  │       └─ Recurring / similar risk pattern detection          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  DATA ACCESS LAYER (SQLAlchemy)              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        DATABASE (SQLite)                             │
│                                                                      │
│   reports | analysis_results | hse_reviews | feedback | embeddings   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Breakdown

### 3.1 Frontend — `frontend/`

| Module | Technology | Role |
|---|---|---|
| Report Submission Form | React | Multi-field form: report type, description, location, date, severity |
| HSE Review Queue | React | List of pending AI-analyzed reports for human review |
| Review Detail Page | React | AI result + entity highlights + explanation; confirm / reject / correct |
| Analytics Dashboard | React + Recharts | Trend charts, SIF rate over time, recurring pattern heatmap |
| Styling | Vanilla CSS | Pure CSS without framework overhead |
| HTTP Client | Native Fetch API | REST calls to FastAPI backend |
| State Management | React Hooks | Server-state synchronization and caching |

### 3.2 Backend — `backend/`

#### API Layer — `backend/api/`
- Built with **FastAPI** (async, auto-generates OpenAPI docs at `/docs`)
- Routes: `/reports`, `/analysis`, `/reviews`, `/dashboard`, `/similar`
- Pydantic schemas for strict input/output validation
- JWT-based authentication (simple, local, no external service)

#### NLP / AI Pipeline — `backend/pipeline/`

| Stage | File | Technology |
|---|---|---|
| Text Preprocessor | `preprocessor.py` | regex, Python stdlib |
| Entity Extractor | `entity_extractor.py` | Regex/Gazetteers + custom rules |
| SIF Classifier | `classifier.py` | HuggingFace Transformers — DistilBERT fine-tuned |
| Rule Engine | `rule_engine.py` | Pure Python deterministic rules |
| Priority Scorer | `scorer.py` | Weighted composite formula |
| Explainer | `decision_engine.py` | Deterministic evidence attribution |
| Similarity Engine | `similarity.py` | `sentence-transformers` + NumPy (in-memory) |

#### Data Layer — `backend/db/`
- **SQLAlchemy** ORM with Alembic migrations
- Async sessions with `asyncpg` (if scalable) or pure sqlite
- Repository pattern: one repository class per entity

### 3.3 Database — SQLite

```sql
-- Core tables (simplified)

reports            -- raw submitted report
analysis_results   -- AI pipeline output linked to a report
hse_reviews        -- HSE officer decision (confirm/reject/correct)
feedback_log       -- structured feedback for retraining
report_embeddings  -- vector embedding per report (for similarity search)
```

---

## 4. NLP / AI Pipeline — Detailed Flow

```
Raw Report Text
      │
      ▼
┌─────────────────────────────────┐
│  STAGE 1: Text Preprocessor     │
│  - Lowercase, strip HTML/noise  │
│  - Expand abbreviations         │
│  - Sentence segmentation        │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  STAGE 2: NLP Entity Extractor  │
│  Entities extracted:            │
│  • ACTIVITY  (e.g. "hot work")  │
│  • HAZARD    (e.g. "H2S leak")  │
│  • LOCATION  (e.g. "well site") │
│  • BARRIER   (e.g. "no PPE")    │
│  • EQUIPMENT (e.g. "crane")     │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  STAGE 3: SIF Classifier        │
│  Model: DistilBERT fine-tuned   │
│  on synthetic + public safety   │
│  incident datasets              │
│  Output: SIF-Precursor / Non-SIF│
│          + confidence score     │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  STAGE 4: Rule Engine           │
│  Deterministic safety rules:    │
│  e.g. IF hazard = "fall_from_   │
│  height" AND barrier_absent     │
│  THEN flag = HIGH               │
│  Rules are auditable YAML/JSON  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  STAGE 5: Priority Scorer       │
│  Score = w1 x model_conf +      │
│          w2 x rule_severity +   │
│          w3 x barrier_gap +     │
│          w4 x recurrence_factor │
│  Range: 0.0 to 1.0              │
│  Bands: LOW / MEDIUM / HIGH /   │
│         CRITICAL                │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  STAGE 6: Explainer             │
│  - Deterministic evidence factors│
│  - Which rules fired            │
│  - Triggered safety categories  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  STAGE 7: Similarity Engine     │
│  - Embed report with SBERT      │
│  - Search NumPy embeddings of past│
│    reports                      │
│  - Return top-k similar reports │
│    (recurring risk detection)   │
└────────────────┬────────────────┘
                 │
                 ▼
         Structured Result
      (stored in DB + returned
        to frontend for HSE
              review)
```

---

## 5. SIF Priority Score Formula

The priority score is a **weighted composite** of four signals:

```
priority_score = (
    w1 x model_confidence      +   # DistilBERT SIF probability
    w2 x rule_severity_score   +   # Deterministic rule output (0-1)
    w3 x barrier_gap_score     +   # Missing/failed barriers detected
    w4 x recurrence_score          # Frequency of similar past events
)

Default weights (tunable):
  w1 = 0.35
  w2 = 0.30
  w3 = 0.20
  w4 = 0.15

Bands:
  0.00 - 0.39  =>  LOW       (informational)
  0.40 - 0.59  =>  MEDIUM    (monitor)
  0.60 - 0.79  =>  HIGH      (HSE review required)
  0.80 - 1.00  =>  CRITICAL  (immediate escalation)
```

---

## 6. Data Flow — End to End

```
[HSE Field Worker]
       │  submits report (text form)
       ▼
[Frontend: Report Form]
       │  POST /api/reports
       ▼
[FastAPI: Report Router]
       │  validates, saves raw report to DB
       │  runs pipeline
       ▼
[NLP Pipeline] (synchronous for MVP)
       │  returns AnalysisResult
       ▼
[FastAPI: Response]
       │  saves AnalysisResult to DB
       ▼
[Frontend: HSE Review Queue]
       │  HSE officer views result
       │  reads explanation, entity highlights
       │  sees similar past reports
       ▼
[HSE Officer Decision]
       │  confirm / reject / correct
       │  PATCH /api/reviews/{id}
       ▼
[FastAPI: Review Router]
       │  saves HseReview + FeedbackLog to DB
       ▼
[Database: feedback_log]
       │  used in periodic model retraining
       ▼
[Analytics Dashboard]
       │  GET /api/dashboard/summary
       └  trend charts, SIF rate, heatmaps
```

---

## 7. Directory Structure

```
SIF-Sentinel/
│
├── backend/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── reports.py
│   │   │   ├── analysis.py
│   │   │   ├── reviews.py
│   │   │   ├── dashboard.py
│   │   │   └── similar.py
│   │   ├── schemas/
│   │   │   ├── report.py
│   │   │   ├── analysis.py
│   │   │   └── review.py
│   │   └── dependencies.py
│   ├── pipeline/
│   │   ├── preprocessor.py
│   │   ├── entity_extractor.py
│   │   ├── classifier.py
│   │   ├── rule_engine.py
│   │   ├── scorer.py
│   │   ├── similarity.py
│   │   └── pipeline.py          # orchestrator
│   ├── db/
│   │   ├── models.py
│   │   ├── repositories/
│   │   │   ├── report_repo.py
│   │   │   ├── review_repo.py
│   │   │   └── feedback_repo.py
│   │   ├── session.py
│   │   └── migrations/          # Alembic
│   ├── rules/
│   │   └── sif_rules.yaml       # auditable safety rules
│   ├── models/                  # saved model checkpoints
│   ├── tests/
│   │   ├── test_preprocessor.py
│   │   ├── test_classifier.py
│   │   ├── test_rule_engine.py
│   │   ├── test_scorer.py
│   │   └── test_api.py
│   ├── main.py
│   ├── config.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ReportForm/
│   │   │   ├── ReviewQueue/
│   │   │   ├── ReviewDetail/
│   │   │   └── Dashboard/
│   │   ├── pages/
│   │   │   ├── Submit.jsx
│   │   │   ├── Queue.jsx
│   │   │   ├── ReviewDetail.jsx
│   │   │   └── Analytics.jsx
│   │   ├── hooks/
│   │   ├── api/
│   │   │   └── client.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── data/
│   ├── raw/                     # public / synthetic datasets
│   ├── processed/
│   └── README.md                # dataset provenance notes
│
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_model_training.ipynb
│   └── 03_evaluation.ipynb
│
├── scripts/
│   ├── seed_db.py
│   └── train_model.py
│
├── ARCHITECTURE.md
├── DEVELOPMENT_PLAN.md
├── AI_RULES.md
└── README.md
```

---

## 8. Technology Justification

| Technology | Why chosen |
|---|---|
| **FastAPI** | Async Python, auto OpenAPI docs, Pydantic validation — ideal for AI backends |
| **DistilBERT** | 40% smaller than BERT, retains 97% accuracy — runs on CPU for demo |
| **Regex/Gazetteers** | Fast, deterministic custom NER, easily supports domain vocabulary |
| **Sentence Transformers** | State-of-art semantic similarity, pre-trained, no fine-tuning needed for search |
| **NumPy** | CPU-friendly vector index for in-memory similarity search |
| **Deterministic Explainer** | Clear rule-based evidence attribution — critical for HSE officer trust |
| **SQLite** | Reliable, structured storage suitable for this scale |
| **SQLAlchemy + Alembic** | Mature ORM with migration support |
| **React + Vite** | Fast dev experience, component model fits complex review workflow |
| **Vanilla CSS** | Rapid, consistent UI with full control |
| **React Hooks** | Handles server-state, caching, loading states cleanly |

---

## 9. Key Design Decisions

1. **Synchronous pipeline for MVP** — The AI pipeline runs inline per request for simplicity. A task queue (Celery/RQ) can be added later without changing the pipeline logic.

2. **YAML rules file** — SIF trigger rules are stored in `backend/rules/sif_rules.yaml`, not hardcoded. This means HSE experts can audit and adjust rules without touching Python code.

3. **Composite scorer** — Combining model confidence with deterministic rules prevents false negatives that a pure ML model might miss (e.g., a factual rule: "fall from height > 2m with no harness = HIGH regardless of model score").

4. **Human-in-the-loop feedback loop** — Every HSE decision is logged in `feedback_log`. This table becomes the training set for the next model version.

5. **No external AI APIs** — All inference is local. No data leaves the system. This is critical for industrial safety data confidentiality.

6. **Explainability first** — Deterministic explanations and rule-fire logs are stored alongside every prediction. HSE officers can see exactly why the system raised a flag.

---

## 10. Security Considerations (MVP)

- All API endpoints require JWT authentication
- Passwords stored as bcrypt hashes
- No PII beyond what HSE submits in the report form
- CORS restricted to frontend origin
- Input sanitized before passing to NLP pipeline
- No external API calls — fully air-gappable

---

*Last updated: September 2026 | Team 6Bits | SIH26165*
