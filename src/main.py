"""Industrial Knowledge Intelligence — Main API Application.

Day 4: Real LLM integration (Ollama, no API key), /benchmark/run, /feedback,
        /debug/search added.
"""

import json
import os
import shutil
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger

from src.config import settings
from src.pipeline.ingest import IngestionPipeline
from src.pipeline.embedder import TextEmbedder
from src.pipeline.extractor import extract_entities
from src.pipeline.compliance import check_compliance
from src.pipeline.llm import generate_rag_answer, get_llm
from src.pipeline.query_engine import retrieve_context, generate_answer
from src.storage.chroma_store import VectorStore
from src.graph.knowledge_graph import get_knowledge_graph

# In-memory feedback store (persisted to disk on each write)
_FEEDBACK_FILE = settings.data_dir / "feedback.jsonl"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG-powered industrial knowledge intelligence system with vector search + knowledge graph.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ComplianceRequest(BaseModel):
    """Schema for compliance check requests."""
    requirement: str
    top_k: Optional[int] = 10


class QueryRequest(BaseModel):
    """Schema for incoming RAG queries."""
    question: str = Field(..., min_length=1, max_length=1000, description="The query string")
    top_k: Optional[int] = Field(settings.top_k, ge=1, le=20)
    router_mode: Optional[str] = Field(
        "hybrid",
        description="LLM routing: hybrid (auto), local (Ollama), or cloud (NVIDIA NIM)",
    )


class QueryResponse(BaseModel):
    """Schema for RAG query response (Day 4: includes LLM fields)."""
    answer: str
    sources: List[dict]
    confidence: Union[str, float]   # float 0.0-1.0 from query_engine, or 'High'/'Medium'/'Low'
    entities_used: List[str] = []
    key_points: List[str] = []
    model_used: str = "unknown"
    latency_ms: int = 0
    llm_latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    token_throughput_tps: float = 0.0
    router_mode: str = "hybrid"
    route_target: str = ""
    route_reason: str = ""


class FeedbackRequest(BaseModel):
    """Thumbs-up / thumbs-down on an answer."""
    question: str
    answer: str
    rating: int          # +1 = positive, -1 = negative
    comment: Optional[str] = None


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "version": settings.app_version}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


# --- Compliance Check Endpoint ---

