# Contract Intelligence Platform - Implementation Plan

## Overview

This document provides detailed implementation plans for each phase of the Contract Intelligence Platform development.

---

# Phase 2: Intelligence Agents

**Goal:** Add internal analysis capabilities that work with existing contract data.

**Duration Estimate:** 4-6 weeks
**Dependencies:** Phase 1 (Complete)

---

## 2.1 Obligation Extraction Agent

### Purpose
Extract and track contractual obligations, deadlines, and commitments from analyzed contracts.

### Data Model

```python
# shared/models/obligation.py

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ObligationType(str, Enum):
    """Types of contractual obligations."""
    PAYMENT = "payment"
    DELIVERY = "delivery"
    NOTICE = "notice"
    REPORTING = "reporting"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    INSURANCE = "insurance"
    OTHER = "other"


class ObligationStatus(str, Enum):
    """Status of an obligation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class ObligationPriority(str, Enum):
    """Priority level of an obligation."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Obligation(BaseModel):
    """
    Extracted contractual obligation.

    Cosmos DB Container: obligations
    Partition Key: contract_id
    """
    id: str = Field(..., description="Unique obligation identifier")
    contract_id: str = Field(..., description="Parent contract ID")
    partition_key: str = Field(..., description="Cosmos DB partition key")

    # Obligation details
    obligation_type: ObligationType
    title: str = Field(..., description="Short title of the obligation")
    description: str = Field(..., description="Full description from contract")
    source_clause_id: Optional[str] = Field(None, description="Clause this was extracted from")
    source_text: Optional[str] = Field(None, description="Original text snippet")

    # Responsible parties
    obligor: str = Field(..., description="Party responsible (us/counterparty)")
    obligee: str = Field(..., description="Party receiving benefit")

    # Timing
    due_date: Optional[datetime] = Field(None, description="When obligation is due")
    recurrence: Optional[str] = Field(None, description="Recurrence pattern (monthly, quarterly, etc.)")
    reminder_days_before: int = Field(default=30, description="Days before due date to remind")

    # Financial
    amount: Optional[float] = Field(None, description="Financial amount if applicable")
    currency: str = Field(default="USD", description="Currency code")

    # Status tracking
    status: ObligationStatus = Field(default=ObligationStatus.PENDING)
    priority: ObligationPriority = Field(default=ObligationPriority.MEDIUM)
    assigned_to: Optional[str] = Field(None, description="User assigned to track this")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_confidence: float = Field(default=0.0, description="AI confidence score")
    manually_verified: bool = Field(default=False)
    notes: Optional[str] = Field(None)


class ObligationCalendarEvent(BaseModel):
    """Calendar event representation for an obligation."""
    obligation_id: str
    title: str
    description: str
    start_date: datetime
    end_date: Optional[datetime]
    reminder_date: datetime
    calendar_type: str = "outlook"  # outlook, google, ical
```

### Service Implementation

```python
# shared/services/obligation_service.py

class ObligationExtractionService:
    """
    Extracts and manages contractual obligations.
    """

    def __init__(self):
        self.openai_client = get_openai_client()
        self.obligation_repo = ObligationRepository()
        self.clause_repo = ClauseRepository()

    async def extract_obligations(
        self,
        contract_id: str,
        contract_metadata: dict
    ) -> List[Obligation]:
        """
        Extract all obligations from a contract's clauses.

        Process:
        1. Get all clauses for the contract
        2. Filter to obligation-relevant clause types
        3. Use GPT to extract structured obligations
        4. Deduplicate and validate
        5. Store in database
        """
        pass

    async def _extract_from_clause(
        self,
        clause: Clause,
        contract_metadata: dict
    ) -> List[Obligation]:
        """Extract obligations from a single clause using GPT."""
        pass

    def get_upcoming_obligations(
        self,
        contract_id: str,
        days_ahead: int = 90
    ) -> List[Obligation]:
        """Get obligations due within specified days."""
        pass

    def get_overdue_obligations(
        self,
        contract_id: str
    ) -> List[Obligation]:
        """Get all overdue obligations."""
        pass

    def update_obligation_status(
        self,
        obligation_id: str,
        status: ObligationStatus,
        notes: Optional[str] = None
    ) -> Obligation:
        """Update the status of an obligation."""
        pass

    def generate_calendar_events(
        self,
        contract_id: str,
        format: str = "ical"
    ) -> str:
        """Generate calendar file for obligations."""
        pass
```

### API Endpoints

```python
# api/obligations/__init__.py

# POST /api/obligations/{contract_id}/extract
# Trigger obligation extraction for a contract

# GET /api/obligations/{contract_id}
# Get all obligations for a contract
# Query params: type, status, due_before, due_after

# GET /api/obligations/{contract_id}/upcoming
# Get upcoming obligations (next 90 days by default)

# GET /api/obligations/{contract_id}/overdue
# Get overdue obligations

# PUT /api/obligations/{obligation_id}
# Update an obligation (status, assigned_to, notes)

# GET /api/obligations/{contract_id}/calendar
# Download calendar file (ICS format)
```

### Frontend Components

```typescript
// src/components/obligations/ObligationList.tsx
// - List view of all obligations with filters
// - Status badges and due date indicators
// - Quick status update actions

// src/components/obligations/ObligationCalendar.tsx
// - Calendar view of obligations
// - Color-coded by type/priority
// - Click to view details

// src/components/obligations/ObligationTimeline.tsx
// - Timeline view showing upcoming deadlines
// - Visual indicators for urgency

// src/pages/ObligationsPage.tsx
// - Main obligations dashboard
// - Summary statistics
// - Export to calendar button
```

### Implementation Tasks

```
[ ] 1. Create Obligation data model (shared/models/obligation.py)
[ ] 2. Create ObligationRepository (shared/db/repositories/obligation_repository.py)
[ ] 3. Create Cosmos DB container 'obligations'
[ ] 4. Implement ObligationExtractionService
[ ] 5. Create GPT prompt for obligation extraction
[ ] 6. Implement API endpoints (extract, list, update, calendar)
[ ] 7. Add routes to function_app.py
[ ] 8. Create TypeScript types (shared-types)
[ ] 9. Implement frontend ObligationList component
[ ] 10. Implement ObligationCalendar component
[ ] 11. Create ObligationsPage
[ ] 12. Add obligations tab to ContractDetailPage
[ ] 13. Implement ICS calendar export
[ ] 14. Write unit tests
[ ] 15. Integration testing
```

---

## 2.2 Contract Comparison Agent

### Purpose
Compare contracts against each other, templates, or previous versions to identify deviations.

### Data Model

