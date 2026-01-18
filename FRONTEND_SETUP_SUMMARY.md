# Frontend Setup - Implementation Summary

## Overview

Phase 7 Task 14 implements a **professional React + TypeScript frontend** for the Contract Leakage Engine with a **KPMG Master Guide-inspired design system**, providing a modern single-page application for contract analysis.

---

## What Was Built

### 1. **Project Configuration** (Vite + React + TypeScript)

**Package Configuration** (`package.json`):
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.1",
    "@tanstack/react-query": "^5.17.9",
    "axios": "^1.6.5",
    "date-fns": "^3.0.6",
    "lucide-react": "^0.307.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "tailwindcss": "^3.4.1",
    "vite": "^5.0.11"
  }
}
```

**Key Technology Choices:**
- **Vite**: Lightning-fast build tool with HMR
- **React 18**: Latest React with concurrent features
- **TypeScript 5.3**: Full type safety
- **TanStack Query**: Server state management
- **Tailwind CSS**: Utility-first styling
- **Axios**: Promise-based HTTP client
- **React Router 6**: Declarative routing

---

### 2. **Design System - KPMG Inspired**

Implemented professional design system matching backend `brand_constants.py`:

#### Tailwind Configuration (`tailwind.config.js`)

```javascript
colors: {
  // Brand colors
  primary: {
    DEFAULT: '#1a237e',    // PRIMARY_BLUE
    light: '#1976d2',      // ACCENT_BLUE
    dark: '#0d1b2a',       // DARK_NAVY
  },

  // Severity colors (matching backend)
  severity: {
    critical: '#d32f2f',
    'critical-light': '#ffebee',
    high: '#f57c00',
    'high-light': '#fff9e6',
    medium: '#fbc02d',
    'medium-light': '#fffde7',
    low: '#388e3c',
    'low-light': '#e8f5e9',
  },

  // Semantic colors
  success: { DEFAULT: '#00853f', light: '#e8f5e9' },
  error: { DEFAULT: '#da291c', light: '#ffebee' },
},

boxShadow: {
  'card': '0 1px 3px 0 rgba(0, 0, 0, 0.08)...',
  'card-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.08)...',
  'primary': '0 4px 14px 0 rgba(26, 35, 126, 0.15)',
},
```

**Inspiration Source**: Examined `esg_frontend/src/assets/styles/_variables.scss` for KPMG design tokens including:
- Color system (primary, semantic, neutral palettes)
- Typography scale (Inter font family)
- Spacing scale (4px base unit)
- Shadow system (light/dark theme)
- Border radius tokens
- Animation durations and easing functions

#### Global Styles (`src/index.css`)

```css
/* Component utilities */
.card {
  @apply bg-white rounded-lg shadow-card p-6
         hover:shadow-card-hover transition-all
         duration-200 border border-gray-100;
}

.severity-badge {
  @apply inline-flex items-center px-3 py-1
         rounded-full text-sm font-medium text-white;
}

.btn-primary {
  @apply bg-primary text-white hover:bg-primary-dark;
}
```

---

### 3. **Project Structure**

```
contract-leakage-engine-frontend/
├── public/
├── src/
│   ├── components/
│   │   └── layout/
│   │       ├── Layout.tsx          # Main layout wrapper
│   │       ├── Header.tsx          # Professional top nav
│   │       └── Sidebar.tsx         # Side navigation
│   │
│   ├── pages/
│   │   ├── HomePage.tsx            # Landing with feature cards
│   │   ├── UploadPage.tsx          # Contract upload (placeholder)
│   │   ├── ContractDetailPage.tsx  # Contract details (placeholder)
│   │   ├── FindingsPage.tsx        # Findings list (placeholder)
│   │   ├── ClausesPage.tsx         # Clause viewer (placeholder)
│   │   └── NotFoundPage.tsx        # 404 error page
│   │
│   ├── services/
│   │   ├── api.ts                  # Axios client with interceptors
│   │   ├── contractService.ts      # Contract operations
│   │   ├── findingsService.ts      # Findings operations
│   │   ├── clausesService.ts       # Clauses operations
│   │   └── index.ts                # Service exports
│   │
│   ├── utils/
│   │   └── format.ts               # Formatting utilities
│   │
│   ├── App.tsx                     # Root with routing
│   ├── main.tsx                    # Entry point
│   └── index.css                   # Global styles
│
├── package.json
├── tsconfig.json                   # TypeScript config
├── vite.config.ts                  # Vite config with proxy
├── tailwind.config.js              # Tailwind design tokens
├── postcss.config.js
├── index.html
└── README.md
```

---

### 4. **Layout System**

#### Header Component

```tsx
<header className="bg-primary text-white shadow-lg">
  <div className="flex items-center justify-between">
    <Link to="/" className="flex items-center space-x-3">
      <FileText size={32} />
      <div>
        <h1>Contract Leakage Engine</h1>
        <p className="text-sm">AI-Powered Commercial Leakage Analysis</p>
      </div>
    </Link>

    <Link to="/upload" className="btn bg-white text-primary">
      <Upload /> Upload Contract
    </Link>
  </div>
