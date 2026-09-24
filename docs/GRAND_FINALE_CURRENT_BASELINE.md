# SIF Sentinel — Grand Finale Current Baseline Audit

**Problem Statement:** SIH26165 (SIH 2026)  
**Repository:** Ronak-Kothari007/SIF-Sentinel  
**Audit Date:** 2026-09-23  
**Auditor:** Automated full-codebase inspection (138 files, 92,034 lines)

---

## 1. Current Working Functionality

### 1.1 AI/NLP Pipeline (FULLY FUNCTIONAL — PRESERVE)

| Component | Status | Location | Details |
|---|---|---|---|
| **DistilBERT Classifier** | ✅ Trained & checkpoint saved | `models/distilbert/best_checkpoint/` (267 MB safetensors) | Fine-tuned binary SIF precursor classifier. Lazy-loaded at first inference. |
| **Baseline TF-IDF Classifier** | ✅ Trained & checkpoint saved | `models/baseline/baseline_pipeline.joblib` (54 KB) | Fallback if DistilBERT unavailable. |
| **Hybrid Entity Extractor** | ✅ Production-ready | `backend/app/services/extractor.py` (733 lines) | Deterministic gazetteer + NLP contextual pattern extraction for activity, hazard, barrier, barrier_status, location, equipment. YAML-configurable via `extraction_rules.yaml`. |
| **Deterministic Safety Rule Engine** | ✅ Production-ready | `backend/app/services/rule_engine.py` (357 lines) | 10+ OSHA/SIF precursor rules in `sif_rules.yaml`. Severity 1-4, signal-phrase matching with evidence tracking. |
| **Composite Decision Engine** | ✅ Production-ready | `backend/app/services/decision_engine.py` (702 lines) | Weighted multi-factor scoring: ML probability + rule severity + barrier failure + hazard multiplier + activity multiplier + recurrence. YAML-configurable weights via `decision_config.yaml`. Includes safety escalation policies. |
| **Semantic Embedding Service** | ✅ Production-ready | `backend/app/services/embedding_service.py` (214 lines) | `all-MiniLM-L6-v2` Sentence Transformers (384-dim). 3-tier fallback: SentenceTransformer → HF AutoModel → deterministic hash projection. |
| **Recurring Risk / Similarity Engine** | ✅ Production-ready | `backend/app/services/similarity_engine.py` (418 lines) | In-memory cosine similarity over dense embeddings. Nearest-neighbor retrieval, recurrence signal computation, semantic clustering. |
| **Structured Explanation Generator** | ✅ Production-ready | Inside `decision_engine.py` | Phase 14 non-contradictory itemized explainability. Consistency validator prevents HIGH/LOW contradictions. |

### 1.2 Backend API (FULLY FUNCTIONAL — PRESERVE)

| Endpoint | Method | Purpose | Status |
|---|---|---|---|
| `/api/v1/analyze-report` | POST | Submit report → full AI+rule pipeline → persist | ✅ Working |
| `/api/v1/reports` | GET | Paginated list with priority/hazard/activity filters | ✅ Working |
| `/api/v1/reports/{id}` | GET | Full decision result + review dual-view | ✅ Working |
| `/api/v1/high-risk` | GET | HIGH-priority review queue | ✅ Working |
| `/api/v1/similar-reports/{id}` | GET | Semantic similar reports via Sentence Transformers | ✅ Working |
| `/api/v1/patterns` | GET | Recurring risk patterns, clusters, trends | ✅ Working |
| `/api/v1/hse-review` | POST | Submit HSE officer confirm/reject/correct | ✅ Working |
| `/api/v1/feedback` | POST/GET | Model annotations & user feedback | ✅ Working |
| `/api/v1/reports/{id}/audit-trail` | GET | Immutable chronological audit log | ✅ Working |
| `/api/v1/dashboard-summary` | GET | Executive dashboard metrics | ✅ Working |
| `/api/v1/alerts` | GET | Internal precursor safety alerts | ✅ Working |
| `/api/v1/alerts/{id}/acknowledge` | POST | Officer acknowledge alert | ✅ Working |
| `/api/v1/workflow/status/{id}` | GET | Automated workflow lifecycle status | ✅ Working |
| `/api/v1/demo/status` | GET | Demo dataset loaded status | ✅ Working |
| `/api/v1/demo/load` | POST | One-click load 10 demo scenarios through live pipeline | ✅ Working |
| `/api/v1/demo/reset` | POST | Purge demo records from memory + DB | ✅ Working |
| `/reports/test` | POST | Legacy Phase 1/2 rule-engine-only endpoint | ✅ Legacy (preserved) |
| `/health` | GET | Backend health check | ✅ Working |

