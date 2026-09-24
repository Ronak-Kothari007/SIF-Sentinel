# SIF Sentinel — Development Plan

**Project:** SIF Sentinel
**Team:** 6Bits
**Problem Statement ID:** SIH26165
**Theme:** Smart Automation — Smart India Hackathon 2026

---

## Overview

This document defines the phased development plan for the SIF Sentinel MVP.
Each phase has a clear goal, specific deliverables, and acceptance criteria.
The plan is designed so that each phase produces a working, demonstrable system.

---

## Phase 0 — Project Bootstrap
**Goal:** Runnable skeleton with zero business logic. CI confirmed working.

### Tasks
- [ ] Initialize Git repository and `.gitignore`
- [ ] Create `backend/` Python project with `pyproject.toml` or `requirements.txt`
- [ ] Create `frontend/` with Vite + React + Vanilla CSS scaffold
- [ ] Set up SQLite
- [ ] Set up Alembic for migrations
- [ ] Confirm `uvicorn backend.main:app --reload` starts cleanly
- [ ] Confirm `npm run dev` starts cleanly

### Deliverables
- Running FastAPI at `http://localhost:8000`
- Running React app at `http://localhost:5173`
- SQLite database initialized
- `GET /health` returns `{"status": "ok"}`

### Acceptance Criteria
- Both servers start with no errors
- Health endpoint responds

---

## Phase 1 — Database Schema & Data Models
**Goal:** All core database tables defined, migrated, and tested.

### Tasks
- [ ] Define SQLAlchemy models: `Report`, `AnalysisResult`, `HseReview`, `FeedbackLog`, `ReportEmbedding`
- [ ] Write and run Alembic migration: `initial_schema`
- [ ] Write basic CRUD for `Report` repository
- [ ] Write seed script `scripts/seed_db.py` with 20–30 synthetic reports
- [ ] Write pytest tests for CRUD operations

### Schema Summary

```
reports
  id              UUID PRIMARY KEY
  submitted_at    TIMESTAMP
  report_type     TEXT  -- 'unsafe_act', 'unsafe_condition', 'near_miss'
  description     TEXT
  location        TEXT
  reported_by     TEXT
  severity_self   TEXT  -- reporter's own severity rating

analysis_results
  id              UUID PRIMARY KEY
  report_id       UUID REFERENCES reports(id)
  analyzed_at     TIMESTAMP
  sif_flag        BOOLEAN
  model_confidence FLOAT
  rule_severity   FLOAT
  barrier_gap     FLOAT
  recurrence_score FLOAT
  priority_score  FLOAT
  priority_band   TEXT  -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
  entities        JSONB
  explanation     JSONB
  similar_reports JSONB

hse_reviews
  id              UUID PRIMARY KEY
  analysis_id     UUID REFERENCES analysis_results(id)
  reviewed_at     TIMESTAMP
  reviewer_id     TEXT
  decision        TEXT  -- 'confirm', 'reject', 'correct'
  corrected_band  TEXT
  notes           TEXT

feedback_log
  id              UUID PRIMARY KEY
  report_id       UUID REFERENCES reports(id)
  review_id       UUID REFERENCES hse_reviews(id)
  ai_label        TEXT
  human_label     TEXT
  logged_at       TIMESTAMP

report_embeddings
  id              UUID PRIMARY KEY
  report_id       UUID REFERENCES reports(id)
  embedding       JSON  -- or NumPy matrix
```

### Deliverables
- All tables created in SQLite
- Seed data loadable via `python scripts/seed_db.py`
- pytest suite for models and repositories passes

---

## Phase 2 — NLP Pipeline (Offline / Standalone)
**Goal:** The 7-stage pipeline runs end-to-end on a single text input, offline.
Each stage has unit tests. No API integration yet.

### Tasks

#### Stage 1 — Text Preprocessor
- [ ] `backend/pipeline/preprocessor.py`
- [ ] Lowercase, strip punctuation noise, expand common safety abbreviations (PPE, JSA, PTW, H2S, LOTO)
- [ ] Sentence segmentation
- [ ] Unit tests: 10+ test cases covering edge cases

#### Stage 2 — Entity Extractor
- [ ] `backend/pipeline/entity_extractor.py`
- [ ] Load regex rules and gazetteers
- [ ] Add custom entity patterns for: ACTIVITY, HAZARD, LOCATION, BARRIER, EQUIPMENT
- [ ] Return structured dict of extracted entities
- [ ] Unit tests covering each entity type

