# AI Contract & Commercial Leakage Engine - Backend

Azure Functions backend for the AI Contract & Commercial Leakage Engine POC.

## Overview

This backend provides REST API endpoints for:
- Contract document upload and ingestion
- OCR and text extraction
- Clause extraction using NLP
- Commercial leakage detection (rule-based + AI)
- Impact quantification
- Analysis results and reporting

## Architecture

- **Runtime**: Python 3.12.9 on Azure Functions (Consumption plan)
- **Database**: Azure Cosmos DB (NoSQL)
- **Storage**: Azure Blob Storage
- **AI Services**: Azure OpenAI (GPT 5.2 + text-embedding-3-large), Azure AI Search (RAG), Azure Document Intelligence
- **Deployment**: Cloud-first to Azure

## Project Structure

```
contract-leakage-engine-backend/
├── api/                          # Azure Functions HTTP endpoints
│   ├── upload_contract/          # Contract file upload
│   ├── extract_text/             # OCR and text extraction
│   ├── extract_clauses/          # NLP clause extraction
│   ├── detect_leakage/           # Leakage detection orchestration
│   ├── calculate_impact/         # Financial impact calculation
│   ├── get_analysis/             # Retrieve analysis results
│   ├── generate_report/          # Export reports
│   └── cleanup_session/          # Session cleanup
├── shared/                       # Shared Python modules
│   ├── models/                   # Pydantic data models
│   ├── services/                 # Business logic services
│   │   ├── storage_service.py    # Azure Blob Storage operations
│   │   ├── ocr_service.py        # Document Intelligence integration
│   │   ├── document_service.py   # Document processing orchestration
│   │   ├── text_preprocessing_service.py  # Text cleaning & segmentation
│   │   ├── nlp_service.py        # spaCy NLP analysis
│   │   ├── clause_extraction_service.py   # Clause extraction orchestration
│   │   ├── rules_engine.py       # YAML-based leakage detection
│   │   ├── embedding_service.py  # Vector embeddings (text-embedding-3-large)
│   │   ├── search_service.py     # Azure AI Search integration
│   │   ├── rag_service.py        # RAG orchestration
│   │   └── ai_detection_service.py  # GPT 5.2 leakage detection
│   ├── db/                       # Cosmos DB operations
│   │   ├── cosmos_client.py      # Cosmos DB client wrapper
│   │   └── repositories/         # Data access layer
│   └── utils/                    # Utility functions
│       ├── config.py             # Configuration management
│       ├── logging.py            # Logging setup
│       └── exceptions.py         # Custom exceptions
├── rules/                        # YAML leakage detection rules
│   └── leakage_rules.yaml
├── requirements.txt              # Python dependencies
├── host.json                     # Azure Functions configuration
├── local.settings.json.example   # Example local settings (copy to local.settings.json)
├── .gitignore
├── .funcignore
├── AZURE_SETUP.md               # Azure resources setup guide
└── README.md                     # This file
```

## Prerequisites

1. **Azure Resources**: Follow [AZURE_SETUP.md](./AZURE_SETUP.md) to create required Azure resources
2. **Python**: Python 3.12.9
3. **Azure Functions Core Tools**: v4.x
4. **Git**: For version control

## Local Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd contract-leakage-engine-backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Local Settings

```bash
# Copy example settings
cp local.settings.json.example local.settings.json

# Edit local.settings.json and fill in your Azure resource connection strings
```

Get the connection strings from:
- Azure Portal → Your Resource Group → Each Resource → Keys/Connection Strings

### 5. Download spaCy Model (for NLP)

```bash
python -m spacy download en_core_web_lg
```

### 6. Run Locally

```bash
func start
```

The API will be available at `http://localhost:7071/api/`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload_contract` | POST | Upload contract file (PDF/DOCX) |
| `/api/extract_text` | POST | Extract text from uploaded contract |
| `/api/extract_clauses` | POST | Extract and classify clauses |
| `/api/detect_leakage` | POST | Run leakage detection (rules + AI) |
| `/api/calculate_impact` | POST | Calculate financial impact |
| `/api/get_analysis/{contract_id}` | GET | Get complete analysis results |
| `/api/generate_report/{contract_id}` | GET | Export analysis report |
| `/api/cleanup_session/{session_id}` | DELETE | Clean up analysis session |

## Deployment

### Deploy to Azure Functions

```bash
# Login to Azure
az login

# Deploy
func azure functionapp publish func-contract-leakage-poc
```

### CI/CD

GitHub Actions workflow (coming soon) will automatically deploy on push to `main` branch.

## Development Workflow

### Phase 1-3: Foundation
1. Contract ingestion
2. Text extraction (OCR)
3. Clause extraction (NLP)

### Phase 4: Rule-Based Detection
1. Implement YAML rules engine
2. Add leakage detection rules

### Phase 5: AI-Powered Detection
1. Implement RAG with Azure AI Search
2. Integrate Azure OpenAI for reasoning
3. Add impact quantification

### Phase 6-7: Complete POC
1. Export and reporting
2. User overrides and adjustments
3. End-to-end testing

## Data Model (Cosmos DB)

### Containers

All containers use `contract_id` as partition key:

1. **contracts**: Contract metadata
2. **clauses**: Extracted clauses with embeddings
3. **leakage_findings**: Detected risks and issues
4. **analysis_sessions**: User interactions and overrides

See `shared/models/` for detailed schemas.

## Testing

```bash
# Run unit tests
pytest

# Run with coverage
pytest --cov=shared --cov=api
```

## Monitoring

Application Insights is configured for monitoring:
- Function execution times
- AI service latency
- Error rates
- Custom metrics

Access via Azure Portal → Function App → Application Insights

## Troubleshooting

### Issue: Import errors when running locally
**Solution**: Ensure virtual environment is activated and all dependencies are installed

### Issue: "Cannot find module 'shared'"
**Solution**: Azure Functions requires shared code in `shared/` directory. Verify structure matches documentation.

### Issue: Cosmos DB connection fails
**Solution**: Verify connection string in `local.settings.json` and ensure Cosmos DB firewall allows your IP

### Issue: OpenAI API errors
**Solution**:
- Verify deployment names match (`gpt-4o-deployment`, `text-embedding-deployment`)
- Check API version is compatible
- Ensure sufficient quota

## Contributing

1. Create feature branch from `main`
2. Make changes
3. Test locally
4. Submit pull request

## License

Proprietary - KPMG Bahrain

## Support

For issues or questions, contact the development team.
