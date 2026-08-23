import logging
import warnings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from pathlib import Path

from backend.config import config
from backend.rag_system import RAGSystem
from backend.vector_store import VectorStore
from backend.brand_kb import BrandKnowledgeBase
from backend.campaign_store import CampaignStore
from backend.workflow import CampaignWorkflow
from backend.routes.campaigns import router as campaigns_router, init_workflow
from backend.routes.documents import router as documents_router, init_brand_kb
from backend.routes.export import router as export_router, init_export

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title="CampaignForge", description="Multi-Agent AI Marketing Campaign Generator")

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

rag_system = RAGSystem(config)
vector_store = rag_system.vector_store
brand_kb = BrandKnowledgeBase(vector_store)
store = CampaignStore(config.CAMPAIGN_STORE_PATH)
workflow = CampaignWorkflow(brand_kb, store)

init_workflow(workflow, store)
init_brand_kb(brand_kb)
init_export(store, workflow.publisher_agent)

app.include_router(campaigns_router)
app.include_router(documents_router)
app.include_router(export_router)


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: list
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: list


@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    try:
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()
        answer, sources = rag_system.query(request.query, session_id)
        return QueryResponse(answer=answer, sources=sources, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    try:
        analytics = rag_system.get_course_analytics()
        return CourseStats(total_courses=analytics["total_courses"], course_titles=analytics["course_titles"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


@app.on_event("startup")
async def startup_event():
    docs_path = Path(__file__).resolve().parent.parent / "docs" / "brand"
    if docs_path.exists():
        logger.info("Loading brand documents...")
        try:
            for f in docs_path.iterdir():
                if f.is_file():
                    try:
                        text = f.read_text(encoding="utf-8", errors="ignore")
                        brand_kb.add_document(f.name, text, metadata={"document_type": "brand", "path": str(f)})
                        logger.info(f"Loaded brand doc: {f.name}")
                    except Exception as e:
                        logger.warning(f"Failed to load {f.name}: {e}")
        except Exception as e:
            logger.warning(f"Brand doc load error: {e}")

    docs_path_legacy = Path(__file__).resolve().parent.parent / "docs"
    if docs_path_legacy.exists():
        try:
            courses, chunks = rag_system.add_course_folder(docs_path_legacy, clear_existing=False)
            logger.info(f"Loaded {courses} legacy courses with {chunks} chunks")
        except Exception as e:
            logger.warning(f"Legacy doc load error: {e}")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "campaignforge"}


frontend_path = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")
