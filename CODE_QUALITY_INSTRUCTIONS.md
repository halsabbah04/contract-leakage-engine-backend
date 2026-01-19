# Code Quality Instructions - Backend & Frontend

## Backend (Python)

### Setup

Install development dependencies:

```bash
cd contract-leakage-engine-backend
pip install black isort flake8 mypy pylint pytest
```

Or add to `requirements-dev.txt`:
```
black==24.1.1
isort==5.13.2
flake8==7.0.0
mypy==1.8.0
pylint==3.0.3
pytest==8.0.0
```

Then install:
```bash
pip install -r requirements-dev.txt
```

---

### 1. Code Formatting with Black

**Check formatting (no changes):**
```bash
black --check shared/ api/
```

**Format code:**
```bash
black shared/ api/
```

**Configuration** (create `pyproject.toml`):
```toml
[tool.black]
line-length = 120
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  \.venv
  | __pycache__
  | \.pytest_cache
)/
'''
```

---

### 2. Import Sorting with isort

**Check imports:**
```bash
isort --check-only shared/ api/
```

**Sort imports:**
```bash
isort shared/ api/
```

**Configuration** (add to `pyproject.toml`):
```toml
[tool.isort]
profile = "black"
line_length = 120
skip_glob = ["*/.venv/*", "*/__pycache__/*"]
```

---

### 3. Linting with flake8

**Run linter:**
```bash
flake8 shared/ api/ --max-line-length=120 --ignore=E203,W503,E501
```

**Ignore codes:**
- `E203`: Whitespace before ':' (conflicts with Black)
- `W503`: Line break before binary operator (conflicts with Black)
- `E501`: Line too long (Black handles this)

**Configuration** (create `.flake8`):
```ini
[flake8]
max-line-length = 120
ignore = E203,W503,E501
exclude =
    .venv,
    __pycache__,
    .pytest_cache,
    .git
per-file-ignores =
    __init__.py:F401
```

---

### 4. Type Checking with mypy

**Run type checker:**
```bash
mypy shared/ api/ --ignore-missing-imports
```