```python
# shared/models/comparison.py

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class ComparisonType(str, Enum):
    """Types of contract comparisons."""
    VERSION = "version"           # Current vs previous version
    TEMPLATE = "template"         # Contract vs master template
    VENDOR = "vendor"             # Vendor A vs Vendor B
    HISTORICAL = "historical"     # New vs previously negotiated


class ChangeType(str, Enum):
    """Type of change detected."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class ChangeSeverity(str, Enum):
    """Severity/importance of the change."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"


class ClauseChange(BaseModel):
    """A single clause-level change."""
    clause_type: str
    change_type: ChangeType
    severity: ChangeSeverity

    # Source content
    source_text: Optional[str] = Field(None, description="Text from source contract")
    target_text: Optional[str] = Field(None, description="Text from target contract")

    # Analysis
    summary: str = Field(..., description="Human-readable summary of change")
    risk_implication: Optional[str] = Field(None, description="What this change means for risk")
    recommendation: Optional[str] = Field(None, description="Suggested action")


class TermComparison(BaseModel):
    """Comparison of a specific contract term."""
    term_name: str
    source_value: Optional[str]
    target_value: Optional[str]
    difference: str
    favors: str = Field(..., description="us/counterparty/neutral")


class ContractComparison(BaseModel):
    """
    Full comparison between two contracts.

    Cosmos DB Container: contract_comparisons
    Partition Key: source_contract_id
    """
    id: str = Field(..., description="Unique comparison identifier")
    partition_key: str

    # Contracts being compared
    comparison_type: ComparisonType
    source_contract_id: str = Field(..., description="Base/original contract")
    target_contract_id: str = Field(..., description="Contract being compared to")
    source_contract_name: str
    target_contract_name: str

    # Results
    clause_changes: List[ClauseChange] = Field(default_factory=list)
    term_comparisons: List[TermComparison] = Field(default_factory=list)

    # Summary statistics
    total_clauses_compared: int = 0
    clauses_added: int = 0
    clauses_removed: int = 0
    clauses_modified: int = 0
    critical_changes: int = 0
    major_changes: int = 0

    # Overall assessment
    overall_risk_change: str = Field(..., description="increased/decreased/unchanged")
    executive_summary: str = Field(..., description="AI-generated summary")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
```

### Service Implementation

```python
# shared/services/comparison_service.py

class ContractComparisonService:
    """
    Compares contracts and identifies differences.
    """

    def __init__(self):
        self.openai_client = get_openai_client()
        self.comparison_repo = ComparisonRepository()
        self.clause_repo = ClauseRepository()
        self.embedding_service = EmbeddingService()

    async def compare_contracts(
        self,
        source_contract_id: str,
        target_contract_id: str,
        comparison_type: ComparisonType
    ) -> ContractComparison:
        """
        Compare two contracts and generate detailed diff.

        Process:
        1. Load clauses from both contracts
        2. Match clauses by type and semantic similarity
        3. Generate detailed diff for each matched pair
        4. Identify added/removed clauses
        5. Analyze risk implications
        6. Generate executive summary
        """
        pass

    async def compare_to_template(
        self,
        contract_id: str,
        template_id: str
    ) -> ContractComparison:
        """Compare a contract against a master template."""
        pass

    async def _match_clauses(
        self,
        source_clauses: List[Clause],
        target_clauses: List[Clause]
    ) -> List[tuple]:
        """Match clauses between contracts using embeddings."""
        pass

    async def _analyze_clause_change(
        self,
        source_clause: Optional[Clause],
        target_clause: Optional[Clause]
    ) -> ClauseChange:
        """Analyze the difference between two clauses."""
        pass

    def _extract_key_terms(
        self,
        clauses: List[Clause]
    ) -> Dict[str, str]:
        """Extract key terms (liability cap, notice period, etc.)."""
        pass
```

### API Endpoints

```python
# POST /api/compare
# Body: { source_contract_id, target_contract_id, comparison_type }
# Returns: comparison_id

# GET /api/compare/{comparison_id}
# Get comparison results

# GET /api/compare/contract/{contract_id}
# List all comparisons involving a contract

# GET /api/templates
# List available master templates for comparison
```

### Frontend Components

```typescript
// src/components/comparison/ComparisonSelector.tsx
// - Select two contracts to compare
// - Choose comparison type

// src/components/comparison/DiffViewer.tsx
// - Side-by-side diff view
// - Highlighted changes
// - Expandable clause details

// src/components/comparison/TermComparisonTable.tsx
// - Table comparing key terms
// - Visual indicators for favorable/unfavorable

// src/components/comparison/ComparisonSummary.tsx
// - Executive summary
// - Change statistics
// - Risk delta visualization

// src/pages/ComparisonPage.tsx
// - Main comparison interface
```

### Implementation Tasks

```
[ ] 1. Create Comparison data models
[ ] 2. Create ComparisonRepository
[ ] 3. Create Cosmos DB container 'contract_comparisons'
[ ] 4. Implement clause matching using embeddings
[ ] 5. Implement ContractComparisonService
[ ] 6. Create GPT prompts for change analysis
[ ] 7. Implement API endpoints
[ ] 8. Add routes to function_app.py
[ ] 9. Create TypeScript types
[ ] 10. Implement DiffViewer component
[ ] 11. Implement TermComparisonTable
[ ] 12. Create ComparisonPage
[ ] 13. Add "Compare" button to contract list
[ ] 14. Write unit tests
[ ] 15. Integration testing
```

---

## 2.3 Benchmark Agent

### Purpose
Compare contract terms against industry standards and internal historical data.

### Data Model

```python
# shared/models/benchmark.py

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class BenchmarkSource(str, Enum):
    """Source of benchmark data."""
    INTERNAL = "internal"        # From our contract database
    INDUSTRY = "industry"        # Industry-wide standards
    MARKET = "market"            # Current market rates


class BenchmarkCategory(str, Enum):
    """Category of benchmark."""
    PAYMENT_TERMS = "payment_terms"
    LIABILITY = "liability"
    TERMINATION = "termination"
    SLA = "sla"
    PRICING = "pricing"
    INDEMNIFICATION = "indemnification"
    INSURANCE = "insurance"
    NOTICE_PERIODS = "notice_periods"


class DeviationDirection(str, Enum):
    """Direction of deviation from benchmark."""
    ABOVE = "above"              # Better than benchmark
    BELOW = "below"              # Worse than benchmark
    AT = "at"                    # At benchmark


class TermBenchmark(BaseModel):
    """Benchmark comparison for a single term."""
    term_name: str
    category: BenchmarkCategory

    # Contract value
    contract_value: str
    contract_value_numeric: Optional[float] = None

    # Benchmark values
    benchmark_value: str
    benchmark_value_numeric: Optional[float] = None
    benchmark_source: BenchmarkSource
    benchmark_percentile: Optional[int] = Field(None, description="Where this falls in distribution")

    # Analysis
    deviation: DeviationDirection
    deviation_percent: Optional[float] = None
    risk_assessment: str = Field(..., description="How this deviation affects risk")
    recommendation: Optional[str] = None


class BenchmarkAnalysis(BaseModel):
    """
    Full benchmark analysis for a contract.

    Cosmos DB Container: benchmarks
    Partition Key: contract_id
    """
    id: str
    contract_id: str
    partition_key: str

    # Analysis results
    term_benchmarks: List[TermBenchmark] = Field(default_factory=list)

    # Summary
    terms_above_benchmark: int = 0
    terms_below_benchmark: int = 0
    terms_at_benchmark: int = 0
    overall_position: str = Field(..., description="favorable/unfavorable/neutral")

    # Key findings
    favorable_terms: List[str] = Field(default_factory=list)
    unfavorable_terms: List[str] = Field(default_factory=list)
    negotiation_opportunities: List[str] = Field(default_factory=list)

    # Context
    industry: Optional[str] = None
    contract_type: Optional[str] = None
    region: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    benchmark_data_date: datetime = Field(default_factory=datetime.utcnow)


# Benchmark reference data (can be stored in config or database)
class BenchmarkReference(BaseModel):
    """Reference data for benchmarks."""
    category: BenchmarkCategory
    term_name: str
    industry: Optional[str] = None
    region: Optional[str] = None

    # Statistical values
    p25: float  # 25th percentile
    p50: float  # Median
    p75: float  # 75th percentile
    mean: float

    # Human-readable
    typical_range: str
    notes: Optional[str] = None

    last_updated: datetime
```

