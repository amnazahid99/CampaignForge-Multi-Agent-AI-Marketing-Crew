# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the app (from project root)
./run.sh
# Or manually:
cd backend && uv run fastapi dev app.py

# App available at http://localhost:8000, API docs at http://localhost:8000/docs
```

There are no tests or linting configured in this project.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for querying course materials. Python 3.11+ backend with a vanilla HTML/CSS/JS frontend.

### Backend (`backend/`)

The system uses Ollama (local LLM) with tool use for search — the AI decides when to search course content via a registered tool.

**Request flow:** `app.py` (FastAPI) → `RAGSystem` (orchestrator) → `AIGenerator` (Ollama API with tool use) → `CourseSearchTool` (executed by LLM when needed) → `VectorStore` (ChromaDB query) → response back through the chain.

Key components:
- **`rag_system.py`** — `RAGSystem` orchestrator that wires everything together. Owns document ingestion and query processing.
- **`ai_generator.py`** — `AIGenerator` wraps the Ollama API. Handles the tool-use loop: sends tools to the LLM, executes tool calls via `ToolManager`, sends results back for final response.
- **`search_tools.py`** — `Tool` ABC and `ToolManager` registry. `CourseSearchTool` is the only tool; it delegates to `VectorStore.search()` which handles course name resolution and content filtering.
- **`vector_store.py`** — ChromaDB with two collections: `course_catalog` (course titles for fuzzy matching) and `course_content` (chunked lesson text). Uses `sentence-transformers/all-MiniLM-L6-v2` for embeddings.
- **`document_processor.py`** — Parses course documents with a specific format (Course Title/Link/Instructor header, then `Lesson N:` markers). Chunks text by sentences with configurable overlap.
- **`session_manager.py`** — In-memory conversation history per session (no persistence).
- **`config.py`** — Dataclass-based config loading from `.env`. Key settings: chunk size (800), overlap (100), max results (5), max history (2).
- **`models.py`** — Pydantic models: `Course`, `Lesson`, `CourseChunk`.

### Frontend (`frontend/`)

Static files served by FastAPI's `StaticFiles` mount at `/`. Simple chat UI that calls `POST /api/query` and `GET /api/courses`.

### Data (`docs/`)

Course documents in `.txt` format with expected header format:
```
Course Title: ...
Course Link: ...
Course Instructor: ...

Lesson 0: Title
Lesson Link: ...
Content...
```

### API Endpoints

- `POST /api/query` — Takes `{query, session_id?}`, returns `{answer, sources[], session_id}`
- `GET /api/courses` — Returns `{total_courses, course_titles[]}`

Documents in `docs/` are auto-loaded on startup.

## Environment

Requires Ollama running locally (see `.env.example` for `OLLAMA_HOST` and `OLLAMA_MODEL` settings). ChromaDB persists to `backend/chroma_db/`.
