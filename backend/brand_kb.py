import os
import re
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from backend.models import BrandDocument, CampaignBrief
from backend.config import config
from backend.vector_store import VectorStore, SearchResults


class BrandKnowledgeBase:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.documents: Dict[str, BrandDocument] = {}

    def add_document(self, filename: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> BrandDocument:
        cleaned = self._clean_text(content)
        chunks = self._chunk_text(cleaned)
        doc = BrandDocument(
            filename=filename,
            content=cleaned,
            metadata=metadata or {},
            chunk_count=len(chunks),
        )
        self.documents[filename] = doc

        chunk_texts = [c["text"] for c in chunks]
        chunk_metas = [
            {
                "filename": filename,
                "chunk_index": c["index"],
                "char_start": c["start"],
                "char_end": c["end"],
                "source": filename,
                "document_type": (metadata or {}).get("document_type", "brand"),
                **{k: v for k, v in (metadata or {}).items() if k not in ("document_type",)},
            }
            for c in chunks
        ]
        chunk_ids = [f"{filename}::chunk::{c['index']}" for c in chunks]

        self.vector_store.add_brand_chunks(
            documents=chunk_texts,
            metadatas=chunk_metas,
            ids=chunk_ids,
        )
        return doc

    def add_documents_batch(self, docs: List[BrandDocument]):
        for doc in docs:
            self.add_document(doc.filename, doc.content, doc.metadata)

    def retrieve(self, query: str, n_results: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        results = self.vector_store.search_brand(query=query, n_results=n_results, where=filters)
        return self._format_results(results)

    def retrieve_for_brief(self, brief: CampaignBrief, n_results: int = 5) -> List[Dict[str, Any]]:
        queries = [
            brief.product_service,
            brief.target_audience,
            brief.tone,
            brief.cta,
            "brand guidelines",
            "approved claims",
            "product description",
            "tone of voice",
            "customer personas",
        ]
        seen = set()
        all_results = []
        for q in queries:
            if not q or q in seen:
                continue
            seen.add(q)
            res = self.retrieve(q, n_results=2)
            all_results.extend(res)
        unique = {r["id"]: r for r in all_results}
        return list(unique.values())[:n_results * 2]

    def get_context(self, query: str, n_results: int = 5) -> str:
        results = self.retrieve(query, n_results=n_results)
        if not results:
            return "No relevant brand information found in knowledge base."
        parts = []
        for r in results:
            parts.append(f"[{r['source']}]\n{r['text']}")
        return "\n\n".join(parts)

    def list_documents(self) -> List[Dict[str, Any]]:
        return [
            {
                "filename": d.filename,
                "chunk_count": d.chunk_count,
                "uploaded_at": d.uploaded_at.isoformat(),
                "metadata": d.metadata,
            }
            for d in self.documents.values()
        ]

    def clear(self):
        self.documents.clear()
        self.vector_store.clear_brand_data()

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"index": idx, "text": chunk_text, "start": start, "end": end})
                idx += 1
            start = max(end - overlap, start + 1)
        return chunks

    def _format_results(self, results: SearchResults) -> List[Dict[str, Any]]:
        formatted = []
        for doc, meta, dist in zip(results.documents, results.metadata, results.distances):
            formatted.append({
                "id": meta.get("id", ""),
                "text": doc,
                "source": meta.get("source", meta.get("filename", "unknown")),
                "score": float(dist),
                "metadata": meta,
            })
        return formatted