#### Stage 3 — SIF Classifier
- [ ] `backend/pipeline/classifier.py`
- [ ] Load DistilBERT from Hugging Face (`distilbert-base-uncased`)
- [ ] Fine-tune on synthetic safety dataset (30–50 labeled examples for MVP demo; label: SIF-Precursor / Non-SIF)
- [ ] Save fine-tuned model to `backend/models/sif_classifier/`
- [ ] Inference function: text → {label, confidence}
- [ ] Training script: `scripts/train_model.py`
- [ ] Notebook: `notebooks/02_model_training.ipynb`
- [ ] Unit test: model loads and predicts without error

#### Stage 4 — Rule Engine
- [ ] `backend/rules/sif_rules.yaml` — define at least 15 SIF trigger rules
- [ ] `backend/pipeline/rule_engine.py` — load and evaluate rules against entities
- [ ] Rules based on: hazard type, activity type, missing barriers, equipment involved
- [ ] Output: `{rules_fired: [...], rule_severity_score: float}`
- [ ] Unit tests for each rule category

#### Stage 5 — Priority Scorer
- [ ] `backend/pipeline/scorer.py`
- [ ] Implement composite score formula (see ARCHITECTURE.md §5)
- [ ] Weights configurable from `backend/config.py`
- [ ] Output: `{priority_score: float, priority_band: str}`
- [ ] Unit tests for score calculation and band boundaries

#### Stage 6 — Explainer
- [ ] `backend/pipeline/explainer.py`
- [ ] Deterministic attribution: map keywords to severity factors
- [ ] Rule explanation: list of human-readable fired rules
- [ ] Output: `{lime_tokens: [...], rules_fired: [...], summary: str}`
- [ ] Unit test: explainer returns valid structure

#### Stage 7 — Similarity Engine
- [ ] `backend/pipeline/similarity.py`
- [ ] Load `sentence-transformers/all-MiniLM-L6-v2`
- [ ] Build NumPy embedding matrix over seed report embeddings
- [ ] Query: embed new report → top-k similar report IDs + scores
- [ ] Unit test: returns k results from index

#### Pipeline Orchestrator
- [ ] `backend/pipeline/pipeline.py`
- [ ] Calls stages 1–7 in sequence
- [ ] Returns `PipelineResult` dataclass
- [ ] Integration test: run full pipeline on a sample text

### Deliverables
- All 7 pipeline stages independently tested
- `pipeline.py` runs end-to-end and returns structured result
- Fine-tuned DistilBERT checkpoint saved locally
- NumPy embeddings built from seed data

---

## Phase 3 — FastAPI Backend
**Goal:** All API endpoints live, connected to pipeline and database.

### Tasks

#### Report Ingestion
- [ ] `POST /api/reports` — accept report, run pipeline, save results, return analysis
- [ ] `GET /api/reports` — list all reports (paginated)
- [ ] `GET /api/reports/{id}` — get single report with analysis

#### HSE Review
- [ ] `GET /api/reviews` — list pending reviews (priority_band >= HIGH first)
- [ ] `GET /api/reviews/{id}` — single review detail
- [ ] `PATCH /api/reviews/{id}` — HSE officer decision (confirm/reject/correct)

#### Dashboard
- [ ] `GET /api/dashboard/summary` — total reports, SIF count, band breakdown
- [ ] `GET /api/dashboard/trends` — report counts grouped by day/week
- [ ] `GET /api/dashboard/top-hazards` — most frequent hazard types

#### Similarity
- [ ] `GET /api/reports/{id}/similar` — top-k similar past reports

#### Auth (simple JWT)
- [ ] `POST /api/auth/login` — returns JWT
- [ ] Dependency injection: `get_current_user` for protected routes

#### API Documentation
- [ ] All routes fully documented with Pydantic schemas
- [ ] FastAPI auto-generates OpenAPI docs at `/docs`

### Deliverables
- All endpoints return correct responses
- pytest-based API integration tests pass (using `httpx` TestClient)
- `/docs` UI works and is demonstrable to judges

---

## Phase 4 — React Frontend
**Goal:** Complete, interactive UI for report submission, review, and analytics.

### Tasks

#### Layout & Navigation
- [ ] Top navigation: Submit Report | Review Queue | Analytics
- [ ] Responsive layout with Vanilla CSS
- [ ] Dark/light mode toggle

#### Page 1: Report Submission (`/submit`)
- [ ] Form fields: Report Type, Description (textarea), Location, Date, Severity (self-rated)
- [ ] Submit button → calls `POST /api/reports`
- [ ] Loading spinner during AI analysis
- [ ] On success: redirect to review result for that report

