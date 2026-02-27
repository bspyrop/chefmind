"""
ChefMind Professional Theme
Drop this function into your Streamlit app and call apply_theme() at the top of your main file.

Fonts used:
  - "Playfair Display" → headings (elegant, editorial, food-magazine feel)
  - "DM Sans"          → body & UI text (clean, modern, highly readable)
  - "DM Mono"          → code / tool call labels (crisp, technical contrast)
"""

import streamlit as st


def apply_theme():
    st.markdown("""
    <style>
    /* ─────────────────────────────────────────────
       FONT IMPORT
    ───────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    /* ─────────────────────────────────────────────
       CSS VARIABLES (edit here to retheme globally)
    ───────────────────────────────────────────── */
    :root {
        --bg-main:        #1A1A1A;
        --bg-surface:     #242424;
        --bg-sidebar:     #1F1F1F;
        --bg-card:        #2A2A2A;

        --accent-amber:   #E8A020;
        --accent-amber-dim: #B87D18;
        --accent-red:     #D94F3D;

        --text-primary:   #F5F0E8;
        --text-secondary: #A09080;
        --text-muted:     #6B6055;

        --border:         #333333;
        --border-accent:  #E8A020;

        --radius-sm:      6px;
        --radius-md:      10px;
        --radius-lg:      14px;

        --font-display:   'Playfair Display', Georgia, serif;
        --font-body:      'DM Sans', system-ui, sans-serif;
        --font-mono:      'DM Mono', 'Courier New', monospace;
    }

    /* ─────────────────────────────────────────────
       BASE
    ───────────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: var(--font-body) !important;
        font-size: 15px;
        line-height: 1.65;
        color: var(--text-primary);
        -webkit-font-smoothing: antialiased;
    }

    .stApp {
        background-color: var(--bg-main);
    }

    /* ─────────────────────────────────────────────
       TYPOGRAPHY — HEADINGS
    ───────────────────────────────────────────── */
    h1 {
        font-family: var(--font-display) !important;
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.5px;
        line-height: 1.2 !important;
    }

    h2 {
        font-family: var(--font-display) !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: var(--accent-amber) !important;
        letter-spacing: -0.3px;
        margin-top: 1.4rem !important;
    }

    h3 {
        font-family: var(--font-display) !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
    }

    /* Section labels (YOUTUBE PLAYER, TOOL CALLS, etc.) */
    h3, .stMarkdown h3, small, .caption {
        font-family: var(--font-body) !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        color: var(--text-secondary) !important;
    }

    /* Body text */
    p, li, .stMarkdown p {
        font-family: var(--font-body) !important;
        font-size: 0.95rem !important;
        font-weight: 400 !important;
        color: var(--text-primary) !important;
        line-height: 1.75 !important;
    }

    /* Subtitle / description line */
    .stApp [data-testid="stMarkdownContainer"] > p:first-child em {
        font-family: var(--font-body) !important;
        font-size: 0.88rem !important;
        color: var(--text-secondary) !important;
        font-style: normal !important;
        font-weight: 300 !important;
        letter-spacing: 0.02em;
    }

    /* ─────────────────────────────────────────────
       SIDEBAR
    ───────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border) !important;
    }

    [data-testid="stSidebar"] * {
        font-family: var(--font-body) !important;
    }

    /* ─────────────────────────────────────────────
       CARDS & EXPANDERS (Tool Calls, RAG Evidence)
    ───────────────────────────────────────────── */
    [data-testid="stExpander"] {
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        margin-bottom: 6px !important;
        transition: border-color 0.2s ease;
    }

    [data-testid="stExpander"]:hover {
        border-color: var(--accent-amber-dim) !important;
    }

    [data-testid="stExpander"] summary {
        font-family: var(--font-mono) !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        padding: 10px 14px !important;
    }

    [data-testid="stExpander"] summary:hover {
        color: var(--accent-amber) !important;
    }

    /* ─────────────────────────────────────────────
       CHAT MESSAGES
    ───────────────────────────────────────────── */
    [data-testid="stChatMessage"] {
        background-color: var(--bg-surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 14px 18px !important;
        margin-bottom: 10px !important;
        font-family: var(--font-body) !important;
        font-size: 0.95rem !important;
    }

    /* ─────────────────────────────────────────────
       CHAT INPUT
    ───────────────────────────────────────────── */
    [data-testid="stChatInput"] {
        background-color: var(--bg-surface) !important;
        border-top: 1px solid var(--border) !important;
    }

    [data-testid="stChatInput"] textarea {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1.5px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        font-family: var(--font-body) !important;
        font-size: 0.95rem !important;
        font-weight: 400 !important;
        padding: 12px 16px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    [data-testid="stChatInput"] textarea:focus {
        border-color: var(--accent-amber) !important;
        box-shadow: 0 0 0 3px rgba(232, 160, 32, 0.12) !important;
        outline: none !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: var(--text-muted) !important;
        font-style: italic;
    }

    /* ─────────────────────────────────────────────
       BUTTONS
    ───────────────────────────────────────────── */
    .stButton > button {
        background-color: var(--accent-amber) !important;
        color: #1A1A1A !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        font-family: var(--font-body) !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.03em !important;
        padding: 8px 18px !important;
        transition: background-color 0.2s ease, transform 0.1s ease;
    }

    .stButton > button:hover {
        background-color: var(--accent-amber-dim) !important;
        transform: translateY(-1px);
    }

    /* ─────────────────────────────────────────────
       VIDEO CATALOG ITEMS (sidebar buttons)
    ───────────────────────────────────────────── */
    [data-testid="stSidebar"] .stButton > button {
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        text-align: left !important;
        font-size: 0.82rem !important;
        font-weight: 400 !important;
        width: 100% !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        border-color: var(--accent-amber) !important;
        color: var(--accent-amber) !important;
        background-color: var(--bg-card) !important;
        transform: none;
    }

    /* ─────────────────────────────────────────────
       SCROLLBAR
    ───────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: var(--bg-main); }
    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover { background: var(--accent-amber-dim); }

    /* ─────────────────────────────────────────────
       DIVIDERS
    ───────────────────────────────────────────── */
    hr {
        border-color: var(--border) !important;
        margin: 1.5rem 0 !important;
    }

    /* ─────────────────────────────────────────────
       CODE / MONO TEXT
    ───────────────────────────────────────────── */
    code, pre, .stCode {
        font-family: var(--font-mono) !important;
        font-size: 0.85rem !important;
        background-color: var(--bg-card) !important;
        color: var(--accent-amber) !important;
        border-radius: var(--radius-sm) !important;
        padding: 2px 6px !important;
    }

    </style>
    """, unsafe_allow_html=True)