### Benchmark Reference Data

```yaml
# data/benchmark_references.yaml

payment_terms:
  net_payment_days:
    industry_default:
      p25: 30
      p50: 45
      p75: 60
      typical_range: "Net 30 to Net 60"
    technology:
      p25: 30
      p50: 30
      p75: 45
      typical_range: "Net 30 to Net 45"
    manufacturing:
      p25: 45
      p50: 60
      p75: 90
      typical_range: "Net 45 to Net 90"

liability:
  liability_cap_multiplier:
    industry_default:
      p25: 1.0
      p50: 1.5
      p75: 2.0
      typical_range: "1x to 2x annual contract value"
    notes: "Expressed as multiple of annual contract value"

  unlimited_liability_acceptable:
    industry_default:
      typical_range: "IP infringement, gross negligence, confidentiality breach"
      notes: "Carve-outs where unlimited liability is market standard"

termination:
  notice_period_days:
    industry_default:
      p25: 30
      p50: 60
      p75: 90
      typical_range: "30 to 90 days"

  termination_for_convenience:
    industry_default:
      typical_range: "Standard with 30-90 days notice"
      notes: "Usually mutual"

sla:
  uptime_percentage:
    saas:
      p25: 99.5
      p50: 99.9
      p75: 99.95
      typical_range: "99.5% to 99.99%"
    infrastructure:
      p25: 99.9
      p50: 99.95
      p75: 99.99
      typical_range: "99.9% to 99.99%"

  response_time_hours:
    critical_issues:
      p25: 1
      p50: 4
      p75: 8
      typical_range: "1 to 8 hours for critical issues"

pricing:
  annual_escalation_percent:
    industry_default:
      p25: 2.0
      p50: 3.0
      p75: 5.0
      typical_range: "CPI to CPI+3%"
```

### Service Implementation

```python
# shared/services/benchmark_service.py

class BenchmarkService:
    """
    Compares contract terms against industry benchmarks.
    """

    def __init__(self):
        self.openai_client = get_openai_client()
        self.benchmark_repo = BenchmarkRepository()
        self.clause_repo = ClauseRepository()
        self.benchmark_data = self._load_benchmark_references()

    async def analyze_benchmarks(
        self,
        contract_id: str,
        industry: Optional[str] = None,
        region: Optional[str] = None
    ) -> BenchmarkAnalysis:
        """
        Compare contract terms against benchmarks.

        Process:
        1. Extract key terms from contract clauses
        2. Load relevant benchmark data
        3. Compare each term against benchmarks
        4. Calculate deviations and percentiles
        5. Generate recommendations
        """
        pass

    async def _extract_contract_terms(
        self,
        contract_id: str
    ) -> Dict[str, any]:
        """Extract quantifiable terms from contract."""
        pass

    def _compare_term(
        self,
        term_name: str,
        term_value: any,
        category: BenchmarkCategory,
        industry: str
    ) -> TermBenchmark:
        """Compare a single term against benchmark."""
        pass

    def _calculate_percentile(
        self,
        value: float,
        benchmark: BenchmarkReference
    ) -> int:
        """Calculate where value falls in benchmark distribution."""
        pass

    def get_industry_benchmarks(
        self,
        industry: str,
        category: Optional[BenchmarkCategory] = None
    ) -> List[BenchmarkReference]:
        """Get benchmark reference data for an industry."""
        pass
```

### API Endpoints

```python
# POST /api/benchmark/{contract_id}
# Trigger benchmark analysis
# Query params: industry, region

# GET /api/benchmark/{contract_id}
# Get benchmark analysis results

# GET /api/benchmark/references
# Get available benchmark reference data
# Query params: industry, category
```

### Frontend Components

```typescript
// src/components/benchmark/BenchmarkGauge.tsx
// - Visual gauge showing where term falls vs benchmark
// - Color-coded (green=favorable, red=unfavorable)

// src/components/benchmark/BenchmarkTable.tsx
// - Table of all term comparisons
// - Sortable by deviation, category

// src/components/benchmark/BenchmarkSummary.tsx
// - Overall benchmark position
// - Key negotiation opportunities

// src/pages/BenchmarkPage.tsx
// - Full benchmark analysis view
```

### Implementation Tasks

```
[ ] 1. Create Benchmark data models
[ ] 2. Create benchmark reference data (YAML)
[ ] 3. Create BenchmarkRepository
[ ] 4. Create Cosmos DB container 'benchmarks'
[ ] 5. Implement term extraction from clauses
[ ] 6. Implement BenchmarkService
[ ] 7. Implement percentile calculations
[ ] 8. Create API endpoints
[ ] 9. Add routes to function_app.py
[ ] 10. Create TypeScript types
[ ] 11. Implement BenchmarkGauge component
[ ] 12. Implement BenchmarkTable component
[ ] 13. Create BenchmarkPage
[ ] 14. Add benchmark tab to ContractDetailPage
[ ] 15. Write unit tests
```

---

## 2.4 Compliance & Regulatory Agent

### Purpose
Check contracts against regulatory requirements and internal compliance policies.

### Data Model