### 1.3 Database & Persistence (FUNCTIONAL — PRESERVE)

| Component | Details |
|---|---|
| **ORM** | SQLAlchemy 2.0 with 10 tables (User, Report, Prediction, Entity, TriggeredRule, HSEReview, Feedback, RiskPattern, AuditLog, AlertEvent) |
| **Migration** | Alembic configured, initial migration present |
| **Default DB** | SQLite (`sif_sentinel.db`) for dev/demo, PostgreSQL-ready via `DATABASE_URL` env var |
| **Dual Persistence** | In-memory `ReportRepository` (fast) + SQLAlchemy DB (durable). Both written to on every operation. |

### 1.4 Automated HSE Workflow (FUNCTIONAL — PRESERVE)

| Feature | Details |
|---|---|
| **Auto-Escalation** | HIGH priority → 5-step sequence: save → mark HIGH → enter review queue → create alert → audit log |
| **Workflow States** | `HSE_REVIEW_REQUIRED`, `ROUTINE_MONITORING`, `CONTROLLED`, `REVIEWED_CONFIRMED`, `REVIEWED_CORRECTED`, `REVIEWED_REJECTED` |
| **Alert System** | Internal AlertItem model with acknowledge flow |
| **Review Resolution** | Officer confirm/reject/correct transitions workflow state and resolves alerts |

### 1.5 Demo Mode (FUNCTIONAL — PRESERVE)

- 10 curated synthetic scenarios spanning: energy isolation, confined space, work at height, hot work, line of fire, routine housekeeping, ergonomics, near-miss, ambiguous case, recurring pattern
- All processed through the LIVE AI pipeline (not mocked)
- Pre-staged HSE reviews for demonstration
- One-click load/reset via API

---

## 2. Current Frontend Routes/Pages

| Tab/Route | Component | Size | Description |
|---|---|---|---|
| `dashboard` | `DashboardPage.jsx` | 758 lines / 36 KB | Executive KPI cards, priority distribution, trend chart (computed from live data), recent high-risk queue, active alerts panel with acknowledge, top hazards/activities breakdown |
| `reports` | `ReportsPage.jsx` | 290 lines / 10 KB | Paginated reports table with priority/hazard filters, client-side text search, sortable columns |
| `details` | `ReportDetailsPage.jsx` | 1,010 lines / 46 KB | Full AI decision display, structured explanation, factor scores, triggered rules, similar reports panel, HSE review form (confirm/reject/correct with multi-field correction), audit trail timeline, feedback submission |
| `patterns` | `RiskPatternsPage.jsx` | 312 lines / 14 KB | Semantic recurring patterns, barrier gap analysis, temporal trends, cluster visualization |
| `review` | `HSEReviewPage.jsx` | 496 lines / 22 KB | Review queue filtered by status (pending/confirmed/corrected/rejected/all), inline quick-review form with correction fields |

### Frontend Components

| Component | Size | Purpose |
|---|---|---|
| `Navbar.jsx` | 182 lines | Navigation header with tabs, demo load button, judge demo toggle, health indicator, analyze button |
| `AnalyzeModal.jsx` | 424 lines | Full-screen modal for submitting new reports. 4 preset examples. Shows live analysis results with priority badge, triggered rules, explanation. "Proceed to Review" flow. |
| `JudgeDemoGuide.jsx` | 13.7 KB | 5-minute SIH judge demonstration stepper guide with 13+ steps |

### Frontend Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| React | 18.3.1 | UI framework |
| Vite | 6.0.3 | Build tool & dev server |
| lucide-react | 0.468.0 | Icon library |
| Vanilla CSS | — | Custom design system (861 lines, industrial HSE palette, no Tailwind) |

### Frontend ↔ Backend Integration

- **API client:** `frontend/src/services/api.js` — 15 functions calling all `/api/v1/*` endpoints
- **Proxy:** Vite dev server proxies `/api` → `http://127.0.0.1:8000`
- **No mock data anywhere** — all dashboard metrics, reports, patterns, alerts come from live FastAPI
- **No React Router** — uses `currentTab` state-based navigation (custom SPA routing)

