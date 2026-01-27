# CLAUDE.md - Contract Leakage Engine Reference Guide

## Project Overview

**AI Contract & Commercial Leakage Engine** - A comprehensive POC system for detecting commercial leakage risks in contracts using AI-powered analysis.

### What It Does
1. **Ingests** contract documents (PDF, DOCX, DOC, TXT)
2. **Extracts** clauses using NLP (spaCy) + GPT-4.5
3. **Detects** commercial leakage using YAML rules + GPT-5.2 + RAG
4. **Presents** findings in an interactive React frontend
5. **Allows** users to review, accept, reject, and adjust findings
6. **Generates** professional PDF/Excel reports

### Technology Stack

**Backend (Python 3.12.9)**
- Azure Functions v4 (Consumption plan)
- Azure Cosmos DB (NoSQL) - serverless
- Azure Blob Storage
- Azure OpenAI (GPT-5.2 + text-embedding-3-large)
- Azure AI Search (vector search + RAG)
- Azure Document Intelligence (OCR)
- Pydantic 2.6 (data validation)
- spaCy 3.7 (NLP)
- ReportLab + OpenPyXL (reports)

**Frontend (React + TypeScript)**
- React 18 + TypeScript 5.3
- Vite 5 (build tool)
- TailwindCSS 3 (styling)
- TanStack Query (React Query)
- React Router 6
- Axios (HTTP client)
- Lucide React (icons)

---

## Project Structure

```
contract-leakage-engine-backend/
├── api/                              # Azure Functions endpoints (10 endpoints)
│   ├── upload_contract/              # POST /api/upload_contract
│   ├── analyze_contract/             # POST /api/analyze_contract
│   ├── get_analysis/                 # GET /api/get_analysis/{id}
│   ├── list_contracts/               # GET /api/list_contracts
│   ├── dismiss_finding/              # POST /api/dismiss_finding/{id}/{finding_id}
│   ├── export_report/                # GET /api/export_report/{id}
│   ├── create_override/              # POST /api/overrides/{id}
│   ├── get_overrides/                # GET /api/overrides/{id}
│   ├── get_override_summary/         # GET /api/overrides/{id}/summary
│   └── health/                       # GET /api/health
│
├── shared/                           # Shared Python modules
│   ├── models/                       # Pydantic data models
│   │   ├── contract.py               # Contract, ContractMetadata
│   │   ├── clause.py                 # Clause, ExtractedEntities
│   │   ├── finding.py                # LeakageFinding, EstimatedImpact, Assumptions
│   │   ├── session.py                # AnalysisSession
│   │   └── override.py               # UserOverride, OverrideAction, FindingStatus
│   │
│   ├── db/                           # Cosmos DB layer
│   │   ├── cosmos_client.py          # Client wrapper with containers
│   │   └── repositories/             # Data access layer (5 repositories)
│   │       ├── contract_repository.py
│   │       ├── clause_repository.py
│   │       ├── finding_repository.py
│   │       ├── session_repository.py
│   │       └── override_repository.py
│   │
│   ├── services/                     # Business logic (12 services)
│   │   ├── storage_service.py        # Azure Blob Storage operations
│   │   ├── ocr_service.py            # Document Intelligence integration
│   │   ├── document_service.py       # Document processing orchestration
│   │   ├── text_preprocessing_service.py  # Text cleaning & segmentation
│   │   ├── nlp_service.py            # spaCy NLP analysis
│   │   ├── clause_extraction_service.py   # Clause extraction orchestration
│   │   ├── rules_engine.py           # YAML-based leakage detection
│   │   ├── embedding_service.py      # Vector embeddings (text-embedding-3-large)
│   │   ├── search_service.py         # Azure AI Search integration
│   │   ├── rag_service.py            # RAG orchestration
│   │   ├── ai_detection_service.py   # GPT-5.2 leakage detection
│   │   └── report_service.py         # PDF/Excel generation
│   │
│   └── utils/                        # Utilities
│       ├── config.py                 # Configuration management (Settings class)
│       ├── logging.py                # Logging setup
│       ├── exceptions.py             # Custom exceptions
│       └── brand_constants.py        # KPMG-inspired branding for reports
│
├── rules/
│   └── leakage_rules.yaml            # 15+ detection rules
│
├── shared-types/                     # TypeScript types package
│   └── src/
│       ├── models/                   # TS interfaces matching Python models
│       ├── enums/                    # TS enums
│       └── api/                      # Request/response types
│
├── contract-leakage-engine-frontend/ # React frontend (separate directory)
│
├── requirements.txt                  # Python dependencies
├── host.json                         # Azure Functions config
├── local.settings.json               # Local config (NOT in git)
└── reference docs/                   # Original POC specifications (.docx)
```