```python
# shared/models/compliance.py

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ComplianceFramework(str, Enum):
    """Regulatory frameworks."""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    SOX = "sox"
    FCPA = "fcpa"
    UK_BRIBERY = "uk_bribery"
    MODERN_SLAVERY = "modern_slavery"
    EXPORT_CONTROL = "export_control"
    SANCTIONS = "sanctions"
    INTERNAL_POLICY = "internal_policy"


class ComplianceStatus(str, Enum):
    """Status of a compliance check."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"
    REQUIRES_REVIEW = "requires_review"


class ComplianceSeverity(str, Enum):
    """Severity of non-compliance."""
    CRITICAL = "critical"     # Legal/regulatory violation risk
    HIGH = "high"             # Significant policy breach
    MEDIUM = "medium"         # Policy deviation
    LOW = "low"               # Minor gap
    INFO = "info"             # Informational


class ComplianceCheck(BaseModel):
    """Individual compliance check result."""
    check_id: str
    framework: ComplianceFramework
    requirement_name: str
    requirement_description: str

    # Result
    status: ComplianceStatus
    severity: ComplianceSeverity

    # Details
    finding: str = Field(..., description="What was found/not found")
    evidence: Optional[str] = Field(None, description="Clause text supporting the finding")
    clause_id: Optional[str] = None

    # Remediation
    recommendation: str
    suggested_clause: Optional[str] = Field(None, description="Suggested language to add")

    # Metadata
    automated: bool = True
    requires_legal_review: bool = False


class ComplianceAnalysis(BaseModel):
    """
    Full compliance analysis for a contract.

    Cosmos DB Container: compliance_checks
    Partition Key: contract_id
    """
    id: str
    contract_id: str
    partition_key: str

    # Frameworks checked
    frameworks_analyzed: List[ComplianceFramework]

    # Results
    checks: List[ComplianceCheck] = Field(default_factory=list)

    # Summary
    total_checks: int = 0
    compliant: int = 0
    non_compliant: int = 0
    partial: int = 0
    requires_review: int = 0

    # By severity
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0

    # Overall
    overall_compliance_score: float = Field(..., description="0-100 score")
    overall_status: ComplianceStatus

    # Flags
    requires_legal_review: bool = False
    requires_dpa: bool = False  # Data Processing Agreement
    involves_pii: bool = False  # Personal Identifiable Information
    cross_border_data: bool = False

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    jurisdiction: Optional[str] = None
```

### Compliance Rules Configuration

```yaml
# rules/compliance_rules.yaml

gdpr:
  - id: GDPR_DPA_REQUIRED
    name: "Data Processing Agreement Required"
    description: "Contracts involving EU personal data require a DPA"
    severity: critical
    check_type: clause_presence
    required_clause_types: [data_protection]
    keywords: ["data processing agreement", "DPA", "Article 28"]
    trigger_conditions:
      - involves_eu_data: true
      - processes_personal_data: true

  - id: GDPR_DATA_TRANSFER
    name: "Cross-Border Data Transfer Mechanism"
    description: "Data transfers outside EU require appropriate safeguards"
    severity: critical
    check_type: clause_presence
    keywords: ["standard contractual clauses", "SCC", "adequacy decision", "BCR"]
    trigger_conditions:
      - data_transfer_outside_eu: true

  - id: GDPR_SUBPROCESSOR
    name: "Sub-processor Requirements"
    description: "Contract should specify sub-processor approval process"
    severity: high
    check_type: clause_presence
    keywords: ["sub-processor", "subcontractor", "prior authorization"]

hipaa:
  - id: HIPAA_BAA_REQUIRED
    name: "Business Associate Agreement Required"
    description: "Contracts involving PHI require a BAA"
    severity: critical
    check_type: clause_presence
    required_clause_types: [data_protection]
    keywords: ["business associate", "BAA", "protected health information", "PHI"]
    trigger_conditions:
      - involves_phi: true

  - id: HIPAA_BREACH_NOTIFICATION
    name: "Breach Notification Requirements"
    description: "BAA must include breach notification procedures"
    severity: high
    check_type: keyword_presence
    keywords: ["breach notification", "security incident", "notify within"]

pci_dss:
  - id: PCI_COMPLIANCE_ATTESTATION
    name: "PCI DSS Compliance Attestation"
    description: "Vendor handling card data must attest PCI compliance"
    severity: critical
    check_type: clause_presence
    keywords: ["PCI DSS", "payment card industry", "AOC", "attestation of compliance"]
    trigger_conditions:
      - handles_payment_cards: true

anti_corruption:
  - id: FCPA_ANTI_BRIBERY
    name: "Anti-Bribery Clause"
    description: "Contract should include anti-bribery provisions"
    severity: high
    check_type: clause_presence
    keywords: ["anti-bribery", "anti-corruption", "FCPA", "foreign officials"]

  - id: FCPA_AUDIT_RIGHTS
    name: "Audit Rights for Compliance"
    description: "Should have right to audit for compliance"
    severity: medium
    check_type: clause_presence
    keywords: ["audit rights", "inspect records", "compliance audit"]

internal_policy:
  - id: INTERNAL_INSURANCE_REQUIRED
    name: "Insurance Requirements"
    description: "Vendor contracts over $100K require insurance provisions"
    severity: medium
    check_type: clause_presence
    required_clause_types: [insurance]
    keywords: ["insurance", "liability insurance", "errors and omissions"]
    trigger_conditions:
      - contract_value_over: 100000
```

### Service Implementation

```python
# shared/services/compliance_service.py

class ComplianceService:
    """
    Checks contracts against regulatory requirements.
    """

    def __init__(self):
        self.openai_client = get_openai_client()
        self.compliance_repo = ComplianceRepository()
        self.clause_repo = ClauseRepository()
        self.compliance_rules = self._load_compliance_rules()

    async def analyze_compliance(
        self,
        contract_id: str,
        frameworks: Optional[List[ComplianceFramework]] = None,
        contract_metadata: Optional[dict] = None
    ) -> ComplianceAnalysis:
        """
        Check contract against compliance requirements.

        Process:
        1. Determine applicable frameworks based on contract context
        2. Load relevant compliance rules
        3. Check each rule against contract clauses
        4. Use GPT for nuanced interpretation
        5. Generate findings and recommendations
        """
        pass

    def _determine_applicable_frameworks(
        self,
        contract_metadata: dict
    ) -> List[ComplianceFramework]:
        """Determine which frameworks apply based on contract context."""
        pass

    async def _check_rule(
        self,
        rule: dict,
        clauses: List[Clause],
        contract_metadata: dict
    ) -> ComplianceCheck:
        """Check a single compliance rule."""
        pass

    async def _check_clause_presence(
        self,
        required_keywords: List[str],
        clauses: List[Clause]
    ) -> tuple[bool, Optional[Clause]]:
        """Check if required clause/language is present."""
        pass

    def _calculate_compliance_score(
        self,
        checks: List[ComplianceCheck]
    ) -> float:
        """Calculate overall compliance score."""
        pass
```

### API Endpoints

```python
# POST /api/compliance/{contract_id}
# Trigger compliance analysis
# Body: { frameworks: ["gdpr", "hipaa"], jurisdiction: "EU" }

# GET /api/compliance/{contract_id}
# Get compliance analysis results

# GET /api/compliance/frameworks
# List available compliance frameworks

# GET /api/compliance/requirements/{framework}
# Get requirements for a specific framework
```

### Frontend Components