</header>
```

**Professional Features:**
- KPMG-inspired blue header with white branding
- Prominent CTA button for contract upload
- Clean typography with clear hierarchy
- Responsive layout with proper spacing

#### Sidebar Component

```tsx
<aside className="w-64 bg-white border-r shadow-sm">
  <nav>
    <NavLink to="/" className={({ isActive }) =>
      isActive ? 'bg-primary text-white' : 'text-gray-700 hover:bg-gray-100'
    }>
      <Home /> Home
    </NavLink>
    {/* More nav items */}
  </nav>
</aside>
```

---

### 5. **API Service Layer**

#### Base API Client (`services/api.ts`)

```typescript
const apiClient = axios.create({
  baseURL: '/api',  // Proxied to http://localhost:7071
  timeout: 120000,   // 2 minutes for analysis
});

// Request interceptor - add auth
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor - handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data);
    return Promise.reject(error);
  }
);
```

#### Contract Service (`services/contractService.ts`)

```typescript
export const contractService = {
  // Upload contract with multipart/form-data
  async uploadContract(file, contractName, uploadedBy, metadata) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('contract_name', contractName);
    formData.append('uploaded_by', uploadedBy);
    return apiClient.post('/upload_contract', formData);
  },

  // Trigger analysis
  async analyzeContract(contractId) {
    return apiClient.post('/analyze_contract', { contract_id: contractId });
  },

  // Get contract details
  async getContract(contractId) {
    const response = await apiClient.get(`/get_contract/${contractId}`);
    return response.data.contract;
  },

  // Export and download report
  async downloadReport(contractId, format, includeClauses) {
    const blob = await this.exportReport(contractId, format, includeClauses);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Contract_Report_${contractId}.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
    link.click();
    window.URL.revokeObjectURL(url);
  },
};
```

#### Findings Service (`services/findingsService.ts`)

```typescript
export const findingsService = {
  // Get findings with filters
  async getFindings(contractId, options) {
    return apiClient.get(`/get_findings/${contractId}`, { params: options });
  },

  // Group by severity
  async getFindingsBySeverity(contractId) {
    const response = await this.getFindings(contractId);
    const grouped = { CRITICAL: [], HIGH: [], MEDIUM: [], LOW: [] };
    response.findings.forEach((f) => grouped[f.severity].push(f));
    return grouped;
  },

  // Calculate total impact
  async getTotalFinancialImpact(contractId) {
    const response = await this.getFindings(contractId);
    return response.summary.total_estimated_impact || { amount: 0, currency: 'USD' };
  },
};
```

#### Clauses Service (`services/clausesService.ts`)

```typescript
export const clausesService = {
  // Get clauses with filters
  async getClauses(contractId, options) {
    return apiClient.get(`/get_clauses/${contractId}`, { params: options });
  },

  // Group by type
  async getClausesByType(contractId) {
    const response = await this.getClauses(contractId);
    const grouped = {};
    response.clauses.forEach((c) => {
      if (!grouped[c.clause_type]) grouped[c.clause_type] = [];
      grouped[c.clause_type].push(c);
    });
    return grouped;
  },

  // Filter risky clauses
  async getRiskyClauses(contractId) {
    const response = await this.getClauses(contractId);
    return response.clauses.filter((c) => c.risk_signals?.length > 0);
  },

  // Search clauses
  async searchClauses(contractId, searchText) {
    const response = await this.getClauses(contractId);
    return response.clauses.filter((c) =>
      c.original_text.toLowerCase().includes(searchText.toLowerCase())
    );
  },
};
```

---

### 6. **Utility Functions** (`utils/format.ts`)

```typescript
// Date formatting with date-fns
export function formatDate(date: string, formatStr = 'PPP'): string {
  return format(parseISO(date), formatStr);
}