**Configuration** (add to `pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
exclude = [
    "\.venv",
    "__pycache__",
]
```

---

### 5. Comprehensive Linting with pylint

**Run pylint:**
```bash
pylint shared/ api/ --max-line-length=120 --disable=C0111,R0903
```

**Disable codes:**
- `C0111`: Missing docstring (enable only for public APIs)
- `R0903`: Too few public methods (Pydantic models)

**Configuration** (create `.pylintrc` or add to `pyproject.toml`):
```toml
[tool.pylint.main]
max-line-length = 120

[tool.pylint.messages_control]
disable = [
    "C0111",  # missing-docstring
    "R0903",  # too-few-public-methods
    "R0913",  # too-many-arguments
]
```

---

### 6. Testing with pytest

**Run tests:**
```bash
pytest tests/ -v
```

**Run with coverage:**
```bash
pytest tests/ --cov=shared --cov=api --cov-report=html
```

---

### Combined Script

Create `scripts/lint.sh` (Linux/Mac) or `scripts/lint.bat` (Windows):

**lint.sh:**
```bash
#!/bin/bash
echo "=== Running Black ==="
black shared/ api/

echo "=== Running isort ==="
isort shared/ api/

echo "=== Running flake8 ==="
flake8 shared/ api/ --max-line-length=120 --ignore=E203,W503,E501

echo "=== Running mypy ==="
mypy shared/ api/ --ignore-missing-imports

echo "=== Done! ==="
```

**lint.bat:**
```batch
@echo off
echo === Running Black ===
black shared\ api\

echo === Running isort ===
isort shared\ api\

echo === Running flake8 ===
flake8 shared\ api\ --max-line-length=120 --ignore=E203,W503,E501

echo === Running mypy ===
mypy shared\ api\ --ignore-missing-imports

echo === Done! ===
```

Make executable:
```bash
chmod +x scripts/lint.sh
```

Run:
```bash
./scripts/lint.sh
```

---

## Frontend (TypeScript/React)

### Setup

Dependencies already in `package.json`:
- ESLint - Linting
- TypeScript - Type checking
- Prettier (if added)

Install if needed:
```bash
cd contract-leakage-engine-frontend
npm install --save-dev prettier
```

---

### 1. Type Checking with TypeScript

**Check types:**
```bash
npm run type-check
```

This runs: `tsc --noEmit`

**Fix import errors:**
- Ensure `npm install` has been run
- Ensure shared-types is built: `cd ../shared-types && npm run build`
- Restart VS Code TypeScript server: `Ctrl+Shift+P` → "TypeScript: Restart TS Server"

---

### 2. Linting with ESLint

**Check linting:**
```bash
npm run lint
```

This runs: `eslint . --ext ts,tsx`

**Fix auto-fixable issues:**
```bash
npx eslint . --ext ts,tsx --fix
```

**Configuration** (`.eslintrc.cjs` already exists)

---

### 3. Code Formatting with Prettier (Optional)

**Install:**
```bash
npm install --save-dev prettier
```

**Create `.prettierrc`:**
```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "arrowParens": "always"
}
```

**Format code:**
```bash
npx prettier --write "src/**/*.{ts,tsx,json,css}"
```

**Check formatting:**
```bash
npx prettier --check "src/**/*.{ts,tsx,json,css}"
```

**Add to package.json scripts:**
```json
{
  "scripts": {
    "format": "prettier --write \"src/**/*.{ts,tsx,json,css}\"",
    "format:check": "prettier --check \"src/**/*.{ts,tsx,json,css}\""
  }
}
```

---

### 4. Build Verification

**Build frontend:**
```bash
npm run build
```

**Expected output:**
```
vite v5.0.11 building for production...
✓ 1234 modules transformed.
dist/index.html                   0.45 kB │ gzip:  0.30 kB
dist/assets/index-abc123.css     24.56 kB │ gzip:  6.78 kB
dist/assets/index-xyz789.js     234.56 kB │ gzip: 78.90 kB
✓ built in 3.45s
```

---

### Combined Script

Create `scripts/lint.sh`:

**lint.sh:**
```bash
#!/bin/bash
echo "=== Building shared-types ==="
cd ../contract-leakage-engine-backend/shared-types
npm run build

echo "=== Installing frontend deps ==="
cd ../../contract-leakage-engine-frontend
npm install

echo "=== Running TypeScript type check ==="
npm run type-check

echo "=== Running ESLint ==="
npm run lint

echo "=== Building frontend ==="
npm run build

echo "=== Done! ==="
```

---

## Pre-Commit Hooks (Optional)

### Install pre-commit

```bash
pip install pre-commit
```

### Create `.pre-commit-config.yaml` (Backend):

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=120', '--ignore=E203,W503,E501']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: ['--ignore-missing-imports']
```

### Install hooks:

```bash
pre-commit install
```

### Run manually:

```bash
pre-commit run --all-files
```

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/lint.yml`:

```yaml
name: Lint and Test

on: [push, pull_request]

jobs:
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd contract-leakage-engine-backend
          pip install black isort flake8 mypy
      - name: Run Black
        run: |
          cd contract-leakage-engine-backend
          black --check shared/ api/
      - name: Run isort
        run: |
          cd contract-leakage-engine-backend
          isort --check-only shared/ api/
      - name: Run flake8
        run: |
          cd contract-leakage-engine-backend
          flake8 shared/ api/ --max-line-length=120

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Build shared-types
        run: |
          cd contract-leakage-engine-backend/shared-types
          npm install
          npm run build
      - name: Install frontend dependencies
        run: |
          cd contract-leakage-engine-frontend
          npm install
      - name: Type check
        run: |
          cd contract-leakage-engine-frontend
          npm run type-check
      - name: Lint
        run: |
          cd contract-leakage-engine-frontend
          npm run lint
      - name: Build
        run: |
          cd contract-leakage-engine-frontend
          npm run build
```

---

## Quick Reference

### Backend Commands
```bash
# Format
black shared/ api/
isort shared/ api/

# Lint
flake8 shared/ api/ --max-line-length=120 --ignore=E203,W503,E501
mypy shared/ api/ --ignore-missing-imports
pylint shared/ api/ --max-line-length=120

# Test
pytest tests/ -v
```

### Frontend Commands
```bash
# Build shared-types first
cd ../contract-leakage-engine-backend/shared-types && npm run build && cd ../../contract-leakage-engine-frontend

# Install deps
npm install

# Type check
npm run type-check

# Lint
npm run lint

# Build
npm run build
```

---

## Current Status

### Backend ✅
- ✅ Models created with type hints
- ✅ Repositories with proper error handling
- ✅ Azure Functions endpoints
- ⏳ **Needs**: black, isort, flake8, mypy run
- ⏳ **Needs**: Tests written

### Frontend ✅
- ✅ TypeScript strict mode
- ✅ ESLint configured
- ✅ Components properly typed
- ⏳ **Needs**: npm install (to link shared-types)
- ⏳ **Needs**: Type check pass
- ⏳ **Needs**: Build verification

### Shared Types ✅
- ✅ TypeScript types match Python models
- ⏳ **Needs**: npm run build
- ⏳ **Needs**: Link to frontend

---

## Recommended Order

1. **Build shared-types**: `cd shared-types && npm install && npm run build`
2. **Install frontend deps**: `cd ../frontend && npm install`
3. **Format backend**: `black shared/ api/ && isort shared/ api/`
4. **Lint backend**: `flake8 shared/ api/ --max-line-length=120`
5. **Type check frontend**: `npm run type-check`
6. **Lint frontend**: `npm run lint`
7. **Build frontend**: `npm run build`
8. **Test backend**: `pytest tests/ -v`

This ensures all code quality checks pass before deployment! 🚀
