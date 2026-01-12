# Shared TypeScript Types Package

## Overview

Created a comprehensive TypeScript types package (`shared-types/`) that provides strongly-typed interfaces matching all Python Pydantic models and API structures. This ensures type safety and consistency between backend and frontend.

---

## Package Structure

```
shared-types/
├── package.json              # NPM package configuration
├── tsconfig.json            # TypeScript compiler configuration
├── .gitignore               # Git ignore rules
├── README.md                # Package documentation
└── src/
    ├── index.ts             # Main export file
    ├── enums/
    │   └── index.ts         # All enums
    ├── models/
    │   ├── contract.ts      # Contract & ContractMetadata
    │   ├── clause.ts        # Clause & ExtractedEntities
    │   ├── finding.ts       # LeakageFinding & FinancialImpact
    │   └── session.ts       # AnalysisSession
    └── api/
        ├── requests.ts      # API request types
        └── responses.ts     # API response types
```

---

## Type Definitions

### Enums

All Python enums converted to TypeScript string enums:

```typescript
export enum ContractStatus {
  PENDING = "pending",
  PROCESSING = "processing",
  ANALYZED = "analyzed",
  ERROR = "error"
}

export enum Severity {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL"
}

export enum ClauseType {
  PRICING = "pricing",
  PAYMENT_TERMS = "payment_terms",
  RENEWAL = "renewal",
  TERMINATION = "termination",
  // ... 13 total types
}

export enum LeakageCategory {
  PRICING = "pricing",
  PAYMENT = "payment",
  RENEWAL = "renewal",
  // ... 10 total categories
}

export enum DetectionMethod {
  RULE = "RULE",
  AI = "AI",
  HYBRID = "HYBRID"
}
```

---

### Data Models

#### Contract

```typescript
export interface Contract {
  id: string;
  contract_id: string;           // Partition key
  contract_name: string;
  uploaded_by: string;
  upload_date: string;            // ISO 8601 datetime
  file_path: string;
  status: ContractStatus;
  metadata: ContractMetadata;
  created_at: string;
  updated_at: string;
}

export interface ContractMetadata {
  file_type?: string;
  file_size?: number;
  contract_value?: number;
  currency?: string;
  start_date?: string;
  end_date?: string;
  auto_renewal?: boolean;
  counterparty_name?: string;
  custom_fields?: Record<string, any>;
}
```

#### Clause

```typescript
export interface Clause {
  id: string;
  contract_id: string;           // Partition key
  clause_type: ClauseType;
  section_number?: string;
  original_text: string;
  normalized_summary: string;    // Optimized for AI/RAG
  entities: ExtractedEntities;
  risk_signals: string[];
  confidence_score: number;      // 0.0 to 1.0
  embedding?: number[];          // 3072-dim vector (optional)
  created_at: string;
}

export interface ExtractedEntities {
  dates?: string[];
  monetary_values?: MonetaryValue[];
  percentages?: string[];
  parties?: string[];
  obligations?: string[];
  conditions?: string[];
  deadlines?: string[];
}
```

#### LeakageFinding

```typescript
export interface LeakageFinding {
  id: string;
  contract_id: string;           // Partition key
  finding_id: string;
  category: LeakageCategory;
  severity: Severity;
  risk_type: string;
  explanation: string;
  recommended_action: string;
  affected_clause_ids: string[];
  confidence_score: number;
  detection_method: DetectionMethod;
  rule_id?: string;
  estimated_financial_impact?: FinancialImpact;
  assumptions?: string[];
  created_at: string;
}

export interface FinancialImpact {
  amount: number;
  currency: string;
  calculation_method?: string;
  notes?: string;
}
```

#### AnalysisSession

```typescript
export interface AnalysisSession {
  id: string;
  contract_id: string;
  session_id: string;
  status: SessionStatus;
  start_time: string;
  end_time?: string;
  total_findings: number;
  findings_by_severity: FindingsBySeverity;
  processing_steps: ProcessingStep[];
  error_message?: string;
  created_at: string;
}
```

---

### API Request Types

Request interfaces for all 6 endpoints:

