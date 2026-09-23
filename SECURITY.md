# SIF Sentinel — Security Review & Architecture Guide (SECURITY.md)

> [!WARNING]
> **Prototype Security Notice**: SIF Sentinel is currently an advanced functional prototype designed for local development, evaluation, and research demonstration. **It is NOT claimed to be production-secure in its current state.** Prior to deploying this system in live industrial, energy, or mission-critical enterprise environments, the limitations documented below must be remediated according to the production hardening roadmap.

---

## 1. Executive Summary

This security review evaluates the **SIF Sentinel** decision engine, backend API (FastAPI), database layer (SQLAlchemy / SQLite / PostgreSQL), and frontend client (React / Vite). 

The prototype exhibits **strong defensive foundations** in API schema validation, parameterized ORM queries, environment variable decoupling, and deterministic explainability. However, as an MVP prototype, it lacks transport-layer authentication, role-based authorization, cryptographic password hashing, and automated PII anonymization.

---

## 2. Detailed Dimension-by-Dimension Audit

### 2.1 Secrets in Source Code
- **Current Protections**:
  - No production credentials, database passwords, API tokens, cloud access keys (AWS/GCP/Azure), or private keys are hardcoded in the codebase or git history.
  - `.env.example` provides template placeholders only (`your-secret-key-here`, `postgresql+asyncpg://user:password@localhost:5432/sif_sentinel`).
  - `.gitignore` explicitly excludes `.env`, credential files, and binary artifacts.
- **Current Limitations**:
  - Initial seed script (`backend/app/db/seed.py`) contains illustrative default credentials for local development mock users (`AdminPass2026!`, `HseReview2026!`).
- **Production Recommendations**:
  - Integrate secret scanning into CI/CD pipelines (e.g., Gitleaks, TruffleHog, GitHub Secret Scanning).
  - Externalize production secrets using a cloud secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault, Azure Key Vault) rather than static files on disk.

### 2.2 Environment Variables & Configuration
- **Current Protections**:
  - Configuration is centrally managed via Pydantic `BaseSettings` (`backend/app/core/config.py`).
  - Sensitive parameters (such as `DATABASE_URL`) load dynamically from system environment variables or local `.env` files.
- **Current Limitations**:
  - `ALLOWED_ORIGINS` is statically declared as a Python list with a fallback rather than parsed strictly from an environment variable list.
- **Production Recommendations**:
  - Require strict environment validation: fail fast on startup if required production environment variables (e.g., `DATABASE_URL`, `JWT_SECRET_KEY`) are missing or set to insecure defaults.
  - Separate configuration profiles strictly across `development`, `testing`, `staging`, and `production`.

### 2.3 SQL Injection Risks
- **Current Protections**:
  - All database queries and write operations in `DatabaseService` (`backend/app/services/db_service.py`) exclusively utilize the **SQLAlchemy 2.0 ORM** query API.
  - Zero raw SQL queries (`text()`), zero unparameterized SQL strings, and zero string concatenations or format strings (`f"SELECT..."`) exist in application code.
  - All queries utilize bound parameters, eliminating classical SQL injection vulnerabilities across report search, review recording, and audit trail operations.
- **Current Limitations**:
  - Dynamic sorting or complex ad-hoc filtering is currently constrained to predefined ORM filters.
- **Production Recommendations**:
  - Maintain the strict ban on raw SQL string concatenation.
  - Apply the principle of least privilege to database users (e.g., grant only `SELECT`, `INSERT`, `UPDATE` to the API application role; reserve `DROP`, `ALTER`, and schema modifications for migration service accounts).

### 2.4 API Validation & Input Boundaries
- **Current Protections**:
  - All v1 endpoints (`backend/app/api/v1/api.py`) strictly enforce Pydantic v2 schemas (`backend/app/schemas/api_v1.py`).
  - String length bounds are enforced: `report_text` (`min_length=10`, `max_length=10000`), `report_id` (`max_length=50`), `comments` (`max_length=2000`).
  - Numeric ranges are constrained: `recurring_risk_signal` (`ge=0.0`, `le=1.0`), pagination query parameters (`limit: ge=1, le=200`, `offset: ge=0`).
  - Categorical inputs are regex-enforced: `decision` matches `^(confirmed|rejected|corrected)$`.
  - Priority levels use typed enumerations (`PriorityLevel.HIGH`, `MEDIUM`, `LOW`).
  - Invalid requests are rejected with structured `422 Unprocessable Entity` responses detailing field-level violations.
- **Current Limitations**:
  - No request rate limiting (throttling) or request body size limits enforced at the reverse proxy layer.
