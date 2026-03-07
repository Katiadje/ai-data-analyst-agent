# 🤖 AI Data Analyst Agent

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-4F46E5?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2-7C3AED?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-10B981?style=for-the-badge&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.37-EC4899?style=for-the-badge&logo=streamlit&logoColor=white)
![Azure](https://img.shields.io/badge/Azure_Container_Apps-0078D4?style=for-the-badge&logo=microsoft-azure&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)

**An autonomous AI agent that turns any CSV or Excel dataset into a full analytical report — profiling, insights, visualizations, narrative — automatically.**

### 🚀 [Live Demo](https://ca-ai-analyst-app-prod.delightfulsky-02ee6e1c.westeurope.azurecontainerapps.io)

</div>

---

## ✨ What It Does

Drop a dataset. The agent handles everything:

| Step | Description |
|------|-------------|
| **1. Profiling** | Type detection, missing value analysis, statistical summary |
| **2. Insights** | LLM identifies patterns, correlations, anomalies & business implications |
| **3. Visualization** | Agent selects and generates the most impactful charts |
| **4. Code Gen** | LLM writes Python viz code executed in a sandboxed environment |
| **5. Report** | Full narrative Markdown report with executive summary & recommendations |

**Supported:** CSV, Excel (`.xlsx`, `.xls`) — up to 50 MB

---

## 🏗️ Architecture

```
User → Streamlit UI → FastAPI (async) → LangGraph Agent
                                              │
                          load → profile → insights
                               → plan_viz → generate_viz
                               → write_report → done
```

**Stack:** LangGraph · FastAPI · Streamlit · Pandas · Seaborn · Azure Container Apps · Terraform · Docker · GitHub Actions

---

## 🚀 Quick Start

```bash
git clone https://github.com/Katiadje/ai-data-analyst-agent.git
cd ai-data-analyst-agent

cp .env.example .env
# Add your API key (OpenAI or Groq — free tier works)

docker compose up -d
# UI  → http://localhost:8501
# API → http://localhost:8000/docs
```

---

## ☁️ Deploy to Azure

```bash
cd infra
terraform init
terraform apply -var-file="terraform.tfvars" -auto-approve

# Then push images to ACR
az acr login --name acraianalyst
docker build -f docker/Dockerfile.api -t acraianalyst.azurecr.io/ai-analyst-api:latest .
docker push acraianalyst.azurecr.io/ai-analyst-api:latest
docker build -f docker/Dockerfile.app -t acraianalyst.azurecr.io/ai-analyst-app:latest .
docker push acraianalyst.azurecr.io/ai-analyst-app:latest
```

Infrastructure provisioned: ACR · Container Apps · Storage Account · Log Analytics

---

## 📡 API

```http
POST /api/v1/upload          # Upload CSV/Excel
POST /api/v1/analyse/{id}    # Start analysis (async, returns 202)
GET  /api/v1/analyse/{id}    # Poll status & results
DELETE /api/v1/analyse/{id}  # Cleanup session
```

---

## 🧪 Tests

```bash
make test        # Run test suite
make test-cov    # With coverage report
```

---

## 📁 Structure

```
├── agent/          # LangGraph pipeline (nodes, state, prompts)
├── api/            # FastAPI backend + routes
├── app/            # Streamlit frontend
├── infra/          # Terraform (Azure)
├── docker/         # Dockerfiles
├── tests/          # Test suite
└── .github/        # CI/CD (lint → test → build → deploy)
```

---

## 👤 Author

**[Katiadje](https://github.com/Katiadje)** — Generative AI Engineer · M2 Développement & Data