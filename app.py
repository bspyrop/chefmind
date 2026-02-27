"""
app.py
ChefMind — AI Recipe & Meal Planning Assistant
Streamlit entry point.

Layout (3 columns):
  Left  (~22%): YouTube Player + Video Catalog
  Center (~56%): Chat
  Right (~22%): Tool Calls + RAG Evidence
"""

import json
import logging
import os

import streamlit as st
from dotenv import load_dotenv

from chefmind_theme import apply_theme

# ── Environment ───────────────────────────────────────────────────────────────
load_dotenv()

logging.basicConfig(level=logging.INFO)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ChefMind",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_theme()

st.markdown(
    """
    <style>
    /* Panel headers */
    .panel-header {
        font-size: 0.85rem; font-weight: 600; color: #888;
        text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;
    }
    /* Remove default top padding from columns */
    div[data-testid="column"] > div:first-child { padding-top: 0; }

    /* ── Remove default top padding above the title ── */
    [data-testid="stMainBlockContainer"] { padding-top: 2rem !important; }
    [data-testid="stAppViewBlockContainer"] { padding-top: 0 !important; }

    /* ── Center the page title and caption ── */
    h1 { text-align: center !important; }
    [data-testid="stCaptionContainer"] p { text-align: center !important; }

    /* ── Chat input cursor visibility ── */
    [data-testid="stChatInput"] textarea {
        caret-color: #ffffff !important;
        color: #ffffff !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)



# ── Session state initialisation ─────────────────────────────────────────────

def _init_state() -> None:
    """Initialise all session-state keys on first load."""
    if "agent" not in st.session_state:
        from agent.agent import build_agent
        st.session_state.agent = build_agent()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "rag_chunks" not in st.session_state:
        st.session_state.rag_chunks = []

    if "tool_calls" not in st.session_state:
        st.session_state.tool_calls = []

    if "selected_video_id" not in st.session_state:
        st.session_state.selected_video_id = None

    if "video_start_time" not in st.session_state:
        st.session_state.video_start_time = 0

    if "show_tool_calls" not in st.session_state:
        st.session_state.show_tool_calls = False

    if "show_rag_chunks" not in st.session_state:
        st.session_state.show_rag_chunks = False

    if "usage_log" not in st.session_state:
        st.session_state.usage_log = []

    if "show_usage" not in st.session_state:
        st.session_state.show_usage = False


_init_state()


# ── Utility: format seconds → MM:SS ──────────────────────────────────────────

def _fmt_time(seconds: int | None) -> str:
    if seconds is None:
        return "?"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def _mm_ss_to_sec(time_str: str) -> int:
    """Convert 'MM:SS' string to integer seconds."""
    try:
        parts = time_str.strip().split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return 0


# ── Helper: fetch current catalog ────────────────────────────────────────────

def _get_catalog() -> list[dict]:
    from tools.tools import get_store
    return get_store().get_catalog()


# ── Helper: update UI state from UI_JSON ─────────────────────────────────────

def _apply_ui_json(ui_json: dict) -> list[dict]:
    """Apply UI_JSON fields to session state. Returns the timestamps list."""
    if not ui_json:
        return []
    if ui_json.get("selected_video_id"):
        st.session_state.selected_video_id = ui_json["selected_video_id"]
    return ui_json.get("timestamps", [])


# ── Helper: run agent + capture tool calls ───────────────────────────────────

def _run_agent(user_input: str) -> tuple[str, dict]:
    from agent.agent import run_agent

    display_text, ui_json, tool_calls, usage = run_agent(
        st.session_state.agent,
        user_input,
        thread_id="chefmind-session",
    )

    # Reset panels for each new user message, then populate with fresh results
    st.session_state.tool_calls = []
    st.session_state.rag_chunks = []

    for tc in tool_calls:
        st.session_state.tool_calls.append(tc)
        if tc["tool"] == "rag_search":
            try:
                parsed = json.loads(tc["output"])
                chunks = parsed.get("results", [])
                if chunks:
                    st.session_state.rag_chunks = chunks
            except (json.JSONDecodeError, TypeError):
                pass

    st.session_state.usage_log.append({
        "turn": len(st.session_state.usage_log) + 1,
        **usage,
    })

    return display_text, ui_json



# ── Layout ────────────────────────────────────────────────────────────────────

st.title("🍳 ChefMind")
st.caption("AI Recipe & Meal Planning Assistant — powered by YouTube RAG")

col_left, col_center, col_right = st.columns([2, 5, 3])


# ═══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN: YouTube Player → Video Catalog
# ═══════════════════════════════════════════════════════════════════════════════

with col_left:
    # ── Panel: YouTube Player (top) ───────────────────────────────────────────
    st.markdown('<div class="panel-header">▶ YouTube Player</div>', unsafe_allow_html=True)

    vid = st.session_state.selected_video_id
    if vid:
        # Build embed URL with start time baked in so the iframe always
        # reloads when the timestamp changes (st.video() caches the element
        # and ignores start_time changes without a URL change).
        start_sec = st.session_state.video_start_time
        end_sec   = start_sec + 30 if start_sec > 0 else 0
        autoplay  = "&autoplay=1" if start_sec > 0 else ""
        embed_url = (
            f"https://www.youtube.com/embed/{vid}"
            f"?start={start_sec}{autoplay}&rel=0"
            + (f"&end={end_sec}" if end_sec > 0 else "")
        )
        st.markdown(
            f'<iframe width="100%" height="240" src="{embed_url}" '
            f'frameborder="0" '
            f'allow="autoplay; encrypted-media; fullscreen" '
            f'allowfullscreen></iframe>',
            unsafe_allow_html=True,
        )
        # Consume the timestamp so the next rerun doesn't re-trigger autoplay
        if start_sec > 0:
            st.session_state.video_start_time = 0
    else:
        st.markdown(
            '<div style="background:#1a1a1a;border-radius:8px;padding:2rem;'
            'text-align:center;color:#555;font-size:0.85rem;">'
            'Select a video from the catalog<br>or ask ChefMind to recommend one.</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Panel: Video Catalog (bottom) ─────────────────────────────────────────
    st.markdown('<div class="panel-header">📚 Video Catalog</div>', unsafe_allow_html=True)

    catalog = _get_catalog()

    if not catalog:
        st.info("No videos indexed yet.\nAsk ChefMind to add a YouTube URL.", icon="ℹ️")
    else:
        for entry in catalog:
            vid_id = entry.get("video_id", "")
            title  = entry.get("title", "Unknown")
            is_selected = st.session_state.selected_video_id == vid_id
            label = f"▶ {title}" if is_selected else title
            if st.button(label, key=f"catalog_{vid_id}", use_container_width=True):
                st.session_state.selected_video_id = vid_id
                st.session_state.video_start_time  = 0
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# CENTER COLUMN: Chat
# ═══════════════════════════════════════════════════════════════════════════════

with col_center:
    # ── Area 1: Conversation history (scrollable, fixed height) ───────────────
    # Created first so it occupies the top slot; filled below via context manager.
    chat_container = st.container(height=560, border=False)

    # ── Area 2: User input ────────────────────────────────────────────────────
    # st.chat_input always renders in Streamlit's stBottom element at the very
    # bottom of the page — naturally below the chat_container above.
    if user_input := st.chat_input("Ask ChefMind anything about recipes…"):

        if not os.getenv("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is not set. Please add it to your .env file.")
            st.stop()

        # Append user message to history
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Re-render history + live spinner inside the container for this run
        with chat_container:
            for msg_idx, msg in enumerate(st.session_state.messages):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            with st.chat_message("assistant"):
                with st.spinner("ChefMind is thinking…"):
                    display_text, ui_json = _run_agent(user_input)
                st.markdown(display_text)

        # Persist assistant message and rerun for a clean re-render
        timestamps = _apply_ui_json(ui_json)
        st.session_state.messages.append({
            "role": "assistant",
            "content": display_text,
            "timestamps": timestamps,
        })
        st.rerun()

    # ── Render history from session state (every normal load / rerun) ─────────
    with chat_container:
        for msg_idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                # "Watch here" buttons for any timestamps in this message
                for ts_idx, ts in enumerate(msg.get("timestamps") or []):
                    label    = ts.get("label", "this moment")
                    time_str = ts.get("time", "00:00")
                    vid_id   = ts.get("video_id") or st.session_state.selected_video_id
                    time_sec = _mm_ss_to_sec(time_str)
                    if st.button(
                        f"▶ Watch in video: {label} @ {time_str}",
                        key=f"ts_{msg_idx}_{ts_idx}",
                        use_container_width=False,
                    ):
                        st.session_state.selected_video_id = vid_id
                        st.session_state.video_start_time  = time_sec
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN: Tool Calls → RAG Evidence
# ═══════════════════════════════════════════════════════════════════════════════

with col_right:
    # ── Panel: Usage & Costs ──────────────────────────────────────────────────
    n_turns = len(st.session_state.usage_log)
    usage_label = f"💰 Usage & Costs ({n_turns} turns)" if n_turns else "💰 Usage & Costs"
    usage_toggle = "▲ Hide" if st.session_state.show_usage else "▼ Show"

    u_hdr, u_btn = st.columns([3, 1])
    u_hdr.markdown(f'<div class="panel-header">{usage_label}</div>', unsafe_allow_html=True)
    if u_btn.button(usage_toggle, key="toggle_usage", use_container_width=True):
        st.session_state.show_usage = not st.session_state.show_usage
        st.rerun()

    if st.session_state.show_usage:
        if not st.session_state.usage_log:
            st.caption("Token usage will appear here after your first message.")
        else:
            total_in  = sum(e["prompt_tokens"]     for e in st.session_state.usage_log)
            total_out = sum(e["completion_tokens"]  for e in st.session_state.usage_log)
            total_tok = sum(e["total_tokens"]       for e in st.session_state.usage_log)
            total_cost = sum(e["cost_usd"]          for e in st.session_state.usage_log)

            st.markdown(
                f"**Session total &nbsp;—&nbsp;** "
                f"In: `{total_in:,}` &nbsp; Out: `{total_out:,}` &nbsp; "
                f"Total: `{total_tok:,}` &nbsp;|&nbsp; **${total_cost:.5f}**",
                unsafe_allow_html=True,
            )
            st.dataframe(
                [
                    {
                        "Turn": e["turn"],
                        "In": e["prompt_tokens"],
                        "Out": e["completion_tokens"],
                        "Total": e["total_tokens"],
                        "Cost $": f"{e['cost_usd']:.5f}",
                    }
                    for e in reversed(st.session_state.usage_log)
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.divider()

    # ── Panel: Tool Calls ─────────────────────────────────────────────────────
    tc_count = len(st.session_state.tool_calls)
    tc_label = f"🔧 Tool Calls ({tc_count})" if tc_count else "🔧 Tool Calls"
    tc_toggle = "▲ Hide" if st.session_state.show_tool_calls else "▼ Show"

    tc_hdr, tc_btn = st.columns([3, 1])
    tc_hdr.markdown(f'<div class="panel-header">{tc_label}</div>', unsafe_allow_html=True)
    if tc_btn.button(tc_toggle, key="toggle_tool_calls", use_container_width=True):
        st.session_state.show_tool_calls = not st.session_state.show_tool_calls
        st.rerun()

    if st.session_state.show_tool_calls:
        if not st.session_state.tool_calls:
            st.caption("Tool invocations will appear here.")
        else:
            for i, call in enumerate(reversed(st.session_state.tool_calls), 1):
                with st.expander(f"[{i}] {call['tool']}", expanded=False):
                    st.markdown("**Input:**")
                    st.code(
                        json.dumps(call["input"], indent=2, ensure_ascii=False)
                        if isinstance(call["input"], dict)
                        else str(call["input"]),
                        language="json",
                    )
                    st.markdown("**Output:**")
                    try:
                        parsed_output = json.loads(call["output"])
                        output_display = json.dumps(parsed_output, indent=2, ensure_ascii=False)
                    except (json.JSONDecodeError, TypeError):
                        output_display = call["output"]
                    st.code(output_display[:1200], language="json")

    st.divider()

    # ── Panel: RAG Evidence (bottom) ──────────────────────────────────────────
    rag_count = len(st.session_state.rag_chunks)
    rag_label = f"🔍 RAG Evidence ({rag_count})" if rag_count else "🔍 RAG Evidence"
    rag_toggle = "▲ Hide" if st.session_state.show_rag_chunks else "▼ Show"

    rag_hdr, rag_btn = st.columns([3, 1])
    rag_hdr.markdown(f'<div class="panel-header">{rag_label}</div>', unsafe_allow_html=True)
    if rag_btn.button(rag_toggle, key="toggle_rag_chunks", use_container_width=True):
        st.session_state.show_rag_chunks = not st.session_state.show_rag_chunks
        st.rerun()

    if st.session_state.show_rag_chunks:
        if not st.session_state.rag_chunks:
            st.caption("Retrieved transcript chunks will appear here.")
        else:
            for i, chunk in enumerate(st.session_state.rag_chunks, 1):
                with st.expander(
                    f"[{i}] {chunk.get('title', 'Unknown')} "
                    f"@ {_fmt_time(chunk.get('start_time_sec', 0))}–{_fmt_time(chunk.get('end_time_sec', 0))}",
                    expanded=False,
                ):
                    st.markdown(f"**Video:** [{chunk.get('title')}]({chunk.get('url')})")
                    st.markdown(
                        f"**Timestamps:** `{_fmt_time(chunk.get('start_time_sec', 0))}` → "
                        f"`{_fmt_time(chunk.get('end_time_sec', 0))}`"
                    )
                    score = chunk.get("score")
                    if score is not None:
                        st.markdown(f"**L2 distance:** `{score}`")
                    st.markdown("**Transcript excerpt:**")
                    st.markdown(f"> {chunk.get('chunk_text', '')[:400]}…")
