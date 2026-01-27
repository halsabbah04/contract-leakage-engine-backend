# Contract Leakage Engine - Comprehensive Evaluation Plan

## Overview
This plan outlines a complete evaluation of the Contract Leakage Engine POC covering code quality, security, database, API contracts, dependencies, and documentation alignment.

---

## Phase 1: Backend Code Quality (Python)

### 1.1 Static Analysis
- [ ] Run `black` for code formatting check
- [ ] Run `isort` for import ordering
- [ ] Run `flake8` for linting (max-line-length=120)
- [ ] Run `mypy` for type checking with Pydantic plugin

### 1.2 Code Structure Review
- [ ] Verify all 10 Azure Functions endpoints have proper error handling
- [ ] Check repository pattern implementation consistency
- [ ] Validate service layer patterns
- [ ] Review exception handling in all services

### 1.3 Files to Analyze
```
api/                  (10 endpoints)
shared/models/        (5 Pydantic models)
shared/db/            (Cosmos client + 5 repositories)
shared/services/      (12 services)
shared/utils/         (config, logging, exceptions)
```

---

## Phase 2: Frontend Code Quality (React/TypeScript)

### 2.1 Static Analysis
- [ ] Run `npm run lint` (ESLint)
- [ ] Run `npm run type-check` (TypeScript)
- [ ] Check for console.log statements in production code

### 2.2 Code Structure Review
- [ ] Verify component structure and naming conventions
- [ ] Check React hooks usage patterns
- [ ] Validate TanStack Query implementations
- [ ] Review error boundary implementations

### 2.3 Files to Analyze
```
src/pages/            (Main page components)
src/components/       (Reusable components)
src/hooks/            (Custom hooks)
src/services/         (API service layer)
```

---

## Phase 3: Security Analysis

### 3.1 Backend Security
- [ ] **Input Validation**: Check all API endpoints for proper input sanitization
- [ ] **File Upload Security**: Validate file type/size restrictions in upload_contract
- [ ] **SQL/NoSQL Injection**: Review Cosmos DB queries for parameterization
- [ ] **Secrets Management**: Verify no hardcoded secrets, proper use of environment variables
- [ ] **Authentication**: Verify Function-level auth on all endpoints (except /health)
- [ ] **CORS Configuration**: Review host.json CORS settings

### 3.2 Frontend Security
- [ ] **XSS Prevention**: Check for dangerouslySetInnerHTML usage
- [ ] **API Key Exposure**: Ensure no secrets in frontend code
- [ ] **Local Storage**: Review what's stored (user email only)
- [ ] **Input Sanitization**: Verify form inputs are properly handled

### 3.3 Dependency Security
- [ ] Run `pip audit` or `safety check` on Python dependencies
- [ ] Run `npm audit` on frontend dependencies

---

## Phase 4: Database & Data Model Validation

### 4.1 Cosmos DB Schema Review
- [ ] Verify partition key design (`contract_id` for all containers)
- [ ] Check index policies
- [ ] Review query efficiency patterns

### 4.2 Data Model Consistency
- [ ] Compare Python Pydantic models with TypeScript interfaces
- [ ] Verify enum values match between backend and frontend
- [ ] Check for missing or extra fields

### 4.3 Containers to Validate
```
contracts           (Contract model)
clauses             (Clause model)
leakage_findings    (LeakageFinding model)
analysis_sessions   (AnalysisSession model)
user_overrides      (UserOverride model)
```

---

## Phase 5: API Contract Validation

### 5.1 Endpoint Coverage
- [ ] Verify all 10 endpoints documented in API_REFERENCE.md exist
- [ ] Check request/response types match shared-types package

### 5.2 Endpoints to Verify
| Endpoint | Method | Auth |
|----------|--------|------|
| /api/health | GET | Anonymous |
| /api/upload_contract | POST | Function Key |
| /api/analyze_contract | POST | Function Key |
| /api/get_analysis/{id} | GET | Function Key |
| /api/list_contracts | GET | Function Key |
| /api/dismiss_finding/{id}/{finding_id} | POST | Function Key |
| /api/export_report/{id} | GET | Function Key |
| /api/overrides/{id} | POST | Function Key |
| /api/overrides/{id} | GET | Function Key |
| /api/overrides/{id}/summary | GET | Function Key |

