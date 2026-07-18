"""Hybrid LLM router — route queries to local Ollama or cloud NVIDIA NIM.

Enterprise factories need sensitive personnel/incident data to stay on-premises
while complex cross-document reasoning can use the cloud reasoning engine.
"""

import re
from typing import Any, Dict, Optional, Tuple

from loguru import logger

from src.pipeline.llm import NvidiaLLM, OllamaLLM, get_nvidia_llm, get_ollama_llm

ROUTER_MODES = ("hybrid", "local", "cloud")

# Personnel / HR / incident data — keep on local Ollama
_CONFIDENTIAL_PHRASES = (
    "employee",
    "incident history",
    "incident report",
    "personnel",
    "disciplinary",
    "medical record",
    "salary",
    "witness statement",
    "staff record",
    "hr record",
    "confidential",
    "private data",
    "injury report",
    "accident victim",
    "employee id",
)

# Multi-hop reasoning — prefer NVIDIA NIM
_REASONING_PHRASES = (
    "cross-reference",
    "cross reference",
    "crossreference",
    "compare and",
    "correlat",
    "deep engineering",
    "engineering schematic",
    "schematics",
    "multi-step",
    "multistep",
    "relationship between",
    "interdepend",
    "synthesize",
    "comprehensive analysis",
    "regulation",
    "analyze the",
    "analyse the",
    "evaluate compliance across",
    "how does .* relate",
    "both .* and",
)

_REASONING_REGEX = tuple(re.compile(p, re.I) for p in _REASONING_PHRASES)

_SIMPLE_PHRASES = (
    "show ",
    "list ",
    "what is ",
    "who is ",
    "when was ",
    "where is ",
    "how many ",
    "status of ",
    "find ",
    "get ",
)


def classify_route(question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """Score a query and pick local vs cloud for hybrid mode."""
    q = question.lower().strip()
    ctx = context or {}

    for phrase in _CONFIDENTIAL_PHRASES:
        if phrase in q:
            return {
                "target": "local",
                "reason": "Confidential personnel/incident data — kept on-premises (Ollama)",
            }

    for pattern in _REASONING_REGEX:
        if pattern.search(q):
            return {
                "target": "cloud",
                "reason": "Complex cross-document reasoning — routed to NVIDIA NIM",
            }

    n_rel = len(ctx.get("graph_relations", []))
    n_chunks = len(ctx.get("vector_chunks", []))
    if n_rel >= 4 or (n_rel >= 2 and n_chunks >= 3):
        return {
            "target": "cloud",
            "reason": "Rich graph + document context — cloud reasoning engine",
        }

    word_count = len(q.split())
    if word_count <= 10 and any(q.startswith(p) or f" {p.strip()} " in f" {q} " for p in _SIMPLE_PHRASES):
        return {
            "target": "local",
            "reason": "Simple lookup query — local model sufficient",
        }

    return {
        "target": "local",
        "reason": "Standard operational query — processed locally for data privacy",
    }


def resolve_llm(
    router_mode: str,
    question: str,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Any], Dict[str, str]]:
    """Pick the LLM backend and return routing metadata for the UI."""
    mode = (router_mode or "hybrid").lower()
    if mode not in ROUTER_MODES:
        mode = "hybrid"

    nvidia = get_nvidia_llm()
    ollama = get_ollama_llm()

    if mode == "local":
        route = {"target": "local", "reason": "Control Panel: Local Mode (Ollama) enforced"}
    elif mode == "cloud":
        route = {"target": "cloud", "reason": "Control Panel: Cloud Mode (NVIDIA NIM) enforced"}
    else:
        route = classify_route(question, context)

    target = route["target"]

    if target == "cloud":
        if nvidia.available:
            logger.info(f"Router → NVIDIA NIM | {route['reason']}")
            return nvidia, {**route, "router_mode": mode}
        if ollama.available:
            fallback = f"{route['reason']} (NVIDIA unavailable — Ollama fallback)"
            logger.warning(f"Router → Ollama fallback | {fallback}")
            return ollama, {"target": "local", "reason": fallback, "router_mode": mode}
        logger.warning("Router → no LLM available")
        return ollama, {**route, "router_mode": mode}

    if ollama.available:
        logger.info(f"Router → Ollama | {route['reason']}")
        return ollama, {**route, "router_mode": mode}
    if nvidia.available:
        fallback = f"{route['reason']} (Ollama unavailable — NVIDIA fallback)"
        logger.warning(f"Router → NVIDIA fallback | {fallback}")
        return nvidia, {"target": "cloud", "reason": fallback, "router_mode": mode}
    logger.warning("Router → no LLM available")
    return ollama, {**route, "router_mode": mode}


def llm_display_label(llm: Any) -> str:
    if isinstance(llm, NvidiaLLM):
        return "NVIDIA API"
    if isinstance(llm, OllamaLLM):
        return "Ollama"
    return "Smart Context"
