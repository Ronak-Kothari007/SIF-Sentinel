# SIF Sentinel

**AI/NLP Engine to Detect Serious Injury & Fatality (SIF) Precursors in Safety Reports**

**Team:** 6Bits | **Problem Statement ID:** SIH26165 | **SIH 2026**

---

## What is SIF Sentinel?

SIF Sentinel is an AI-assisted safety intelligence platform for Oil India Limited (OIL).
It analyzes Unsafe-Act / Unsafe-Condition and Near-Miss safety reports using Natural Language Processing,
identifies potential Serious Injury & Fatality (SIF) precursor signals,
and routes high-priority reports to Human Safety Expert (HSE) officers for review.

> **AI assists. HSE validates. Safety decisions are always human-in-the-loop.**

---

## Key Features

| Feature | Description |
|---|---|
| **Report Submission** | Web form for submitting UA/UC and near-miss reports |
| **NLP Entity Extraction** | Automatically identifies Activity, Hazard, Location, Barrier, Equipment |
| **SIF Classification** | DistilBERT model flags potential SIF precursors |
| **Safety Rule Engine** | Deterministic rules encode domain-specific SIF triggers |
| **Priority Scoring** | Composite score combining AI + rules → LOW / MEDIUM / HIGH / CRITICAL |
| **Explainability** | Deterministic multi-factor evidence attribution + fired rules — HSE officers see exactly why |
| **Similar Reports** | Sentence Transformers + NumPy vector similarity surfaces recurring risk patterns |
| **HSE Review Workflow** | Officers confirm, reject, or correct every AI result |
| **Feedback Loop** | All HSE decisions stored for future model retraining |
| **Analytics Dashboard** | Trends, hazard frequency, SIF rate over time |

---

## Architecture Summary

```
[Report Form] → [FastAPI Backend] → [NLP Pipeline] → [SQLite]
                                          |
             [Preprocessor] → [Entity Extractor] → [SIF Classifier]
                    → [Rule Engine] → [Scorer] → [Explainer] → [Similarity]
                                          |
                           [HSE Review Queue] → [Dashboard]
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full diagram and component breakdown.

---

## Technology Stack

### Backend
- **Python 3.11+**
- **FastAPI** — REST API
- **SQLAlchemy + Alembic** — ORM and migrations
- **SQLite** — primary database (in-memory caching for similarity)

### AI / NLP
- **Hugging Face Transformers** — DistilBERT for SIF classification
- **Regex/Gazetteers** — entity extraction
- **Sentence Transformers** — semantic similarity
- **NumPy** — in-memory vector similarity search
- **Deterministic Attribution** — explainability
- **scikit-learn** — evaluation metrics
- **PyTorch** — model training

### Frontend
- **React + Vite**
- **Vanilla CSS**
- **Recharts** — analytics visualizations
- **Native Fetch API** — HTTP client

---

## Project Structure

```
SIF-Sentinel/
├── backend/
│   ├── api/           # FastAPI routes and schemas
│   ├── pipeline/      # NLP pipeline stages
│   ├── db/            # SQLAlchemy models, repositories, migrations
│   ├── rules/         # sif_rules.yaml — auditable safety rules
│   ├── models/        # trained model checkpoints
│   ├── tests/         # pytest test suite
│   └── main.py
├── frontend/
│   └── src/           # React components and pages
├── data/
│   ├── raw/           # public / synthetic datasets
│   └── processed/
├── notebooks/         # EDA, training, evaluation
├── scripts/           # seed_db, train_model
├── ARCHITECTURE.md
├── DEVELOPMENT_PLAN.md
└── AI_RULES.md
```

---

## Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### 1. Clone the repository
```bash
git clone https://github.com/your-org/SIF-Sentinel.git
cd SIF-Sentinel
```

### 2. Backend setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env: set DATABASE_URL, SECRET_KEY
```

### 4. Database setup
```bash
# Run migrations
alembic upgrade head

# Seed synthetic/demo data
python scripts/seed_db.py
```

### 5. Start backend
```bash
uvicorn main:app --reload --port 8000
```
API docs available at: `http://localhost:8000/docs`

### 6. Frontend setup
```bash
cd ../frontend
npm install
npm run dev
```
App available at: `http://localhost:5173`

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/reports` | Submit a new safety report |
| GET | `/api/reports` | List all reports |
| GET | `/api/reports/{id}` | Get single report with analysis |
| GET | `/api/reviews` | List pending HSE reviews |
| GET | `/api/reviews/{id}` | Review detail |
| PATCH | `/api/reviews/{id}` | Submit HSE decision |
| GET | `/api/reports/{id}/similar` | Find similar past reports |
| GET | `/api/dashboard/summary` | Dashboard summary stats |
| GET | `/api/dashboard/trends` | Report trends over time |
| POST | `/api/auth/login` | Obtain JWT token |

Full interactive documentation: `http://localhost:8000/docs`

---

## SIF Priority Score

```
priority_score = 0.35 × model_confidence
              + 0.30 × rule_severity_score
              + 0.20 × barrier_gap_score
              + 0.15 × recurrence_score

Bands:
  0.00 – 0.39  →  LOW       (informational)
  0.40 – 0.59  →  MEDIUM    (monitor)
  0.60 – 0.79  →  HIGH      (HSE review required)
  0.80 – 1.00  →  CRITICAL  (immediate escalation)
```

---

## Important Disclaimers

1. **SIF Sentinel identifies potential SIF precursor signals and prioritizes safety reports. It does not predict accidents. AI outputs remain subject to HSE validation.**
2. **Performance metrics are measured on synthetic/demo data. Real-world performance requires validation on actual historical data.**
3. **No real confidential data is used in this prototype.**

---

## Documentation

| Document | Contents |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System architecture, component breakdown, data flow |
| [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) | Phased development plan with tasks and acceptance criteria |
| [AI_RULES.md](./AI_RULES.md) | AI ethics, constraints, data governance, explainability standards |

---

## Team 6Bits

| Role | Responsibility |
|---|---|
| Backend Lead | FastAPI, database, pipeline orchestration |
| AI/ML Lead | DistilBERT training, deterministic attribution, rule engine, vector similarity |
| Frontend Lead | React UI, Vanilla CSS, Recharts |
| QA / DevOps | Testing, seed data, documentation |

---

*Smart India Hackathon 2026 | Problem Statement SIH26165 | Theme: Smart Automation*