---

## Key Concepts & Terminology

### Data Models

| Model | Description | Partition Key |
|-------|-------------|---------------|
| **Contract** | Uploaded contract metadata and status | `contract_id` |
| **Clause** | Extracted clause with type, entities, risk signals | `contract_id` |
| **LeakageFinding** | Detected risk with severity, impact, explanation | `contract_id` |
| **AnalysisSession** | Analysis job tracking | `contract_id` |
| **UserOverride** | User actions on findings (accept, reject, etc.) | `contract_id` |

### Enums

**ContractStatus**: `pending`, `processing`, `analyzed`, `error`

**ClauseType** (13 types): `pricing`, `payment_terms`, `renewal`, `termination`, `service_level`, `liability`, `indemnification`, `intellectual_property`, `confidentiality`, `force_majeure`, `audit_rights`, `data_protection`, `general`

**Severity**: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

**LeakageCategory** (10 categories): `pricing`, `payment`, `renewal`, `termination`, `service_level`, `liability`, `penalties`, `volume_commitment`, `compliance`, `other`

**DetectionMethod**: `RULE`, `AI`, `HYBRID`

**OverrideAction**: `accept`, `reject`, `change_severity`, `mark_false_positive`, `add_note`, `resolve`

### Detection Pipeline

```
Upload → OCR → Text Preprocessing → Clause Extraction (NLP + GPT-4.5)
                                           ↓
                              ┌────────────┴────────────┐
                              ↓                         ↓
                      Rules Engine              AI Detection (GPT-5.2)
                    (YAML patterns)                   (RAG context)
                              ↓                         ↓
                              └────────────┬────────────┘
                                           ↓
                                   Combined Findings
                                           ↓
                                   User Review & Export
```

### RAG Architecture

```
Clauses → Embeddings (3072-dim) → Azure AI Search Index
                                         ↓
User Query → Query Embedding → Vector Search → Top K Clauses
                                         ↓
                         RAG Context (15 clauses) → GPT-5.2 → AI Findings
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check (anonymous) |
| `POST` | `/api/upload_contract` | Upload contract file (multipart/form-data) |
| `POST` | `/api/analyze_contract/{contract_id}` | Trigger analysis pipeline |
| `GET` | `/api/get_analysis/{contract_id}` | Get complete analysis results |
| `GET` | `/api/list_contracts` | List all contracts |
| `POST` | `/api/dismiss_finding/{contract_id}/{finding_id}` | Dismiss a finding |
| `GET` | `/api/export_report/{contract_id}?format=pdf\|excel` | Export report |
| `POST` | `/api/overrides/{contract_id}` | Create user override |
| `GET` | `/api/overrides/{contract_id}` | Get overrides for contract |
| `GET` | `/api/overrides/{contract_id}/summary` | Get override summary |

### Authentication
All endpoints (except `/health`) use Function-level authentication:
- Header: `x-functions-key: <function-key>`
- Query: `?code=<function-key>`

---

## Cosmos DB Containers

| Container | Partition Key | Purpose |
|-----------|---------------|---------|
| `contracts` | `/contract_id` | Contract metadata |
| `clauses` | `/contract_id` | Extracted clauses |
| `leakage_findings` | `/contract_id` | Detected risks |
| `analysis_sessions` | `/contract_id` | Analysis jobs |
| `user_overrides` | `/contract_id` | User actions |

---

## Leakage Detection Rules

Rules are defined in `rules/leakage_rules.yaml`. Current rules include:

| Rule ID | Category | Severity | Description |
|---------|----------|----------|-------------|
| `MISSING_PRICE_ESCALATION` | pricing | HIGH | Fixed pricing without escalation in multi-year contracts |
| `NO_VOLUME_DISCOUNT_CAP` | pricing | MEDIUM | Volume discounts without minimum/cap |
| `MISSING_LATE_PAYMENT_PENALTY` | payment | MEDIUM | No late fee provisions |
| `AUTO_RENEWAL_WITHOUT_PRICE_INCREASE` | renewal | HIGH | Auto-renewal without price adjustment |
| `UNFAVORABLE_TERMINATION_TERMS` | termination | MEDIUM | Termination for convenience without penalty |
| `SHORT_NOTICE_PERIOD` | termination | LOW | Notice period < 60 days |
| `NO_SERVICE_LEVEL_AGREEMENT` | service_level | MEDIUM | Missing SLA |
| `SLA_WITHOUT_CREDITS` | service_level | MEDIUM | SLA exists but no service credits |
| `UNLIMITED_LIABILITY` | liability | CRITICAL | No liability cap |
| `ONE_SIDED_INDEMNIFICATION` | liability | HIGH | Asymmetric indemnification |
| `MISSING_LIQUIDATED_DAMAGES` | penalties | MEDIUM | No penalty for delays |
| `NO_MINIMUM_COMMITMENT` | volume_commitment | MEDIUM | Usage-based without minimums |

---

## Configuration

### Environment Variables (local.settings.json)

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "CosmosDBConnectionString": "AccountEndpoint=...",
    "CosmosDBDatabaseName": "ContractLeakageDB",
    "CosmosDBOverridesContainer": "user_overrides",
    "StorageConnectionString": "DefaultEndpointsProtocol=...",
    "StorageContainerName": "contracts",
    "OpenAIKey": "...",
    "OpenAIEndpoint": "https://...",
    "OpenAIDeploymentName": "gpt-5.2",
    "OpenAIEmbeddingDeploymentName": "text-embedding-3-large",
    "OpenAIAPIVersion": "2024-08-01-preview",
    "EmbeddingDimensions": "3072",
    "SearchServiceEndpoint": "https://...",
    "SearchServiceKey": "...",
    "SearchIndexName": "clauses-index",
    "DocumentIntelligenceEndpoint": "https://...",
    "DocumentIntelligenceKey": "..."
  }
}
```