### 5.3 Shared Types Validation
- [ ] Build shared-types package
- [ ] Verify TypeScript types compile
- [ ] Check exports match documentation

---

## Phase 6: Dependency Analysis

### 6.1 Backend (requirements.txt)
- [ ] Check for outdated packages
- [ ] Identify known vulnerabilities
- [ ] Verify version pinning

### 6.2 Frontend (package.json)
- [ ] Check for outdated packages
- [ ] Identify known vulnerabilities
- [ ] Verify compatible React/TypeScript versions

---

## Phase 7: Documentation Accuracy

### 7.1 Backend Documentation (15 files)
- [ ] README.md - Project overview accuracy
- [ ] AZURE_SETUP.md - Setup instructions completeness
- [ ] API_REFERENCE.md - Endpoint documentation accuracy
- [ ] CLAUDE.md - Reference guide accuracy
- [ ] PHASE_5_RAG_AI_SUMMARY.md - RAG implementation details
- [ ] PHASE_6_EXPORT_SUMMARY.md - Report generation details
- [ ] BACKEND_OVERRIDES_IMPLEMENTATION.md - Override system docs

### 7.2 Frontend Documentation (7 files)
- [ ] README.md - Setup and usage
- [ ] PROJECT_STATUS.md - Current status accuracy
- [ ] Component summaries (4 files)

### 7.3 Reference Docs Alignment (15 .docx files)
- [ ] Functional Requirements vs Implementation
- [ ] Data Model vs Actual Schema
- [ ] Non-Functional Requirements vs Current State

---

## Phase 8: Configuration Review

### 8.1 Azure Functions Config
- [ ] host.json - Function settings, CORS
- [ ] local.settings.json.example - Template completeness
- [ ] function.json files - Route bindings

### 8.2 Frontend Config
- [ ] vite.config.ts - Build settings, proxy config
- [ ] tsconfig.json - TypeScript settings
- [ ] tailwind.config.js - Theme configuration

---

## Phase 9: Rules Engine Validation

### 9.1 Leakage Rules (rules/leakage_rules.yaml)
- [ ] Verify all 15+ rules are properly structured
- [ ] Check severity levels are consistent
- [ ] Validate impact calculation methods

---

## Execution Commands

### Backend Checks
```bash
cd contract-leakage-engine-backend
source .venv/Scripts/activate  # Windows

# Code formatting
black shared/ api/ --check --exclude=".venv"
isort shared/ api/ --check-only --skip=.venv

# Linting
flake8 shared/ api/ --max-line-length=120 --ignore=E203,W503,E501 --exclude=.venv

# Type checking
mypy shared/ api/ --ignore-missing-imports --exclude=".venv"

# Security
pip install safety
safety check -r requirements.txt
```

### Frontend Checks
```bash
cd contract-leakage-engine-frontend

# Linting and type-check
npm run lint
npm run type-check

# Security
npm audit

# Build verification
npm run build
```

### Shared Types
```bash
cd contract-leakage-engine-backend/shared-types
npm install
npm run build
```

---

## Output Deliverables

1. **EVALUATION_REPORT.md** - Detailed findings with severity ratings
2. **Issues List** - Prioritized list of issues to fix
3. **Security Assessment** - Security-specific findings
4. **Recommendations** - Suggested improvements

---

## Estimated Scope

| Phase | Items | Parallel Agents |
|-------|-------|-----------------|
| Phase 1: Backend Code | 4 checks | 1 |
| Phase 2: Frontend Code | 4 checks | 1 |
| Phase 3: Security | 10 checks | 2 |
| Phase 4: Database | 5 checks | 1 |
| Phase 5: API Contracts | 12 endpoints | 1 |
| Phase 6: Dependencies | 2 checks | 2 |
| Phase 7: Documentation | 22 files | 1 |
| Phase 8: Configuration | 6 files | 1 |
| Phase 9: Rules Engine | 1 file | 1 |

**Total: ~67 individual checks**

---

*Plan created: 2026-01-20*
