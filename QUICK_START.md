# Quick Start Guide

Get the Contract Leakage Engine backend running locally in minutes.

## Prerequisites

✅ Python 3.12.9 installed
✅ Azure Functions Core Tools v4.x installed
✅ Azure resources created (see [AZURE_SETUP.md](./AZURE_SETUP.md))
✅ Git installed

---

## Step 1: Clone and Setup

```bash
# Navigate to backend directory
cd contract-leakage-engine-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Local Settings

Copy your Azure connection strings into `local.settings.json`:

```json
{
  "Values": {
    "CosmosDBConnectionString": "AccountEndpoint=https://...;AccountKey=...;",
    "StorageConnectionString": "DefaultEndpointsProtocol=https;...",
    "OpenAIKey": "your-key-here",
    "OpenAIEndpoint": "https://your-openai.openai.azure.com/",
    ...
  }
}
```

Get these values from Azure Portal → Your Resources → Keys/Connection Strings

---

## Step 3: Download NLP Model

```bash
python -m spacy download en_core_web_lg
```

---

## Step 4: Run Locally

```bash
func start
```

You should see:
```
Azure Functions Core Tools
Core Tools Version:       4.x.x
Function Runtime Version: 4.x.x

Functions:
        analyze_contract: [POST] http://localhost:7071/api/analyze_contract/{contract_id}
        dismiss_finding: [POST] http://localhost:7071/api/dismiss_finding/{contract_id}/{finding_id}
        get_analysis: [GET] http://localhost:7071/api/get_analysis/{contract_id}
        health: [GET] http://localhost:7071/api/health
        list_contracts: [GET] http://localhost:7071/api/list_contracts
        upload_contract: [POST] http://localhost:7071/api/upload_contract
```

---

## Step 5: Test the API

### Health Check
```bash
curl http://localhost:7071/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "AI Contract & Commercial Leakage Engine",
  "version": "1.0.0-poc"
}
```

### Upload a Contract (Example)
```bash
curl -X POST http://localhost:7071/api/upload_contract \
  -F "file=@test_contract.pdf" \
  -F "contract_name=Test Contract" \
  -F "counterparty=Test Corp"
```

Expected response:
```json
{
  "message": "Contract uploaded successfully",
  "contract_id": "contract_abc123...",
  "status": "uploaded"
}
```

### List Contracts
```bash
curl http://localhost:7071/api/list_contracts
```

---

## Project Structure Overview

```
contract-leakage-engine-backend/
├── api/                          # ✅ Azure Functions (6 endpoints)
│   ├── upload_contract/
│   ├── analyze_contract/
│   ├── get_analysis/
│   ├── list_contracts/
│   ├── dismiss_finding/
│   └── health/
├── shared/                       # ✅ Shared modules
│   ├── models/                   # ✅ Pydantic data models
│   ├── db/                       # ✅ Cosmos DB layer
│   ├── services/                 # TODO: Business logic
│   └── utils/                    # ✅ Config, logging, exceptions
├── rules/                        # TODO: YAML leakage rules
├── requirements.txt              # ✅ Dependencies
├── host.json                     # ✅ Functions config
├── local.settings.json           # ✅ Local configuration
└── README.md                     # ✅ Full documentation
```

---

## Current API Capabilities

### ✅ Working Now
- **Health check** - Verify API is running
- **Upload contract** - Upload PDF/DOCX files
- **List contracts** - View uploaded contracts
- **Get analysis** - Retrieve full analysis results
- **Dismiss findings** - User overrides

### 🚧 In Progress
- **Analyze contract** - Currently updates status, full pipeline coming in phases:
  - Phase 2: Text extraction (OCR)
  - Phase 3: Clause extraction (NLP)
  - Phase 4: Leakage detection (Rules)
  - Phase 5: AI-powered detection (OpenAI + RAG)
  - Phase 6: Report generation

---

## Next Steps

1. **Phase 2**: Build document ingestion and OCR services
2. **Phase 3**: Build NLP clause extraction
3. **Phase 4**: Implement YAML rules engine
4. **Phase 5**: Add Azure OpenAI and RAG services
5. **Phase 6**: Build export/reporting
6. **Phase 7**: Deploy and test end-to-end

---

## Troubleshooting

### "Module not found" errors
```bash
# Make sure virtual environment is activated
# Windows:
venv\Scripts\activate
# Then reinstall:
pip install -r requirements.txt
```

### "Cannot connect to Cosmos DB"
- Verify `CosmosDBConnectionString` in `local.settings.json`
- Check Azure Portal → Cosmos DB → Keys
- Ensure database `ContractLeakageDB` exists
- Ensure all 4 containers exist (contracts, clauses, leakage_findings, analysis_sessions)

### "Function not found" errors
- Ensure you're in the backend directory when running `func start`
- Check `api/` folder contains all function folders
- Each function folder should have `__init__.py` and `function.json`

### Port already in use
```bash
# Change port in local.settings.json:
"Host": {
  "LocalHttpPort": 7072  # Use different port
}
```

---

## Deployment to Azure

```bash
# Login to Azure
az login

# Deploy to Azure Functions
func azure functionapp publish func-contract-leakage-poc
```

After deployment, get the function key:
```bash
# Azure Portal → Function App → Functions → Any function → Function Keys
```

Use the key in requests:
```bash
curl https://func-contract-leakage-poc.azurewebsites.net/api/health \
  -H "x-functions-key: YOUR_FUNCTION_KEY"
```

---

## Useful Commands

```bash
# Start local development
func start

# Start with specific port
func start --port 7072

# View logs in real-time
func start --verbose

# Deploy to Azure
func azure functionapp publish func-contract-leakage-poc

# Check Python version
python --version  # Should be 3.12.9

# List installed packages
pip list

# Update a specific package
pip install --upgrade azure-functions
```

---

## Documentation

- [README.md](./README.md) - Full project documentation
- [API_REFERENCE.md](./API_REFERENCE.md) - Complete API documentation
- [AZURE_SETUP.md](./AZURE_SETUP.md) - Azure resources setup guide
- Reference docs/ - Original POC specifications

---

## Support

For issues or questions, check:
1. This QUICK_START.md
2. Troubleshooting section above
3. [README.md](./README.md) for detailed docs
4. Azure Portal for resource configuration

---

**You're all set!** The backend is ready for development. Next: Build the service layer (OCR, NLP, AI services).
