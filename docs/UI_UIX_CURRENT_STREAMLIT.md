# CARF UI/UX Documentation (Current Implementation)

**Version**: 1.0 (Streamlit MVP)
**Status**: Active / Production
**Related Docs**: [Vision (React)](UI_UIX_VISION_REACT.md)

## 1. Overview

The current CARF Epistemic Cockpit is implemented as a **Streamlit** application (`src/dashboard/app.py`). It provides a high-fidelity simulation of the "Two-Speed Cognitive Model" (Fast vs. Slow thinking) required by the [PRD](../PRD.md).

While the long-term vision is a React micro-frontend architecture, the current implementation achieves visual parity using custom CSS injection and Python-based component rendering.

## 2. Architecture

### 2.1 Monolithic Structure
The entire dashboard logic resides in `src/dashboard/app.py`.
*   **Entry Point**: `main()` function handles routing (tabs) and state initialization.
*   **State Management**: Uses `st.session_state` to persist:
    *   `session_id`
    *   `scenarios` (fetched from API)
    *   `analysis_result` (from `POST /query`)
    *   `selected_scenario`

### 2.2 Styling System
The application uses a "Glassmorphism" aesthetic built on Tailwind-like color tokens, injected via `inject_custom_css()`.
*   **Theme**: Fixed Light Theme (hardcoded tokens).
*   **CSS Injection**: ~600 lines of CSS override Streamlit's default padding, fonts, and widget styling.

## 3. Core Components

### 3.1 `render_dashboard_header()`
*   **Function**: Displays branding, session ID, and the **Scenario Selector**.
*   **Data Flow**: Fetches scenarios from `GET /scenarios`. selecting a scenario updates `st.session_state["selected_scenario"]`.

### 3.2 `render_guided_walkthrough()`
*   **Function**: Provides the "Demo" experience.
*   **Modes**:
    *   **Guided Demo**: Offers distinct buttons to populate the query input with "Scenario-aware" prompts.
    *   **Custom Guidance**: Static text explaining how to form a custom query (currently incomplete functionality).

### 3.3 `render_causal_dag()`
*   **Implementation**: Uses `st.graphviz_chart`.
*   **Limitation**: Static rendering. Nodes are **not clickable**. The "Highlight Markov Blanket" feature described in the vision doc is simulated or missing.

### 3.4 `render_bayesian_belief_state()`
*   **Implementation**: Uses `Altair` charts to render Prior vs. Posterior distributions.
*   **Data**: Currently uses mock distribution generation (`numpy` logic inside the component) for demo purposes, unless overridden by API data.

### 3.5 `render_guardian_policy_check()`
*   **Function**: Simulates the "Fast Thinking" approval gate.
*   **Flow**:
    *   Displays policy pass/fail status.
    *   Provides "Approve/Reject" buttons (simulating HumanLayer interaction).

## 4. API Integration

The dashboard connects to the backend (`src.main`) via `urllib`:
*   `_fetch_scenarios()` -> `GET /scenarios`
*   `_run_analysis()` -> `POST /query`

### Payload Handling
When a Scenario is selected (e.g., "Scope 3 Attribution"), the dashboard fetches its full JSON payload (context, causal graph structure, etc.) and injects it into the `/query` call. This allows the backend to perform "real" analysis on predefined data.

## 5. Known Limitations & Roadmap

| Feature | Status | Constraint |
| :--- | :--- | :--- |
| **User Data Upload** | ❌ Missing | No `file_uploader` widget. Backend assumes local file path or API payload. |
| **Interactive Graphs** | ⚠️ Static | Graphviz generates images, not interactive DOM elements. |
| **Theming** | ⚠️ Partial | Dark mode tokens exist but are currently overridden by Light mode defaults. |

## 6. How to Run
```bash
# Launch Backend
python -m src.main

# Launch Dashboard (in separate terminal)
streamlit run src/dashboard/app.py
```