---

## Development Setup

### Backend

```bash
# Navigate to backend
cd contract-leakage-engine-backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_lg

# Copy and configure local settings
cp local.settings.json.example local.settings.json

# Start locally
func start
```

### Frontend

```bash
# Build shared-types first
cd shared-types
npm install && npm run build && npm link

# Setup frontend
cd ../contract-leakage-engine-frontend
npm install
npm link @contract-leakage/shared-types

# Start development server (port 3000)
npm run dev
```

---

## Code Quality

### Backend Commands

```bash
# Format with Black
black shared/ api/ --exclude=".venv"

# Sort imports with isort
isort shared/ api/ --skip=.venv

# Lint with flake8
flake8 shared/ api/ --max-line-length=120 --ignore=E203,W503,E501 --exclude=.venv

# Type check with mypy
mypy shared/ api/ --ignore-missing-imports --exclude=".venv"
```

### Frontend Commands

```bash
# Type check
npm run type-check

# Lint with ESLint
npm run lint

# Build
npm run build
```

### Pydantic Best Practices

When using `default_factory` with Pydantic models:
```python
# CORRECT - use lambda for mutable defaults
assumptions: Assumptions = Field(
    default_factory=lambda: Assumptions(inflation_rate=None, remaining_years=None)
)

# INCORRECT - direct reference causes mypy errors
assumptions: Assumptions = Field(default_factory=Assumptions)
```

---

## Common Patterns

### Repository Pattern

All repositories extend `BaseRepository` and use `contract_id` as partition key:

```python
from shared.db.repositories.base import BaseRepository

class FindingRepository(BaseRepository):
    def get_by_contract_id(self, contract_id: str) -> List[LeakageFinding]:
        return self.query(
            query="SELECT * FROM c WHERE c.contract_id = @contract_id",
            parameters=[{"name": "@contract_id", "value": contract_id}]
        )
```

### Service Layer Pattern

Services encapsulate business logic and use dependency injection:

```python
class AIDetectionService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.rag_service = RAGService()
        self.finding_repo = FindingRepository()

    async def detect_leakage(self, contract_id: str, metadata: Dict) -> List[LeakageFinding]:
        # Index clauses for RAG
        await self.rag_service.index_contract_clauses(contract_id)
        # Build context and call GPT-5.2
        context = await self.rag_service.build_rag_context(queries, contract_id)
        # Parse and store findings
        ...
```

### Error Handling

Custom exceptions in `shared/utils/exceptions.py`:

```python
class ContractNotFoundError(Exception): ...
class FileSizeExceededError(Exception): ...
class UnsupportedFileTypeError(Exception): ...
class AIServiceError(Exception): ...
class EmbeddingServiceError(AIServiceError): ...
class RAGServiceError(AIServiceError): ...
```

