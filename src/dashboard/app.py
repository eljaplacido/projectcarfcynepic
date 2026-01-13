"""CARF Epistemic Cockpit - Modern UI/UX Implementation.

Implements the Two-Speed Cognitive Model with component architecture
matching the flow-visualizer reference design.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import random
from datetime import datetime
from typing import Any
from urllib import error, request

import streamlit as st

from src.services import get_neo4j_service


# =============================================================================
# DESIGN SYSTEM TOKENS - LIGHT THEME
# =============================================================================

COLORS = {
    # Primary palette
    "primary": "#7C3AED",
    "primary_light": "#A78BFA",
    "accent": "#10B981",
    "accent_light": "#34D399",

    # Backgrounds - LIGHT THEME
    "bg_page": "#F8FAFC",
    "bg_card": "#FFFFFF",
    "bg_muted": "#F1F5F9",
    "bg_input": "#FFFFFF",

    # Text
    "text_primary": "#0F172A",
    "text_secondary": "#475569",
    "text_muted": "#94A3B8",

    # Borders
    "border": "#E2E8F0",
    "border_light": "#F1F5F9",

    # Status colors
    "status_success": "#10B981",
    "status_warning": "#F59E0B",
    "status_error": "#EF4444",
    "status_info": "#3B82F6",

    # Confidence levels
    "confidence_high": "#10B981",
    "confidence_medium": "#F59E0B",
    "confidence_low": "#EF4444",

    # Cynefin domains
    "cynefin_clear": "#10B981",
    "cynefin_complicated": "#3B82F6",
    "cynefin_complex": "#8B5CF6",
    "cynefin_chaotic": "#EF4444",

    # Chart colors
    "chart_1": "#3B82F6",
    "chart_2": "#10B981",
    "chart_3": "#F59E0B",
    "chart_4": "#8B5CF6",
    "chart_5": "#EC4899",
}

CYNEFIN_CONFIG = {
    "clear": {"label": "Clear", "color": COLORS["cynefin_clear"], "bg": "rgba(16, 185, 129, 0.1)", "desc": "Best practice - Sense, Categorize, Respond"},
    "complicated": {"label": "Complicated", "color": COLORS["cynefin_complicated"], "bg": "rgba(59, 130, 246, 0.1)", "desc": "Expert analysis - Sense, Analyze, Respond"},
    "complex": {"label": "Complex", "color": COLORS["cynefin_complex"], "bg": "rgba(139, 92, 246, 0.1)", "desc": "Emergent practice - Probe, Sense, Respond"},
    "chaotic": {"label": "Chaotic", "color": COLORS["cynefin_chaotic"], "bg": "rgba(239, 68, 68, 0.1)", "desc": "Novel practice - Act, Sense, Respond"},
}

SUGGESTED_QUERIES = [
    "Which suppliers have the highest emissions reduction potential?",
    "What ROI can we expect from renewable energy investments?",
    "How do shipping mode changes affect our carbon footprint?",
]


# =============================================================================
# CUSTOM CSS STYLING - LIGHT THEME
# =============================================================================

def inject_custom_css() -> None:
    """Inject modern CSS styling for the dashboard - LIGHT THEME."""
    st.markdown(f"""
    <style>
    /* Global Styles - LIGHT THEME */
    .stApp {{
        background-color: {COLORS["bg_page"]};
    }}

    .main .block-container {{
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }}

    /* Typography */
    h1, h2, h3, h4, h5, h6 {{
        color: {COLORS["text_primary"]} !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}

    p, span, label, .stMarkdown {{
        color: {COLORS["text_secondary"]} !important;
    }}

    /* Card Component - Light Theme */
    .card {{
        background: {COLORS["bg_card"]};
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        border: 1px solid {COLORS["border"]};
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}

    .card-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
    }}

    .card-title {{
        font-size: 14px;
        font-weight: 600;
        color: {COLORS["text_primary"]};
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    /* Badge Component */
    .badge {{
        display: inline-flex;
        align-items: center;
        padding: 6px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 500;
    }}

    .badge-primary {{
        background: {COLORS["primary"]};
        color: white;
    }}

    .badge-success {{
        background: rgba(16, 185, 129, 0.15);
        color: {COLORS["status_success"]};
    }}

    .badge-warning {{
        background: rgba(245, 158, 11, 0.15);
        color: {COLORS["status_warning"]};
    }}

    .badge-error {{
        background: rgba(239, 68, 68, 0.15);
        color: {COLORS["status_error"]};
    }}

    .badge-info {{
        background: rgba(59, 130, 246, 0.15);
        color: {COLORS["status_info"]};
    }}

    .badge-complicated {{
        background: {COLORS["cynefin_complicated"]};
        color: white;
    }}

    /* Suggested Query Cards */
    .query-card {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.2s;
        color: {COLORS["chart_1"]};
        font-size: 13px;
        font-weight: 500;
    }}

    .query-card:hover {{
        border-color: {COLORS["chart_1"]};
        background: rgba(59, 130, 246, 0.05);
    }}

    /* Stats Box */
    .stat-box {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        padding: 16px;
    }}

    .stat-value {{
        font-size: 28px;
        font-weight: 700;
        color: {COLORS["text_primary"]};
    }}

    .stat-label {{
        font-size: 12px;
        color: {COLORS["text_muted"]};
        margin-top: 4px;
    }}

    /* Progress Bar */
    .progress-bar {{
        height: 6px;
        background: {COLORS["border"]};
        border-radius: 3px;
        overflow: hidden;
    }}

    .progress-fill {{
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }}

    /* Timeline */
    .timeline-item {{
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 16px;
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }}

    .timeline-item:hover {{
        border-color: {COLORS["primary"]};
    }}

    .timeline-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-top: 4px;
        flex-shrink: 0;
    }}

    .timeline-content {{
        flex: 1;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}

    .timeline-title {{
        font-size: 14px;
        font-weight: 500;
        color: {COLORS["text_primary"]};
    }}

    .timeline-time {{
        font-size: 12px;
        color: {COLORS["text_muted"]};
        font-family: monospace;
        background: {COLORS["bg_muted"]};
        padding: 2px 8px;
        border-radius: 4px;
    }}

    /* Confidence Indicator */
    .confidence-indicator {{
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px 16px;
        border-radius: 8px;
        margin-top: 12px;
    }}

    .confidence-high {{
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.2);
    }}

    .confidence-medium {{
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.2);
    }}

    .confidence-low {{
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.2);
    }}

    /* Policy Check Item */
    .policy-item {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        background: {COLORS["bg_card"]};
        border-radius: 8px;
        margin-bottom: 8px;
        border: 1px solid {COLORS["border"]};
    }}

    .policy-item-pass {{
        border-left: 3px solid {COLORS["status_success"]};
    }}

    .policy-item-fail {{
        border-left: 3px solid {COLORS["status_error"]};
    }}

    .policy-item-pending {{
        border-left: 3px solid {COLORS["status_warning"]};
    }}

    /* Action Buttons */
    .stButton > button {{
        border-radius: 8px !important;
        font-weight: 500 !important;
        padding: 12px 24px !important;
        transition: all 0.2s !important;
    }}

    .stButton > button[kind="primary"] {{
        background: {COLORS["status_success"]} !important;
        color: white !important;
        border: none !important;
    }}

    .stButton > button[kind="secondary"] {{
        background: transparent !important;
        color: {COLORS["text_secondary"]} !important;
        border: 1px solid {COLORS["border"]} !important;
    }}

    /* Slider Customization */
    .stSlider > div > div {{
        background: {COLORS["border"]} !important;
    }}

    .stSlider > div > div > div {{
        background: {COLORS["primary"]} !important;
    }}

    /* Input Customization */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background: {COLORS["bg_card"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        color: {COLORS["text_primary"]} !important;
        border-radius: 8px !important;
    }}

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {COLORS["primary"]} !important;
        box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.1) !important;
    }}

    /* Tab Navigation */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background: {COLORS["bg_muted"]};
        padding: 4px;
        border-radius: 10px;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
        color: {COLORS["text_secondary"]};
    }}

    .stTabs [aria-selected="true"] {{
        background: white !important;
        color: {COLORS["text_primary"]} !important;
    }}

    /* DAG Legend */
    .dag-legend {{
        display: flex;
        gap: 16px;
        padding: 12px 16px;
        background: {COLORS["bg_muted"]};
        border-radius: 8px;
        margin-top: 12px;
    }}

    .legend-item {{
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: {COLORS["text_secondary"]};
    }}

    .legend-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }}

    /* Header Styles */
    .header-container {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        padding: 12px 0;
        margin-bottom: 16px;
    }}

    .scenario-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 9999px;
        font-size: 14px;
        font-weight: 500;
        color: {COLORS["text_primary"]};
    }}

    .scenario-dot {{
        width: 10px;
        height: 10px;
        background: {COLORS["status_success"]};
        border-radius: 50%;
    }}

    .session-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: rgba(16, 185, 129, 0.1);
        border-radius: 9999px;
        font-size: 13px;
        color: {COLORS["status_success"]};
    }}

    .session-dot {{
        width: 8px;
        height: 8px;
        background: {COLORS["status_success"]};
        border-radius: 50%;
        animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}

    /* KPI Card */
    .kpi-card {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 16px;
    }}

    .kpi-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }}

    .kpi-label {{
        font-size: 12px;
        color: {COLORS["text_muted"]};
    }}

    .kpi-value {{
        font-size: 28px;
        font-weight: 700;
        color: {COLORS["text_primary"]};
    }}

    /* Hero Card */
    .hero-card {{
        background: linear-gradient(135deg, {COLORS["bg_card"]} 0%, rgba(124, 58, 237, 0.03) 100%);
        border: 1px solid rgba(124, 58, 237, 0.15);
        border-radius: 16px;
        padding: 32px;
    }}

    /* Proposed Action Card */
    .action-card {{
        background: rgba(16, 185, 129, 0.05);
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 12px;
        padding: 20px;
    }}

    /* Risk Level Badge */
    .risk-badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 12px 24px;
        border-radius: 9999px;
        font-size: 16px;
        font-weight: 700;
        text-transform: uppercase;
    }}

    .risk-low {{
        background: rgba(16, 185, 129, 0.1);
        color: {COLORS["status_success"]};
    }}

    .risk-medium {{
        background: rgba(245, 158, 11, 0.1);
        color: {COLORS["status_warning"]};
    }}

    .risk-high {{
        background: rgba(239, 68, 68, 0.1);
        color: {COLORS["status_error"]};
    }}

    /* HITL Warning */
    .hitl-warning {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px;
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.2);
        border-radius: 8px;
        margin: 16px 0;
    }}

    /* Expander */
    .streamlit-expanderHeader {{
        background: {COLORS["bg_card"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 8px !important;
    }}

    /* Select box */
    .stSelectbox > div > div {{
        background: {COLORS["bg_card"]} !important;
        border-color: {COLORS["border"]} !important;
    }}
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _run_async(coro) -> Any:
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if loop.is_running():
        return None
    return loop.run_until_complete(coro)


def _call_api(url: str, payload: dict[str, Any] | None = None, method: str = "POST") -> dict[str, Any]:
    """Call API endpoint."""
    if payload:
        data = json.dumps(payload).encode("utf-8")
    else:
        data = None

    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def _fetch_scenarios() -> list[dict]:
    """Fetch available scenarios from API."""
    api_url = os.getenv("CARF_API_URL", "http://localhost:8000")
    try:
        response = _call_api(f"{api_url}/scenarios", method="GET")
        return response.get("scenarios", [])
    except Exception:
        return []


def _fetch_scenario_payload(scenario_id: str) -> dict[str, Any]:
    """Fetch scenario payload from API."""
    api_url = os.getenv("CARF_API_URL", "http://localhost:8000")
    try:
        response = _call_api(f"{api_url}/scenarios/{scenario_id}", method="GET")
        return response.get("payload", {})
    except Exception:
        return {}


def _run_analysis(query: str, context: dict | None = None, causal_config: dict | None = None, bayesian_config: dict | None = None) -> dict[str, Any]:
    """Run analysis through CARF API."""
    api_url = os.getenv("CARF_API_URL", "http://localhost:8000")
    payload = {"query": query}
    if context:
        payload["context"] = context
    if causal_config:
        payload["causal_estimation"] = causal_config
    if bayesian_config:
        payload["bayesian_inference"] = bayesian_config

    return _call_api(f"{api_url}/query", payload)


def _generate_session_id() -> str:
    """Generate a session ID."""
    return f"sess_demo_{random.randint(10, 99)}..."


def _get_confidence_color(level: str) -> str:
    """Get color for confidence level."""
    return {
        "high": COLORS["confidence_high"],
        "medium": COLORS["confidence_medium"],
        "low": COLORS["confidence_low"],
    }.get(level, COLORS["text_muted"])


# =============================================================================
# MOCK DATA GENERATORS
# =============================================================================

def _get_mock_execution_trace() -> list[dict]:
    """Generate mock execution trace steps."""
    return [
        {"node": "QueryParser", "status": "success", "duration": 120, "time": "12:30:00 PM"},
        {"node": "CynefinRouter", "status": "success", "duration": 340, "time": "12:30:00 PM"},
        {"node": "CausalAnalyst", "status": "success", "duration": 2310, "time": "12:30:00 PM"},
        {"node": "BayesianUpdater", "status": "success", "duration": 890, "time": "12:30:02 PM"},
        {"node": "Guardian", "status": "warning", "duration": 590, "time": "12:30:03 PM"},
    ]


def _get_mock_policies() -> list[dict]:
    """Generate mock policy checks."""
    return [
        {"name": "Budget Authority", "desc": "Allocation within authorized spending limits", "status": "pass", "version": "v2.1.0"},
        {"name": "ESG Compliance", "desc": "Meets corporate sustainability targets", "status": "pass", "version": "v3.0.1"},
        {"name": "ROI Threshold", "desc": "Expected ROI exceeds minimum threshold of 2.0x", "status": "pass", "version": "v1.5.0"},
        {"name": "Risk Assessment", "desc": "Risk score within acceptable bounds", "status": "pass", "version": "v2.0.0"},
        {"name": "Stakeholder Approval", "desc": "Requires sign-off from Sustainability Committee", "status": "pending", "version": "v1.0.0"},
    ]


def _get_mock_causal_result() -> dict:
    """Generate mock causal analysis result."""
    return {
        "effect": -75,
        "unit": "tonnes CO2e per $1M invested",
        "p_value": 0.0038,
        "ci_low": -97.1,
        "ci_high": -52.9,
        "description": "Each $1M invested in supplier sustainability programs causally reduces Scope 3 emissions by approximately 75 tonnes CO2e annually.",
        "refutations_passed": 4,
        "refutations_total": 5,
        "confounders_controlled": 3,
        "confounders_total": 4,
        "evidence_base": "Based on 45 supplier programs across 12 regions",
        "meta_analysis": True,
        "studies": 45,
    }


def _get_mock_belief_state() -> dict:
    """Generate mock Bayesian belief state."""
    return {
        "variable": "Emissions Reduction",
        "prior_mean": -650.00,
        "prior_std": 120.00,
        "posterior_mean": -750.00,
        "posterior_std": 85.00,
        "ci_95": [-917, -583],
        "epistemic_uncertainty": 0.23,
        "aleatoric_uncertainty": 0.14,
        "total_uncertainty": 0.22,
        "confidence_level": "high",
        "interpretation": "High confidence in emissions reduction estimate. Safe to proceed with decision.",
    }


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_dashboard_header() -> tuple[str, str | None]:
    """Render the centered header with scenario dropdown and session badges."""
    session_id = st.session_state.get("session_id", _generate_session_id())
    st.session_state["session_id"] = session_id

    # Fetch scenarios
    if "scenarios" not in st.session_state:
        st.session_state["scenarios"] = _fetch_scenarios()

    scenarios = st.session_state["scenarios"]
    scenario_names = ["Select Scenario..."] + [s.get("name", s.get("id", "Unknown")) for s in scenarios]

    col1, col2, col3 = st.columns([2, 2, 2])

    with col2:
        selected_idx = st.selectbox(
            "Scenario",
            range(len(scenario_names)),
            format_func=lambda i: scenario_names[i],
            key="header_scenario_select",
            label_visibility="collapsed",
        )

    selected_scenario_id = None
    selected_name = "No Scenario Selected"
    if selected_idx > 0 and scenarios:
        selected_scenario = scenarios[selected_idx - 1]
        selected_scenario_id = selected_scenario.get("id")
        selected_name = selected_scenario.get("name", selected_scenario_id)
        st.session_state["selected_scenario"] = selected_scenario

    st.markdown(f"""
    <div class="header-container">
        <div class="scenario-badge">
            <div class="scenario-dot"></div>
            {selected_name}
        </div>
        <div class="session-badge">
            <div class="session-dot"></div>
            Session: {session_id}
        </div>
    </div>
    """, unsafe_allow_html=True)

    return session_id, selected_scenario_id


def render_guided_walkthrough(
    selected_scenario_id: str | None,
    key_prefix: str = "enduser",
) -> None:
    """Render guided walkthrough for demo and custom onboarding."""
    selected_scenario = st.session_state.get("selected_scenario")
    scenario_name = None
    if isinstance(selected_scenario, dict):
        scenario_name = selected_scenario.get("name") or selected_scenario.get("id")

    with st.container(border=True):
        st.markdown("**:material/assistant: Guided Walkthrough**")
        mode = st.radio(
            "Walkthrough Mode",
            ["Guided demo", "Custom guidance"],
            horizontal=True,
            label_visibility="collapsed",
            key=f"{key_prefix}_walkthrough_mode",
        )

        if mode == "Guided demo":
            st.caption("Run a predefined analysis flow to see the platform end-to-end.")
            st.markdown(
                "- Select a scenario in the header to load context\n"
                "- Pick a guided prompt or write your own question\n"
                "- Click Analyze to run the full pipeline"
            )
            if selected_scenario_id:
                st.success(f"Scenario ready: {scenario_name or selected_scenario_id}")
            else:
                st.info("Pick a scenario from the header to load a demo payload.")

            for idx, suggestion in enumerate(SUGGESTED_QUERIES):
                if st.button(
                    f"Use demo prompt: {suggestion}",
                    key=f"{key_prefix}_demo_prompt_{idx}",
                    use_container_width=True,
                ):
                    st.session_state[f"{key_prefix}_query_input"] = suggestion
        else:
            st.caption("Use this path for your own data, domain routing, and policy setup.")
            st.markdown(
                "**What to include in your question**\n"
                "- Decision you want to make\n"
                "- Outcome you care about (metric)\n"
                "- Intervention or change you are testing\n"
                "- Constraints or approval requirements"
            )

            guided_prompts = [
                "Help me define a causal question using treatment, outcome, and confounders.",
                "Guide me on data I need to run a Bayesian update for this decision.",
                "Explain how to train a domain-specific router for my industry queries.",
                "Outline guardian policy checks needed before acting on this decision.",
            ]
            for idx, prompt in enumerate(guided_prompts):
                if st.button(
                    f"Use guidance prompt: {prompt}",
                    key=f"{key_prefix}_guidance_prompt_{idx}",
                    use_container_width=True,
                ):
                    st.session_state[f"{key_prefix}_query_input"] = prompt

            with st.expander("Router training checklist", expanded=False):
                st.markdown(
                    "- Collect labeled examples per domain\n"
                    "- Train a base model on mixed domains\n"
                    "- Fine-tune on domain-specific examples\n"
                    "- Validate with confusion matrix and thresholds"
                )

            with st.expander("Causal and Bayesian setup hints", expanded=False):
                st.markdown(
                    "- Define treatment, outcome, and confounders\n"
                    "- Confirm data granularity and time windows\n"
                    "- Validate assumptions and refutation tests\n"
                    "- Record priors and evidence sources"
                )

            with st.expander("Guardian policy planning", expanded=False):
                st.markdown(
                    "- Identify approval gates and risk thresholds\n"
                    "- Document prohibited actions and escalation rules\n"
                    "- Map policies to your compliance framework"
                )


def render_query_input(key_prefix: str = "enduser") -> tuple[str, bool]:
    """Render the query input with suggestions."""
    query = st.text_area(
        "Ask a question about your data...",
        placeholder="Ask a question about your data...",
        height=80,
        key=f"{key_prefix}_query_input",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; height: 40px; cursor: pointer;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{COLORS["text_muted"]}" stroke-width="2">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        # Custom styled Analyze button
        st.markdown(f"""
        <style>
            div[data-testid="stButton"][data-baseweb="button"] button[kind="primary"] {{
                background: linear-gradient(135deg, {COLORS["chart_1"]} 0%, {COLORS["primary"]} 100%) !important;
                border: none !important;
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
            }}
        </style>
        """, unsafe_allow_html=True)
        analyze_clicked = st.button("Analyze", use_container_width=True, type="primary", key=f"{key_prefix}_analyze_btn")

    st.markdown(f'<p style="font-size: 11px; color: {COLORS["text_muted"]}; margin: 20px 0 12px 0; text-transform: uppercase; letter-spacing: 0.5px;">Suggested Queries</p>', unsafe_allow_html=True)

    for idx, suggestion in enumerate(SUGGESTED_QUERIES):
        if st.button(
            suggestion,
            key=f"{key_prefix}_suggestion_{idx}",
            use_container_width=True,
        ):
            st.session_state[f"{key_prefix}_query_input"] = suggestion

    return query, analyze_clicked


def render_simulation_controls(key_prefix: str = "enduser") -> dict:
    """Render simulation control sliders."""
    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <span class="card-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="{COLORS["text_secondary"]}" stroke-width="2">
                    <line x1="4" y1="21" x2="4" y2="14"/>
                    <line x1="4" y1="10" x2="4" y2="3"/>
                    <line x1="12" y1="21" x2="12" y2="12"/>
                    <line x1="12" y1="8" x2="12" y2="3"/>
                    <line x1="20" y1="21" x2="20" y2="16"/>
                    <line x1="20" y1="12" x2="20" y2="3"/>
                    <line x1="1" y1="14" x2="7" y2="14"/>
                    <line x1="9" y1="8" x2="15" y2="8"/>
                    <line x1="17" y1="16" x2="23" y2="16"/>
                </svg>
                Simulation Controls
            </span>
            <span style="font-size: 12px; color: {COLORS["text_muted"]}; cursor: pointer; display: flex; align-items: center; gap: 4px;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="{COLORS["text_muted"]}" stroke-width="2">
                    <path d="M1 4v6h6"/>
                    <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
                </svg>
                Reset
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    investment_mult = st.slider(
        "Investment Multiplier",
        min_value=0.5,
        max_value=2.0,
        value=1.00,
        step=0.01,
        format="%.2fx",
        key=f"{key_prefix}_investment_mult",
    )

    confidence_threshold = st.slider(
        "Confidence Threshold",
        min_value=50,
        max_value=100,
        value=70,
        step=1,
        format="%d%%",
        key=f"{key_prefix}_confidence_threshold",
    )

    uncertainty_tolerance = st.slider(
        "Uncertainty Tolerance",
        min_value=0,
        max_value=100,
        value=30,
        step=1,
        key=f"{key_prefix}_uncertainty_tolerance",
    )

    policy_strictness = st.selectbox(
        "Policy Strictness",
        ["Standard", "Strict", "Lenient"],
        index=0,
        key=f"{key_prefix}_policy_strictness",
    )

    return {
        "investment_multiplier": investment_mult,
        "confidence_threshold": confidence_threshold / 100,
        "uncertainty_tolerance": uncertainty_tolerance / 100,
        "policy_strictness": policy_strictness.lower(),
    }


def render_cynefin_classification(domain: str = "complicated", confidence: float = 0.61, entropy: float = 0.32) -> None:
    """Render Cynefin domain classification panel."""
    config = CYNEFIN_CONFIG.get(domain, CYNEFIN_CONFIG["complicated"])

    # Domain scores for visualization
    domain_scores = {
        "clear": 12,
        "complicated": 87,
        "complex": 45,
        "chaotic": 8,
    }

    with st.container(border=True):
        # Header row
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**:material/info: Cynefin Classification**")
        with col2:
            st.markdown(f'<span style="background: {config["color"]}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500;">{config["label"]}</span>', unsafe_allow_html=True)

        st.caption(config['desc'])

        # Metrics row
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Signal Entropy")
            st.markdown(f"**`{entropy:.2f}`**")
            st.progress(entropy)
        with col2:
            st.caption("Confidence")
            st.markdown(f"**{confidence * 100:.0f}%**")
            st.progress(confidence)

        # Routed to box
        st.info(f":material/route: Routed to: **CausalAnalyst**")

        # Domain scores expander
        with st.expander("View domain scores"):
            for domain_key, label, color in [
                ("clear", "Clear", COLORS["cynefin_clear"]),
                ("complicated", "Complicated", COLORS["cynefin_complicated"]),
                ("complex", "Complex", COLORS["cynefin_complex"]),
                ("chaotic", "Chaotic", COLORS["cynefin_chaotic"]),
            ]:
                score = domain_scores[domain_key]
                col1, col2, col3 = st.columns([2, 5, 1])
                with col1:
                    st.markdown(f'<span style="color: {color}; font-weight: 500;">{label}</span>', unsafe_allow_html=True)
                with col2:
                    st.progress(score / 100)
                with col3:
                    st.markdown(f"**{score}%**")

            st.caption("Linear supply chain relationships with measurable intervention points. Expert analysis required but deterministic outcomes expected.")


def render_bayesian_belief_state(belief: dict | None = None) -> None:
    """Render Bayesian belief state visualization with actual chart."""
    if belief is None:
        belief = _get_mock_belief_state()

    variable_options = ["Investment ROI", "Emissions Reduction", "Cost Savings", "Risk Score"]

    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("**:material/monitoring: Bayesian Belief State**")
        with col2:
            st.selectbox(
                "Variable",
                variable_options,
                index=0,
                key="bayesian_variable_select",
                label_visibility="collapsed",
            )

    # Generate distribution data for chart
    import numpy as np
    import pandas as pd
    import altair as alt

    # Use ROI-like values for the chart (matching screenshot: 2-5 range)
    roi_mean = 3.20
    roi_std = 0.45
    prior_mean = 3.0
    prior_std = 0.6

    x = np.linspace(2, 5, 100)
    prior_y = (1/(prior_std * np.sqrt(2*np.pi))) * np.exp(-0.5*((x - prior_mean)/prior_std)**2)
    posterior_y = (1/(roi_std * np.sqrt(2*np.pi))) * np.exp(-0.5*((x - roi_mean)/roi_std)**2)

    chart_data = pd.DataFrame({
        "x": x,
        "Prior": prior_y,
        "Posterior": posterior_y,
    })

    area = alt.Chart(chart_data).mark_area(opacity=0.2, color=COLORS["chart_1"]).encode(
        x=alt.X("x", title=""),
        y=alt.Y("Posterior", title=""),
    )
    prior = alt.Chart(chart_data).mark_line(color=COLORS["text_muted"], strokeDash=[4, 4]).encode(
        x="x",
        y="Prior",
    )
    st.altair_chart((area + prior).properties(height=150), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Posterior Mean")
        st.markdown("**3.20**")
        st.caption("+/- 0.45 std")
    with col2:
        st.caption("95% CI")
        st.markdown("**[2, 4]**")

    st.markdown("**Uncertainty Decomposition**")
    for label, value in [
        ("Epistemic", 0.20),
        ("Aleatoric", 0.09),
        ("Total", 0.17),
    ]:
        col1, col2, col3 = st.columns([2, 5, 1])
        with col1:
            st.caption(label)
        with col2:
            st.progress(value)
        with col3:
            st.caption(f"{int(value * 100)}%")

    st.success("High confidence. Strong positive ROI expected with narrow confidence interval.")

    with st.expander("How to interpret this belief state", expanded=False):
        st.markdown(
            "- Posterior mean is the updated best estimate after evidence\n"
            "- The shaded curve shows the distribution of likely outcomes\n"
            "- A tighter confidence interval means lower uncertainty\n"
            "- Epistemic uncertainty can be reduced with more data"
        )

    st.markdown("**Belief Evolution**")

    # Simple trend line for belief evolution
    evolution_data = pd.DataFrame({
        "Quarter": ["Q2 2024", "Q3 2024", "Q4 2024"],
        "Belief": [2.8, 3.0, 3.2],
    })
    st.line_chart(evolution_data, x="Quarter", y="Belief", height=80, use_container_width=True)


def render_causal_dag() -> None:
    """Render interactive Causal DAG visualization."""
    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <span class="card-title">Causal DAG</span>
            <div style="display: flex; gap: 8px; align-items: center;">
                <span style="font-size: 12px; color: {COLORS["text_muted"]};">100%</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        show_confounders = st.toggle("Show Confounders", value=True, key="dag_show_confounders")
    with col2:
        highlight_backdoor = st.toggle("Highlight Backdoor Paths", value=False, key="dag_highlight_backdoor")

    # Render graph using Streamlit's graphviz
    dot_code = """
    digraph G {
        bgcolor="transparent";
        node [fontname="Inter", fontsize=10, style=filled];
        edge [fontname="Inter", fontsize=9, color="#94A3B8"];

        // Nodes
        "Supplier\\nPrograms" [fillcolor="#3B82F6", fontcolor="white", shape=hexagon];
        "Emissions" [fillcolor="#10B981", fontcolor="white", shape=circle];
        "Sustainability" [fillcolor="#3B82F6", fontcolor="white", shape=hexagon];
        "Scope 3\\nEmissions" [fillcolor="#F59E0B", fontcolor="white", shape=doublecircle];
        "Production URL" [fillcolor="#10B981", fontcolor="white", shape=circle];
        "Energy Source Mix" [fillcolor="#3B82F6", fontcolor="white", shape=hexagon];
        "Market Conditions" [fillcolor="#8B5CF6", fontcolor="white", shape=diamond];

        // Edges
        "Supplier\\nPrograms" -> "Emissions" [label="+0.42", color="#10B981", penwidth=2];
        "Sustainability" -> "Emissions" [label="+0.33"];
        "Emissions" -> "Scope 3\\nEmissions" [label="+0.67", color="#10B981", penwidth=2];
        "Production URL" -> "Scope 3\\nEmissions" [label="+0.28"];
        "Energy Source Mix" -> "Emissions" [label="+0.15"];
        "Market Conditions" -> "Scope 3\\nEmissions" [style=dashed, label="-0.08"];
    }
    """

    st.graphviz_chart(dot_code, use_container_width=True)

    st.markdown(f"""
    <div class="dag-legend">
        <div class="legend-item">
            <div class="legend-dot" style="background: {COLORS["chart_1"]};"></div>
            Variable
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background: {COLORS["chart_4"]};"></div>
            Confounder
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background: {COLORS["chart_2"]};"></div>
            Intervention
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background: {COLORS["chart_3"]};"></div>
            Outcome
        </div>
        <div style="flex: 1;"></div>
        <span style="font-size: 12px; color: {COLORS["text_muted"]};">6 nodes - 6 edges</span>
    </div>
    """, unsafe_allow_html=True)


def render_causal_analysis_results(result: dict | None = None) -> None:
    """Render causal analysis results card."""
    if result is None:
        result = _get_mock_causal_result()

    ci_low = float(result["ci_low"])
    ci_high = float(result["ci_high"])
    ci_min = min(ci_low, ci_high)
    ci_max = max(ci_low, ci_high)

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**:material/biotech: Causal Analysis Results**")
        with col2:
            badge_text = f'{result["refutations_passed"]}/{result["refutations_total"]} Refutations Passed'
            st.markdown(
                f'<span style="background: rgba(239, 68, 68, 0.15); color: {COLORS["status_error"]}; '
                f'padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;">{badge_text}</span>',
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            st.caption("Causal Effect Estimate")
            st.markdown(f"## {result['effect']}")
            st.caption(result["unit"])
            st.caption(f"p-value: {result['p_value']}")

        st.caption("95% Confidence Interval")
        st.slider(
            "Confidence Interval",
            min_value=ci_min,
            max_value=ci_max,
            value=(ci_low, ci_high),
            step=0.1,
            disabled=True,
            label_visibility="collapsed",
            key="causal_ci_slider",
        )

        st.caption(result["description"])

    with st.expander("How to interpret these results", expanded=False):
        st.markdown(
            "- Effect size estimates the causal impact of the intervention\n"
            "- The confidence interval shows a plausible range for the effect\n"
            "- Lower p-values suggest stronger evidence for the effect\n"
            "- Refutation tests help stress-check the causal claim"
        )

    with st.expander("Refutation Tests", expanded=False):
        st.caption(f'{result["refutations_passed"]}/{result["refutations_total"]} passed')
        tests = [
            ("Placebo Treatment", True, 0.823),
            ("Random Common Cause", True, 0.912),
            ("Data Subset", True, 0.876),
            ("Unobserved Confounder", True, 0.654),
            ("Bootstrap Refute", False, 0.043),
        ]
        for name, passed, p_val in tests:
            icon = ":material/check_circle:" if passed else ":material/cancel:"
            status = "passed" if passed else "failed"
            col1, col2, col3 = st.columns([0.3, 3, 1])
            with col1:
                st.markdown(icon)
            with col2:
                st.markdown(f"**{name}**")
                st.caption(f"p={p_val}")
            with col3:
                st.caption(status)

    with st.expander("Confounders Controlled", expanded=False):
        st.caption(f'{result["confounders_controlled"]}/{result["confounders_total"]}')
        st.markdown("- Region (controlled)\n- Market Conditions (controlled)\n- Seasonality (controlled)\n- Supplier Size (uncontrolled)")

    with st.container(border=True):
        st.caption(result["evidence_base"])
        st.caption(f'Meta-analysis: {"Yes" if result["meta_analysis"] else "No"} | Studies: {result["studies"]}')


def render_guardian_policy_check(policies: list[dict] | None = None) -> None:
    """Render Guardian policy check panel with approval workflow."""
    if policies is None:
        policies = _get_mock_policies()

    passed = sum(1 for p in policies if p["status"] == "pass")
    pending = sum(1 for p in policies if p["status"] == "pending")
    failed = sum(1 for p in policies if p["status"] == "fail")

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**:material/shield: Guardian Policy Check**")
        with col2:
            st.markdown(
                f'<span style="background: {COLORS["bg_muted"]}; color: {COLORS["text_secondary"]}; '
                f'border: 1px solid {COLORS["border"]}; padding: 4px 10px; border-radius: 999px; font-size: 12px;">PENDING</span>',
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            col1, col2 = st.columns([0.3, 3])
            with col1:
                st.markdown(":material/target:")
            with col2:
                st.caption("Proposed Action")
                st.markdown("**BUDGET ALLOCATION**")
                st.caption("Supplier Sustainability Program")

            col1, col2 = st.columns(2)
            with col1:
                st.caption("Amount")
                st.markdown("**10 M USD**")
            with col2:
                st.caption("Expected Effect")
                st.markdown(":material/bolt: Reduce Scope 3 emissions by 750 tonnes CO2e annually")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Passed", passed)
        with col2:
            st.metric("Pending", pending)
        with col3:
            st.metric("Failed", failed)

    for policy in policies:
        status = policy["status"]
        if status == "pass":
            icon = ":material/check_circle:"
            status_label = "Passed"
        elif status == "pending":
            icon = ":material/schedule:"
            status_label = "Pending"
        else:
            icon = ":material/cancel:"
            status_label = "Failed"

        with st.container(border=True):
            col1, col2, col3 = st.columns([0.4, 3, 1])
            with col1:
                st.markdown(icon)
            with col2:
                st.markdown(f"**{policy['name']}**")
                st.caption(policy["desc"])
            with col3:
                st.caption(policy["version"])
                st.caption(status_label)

    st.info("Human-in-the-loop required. This action requires your explicit approval before execution.")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("Approve", use_container_width=True, type="primary", key="guardian_approve_btn"):
            st.success("Action approved!")
    with col2:
        if st.button("Clarify", use_container_width=True, key="guardian_clarify_btn"):
            st.info("Opening clarification...")
    with col3:
        if st.button("Reject", use_container_width=True, key="guardian_reject_btn"):
            st.error("Action rejected.")


def render_execution_trace(trace: list[dict] | None = None) -> None:
    """Render execution trace timeline."""
    if trace is None:
        trace = _get_mock_execution_trace()

    total_duration = sum(step["duration"] for step in trace)
    receipt_id = "rcpt_s3ae_2024_001_7f8a9b2c"

    success_count = sum(1 for step in trace if step["status"] == "success")
    warning_count = sum(1 for step in trace if step["status"] == "warning")
    error_count = sum(1 for step in trace if step["status"] == "error")

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**:material/monitor_heart: Execution Trace**")
        with col2:
            st.markdown(f"**`{total_duration / 1000:.2f}s`**")

        with st.container(border=True):
            st.caption("Receipt ID")
            col1, col2 = st.columns([5, 1])
            with col1:
                st.text_input(
                    "Receipt",
                    value=receipt_id,
                    disabled=True,
                    label_visibility="collapsed",
                    key="trace_receipt_id",
                )
            with col2:
                st.button("Copy", use_container_width=True, key="trace_copy_btn")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Passed", success_count)
        with col2:
            st.metric("Warnings", warning_count)
        with col3:
            st.metric("Errors", error_count)

    for step in trace:
        status = step["status"]
        if status == "success":
            icon = ":material/check_circle:"
        elif status == "warning":
            icon = ":material/warning:"
        else:
            icon = ":material/cancel:"

        with st.container(border=True):
            col1, col2, col3 = st.columns([0.4, 3, 1])
            with col1:
                st.markdown(icon)
            with col2:
                st.markdown(f"**{step['node']}**")
                st.caption(step["time"])
            with col3:
                st.markdown(f"`{step['duration']}ms`")
                st.caption(status)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Export JSON",
            data=json.dumps(trace, indent=2),
            file_name="execution_trace.json",
            mime="application/json",
            use_container_width=True,
            key="trace_export_btn",
        )
    with col2:
        if st.button("View in LangSmith", use_container_width=True, key="trace_langsmith_btn"):
            st.info("Open LangSmith in a browser to view this session.")

    st.caption(f'Session: {st.session_state.get("session_id", "sess_abc123def456")}')


def render_developer_view() -> None:
    """Render the Developer debug view with tabs."""
    trace = _get_mock_execution_trace()
    total_duration = sum(step["duration"] for step in trace)

    # Performance Summary Bar
    st.markdown(f"""
    <div class="hero-card" style="margin-bottom: 24px;">
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px;">
            <div>
                <p style="font-size: 12px; color: {COLORS["text_muted"]}; margin: 0;">Total Time</p>
                <p style="font-size: 28px; font-weight: 700; color: {COLORS["text_primary"]}; margin: 0;">{total_duration}ms</p>
            </div>
            <div>
                <p style="font-size: 12px; color: {COLORS["text_muted"]}; margin: 0;">Nodes Processed</p>
                <p style="font-size: 28px; font-weight: 700; color: {COLORS["text_primary"]}; margin: 0;">6</p>
            </div>
            <div>
                <p style="font-size: 12px; color: {COLORS["text_muted"]}; margin: 0;">Edges Analyzed</p>
                <p style="font-size: 28px; font-weight: 700; color: {COLORS["text_primary"]}; margin: 0;">6</p>
            </div>
            <div>
                <p style="font-size: 12px; color: {COLORS["text_muted"]}; margin: 0;">Policies Checked</p>
                <p style="font-size: 28px; font-weight: 700; color: {COLORS["text_primary"]}; margin: 0;">5</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Developer Tabs
    dev_tab1, dev_tab2, dev_tab3, dev_tab4 = st.tabs(["Execution Trace", "DAG Structure", "State Snapshots", "Raw JSON"])

    with dev_tab1:
        st.markdown(f'<p style="font-size: 14px; font-weight: 600; color: {COLORS["text_primary"]}; margin-bottom: 16px;">Execution Flow</p>', unsafe_allow_html=True)
        for step in trace:
            status_color = COLORS["status_success"] if step["status"] == "success" else COLORS["status_warning"]
            st.markdown(f"""
            <div class="timeline-item">
                <div class="timeline-dot" style="background: {status_color};"></div>
                <div class="timeline-content">
                    <span class="timeline-title">{step["node"]}</span>
                    <span class="timeline-time">{step["duration"]}ms</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with dev_tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Nodes**")
            st.json(["Supplier Programs", "Emissions", "Sustainability", "Scope 3 Emissions", "Production URL", "Market Conditions"])
        with col2:
            st.markdown("**Edges**")
            st.json([{"source": "Supplier Programs", "target": "Emissions", "effect": 0.42}])

    with dev_tab3:
        st.markdown("**Cynefin State**")
        st.json({"domain": "complicated", "confidence": 0.61, "entropy": 0.32})
        st.markdown("**Guardian State**")
        st.json({"verdict": "pending", "policies_passed": 4, "policies_total": 5})

    with dev_tab4:
        st.json({
            "session_id": st.session_state.get("session_id", "sess_demo"),
            "scenario": "s3ae",
            "cynefin": {"domain": "complicated", "confidence": 0.61},
            "causal_result": {"effect": -75, "p_value": 0.0038},
            "guardian": {"verdict": "pending"}
        })


def render_executive_view() -> None:
    """Render the Executive summary view."""
    result = _get_mock_causal_result()
    policies = _get_mock_policies()
    passed = sum(1 for p in policies if p["status"] == "pass")

    # Hero Card
    st.markdown(f"""
    <div class="hero-card">
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 32px; align-items: center;">
            <div>
                <p style="font-size: 12px; color: {COLORS["text_muted"]}; margin: 0 0 8px 0;">Expected Impact</p>
                <p style="font-size: 42px; font-weight: 700; color: {COLORS["text_primary"]}; margin: 0;">{result["effect"]} {result["unit"].split()[0]} {result["unit"].split()[1]}</p>
                <p style="font-size: 14px; color: {COLORS["text_secondary"]}; margin: 4px 0 0 0;">per $1M invested</p>
                <p style="font-size: 12px; color: {COLORS["text_muted"]}; margin: 8px 0 0 0;">Confidence: {result["ci_low"]} to {result["ci_high"]}</p>
                <p style="font-size: 13px; color: {COLORS["status_warning"]}; margin: 8px 0 0 0;">↓ Pending Validation</p>
            </div>
            <div style="text-align: center; border-left: 1px solid {COLORS["border"]}; border-right: 1px solid {COLORS["border"]}; padding: 0 24px;">
                <span class="badge badge-complicated" style="font-size: 14px; padding: 8px 16px;">Complicated Domain</span>
                <div style="margin-top: 16px;">
                    <p style="font-size: 12px; color: {COLORS["text_muted"]}; margin: 0;">System Confidence</p>
                    <p style="font-size: 18px; font-weight: 600; color: {COLORS["text_primary"]}; margin: 4px 0;">61%</p>
                    <div class="progress-bar" style="margin-top: 8px;">
                        <div class="progress-fill" style="width: 61%; background: {COLORS["status_success"]};"></div>
                    </div>
                </div>
            </div>
            <div style="text-align: right;">
                <p style="font-size: 12px; color: {COLORS["text_muted"]}; margin: 0 0 8px 0;">Risk Level</p>
                <div class="risk-badge risk-low">
                    <span>✓</span> LOW
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-label">Policy Compliance</span>
            </div>
            <div class="kpi-value">{passed}/5</div>
            <div class="progress-bar" style="margin-top: 8px;">
                <div class="progress-fill" style="width: {passed/5*100}%; background: {COLORS["status_success"]};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-label">Avg Confidence</span>
            </div>
            <div class="kpi-value">79%</div>
            <div class="progress-bar" style="margin-top: 8px;">
                <div class="progress-fill" style="width: 79%; background: {COLORS["chart_1"]};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-label">Variables Analyzed</span>
            </div>
            <div class="kpi-value">2</div>
            <p style="font-size: 11px; color: {COLORS["text_muted"]}; margin-top: 8px;">Across causal graph</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-header">
                <span class="kpi-label">Signal Entropy</span>
            </div>
            <div class="kpi-value">0.32</div>
            <p style="font-size: 11px; color: {COLORS["text_muted"]}; margin-top: 8px;">Moderate</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Proposed Action Card
    st.markdown(f"""
    <div class="card" style="border-color: rgba(124, 58, 237, 0.3);">
        <div class="card-header">
            <span class="card-title">→ Proposed Action</span>
            <span class="badge" style="background: {COLORS["bg_muted"]}; color: {COLORS["text_secondary"]};">Requires Approval</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px; background: {COLORS["bg_muted"]}; border-radius: 8px; margin-bottom: 16px;">
            <div>
                <p style="font-size: 14px; font-weight: 600; color: {COLORS["text_primary"]}; margin: 0;">BUDGET_ALLOCATION</p>
                <p style="font-size: 12px; color: {COLORS["text_muted"]}; margin: 4px 0 0 0;">Target: Supplier Sustainability Program • Amount: 10</p>
            </div>
            <div style="text-align: right;">
                <p style="font-size: 11px; color: {COLORS["text_muted"]}; margin: 0;">Expected Effect</p>
                <p style="font-size: 13px; color: {COLORS["status_success"]}; font-weight: 500; margin: 4px 0 0 0;">Reduce Scope 3 emissions by 750 tonnes CO2e annually</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.button("Approve Action", use_container_width=True, type="primary", key="exec_approve_action_btn")
    with col2:
        st.button("Reject", use_container_width=True, key="exec_reject_btn")

    st.markdown("<br>", unsafe_allow_html=True)

    # Policy Summary
    st.markdown(f"""
    <div class="card">
        <p style="font-size: 14px; font-weight: 600; color: {COLORS["text_primary"]}; margin-bottom: 16px;">Policy Check Summary</p>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
    """, unsafe_allow_html=True)

    policy_html = ""
    for policy in policies:
        if policy["status"] == "pass":
            bg_color = "rgba(16, 185, 129, 0.1)"
            icon = "✓"
            text_color = COLORS["status_success"]
        else:
            bg_color = "rgba(245, 158, 11, 0.1)"
            icon = "△"
            text_color = COLORS["status_warning"]
        policy_html += f'<div style="background: {bg_color}; padding: 8px 12px; border-radius: 6px; display: flex; align-items: center; gap: 8px;"><span style="color: {text_color};">{icon}</span> <span style="font-size: 13px; color: {COLORS["text_primary"]};">{policy["name"]}</span></div>'

    st.markdown(policy_html + "</div></div>", unsafe_allow_html=True)


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        page_title="CARF Epistemic Cockpit",
        page_icon="",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    inject_custom_css()

    # Render header with scenario selector
    session_id, selected_scenario_id = render_dashboard_header()

    # Get last analysis result from session state
    analysis_result = st.session_state.get("analysis_result")
    domain = analysis_result.get("domain", "complicated") if analysis_result else "complicated"
    confidence = analysis_result.get("domain_confidence", 0.61) if analysis_result else 0.61

    # View mode tabs
    tab1, tab2, tab3 = st.tabs(["End-User", "Developer", "Executive"])

    # Extract data from analysis result for components
    reasoning_chain = []
    guardian_verdict = None
    if analysis_result:
        reasoning_chain = analysis_result.get("reasoning_chain", [])
        guardian_verdict = analysis_result.get("guardian_verdict")

    # Build execution trace from reasoning chain
    execution_trace = []
    for i, step in enumerate(reasoning_chain):
        execution_trace.append({
            "node": step.get("node", f"Step {i+1}"),
            "status": "success" if step.get("confidence") in ["high", "medium"] else "warning",
            "duration": random.randint(100, 2500),
            "time": f"12:30:{i:02d} PM",
        })

    with tab1:
        # End-User View - Three-column layout
        col_left, col_center, col_right = st.columns([3, 6, 3], gap="medium")

        with col_left:
            render_guided_walkthrough(selected_scenario_id, key_prefix="enduser")
            query_eu, analyze_eu = render_query_input(key_prefix="enduser")
            render_simulation_controls(key_prefix="enduser")
            render_cynefin_classification(domain=domain, confidence=confidence)
            render_bayesian_belief_state()

        with col_center:
            render_causal_dag()
            render_causal_analysis_results()
            render_guardian_policy_check()

        with col_right:
            render_execution_trace(trace=execution_trace if execution_trace else None)

        # Handle analysis
        if analyze_eu and query_eu:
            with st.spinner("Running CARF analysis pipeline..."):
                try:
                    # Check if a scenario is selected and fetch its payload
                    context = None
                    causal_config = None
                    bayesian_config = None

                    if selected_scenario_id:
                        payload = _fetch_scenario_payload(selected_scenario_id)
                        context = payload.get("context")
                        causal_config = payload.get("causal_estimation")
                        bayesian_config = payload.get("bayesian_inference")

                    response = _run_analysis(
                        query=query_eu,
                        context=context,
                        causal_config=causal_config,
                        bayesian_config=bayesian_config,
                    )
                    st.session_state["analysis_result"] = response
                    st.success(f"Analysis complete! Domain: {response.get('domain', 'unknown')}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Analysis failed: {e}")

    with tab2:
        # Developer View
        col_left, col_main = st.columns([1, 3], gap="medium")

        with col_left:
            query_dev, analyze_dev = render_query_input(key_prefix="developer")
            render_simulation_controls(key_prefix="developer")

        with col_main:
            render_developer_view()

    with tab3:
        # Executive View
        col_left, col_main = st.columns([1, 3], gap="medium")

        with col_left:
            query_exec, analyze_exec = render_query_input(key_prefix="executive")

        with col_main:
            render_executive_view()


if __name__ == "__main__":
    main()