- **Production Recommendations**:
  - Deploy an API gateway or reverse proxy (e.g., NGINX, Cloudflare, AWS API Gateway) with rate limiting (e.g., 60 requests/minute per IP/token) to mitigate denial-of-service (DoS) and automated scraping.

### 2.5 Unsafe File Handling & Deserialization
- **Current Protections**:
  - The API does not expose any direct file upload, file modification, or arbitrary file read endpoints.
  - Configuration files (`decision_config.yaml`) are parsed using `yaml.safe_load()`, preventing YAML object deserialization code execution.
  - Machine learning models are loaded from fixed internal directory paths (`models/distilbert/best_checkpoint` and `models/baseline/baseline_pipeline.joblib`) without user-controlled path parameters.
- **Current Limitations**:
  - The baseline fallback model uses `joblib.load()` (Python pickle under the hood). While safe in controlled local prototypes, pickle/joblib deserialization is inherently vulnerable to arbitrary code execution if an untrusted file is substituted on the filesystem.
- **Production Recommendations**:
  - Verify cryptographic hashes (SHA-256) of all model checkpoints before loading into memory.
  - Store production models in read-only mounts with strict filesystem permissions.
  - Transition machine learning artifacts to safer serialization formats such as **Safetensors** or **ONNX** runtime.

### 2.6 Authentication Readiness
- **Current Protections**:
  - Relational schema for user identity (`User` model in `backend/app/db/models.py`) already exists with `id`, `username`, `email`, `hashed_password`, `role`, and `is_active`.
- **Current Limitations**:
  - **No authentication is currently enforced at the HTTP layer.** All endpoints (`/api/v1/analyze-report`, `/api/v1/reports`, `/api/v1/hse-review`, `/api/v1/alerts/{id}/acknowledge`) are publicly reachable on the network without credentials.
  - Any caller can submit analyses, inspect proprietary safety reports, or trigger reviews.
- **Production Recommendations**:
  - Implement enterprise identity integration: OAuth2 with JWT Bearer tokens, OIDC (OpenID Connect), or corporate SSO (SAML 2.0 / Azure AD / Okta).
  - Protect all `/api/v1/*` endpoints behind FastAPI security dependencies (`Security(get_current_active_user)`).

### 2.7 Authorization & Access Control
- **Current Protections**:
  - Database schema models support user roles (`admin`, `hse_officer`, `supervisor`).
- **Current Limitations**:
  - No Role-Based Access Control (RBAC) is enforced by API route decorators.
  - Callers can submit any arbitrary `reviewer_id` in `POST /api/v1/hse-review` without verification of the caller's identity or role.
  - Safety alerts can be acknowledged by any unauthenticated requester.
- **Production Recommendations**:
  - Enforce role-based access decorators:
    - `hse_officer` & `admin`: Authorized for `/api/v1/hse-review`, `/api/v1/alerts/*/acknowledge`.
    - `supervisor` & `operator`: Authorized for `/api/v1/analyze-report` (report submission).
    - `viewer` / `auditor`: Read-only access to `/api/v1/reports`, `/api/v1/dashboard-summary`.
  - Derive `reviewer_id` directly from the authenticated cryptographic token rather than accepting client-supplied JSON values.

### 2.8 Password Handling
- **Current Protections**:
  - User model designates `hashed_password` (not plain text) as the storage column.
- **Current Limitations**:
  - The local database seed script (`backend/app/db/seed.py`) uses single-iteration unsalted `hashlib.sha256(password.encode()).hexdigest()`.
  - Plain SHA-256 lacks cryptographic salting, configurable work factors, and memory-hardness, making it vulnerable to precomputed rainbow tables and GPU-accelerated cracking.
- **Production Recommendations**:
  - Enforce state-of-the-art password hashing algorithms: **Argon2id** (recommended by OWASP) or **bcrypt** (minimum work factor 12) with unique per-user cryptographically random salts.
  - Enforce password complexity rules (minimum 12 characters, entropy checks) and account lockout policies after repeated failed attempts.

### 2.9 Logging of Sensitive Information & PII
- **Current Protections**:
  - HTTP middleware (`log_and_time_requests`) logs only method, path, HTTP status, and duration (ms). It does NOT log headers, cookies, or request payload bodies.
  - API logger records narrative length (`len(payload.report_text)`) rather than dumping full text into operational logs.
- **Current Limitations**:
  - Industrial safety incident reports frequently contain **Personally Identifiable Information (PII)** and Protected Health Information (PHI): injured worker names, supervisor identities, badge numbers, contractor company names, or medical descriptions.
  - Reports are currently persisted and vectorized in raw form without automated PII scrubbing or redaction.
