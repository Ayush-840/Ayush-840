"""Query Engine — context retrieval + answer generation.

Public API
----------
retrieve_context(query, top_k, collection_name)
    Embeds the query, searches ChromaDB for top_k chunks, extracts entities with
    spaCy/regex, traverses the NetworkX knowledge graph 1-hop per entity, and
    returns a merged, deduplicated context dict:
        {vector_chunks: [...], graph_entities: [...], graph_relations: [...]}

generate_answer(query, context)
    Builds a structured RAG prompt from the context object, calls the local LLM
    (Ollama if running, otherwise smart-fallback), and safe-parses the required
    JSON response:
        {answer: str, sources: [{doc_id, excerpt}], confidence: float,
         entities_used: [str], key_points: [str]}

The module does NOT call the Claude API — it uses Ollama (local, no API key).
To enable LLM answers: install Ollama (https://ollama.com) and run
  ollama pull llama3.2 && ollama serve
"""

import json
from typing import Dict, Any, List, Optional
from loguru import logger

from src.pipeline.embedder import TextEmbedder
from src.storage.chroma_store import VectorStore
from src.pipeline.extractor import extract_entities
from src.graph.knowledge_graph import get_knowledge_graph
from src.pipeline.llm import _extract_json, _smart_fallback
from src.pipeline.router import resolve_llm, llm_display_label

# Singletons for reusing instances across calls
_embedder: Optional[TextEmbedder] = None
_vector_store: Optional[VectorStore] = None


def get_embedder() -> TextEmbedder:
    """Get or create the text embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedder()
    return _embedder


def get_vector_store(collection_name: str = "docs") -> VectorStore:
    """Get or create the vector store instance for the specified collection."""
    global _vector_store
    if _vector_store is None or _vector_store.collection_name != collection_name:
        _vector_store = VectorStore(collection_name=collection_name)
    return _vector_store


def retrieve_context(query: str, top_k: int = 5, collection_name: str = "docs") -> Dict[str, Any]:
    """Retrieve and merge context from ChromaDB (vector) and NetworkX (graph).

    Args:
        query: The natural language search query.
        top_k: Number of chunks to retrieve from the vector store.
        collection_name: ChromaDB collection to search against.

    Returns:
        A dictionary with merged and deduplicated context:
        {
            "vector_chunks": [
                {
                    "chunk_id": str,
                    "text": str,
                    "metadata": dict,
                    "distance": float
                },
                ...
            ],
            "graph_entities": [
                {
                    "id": str,
                    "type": str
                },
                ...
            ],
            "graph_relations": [
                {
                    "source": str,
                    "target": str,
                    "relation": str
                },
                ...
            ]
        }
    """
    logger.info(f"Retrieving context for query: '{query}'")

    # 1. Embed the query and retrieve top_k chunks from ChromaDB
    embedder = get_embedder()
    store = get_vector_store(collection_name)
    
    query_embedding = embedder.embed_query(query)
    search_results = store.query(query_embedding, n_results=top_k)

    vector_chunks = []
    if search_results and search_results["documents"] and len(search_results["documents"][0]) > 0:
        for i in range(len(search_results["documents"][0])):
            chunk_id = search_results["ids"][0][i]
            text = search_results["documents"][0][i]
            metadata = search_results["metadatas"][0][i]
            distance = search_results["distances"][0][i]
            vector_chunks.append({
                "chunk_id": chunk_id,
                "text": text,
                "metadata": metadata,
                "distance": distance
            })
    logger.debug(f"Retrieved {len(vector_chunks)} vector chunks from ChromaDB collection '{collection_name}'")

    # 2. Extract entities from the query using the existing extractor
    extracted_entities = extract_entities(query)
    
    # Flatten and deduplicate all query entities
    query_entity_ids = set()
    for category, entities in extracted_entities.items():
        for entity in entities:
            query_entity_ids.add(entity)

    # 3. Traverse the NetworkX graph 1-hop for each found entity
    kg = get_knowledge_graph()
    graph_entities_list = []
    graph_relations_list = []

    for entity in query_entity_ids:
        # Check if node exists in NetworkX graph
        if kg.graph.has_node(entity):
            # Include the queried node itself
            graph_entities_list.append({
                "id": entity,
                "type": kg.graph.nodes[entity].get("type", "unknown")
            })

            # Traverse 1-hop neighbors
            for neighbor in kg.graph.neighbors(entity):
                # Add neighbor node
                graph_entities_list.append({
                    "id": neighbor,
                    "type": kg.graph.nodes[neighbor].get("type", "unknown")
                })
                
                # Add relationship edge
                edge_data = kg.graph.edges[entity, neighbor]
                graph_relations_list.append({
                    "source": entity,
                    "target": neighbor,
                    "relation": edge_data.get("relation", "related_to")
                })

    # 4. Deduplicate graph nodes and edges
    # Deduplicate entities by 'id'
    seen_entities = set()
    deduped_entities = []
    for ent in graph_entities_list:
        if ent["id"] not in seen_entities:
            seen_entities.add(ent["id"])
            deduped_entities.append(ent)

    # Deduplicate relations (sorting source/target to treat undirected edges as identical)
    seen_relations = set()
    deduped_relations = []
    for rel in graph_relations_list:
        edge_key = (
            min(rel["source"], rel["target"]),
            max(rel["source"], rel["target"]),
            rel["relation"]
        )
        if edge_key not in seen_relations:
            seen_relations.add(edge_key)
            deduped_relations.append(rel)

    logger.debug(f"Traversed graph: found {len(deduped_entities)} entities and {len(deduped_relations)} relations")

    return {
        "vector_chunks": vector_chunks,
        "graph_entities": deduped_entities,
        "graph_relations": deduped_relations
    }


# ── Answer generation ──────────────────────────────────────────────────────────

# Confidence guidance injected into the prompt so the LLM scores it consistently.
_CONFIDENCE_GUIDE = """
Confidence scoring rules (follow strictly — do NOT invent a number):
  High   (0.80-1.00) → direct, clear answer present in ≥2 document sources
  Medium (0.50-0.79) → partial information or only 1 source found, or no graph entities
  Low    (0.00-0.49) → context is empty, off-topic, or graph returned nothing