@app.post("/compliance/check")
async def compliance_check(request: ComplianceRequest):
    """Check a regulatory requirement against ingested procedures for gaps."""
    try:
        logger.info(f"Compliance check request: {request.requirement[:100]}...")
        result = check_compliance(request.requirement, top_k=request.top_k)
        return result
    except Exception as e:
        logger.error(f"Error during compliance check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Knowledge Graph Endpoints ---

@app.get("/graph")
async def get_graph(max_nodes: int = Query(default=500, le=2000)):
    """Get the full knowledge graph as nodes/edges JSON for visualization."""
    try:
        kg = get_knowledge_graph()
        return kg.to_json(max_nodes=max_nodes)
    except Exception as e:
        logger.error(f"Error fetching knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/search")
async def graph_search(
    q: str = Query(..., description="Search term to match against node IDs"),
    node_types: Optional[str] = Query(default=None, description="Comma-separated list of node types to filter by"),
    limit: int = Query(default=50, le=200, description="Max results to return")
):
    """Search for graph nodes by name/label."""
    try:
        kg = get_knowledge_graph()
        types_list = [t.strip() for t in node_types.split(",")] if node_types else None
        matches = kg.search_nodes(q, node_types=types_list, limit=limit)
        return {"query": q, "results": matches, "count": len(matches)}
    except Exception as e:
        logger.error(f"Error searching graph nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/node/{node_id}")
async def get_graph_node(node_id: str):
    """Get node metadata, immediate neighbors, and linked resource IDs."""
    try:
        kg = get_knowledge_graph()
        return kg.get_node_metadata(node_id)
    except Exception as e:
        logger.error(f"Error fetching node metadata for {node_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/top")
async def get_graph_top(
    n: int = Query(default=30, le=200, description="Number of top nodes to return"),
    node_types: Optional[str] = Query(default=None, description="Comma-separated list of node types to filter by")
):
    """Get top N most-connected nodes for initial graph loading."""
    try:
        kg = get_knowledge_graph()
        types_list = [t.strip() for t in node_types.split(",")] if node_types else None
        top_ids = kg.get_top_nodes(n=n, node_types=types_list)
        subgraph = kg.get_subgraph_for_nodes(top_ids)
        return subgraph
    except Exception as e:
        logger.error(f"Error fetching top graph nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@lru_cache(maxsize=128)
def _fetch_subgraph_cached(entity_id: str, depth: int) -> Optional[dict]:
    """Helper to fetch and format the subgraph, cached in-memory."""
    kg = get_knowledge_graph()
    raw = kg.get_entity_neighbors(entity_id, depth=depth)
    
    if "error" in raw:
        return None
        
    center_data = raw.get("center", {})
    center = {
        "id": center_data.get("id", entity_id),
        "label": center_data.get("id", entity_id),
        "type": center_data.get("type", "unknown")
    }
    
    neighbors = []
    edges = []
    
    for n in raw.get("neighbors", []):
        neighbors.append({
            "id": n.get("id"),
            "label": n.get("id"),
            "type": n.get("type", "unknown"),
            "relation": n.get("relation", "related_to")
        })
        edges.append({
            "source": n.get("source"),
            "target": n.get("id"),
            "relation_type": n.get("relation", "related_to")
        })
        
    return {
        "center": center,
        "neighbors": neighbors,
        "edges": edges
    }

@app.get("/graph/entity/{entity_id}")
async def get_entity_subgraph(entity_id: str, depth: int = Query(default=1, le=2)):
    """Get subgraph centered on one entity for frontend visualization."""
    try:
        subgraph = _fetch_subgraph_cached(entity_id, depth)
        if not subgraph:
            raise HTTPException(
                status_code=404, 
                detail=f"Entity '{entity_id}' not found in the knowledge graph. Check the ID."
            )
        return subgraph
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching entity subgraph for {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/entities")
async def get_entities():
    """List all extracted entities grouped by type."""
    try:
        kg = get_knowledge_graph()
        entities_by_type = kg.get_entities_by_type()
        stats = kg.get_stats()
        return {
            "entities": entities_by_type,
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Error fetching entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Ingestion Endpoints ---

SUPPORTED_EXTENSIONS = {".txt", ".csv", ".pdf", ".docx"}

@app.post("/ingest/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload and ingest one or more documents (PDF, DOCX, CSV, TXT)."""
    pipeline = IngestionPipeline()
    temp_dir = settings.data_dir / "temp_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        store = VectorStore()
        existing_docs = store.collection.get(include=["metadatas"])
        existing_filenames = set()
        if existing_docs and existing_docs.get("metadatas"):
            for meta in existing_docs["metadatas"]:
                if meta and "doc_id" in meta:
                    existing_filenames.add(meta["doc_id"])
    except Exception as e:
        logger.warning(f"Failed to fetch existing documents for duplicate check: {e}")
        existing_filenames = set()
    
    results = []
    for file in files:
        safe_filename = Path(file.filename).name
        ext = Path(safe_filename).suffix.lower()
        
        if ext not in SUPPORTED_EXTENSIONS:
            results.append({
                "doc_id": safe_filename, 
                "status": "error", 
                "error": f"Unsupported file type: '{ext}'. Allowed: {', '.join(SUPPORTED_EXTENSIONS)}"
            })
            continue
            
        if safe_filename in existing_filenames:
            results.append({
                "doc_id": safe_filename, 
                "status": "error", 
                "error": "Duplicate upload. A document with this filename is already indexed."
            })
            continue

        temp_file_path = temp_dir / safe_filename
        try:
            # Save file temporarily to disk
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            if temp_file_path.stat().st_size == 0:
                raise ValueError("File is empty or corrupted.")
            
            # Ingest file (it will copy to uploads persistently)
            logger.info(f"Uploading and ingesting: {safe_filename}")
            res = pipeline.ingest_file(temp_file_path, copy_to_uploads=True)
            results.append(res)
        except Exception as e:
            logger.error(f"Failed to ingest uploaded file {safe_filename}: {e}")
            results.append({"doc_id": safe_filename, "status": "error", "error": f"File parsing failed: {str(e)}"})
        finally:
            # Clean up temporary file
            if temp_file_path.exists():
                os.remove(temp_file_path)
                
    return {"results": results}


@app.post("/ingest/initialize")
async def initialize_corpus():
    """Clear database and ingest all files in default corpus directories."""
    try:
        pipeline = IngestionPipeline()
        stats = pipeline.initialize_corpus()
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Error during corpus initialization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize corpus: {str(e)}")


# --- Document Information Endpoints ---

@app.get("/documents")
async def list_documents():
    """List all ingested documents with metadata."""
    pipeline = IngestionPipeline()
    return pipeline.list_documents()


@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get full details and chunks for a specific document."""
    store = VectorStore()
    
    # Query ChromaDB for all chunks where doc_id matches
    # Use ChromaDB client collection.get
    try:
        results = store.collection.get(where={"doc_id": doc_id})
        
        if not results or not results["ids"]:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found or has no chunks.")
            
        chunks = []
        for i in range(len(results["ids"])):
            chunks.append({
                "chunk_id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i]
            })
            
        # Sort chunks by chunk_index to ensure text is in order
        chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
        
        return {
            "doc_id": doc_id,
            "filename": doc_id,
            "chunk_count": len(chunks),
            "chunks": chunks
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Query Endpoint ───────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """POST /query — retrieve context then generate a structured answer.

    Uses query_engine.retrieve_context() (vector + graph) then
    query_engine.generate_answer() (Ollama LLM or smart fallback).
    Returns {answer, sources, confidence, entities_used, key_points, model_used}.
    """
    t_start = time.time()

    # ── Guard: empty question ───────────────────────────────────────────────
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    try:
        logger.info(f"POST /query: '{request.question}'")

        # ── Guard: empty database ────────────────────────────────────────────
        store = VectorStore()
        if store.count() == 0:
            return QueryResponse(
                answer=(
                    "No documents indexed yet. "
                    "Please open the **Control & Setup Panel** tab and click "
                    "**Scan & Index Default Corpus** to initialise the system."
                ),
                sources=[],
                confidence=0.0,
                entities_used=[],
                key_points=[],
                model_used="N/A",
                latency_ms=0,
            )

        # ── Step 1: Retrieve merged context (vector + graph) ────────────────────
        top_k   = request.top_k or settings.top_k
        context = retrieve_context(request.question, top_k=top_k)

        # ── Guard: no results found ────────────────────────────────────────────
        if not context["vector_chunks"] and not context["graph_entities"]:
            return QueryResponse(
                answer=(
                    "No matching documents or entities were found for your query. "
                    "Try rephrasing, or check that the corpus has been indexed."
                ),
                sources=[],
                confidence=0.0,
                entities_used=[],
                key_points=[],
                model_used="N/A",
                latency_ms=int((time.time() - t_start) * 1000),
            )

        # ── Step 2: Generate answer (LLM / smart fallback) ─────────────────────
        ans = generate_answer(request.question, context, router_mode=request.router_mode or "hybrid")
        llm_metrics = ans.get("llm_metrics") or {}

        latency_ms = int((time.time() - t_start) * 1000)
        logger.info(
            f"/query answered in {latency_ms} ms | "
            f"confidence={ans.get('confidence')} | model={ans.get('model_used')} | "
            f"route={ans.get('route_target')} | llm={llm_metrics.get('llm_latency_ms', 0)} ms"
        )

        return QueryResponse(
            answer       = ans.get("answer", ""),
            sources      = ans.get("sources", []),
            confidence   = ans.get("confidence", 0.0),
            entities_used= ans.get("entities_used", []),
            key_points   = ans.get("key_points", []),
            model_used   = ans.get("model_used", "unknown"),
            latency_ms   = latency_ms,
            llm_latency_ms       = llm_metrics.get("llm_latency_ms", 0),
            prompt_tokens        = llm_metrics.get("prompt_tokens", 0),
            completion_tokens    = llm_metrics.get("completion_tokens", 0),
            total_tokens         = llm_metrics.get("total_tokens", 0),
            estimated_cost_usd   = llm_metrics.get("estimated_cost_usd", 0.0),
            token_throughput_tps = llm_metrics.get("token_throughput_tps", 0.0),
            router_mode          = ans.get("router_mode", request.router_mode or "hybrid"),
            route_target         = ans.get("route_target", ""),
            route_reason         = ans.get("route_reason", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in POST /query: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ── Benchmark Endpoint ────────────────────────────────────────────────────────

@app.get("/benchmark/run")
async def run_benchmark(max_questions: int = Query(default=18, le=50)):
    """Run the ground-truth Q&A benchmark and return accuracy metrics."""
    qa_file = settings.benchmarks_dir / "qa_pairs.json"
    if not qa_file.exists():
        raise HTTPException(status_code=404, detail="No benchmark file found at data/benchmarks/qa_pairs.json")

    try:
        qa_pairs = json.loads(qa_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load benchmark file: {e}")

    store    = VectorStore()

    if store.count() == 0:
        raise HTTPException(status_code=400, detail="Vector store is empty. Run /ingest/initialize first.")

    results   = []
    total     = min(len(qa_pairs), max_questions)
    correct   = 0
    total_ms  = 0

    for qa in qa_pairs[:total]:
        t0 = time.time()
        question = qa["question"]
        expected = qa["answer"].lower()

        context = retrieve_context(question, top_k=3)
        llm_result = generate_answer(question, context)
        
        answer_text = llm_result.get("answer", "")
        sources_list = llm_result.get("sources", [])
        retrieved_source_docs = {s.get("citation", s.get("doc_id", "")) for s in sources_list}
        
        elapsed_ms = int((time.time() - t0) * 1000)
        total_ms += elapsed_ms

        expected_source_docs = set(qa.get("source_docs", []))

        # Simple keyword-overlap scoring
        expected_keywords = set(expected.split())
        answer_lower      = answer_text.lower()
        matches = sum(1 for kw in expected_keywords if len(kw) > 4 and kw in answer_lower)
        hit_text = matches >= max(1, len(expected_keywords) // 4)
        
        hit_source = True
        if expected_source_docs:
            hit_source = any(
                any(es.lower() in rs.lower() for rs in retrieved_source_docs)
                for es in expected_source_docs
            )
            
        hit = hit_text and hit_source
        if hit:
            correct += 1
            
        reason = []
        if not hit_text: reason.append("wrong answer text")
        if expected_source_docs and not hit_source: reason.append("wrong source retrieved")
        if llm_result.get("confidence") == "Low": reason.append("low confidence")
        reason_str = ", ".join(reason) if not hit else ""

        results.append({
            "id":           qa.get("id", ""),
            "question":     question,
            "expected":     qa["answer"],
            "got":          answer_text[:300],
            "confidence":   llm_result.get("confidence", "Low"),
            "passed":       hit,
            "reason":       reason_str,
            "latency_ms":   elapsed_ms,
            "category":     qa.get("category", ""),
        })
        logger.info(f"Benchmark {qa.get('id')}: {'PASS' if hit else 'FAIL'} ({elapsed_ms} ms) - {reason_str}")

    accuracy = round(correct / total * 100, 1) if total > 0 else 0.0
    avg_ms   = round(total_ms / total) if total > 0 else 0

    return {
        "total":           total,
        "correct":         correct,
        "accuracy_pct":    accuracy,
        "avg_latency_ms":  avg_ms,
        "model_used":      get_llm().model or "smart-fallback",
        "results":         results,
    }


# ── Feedback Endpoint ─────────────────────────────────────────────────────────

@app.post("/feedback")
async def log_feedback(request: FeedbackRequest):
    """Log thumbs-up (+1) or thumbs-down (-1) feedback on an answer."""
    entry = {
        "ts":       time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "question": request.question,
        "answer":   request.answer[:300],
        "rating":   request.rating,
        "comment":  request.comment or "",
    }
    try:
        _FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Feedback logged: rating={request.rating}")
    except Exception as e:
        logger.error(f"Failed to write feedback: {e}")
    return {"status": "logged"}


# ── Debug: raw vector search (no LLM) ────────────────────────────────────────

@app.get("/debug/search")
async def debug_search(
    q: str = Query(..., description="Raw search query — no LLM, pure vector similarity"),
    n: int = Query(default=5, le=20),
):
    """Raw vector similarity search without LLM — useful for tuning chunk size / top-k."""
    try:
        embedder = TextEmbedder()
        store    = VectorStore()
        emb      = embedder.embed_query(q)
        results  = store.query(emb, n_results=n)

        hits = []
        if results and results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                hits.append({
                    "rank":     i + 1,
                    "doc_id":   results["metadatas"][0][i].get("doc_id", "?"),
                    "distance": round(results["distances"][0][i], 4),
                    "score":    round(1 - results["distances"][0][i], 4),
                    "excerpt":  results["documents"][0][i][:300],
                    "metadata": results["metadatas"][0][i],
                })
        return {"query": q, "hits": hits, "total_in_db": store.count()}
    except Exception as e:
        logger.error(f"Debug search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── LLM status endpoint ───────────────────────────────────────────────────────

@app.get("/llm/status")
async def llm_status():
    """Check whether NVIDIA NIM and Ollama are available for hybrid routing."""
    from src.pipeline.llm import get_nvidia_llm, get_ollama_llm

    nvidia = get_nvidia_llm()
    ollama = get_ollama_llm()
    primary = get_llm()

    return {
        "nvidia_available": nvidia.available,
        "ollama_available": ollama.available,
        "nvidia_model":     nvidia.model or "none",
        "ollama_model":     ollama.model or "none",
        "model":            primary.model or "none",
        "base_url":         getattr(primary, "base_url", ""),
        "mode":             "hybrid" if nvidia.available and ollama.available else (
            "nvidia" if nvidia.available else ("ollama" if ollama.available else "smart-context-fallback")
        ),
        "router_modes":     ["hybrid", "local", "cloud"],
    }
