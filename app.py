"""
DevTeam.AI - Autonomous Development Team
Main Streamlit Application Entry Point

Phase 1: Minimal Viable Graph
- Integrates with LangGraph workflow
- Triggers clarification cycle on button click
- Displays workflow output and persisted state
"""

import uuid

import streamlit as st

from orchestrator import Orchestrator, run_workflow

# Page configuration
st.set_page_config(
    page_title="DevTeam.AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session_{uuid.uuid4().hex[:8]}"
if "workflow_history" not in st.session_state:
    st.session_state.workflow_history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None

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

        **Current Phase**: 1 - Minimal Viable Graph
        """
    )

    st.divider()

    st.header("Session Info")
    st.code(f"Thread ID: {st.session_state.thread_id}")

    # Option to reset thread
    if st.button("New Session"):
        st.session_state.thread_id = f"session_{uuid.uuid4().hex[:8]}"
        st.session_state.workflow_history = []
        st.session_state.last_result = None
        st.rerun()

    st.divider()

    # Check for persisted state
    st.header("Persisted State")
    orchestrator = Orchestrator(thread_id=st.session_state.thread_id)
    persisted_state = orchestrator.get_current_state()

    if persisted_state:
        st.success("State found!")
        messages = persisted_state.get("messages", [])
        with st.expander(f"Messages ({len(messages)})", expanded=False):
            for i, msg in enumerate(messages):
                content = msg.content if hasattr(msg, "content") else str(msg)
                st.text(f"{i + 1}. {content[:100]}...")
    else:
        st.info("No persisted state yet")

# Main content area
st.markdown("---")

# Project idea input
st.header("Start a New Project")
st.markdown(
    """
    Enter your project idea below. The workflow will process it through
    the clarification node (dummy in Phase 1, full agent in Phase 3).
    """
)

# Text input for project idea
project_idea = st.text_area(
    "Describe your project idea:",
    height=150,
    placeholder="Example: Build a todo app with user authentication, "
    "real-time sync, and mobile support...",
)

# Submit button
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    run_clicked = st.button(
        "Run Workflow",
        type="primary",
        disabled=not project_idea,
    )

with col2:
    resume_clicked = st.button(
        "Resume",
        disabled=not persisted_state,
    )

# Handle workflow execution
if run_clicked and project_idea:
    with st.spinner("Running workflow..."):
        result = run_workflow(project_idea, thread_id=st.session_state.thread_id)
        st.session_state.last_result = result
        st.session_state.workflow_history.append(
            {
                "idea": project_idea,
                "success": result.success,
                "messages": result.messages,
            }
        )

if resume_clicked and persisted_state:
    with st.spinner("Resuming workflow..."):
        resumed = orchestrator.resume()
        if resumed:
            st.session_state.last_result = resumed
            st.success("Workflow resumed from persisted state!")

# Display results
if st.session_state.last_result:
    st.markdown("---")
    st.header("Workflow Output")

    result = st.session_state.last_result

    if result.success:
        st.success("Workflow completed successfully!")
    else:
        st.error(f"Workflow failed: {result.error}")

    # Display messages
    st.subheader("Messages")
    for i, msg in enumerate(result.messages):
        with st.chat_message("assistant" if i % 2 else "user"):
            st.write(msg)

    # Display raw state (for debugging)
    with st.expander("Raw State (Debug)", expanded=False):
        st.json(
            {
                "success": result.success,
                "thread_id": result.thread_id,
                "messages": result.messages,
                "error": result.error,
            }
        )

# Workflow history
if st.session_state.workflow_history:
    st.markdown("---")
    st.header("Session History")

    for i, entry in enumerate(reversed(st.session_state.workflow_history)):
        with st.expander(
            f"Run {len(st.session_state.workflow_history) - i}", expanded=i == 0
        ):
            st.write(f"**Idea:** {entry['idea'][:100]}...")
            st.write(f"**Success:** {entry['success']}")
            st.write(f"**Messages:** {len(entry['messages'])}")

# Agent status placeholder
st.markdown("---")
st.header("Agent Status")

# Create columns for agent status display
agents = [
    ("Orchestrator", "active", "Routing tasks"),
    ("BudgetGuard", "idle", "Monitoring"),
    ("Clarifying PM", "idle", "Waiting"),
    ("Solution Architect", "idle", "Waiting"),
    ("Tech Lead", "idle", "Waiting"),
    ("Frontend", "idle", "Waiting"),
    ("Backend", "idle", "Waiting"),
    ("Database", "idle", "Waiting"),
]

cols = st.columns(4)
for i, (name, status, info) in enumerate(agents):
    with cols[i % 4]:
        if status == "active":
            st.metric(name, "Active", info)
        else:
            st.metric(name, "Idle", info)

# Footer
st.markdown("---")
st.caption(
    "DevTeam.AI v0.1.1 | Phase 1 - Minimal Viable Graph | "
    "[Documentation](https://github.com/your-repo/devteam-ai-2025)"
)
