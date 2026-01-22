---
description: Start development servers for CARF (API + Frontend)
---

# Dev Server Workflow

Start both backend API and frontend Vite dev servers.

// turbo-all

## Prerequisites
- Python 3.11+ with venv activated
- Node.js 18+ installed
- `.env` file configured with API keys

## Steps

1. Start the FastAPI backend server:
```bash
cd c:\Users\35845\Desktop\DIGICISU\projectcarf
python -m uvicorn src.main:app --reload --port 8000
```

2. In a separate terminal, start the Vite frontend:
```bash
cd c:\Users\35845\Desktop\DIGICISU\projectcarf\carf-cockpit
npm run dev
```

## Access Points
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173

## Troubleshooting
- If port 8000 is in use: `--port 8001`
- If Vite fails: `npm install` first
- If LLM errors: Check `OPENAI_API_KEY` or `DEEPSEEK_API_KEY` in `.env`
