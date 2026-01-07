"""
DevTeam.AI - Autonomous Development Team
Main Streamlit Application Entry Point

This is the minimal UI for Phase 0. Future phases will expand this
with full workflow visualization and agent interaction.
"""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="DevTeam.AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Main title
st.title("DevTeam.AI")
st.subheader("Autonomous Development Team")

# Sidebar with project info
with st.sidebar:
    st.header("About")
    st.markdown(
        """
        DevTeam.AI is a fully autonomous, parallel-first,
        iterative multi-agent system that replicates a
        12-14 person modern software development team.

        **Current Phase**: 0 - Repository Bootstrap
        """
    )

    st.divider()

    st.header("Status")
    st.info("System initialized. Ready for Phase 1 implementation.")

# Main content area
st.markdown("---")

# Project idea input
st.header("Start a New Project")
st.markdown(
    """
    Enter your project idea below. The Clarifying PM Agent will help
    transform your idea into a comprehensive Product Requirements Document (PRD).
    """
)

# Text input for project idea
project_idea = st.text_area(
    "Describe your project idea:",
    height=150,
    placeholder="Example: Build a todo app with user authentication, "
    "real-time sync, and mobile support...",
)

# Submit button (placeholder for Phase 1)
col1, col2 = st.columns([1, 4])
with col1:
    if st.button("Start Project", type="primary", disabled=not project_idea):
        st.info(
            "🚧 Agent workflow not yet implemented. " "This will be enabled in Phase 1."
        )
        with st.expander("Your idea (preview)"):
            st.write(project_idea)

# Placeholder for future agent visualization
st.markdown("---")
st.header("Agent Workflow")
st.markdown(
    """
    The agent workflow visualization will appear here once Phase 1 is complete.

    **Planned agents (15 total):**
    - Orchestrator Agent (supervisor)
    - BudgetGuard Agent (cost control)
    - Clarifying PM Agent (requirements)
    - Product Owner Agent (user intent)
    - Solution Architect Agent (technical design)
    - Tech Lead Agent (task breakdown)
    - UI/UX Designer Agent (design)
    - Frontend Agent (UI implementation)
    - Backend Agent (API/server)
    - Database Agent (data layer)
    - AI/ML Agent (ML features)
    - DevOps Agent (infrastructure)
    - Security Agent (security review)
    - QA/Test Agent (testing)
    - Technical Writer Agent (documentation)
    - Delivery Summarizer Agent (status updates)
    """
)

# Footer
st.markdown("---")
st.caption(
    "DevTeam.AI v0.1.0 | Phase 0 - Repository Bootstrap | "
    "[Documentation](https://github.com/your-repo/devteam-ai-2025)"
)