---

## 3. Current Backend APIs (Summary)

Total production endpoints: **17** (plus 1 legacy)

**API Architecture:**
- `app/api/v1/api.py` — Main v1 router (608 lines, 13 endpoints)
- `app/api/v1/demo.py` — Demo mode router (337 lines, 3 endpoints)
- `app/api/routes/reports.py` — Legacy Phase 1/2 router (1 endpoint)
- `app/api/routes/health.py` — Health check (1 endpoint)

**Middleware:** CORS (Vite origins), request timing/logging, structured error handlers (HTTP 4xx, validation 422)

**Schemas:**
- `schemas/api_v1.py` — 433 lines, 20+ Pydantic models for requests/responses
- `schemas/decision.py` — 192 lines, `DecisionResult`, `FactorScores`, `StructuredExplanation`, `PriorityLevel`
- `schemas/context.py` — Safety context and entity extraction schemas
- `schemas/report.py` — Legacy Phase 1/2 schemas
- `schemas/health.py` — Health check schema

---

## 4. Current AI/NLP Components

### 4.1 Model Pipeline

```
Report Text
    │
    ├─→ [1] HybridSafetyExtractor (extractor.py)
    │       ├── DeterministicExtractor (gazetteer matching)
    │       └── NLPExtractor (contextual patterns + negation)
    │       → SafetyContext: activity, hazard, barrier, barrier_status, location, equipment
    │
    ├─→ [2] SIFRuleEngine (rule_engine.py)
    │       → RuleEngineResult: matched_rules[], severity, sif_flag, evidence
    │
    ├─→ [3] DistilBERTPredictor OR BaselinePredictor
    │       → sif_probability: float [0.0, 1.0]
    │
    ├─→ [4] RecurringRiskEngine (similarity_engine.py)
    │       → recurrence_signal: float [0.0, 1.0]
    │
    └─→ [5] SIFDecisionEngine (decision_engine.py)
            → DecisionResult: priority, score, explanation, triggered_rules, evidence, factor_scores
```

### 4.2 Configuration Files

| File | Purpose |
|---|---|
| `backend/app/rules/sif_rules.yaml` | 10+ deterministic SIF precursor rules (energy isolation, confined space, height, hot work, line of fire, etc.) |
| `backend/app/rules/extraction_rules.yaml` | Entity extraction gazetteers (activities, hazards, barriers, locations, equipment, status modifiers) |
| `backend/app/rules/decision_config.yaml` | Scoring weights, hazard/activity multipliers, barrier scores, priority thresholds, escalation policies |

### 4.3 Training Infrastructure

| File | Purpose |
|---|---|
| `models/train_distilbert.py` | DistilBERT fine-tuning (20 KB) |
| `models/train_baseline.py` | TF-IDF + Logistic Regression baseline (10 KB) |
| `models/compare_models.py` | Model comparison report |
| `models/distilbert_data.py` | Data loading and preprocessing |
| `dataset/` | Synthetic dataset with train/val/test splits |

---

## 5. Current Database/Persistence Behavior

### 5.1 Dual-Layer Architecture

1. **In-Memory Repository** (`report_store.py`, `ReportRepository` class)
   - Thread-safe `dict[str, StoredReport]` keyed by `report_id`
   - Fast read/write for all API operations
   - Pre-seeds from CSV on startup (synthetic dataset)
   - Similarity engine vectors stored in memory
   - Alerts stored in memory as `dict[str, AlertItem]`
   - **Volatile** — data lost on server restart

2. **SQLAlchemy Database** (`db_service.py`, `DatabaseService` class)
   - 10 normalized tables
   - Written to as a secondary persistence layer (wrapped in try/except)
   - SQLite default (file-based), PostgreSQL-ready
   - Alembic migration for schema versioning

### 5.2 Key Observation

The in-memory repo is the **primary data source** for all API reads. The SQL DB is written to but **not consistently read from** by the API layer. This means:
- After a server restart, the SQL DB has data but the API shows empty state until demo is reloaded
- The dual-write approach works for the demo/prototype but introduces inconsistency risk

---

## 6. Existing Components That Should Be PRESERVED

> **CRITICAL: These are the working AI/backend core. Do NOT rebuild these.**