export function formatRelativeTime(date: string): string {
  return formatDistance(parseISO(date), new Date(), { addSuffix: true });
}

// Currency formatting
export function formatCurrency(amount: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount);
}

// Confidence score
export function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}

// Severity utilities
export function getSeverityColor(severity: Severity): string {
  const colors = {
    CRITICAL: '#d32f2f',
    HIGH: '#f57c00',
    MEDIUM: '#fbc02d',
    LOW: '#388e3c',
  };
  return colors[severity];
}

export function getSeverityBadgeClasses(severity: Severity): string {
  const classes = {
    CRITICAL: 'bg-severity-critical text-white',
    HIGH: 'bg-severity-high text-white',
    MEDIUM: 'bg-severity-medium text-gray-900',
    LOW: 'bg-severity-low text-white',
  };
  return classes[severity];
}

// Text utilities
export function truncateText(text: string, maxLength = 100): string {
  return text.length <= maxLength ? text : `${text.slice(0, maxLength)}...`;
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : (plural || `${singular}s`);
}
```

---

### 7. **Routing Configuration** (`App.tsx`)

```tsx
import { Routes, Route } from 'react-router-dom';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="contract/:contractId" element={<ContractDetailPage />} />
        <Route path="contract/:contractId/findings" element={<FindingsPage />} />
        <Route path="contract/:contractId/clauses" element={<ClausesPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
```

**Route Structure:**
- `/` - Landing page with feature overview
- `/upload` - Contract upload form
- `/contract/:id` - Contract details dashboard
- `/contract/:id/findings` - Findings analysis view
- `/contract/:id/clauses` - Clause viewer
- `*` - 404 error page

---

### 8. **Vite Configuration** (`vite.config.ts`)

```typescript
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@services': path.resolve(__dirname, './src/services'),
      '@utils': path.resolve(__dirname, './src/utils'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:7071',  // Azure Functions backend
        changeOrigin: true,
      },
    },
  },
});
```

**Key Features:**
- Path aliases for clean imports (`@services/contractService`)
- API proxy to backend (avoids CORS issues)
- Port 3000 for dev server
- Hot module replacement (HMR) enabled

---

## HomePage - Landing Page

```tsx
<div className="grid grid-cols-1 md:grid-cols-4 gap-6">
  {/* Upload Card */}
  <div className="card text-center">
    <div className="p-4 bg-primary/10 rounded-full">
      <Upload className="text-primary" />
    </div>
    <h3>Upload Contract</h3>
    <p>Upload PDF, Word, or text contracts for analysis</p>
    <Link to="/upload" className="btn btn-primary">Get Started</Link>
  </div>

  {/* AI Analysis Card */}
  <div className="card text-center">
    <FileSearch />
    <h3>AI Analysis</h3>
    <p>GPT 5.2 powered detection with RAG</p>
  </div>

  {/* Leakage Detection Card */}
  <div className="card text-center">
    <AlertTriangle />
    <h3>Leakage Detection</h3>
    <p>Identify pricing, payment, renewal, and compliance risks</p>
  </div>

  {/* Reports Card */}
  <div className="card text-center">
    <BarChart />
    <h3>Professional Reports</h3>
    <p>Export PDF and Excel reports with executive summaries</p>
  </div>
</div>
```

**Design Features:**
- 4-column grid of feature cards
- Icon-driven visual communication
- Clear call-to-action hierarchy
- Professional spacing and shadows
- Responsive layout (1 col mobile, 4 cols desktop)

---

## Type Safety Integration

All API services use shared TypeScript types:

```typescript
import type {
  Contract,
  Clause,
  LeakageFinding,
  Severity,
  GetFindingsResponse,
} from '@contract-leakage/shared-types';

// Type-safe service methods
async function getFindings(contractId: string): Promise<GetFindingsResponse> {
  const response = await apiClient.get(`/get_findings/${contractId}`);
  return response.data;
}

