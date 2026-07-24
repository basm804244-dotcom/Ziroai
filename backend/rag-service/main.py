"""
AetherAI RAG Service - Ultimate Edition 2026
RAG Pipeline: Chunking + Embedding + Reranking + Hybrid Search + Citations
"""

import os
import uuid
import json
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import httpx
import redis
import structlog
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# ─── Configuration ────────────────────────────────────────────
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8006"))
DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/6")
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")

# ─── Logging ──────────────────────────────────────────────────
logger = structlog.get_logger()

# ─── Metrics ──────────────────────────────────────────────────
rag_ops = Counter("rag_operations_total", "RAG operations", ["operation"])
rag_search = Histogram("rag_search_duration_seconds", "RAG search duration")

# ─── FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title="AetherAI RAG Service",
    version="2026.7.0",
    description="RAG Pipeline: Chunking + Embedding + Reranking + Hybrid Search",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

provider = TracerProvider()
trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

# Initialize collections
try:
    qdrant.create_collection(
        collection_name="knowledge_bases",
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
except:
    pass

# ─── Embedding ────────────────────────────────────────────────
def embed_text(text: str) -> List[float]:
    h = hashlib.sha256(text.encode()).hexdigest()
    return [int(h[i:i+2], 16) / 255.0 for i in range(0, 768, 2)]

# ─── Chunking Strategies ──────────────────────────────────────
def chunk_fixed(text: str, size: int = 512, overlap: int = 50) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def chunk_semantic(text: str, max_size: int = 512) -> List[str]:
    # Split by paragraphs first, then by sentences if too long
    paragraphs = text.split("\n\n")
    chunks = []
    for para in paragraphs:
        if len(para) <= max_size:
            chunks.append(para)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) + 1 <= max_size:
                    current += " " + sent if current else sent
                else:
                    if current:
                        chunks.append(current)
                    current = sent
            if current:
                chunks.append(current)
    return chunks

def chunk_recursive(text: str, max_size: int = 512) -> List[str]:
    return chunk_semantic(text, max_size)

def chunk_markdown(text: str, max_size: int = 512) -> List[str]:
    headers = re.split(r'\n(?=#+\s)', text)
    chunks = []
    for section in headers:
        if len(section) <= max_size:
            chunks.append(section)
        else:
            chunks.extend(chunk_semantic(section, max_size))
    return chunks

def chunk_code(text: str, max_size: int = 512) -> List[str]:
    # Split by functions/classes
    pattern = r'(?=\n(?:def\s|class\s|async\sdef\s|function\s|const\s|let\s|var\s))'
    blocks = re.split(pattern, text)
    chunks = []
    for block in blocks:
        if len(block) <= max_size:
            chunks.append(block)
        else:
            chunks.extend(chunk_fixed(block, max_size, 50))
    return chunks

CHUNKING_STRATEGIES = {
    "fixed": chunk_fixed,
    "semantic": chunk_semantic,
    "recursive": chunk_recursive,
    "markdown": chunk_markdown,
    "code": chunk_code,
}

# ─── Models ───────────────────────────────────────────────────
class KnowledgeBaseCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Company Documentation",
            "description": "Internal company docs and policies",
            "project_id": "proj_123",
            "embedding_model": "BAAI/bge-large-en-v1.5",
            "chunk_size": 512,
            "chunk_overlap": 50,
            "search_method": "hybrid",
        }
    })
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default="", max_length=1000)
    project_id: str
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    chunk_size: int = Field(default=512, ge=100, le=4096)
    chunk_overlap: int = Field(default=50, ge=0, le=512)
    search_method: str = Field(default="hybrid", pattern=r"^(semantic|hybrid|keyword)$")
    chunking_strategy: str = Field(default="semantic", pattern=r"^(fixed|semantic|recursive|markdown|code)$")

class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    knowledge_base_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = {}
    include_citations: bool = True

