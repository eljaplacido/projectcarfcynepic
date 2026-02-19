# CARF UI/UX Documentation

**Version**: 2.0 (React Cockpit)
**Status**: Active
**Supersedes**: Streamlit MVP (removed)

## 1. Overview

The CARF Epistemic Cockpit is implemented as a **React 18 + TypeScript + Vite** SPA in the `carf-cockpit/` directory. It connects to the FastAPI backend for live analysis results.

The previous Streamlit implementation (`src/dashboard/app.py`) has been removed. All UI functionality now lives in the React cockpit.

## 2. Architecture

### 2.1 Component-Based Structure
The cockpit uses a modular React component architecture under `carf-cockpit/src/components/carf/`:
*   **Entry Point**: `DashboardLayout.tsx` handles routing, state, and API calls.
*   **State Management**: React state with live API responses from `POST /query`.
*   **Styling**: Tailwind CSS utility classes.

### 2.2 Key Components

| Component | Purpose |
| :--- | :--- |
| `DashboardLayout` | Main layout, view mode switching, API integration |
| `CausalDAG` | Interactive causal graph visualization (ReactFlow) |
| `BayesianPanel` | Prior/posterior distribution charts (Recharts) |
| `GuardianPanel` | Policy check results and verdict display |
| `ExecutionTrace` | Pipeline step timeline |
| `SimulationArena` | What-if scenario controls |
| `IntelligentChatTab` | Follow-up chat with CARF |
| `AnalysisHistoryPanel` | Analysis comparison and history |

### 2.3 View Modes
Three tailored views: **Analyst**, **Developer**, **Executive** (switchable via tabs).

## 3. API Integration

The cockpit connects to the FastAPI backend:
*   `apiSubmitQuery()` -> `POST /query`
*   Scenario cards -> `GET /scenarios`
*   Dataset upload -> `POST /datasets`

All visualization components receive live results from API responses.

## 4. How to Run
```bash
# Launch Backend (Terminal 1)
python -m src.main

# Launch React Cockpit (Terminal 2)
cd carf-cockpit
npm install
npm run dev
```

Access at http://localhost:5175