| Component | Why Preserve |
|---|---|
| `services/decision_engine.py` | Central synthesis engine — proven, tested, transparent |
| `services/extractor.py` | Hybrid entity extraction — gazetteer + NLP patterns |
| `services/rule_engine.py` | Deterministic safety rules — OSHA-referenced, explainable |
| `services/similarity_engine.py` | Semantic similarity — Sentence Transformers integration |
| `services/embedding_service.py` | 3-tier embedding fallback chain |
| `services/workflow_service.py` | Automated HSE escalation workflow |
| `services/report_store.py` | In-memory repository with full CRUD + analytics |
| `services/db_service.py` | SQLAlchemy persistence layer |
| `api/v1/api.py` | All 13 production API endpoints |
| `api/v1/demo.py` | Demo mode (10 scenarios through live pipeline) |
| `schemas/decision.py` | DecisionResult schema — consumed by frontend |
| `schemas/api_v1.py` | All API request/response contracts |
| `rules/*.yaml` | All 3 YAML configuration files |
| `models/predict_distilbert.py` | DistilBERT inference service |
| `models/predict_baseline.py` | Baseline inference service |
| `models/distilbert/best_checkpoint/` | Trained DistilBERT weights (267 MB) |
| `models/baseline/baseline_pipeline.joblib` | Trained baseline pipeline |
| `db/models.py` | All 10 SQLAlchemy table definitions |
| `db/session.py` | Engine/session configuration |
| `demo/scenarios.py` | 10 curated demo scenarios |
| All 13 backend test files | Test coverage for every service |

---

## 7. Existing Components That Need UX Redesign

> **These components WORK functionally but need visual/UX overhaul for Grand Finale.**

### 7.1 Frontend — Complete UX Redesign Required

| Component | Current State | Redesign Need |
|---|---|---|
| **DashboardPage** | Functional but generic card layout, no data viz charts, CSS-only bar approximations | Needs professional data visualization (Chart.js/Recharts), real-time feel, animated KPI tiles, risk heatmap, geographic view |
| **ReportsPage** | Basic table with text search | Needs advanced data grid, pagination controls, bulk actions, column sorting, export capability |
| **ReportDetailsPage** | Largest page (1,010 lines), functional but monolithic | Needs tabbed layout, visual factor score radar/gauge chart, side-by-side AI vs. HSE dual view, timeline visualization |
| **HSEReviewPage** | Functional inline review | Needs dedicated review workbench UX, split-pane layout, keyboard shortcuts for rapid triage |
| **RiskPatternsPage** | Text-based pattern display | Needs network graph visualization, interactive cluster exploration, trend charts |
| **Navbar** | Functional but plain | Needs professional header with user profile, notification bell with dropdown, breadcrumbs |
| **AnalyzeModal** | Functional full-screen modal | Needs step-by-step wizard UX, drag-and-drop file upload, real-time analysis progress indicator |
| **CSS Design System** | 861-line vanilla CSS, industrial palette (good foundation) | Needs responsive breakpoints, dark mode toggle, micro-animations, glassmorphism accents, typography upgrade |
| **SPA Routing** | State-based `currentTab` switching | Needs React Router for URL-based navigation, browser back/forward support, deep linking |
| **State Management** | Props drilling through App.jsx | Consider lightweight context or Zustand for shared state |

### 7.2 Missing Frontend Features for Grand Finale

| Feature | Priority | Notes |
|---|---|---|
| **React Router** | HIGH | URL-based routing, deep links to reports/reviews |
| **Chart Library** | HIGH | Recharts or Chart.js for dashboard visualizations |
| **Responsive Design** | HIGH | Mobile/tablet breakpoints |
| **Loading Skeletons** | MEDIUM | Professional loading states instead of spinner |
| **Toast/Notification System** | MEDIUM | Replace basic toast with a proper notification center |
| **Dark Mode** | MEDIUM | Toggle with CSS variables already in place |
| **PDF/CSV Export** | MEDIUM | Export report analysis or dashboard data |
| **Real-time Updates** | LOW | WebSocket or SSE for live dashboard refresh |
| **Authentication UI** | LOW | Login page (backend User model exists but no auth flow) |

---

## 8. Existing Mock/Demo-Only Functionality