```typescript
// src/components/compliance/ComplianceScoreCard.tsx
// - Overall compliance score visualization
// - Framework-by-framework breakdown

// src/components/compliance/ComplianceCheckList.tsx
// - List of all compliance checks
// - Status indicators (pass/fail/warning)
// - Expandable details with recommendations

// src/components/compliance/ComplianceAlerts.tsx
// - Critical compliance issues prominently displayed
// - Action items

// src/pages/CompliancePage.tsx
// - Full compliance analysis view
```

### Implementation Tasks

```
[ ] 1. Create Compliance data models
[ ] 2. Create compliance rules YAML
[ ] 3. Create ComplianceRepository
[ ] 4. Create Cosmos DB container 'compliance_checks'
[ ] 5. Implement rule loading and parsing
[ ] 6. Implement ComplianceService
[ ] 7. Create GPT prompts for nuanced checks
[ ] 8. Implement API endpoints
[ ] 9. Add routes to function_app.py
[ ] 10. Create TypeScript types
[ ] 11. Implement ComplianceScoreCard
[ ] 12. Implement ComplianceCheckList
[ ] 13. Create CompliancePage
[ ] 14. Add compliance tab to ContractDetailPage
[ ] 15. Write unit tests
```

---

# Phase 3: External Intelligence

**Goal:** Add agents that leverage external data sources.

**Duration Estimate:** 6-8 weeks
**Dependencies:** Phase 2

---

## 3.1 Party Intelligence Agent

### Purpose
Research and provide context about contract counterparties.

### Data Model

```python
# shared/models/party_intelligence.py

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level assessment."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PartyType(str, Enum):
    """Type of party."""
    VENDOR = "vendor"
    CUSTOMER = "customer"
    PARTNER = "partner"
    SUBCONTRACTOR = "subcontractor"


class FinancialHealth(BaseModel):
    """Financial health indicators."""
    credit_rating: Optional[str] = None
    credit_score: Optional[int] = None
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    year_founded: Optional[int] = None
    profitability: Optional[str] = None  # profitable/break-even/loss-making
    payment_behavior: Optional[str] = None  # excellent/good/fair/poor


class LitigationRecord(BaseModel):
    """A litigation record."""
    case_type: str  # breach_of_contract, ip_dispute, etc.
    role: str  # plaintiff/defendant
    status: str  # pending/settled/dismissed/judgment
    date_filed: Optional[datetime] = None
    summary: str
    relevance: str  # How relevant to our contract


class NewsItem(BaseModel):
    """A news item about the party."""
    headline: str
    source: str
    date: datetime
    sentiment: str  # positive/negative/neutral
    summary: str
    url: Optional[str] = None


class SanctionCheck(BaseModel):
    """Sanctions/watchlist check result."""
    list_name: str
    match_found: bool
    match_details: Optional[str] = None
    check_date: datetime


class PartyIntelligence(BaseModel):
    """
    Intelligence about a contract party.

    Cosmos DB Container: party_intelligence
    Partition Key: contract_id
    """
    id: str
    contract_id: str
    partition_key: str

    # Party identification
    party_name: str
    party_type: PartyType
    legal_name: Optional[str] = None
    registration_number: Optional[str] = None
    jurisdiction: Optional[str] = None

    # Company profile
    industry: Optional[str] = None
    sector: Optional[str] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None

    # Financial health
    financial_health: Optional[FinancialHealth] = None

    # Risk signals
    litigation_records: List[LitigationRecord] = Field(default_factory=list)
    news_items: List[NewsItem] = Field(default_factory=list)
    sanction_checks: List[SanctionCheck] = Field(default_factory=list)

    # Relationship history (from internal data)
    previous_contracts: int = 0
    total_contract_value: float = 0.0
    payment_history: Optional[str] = None  # Summary of payment behavior
    dispute_history: List[str] = Field(default_factory=list)

    # Risk assessment
    overall_risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_factors: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    data_sources: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
```

### External Data Sources Integration

```python
# shared/services/external_data/

# company_data_service.py - D&B, Bloomberg, etc.
# news_service.py - NewsAPI, Google News
# litigation_service.py - Court records APIs
# sanctions_service.py - OFAC, EU sanctions lists
# credit_service.py - Credit rating agencies
```

### Service Implementation

```python
# shared/services/party_intelligence_service.py

class PartyIntelligenceService:
    """
    Researches contract counterparties.
    """

    def __init__(self):
        self.openai_client = get_openai_client()
        self.party_intel_repo = PartyIntelligenceRepository()
        self.company_data = CompanyDataService()
        self.news_service = NewsService()
        self.litigation_service = LitigationService()
        self.sanctions_service = SanctionsService()

    async def research_party(
        self,
        contract_id: str,
        party_name: str,
        party_type: PartyType
    ) -> PartyIntelligence:
        """
        Research a contract party.

        Process:
        1. Identify party (resolve to legal entity)
        2. Fetch company profile data
        3. Check financial health indicators
        4. Search for litigation history
        5. Monitor news sentiment
        6. Check sanctions/watchlists
        7. Check internal relationship history
        8. Assess overall risk
        """
        pass

    async def _identify_party(
        self,
        party_name: str
    ) -> dict:
        """Resolve party name to legal entity."""
        pass

    async def _fetch_company_profile(
        self,
        legal_name: str,
        registration_number: Optional[str]
    ) -> dict:
        """Fetch company profile from external sources."""
        pass

    async def _check_sanctions(
        self,
        party_name: str,
        jurisdiction: str
    ) -> List[SanctionCheck]:
        """Check against sanctions and watchlists."""
        pass

    async def _assess_risk(
        self,
        intelligence: PartyIntelligence
    ) -> tuple[RiskLevel, List[str], List[str]]:
        """Assess overall risk and generate recommendations."""
        pass
```

### API Endpoints

```python
# POST /api/party-intel/{contract_id}
# Trigger party intelligence gathering
# Body: { party_name, party_type }

# GET /api/party-intel/{contract_id}
# Get party intelligence results

# POST /api/party-intel/search
# Search for a company (without contract context)
# Body: { company_name, country }
```

### Implementation Tasks

```
[ ] 1. Create PartyIntelligence data models
[ ] 2. Create PartyIntelligenceRepository
[ ] 3. Create Cosmos DB container 'party_intelligence'
[ ] 4. Implement CompanyDataService (mock initially, real APIs later)
[ ] 5. Implement NewsService
[ ] 6. Implement SanctionsService (OFAC list checking)
[ ] 7. Implement PartyIntelligenceService
[ ] 8. Create risk assessment logic
[ ] 9. Implement API endpoints
[ ] 10. Create TypeScript types
[ ] 11. Implement PartyIntelCard component
[ ] 12. Implement RiskIndicators component
[ ] 13. Create PartyIntelligencePage
[ ] 14. Add party intel section to ContractDetailPage
[ ] 15. Write unit tests
```

---

## 3.2 Risk Forecasting Agent

### Purpose
Monitor external factors and forecast risks for active contracts.

### Data Model