// Type-safe component props
interface FindingCardProps {
  finding: LeakageFinding;
  onSelect: (id: string) => void;
}
```

**Benefits:**
- IntelliSense autocomplete in VS Code
- Compile-time type checking
- Refactoring support
- Self-documenting code

---

## Design System Comparison: ESG vs Contract Leakage

### Similarities (Inspired by ESG)

| Feature | ESG Frontend | Contract Leakage Frontend |
|---------|-------------|--------------------------|
| **Primary Color** | KPMG Blue (#00338D) | Contract Blue (#1a237e) |
| **Typography** | Inter font family | Inter font family |
| **Spacing Scale** | 4px base unit | Tailwind 4px base |
| **Shadow System** | Light/dark theme shadows | Card/hover shadows |
| **Component Structure** | Card-based layout | Card-based layout |
| **Navigation** | Header + Sidebar | Header + Sidebar |
| **Severity Colors** | Semantic colors | Critical/High/Medium/Low |

### Differences (Contract-Specific)

| Aspect | Contract Leakage Unique Approach |
|--------|----------------------------------|
| **Color Palette** | Severity-focused (red/orange/yellow/green) |
| **Font Family** | Also supports Helvetica (matching PDF reports) |
| **Brand Identity** | Contract analysis theme vs ESG reporting |
| **Page Structure** | Contract-centric routing |
| **Data Visualization** | Leakage findings emphasis |

---

## Installation & Usage

### Install Dependencies

```bash
cd contract-leakage-engine-frontend
npm install
```

### Install Shared Types

```bash
cd ../contract-leakage-engine-backend/shared-types
npm install && npm run build && npm link

cd ../../contract-leakage-engine-frontend
npm link @contract-leakage/shared-types
```

### Start Development

```bash
# Terminal 1: Start backend
cd contract-leakage-engine-backend
func start

# Terminal 2: Start frontend
cd contract-leakage-engine-frontend
npm run dev
```

**Access:** `http://localhost:3000`

---

## Build for Production

```bash
npm run build
```

Output: `dist/` directory

**Deploy to:**
- Azure Static Web Apps
- Vercel
- Netlify
- Any static hosting

---

## Next Implementation Steps

**Task 15: Upload Component** (Next)
- File upload with drag-and-drop
- Contract metadata form
- Progress indicator
- Success/error states

**Task 16: Findings Views**
- Findings list with severity filtering
- Finding detail cards
- Financial impact visualization
- Export actions

**Task 17: Clause Viewer**
- Clause list with type filtering
- Syntax highlighting for risk signals
- Entity extraction display
- Search functionality

**Task 18: User Overrides**
- Edit finding severity
- Add custom notes
- Accept/reject findings
- Audit trail

---

## Summary

**Task 14 Achievement**: Professional React + TypeScript frontend with:
- ✅ Vite + React 18 + TypeScript 5.3 setup
- ✅ KPMG-inspired design system (colors, typography, shadows)
- ✅ Tailwind CSS with custom configuration
- ✅ Professional layout (Header, Sidebar, Layout wrapper)
- ✅ Routing with React Router 6
- ✅ API service layer (Contract, Findings, Clauses)
- ✅ Utility functions (formatting, severity helpers)
- ✅ Type-safe integration with shared types package
- ✅ Placeholder pages for all routes
- ✅ Vite dev server with backend proxy
- ✅ Comprehensive README documentation

**Status**: **14/19 tasks complete (74%)**

The frontend foundation is **production-ready** for component implementation in Tasks 15-17.

---

## Design Inspiration Acknowledgment

This frontend design system draws inspiration from the **KPMG Master Guide** standards implemented in the ESG project (`esg_frontend`), specifically:

**From `esg_frontend/src/assets/styles/_variables.scss`:**
- Professional color system (primary, semantic, neutral palettes)
- Typography scale with Inter font family
- Spacing scale (4px base unit)
- Shadow system (elevation tokens)
- Border radius tokens
- Animation duration and easing functions
- Component tokens (buttons, inputs, cards)

**Adapted for Contract Leakage Engine:**
- Contract analysis-specific color scheme
- Severity-focused design language
- Simplified component structure
- Tailwind CSS utility-first approach
- React component architecture
- Contract/findings/clauses domain models
