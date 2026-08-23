import logging
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional, Optional

from backend.brand_kb import BrandKnowledgeBase
from backend.config import config
from backend.models import BrandDocument

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

_brand_kb: Optional[BrandKnowledgeBase] = None


def init_brand_kb(brand_kb: BrandKnowledgeBase):
    global _brand_kb
    _brand_kb = brand_kb


@router.post("/upload")
async def upload_document(files: List[UploadFile] = File(...), document_type: str = Form("brand")):
    if not _brand_kb:
        raise HTTPException(status_code=500, detail="Brand KB not initialized")
    added = 0
    for file in files:
        filename = file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower()
        allowed = [e.lower() for e in config.ALLOWED_EXTENSIONS]
        if ext not in allowed:
            continue
        content = await file.read()
        if len(content) > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            continue
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            text = str(content)
        _brand_kb.add_document(filename=filename, content=text, metadata={"document_type": document_type})
        added += 1
    return {"uploaded": added}


@router.get("/")
async def list_documents():
    if not _brand_kb:
        raise HTTPException(status_code=500, detail="Brand KB not initialized")
    return _brand_kb.list_documents()


@router.delete("/{filename}")
async def delete_document(filename: str):
    if not _brand_kb:
        raise HTTPException(status_code=500, detail="Brand KB not initialized")
    _brand_kb.documents.pop(filename, None)
    _brand_kb.vector_store.clear_brand_data()
    for doc in _brand_kb.documents.values():
        _brand_kb.add_document(doc.filename, doc.content, doc.metadata)
    return {"deleted": filename}


@router.post("/ingest-folder")
async def ingest_folder(path: str = Form("docs/brand")):
    if not _brand_kb:
        raise HTTPException(status_code=500, detail="Brand KB not initialized")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Invalid folder path")
    added = 0
    for fname in os.listdir(path):
        fpath = os.path.join(path, fname)
        if os.path.isfile(fpath):
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                _brand_kb.add_document(filename=fname, content=content, metadata={"document_type": "brand", "path": fpath})
                added += 1
            except Exception as e:
                logger.warning(f"Failed to ingest {fname}: {e}")
    return {"ingested": added}
