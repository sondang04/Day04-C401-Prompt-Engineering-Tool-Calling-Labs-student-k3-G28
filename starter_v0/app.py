import os
from pathlib import Path
# pyrefly: ignore [missing-import]
import streamlit as st

from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from chat import run_model_tool_loop, trim_history
from versioning import build_artifact_version

# Page configuration
st.set_page_config(
    page_title="Research Agent - LeadBot Widget",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Fix Visibility & Contrast Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Quicksand', sans-serif;
    }
    
    /* Background Gradient */
    .stApp {
        background: linear-gradient(135deg, #2563eb 0%, #7c3aed 50%, #db2777 100%);
        min-height: 100vh;
    }
    
    /* Header Card */
    .widget-header {
        background: linear-gradient(135deg, #9333ea 0%, #a855f7 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 16px;
        color: white;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    }
    
    .widget-title-container {
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }
    
    .bot-avatar {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
    }
    
    .bot-name {
        font-weight: 700;
        font-size: 1.15rem;
        color: #ffffff;
    }
    
    .bot-status {
        font-size: 0.8rem;
        color: #f3e8ff;
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }
    
    .online-dot {
        width: 8px;
        height: 8px;
        background-color: #4ade80;
        border-radius: 50%;
    }

    /* ALL Chat Message Container Fixes */
    div[data-testid="stChatMessage"] {
        border-radius: 16px !important;
        padding: 1.2rem 1.4rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Assistant Chat Bubble - White Background & Extremely Clear Dark Text */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) p,
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) div,
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) span {
        color: #0f172a !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
    }

    /* User Chat Bubble - Purple Background & White Text */
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) {
        background: linear-gradient(135deg, #9333ea 0%, #7e22ce 100%) !important;
        border: none !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) p,
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) div,
    div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) span {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
    }

    /* Bottom Input Bar High Contrast */
    div[data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border-radius: 9999px !important;
        border: 2px solid #a855f7 !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2) !important;
    }
    
    div[data-testid="stChatInput"] input {
        color: #0f172a !important;
        font-size: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)

# Render LeadBot Header
st.markdown("""
<div class="widget-header">
    <div class="widget-title-container">
        <div class="bot-avatar">🤖</div>
        <div>
            <div class="bot-name">LeadBot</div>
            <div class="bot-status"><span class="online-dot"></span> Online Now • Group 28</div>
        </div>
    </div>
    <div style="font-size: 1.3rem;">•••</div>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    provider_name = st.selectbox("Provider", ["openai", "gemini", "openrouter", "anthropic"], index=0)
    model_name = st.text_input("Model ID", value="gpt-4o-mini" if provider_name == "openai" else "")
    version_label = st.text_input("Artifact Tag", value="v3")
    max_tool_rounds = st.slider("Max Execution Rounds", min_value=1, max_value=8, value=4)
    
    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    
    if system_prompt_path.exists() and tools_path.exists():
        system_prompt = system_prompt_path.read_text(encoding="utf-8")
        tool_declarations = load_tool_declarations(tools_path)
        openai_tools = to_openai_tools(tool_declarations)
        artifact_version = build_artifact_version(version_label, system_prompt_path, tools_path)
        
        st.divider()
        st.caption(f"**Version:** `{artifact_version.artifact_version}`")
        st.caption(f"**Prompt Hash:** `{artifact_version.prompt_hash[:10]}...`")
        st.caption(f"**Tools Hash:** `{artifact_version.tools_hash[:10]}...`")
    else:
        st.error("Missing system_prompt.md or tools.yaml")

# Session state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

if "history" not in st.session_state:
    st.session_state.history = []

# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "tools" in msg and msg["tools"]:
            with st.expander("🔧 Tool Execution Trace"):
                st.json(msg["tools"])

# Chat input
if user_input := st.chat_input("Reply to LeadBot..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("LeadBot is typing..."):
            try:
                provider = make_provider(provider_name)
                messages = [
                    {"role": "system", "content": system_prompt},
                    *trim_history(st.session_state.history, 5),
                    {"role": "user", "content": user_input},
                ]
                
                result = run_model_tool_loop(
                    provider=provider,
                    messages=messages,
                    tools=openai_tools,
                    model=model_name if model_name else None,
                    max_tool_rounds=max_tool_rounds,
                )
                
                assistant_text = result.get("assistant_text", "")
                tool_events = result.get("tool_events", [])
                
                st.write(assistant_text)
                
                if tool_events:
                    with st.expander("🔧 Tool Execution Trace"):
                        st.json(tool_events)
                        
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_text,
                    "tools": tool_events,
                })
                st.session_state.history.append({"role": "user", "content": user_input})
                st.session_state.history.append({"role": "assistant", "content": assistant_text})
                
            except Exception as exc:
                st.error(f"Error: {type(exc).__name__} - {str(exc)}")
