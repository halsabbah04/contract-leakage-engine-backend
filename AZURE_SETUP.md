# Azure Resources Setup Guide

This guide walks you through creating all required Azure resources manually via the Azure Portal.

## Prerequisites
- Active Azure subscription
- Access to Azure Portal (portal.azure.com)
- Permissions to create resources in your subscription

## Overview of Resources

You will create the following Azure resources:
1. **Resource Group** - Container for all resources
2. **Azure Cosmos DB** - Database for contracts, clauses, findings
3. **Azure Storage Account** - Blob storage for uploaded contracts
4. **Azure OpenAI** - GPT-4o for AI reasoning and embeddings
5. **Azure AI Search** - Vector and hybrid search
6. **Azure AI Document Intelligence** - OCR for scanned documents
7. **Azure Key Vault** - Secrets management
8. **Azure Functions** - Backend API
9. **Azure Static Web Apps** - Frontend hosting (later phase)

**Estimated Setup Time**: 30-45 minutes

---

## Step 1: Create Resource Group

A resource group is a logical container for all your Azure resources.

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **"Resource groups"** in the left menu
3. Click **"+ Create"**
4. Fill in the details:
   - **Subscription**: Select your subscription
   - **Resource group name**: `rg-contract-leakage-poc`
   - **Region**: `East US`
5. Click **"Review + Create"**, then **"Create"**

---

## Step 2: Create Azure Cosmos DB

Cosmos DB will store contracts, clauses, leakage findings, and analysis sessions.

1. In Azure Portal, click **"+ Create a resource"**
2. Search for **"Azure Cosmos DB"** and select it
3. Click **"Create"**
4. Select **"Azure Cosmos DB for NoSQL"** (Core API)
5. Fill in the details:
   - **Subscription**: Your subscription
   - **Resource Group**: `rg-contract-leakage-poc`
   - **Account Name**: `cosmos-contract-leakage-poc` (must be globally unique)
   - **Location**: `East US`
   - **Capacity mode**: **Serverless** (recommended for POC to minimize costs)
   - **Apply Free Tier Discount**: Yes (if available and not already used)
6. Click **"Review + Create"**, then **"Create"**
7. **Wait for deployment** (takes 3-5 minutes)

### After Deployment - Create Containers

1. Go to your Cosmos DB account: `cosmos-contract-leakage-poc`
2. Click **"Data Explorer"** in the left menu
3. Click **"New Database"**:
   - **Database id**: `ContractLeakageDB`
   - **Provision throughput**: Leave unchecked (using serverless)
4. Click **"OK"**
5. Create **4 containers** (repeat for each):

   **Container 1: contracts**
   - Database: `ContractLeakageDB`
   - Container id: `contracts`
   - Partition key: `/contract_id`

   **Container 2: clauses**
   - Database: `ContractLeakageDB`
   - Container id: `clauses`
   - Partition key: `/contract_id`

   **Container 3: leakage_findings**
   - Database: `ContractLeakageDB`
   - Container id: `leakage_findings`
   - Partition key: `/contract_id`

   **Container 4: analysis_sessions**
   - Database: `ContractLeakageDB`
   - Container id: `analysis_sessions`
   - Partition key: `/contract_id`

### Save Connection String

1. In your Cosmos DB account, click **"Keys"** in the left menu
2. Copy the **"PRIMARY CONNECTION STRING"**
3. Save it securely - you'll need it later for configuration

---

## Step 3: Create Azure Storage Account

Storage account will hold uploaded contract files (PDFs, DOCX).

1. Click **"+ Create a resource"**
2. Search for **"Storage account"** and select it
3. Click **"Create"**
4. Fill in the details:
   - **Subscription**: Your subscription
   - **Resource Group**: `rg-contract-leakage-poc`
   - **Storage account name**: `stcontractleakagepoc` (lowercase, no hyphens, must be globally unique)
   - **Region**: `East US`
   - **Performance**: **Standard**
   - **Redundancy**: **LRS (Locally Redundant Storage)** (sufficient for POC)