```python
# shared/models/risk_forecast.py

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class RiskType(str, Enum):
    """Type of forecasted risk."""
    INFLATION = "inflation"
    CURRENCY = "currency"
    VENDOR_STABILITY = "vendor_stability"
    SUPPLY_CHAIN = "supply_chain"
    REGULATORY = "regulatory"
    MARKET = "market"
    GEOPOLITICAL = "geopolitical"


class RiskTrend(str, Enum):
    """Trend direction."""
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"


class RiskTimeframe(str, Enum):
    """Timeframe for forecast."""
    SHORT_TERM = "short_term"      # 0-6 months
    MEDIUM_TERM = "medium_term"    # 6-18 months
    LONG_TERM = "long_term"        # 18+ months


class ForecastedRisk(BaseModel):
    """A single forecasted risk."""
    risk_type: RiskType
    title: str
    description: str

    # Impact assessment
    probability: str  # low/medium/high
    impact_severity: str  # low/medium/high/critical
    financial_impact_estimate: Optional[float] = None
    financial_impact_range: Optional[str] = None  # "$50K - $100K"

    # Trend
    current_value: Optional[str] = None  # e.g., "4.2% inflation"
    trend: RiskTrend
    forecast_value: Optional[str] = None  # e.g., "4.8% expected"
    timeframe: RiskTimeframe

    # Contract relevance
    affected_clauses: List[str] = Field(default_factory=list)
    mitigation_options: List[str] = Field(default_factory=list)

    # Data source
    data_source: str
    last_updated: datetime


class EconomicIndicator(BaseModel):
    """Economic indicator data point."""
    indicator_name: str
    region: str
    current_value: float
    previous_value: float
    change_percent: float
    trend: RiskTrend
    forecast_value: Optional[float] = None
    forecast_date: Optional[datetime] = None
    source: str
    as_of_date: datetime


class RiskForecast(BaseModel):
    """
    Risk forecast for a contract.

    Cosmos DB Container: risk_forecasts
    Partition Key: contract_id
    """
    id: str
    contract_id: str
    partition_key: str

    # Contract context
    contract_value: float
    contract_duration_months: int
    remaining_months: int
    currency: str
    counterparty: Optional[str] = None

    # Forecasted risks
    risks: List[ForecastedRisk] = Field(default_factory=list)

    # Economic indicators
    economic_indicators: List[EconomicIndicator] = Field(default_factory=list)

    # Summary
    total_forecasted_exposure: float = 0.0
    highest_risk_type: Optional[RiskType] = None
    risk_trend_summary: str = ""  # "Overall risk increasing due to inflation"

    # Recommended actions
    immediate_actions: List[str] = Field(default_factory=list)
    watch_items: List[str] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    forecast_generated_at: datetime = Field(default_factory=datetime.utcnow)
    next_review_date: Optional[datetime] = None
```

### External Data Sources

```python
# shared/services/external_data/

# economic_data_service.py
# - Inflation data (BLS, Eurostat)
# - Interest rates (Fed, ECB)
# - GDP forecasts

# currency_service.py
# - Exchange rates
# - Currency forecasts

# market_data_service.py
# - Commodity prices
# - Industry indices
```

### Service Implementation

```python
# shared/services/risk_forecast_service.py

class RiskForecastService:
    """
    Forecasts risks for contracts based on external data.
    """

    def __init__(self):
        self.openai_client = get_openai_client()
        self.forecast_repo = RiskForecastRepository()
        self.economic_data = EconomicDataService()
        self.currency_service = CurrencyService()
        self.party_intel_service = PartyIntelligenceService()

    async def generate_forecast(
        self,
        contract_id: str,
        contract_metadata: dict
    ) -> RiskForecast:
        """
        Generate risk forecast for a contract.

        Process:
        1. Load contract details (value, duration, parties)
        2. Fetch relevant economic indicators
        3. Analyze inflation risk
        4. Analyze currency risk (if multi-currency)
        5. Check vendor stability (from party intelligence)
        6. Generate combined risk assessment
        7. Calculate financial impact estimates
        8. Recommend actions
        """
        pass

    async def _analyze_inflation_risk(
        self,
        contract_value: float,
        duration_months: int,
        region: str,
        has_escalation_clause: bool
    ) -> ForecastedRisk:
        """Analyze inflation risk impact."""
        pass

    async def _analyze_currency_risk(
        self,
        contract_value: float,
        base_currency: str,
        payment_currency: str
    ) -> Optional[ForecastedRisk]:
        """Analyze currency fluctuation risk."""
        pass

    async def _calculate_impact(
        self,
        risk: ForecastedRisk,
        contract_metadata: dict
    ) -> float:
        """Calculate estimated financial impact."""
        pass
```

### API Endpoints

```python
# POST /api/risk-forecast/{contract_id}
# Generate risk forecast

# GET /api/risk-forecast/{contract_id}
# Get risk forecast

# GET /api/risk-forecast/economic-indicators
# Get current economic indicators
# Query params: region, indicator_type

# POST /api/risk-forecast/portfolio
# Generate portfolio-wide risk summary
```

### Implementation Tasks

```
[ ] 1. Create RiskForecast data models
[ ] 2. Create RiskForecastRepository
[ ] 3. Create Cosmos DB container 'risk_forecasts'
[ ] 4. Implement EconomicDataService (mock with sample data)
[ ] 5. Implement CurrencyService
[ ] 6. Implement RiskForecastService
[ ] 7. Create inflation impact calculator
[ ] 8. Create currency risk calculator
[ ] 9. Implement API endpoints
[ ] 10. Create TypeScript types
[ ] 11. Implement RiskForecastCard component
[ ] 12. Implement EconomicIndicatorsChart
[ ] 13. Create RiskForecastPage
[ ] 14. Add forecast section to ContractDetailPage
[ ] 15. Write unit tests
```

---

# Phase 4: Advisory Layer

**Goal:** Synthesize all agent outputs into actionable negotiation guidance.

**Duration Estimate:** 4-6 weeks
**Dependencies:** Phase 2, Phase 3 (partial)

---

## 4.1 Negotiation Strategy Agent

### Purpose
Synthesize all findings and intelligence into prioritized negotiation recommendations.

### Data Model