| Component | Type | Details |
|---|---|---|
| **Demo Mode** (`demo.py`, `scenarios.py`) | ✅ NOT mocked — uses LIVE pipeline | All 10 scenarios run through real DistilBERT, rule engine, extractor, similarity engine. Pre-staged reviews are real HSE review operations. |
| **Legacy `/reports/test`** | ⚠️ Partial — placeholder model confidence | Uses real rule engine but `model_confidence = 0.30` is hardcoded placeholder. Not used by current frontend. |
| **In-memory pre-seeding** | ⚠️ Volatile | `report_store.py` pre-seeds from CSV on startup but this data is lost on restart. |
| **User authentication** | ❌ Not implemented | `User` table exists in DB models but no auth middleware, login endpoint, or JWT/session handling. `reviewer_id` is a free-text string. |
| **Email/SMS notifications** | ❌ Not implemented | Alerts are stored internally but no external notification delivery. |
| **File upload** | ❌ Not implemented | Only accepts text input, no document/PDF/image upload. |

---

## 9. Technical Risks That Must NOT Be Worsened

### 🔴 Critical Risks

1. **DO NOT replace the Decision Engine pipeline.** The 5-stage pipeline (extract → rules → ML → similarity → synthesize) is the core IP. Redesigning the frontend must NOT disconnect from these real endpoints.

2. **DO NOT introduce fake/hardcoded data in the frontend.** Every metric, chart, and table MUST come from the live `/api/v1/*` endpoints. The current codebase has zero mocked frontend data — this must remain true.

3. **DO NOT break the `DecisionResult` schema contract.** All 40+ fields in `DecisionResult` are consumed by `ReportDetailsPage.jsx`. Any schema changes require coordinated frontend updates.

4. **DO NOT remove or bypass the explanation consistency validator.** `_validate_explanation_consistency()` in `decision_engine.py` prevents contradictory AI explanations. This is a competitive differentiator.

### 🟡 Moderate Risks

5. **In-memory state loss on restart.** The `ReportRepository` is the primary data store but is volatile. For Grand Finale, consider making the SQL DB the primary read source, or implementing startup rehydration from SQL.

6. **Large model binary in git.** `model.safetensors` (267 MB) is tracked by git. Should use Git LFS or `.gitignore` for production.

7. **No authentication.** `reviewer_id` is a free-text input. For Grand Finale demo, at minimum implement role-based badge display (no need for full auth).

8. **`sentence-transformers` and `torch` not in requirements.txt.** These are imported at runtime with try/except fallbacks but aren't declared dependencies. Should be added or documented.

### 🟢 Low Risks

9. **Legacy `/reports/test` endpoint.** Still mounted but unused by frontend. Can be deprecated but should not be removed (test coverage depends on it).

10. **SQLite for demo.** Adequate for Grand Finale demonstration. PostgreSQL path is already configured if needed.

---

## 10. Recommended Migration Sequence

### Phase 1: Foundation (No Backend Changes)
1. Install React Router (`react-router-dom`)
2. Install chart library (Recharts recommended — React-native, lightweight)
3. Refactor `App.jsx` to use React Router with URL paths
4. Set up shared state context (dashboard counts, auth mock, theme)
5. Implement responsive CSS grid system and dark mode toggle

### Phase 2: Dashboard Redesign
1. Replace DashboardPage with professional data-viz dashboard
2. Real KPI tiles with animated counters
3. Recharts bar/line charts for priority distribution and trends
4. Interactive alerts panel with notification badge
5. Quick-action cards linking to review queue and analyze

### Phase 3: Reports & Details Overhaul
1. Advanced reports table with proper pagination, column sorting, export
2. Tabbed ReportDetailsPage: Summary | AI Analysis | Review | Audit Trail | Similar
3. Visual factor score breakdown (radar chart or horizontal gauge bars)
4. Side-by-side AI vs. HSE officer dual-view panel
5. Timeline visualization for audit trail

### Phase 4: Review Workbench
1. Professional split-pane review interface
2. Keyboard shortcuts for rapid triage (C = confirm, R = reject, E = edit)
3. Batch review capability
4. Review statistics dashboard

### Phase 5: Risk Intelligence
1. Interactive pattern visualization (network graph or force-directed)
2. Trend analysis charts with time-series data
3. Barrier gap analysis heatmap
4. Drill-down from patterns to individual reports

### Phase 6: Polish & Demo Flow
1. Onboarding/landing page with SIH26165 context
2. Guided 5-minute judge demo flow (upgrade existing JudgeDemoGuide)
3. PDF export of analysis reports
4. Micro-animations, transitions, loading skeletons
5. Final responsive pass (mobile/tablet)

