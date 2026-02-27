import html
import streamlit as st
from agent import run_agent

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="InfoAgent",
    page_icon="🤖",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Mono', monospace;
    }

    .stApp {
        background: #0a0a0f;
        color: #e8e6e0;
    }

    .agent-header {
        text-align: center;
        padding: 2.5rem 0 1rem 0;
    }
    .agent-header h1 {
        font-family: 'Syne', sans-serif;
        font-weight: 800;
        font-size: 2.6rem;
        letter-spacing: -0.02em;
        color: #f0ede6;
        margin: 0;
    }
    .agent-header h1 span { color: #c8f542; }
    .agent-caption {
        font-family: 'DM Mono', monospace;
        font-size: 0.78rem;
        color: #6b6b72;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-top: 0.4rem;
    }

    .hint-row {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        justify-content: center;
        margin: 1rem 0 1.8rem 0;
    }
    .hint-pill {
        background: #111118;
        border: 1px solid #1e1e28;
        border-radius: 20px;
        padding: 0.3rem 0.9rem;
        font-size: 0.72rem;
        color: #5a5a62;
        letter-spacing: 0.04em;
        cursor: default;
    }

    /* Hide default chat avatars */
    [data-testid="stChatMessageAvatarUser"],
    [data-testid="stChatMessageAvatarAssistant"] {
        display: none !important;
    }

    /* User bubble */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: #1a1a24 !important;
        border: 1px solid #2a2a38 !important;
        border-radius: 16px 16px 4px 16px !important;
        padding: 0.75rem 1.1rem !important;
        margin-left: auto !important;
        max-width: 80% !important;
        color: #c8f542 !important;
    }

    /* Agent bubble */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background: #111118 !important;
        border: 1px solid #1e1e2e !important;
        border-radius: 16px 16px 16px 4px !important;
        padding: 0.85rem 1.2rem !important;
        max-width: 88% !important;
        color: #d4d2cc !important;
    }

    /* Message text */
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] div {
        font-family: 'DM Mono', monospace !important;
        font-size: 0.88rem !important;
        line-height: 1.65 !important;
    }

    .stTextInput > div > div > input {
        background: #111118 !important;
        border: 1px solid #2a2a38 !important;
        border-radius: 10px !important;
        color: #e8e6e0 !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.88rem !important;
        padding: 0.65rem 1rem !important;
        caret-color: #c8f542;
    }
    .stTextInput > div > div > input:focus {
        border-color: #c8f542 !important;
        box-shadow: 0 0 0 2px rgba(200, 245, 66, 0.08) !important;
    }
    .stTextInput > label { display: none !important; }

    div.stButton > button {
        background: #c8f542 !important;
        color: #0a0a0f !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'Syne', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.06em !important;
        padding: 0.55rem 1.6rem !important;
        transition: opacity 0.15s ease !important;
        width: 100%;
    }
    div.stButton > button:hover { opacity: 0.85 !important; }

    .stSpinner > div { border-top-color: #c8f542 !important; }

    .divider {
        border: none;
        border-top: 1px solid #1e1e28;
        margin: 1.2rem 0;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="agent-header">
        <h1>Info<span>Agent</span></h1>
        <p class="agent-caption">ReAct · Weather · Search · Calculator</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Hint pills ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hint-row">
        <span class="hint-pill">🌤 Weather in Tokyo</span>
        <span class="hint-pill">📰 Latest AI news</span>
        <span class="hint-pill">🔢 sqrt(2) × 1000</span>
        <span class="hint-pill">🌍 Capital of Brazil</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0

# ── Chat history — native st.chat_message, no unsafe HTML injection ───────────
for chat in st.session_state.chat_history:
    with st.chat_message("user"):
        st.write(chat["question"])
    with st.chat_message("assistant"):
        st.write(chat["answer"])

# ── Input row ─────────────────────────────────────────────────────────────────
col_input, col_btn = st.columns([5, 1])

with col_input:
    user_input = st.text_input(
        "question",
        placeholder="Ask anything — weather, news, math…",
        label_visibility="collapsed",
        key=f"user_input_{st.session_state.input_counter}",
    )

with col_btn:
    send = st.button("Send", use_container_width=True)

# ── Handle send ───────────────────────────────────────────────────────────────
if send and user_input.strip():
    with st.spinner("Thinking…"):
        try:
            final_answer = run_agent(user_input.strip())
        except Exception as e:
            final_answer = f"⚠️ Something went wrong: {e}"

    st.session_state.chat_history.append(
        {"question": user_input.strip(), "answer": final_answer}
    )
    st.session_state.input_counter += 1
    st.rerun()

# ── Clear history ─────────────────────────────────────────────────────────────
if st.session_state.chat_history:
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    _, col_clear, _ = st.columns([3, 1, 3])
    with col_clear:
        if st.button("Clear chat", key="clear"):
            st.session_state.chat_history = []
            st.session_state.input_counter += 1
            st.rerun()