```python
# shared/models/negotiation_strategy.py

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class NegotiationPriority(str, Enum):
    """Priority for negotiation."""
    MUST_FIX = "must_fix"           # Non-negotiable, must address
    SHOULD_PUSH = "should_push"     # Important to improve
    NICE_TO_HAVE = "nice_to_have"   # Would be good but acceptable
    ACCEPT = "accept"               # Acceptable as-is


class NegotiationOutcome(str, Enum):
    """Potential outcome of negotiation."""
    LIKELY_ACHIEVABLE = "likely_achievable"
    POSSIBLE = "possible"
    DIFFICULT = "difficult"
    UNLIKELY = "unlikely"


class LanguageOption(BaseModel):
    """Alternative language option for negotiation."""
    option_name: str  # "Preferred", "Fallback", "Minimum"
    language: str
    description: str
    risk_level: str  # after accepting this option
    likelihood: NegotiationOutcome


class NegotiationPoint(BaseModel):
    """A single negotiation point."""
    id: str
    title: str
    current_position: str  # Current contract language/terms
    issue_summary: str

    # Priority and impact
    priority: NegotiationPriority
    estimated_value_at_risk: Optional[float] = None
    value_range: Optional[str] = None

    # Source
    source_findings: List[str] = Field(default_factory=list)  # Finding IDs
    source_benchmarks: List[str] = Field(default_factory=list)
    source_compliance: List[str] = Field(default_factory=list)

    # Options
    language_options: List[LanguageOption] = Field(default_factory=list)

    # Trade-off suggestions
    trade_off_suggestions: List[str] = Field(default_factory=list)

    # Negotiation context
    counterparty_likely_position: Optional[str] = None
    leverage_points: List[str] = Field(default_factory=list)

    # Outcome
    recommended_action: str
    fallback_position: str


class TradeOff(BaseModel):
    """A suggested trade-off between negotiation points."""
    give_item: str  # What we might concede
    get_item: str   # What we get in return
    rationale: str
    net_benefit: str  # positive/neutral/negative


class NegotiationStrategy(BaseModel):
    """
    Complete negotiation strategy for a contract.

    Cosmos DB Container: negotiation_strategies
    Partition Key: contract_id
    """
    id: str
    contract_id: str
    partition_key: str

    # Contract context
    counterparty: str
    contract_type: Optional[str] = None
    total_value_at_risk: float = 0.0

    # Negotiation points
    negotiation_points: List[NegotiationPoint] = Field(default_factory=list)

    # Summary by priority
    must_fix_count: int = 0
    should_push_count: int = 0
    nice_to_have_count: int = 0

    # Trade-off suggestions
    suggested_trade_offs: List[TradeOff] = Field(default_factory=list)

    # Executive summary
    executive_summary: str = ""
    key_risks: List[str] = Field(default_factory=list)
    key_opportunities: List[str] = Field(default_factory=list)

    # Negotiation context
    counterparty_profile_summary: Optional[str] = None
    market_position: Optional[str] = None  # strong/neutral/weak
    recommended_approach: str = ""  # collaborative/assertive/defensive

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    inputs_used: List[str] = Field(default_factory=list)
```

### Service Implementation

```python
# shared/services/negotiation_strategy_service.py

class NegotiationStrategyService:
    """
    Generates negotiation strategy from all available data.
    """

    def __init__(self):
        self.openai_client = get_openai_client()
        self.strategy_repo = NegotiationStrategyRepository()
        self.finding_repo = FindingRepository()
        self.benchmark_repo = BenchmarkRepository()
        self.compliance_repo = ComplianceRepository()
        self.party_intel_repo = PartyIntelligenceRepository()
        self.risk_forecast_repo = RiskForecastRepository()

    async def generate_strategy(
        self,
        contract_id: str
    ) -> NegotiationStrategy:
        """
        Generate comprehensive negotiation strategy.

        Process:
        1. Gather all inputs (findings, benchmarks, compliance, party intel, forecasts)
        2. Prioritize issues by impact and achievability
        3. Generate alternative language options
        4. Identify trade-off opportunities
        5. Assess counterparty position
        6. Generate executive summary and recommendations
        """
        pass

    async def _gather_inputs(
        self,
        contract_id: str
    ) -> dict:
        """Gather all available intelligence about the contract."""
        pass

    async def _prioritize_issues(
        self,
        findings: List,
        benchmarks: List,
        compliance_issues: List,
        risk_forecasts: List
    ) -> List[NegotiationPoint]:
        """Prioritize all issues into negotiation points."""
        pass

    async def _generate_language_options(
        self,
        negotiation_point: NegotiationPoint,
        context: dict
    ) -> List[LanguageOption]:
        """Generate alternative language options using GPT."""
        pass

    async def _identify_trade_offs(
        self,
        negotiation_points: List[NegotiationPoint]
    ) -> List[TradeOff]:
        """Identify potential trade-offs between points."""
        pass

    async def _generate_executive_summary(
        self,
        strategy: NegotiationStrategy,
        context: dict
    ) -> str:
        """Generate executive summary using GPT."""
        pass
```

### API Endpoints

```python
# POST /api/negotiation/{contract_id}
# Generate negotiation strategy

# GET /api/negotiation/{contract_id}
# Get negotiation strategy

# PUT /api/negotiation/{contract_id}/points/{point_id}
# Update a negotiation point (user overrides)

# POST /api/negotiation/{contract_id}/refresh
# Refresh strategy with latest data
```

### Frontend Components

```typescript
// src/components/negotiation/NegotiationPriorityMatrix.tsx
// - Visual matrix of negotiation points by priority/impact
// - Drag-and-drop to reprioritize

// src/components/negotiation/LanguageOptionsPanel.tsx
// - Show alternative language options
// - Copy to clipboard
// - Track which option is chosen

// src/components/negotiation/TradeOffSuggestions.tsx
// - Display suggested trade-offs
// - Accept/reject trade-offs

// src/components/negotiation/NegotiationPlaybook.tsx
// - Printable negotiation guide
// - Checklist format

// src/pages/NegotiationPage.tsx
// - Main negotiation strategy view
// - Export to PDF
```

### Implementation Tasks

```
[ ] 1. Create NegotiationStrategy data models
[ ] 2. Create NegotiationStrategyRepository
[ ] 3. Create Cosmos DB container 'negotiation_strategies'
[ ] 4. Implement input gathering from all sources
[ ] 5. Implement prioritization logic
[ ] 6. Create GPT prompts for language generation
[ ] 7. Implement trade-off identification
[ ] 8. Implement NegotiationStrategyService
[ ] 9. Create API endpoints
[ ] 10. Create TypeScript types
[ ] 11. Implement NegotiationPriorityMatrix
[ ] 12. Implement LanguageOptionsPanel
[ ] 13. Implement TradeOffSuggestions
[ ] 14. Create NegotiationPage
[ ] 15. Implement PDF export for playbook
[ ] 16. Write unit tests
```

---

# Phase 5: Workflow Automation

**Goal:** Automate contract lifecycle workflows with human-in-the-loop decision points.

**Duration Estimate:** 6-8 weeks
**Dependencies:** Phase 2, Phase 3, Phase 4

---

## 5.1 Approval Workflow Engine

### Features
- Configurable approval chains
- Role-based routing
- Escalation rules
- SLA tracking
- Audit trail

### Data Model

```python
# shared/models/workflow.py

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class ApprovalStep(BaseModel):
    step_number: int
    approver_role: str
    approver_id: Optional[str]
    status: WorkflowStatus
    decision_date: Optional[datetime]
    comments: Optional[str]
    sla_hours: int
    escalation_triggered: bool = False


class ApprovalWorkflow(BaseModel):
    id: str
    contract_id: str
    workflow_type: str  # review, approval, renewal
    steps: List[ApprovalStep]
    current_step: int
    overall_status: WorkflowStatus
    created_at: datetime
    completed_at: Optional[datetime]
```

