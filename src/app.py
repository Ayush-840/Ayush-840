"""Streamlit UI for Industrial Knowledge Intelligence — Day 4.

Day 4 upgrades:
  • Real Ollama LLM answers rendered in Markdown
  • Key-points bullet display
  • 👍 / 👎 feedback buttons wired to /feedback
  • ⚡ Benchmark tab with live progress
  • LLM / Ollama status in sidebar
  • 120 s query timeout for local LLM
"""

import streamlit as st
import requests
import os
from datetime import datetime

try:
    from streamlit_agraph import agraph, Node, Edge, Config
    AGRAPH_AVAILABLE = True
except ImportError:
    AGRAPH_AVAILABLE = False

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Industrial Knowledge Intelligence",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', 'Inter', sans-serif !important;
    }
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* ── Header banner ── */
    .title-container {
        background: linear-gradient(135deg, #090d16 0%, #1e1b4b 50%, #120636 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        border: 1px solid rgba(99, 102, 241, 0.35);
        box-shadow: 0 10px 30px rgba(99, 102, 241, 0.15), inset 0 1px 0 rgba(255,255,255,0.1);
        position: relative; overflow: hidden;
    }
    .title-container h1 {
        margin: 0; font-weight: 800; font-size: 2.3rem; letter-spacing: -0.02em;
        background: linear-gradient(90deg, #ffffff 0%, #c7d2fe 50%, #818cf8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .title-container p { margin: 0.5rem 0 0 0; font-size: 1.05rem; color: #cbd5e1; opacity: 0.9; }

    /* ── Cards ── */
    .doc-card {
        background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(12px);
        border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 12px;
        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); color: #f8fafc;
    }
    .doc-card:hover { transform: translateY(-3px); border-color: rgba(99, 102, 241, 0.5); }

    /* ── Citation card ── */
    .citation-card {
        background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(10px);
        border: 1px solid rgba(99, 102, 241, 0.2); border-left: 4px solid #6366f1;
        border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.75rem;
    }
    .citation-card .cite-header { font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.4rem; }
    .citation-card .cite-text   { font-size: 0.9rem; color: #e2e8f0; line-height: 1.55; }

    /* ── Key-points card ── */
    .keypoints-box {
        background: rgba(16, 185, 129, 0.06);
        border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 10px;
        padding: 0.9rem 1.2rem; margin-top: 0.75rem;
    }
    .keypoints-box ul { margin: 0; padding-left: 1.2rem; }
    .keypoints-box li { color: #6ee7b7; font-size: 0.9rem; line-height: 1.6; }

    /* ── Badges ── */
    .badge {
        display: inline-block; padding: 0.3rem 0.75rem; border-radius: 9999px;
        font-size: 0.75rem; font-weight: 600; margin-right: 0.4rem; margin-bottom: 0.4rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.05);
    }
    .badge-blue   { background-color: rgba(59,130,246,0.2)!important; color: #93c5fd!important; border-color: rgba(59,130,246,0.3)!important; }
    .badge-green  { background-color: rgba(16,185,129,0.2)!important; color: #6ee7b7!important; border-color: rgba(16,185,129,0.3)!important; }
    .badge-purple { background-color: rgba(139,92,246,0.2)!important; color: #c4b5fd!important; border-color: rgba(139,92,246,0.3)!important; }
    .badge-yellow { background-color: rgba(245,158,11,0.2)!important; color: #fde047!important; border-color: rgba(245,158,11,0.3)!important; }
    .badge-red    { background-color: rgba(239,68,68,0.2)!important;  color: #fca5a5!important; border-color: rgba(239,68,68,0.3)!important; }
    .badge-gray   { background-color: rgba(107,114,128,0.2)!important;color: #d1d5db!important; border-color: rgba(107,114,128,0.3)!important; }
    .badge-teal   { background-color: rgba(6,182,212,0.2)!important;  color: #67e8f9!important; border-color: rgba(6,182,212,0.3)!important; }

    /* ── Chat bubbles ── */
    .chat-bubble {
        padding: 1.25rem 1.5rem; border-radius: 12px; margin-bottom: 1.25rem;
        font-size: 0.98rem; line-height: 1.6; border: 1px solid transparent;
        transition: all 0.2s ease;
    }
    .chat-user {
        background-color: rgba(30,41,59,0.5); border: 1px solid rgba(255,255,255,0.08);
        border-left: 5px solid #94a3b8; color: #f1f5f9;
    }
    .chat-assistant {
        background-color: rgba(79,70,229,0.08); border: 1px solid rgba(99,102,241,0.2);
        border-left: 5px solid #6366f1; color: #f8fafc;
        box-shadow: 0 4px 20px rgba(99,102,241,0.08);
    }

    /* ── Scrollbars ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(156,163,175,0.25); border-radius: 9999px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(156,163,175,0.45); }

    /* ── Buttons ── */
    div.stButton > button {
        background: linear-gradient(90deg, #4f46e5 0%, #6366f1 100%) !important;
        color: white !important; border: none !important; border-radius: 10px !important;
        font-weight: 600 !important; font-size: 0.92rem !important;
        padding: 0.55rem 1.4rem !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 4px 15px rgba(79,70,229,0.25) !important;
    }
    div.stButton > button:hover {
        transform: scale(1.015) translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(79,70,229,0.4) !important;
    }
    div.stButton > button:active { transform: scale(0.98) !important; }

    /* ── Benchmark table ── */
    .bench-pass { color: #4ade80 !important; font-weight: 700; }
    .bench-fail { color: #f87171 !important; font-weight: 700; }

    /* ── LLM status pill ── */
    .llm-pill-on  { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.4);
                    border-radius: 8px; padding: 0.5rem 0.9rem; color: #6ee7b7; font-size: 0.82rem; }
    .llm-pill-off { background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.35);
                    border-radius: 8px; padding: 0.5rem 0.9rem; color: #fde047; font-size: 0.82rem; }

    /* ── LLM live metrics ── */
    .llm-metric-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.35rem 0; border-bottom: 1px solid rgba(255,255,255,0.06);
        font-size: 0.78rem; color: #cbd5e1;
    }
    .llm-metric-row:last-child { border-bottom: none; }
    .llm-metric-label { color: #94a3b8; }
    .llm-metric-value { color: #e2e8f0; font-weight: 600; font-variant-numeric: tabular-nums; }
    .llm-metric-value.cost { color: #fcd34d; }
    .llm-metric-value.speed { color: #67e8f9; }
    .llm-metric-value.latency { color: #86efac; }

    /* ── Hybrid router ── */
    .router-pill {
        background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.35);
        border-radius: 8px; padding: 0.45rem 0.75rem; color: #c7d2fe; font-size: 0.78rem;
        margin-top: 0.35rem;
    }
    .router-pill-local {
        background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.35); color: #6ee7b7;
    }
    .router-pill-cloud {
        background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.35); color: #93c5fd;
    }
    .badge-route-local { background: rgba(16,185,129,0.2); color: #6ee7b7; }
    .badge-route-cloud { background: rgba(59,130,246,0.2); color: #93c5fd; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def fmt_time(iso_str: str) -> str:
    try:
        return datetime.fromisoformat(iso_str).strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return iso_str


def confidence_badge(conf: str) -> str:
    colour = {"High": "green", "Medium": "blue", "Low": "yellow"}.get(conf, "gray")
    icon   = {"High": "✅", "Medium": "🔵", "Low": "⚠️"}.get(conf, "")
    return f'<span class="badge badge-{colour}">{icon} Confidence: {conf}</span>'


def route_badge(route_target: str, route_reason: str = "") -> str:
    target = (route_target or "").lower()
    if target == "cloud":
        label = "☁️ Cloud Route"
        css = "badge-route-cloud"
    elif target == "local":
        label = "🔒 Local Route"
        css = "badge-route-local"
    else:
        return ""
    title = route_reason.replace('"', "&quot;") if route_reason else ""
    return f'<span class="badge {css}" title="{title}">{label}</span>'


ROUTER_MODE_LABELS = {
    "hybrid": "🔀 Hybrid Router (Auto)",
    "local": "🔒 Local Mode (Ollama)",
    "cloud": "☁️ Cloud Mode (NVIDIA NIM)",
}


def post_feedback(question: str, answer: str, rating: int):
    try:
        requests.post(
            f"{API_URL}/feedback",
            json={"question": question, "answer": answer, "rating": rating},
            timeout=5,
        )
    except Exception:
        pass


def _default_llm_metrics() -> dict:
    return {
        "llm_latency_ms": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "token_throughput_tps": 0.0,
        "query_count": 0,
    }


def update_llm_metrics_from_response(data: dict) -> None:
    """Persist latest LLM metrics in session state after each /query call."""
    prev = st.session_state.get("llm_metrics", _default_llm_metrics())
    st.session_state["llm_metrics"] = {
        "llm_latency_ms": data.get("llm_latency_ms", 0),
        "prompt_tokens": data.get("prompt_tokens", 0),
        "completion_tokens": data.get("completion_tokens", 0),
        "total_tokens": data.get("total_tokens", 0),
        "estimated_cost_usd": data.get("estimated_cost_usd", 0.0),
        "token_throughput_tps": data.get("token_throughput_tps", 0.0),
        "query_count": prev.get("query_count", 0) + 1,
    }


def render_llm_metrics_sidebar(nvidia_on: bool) -> None:
    """Expandable live latency / cost / throughput panel under LLM Engine."""
    metrics = st.session_state.get("llm_metrics", _default_llm_metrics())
    has_data = metrics.get("query_count", 0) > 0 and metrics.get("llm_latency_ms", 0) > 0

    with st.expander("📈 Live API Metrics", expanded=has_data):
        if not has_data:
            st.caption("Run a query in **Chat Q&A** to populate live metrics.")
            st.markdown(
                '<div class="llm-metric-row">'
                '<span class="llm-metric-label">API Latency</span>'
                '<span class="llm-metric-value latency">—</span></div>'
                '<div class="llm-metric-row">'
                '<span class="llm-metric-label">Est. Cost / Query</span>'
                '<span class="llm-metric-value cost">—</span></div>'
                '<div class="llm-metric-row">'
                '<span class="llm-metric-label">Token Throughput</span>'
                '<span class="llm-metric-value speed">—</span></div>',
                unsafe_allow_html=True,
            )
            return

        latency_s = metrics["llm_latency_ms"] / 1000
        cost = metrics["estimated_cost_usd"]
        tps = metrics["token_throughput_tps"]
        cost_label = f"${cost:.5f}" if nvidia_on else "$0.00000 (local)"
        pricing_note = (
            "NVIDIA NIM · $0.50/M in · $2.20/M out"
            if nvidia_on
            else "Local Ollama — no API billing"
        )

        st.markdown(
            f'<div class="llm-metric-row">'
            f'<span class="llm-metric-label">API Latency</span>'
            f'<span class="llm-metric-value latency">{latency_s:.2f}s</span></div>'
            f'<div class="llm-metric-row">'
            f'<span class="llm-metric-label">Est. Cost / Query</span>'
            f'<span class="llm-metric-value cost">{cost_label}</span></div>'
            f'<div class="llm-metric-row">'
            f'<span class="llm-metric-label">Token Throughput</span>'
            f'<span class="llm-metric-value speed">{tps:.0f} tok/s</span></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"{metrics['prompt_tokens']:,} in · {metrics['completion_tokens']:,} out · "
            f"{metrics['total_tokens']:,} total · {pricing_note}"
        )


@st.dialog("Knowledge Graph Subgraph", width="large")
def show_entity_graph(entity_id: str):
    st.markdown(f"### Subgraph for **{entity_id}**")
    try:
        r = requests.get(f"{API_URL}/graph/entity/{entity_id}?depth=1", timeout=15)
        if r.status_code == 200:
            data = r.json()
            center = data.get("center", {})
            neighbors = data.get("neighbors", [])
            edges = data.get("edges", [])
            
            def get_color(t):
                t = t.lower() if t else ""
                if t == "equipment": return "#ef4444"
                if t == "permit": return "#8b5cf6"
                if t == "regulation": return "#10b981"
                return "#6b7280"
                
            ag_nodes = [Node(
                id=center["id"],
                label=center.get("label", center["id"]),
                size=25,
                color=get_color(center.get("type")),
                title=f"{center['id']} ({center.get('type')})"
            )]
            
            for n in neighbors:
                ag_nodes.append(Node(
                    id=n["id"],
                    label=n.get("label", n["id"]),
                    size=15,
                    color=get_color(n.get("type")),
                    title=f"{n['id']} ({n.get('type')})"
                ))
                
            ag_edges = [Edge(
                source=e["source"],
                target=e["target"],
                label=e.get("relation_type", ""),
                title=e.get("relation_type", "")
            ) for e in edges]
            
            config = Config(
                width="100%", height=400, directed=False, hierarchical=False,
                node={"font": {"size": 12}},
                physics={
                    "enabled": True, "solver": "barnesHut",
                    "barnesHut": {
                        "gravitationalConstant": -2000,
                        "centralGravity": 0.3,
                        "springLength": 95,
                    },
                },
            )
            
            if AGRAPH_AVAILABLE:
                agraph(nodes=ag_nodes, edges=ag_edges, config=config)
            else:
                st.warning("streamlit-agraph not installed")
        else:
            st.error(f"Entity not found: {r.json().get('detail', 'Unknown error')}")
    except Exception as e:
        st.error(f"Error loading graph: {e}")



# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="title-container">
    <h1>🏭 Industrial Knowledge Intelligence</h1>
    <p>RAG-Powered Industrial Document Analysis &nbsp;·&nbsp; Vector Store + Knowledge Graph + Local LLM</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
if "llm_metrics" not in st.session_state:
    st.session_state["llm_metrics"] = _default_llm_metrics()
if "router_mode" not in st.session_state:
    st.session_state["router_mode"] = "hybrid"

with st.sidebar:
    st.image("https://img.icons8.com/isometric-line/100/factory.png", width=60)
    st.markdown("### **System Status**")

    # FastAPI health
    try:
        h = requests.get(f"{API_URL}/health", timeout=15)
        if h.status_code == 200:
            st.success("⚡ FastAPI: Connected")
        else:
            st.warning("⚠️ FastAPI: Unhealthy")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        st.error("❌ FastAPI: Offline")

    # LLM / Ollama status
    st.markdown("---")
    st.markdown("### **LLM Engine**")
    nvidia_on = False
    try:
        llm_resp = requests.get(f"{API_URL}/llm/status", timeout=10)
        if llm_resp.status_code == 200:
            ls = llm_resp.json()
            st.session_state["llm_status"] = ls
            nvidia_on = ls.get("nvidia_available", False)
            ollama_on = ls.get("ollama_available", False)
            router_mode = st.session_state.get("router_mode", "hybrid")

            if nvidia_on and ollama_on:
                n_model = ls.get("nvidia_model", ls.get("model", "nemotron")).replace("nvidia/", "")
                o_model = ls.get("ollama_model", "ollama")
                st.markdown(
                    f'<div class="router-pill">🔀 <b>Hybrid Router</b> · '
                    f'{ROUTER_MODE_LABELS.get(router_mode, router_mode)}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="llm-pill-on router-pill-local">🔒 Local &nbsp;|&nbsp; <b>{o_model}</b></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="llm-pill-on router-pill-cloud">☁️ Cloud &nbsp;|&nbsp; <b>{n_model}</b></div>',
                    unsafe_allow_html=True,
                )
            elif nvidia_on:
                model_name = ls.get("nvidia_model", ls.get("model", "nemotron")).replace("nvidia/", "").replace("meta/", "")
                st.markdown(
                    f'<div class="llm-pill-on">🟢 NVIDIA API &nbsp;|&nbsp; <b>{model_name}</b></div>',
                    unsafe_allow_html=True,
                )
            elif ollama_on:
                st.markdown(
                    f'<div class="llm-pill-on">🟢 Ollama &nbsp;|&nbsp; <b>{ls.get("ollama_model", ls["model"])}</b></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="llm-pill-off">🟡 Smart-Context fallback<br>'
                    '<small>Set NVIDIA_API_KEY or start Ollama</small></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("LLM status unavailable")
    except Exception:
        st.caption("LLM status unavailable")

    render_llm_metrics_sidebar(nvidia_on=nvidia_on)

    # Graph stats
    st.markdown("---")
    try:
        gr = requests.get(f"{API_URL}/entities", timeout=15)
        if gr.status_code == 200:
            gd = gr.json()
            stats = gd.get("stats", {})
            st.markdown("### **Knowledge Graph**")
            c1, c2 = st.columns(2)
            c1.metric("Nodes", stats.get("total_nodes", 0))
            c2.metric("Edges", stats.get("total_edges", 0))
            nt = stats.get("node_types", {})
            if nt:
                with st.expander("Entity Breakdown"):
                    for etype, cnt in sorted(nt.items(), key=lambda x: -x[1]):
                        st.write(f"**{etype.replace('_', ' ').title()}:** {cnt}")
    except Exception:
        pass

    st.markdown("---")
    st.markdown("### **Hackathon Phase**")
    st.success("**Day 4** ✅ — Query Engine + LLM")
    st.caption("ET AI Hackathon 2026 · Problem Statement 8")


# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_chat, tab_docs, tab_graph, tab_entities, tab_bench, tab_setup = st.tabs([
    "💬 Chat Q&A",
    "📁 Document Library",
    "🕸️ Knowledge Graph",
    "🏷️ Entity Explorer",
    "⚡ Benchmark",
    "⚙️ Control Panel",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT Q&A (Day 4: real LLM, key-points, feedback)
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.subheader("🤖 Ask the Industrial Knowledge System")
    llm_status = st.session_state.get("llm_status", {})
    if llm_status.get("nvidia_available"):
        caption_text = "Powered by **Vector Search + Knowledge Graph + NVIDIA LLM API**."
    elif llm_status.get("ollama_available"):
        caption_text = "Powered by **Vector Search + Knowledge Graph + Local LLM (Ollama)** — no API key required."
    else:
        caption_text = "Powered by **Vector Search + Knowledge Graph + Smart Context Fallback**."
    st.caption(caption_text)

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_answer" not in st.session_state:
        st.session_state.last_answer = None

    # ── Chat history ──────────────────────────────────────────────────────────
    for idx, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-bubble chat-user"><b>You:</b><br>{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            # Answer bubble with markdown
            with st.container():
                conf_badge = confidence_badge(msg.get("confidence", "Medium"))
                model_badge = f'<span class="badge badge-teal">🤖 {msg.get("model_used","")}</span>'
                latency_badge = f'<span class="badge badge-gray">⏱ {msg.get("latency_ms", 0)} ms</span>'
                route_b = route_badge(msg.get("route_target", ""), msg.get("route_reason", ""))
                st.markdown(
                    f'<div class="chat-bubble chat-assistant">'
                    f'<b>System:</b><br>'
                    f'{conf_badge} {model_badge} {latency_badge} {route_b}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(msg["content"])  # render markdown from LLM

                # Key points
                kp = msg.get("key_points", [])
                if kp:
                    bullets = "".join(f"<li>{p}</li>" for p in kp)
                    st.markdown(
                        f'<div class="keypoints-box"><b style="color:#a7f3d0">📌 Key Points</b>'
                        f'<ul>{bullets}</ul></div>',
                        unsafe_allow_html=True,
                    )

                # Entities
                ents = msg.get("entities_used", [])
                if ents:
                    st.markdown("<small><b>Entities mentioned (click to view graph):</b></small>", unsafe_allow_html=True)
                    cols = st.columns(len(ents[:6]))
                    for i, e in enumerate(ents[:6]):
                        with cols[i]:
                            if st.button(f"⚙ {e}", key=f"ent_btn_{idx}_{i}", use_container_width=True):
                                show_entity_graph(e)

                # Sources expander
                srcs = msg.get("sources", [])
                if srcs:
                    with st.expander(f"📎 {len(srcs)} Source(s) cited", expanded=False):
                        for si, src in enumerate(srcs, 1):
                            score = round(1 - src.get("distance", 0), 3)
                            st.markdown(
                                f'<div class="citation-card">'
                                f'<div class="cite-header">'
                                f'[{si}] <b>{src["citation"]}</b> &nbsp;|&nbsp; relevance: {score}</div>'
                                f'<div class="cite-text">{src["excerpt"][:350]}…</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                # Feedback buttons
                q_key = f"fb_{idx}"
                c1, c2, _ = st.columns([1, 1, 8])
                if c1.button("👍", key=f"up_{idx}", help="Good answer"):
                    post_feedback(
                        msg.get("question", ""),
                        msg["content"][:300],
                        +1,
                    )
                    st.toast("Thanks for the feedback!", icon="👍")
                if c2.button("👎", key=f"dn_{idx}", help="Poor answer"):
                    post_feedback(
                        msg.get("question", ""),
                        msg["content"][:300],
                        -1,
                    )
                    st.toast("Feedback logged. We'll improve!", icon="👎")

    # ── Input ─────────────────────────────────────────────────────────────────
    user_query = st.chat_input(
        "Ask a safety or regulatory question… "
        "(e.g. 'What PPE is required for hot work near COMP-C01?')"
    )

    if user_query:
        # Show user bubble immediately
        st.markdown(
            f'<div class="chat-bubble chat-user"><b>You:</b><br>{user_query}</div>',
            unsafe_allow_html=True,
        )
        st.session_state.messages.append({"role": "user", "content": user_query})

        with st.spinner("🧠 Hybrid router: retrieving context + generating answer…"):
            try:
                resp = requests.post(
                    f"{API_URL}/query",
                    json={
                        "question": user_query,
                        "top_k": 5,
                        "router_mode": st.session_state.get("router_mode", "hybrid"),
                    },
                    timeout=120,   # Ollama can take up to 2 min on first call
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer      = data.get("answer", "")
                    sources     = data.get("sources", [])
                    confidence  = data.get("confidence", "Medium")
                    key_points  = data.get("key_points", [])
                    entities    = data.get("entities_used", [])
                    model_used  = data.get("model_used", "unknown")
                    latency_ms  = data.get("latency_ms", 0)
                    route_target = data.get("route_target", "")
                    route_reason = data.get("route_reason", "")
                    update_llm_metrics_from_response(data)

                    # Render answer
                    conf_badge   = confidence_badge(confidence)
                    model_badge  = f'<span class="badge badge-teal">🤖 {model_used}</span>'
                    latency_badge = f'<span class="badge badge-gray">⏱ {latency_ms} ms</span>'
                    route_b = route_badge(route_target, route_reason)
                    st.markdown(
                        f'<div class="chat-bubble chat-assistant">'
                        f'<b>System:</b><br>{conf_badge} {model_badge} {latency_badge} {route_b}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if route_reason:
                        st.caption(f"🔀 **Router:** {route_reason}")
                    st.markdown(answer)

                    if key_points:
                        bullets = "".join(f"<li>{p}</li>" for p in key_points)
                        st.markdown(
                            f'<div class="keypoints-box"><b style="color:#a7f3d0">📌 Key Points</b>'
                            f'<ul>{bullets}</ul></div>',
                            unsafe_allow_html=True,
                        )

                    if entities:
                        st.markdown("<small><b>Entities mentioned (click to view graph):</b></small>", unsafe_allow_html=True)
                        cols = st.columns(len(entities[:6]))
                        for i, e in enumerate(entities[:6]):
                            with cols[i]:
                                if st.button(f"⚙ {e}", key=f"ent_btn_live_{i}", use_container_width=True):
                                    show_entity_graph(e)

                    if sources:
                        with st.expander(f"📎 {len(sources)} Source(s) cited", expanded=True):
                            for si, src in enumerate(sources, 1):
                                score = round(1 - src.get("distance", 0), 3)
                                st.markdown(
                                    f'<div class="citation-card">'
                                    f'<div class="cite-header">'
                                    f'[{si}] <b>{src["citation"]}</b> &nbsp;|&nbsp; relevance: {score}</div>'
                                    f'<div class="cite-text">{src["excerpt"][:350]}…</div>'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )

                    # Save to session
                    st.session_state.messages.append({
                        "role":        "assistant",
                        "content":     answer,
                        "confidence":  confidence,
                        "key_points":  key_points,
                        "entities_used": entities,
                        "model_used":  model_used,
                        "latency_ms":  latency_ms,
                        "route_target": route_target,
                        "route_reason": route_reason,
                        "sources":     sources,
                        "question":    user_query,
                    })
                    st.session_state.last_answer = answer
                    st.rerun()

                else:
                    st.error(f"API error {resp.status_code}: {resp.text[:200]}")

            except requests.exceptions.Timeout:
                st.error(
                    "⏳ Request timed out (>120 s). If using Ollama for the first time, "
                    "it may be loading the model — please try again in a moment."
                )
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot reach the FastAPI server at `localhost:8000`. "
                         "Start it with: `PYTHONPATH=. uvicorn src.main:app --reload`")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

    if st.session_state.messages:
        if st.button("🗑️ Clear Chat", use_container_width=False):
            st.session_state.messages = []
            st.session_state.last_answer = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DOCUMENT LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
with tab_docs:
    st.subheader("Ingested Documents")
    st.write("Browse regulatory templates and structured plant logs currently indexed in the search index.")

    try:
        docs_resp = requests.get(f"{API_URL}/documents", timeout=5)
        if docs_resp.status_code == 200:
            docs = docs_resp.json()
            if not docs:
                st.info("No documents indexed yet. Go to the **Control Panel** tab to initialise.")
            else:
                file_types = sorted(set(d["type"] for d in docs))
                sel_types  = st.multiselect("Filter by Type", file_types, default=file_types)
                search_q   = st.text_input("Search document names", "")
                filtered   = [
                    d for d in docs
                    if d["type"] in sel_types
                    and (not search_q or search_q.lower() in d["filename"].lower())
                ]
                st.write(f"Showing **{len(filtered)}** of {len(docs)} documents")
                st.markdown("---")

                for doc in filtered:
                    with st.container():
                        st.markdown(f"""
                        <div class="doc-card">
                            <h4 style="margin:0;color:#c7d2fe;">📄 {doc['filename']}</h4>
                            <div style="margin-top:0.5rem;">
                                <span class="badge badge-purple">{doc['type'].upper()}</span>
                                <span class="badge badge-blue">{doc['chunk_count']} chunks</span>
                                <span class="badge badge-gray">📅 {fmt_time(doc['upload_date'])}</span>
                                <span class="badge badge-green">🏷 {doc.get('entities_found', 0)} entities</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        with st.expander(f"Inspect chunks — {doc['filename']}"):
                            if st.button("Load Chunks", key=f"btn_{doc['doc_id']}"):
                                try:
                                    cr = requests.get(f"{API_URL}/documents/{doc['doc_id']}", timeout=5)
                                    if cr.status_code == 200:
                                        cd = cr.json()
                                        st.write(f"**{len(cd['chunks'])} chunks**")
                                        for c in cd["chunks"]:
                                            st.info(
                                                f"Chunk {c['metadata'].get('chunk_index',0)} "
                                                f"· `{c['chunk_id']}`"
                                            )
                                            st.code(c["text"], language=None)
                                    else:
                                        st.error(cr.text)
                                except Exception as err:
                                    st.error(str(err))
                        st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.error(f"Failed to fetch documents: {docs_resp.status_code}")
    except Exception as e:
        st.error(f"Could not connect to API: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — KNOWLEDGE GRAPH
# ══════════════════════════════════════════════════════════════════════════════
with tab_graph:
    st.subheader("Knowledge Graph Visualisation")
    st.write("Interactive entity-relationship graph extracted from the document corpus.")

    try:
        gr = requests.get(f"{API_URL}/graph?max_nodes=200", timeout=10)
        if gr.status_code == 200:
            gd    = gr.json()
            nodes = gd.get("nodes", [])
            edges = gd.get("edges", [])

            if not nodes:
                st.info("Graph is empty. Initialise the corpus first.")
            else:
                st.write(f"**{len(nodes)} nodes** · **{len(edges)} edges**")
                if AGRAPH_AVAILABLE:
                    ag_nodes = [
                        Node(
                            id=n["id"],
                            label=n["id"] if len(n["id"]) < 20 else n["id"][:18] + "..",
                            color=n.get("color", "#6b7280"),
                            size=max(n.get("size", 5) * 2, 10),
                            title=f"{n['id']} ({n['type']})",
                        )
                        for n in nodes
                    ]
                    ag_edges = [
                        Edge(
                            source=e["from"],
                            target=e["to"],
                            label=e.get("relation", "")[:15],
                            title=e.get("relation", ""),
                        )
                        for e in edges
                    ]
                    config = Config(
                        width="100%", height=600, directed=False, hierarchical=False,
                        node={"font": {"size": 12}},
                        physics={
                            "enabled": True, "solver": "barnesHut",
                            "barnesHut": {
                                "gravitationalConstant": -3000, "centralGravity": 0.15,
                                "springLength": 100, "springConstant": 0.05,
                                "damping": 0.09, "avoidOverlap": 0.5,
                            },
                            "stabilization": {"enabled": True, "iterations": 200, "fit": True},
                            "minVelocity": 0.75,
                        },
                    )
                    agraph(nodes=ag_nodes, edges=ag_edges, config=config)
                else:
                    st.warning("streamlit-agraph not installed. Showing table view.")
                    ca, cb = st.columns(2)
                    with ca:
                        st.markdown("**Nodes**")
                        st.dataframe(
                            [{"id": n["id"], "type": n["type"]} for n in nodes[:100]],
                            use_container_width=True, height=400,
                        )
                    with cb:
                        st.markdown("**Edges**")
                        st.dataframe(
                            [{"from": e["from"], "relation": e["relation"], "to": e["to"]} for e in edges[:100]],
                            use_container_width=True, height=400,
                        )
        else:
            st.error(f"Graph API error {gr.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach FastAPI server.")
    except Exception as e:
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ENTITY EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
with tab_entities:
    st.subheader("Entity Explorer")
    st.write("Browse entities extracted from the document corpus.")

    try:
        er = requests.get(f"{API_URL}/entities", timeout=10)
        if er.status_code == 200:
            ed  = er.json()
            ebt = ed.get("entities", {})
            stats = ed.get("stats", {})

            if not ebt:
                st.info("No entities found. Initialise the corpus first.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Nodes", stats.get("total_nodes", 0))
                c2.metric("Total Edges", stats.get("total_edges", 0))
                c3.metric("Graph Density", f"{stats.get('density', 0):.4f}")
                st.markdown("---")

                sel = st.selectbox(
                    "Filter by Entity Type",
                    sorted(ebt.keys()),
                    format_func=lambda x: x.replace("_", " ").title(),
                )
                if sel:
                    elist = ebt[sel]
                    srch  = st.text_input("Search entities", "", key="ent_srch")
                    if srch:
                        elist = [e for e in elist if srch.lower() in e.lower()]
                    st.write(f"**{len(elist)}** {sel.replace('_',' ').title()} entities")

                    for eid in elist[:50]:
                        with st.container():
                            st.markdown(f"**{eid}**")
                            if st.button("View relationships", key=f"sub_{eid}"):
                                try:
                                    sr = requests.get(
                                        f"{API_URL}/graph/entity/{eid}?depth=1", timeout=5
                                    )
                                    if sr.status_code == 200:
                                        sd = sr.json()
                                        nb = sd.get("neighbors", [])
                                        if nb:
                                            st.write(f"**{len(nb)} connections:**")
                                            for n in nb:
                                                st.markdown(
                                                    f"• *{n['relation']}* → **{n['id']}** ({n['type']})"
                                                )
                                        else:
                                            st.info("No direct connections.")
                                except Exception as ex:
                                    st.error(str(ex))
                            st.markdown("---")

                    if len(elist) > 50:
                        st.info(f"Showing first 50 of {len(elist)} entities.")
        else:
            st.error(f"Entities API error {er.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach FastAPI server.")
    except Exception as e:
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — BENCHMARK  (NEW in Day 4)
# ══════════════════════════════════════════════════════════════════════════════
with tab_bench:
    st.subheader("⚡ Ground-Truth Q&A Benchmark")
    st.write(
        "Runs the 18-question curated test set against the live RAG engine and reports "
        "**accuracy %** and **average latency**. Use this number in your pitch deck."
    )

    col_run, col_n = st.columns([3, 1])
    with col_n:
        max_q = st.number_input("Questions to run", min_value=1, max_value=18, value=18, step=1)
    with col_run:
        run_btn = st.button("🚀 Run Benchmark Now", use_container_width=True)

    if run_btn:
        prog_bar = st.progress(0, text="Starting benchmark…")
        with st.spinner(f"Running {max_q} questions against the RAG engine…"):
            try:
                resp = requests.get(
                    f"{API_URL}/benchmark/run?max_questions={max_q}",
                    timeout=600,   # can take a while with Ollama
                )
                if resp.status_code == 200:
                    bdata   = resp.json()
                    total   = bdata["total"]
                    correct = bdata["correct"]
                    acc     = bdata["accuracy_pct"]
                    avg_ms  = bdata["avg_latency_ms"]
                    model   = bdata.get("model_used", "unknown")
                    results = bdata.get("results", [])
                    prog_bar.progress(1.0, text="Done!")

                    # Headline metrics
                    st.markdown("---")
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    mc1.metric("✅ Accuracy", f"{acc}%")
                    mc2.metric("🎯 Correct", f"{correct} / {total}")
                    mc3.metric("⏱ Avg Latency", f"{avg_ms} ms")
                    mc4.metric("🤖 Model", model)

                    # Results table
                    st.markdown("### Detailed Results")
                    for r in results:
                        icon = "✅" if r["passed"] else "❌"
                        with st.expander(
                            f"{icon} [{r['id']}] {r['question']} · {r['latency_ms']} ms",
                            expanded=False,
                        ):
                            st.markdown(f"**Category:** `{r.get('category','')}`")
                            st.markdown(f"**Expected:** {r['expected']}")
                            st.markdown(f"**Got:** {r['got']}")
                            conf_col = "green" if r["confidence"] == "High" else "blue"
                            st.markdown(
                                f'<span class="badge badge-{conf_col}">Confidence: {r["confidence"]}</span>',
                                unsafe_allow_html=True,
                            )

                    # Category breakdown
                    st.markdown("### Category Breakdown")
                    from collections import defaultdict
                    cat_stats: dict = defaultdict(lambda: {"pass": 0, "fail": 0})
                    for r in results:
                        cat = r.get("category", "other")
                        if r["passed"]:
                            cat_stats[cat]["pass"] += 1
                        else:
                            cat_stats[cat]["fail"] += 1
                    for cat, s in sorted(cat_stats.items()):
                        total_cat = s["pass"] + s["fail"]
                        pct = round(s["pass"] / total_cat * 100)
                        st.markdown(
                            f"**{cat.replace('_',' ').title()}** — "
                            f"{s['pass']}/{total_cat} ({pct}%)"
                        )
                else:
                    prog_bar.empty()
                    st.error(f"Benchmark API error {resp.status_code}: {resp.text[:300]}")

            except requests.exceptions.Timeout:
                st.error("Benchmark timed out — reduce question count or check Ollama.")
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach FastAPI server.")
            except Exception as e:
                st.error(f"Error: {e}")

    # Static info
    st.markdown("---")
    st.info(
        "**Scoring method:** keyword-overlap between expected answer and LLM output. "
        "A question passes if ≥25 % of expected keywords with length >4 chars appear in the answer."
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — CONTROL PANEL
# ══════════════════════════════════════════════════════════════════════════════
with tab_setup:
    st.subheader("Vector Database & Corpus Control")

    st.markdown("### **🔀 Hybrid LLM Router**")
    st.caption(
        "Route sensitive operational data locally while sending complex reasoning to the cloud. "
        "Hybrid mode auto-classifies each query."
    )
    mode_options = ["hybrid", "local", "cloud"]
    mode_labels = [ROUTER_MODE_LABELS[m] for m in mode_options]
    current_mode = st.session_state.get("router_mode", "hybrid")
    selected_label = st.radio(
        "Inference routing",
        mode_labels,
        index=mode_options.index(current_mode) if current_mode in mode_options else 0,
        horizontal=True,
        help=(
            "**Hybrid:** confidential/simple → Ollama; complex cross-doc reasoning → NVIDIA. "
            "**Local:** all queries stay on-premises. **Cloud:** all queries use NVIDIA NIM."
        ),
    )
    st.session_state["router_mode"] = mode_options[mode_labels.index(selected_label)]

    if st.session_state["router_mode"] == "hybrid":
        st.info(
            "**Auto-routing examples:** "
            "“Show employee incident history” → 🔒 Local · "
            "“Cross-reference safety Regulation 4.2 with engineering schematics” → ☁️ Cloud"
        )
    elif st.session_state["router_mode"] == "local":
        st.success("🔒 **Local Mode** — all queries processed on Ollama. Data never leaves the plant network.")
    else:
        st.warning("☁️ **Cloud Mode** — all queries sent to NVIDIA NIM for maximum reasoning power.")

    st.markdown("---")
    st.write("Initialise the index or upload new documents.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### **1. Core Corpus Initialisation**")
        st.write(
            "Index all pre-bundled files: OISD / DGMS / Factory Act regulatory docs "
            "plus synthetic work orders, permits, and incident reports."
        )
        if st.button("🚀 Scan & Index Default Corpus", use_container_width=True):
            with st.spinner("Parsing, embedding, and building knowledge graph… (~60 s)"):
                try:
                    r = requests.post(f"{API_URL}/ingest/initialize", timeout=180)
                    if r.status_code == 200:
                        s = r.json()["stats"]
                        st.success(
                            f"✅ Indexed **{s['files_ingested']}** documents · "
                            f"**{s['total_chunks']}** chunks"
                        )
                        st.rerun()
                    else:
                        st.error(f"Error: {r.text}")
                except Exception as e:
                    st.error(str(e))

    with col2:
        st.markdown("### **2. Upload New Documents**")
        st.write("Upload PDF, DOCX, CSV, or TXT files to add to the live search index.")
        uploaded = st.file_uploader(
            "Select Files",
            type=["txt", "pdf", "docx", "csv"],
            accept_multiple_files=True,
        )
        if uploaded:
            if st.button("📤 Ingest Selected Files", use_container_width=True):
                files_payload = [(
                    "files", (uf.name, uf.getvalue(), uf.type)
                ) for uf in uploaded]
                with st.spinner(f"Ingesting {len(uploaded)} files…"):
                    try:
                        r = requests.post(
                            f"{API_URL}/ingest/upload",
                            files=files_payload,
                            timeout=120,
                        )
                        if r.status_code == 200:
                            results = r.json()["results"]
                            ok = sum(1 for x in results if x.get("status") == "success")
                            st.success(f"✅ Uploaded and ingested {ok} file(s)")
                            for x in results:
                                if x.get("status") == "success":
                                    st.write(f"✓ **{x['doc_id']}** · {x['chunk_count']} chunks")
                                else:
                                    st.error(f"✗ **{x['doc_id']}**: {x.get('error')}")
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {r.text}")
                    except Exception as e:
                        st.error(str(e))

    st.markdown("---")
    st.markdown("### **Debug: Raw Vector Search**")
    st.caption("Test retrieval quality without LLM — great for tuning chunk size / top-k.")
    dq = st.text_input("Search query (raw vector similarity)", "quarterly inspection")
    dn = st.slider("Top-k", 1, 10, 5)
    if st.button("🔍 Run Debug Search"):
        try:
            dr = requests.get(f"{API_URL}/debug/search?q={dq}&n={dn}", timeout=15)
            if dr.status_code == 200:
                dd = dr.json()
                st.write(f"**{len(dd['hits'])} hits** (total in DB: {dd['total_in_db']})")
                for h in dd["hits"]:
                    st.markdown(
                        f"**[{h['rank']}]** `{h['doc_id']}` — score: **{h['score']}**"
                    )
                    st.caption(h["excerpt"])
                    st.markdown("---")
            else:
                st.error(dr.text)
        except Exception as e:
            st.error(str(e))