```typescript
// POST /api/upload_contract
export interface UploadContractRequest {
  contract_name: string;
  uploaded_by: string;
  file: File | Blob;
  metadata?: ContractMetadata;
}

// POST /api/analyze_contract
export interface AnalyzeContractRequest {
  contract_id: string;
}

// GET /api/get_clauses/:contract_id
export interface GetClausesRequest {
  contract_id: string;
  clause_type?: string;      // Optional filter
  limit?: number;            // Pagination
  offset?: number;
}

// GET /api/get_findings/:contract_id
export interface GetFindingsRequest {
  contract_id: string;
  severity?: string;         // Optional filter
  category?: string;
  limit?: number;
  offset?: number;
}

// GET /api/export_report/:contract_id
export interface ExportReportRequest {
  contract_id: string;
  format?: 'pdf' | 'excel';
  include_clauses?: boolean;
}
```

---

### API Response Types

Response interfaces matching backend JSON responses:

```typescript
// Generic error response
export interface ApiErrorResponse {
  error: string;
  details?: string;
  status_code: number;
}

// POST /api/upload_contract
export interface UploadContractResponse {
  message: string;
  contract_id: string;
  contract_name: string;
  file_path: string;
  status: string;
}

// POST /api/analyze_contract
export interface AnalyzeContractResponse {
  message: string;
  contract_id: string;
  session_id: string;
  total_clauses_extracted: number;
  total_findings: number;
  findings_by_severity: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  processing_time_seconds: number;
}

// GET /api/get_findings/:contract_id
export interface GetFindingsResponse {
  contract_id: string;
  findings: LeakageFinding[];
  total_count: number;
  summary: {
    total_findings: number;
    by_severity: {...};
    by_category: Record<string, number>;
    total_estimated_impact?: {
      amount: number;
      currency: string;
    };
  };
  limit?: number;
  offset?: number;
}

// Helper types
export interface PaginatedResponse<T> {
  data: T[];
  total_count: number;
  limit: number;
  offset: number;
  has_more: boolean;
}
```

---

## Type Mapping: Python → TypeScript

| Python Type | TypeScript Type | Notes |
|-------------|----------------|-------|
| `str` | `string` | |
| `int` | `number` | |
| `float` | `number` | |
| `bool` | `boolean` | |
| `datetime` | `string` | ISO 8601 format |
| `List[T]` | `T[]` | |
| `Dict[str, Any]` | `Record<string, any>` | |
| `Optional[T]` | `T?` | Optional property |
| `Union[A, B]` | `A \| B` | Union type |
| `Enum` | `enum` | String enum |

---

## Installation & Usage

### Build the Package

```bash
cd shared-types
npm install
npm run build
```

This compiles TypeScript to JavaScript and generates `.d.ts` declaration files in `dist/`.

### Install in Frontend

```bash
cd ../contract-leakage-engine-frontend
npm install ../contract-leakage-engine-backend/shared-types
```

Or for development with live updates:

```bash
cd shared-types
npm link

cd ../contract-leakage-engine-frontend
npm link @contract-leakage/shared-types
```

### Import in Frontend Code

```typescript
import {
  Contract,
  Clause,
  LeakageFinding,
  ContractStatus,
  Severity,
  GetFindingsResponse,
  AnalyzeContractRequest
} from '@contract-leakage/shared-types';

// Type-safe contract display
const contract: Contract = await fetchContract(contractId);
console.log(contract.contract_name, contract.status);

// Type-safe API calls
async function getFindings(contractId: string): Promise<GetFindingsResponse> {
  const response = await fetch(`/api/get_findings/${contractId}`);
  if (!response.ok) {
    const error: ApiErrorResponse = await response.json();
    throw new Error(error.error);
  }
  return response.json();
}

// Type-safe component props
interface FindingCardProps {
  finding: LeakageFinding;
  onSelect: (id: string) => void;
}

const FindingCard: React.FC<FindingCardProps> = ({ finding, onSelect }) => {
  // TypeScript knows all properties of finding
  return (
    <div className={`severity-${finding.severity.toLowerCase()}`}>
      <h3>{finding.risk_type}</h3>
      <p>{finding.explanation}</p>
      <span className="confidence">{(finding.confidence_score * 100).toFixed(0)}%</span>
    </div>
  );
};
```