#### Page 2: HSE Review Queue (`/queue`)
- [ ] Table of pending reports
- [ ] Columns: ID, Date, Type, Priority Band (color-coded), Status
- [ ] Filter by band, type, date range
- [ ] Click row → navigate to ReviewDetail

#### Page 3: Review Detail (`/reviews/:id`)
- [ ] Report text with entity highlights (color-coded spans per entity type)
- [ ] SIF classification result + confidence badge
- [ ] Priority score bar (0–1)
- [ ] Priority band badge (LOW / MEDIUM / HIGH / CRITICAL — color-coded)
- [ ] Explanation panel: deterministic evidence factors, fired rules listed
- [ ] Similar reports panel: up to 5 similar past reports with similarity score
- [ ] Decision panel: Confirm / Reject / Correct (with correction dropdown and notes)
- [ ] Submit decision → PATCH /api/reviews/{id}

#### Page 4: Analytics Dashboard (`/analytics`)
- [ ] Summary cards: Total Reports, SIF-Flagged, Pending Review, Avg Priority Score
- [ ] Line chart: Reports over time (Recharts)
- [ ] Bar chart: Band breakdown
- [ ] Donut chart: Report types
- [ ] Table: Top hazard categories

### Deliverables
- All 4 pages functional and connected to backend
- Entity highlighting working
- Explanation panel renders evidence attribution and rules
- HSE officer can complete a full review workflow

---

## Phase 5 — Integration, Testing & Polish
**Goal:** End-to-end workflow tested, bugs fixed, demo-ready.

### Tasks
- [ ] End-to-end integration test: submit report → see result → HSE review → confirm → appears in dashboard
- [ ] Improve synthetic dataset: 50–100 labeled examples for better classifier demo
- [ ] Rebuild NumPy embeddings with larger dataset
- [ ] Error handling: API returns proper HTTP codes and messages
- [ ] Frontend error states: network error, empty states, loading skeletons
- [ ] Run full `pytest` suite — all tests must pass
- [ ] Performance check: pipeline latency on target machine (note actual ms)
- [ ] Write `README.md` setup and run instructions
- [ ] Demo run-through: simulate a live HSE workflow for judges

### Deliverables
- All automated tests pass
- Complete demo workflow runnable in under 5 minutes
- `README.md` with clear setup instructions
- No placeholder data — all examples are synthetic but meaningful

---

## Phase 6 — Evaluation & Metrics (Honest)
**Goal:** Produce real, measured performance numbers from actual experiments.

> **RULE: Never invent accuracy numbers. All metrics come from real evaluation.**

### Tasks
- [ ] Create evaluation dataset: minimum 50 labeled examples (held-out test set)
- [ ] Evaluate SIF Classifier: Precision, Recall, F1, ROC-AUC
- [ ] Evaluate Rule Engine: True Positive Rate on known SIF-type scenarios
- [ ] Evaluate Scorer: Rank correlation between AI priority and HSE officer priority
- [ ] Evaluate Similarity Engine: qualitative review of top-k results
- [ ] Document all results in `notebooks/03_evaluation.ipynb`
- [ ] Add honest caveats:
  - Dataset is small and synthetic
  - Real-world performance would require OIL's actual historical data
  - SIF Sentinel identifies potential SIF precursor signals and prioritizes safety reports. It does not predict accidents. AI outputs remain subject to HSE validation.

### Deliverables
- `notebooks/03_evaluation.ipynb` with real metrics
- Metrics summary in `README.md`
- Known limitations documented

---

## Development Timeline (Estimated)

| Phase | Description | Estimated Duration |
|---|---|---|
| Phase 0 | Bootstrap | 0.5 day |
| Phase 1 | Database Schema | 1 day |
| Phase 2 | NLP Pipeline | 3–4 days |
| Phase 3 | FastAPI Backend | 2 days |
| Phase 4 | React Frontend | 2–3 days |
| Phase 5 | Integration & Polish | 1–2 days |
| Phase 6 | Evaluation | 1 day |
| **Total** | | **~10–12 days** |

---

## Definition of Done (per phase)

A phase is complete when:
1. All tasks in the phase checklist are checked off
2. All automated tests pass (`pytest` / Vitest)
3. A team member other than the implementer can run it locally

---

## Team Roles (suggested)

| Role | Responsibilities |
|---|---|
| Backend Lead | FastAPI, database, pipeline orchestration |
| AI/ML Lead | DistilBERT training, deterministic attribution, rule engine, NumPy similarity |
| Frontend Lead | React pages, Vanilla CSS, Recharts, API integration |
| QA / DevOps | pytest, seed data, docker-compose, README |

---

*Last updated: September 2026 | Team 6Bits | SIH26165*