---

## Appendix: Files Inspected

### Backend (48 source files)
- `backend/app/main.py` — FastAPI app factory, middleware, error handlers
- `backend/app/api/v1/api.py` — 13 production API endpoints
- `backend/app/api/v1/demo.py` — 3 demo mode endpoints
- `backend/app/api/routes/reports.py` — Legacy Phase 1/2 endpoint
- `backend/app/api/routes/health.py` — Health check
- `backend/app/core/config.py` — Pydantic settings
- `backend/app/db/models.py` — 10 SQLAlchemy table models
- `backend/app/db/session.py` — Engine, session, Base
- `backend/app/db/seed.py` — (referenced, not inspected in detail)
- `backend/app/demo/scenarios.py` — 10 curated demo scenarios
- `backend/app/schemas/api_v1.py` — 20+ API Pydantic schemas
- `backend/app/schemas/decision.py` — DecisionResult, FactorScores, StructuredExplanation
- `backend/app/schemas/context.py` — Safety context schemas
- `backend/app/schemas/report.py` — Legacy schemas
- `backend/app/schemas/health.py` — Health schema
- `backend/app/services/decision_engine.py` — Composite decision engine (702 lines)
- `backend/app/services/extractor.py` — Hybrid entity extractor (733 lines)
- `backend/app/services/rule_engine.py` — Deterministic rule engine (357 lines)
- `backend/app/services/similarity_engine.py` — Semantic similarity engine (418 lines)
- `backend/app/services/embedding_service.py` — Sentence Transformer embeddings (214 lines)
- `backend/app/services/report_store.py` — In-memory report repository (682 lines)
- `backend/app/services/workflow_service.py` — Automated HSE workflow (296 lines)
- `backend/app/services/db_service.py` — Database persistence service (434 lines)
- `backend/app/rules/sif_rules.yaml` — SIF precursor rules
- `backend/app/rules/extraction_rules.yaml` — Entity extraction config
- `backend/app/rules/decision_config.yaml` — Decision scoring weights
- `backend/requirements.txt` — Python dependencies
- `backend/alembic/` — Migration configuration
- `backend/tests/` — 13 test files (rule engine, API, decision engine, HITL, e2e, etc.)

### Frontend (14 source files)
- `frontend/package.json` — Dependencies (React 18, Vite 6, lucide-react)
- `frontend/vite.config.js` — Vite config with API proxy
- `frontend/src/App.jsx` — Root component with tab navigation
- `frontend/src/main.jsx` — React entry point
- `frontend/src/index.css` — 861-line design system
- `frontend/src/services/api.js` — 15 API client functions
- `frontend/src/components/Navbar.jsx` — Navigation header
- `frontend/src/components/AnalyzeModal.jsx` — Report submission modal
- `frontend/src/components/JudgeDemoGuide.jsx` — Judge demo stepper
- `frontend/src/pages/DashboardPage.jsx` — Executive dashboard
- `frontend/src/pages/ReportsPage.jsx` — Reports list
- `frontend/src/pages/ReportDetailsPage.jsx` — Report details + review
- `frontend/src/pages/HSEReviewPage.jsx` — Review queue
- `frontend/src/pages/RiskPatternsPage.jsx` — Risk patterns

### Models (11 source files + checkpoints)
- `models/predict_distilbert.py`, `models/predict_baseline.py`
- `models/train_distilbert.py`, `models/train_baseline.py`
- `models/compare_models.py`, `models/distilbert_data.py`
- `models/entity_extractor.py`, `models/decision_engine.py`
- `models/distilbert/best_checkpoint/` — DistilBERT weights (267 MB)
- `models/baseline/` — Baseline pipeline + metrics

### Dataset (4 source files + data)
- `dataset/schema.py`, `dataset/split_dataset.py`, `dataset/validate_dataset.py`
- `dataset/processed/` — train/val/test splits
- `dataset/raw/` — Original synthetic CSV

### Documentation (7 files)
- `README.md`, `ARCHITECTURE.md`, `DEVELOPMENT_PLAN.md`, `SECURITY.md`, `AI_RULES.md`
- `docs/AI_EXPLANATION.md`, `docs/TECHNICAL_AUDIT.md`, `docs/JURY_PREPARATION.md`
- `docs/FINAL_VALIDATION.md`, `docs/SIF_SENTINEL_DOSSIER.pdf`