- **Production Recommendations**:
  - Implement an automated PII/PHI redaction pipeline (e.g., Microsoft Presidio, spaCy NER, or regex de-identification) prior to persistent database storage and vector embedding.
  - Ensure application log files are rotated, encrypted at rest, and shipped to centralized security information and event management (SIEM) systems with strict access controls.

### 2.10 Cross-Origin Resource Sharing (CORS)
- **Current Protections**:
  - CORS middleware is enabled with an explicit origin whitelist (`http://localhost:5173`, `http://localhost:3000`) rather than the wildcard `*`.
- **Current Limitations**:
  - `allow_methods=["*"]` and `allow_headers=["*"]` permit all HTTP verbs and headers from the whitelisted origins.
- **Production Recommendations**:
  - Restrict `allow_methods` strictly to `["GET", "POST", "OPTIONS"]`.
  - Restrict `allow_headers` strictly to `["Content-Type", "Authorization", "X-Requested-With"]`.
  - Explicitly define production domain origins via environment variables (disallowing `localhost` in production).

### 2.11 Error Messages & Information Disclosure
- **Current Protections**:
  - Custom exception handlers return standardized, structured JSON envelopes for `HTTPException` and `RequestValidationError`.
  - Handled errors do not expose Python stack traces, internal database schema details, or server directory paths.
- **Current Limitations**:
  - No global unhandled exception handler (`@app.exception_handler(Exception)`) is registered. An unexpected crash could potentially leak tracebacks if debug mode is inadvertently enabled.
- **Production Recommendations**:
  - Implement a catch-all exception handler that logs the stack trace internally with an incident reference ID and returns an opaque error response to the client (`{"error_code": "INTERNAL_SERVER_ERROR", "reference_id": "<UUID>"}`).
  - Ensure FastAPI `debug=False` is enforced in production.

---

## 3. Summary Matrix

| Security Check | Current Status | Prototype Protection Level | Production Action Required |
| :--- | :--- | :--- | :--- |
| **Secrets in Source** | Verified clean | High (clean repo & gitignore) | Continuous CI secret scanning |
| **Environment Variables** | Configured | Moderate (Pydantic BaseSettings) | Require strict env validation on startup |
| **SQL Injection** | Protected | High (100% SQLAlchemy ORM) | Maintain ORM parameterization |
| **API Validation** | Enforced | High (Pydantic schemas & bounds) | Add API gateway rate limiting |
| **Unsafe File Handling** | Controlled | Moderate (No upload endpoints) | Checksum model weights; use Safetensors |
| **Authentication** | Not Enforced | **Low (MVP open access)** | Implement OAuth2 / JWT / SSO |
| **Authorization** | Not Enforced | **Low (No RBAC checks)** | Enforce role-based route guards |
| **Password Handling** | Insecure in seed | **Low (Unsalted SHA-256 demo)** | Migrate to Argon2id / bcrypt |
| **Logging & PII** | Clean logs | Moderate (Raw text in DB) | Automated PII redaction pipeline |
| **CORS** | Whitelisted | Moderate (Localhost whitelisted) | Strict production domain whitelisting |
| **Error Messages** | Structured | Moderate (Structured JSON) | Add global catch-all exception handler |

---

## 4. Production Hardening Checklist

Before moving SIF Sentinel to a production environment:

1. **Identity & Access Management**:
   - [ ] Deploy OAuth2/OIDC provider or corporate Single Sign-On (Azure AD / Okta).
   - [ ] Implement JWT validation middleware on all API routes.
   - [ ] Enforce Role-Based Access Control (RBAC) distinguishing HSE Officers, Site Supervisors, and Read-Only Auditors.
2. **Data Privacy & Governance**:
   - [ ] Add pre-storage PII de-identification to redact names, employee IDs, and medical details from safety narratives.
   - [ ] Enable PostgreSQL Transparent Data Encryption (TDE) or disk-level encryption (LUKS/AWS KMS) for data at rest.
   - [ ] Enforce TLS 1.3 for all data in transit (HTTPS and secure database connections).
3. **ML & Model Security**:
   - [ ] Sign model checkpoints with cryptographic hashes (SHA-256) and verify integrity at startup.
   - [ ] Migrate `joblib`/pickle models to Safetensors or ONNX runtime.
   - [ ] Audit model drift and adversarial safety report inputs designed to deliberately evade precursor detection.
4. **Infrastructure & Network**:
   - [ ] Place backend API behind a reverse proxy / Web Application Firewall (WAF).
   - [ ] Configure strict Content Security Policy (CSP) headers in the frontend.
   - [ ] Implement automated vulnerability scanning for Python dependencies (`pip-audit`, `safety`) and npm packages (`npm audit`).
