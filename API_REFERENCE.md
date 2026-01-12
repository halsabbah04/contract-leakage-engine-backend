# API Reference - Contract Leakage Engine

Base URL (local): `http://localhost:7071/api`
Base URL (Azure): `https://func-contract-leakage-poc.azurewebsites.net/api`

## Authentication

All endpoints (except `/health`) use Function-level authentication. Include the function key in the request:
- Header: `x-functions-key: <your-function-key>`
- Or query parameter: `?code=<your-function-key>`

---

## Endpoints

### 1. Health Check

**GET** `/health`

Check if the API is running.

**Authentication**: None (anonymous)

**Response** (200):
```json
{
  "status": "healthy",
  "timestamp": "2026-01-08T14:30:00.000Z",
  "service": "AI Contract & Commercial Leakage Engine",
  "version": "1.0.0-poc",
  "runtime": "python",
  "database": {
    "cosmos_db": "ContractLeakageDB",
    "connected": true
  }
}
```

---

### 2. Upload Contract

**POST** `/upload_contract`

Upload a contract file (PDF or DOCX) for analysis.

**Content-Type**: `multipart/form-data`

**Request Body** (form data):
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF or DOCX file |
| `contract_name` | string | No | Contract name (defaults to filename) |
| `counterparty` | string | No | Other party name |
| `start_date` | string | No | Contract start date (ISO format) |
| `end_date` | string | No | Contract end date (ISO format) |
| `contract_value` | number | No | Estimated contract value (USD) |

**Response** (201):
```json
{
  "message": "Contract uploaded successfully",
  "contract_id": "contract_a1b2c3d4e5f6",
  "contract_name": "Master Services Agreement.pdf",
  "file_size_mb": 2.5,
  "status": "uploaded"
}
```

**Error Responses**:
- `400` - Invalid file type or missing file
- `413` - File too large (max 50MB)
- `500` - Server error

---

### 3. Analyze Contract

**POST** `/analyze_contract/{contract_id}`

Trigger complete analysis pipeline for an uploaded contract.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `contract_id` | string | Contract identifier |

**Response** (200):
```json
{
  "message": "Analysis completed successfully",
  "contract_id": "contract_a1b2c3d4e5f6",
  "status": "analyzed",
  "duration_seconds": 12.5,
  "note": "Full analysis pipeline will be implemented in subsequent phases"
}
```

**Error Responses**:
- `404` - Contract not found
- `409` - Analysis already in progress
- `500` - Server error

**Note**: Currently returns synchronously. In production, this will be asynchronous with status polling.

---

### 4. Get Analysis

**GET** `/get_analysis/{contract_id}`

Retrieve complete analysis results for a contract.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `contract_id` | string | Contract identifier |

**Response** (200):
```json
{
  "contract": {
    "id": "contract_a1b2c3d4e5f6",
    "contract_name": "Master Services Agreement",
    "status": "analyzed",
    "counterparty": "Acme Corp",
    "contract_value_estimate": 1200000.0,
    ...
  },
  "clauses": [
    {
      "id": "clause_001",
      "clause_type": "pricing",
      "original_text": "Prices shall remain fixed...",
      "normalized_summary": "Fixed pricing with no escalation",
      "risk_signals": ["no_price_escalation"],
      ...
    }
  ],
  "findings": [
    {
      "id": "finding_001",
      "leakage_category": "pricing",
      "severity": "high",
      "explanation": "Fixed pricing may lead to revenue erosion...",
      "estimated_impact": {
        "currency": "USD",
        "value": 72000
      },
      ...
    }
  ],
  "session": {
    "id": "session_contract_a1b2c3d4e5f6",
    "overrides": [],
    ...
  },
  "summary": {
    "total_clauses": 15,
    "total_findings": 5,
    "active_findings": 4,
    "critical_findings": 1,
    "high_findings": 2,
    "total_estimated_impact": 150000.0
  }
}
```

**Error Responses**:
- `404` - Contract not found
- `500` - Server error

---

### 5. List Contracts

**GET** `/list_contracts`

List all contracts with optional filtering.

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (optional) |
| `limit` | number | Max results (default: 50) |

**Valid statuses**:
- `uploaded`
- `extracting_text`
- `text_extracted`
- `extracting_clauses`
- `clauses_extracted`
- `analyzing`
- `analyzed`
- `failed`

**Response** (200):
```json
{
  "contracts": [
    {
      "contract_id": "contract_a1b2c3d4e5f6",
      "contract_name": "Master Services Agreement",
      "status": "analyzed",
      "source": "upload",
      "counterparty": "Acme Corp",
      "created_at": "2026-01-08T10:00:00Z",
      "contract_value_estimate": 1200000.0
    }
  ],
  "total": 1,
  "filters": {
    "status": null,
    "limit": 50
  }
}
```

**Error Responses**:
- `400` - Invalid status value
- `500` - Server error

---

### 6. Dismiss Finding

**POST** `/dismiss_finding/{contract_id}/{finding_id}`

Dismiss a leakage finding and optionally add notes.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `contract_id` | string | Contract identifier |
| `finding_id` | string | Finding identifier |

**Request Body** (JSON, optional):
```json
{
  "reason": "Covered by side letter agreement",
  "notes": "Additional context about why this is not an issue"
}
```

**Response** (200):
```json
{
  "message": "Finding dismissed successfully",
  "finding_id": "finding_001",
  "contract_id": "contract_a1b2c3d4e5f6",
  "finding": {
    "id": "finding_001",
    "user_dismissed": true,
    "user_notes": "Additional context...",
    ...
  }
}
```

**Error Responses**:
- `404` - Finding not found
- `500` - Server error

---

## Error Response Format

All error responses follow this format:

```json
{
  "error": "Human-readable error message",
  "details": "Technical details (if available)"
}
```

---

## Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created successfully |
| 202 | Accepted (async processing started) |
| 400 | Bad request (invalid parameters) |
| 401 | Unauthorized (missing or invalid auth) |
| 404 | Resource not found |
| 409 | Conflict (e.g., operation already in progress) |
| 413 | Payload too large |
| 500 | Internal server error |

---

## Usage Example (cURL)

### Upload and analyze a contract

```bash
# 1. Upload contract
curl -X POST http://localhost:7071/api/upload_contract \
  -F "file=@contract.pdf" \
  -F "contract_name=My Contract" \
  -F "counterparty=Acme Corp"

# Response: {"contract_id": "contract_abc123", ...}

# 2. Trigger analysis
curl -X POST http://localhost:7071/api/analyze_contract/contract_abc123

# 3. Get results
curl http://localhost:7071/api/get_analysis/contract_abc123
```

---

## Coming Soon

The following endpoints will be added in future phases:

- `POST /update_assumptions/{contract_id}` - Update custom assumptions for impact calculation
- `GET /generate_report/{contract_id}` - Export analysis report (PDF/Excel)
- `DELETE /cleanup_session/{session_id}` - Clean up analysis session data
- `GET /search_clauses/{contract_id}` - Semantic search across clauses (RAG)
- `POST /manual_contract` - Submit contract data via structured form (no file upload)

---

## Development Notes

- All timestamps are in UTC ISO 8601 format
- Vector embeddings are excluded from API responses for performance
- Partition key (`contract_id`) is used for all Cosmos DB queries
- File uploads limited to 50MB (configurable in `local.settings.json`)
- Supported file types: PDF, DOCX, DOC