### Implementation Tasks

```
[ ] 1. Create Workflow data models
[ ] 2. Create WorkflowRepository
[ ] 3. Create workflow configuration system
[ ] 4. Implement WorkflowEngine service
[ ] 5. Implement approval routing logic
[ ] 6. Implement SLA tracking
[ ] 7. Implement escalation rules
[ ] 8. Create notification service integration
[ ] 9. Create API endpoints
[ ] 10. Implement workflow dashboard UI
[ ] 11. Implement approval forms
[ ] 12. Create audit trail view
```

---

## 5.2 Alert & Notification System

### Features
- Obligation deadline alerts
- Renewal reminders
- Risk threshold alerts
- Compliance expiry notifications
- Email and in-app notifications

### Implementation Tasks

```
[ ] 1. Create Alert data model
[ ] 2. Create AlertRepository
[ ] 3. Implement AlertService
[ ] 4. Integrate with Azure Service Bus/Event Grid
[ ] 5. Implement email notification service (SendGrid/Azure Communication Services)
[ ] 6. Implement in-app notification system
[ ] 7. Create notification preferences settings
[ ] 8. Implement alert rules configuration
[ ] 9. Create notification inbox UI
[ ] 10. Implement push notifications (optional)
```

---

## 5.3 Calendar Integration

### Features
- Sync obligations to Outlook/Google Calendar
- Automatic calendar event creation
- Reminder synchronization
- Calendar subscription (ICS feed)

### Implementation Tasks

```
[ ] 1. Implement Microsoft Graph API integration
[ ] 2. Implement Google Calendar API integration
[ ] 3. Create ICS feed generator
[ ] 4. Implement calendar sync service
[ ] 5. Create calendar connection UI
[ ] 6. Handle OAuth flows for calendar access
[ ] 7. Implement bi-directional sync (optional)
[ ] 8. Create calendar preference settings
```

---

## 5.4 Renewal Automation

### Features
- Automatic renewal detection
- Renewal notice tracking
- Renewal analysis triggers
- Comparison with current market
- Renewal decision support

### Implementation Tasks

```
[ ] 1. Implement renewal detection from obligations
[ ] 2. Create renewal timeline tracker
[ ] 3. Auto-trigger analysis for upcoming renewals
[ ] 4. Integrate with benchmark agent for market comparison
[ ] 5. Create renewal dashboard
[ ] 6. Implement renewal decision workflow
[ ] 7. Create renewal notification rules
[ ] 8. Generate renewal recommendation reports
```

---

# Summary: Implementation Roadmap

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          IMPLEMENTATION TIMELINE                                 │
│                                                                                 │
│  PHASE 1: FOUNDATION ─────────────────────────────────────────────── ✅ DONE   │
│  │                                                                              │
│  │  Weeks 1-8 (Completed)                                                       │
│  │  • Contract ingestion pipeline                                               │
│  │  • Clause extraction (NLP + GPT-4.5)                                         │
│  │  • Leakage detection (Rules + GPT-5.2 + RAG)                                 │
│  │  • User override system                                                      │
│  │  • Report generation (PDF/Excel)                                             │
│  │  • Dynamic risk profiling                                                    │
│  │                                                                              │
│  PHASE 2: INTELLIGENCE ──────────────────────────────────────────── 🔲 NEXT    │
│  │                                                                              │
│  │  Weeks 9-14 (4-6 weeks)                                                      │
│  │  ┌──────────────────┬──────────────────┐                                    │
│  │  │ Obligation Agent │ Comparison Agent │  ← Weeks 9-11                      │
│  │  └──────────────────┴──────────────────┘                                    │
│  │  ┌──────────────────┬──────────────────┐                                    │
│  │  │ Benchmark Agent  │ Compliance Agent │  ← Weeks 12-14                     │
│  │  └──────────────────┴──────────────────┘                                    │
│  │                                                                              │
│  PHASE 3: EXTERNAL INTELLIGENCE ─────────────────────────────────── 🔲 PLANNED │
│  │                                                                              │
│  │  Weeks 15-22 (6-8 weeks)                                                     │
│  │  ┌────────────────────────┐                                                  │
│  │  │ Party Intelligence     │  ← Weeks 15-18                                  │
│  │  └────────────────────────┘                                                  │
│  │  ┌────────────────────────┐                                                  │
│  │  │ Risk Forecasting       │  ← Weeks 19-22                                  │
│  │  └────────────────────────┘                                                  │
│  │                                                                              │
│  PHASE 4: ADVISORY ──────────────────────────────────────────────── 🔲 PLANNED │
│  │                                                                              │
│  │  Weeks 23-28 (4-6 weeks)                                                     │
│  │  ┌────────────────────────┐                                                  │
│  │  │ Negotiation Strategy   │  ← Weeks 23-26                                  │
│  │  └────────────────────────┘                                                  │
│  │  ┌────────────────────────┐                                                  │
│  │  │ Advisory Dashboard     │  ← Weeks 27-28                                  │
│  │  └────────────────────────┘                                                  │
│  │                                                                              │
│  PHASE 5: WORKFLOW AUTOMATION ───────────────────────────────────── 🔲 PLANNED │
│  │                                                                              │
│  │  Weeks 29-36 (6-8 weeks)                                                     │
│  │  ┌──────────────────┬──────────────────┐                                    │
│  │  │ Approval Workflow│ Alert System     │  ← Weeks 29-32                     │
│  │  └──────────────────┴──────────────────┘                                    │
│  │  ┌──────────────────┬──────────────────┐                                    │
│  │  │ Calendar Sync    │ Renewal Automation│  ← Weeks 33-36                    │
│  │  └──────────────────┴──────────────────┘                                    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

# Resource Requirements

## Azure Resources (Additional)

| Resource | Purpose | Estimated Cost |
|----------|---------|----------------|
| Cosmos DB containers (7 new) | Agent data storage | ~$25/month additional |
| Azure Service Bus | Event-driven workflows | ~$10/month |
| Azure Communication Services | Email notifications | Pay per use |
| External API subscriptions | Party intel, economic data | Variable |

## Development Team

| Role | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|------|---------|---------|---------|---------|
| Backend Developer | 1 FTE | 1 FTE | 0.5 FTE | 1 FTE |
| Frontend Developer | 0.5 FTE | 0.5 FTE | 0.5 FTE | 0.5 FTE |
| AI/ML Engineer | 0.5 FTE | 0.5 FTE | 0.5 FTE | - |
| QA Engineer | 0.25 FTE | 0.25 FTE | 0.25 FTE | 0.25 FTE |

---

*Document created: 2026-01-28*
*Last updated: 2026-01-28*
