---
description: Start and manage CARF development servers (API, Streamlit, React cockpit)
---

# CARF Dev Server Skill

## Purpose
Start/stop development servers for local development, demos, and verification.

## When to Use
- Starting local development session
- Running demos for stakeholders
- Verifying UI/API changes
- Integration testing

## Components

| Component | Port | Purpose |
|-----------|------|---------|
| FastAPI | 8000 | Backend API (`/query`, `/scenarios`, `/datasets`) |
| Streamlit | 8501 | Legacy Epistemic Cockpit (3 view modes) |
| React | 5173 | Platform Cockpit (Vite dev server) |

## Execution Steps

### Start All Servers

#### 1. Start Backend API
```powershell
cd c:\Users\35845\Desktop\DIGICISU\projectcarf
.venv\Scripts\python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verification:**
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", ...}
```

#### 2. Start Streamlit Dashboard (Optional)
Open a new terminal:
```powershell
cd c:\Users\35845\Desktop\DIGICISU\projectcarf
.venv\Scripts\python -m streamlit run src/dashboard/app.py --server.port 8501
```

**URL:** http://localhost:8501

#### 3. Start React Cockpit
Open a new terminal:
```powershell
cd c:\Users\35845\Desktop\DIGICISU\projectcarf\carf-cockpit
npm run dev
```

**URL:** http://localhost:5173

## Environment Variables

Ensure `.env` file exists with required variables:

```bash
# Required
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...

# Optional for full stack
NEO4J_URI=bolt://localhost:7687
CARF_API_URL=http://localhost:8000
```

## Docker Compose (Alternative)

For full stack with Neo4j, Kafka, and OPA:

```bash
cd c:\Users\35845\Desktop\DIGICISU\projectcarf
docker-compose up -d
```

**Services Started:**
- Neo4j: http://localhost:7474
- API: http://localhost:8000
- Streamlit: http://localhost:8501

## Troubleshooting

### Port Already in Use
```powershell
# Find process using port
netstat -ano | findstr :8000

# Kill process by PID
taskkill /PID <pid> /F
```

### API Not Responding
1. Check if uvicorn started without errors
2. Verify `.env` file exists
3. Check `DEEPSEEK_API_KEY` is set

### React Dev Server Issues
```powershell
cd carf-cockpit
rm -rf node_modules
npm install
npm run dev
```

## Verification Checklist

| Server | Check | Expected |
|--------|-------|----------|
| API | `GET /health` | `{"status": "healthy"}` |
| API | `GET /scenarios` | List of 5 demo scenarios |
| Streamlit | Dashboard loads | 3 view mode tabs visible |
| React | Cockpit loads | DashboardLayout renders |