5. Click **"Review + Create"**, then **"Create"**

### After Deployment - Create Blob Container

1. Go to your storage account: `stcontractleakagepoc`
2. Click **"Containers"** in the left menu (under Data storage)
3. Click **"+ Container"**:
   - **Name**: `contracts`
   - **Public access level**: **Private**
4. Click **"Create"**

### Save Connection String

1. In your storage account, click **"Access keys"** in the left menu
2. Under **"key1"**, click **"Show"** next to **Connection string**
3. Copy the connection string
4. Save it securely - you'll need it later

---

## Step 4: Create Azure OpenAI

Azure OpenAI provides GPT-4o for reasoning and text embeddings.

**Note**: Azure OpenAI requires申请 application approval. If you don't have access yet:
- Apply here: https://aka.ms/oai/access
- This may take 1-2 business days

### Create Azure OpenAI Resource

1. Click **"+ Create a resource"**
2. Search for **"Azure OpenAI"** and select it
3. Click **"Create"**
4. Fill in the details:
   - **Subscription**: Your subscription
   - **Resource Group**: `rg-contract-leakage-poc`
   - **Region**: `East US` (check availability of GPT-4o in your region)
   - **Name**: `openai-contract-leakage-poc`
   - **Pricing tier**: **Standard S0**
5. Click **"Next"** through all tabs
6. Click **"Review + Create"**, then **"Create"**

### Deploy Models

After deployment completes:

1. Go to your Azure OpenAI resource
2. Click **"Go to Azure OpenAI Studio"** (or navigate to https://oai.azure.com)
3. In Azure OpenAI Studio, click **"Deployments"** in the left menu
4. Click **"+ Create new deployment"**

   **Deployment 1: GPT-4o (Reasoning)**
   - **Model**: `gpt-4o`
   - **Deployment name**: `gpt-4o-deployment`
   - **Model version**: Auto-update to default
   - **Deployment type**: Standard
   - **Tokens per minute rate limit**: 80K (or max available for POC)
   - Click **"Create"**

5. Click **"+ Create new deployment"** again

   **Deployment 2: Text Embeddings (Vector search)**
   - **Model**: `text-embedding-3-large`
   - **Deployment name**: `text-embedding-deployment`
   - **Model version**: Auto-update to default
   - **Deployment type**: Standard
   - **Tokens per minute rate limit**: 120K (or max available)
   - Click **"Create"**

### Save Credentials

1. Go back to Azure Portal → Your Azure OpenAI resource
2. Click **"Keys and Endpoint"** in the left menu
3. Copy:
   - **KEY 1**
   - **Endpoint** (looks like: `https://openai-contract-leakage-poc.openai.azure.com/`)
4. Save both securely - you'll need them later

---

## Step 5: Create Azure AI Search

AI Search provides vector and hybrid search capabilities for RAG.

1. Click **"+ Create a resource"**
2. Search for **"Azure AI Search"** (or "Cognitive Search") and select it
3. Click **"Create"**
4. Fill in the details:
   - **Subscription**: Your subscription
   - **Resource Group**: `rg-contract-leakage-poc`
   - **Service name**: `search-contract-leakage-poc` (must be globally unique)
   - **Location**: `East US`
   - **Pricing tier**: **Basic** (sufficient for POC, supports vector search)
5. Click **"Review + Create"**, then **"Create"**

### Save Credentials

1. Go to your AI Search resource
2. Click **"Keys"** in the left menu
3. Copy:
   - **Primary admin key**
   - **URL** (looks like: `https://search-contract-leakage-poc.search.windows.net`)
4. Save both securely

---

## Step 6: Create Azure AI Document Intelligence

Document Intelligence provides OCR for scanned contract PDFs.

1. Click **"+ Create a resource"**
2. Search for **"Document Intelligence"** (or "Form Recognizer") and select it
3. Click **"Create"**
4. Fill in the details:
   - **Subscription**: Your subscription
   - **Resource Group**: `rg-contract-leakage-poc`
   - **Region**: `East US`
   - **Name**: `doc-intel-contract-leakage-poc`
   - **Pricing tier**: **Free F0** (sufficient for POC) or **Standard S0**
5. Click **"Review + Create"**, then **"Create"**

### Save Credentials

1. Go to your Document Intelligence resource
2. Click **"Keys and Endpoint"** in the left menu
3. Copy:
   - **KEY 1**
   - **Endpoint**
4. Save both securely

---

## Step 7: Create Azure Key Vault

Key Vault securely stores all your connection strings and API keys.

1. Click **"+ Create a resource"**
2. Search for **"Key Vault"** and select it
3. Click **"Create"**
4. Fill in the details:
   - **Subscription**: Your subscription
   - **Resource Group**: `rg-contract-leakage-poc`
   - **Key vault name**: `kv-contract-leakage-poc` (must be globally unique)
   - **Region**: `East US`
   - **Pricing tier**: **Standard**
5. Click **"Review + Create"**, then **"Create"**

### Add Secrets to Key Vault

After deployment:

1. Go to your Key Vault resource
2. Click **"Secrets"** in the left menu
3. Click **"+ Generate/Import"** for each secret below:

   | Secret Name | Value |
   |-------------|-------|
   | `CosmosDBConnectionString` | Cosmos DB primary connection string |
   | `StorageConnectionString` | Storage account connection string |
   | `OpenAIKey` | Azure OpenAI Key 1 |
   | `OpenAIEndpoint` | Azure OpenAI endpoint URL |
   | `SearchServiceKey` | AI Search primary admin key |
   | `SearchServiceEndpoint` | AI Search URL |
   | `DocumentIntelligenceKey` | Document Intelligence Key 1 |
   | `DocumentIntelligenceEndpoint` | Document Intelligence endpoint |

4. For each secret:
   - **Name**: Use exact name from table above
   - **Value**: Paste the corresponding value you saved earlier
   - Click **"Create"**

---

## Step 8: Create Azure Functions App

This will host your backend API.

1. Click **"+ Create a resource"**
2. Search for **"Function App"** and select it
3. Click **"Create"**
4. Fill in the details:
   - **Subscription**: Your subscription
   - **Resource Group**: `rg-contract-leakage-poc`
   - **Function App name**: `func-contract-leakage-poc` (must be globally unique)
   - **Runtime stack**: **Python**
   - **Version**: **3.10** or **3.11**
   - **Region**: `East US`
   - **Operating System**: **Linux**
   - **Plan type**: **Consumption (Serverless)** (pay-per-execution, ideal for POC)
5. Click **"Next: Storage"**
   - **Storage account**: Select `stcontractleakagepoc` (the one you created)
6. Click **"Review + Create"**, then **"Create"**

### Configure Function App Settings

After deployment:

1. Go to your Function App resource
2. Click **"Configuration"** in the left menu (under Settings)
3. Click **"+ New application setting"** for each:

   | Name | Value |
   |------|-------|
   | `CosmosDBConnectionString` | `@Microsoft.KeyVault(SecretUri=https://kv-contract-leakage-poc.vault.azure.net/secrets/CosmosDBConnectionString/)` |
   | `StorageConnectionString` | `@Microsoft.KeyVault(SecretUri=https://kv-contract-leakage-poc.vault.azure.net/secrets/StorageConnectionString/)` |
   | `OpenAIKey` | `@Microsoft.KeyVault(SecretUri=https://kv-contract-leakage-poc.vault.azure.net/secrets/OpenAIKey/)` |
   | `OpenAIEndpoint` | `@Microsoft.KeyVault(SecretUri=https://kv-contract-leakage-poc.vault.azure.net/secrets/OpenAIEndpoint/)` |
   | `SearchServiceKey` | `@Microsoft.KeyVault(SecretUri=https://kv-contract-leakage-poc.vault.azure.net/secrets/SearchServiceKey/)` |
   | `SearchServiceEndpoint` | `@Microsoft.KeyVault(SecretUri=https://kv-contract-leakage-poc.vault.azure.net/secrets/SearchServiceEndpoint/)` |
   | `DocumentIntelligenceKey` | `@Microsoft.KeyVault(SecretUri=https://kv-contract-leakage-poc.vault.azure.net/secrets/DocumentIntelligenceKey/)` |
   | `DocumentIntelligenceEndpoint` | `@Microsoft.KeyVault(SecretUri=https://kv-contract-leakage-poc.vault.azure.net/secrets/DocumentIntelligenceEndpoint/)` |
   | `OpenAIDeploymentName` | `gpt-4o-deployment` |
   | `OpenAIEmbeddingDeploymentName` | `text-embedding-deployment` |

4. Click **"Save"** at the top

### Enable Managed Identity

This allows Function App to access Key Vault securely:

1. In your Function App, click **"Identity"** in the left menu
2. Under **"System assigned"** tab, toggle **Status** to **"On"**
3. Click **"Save"**, then **"Yes"** to confirm
4. Copy the **Object (principal) ID** that appears

### Grant Key Vault Access to Function App

1. Go back to your Key Vault: `kv-contract-leakage-poc`
2. Click **"Access policies"** in the left menu
3. Click **"+ Create"**
4. **Permissions**:
   - **Secret permissions**: Check **"Get"** and **"List"**
   - Click **"Next"**
5. **Principal**:
   - Search for `func-contract-leakage-poc`
   - Select your Function App
   - Click **"Next"**
6. Click **"Next"** (skip Application)
7. Click **"Create"**

---

## Step 9: Verify All Resources

Go to your resource group `rg-contract-leakage-poc` and verify you have:

- ✅ Cosmos DB account
- ✅ Storage account
- ✅ Azure OpenAI
- ✅ AI Search service
- ✅ Document Intelligence
- ✅ Key Vault
- ✅ Function App

---

## Next Steps

Your Azure infrastructure is now ready! Next:

1. Clone/set up the backend code locally
2. Configure local development settings
3. Deploy Azure Functions code
4. Test the backend API

---

## Estimated Monthly Costs (POC Usage)

| Service | Pricing Tier | Est. Monthly Cost |
|---------|--------------|-------------------|
| Cosmos DB | Serverless | $5-20 (low usage) |
| Storage | Standard LRS | $1-5 |
| Azure OpenAI | Standard S0 | $20-100 (pay-per-token) |
| AI Search | Basic | ~$75/month |
| Document Intelligence | Free F0 or S0 | $0 or ~$10 |
| Key Vault | Standard | $1 |
| Function App | Consumption | $5-10 (low usage) |
| **Total** | | **~$107-221/month** |

**Cost Optimization Tips**:
- Delete resources when not actively demoing
- Use Free tiers where available (Document Intelligence F0, Cosmos DB free tier)
- Consider AI Search Free tier if available (limited features)
- Monitor costs in Azure Cost Management

---

## Troubleshooting

### Issue: Azure OpenAI not available in my region
**Solution**: Create the OpenAI resource in a supported region like `East US` or `West Europe`, then access it from your Function App (cross-region calls are fine for POC).

### Issue: Can't create Azure OpenAI resource
**Solution**: You need to apply for Azure OpenAI access at https://aka.ms/oai/access. Use mock/placeholder in code until approved.

### Issue: Function App can't access Key Vault secrets
**Solution**:
1. Verify Managed Identity is enabled on Function App
2. Verify access policy is granted in Key Vault
3. Check secret URI format in app settings

---

**Setup Complete!** You can now proceed with backend development.