Hint for this specific query:
  vector_chunks retrieved: {n_chunks}
  graph entities matched : {n_entities}
  graph relations found  : {n_relations}
"""

_RAG_TEMPLATE = """
You are an Industrial Knowledge Intelligence AI. Answer ONLY using the retrieved
context below. Never fabricate facts.

=== DOCUMENT CONTEXT ===
{doc_context}

=== KNOWLEDGE GRAPH RELATIONSHIPS ===
{graph_context}

=== QUESTION ===
{question}

{confidence_guide}

Respond with ONLY this JSON object — no markdown fences, no preamble, no trailing text:
{{"answer": "<detailed answer citing [Source N] labels>",
  "sources": [{{"doc_id": "<doc_id>", "excerpt": "<short excerpt>"}}],
  "confidence": <float 0.0-1.0>,
  "entities_used": ["<entity IDs mentioned>"],
  "key_points": ["<key point 1>", "<key point 2>", "<key point 3>"]}}
"""


def generate_answer(
    query: str,
    context: Dict[str, Any],
    router_mode: str = "hybrid",
) -> Dict[str, Any]:
    """Generate a structured RAG answer from the context object produced by retrieve_context().

    Args:
        query:   The original user question.
        context: Output of retrieve_context() — must contain keys
                 vector_chunks, graph_entities, graph_relations.

    Returns:
        A dict with:
          answer       (str)   — full markdown answer citing sources
          sources      (list)  — [{doc_id, excerpt}, ...]
          confidence   (float) — 0.0–1.0 computed from retrieval quality heuristics
          entities_used (list) — entity IDs from the graph traversal
          key_points   (list)  — bullet-point summaries
          model_used   (str)   — label for display (e.g. 'Ollama / llama3.2')
    """
    chunks   = context.get("vector_chunks", [])
    entities = context.get("graph_entities", [])
    relations = context.get("graph_relations", [])

    # ── Confidence heuristic (passed as guidance to the prompt) ──────────────
    n_chunks    = len(chunks)
    n_entities  = len(entities)
    n_relations = len(relations)

    # Baseline confidence from retrieval quality — LLM adjusts within this band
    if n_chunks >= 2 and n_entities >= 1:
        guidance_conf = "High   (0.80-1.00)"
    elif n_chunks >= 1 or n_entities >= 1:
        guidance_conf = "Medium (0.50-0.79)"
    else:
        guidance_conf = "Low    (0.00-0.49)"

    # ── Build numbered source context ─────────────────────────────────────────
    doc_parts: List[str] = []
    source_list: List[Dict] = []
    for i, c in enumerate(chunks[:3], 1):
        doc_id  = c["metadata"].get("doc_id", c.get("chunk_id", "unknown"))
        text    = c["text"].strip()
        dist    = c.get("distance", 0.0)
        score   = round(1.0 - float(dist), 3)
        doc_parts.append(f"[Source {i}] {doc_id}  (relevance: {score})\n{text[:400]}...")
        source_list.append({"doc_id": doc_id, "excerpt": text[:250]})

    doc_context  = "\n\n---\n\n".join(doc_parts) or "No documents retrieved."

    # ── Build graph context string ─────────────────────────────────────────────
    graph_lines: List[str] = []
    for rel in relations[:10]:
        graph_lines.append(
            f"  {rel['source']} --[{rel['relation']}]--> {rel['target']}"
        )
    if not graph_lines:
        graph_lines = ["  No knowledge-graph relationships found for this query."]
    graph_context = "\n".join(graph_lines)

    entity_ids = [e["id"] for e in entities]

    # ── Build prompt ──────────────────────────────────────────────────────────
    conf_guide = _CONFIDENCE_GUIDE.format(
        n_chunks=n_chunks,
        n_entities=n_entities,
        n_relations=n_relations,
    ) + f"  Suggested confidence band: {guidance_conf}"

    prompt = _RAG_TEMPLATE.format(
        doc_context=doc_context,
        graph_context=graph_context,
        question=query,
        confidence_guide=conf_guide,
    )

    # ── Call LLM or fall back to smart context formatter ─────────────
    llm, route = resolve_llm(router_mode, query, context)
    llm_label = llm_display_label(llm)

    if llm.available:
        logger.info(f"generate_answer: calling {llm_label} [{llm.model}] | route={route['target']}")
        try:
            raw    = llm.generate(prompt, max_tokens=1200)
            result = _extract_json(raw)
        except Exception as e:
            logger.error(f"{llm_label} call failed: {e}. Using smart fallback.")
            result = None
    else:
        result = None

    if result is None:
        logger.info("generate_answer: using smart-context fallback")
        # Reuse llm.py fallback, then convert to query_engine schema
        fb = _smart_fallback(query, [
            {"doc_id": c["metadata"].get("doc_id", ""),
             "text": c["text"],
             "citation": c["metadata"].get("doc_id", ""),
             "distance": c.get("distance", 0.0)}
            for c in chunks
        ], graph_lines)
        result = fb
        result["confidence"] = 0.5 if chunks else 0.2
        result["sources"] = source_list
        result["model_used"] = "Smart Context"
        result["entities_used"] = entity_ids
        result["llm_metrics"] = {}
        result["route_target"] = route.get("target", "local")
        result["route_reason"] = route.get("reason", "")
        result["router_mode"] = route.get("router_mode", router_mode)
        return result

    # ── Normalise output schema ───────────────────────────────────────────────
    # Ensure confidence is a float
    raw_conf = result.get("confidence", 0.5)
    if isinstance(raw_conf, str):
        # LLM returned "High" / "Medium" / "Low" — map to float
        raw_conf = {"high": 0.85, "medium": 0.60, "low": 0.25}.get(
            raw_conf.lower(), 0.5
        )
    result["confidence"] = round(float(raw_conf), 3)

    # Merge entity IDs from graph traversal into entities_used
    existing_ents = result.get("entities_used", result.get("entities_mentioned", []))
    result["entities_used"] = list(set(existing_ents + entity_ids))

    # Ensure sources list exists
    if not result.get("sources"):
        result["sources"] = source_list

    result.setdefault("key_points", [])
    result["model_used"] = (
        f"{llm_label} / {llm.model}" if llm.available else "Smart Context"
    )
    metrics = getattr(llm, "last_metrics", None)
    result["llm_metrics"] = metrics.to_dict() if metrics else {}
    result["route_target"] = route.get("target", "local")
    result["route_reason"] = route.get("reason", "")
    result["router_mode"] = route.get("router_mode", router_mode)

    logger.info(
        f"generate_answer done — confidence={result['confidence']}, "
        f"model={result.get('model_used')}"
    )
    return result


if __name__ == "__main__":
    """
    Standalone smoke-test:
      PYTHONPATH=. python3 src/pipeline/query_engine.py
    Tests retrieve_context + generate_answer against 3 benchmark questions.
    """
    SAMPLE_QUERIES = [
        "Which equipment requires quarterly inspection?",
        "What permits are associated with PRM-2026-5001?",
        "What are the OISD-116 safety requirements for PUMP-A01?",
    ]

    print("=" * 70)
    print("Query Engine — retrieve_context + generate_answer smoke test")
    print("=" * 70)

    for i, q in enumerate(SAMPLE_QUERIES, 1):
        print(f"\n{'─'*60}")
        print(f"Q{i}: {q}")
        print("─" * 60)

        ctx = retrieve_context(q, top_k=5)
        print(
            f"  context → {len(ctx['vector_chunks'])} chunks, "
            f"{len(ctx['graph_entities'])} entities, "
            f"{len(ctx['graph_relations'])} relations"
        )

        ans = generate_answer(q, ctx)
        print(f"  confidence : {ans.get('confidence')}")
        print(f"  model      : {ans.get('model_used')}")
        print(f"  entities   : {ans.get('entities_used', [])[:4]}")
        print(f"  answer     : {str(ans.get('answer',''))[:200]}...")
        if ans.get("sources"):
            print(f"  sources    : {[s['doc_id'] for s in ans['sources'][:3]]}")