---

## Report Generation

Reports use KPMG-inspired branding from `brand_constants.py`:

**Colors**:
- Primary Blue: `#1a237e`
- Critical Red: `#d32f2f`
- High Orange: `#f57c00`
- Medium Yellow: `#fbc02d`
- Low Green: `#388e3c`

**PDF Structure**:
1. Cover page with metrics dashboard
2. Executive summary
3. Findings by severity
4. Detailed findings with recommendations
5. Optional clause appendix

---

## Key Files Reference

| File | Purpose |
|------|---------|
| [README.md](README.md) | Project overview |
| [AZURE_SETUP.md](AZURE_SETUP.md) | Azure resource creation guide |
| [QUICK_START.md](QUICK_START.md) | Quick start guide |
| [API_REFERENCE.md](API_REFERENCE.md) | Complete API documentation |
| [PHASE_5_RAG_AI_SUMMARY.md](PHASE_5_RAG_AI_SUMMARY.md) | RAG + AI detection details |
| [PHASE_6_EXPORT_SUMMARY.md](PHASE_6_EXPORT_SUMMARY.md) | Report generation details |
| [FRONTEND_SETUP_SUMMARY.md](FRONTEND_SETUP_SUMMARY.md) | Frontend architecture |
| [SHARED_TYPES_PACKAGE.md](SHARED_TYPES_PACKAGE.md) | TypeScript types package |
| [BACKEND_OVERRIDES_IMPLEMENTATION.md](BACKEND_OVERRIDES_IMPLEMENTATION.md) | User override system |
| [CODE_QUALITY_INSTRUCTIONS.md](CODE_QUALITY_INSTRUCTIONS.md) | Linting and formatting |
| [FINAL_PROJECT_SUMMARY.md](FINAL_PROJECT_SUMMARY.md) | Complete project status |
| [SYSTEM_EVALUATION_REPORT.md](SYSTEM_EVALUATION_REPORT.md) | Comprehensive system evaluation |
| [SYSTEM_EVALUATION_PLAN.md](SYSTEM_EVALUATION_PLAN.md) | Evaluation methodology |
| [rules/leakage_rules.yaml](rules/leakage_rules.yaml) | Detection rules definition |

---

## Troubleshooting

### Backend Issues

**"Module not found" errors**
- Ensure `.venv` is activated
- Run `pip install -r requirements.txt`

**"Cannot connect to Cosmos DB"**
- Check `CosmosDBConnectionString` in `local.settings.json`
- Verify database and containers exist

**mypy Pydantic errors**
- Use `default_factory=lambda: Model()` pattern
- Add `# type: ignore[call-arg]` for known safe calls

### Frontend Issues

**TypeScript import errors**
- Rebuild shared-types: `cd shared-types && npm run build`
- Re-link: `npm link @contract-leakage/shared-types`
- Restart VS Code TS server

**API proxy not working**
- Ensure backend is running on port 7071
- Check `vite.config.ts` proxy configuration

---

## Project Status

**Completion: 95% (20/21 tasks)**

**System Evaluation Grade: B+ (Good with Issues)**

| Area | Score |
|------|-------|
| Architecture | A |
| Feature Completeness | A- |
| Code Quality | B+ |
| Security | B |
| Documentation | A |

### Remaining Tasks
- Azure Cosmos DB `user_overrides` container creation
- Final deployment and end-to-end testing
- Add unit/integration tests (0% coverage currently)
- Setup CI/CD pipeline

### Recent Fixes (2026-01-21)
- Fixed TailwindCSS `border-neutral-medium` undefined error
- Fixed shared-types ESM/CommonJS mismatch for Vite compatibility
- Added `neutral` color palette to tailwind.config.js
- Updated shared-types to ES2020 modules with proper exports

### Known Issues
- 2 moderate npm vulnerabilities in esbuild/vite (dev-only, non-critical)
- 18 outdated Python packages (non-breaking)

---

## Important Notes

1. **Never commit `local.settings.json`** - Contains secrets
2. **Always exclude `.venv`** when running code quality tools
3. **Build shared-types first** before working on frontend
4. **Partition key is `contract_id`** for all containers
5. **GPT-5.2** is used for detection, **GPT-4.5** for clause extraction
6. **Vector embeddings are 3072 dimensions** (text-embedding-3-large)
7. **Reports follow KPMG Master Guide** design principles

---

*Last updated: 2026-01-21*