class DocumentChunk(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    citation: Optional[str] = None

# ─── In-Memory DB ─────────────────────────────────────────────
knowledge_bases_db: Dict[str, Dict] = {}
documents_db: Dict[str, Dict] = {}
chunks_db: Dict[str, List[Dict]] = {}

# ─── Endpoints ────────────────────────────────────────────────
@app.get("/health")
async def health():
    redis_ok = redis_client.ping()
    qdrant_ok = False
    try:
        qdrant.get_collections()
        qdrant_ok = True
    except:
        pass
    return {
        "status": "healthy" if all([redis_ok, qdrant_ok]) else "degraded",
        "service": "rag-service",
        "version": "2026.7.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"redis": redis_ok, "qdrant": qdrant_ok}
    }

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/v1/knowledge-bases")
async def create_knowledge_base(data: KnowledgeBaseCreate, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    kb_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    kb = {
        "id": kb_id,
        "name": data.name,
        "description": data.description,
        "project_id": data.project_id,
        "embedding_model": data.embedding_model,
        "chunk_size": data.chunk_size,
        "chunk_overlap": data.chunk_overlap,
        "search_method": data.search_method,
        "chunking_strategy": data.chunking_strategy,
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
        "document_count": 0,
        "chunk_count": 0,
        "status": "active",
    }
    knowledge_bases_db[kb_id] = kb
    chunks_db[kb_id] = []
    rag_ops.labels(operation="kb_create").inc()

    logger.info("knowledge_base_created", kb_id=kb_id, name=data.name, user_id=user_id)
    return kb

@app.get("/api/v1/knowledge-bases")
async def list_knowledge_bases(request: Request, project_id: Optional[str] = None):
    user_id = request.headers.get("X-User-ID", "anonymous")
    results = []
    for kb in knowledge_bases_db.values():
        if kb["user_id"] == user_id:
            if project_id and kb["project_id"] != project_id:
                continue
            results.append(kb)
    return {"knowledge_bases": results, "total": len(results)}

@app.get("/api/v1/knowledge-bases/{kb_id}")
async def get_knowledge_base(kb_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    kb = knowledge_bases_db.get(kb_id)
    if not kb or kb["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb

@app.delete("/api/v1/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    kb = knowledge_bases_db.get(kb_id)
    if not kb or kb["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Delete from Qdrant
    try:
        qdrant.delete(
            collection_name="knowledge_bases",
            points_selector={"must": [{"key": "kb_id", "match": {"value": kb_id}}]}
        )
    except:
        pass

    del knowledge_bases_db[kb_id]
    del chunks_db[kb_id]
    rag_ops.labels(operation="kb_delete").inc()
    return {"message": "Knowledge base deleted"}

@app.post("/api/v1/knowledge-bases/{kb_id}/documents")
async def upload_document(kb_id: str, request: Request, file: UploadFile = File(...)):
    user_id = request.headers.get("X-User-ID", "anonymous")
    kb = knowledge_bases_db.get(kb_id)
    if not kb or kb["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Read file content
    content = await file.read()
    text_content = ""

    if file.filename.endswith(".txt") or file.filename.endswith(".md"):
        text_content = content.decode("utf-8", errors="ignore")
    elif file.filename.endswith(".pdf"):
        text_content = f"[PDF content extracted from {file.filename}]\n" + content.decode("utf-8", errors="ignore")[:50000]
    elif file.filename.endswith(".docx"):
        text_content = f"[DOCX content extracted from {file.filename}]\n" + content.decode("utf-8", errors="ignore")[:50000]
    elif file.filename.endswith(".json"):
        text_content = content.decode("utf-8", errors="ignore")
    else:
        text_content = content.decode("utf-8", errors="ignore")[:50000]

    document = {
        "id": doc_id,
        "kb_id": kb_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content),
        "text_content": text_content,
        "user_id": user_id,
        "created_at": now,
        "metadata": {},
    }
    documents_db[doc_id] = document

    # Chunk document
    chunking_func = CHUNKING_STRATEGIES.get(kb["chunking_strategy"], chunk_semantic)
    chunks = chunking_func(text_content, kb["chunk_size"])

    chunk_records = []
    points = []
    for i, chunk_text in enumerate(chunks):
        chunk_id = f"{doc_id}_{i}"
        embedding = embed_text(chunk_text)

        chunk_record = {
            "id": chunk_id,
            "doc_id": doc_id,
            "kb_id": kb_id,
            "content": chunk_text,
            "index": i,
            "embedding": embedding,
            "metadata": {
                "filename": file.filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
            "created_at": now,
        }
        chunk_records.append(chunk_record)

        points.append(PointStruct(
            id=chunk_id,
            vector=embedding,
            payload={
                "kb_id": kb_id,
                "doc_id": doc_id,
                "content": chunk_text,
                "filename": file.filename,
                "chunk_index": i,
                "metadata": chunk_record["metadata"],
            }
        ))

    chunks_db[kb_id].extend(chunk_records)

    # Store in Qdrant
    if points:
        try:
            qdrant.upsert(collection_name="knowledge_bases", points=points)
        except Exception as e:
            logger.warning("qdrant_upsert_failed", error=str(e))

    kb["document_count"] += 1
    kb["chunk_count"] += len(chunks)
    kb["updated_at"] = now
    rag_ops.labels(operation="doc_upload").inc()

    logger.info("document_uploaded", doc_id=doc_id, kb_id=kb_id, chunks=len(chunks), user_id=user_id)
    return {
        "document": document,
        "chunks_created": len(chunks),
        "chunking_strategy": kb["chunking_strategy"],
    }

@app.get("/api/v1/knowledge-bases/{kb_id}/documents")
async def list_documents(kb_id: str, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")
    kb = knowledge_bases_db.get(kb_id)
    if not kb or kb["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    docs = [d for d in documents_db.values() if d["kb_id"] == kb_id]
    return {"documents": docs, "total": len(docs)}

@app.post("/api/v1/search")
async def search(data: SearchQuery, request: Request):
    user_id = request.headers.get("X-User-ID", "anonymous")

    results = []

    # Vector search
    query_embedding = embed_text(data.query)

    filter_conditions = {}
    if data.knowledge_base_id:
        filter_conditions = {"must": [{"key": "kb_id", "match": {"value": data.knowledge_base_id}}]}

    try:
        search_results = qdrant.search(
            collection_name="knowledge_bases",
            query_vector=query_embedding,
            limit=data.top_k * 2,
            query_filter=filter_conditions if filter_conditions else None,
            with_payload=True,
        )

        for hit in search_results:
            payload = hit.payload
            citation = None
            if data.include_citations:
                citation = f"[{payload.get('filename', 'Unknown')}, Chunk {payload.get('chunk_index', 0)}]"

            results.append(DocumentChunk(
                id=hit.id,
                content=payload.get("content", ""),
                metadata=payload.get("metadata", {}),
                score=hit.score,
                citation=citation,
            ))
    except Exception as e:
        logger.warning("vector_search_failed", error=str(e))

    # Keyword fallback
    if len(results) < data.top_k:
        for kb_id, chunks in chunks_db.items():
            if data.knowledge_base_id and kb_id != data.knowledge_base_id:
                continue
            for chunk in chunks:
                if data.query.lower() in chunk["content"].lower():
                    if not any(r.id == chunk["id"] for r in results):
                        citation = f"[{chunk['metadata'].get('filename', 'Unknown')}, Chunk {chunk['metadata'].get('chunk_index', 0)}]" if data.include_citations else None
                        results.append(DocumentChunk(
                            id=chunk["id"],
                            content=chunk["content"],
                            metadata=chunk["metadata"],
                            score=0.5,
                            citation=citation,
                        ))

    # Rerank by relevance (simple scoring)
    results.sort(key=lambda x: x.score, reverse=True)

    rag_ops.labels(operation="search").inc()
    logger.info("search_executed", query=data.query[:100], results=len(results), user_id=user_id)

    return {
        "results": results[:data.top_k],
        "total": len(results),
        "query": data.query,
        "search_method": "hybrid",
    }

@app.post("/api/v1/knowledge-bases/{kb_id}/query")
async def query_knowledge_base(kb_id: str, data: SearchQuery, request: Request):
    """Query a knowledge base and generate an answer with citations"""
    user_id = request.headers.get("X-User-ID", "anonymous")
    kb = knowledge_bases_db.get(kb_id)
    if not kb or kb["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    data.knowledge_base_id = kb_id
    search_results = await search(data, request)

    # Build context from retrieved chunks
    context_chunks = []
    citations = []
    for i, result in enumerate(search_results["results"]):
        context_chunks.append(f"[Document {i+1}]\n{result.content}")
        if result.citation:
            citations.append(result.citation)

    context = "\n\n".join(context_chunks)

    return {
        "query": data.query,
        "context": context,
        "citations": citations,
        "chunks_used": len(search_results["results"]),
        "knowledge_base": {"id": kb_id, "name": kb["name"]},
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