---

## Development Workflow

### Watch Mode

For active development, run the build in watch mode:

```bash
cd shared-types
npm run build:watch
```

Changes will automatically recompile.

### Clean Build

```bash
npm run clean
npm run build
```

---

## Benefits

### 1. Type Safety
- Catch type errors at compile time, not runtime
- IntelliSense autocomplete in VS Code
- Refactoring support (rename symbols across files)

### 2. Consistency
- Single source of truth for data structures
- Frontend and backend stay in sync
- API contract is explicit and enforced

### 3. Developer Experience
- Clear API documentation through types
- Reduced bugs from typos or wrong property names
- Faster development with autocomplete

### 4. Maintainability
- Changes to backend models propagate to frontend
- Breaking changes caught by TypeScript compiler
- Self-documenting code

---

## Example Usage in Frontend Components

### Upload Component

```typescript
import { UploadContractRequest, UploadContractResponse } from '@contract-leakage/shared-types';

async function uploadContract(file: File, name: string, user: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('contract_name', name);
  formData.append('uploaded_by', user);

  const response = await fetch('/api/upload_contract', {
    method: 'POST',
    body: formData
  });

  const result: UploadContractResponse = await response.json();
  return result.contract_id;
}
```

### Findings List Component

```typescript
import {
  GetFindingsResponse,
  LeakageFinding,
  Severity
} from '@contract-leakage/shared-types';

function FindingsList({ contractId }: { contractId: string }) {
  const [data, setData] = useState<GetFindingsResponse | null>(null);

  useEffect(() => {
    fetch(`/api/get_findings/${contractId}`)
      .then(res => res.json())
      .then((data: GetFindingsResponse) => setData(data));
  }, [contractId]);

  return (
    <div>
      <h2>Findings: {data?.summary.total_findings}</h2>
      {data?.findings.map((finding: LeakageFinding) => (
        <FindingCard key={finding.id} finding={finding} />
      ))}
    </div>
  );
}
```

### Severity Badge Component

```typescript
import { Severity } from '@contract-leakage/shared-types';

const severityColors: Record<Severity, string> = {
  [Severity.CRITICAL]: '#d32f2f',
  [Severity.HIGH]: '#f57c00',
  [Severity.MEDIUM]: '#fbc02d',
  [Severity.LOW]: '#388e3c'
};

function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      style={{
        backgroundColor: severityColors[severity],
        color: 'white',
        padding: '4px 8px',
        borderRadius: '4px'
      }}
    >
      {severity}
    </span>
  );
}
```

---

## Version Compatibility

- **Package Version**: 1.0.0
- **Backend Version**: Contract Leakage Engine v1.0
- **TypeScript**: ^5.3.3
- **Target**: ES2020

---

## Future Enhancements

1. **Validation**: Add `class-validator` decorators for runtime validation
2. **Serialization**: Add JSON serialization/deserialization utilities
3. **API Client**: Add typed API client factory functions
4. **Mock Data**: Add mock data generators for testing
5. **OpenAPI**: Generate OpenAPI schema from types
6. **GraphQL**: Add GraphQL schema generation

---

## Summary

**What Was Created:**
- ✅ Complete TypeScript type definitions matching Python models
- ✅ API request/response types for all 6 endpoints
- ✅ Enum definitions (ContractStatus, Severity, ClauseType, etc.)
- ✅ Comprehensive documentation and usage examples
- ✅ NPM package configuration with build scripts
- ✅ TypeScript compiler configuration

**Impact:**
- **Type Safety**: Frontend development with full IntelliSense and type checking
- **Consistency**: Single source of truth for data structures
- **Developer Experience**: Faster development with autocomplete and error detection
- **Maintainability**: Refactoring and breaking changes caught at compile time

**Status**: Task 13 complete! Shared TypeScript types package ready for frontend integration.
