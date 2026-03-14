# CARF Platform UIX & Feature Evaluation Report

## 1. Executive Summary

The CARF platform currently demonstrates a **bifurcated maturity level**:
*   **Simulated Use Cases**: **High Maturity**. The "Scenario" usage flow is polished, functional, and visually rich. It successfully demonstrates the value proposition using pre-loaded payloads.
*   **User Data Integration**: **Low Maturity (UI-only)**. While the backend supports a Dataset Registry and dynamic querying, the User Interface (Streamlit) **lacks the widgets/flows to leverage this**. The "Bring Your Own Data" experience is currently a text-based placeholder.
*   **Documentation Alignment**: **Low**. The primary design document (`UI_UIX.md`) describes a React/Next.js architecture that does not exist. The actual implementation is a (very capable) Streamlit application.

## 2. Feature & Flow Evaluation

### 2.1 Simulated Use Cases (The "Scenario" Flow)
*   **Status**: ✅ **Mature & Polished**
*   **User Flow**: Users select a scenario (e.g., "Scope 3 Attribution") from the header. This triggers a backend fetch to `/scenarios/{id}`, loading a full context payload. The Dashboard then renders:
    *   **Interactive Components**: Causal DAGs (Graphviz), Bayesian Belief plots (Altair), and Guardian Policy checks.
    *   **Feedback Loops**: Use of "Demo Prompts" works seamlessly to trigger analysis.
*   **Strengths**: Visuals are excellent (custom CSS "Glassmorphism" in Streamlit). The 3-column layout (Inputs | Analysis | Audit) maps well to the cognitive model.

### 2.2 User Data Integration (The "Custom" Flow)
*   **Status**: ⚠️ **Incomplete (Backend Ready, UI Missing)**
*   **Backend Capabilities**: The API (`src/main.py`) **is fully ready**.
    *   `POST /datasets`: Supports uploading datasets to a local registry.
    *   `POST /query`: Accepts `dataset_selection` to run analysis on user data.
*   **UI Gap**: The Streamlit interface (`src/dashboard/app.py`) has **no mechanism** to:
    1.  Upload a CSV file.
    2.  Call `POST /datasets`.
    3.  Select a newly created dataset for analysis.
*   **Current Experience**: The "Custom guidance" mode merely displays static text instructions ("Define treatment, outcome..."), leaving the user with no valid actions to take.

### 2.3 Documentation vs. Reality
*   **Identity Crisis**: `docs/UI_UIX.md` describes a React Component library (`src/components/carf/DashboardHeader.tsx`, `CausalDAG.tsx`). **These files do not exist.** The actual implementation is a monolithic Streamlit file (`src/dashboard/app.py`).
*   **User Stories**:
    *   *Story 1 (Approvals)*: Simulated well via "Guardian Panel".
    *   *Story 2 (Data Scientist)*: Claims "Interactive node selection" in DAGs. The Streamlit Graphviz implementation is static; users cannot click nodes to highlight Markov blankets as promised.

## 3. Deep Dive Findings

### 3.1 Coherence of User Stories & Error Handling
*   **Inputs/Outputs**: Well-defined for the API (`QueryRequest`, `QueryResponse`).
*   **Error Handling**:
    *   **Backend**: robust `HTTPException` usage.
    *   **Frontend**: Basic `try/except` blocks that catch generic exceptions. If the backend returns a specific validation error (e.g., "Dataset too large"), the UI may just show a generic "Analysis failed" message without parsing the detail.

### 3.2 Codebase Quality (UI)
*   The Streamlit code is **high quality** but **brittle**. It relies on ~600 lines of raw CSS injection (`inject_custom_css`) to fight Streamlit's default styling. This makes it hard to maintain and prone to breaking with Streamlit updates.

## 4. Recommendations & Roadmap

### 4.1 Immediate Fixes (The "Bridge")
1.  **Implement Data Onboarding in Streamlit**:
    *   Add `st.file_uploader` to the "Custom" tab.
    *   Wire it to `POST /datasets`.
    *   Add a `st.selectbox` to choose from uploaded datasets (linking to `dataset_selection` in the query API).
2.  **Sync Documentation**:
    *   Rename `UI_UIX.md` to `UI_UIX_VISION_REACT.md` (making it clear it's a future goal).
    *   Create `UI_UIX_CURRENT_STREAMLIT.md` documenting the actual `app.py` architecture.

### 4.2 Strategic Improvements
1.  **Move to React (Eventual Goal)**: The custom CSS in Streamlit is a temporary patch. To achieve the interactivity promised in `UI_UIX.md` (e.g., clickable DAG nodes), a move to a true frontend framework (React/Next.js) is necessary.
2.  **Interactive Visuals**: Replace `st.graphviz_chart` with a Streamlit Component wrapper for `react-force-graph` or similar to enable the "Markov blanket highlighting" feature.

## 5. Conclusion
The platform is a "Potemkin Village" of high-fidelity simulation but fully functional logic. The backend is solid and ready for user data. The UI looks beautiful but restricts users to the "happy path" of pre-canned demos. **Prioritizing the CSV Upload widget in Streamlit is the highest leverage action to unlock true platform value.**
