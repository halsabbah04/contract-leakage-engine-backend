# Contract Leakage Engine - Shared Types

TypeScript type definitions for the Contract Leakage Engine, matching the Python Pydantic models and API structures.

## Overview

This package provides strongly-typed interfaces for:
- **Data Models**: Contract, Clause, LeakageFinding, AnalysisSession
- **Enums**: ContractStatus, ClauseType, Severity, LeakageCategory, DetectionMethod
- **API Types**: Request and response interfaces for all endpoints

## Installation

### Local Development

```bash
cd shared-types
npm install
npm run build
```

### Using in Frontend

```bash
cd ../contract-leakage-engine-frontend
npm install ../contract-leakage-engine-backend/shared-types
```

Or link for development:

```bash
cd shared-types
npm link

cd ../contract-leakage-engine-frontend
npm link @contract-leakage/shared-types
```

## Usage

```typescript
import {
  Contract,
  Clause,
  LeakageFinding,
  ContractStatus,
  Severity,
  GetFindingsResponse
} from '@contract-leakage/shared-types';

// Use types in your frontend components
const contract: Contract = {
  id: '123',
  contract_id: 'contract_abc',
  contract_name: 'Master Services Agreement',
  status: ContractStatus.ANALYZED,
  // ...
};

// Type-safe API calls
async function getFindings(contractId: string): Promise<GetFindingsResponse> {
  const response = await fetch(`/api/get_findings/${contractId}`);
  return response.json() as Promise<GetFindingsResponse>;
}
```

## Structure

```
shared-types/
├── src/
│   ├── enums/
│   │   └── index.ts          # All enums (ContractStatus, Severity, etc.)
│   ├── models/
│   │   ├── contract.ts       # Contract and ContractMetadata
│   │   ├── clause.ts         # Clause and ExtractedEntities
│   │   ├── finding.ts        # LeakageFinding and FinancialImpact
│   │   └── session.ts        # AnalysisSession
│   ├── api/
│   │   ├── requests.ts       # API request types
│   │   └── responses.ts      # API response types
│   └── index.ts              # Main export file
├── package.json
├── tsconfig.json
└── README.md
```

## Type Mapping

### Python → TypeScript

| Python | TypeScript | Notes |
|--------|-----------|-------|
| `str` | `string` | |
| `int` | `number` | |
| `float` | `number` | |
| `bool` | `boolean` | |
| `datetime` | `string` | ISO 8601 format |
| `List[T]` | `T[]` | |
| `Dict[str, Any]` | `Record<string, any>` | |
| `Optional[T]` | `T \| undefined` | Optional properties |
| `Enum` | `enum` | String enums |

### Data Models

All TypeScript interfaces match the Python Pydantic models exactly:

- **Contract** (`shared/models/contract.py`)
- **Clause** (`shared/models/clause.py`)
- **LeakageFinding** (`shared/models/finding.py`)
- **AnalysisSession** (`shared/models/session.py`)

### API Endpoints

Request and response types for all 6 API endpoints:

1. `POST /api/upload_contract` - Upload contract file
2. `POST /api/analyze_contract` - Trigger analysis
3. `GET /api/get_contract/:contract_id` - Get contract details
4. `GET /api/get_clauses/:contract_id` - Get extracted clauses
5. `GET /api/get_findings/:contract_id` - Get leakage findings
6. `GET /api/export_report/:contract_id` - Export PDF/Excel report

## Development

### Build

```bash
npm run build
```

Compiles TypeScript to JavaScript and generates `.d.ts` declaration files in `dist/`.

### Watch Mode

```bash
npm run build:watch
```

Automatically rebuilds on file changes.

### Clean

```bash
npm run clean
```

Removes the `dist/` directory.

## Version

- **Version**: 1.0.0
- **Compatible with Backend**: Contract Leakage Engine Python Backend v1.0

## Notes

- All datetime fields are represented as ISO 8601 strings (`YYYY-MM-DDTHH:MM:SSZ`)
- Optional fields are marked with `?` in TypeScript interfaces
- Embedding vectors (3072-dim) are optional in frontend responses to reduce payload size
- Currency amounts use `number` type; format on display (e.g., using `Intl.NumberFormat`)

## Future Enhancements

- Add validation decorators (e.g., using `class-validator`)
- Add serialization/deserialization utilities
- Add API client factory functions
- Add mock data generators for testing
