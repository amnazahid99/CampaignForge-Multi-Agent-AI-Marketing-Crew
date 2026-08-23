import faiss
import numpy as np
import pickle
import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from backend.models import Course, CourseChunk
from sentence_transformers import SentenceTransformer


@dataclass
class SearchResults:
    """Container for search results with metadata"""
    documents: List[str]
    metadata: List[Dict[str, Any]]
    distances: List[float]
    error: Optional[str] = None

    @classmethod
    def empty(cls, error_msg: str) -> 'SearchResults':
        """Create empty results with error message"""
        return cls(documents=[], metadata=[], distances=[], error=error_msg)

    def is_empty(self) -> bool:
        """Check if results are empty"""
        return len(self.documents) == 0


class FAISSCollection:
    """
    A FAISS-backed collection that mimics ChromaDB's collection interface.
    Stores embeddings in a FAISS index and documents/metadata in pickle files.
    """

    def __init__(self, name: str, base_path: str, embedding_model: SentenceTransformer):
        self.name = name
        self.base_path = base_path
        self.model = embedding_model

        # File paths for persistence
        self.index_path = os.path.join(base_path, f"{name}.index")
        self.data_path  = os.path.join(base_path, f"{name}.pkl")

        # In-memory storage
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        self.index: Optional[faiss.Index] = None

        # Load existing data if present
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self):
        """Load index and metadata from disk if they exist."""
        if os.path.exists(self.index_path) and os.path.exists(self.data_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.data_path, "rb") as f:
                    data = pickle.load(f)
                self.documents = data["documents"]
                self.metadatas = data["metadatas"]
                self.ids       = data["ids"]
            except Exception as e:
                print(f"Warning: could not load collection '{self.name}': {e}")
                self._reset()

    def _save(self):
        """Persist index and metadata to disk."""
        os.makedirs(self.base_path, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)
        with open(self.data_path, "wb") as f:
            pickle.dump({
                "documents": self.documents,
                "metadatas": self.metadatas,
                "ids":       self.ids,
            }, f)

    def _reset(self):
        """Clear all in-memory data."""
        self.documents = []
        self.metadatas = []
        self.ids       = []
        self.index     = None

    # ------------------------------------------------------------------
    # Public API (mirrors ChromaDB collection methods used in the project)
    # ------------------------------------------------------------------

    def add(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Embed and add documents to the collection."""
        # Skip duplicate IDs
        new_docs, new_metas, new_ids = [], [], []
        existing_ids = set(self.ids)
        for doc, meta, id_ in zip(documents, metadatas, ids):
            if id_ not in existing_ids:
                new_docs.append(doc)
                new_metas.append(meta)
                new_ids.append(id_)

        if not new_docs:
            return

        # Compute embeddings
        embeddings = self.model.encode(new_docs, convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(embeddings)

        # Build or expand the FAISS index
        dim = embeddings.shape[1]
        if self.index is None:
            self.index = faiss.IndexFlatIP(dim)   # Inner-product == cosine after L2 norm

        self.index.add(embeddings)
        self.documents.extend(new_docs)
        self.metadatas.extend(new_metas)
        self.ids.extend(new_ids)
        self._save()

    def query(self,
              query_texts: List[str],
              n_results: int = 5,
              where: Optional[Dict] = None) -> Dict:
        """
        Search the collection.  Returns a dict that mirrors ChromaDB's format:
        {'documents': [[...]], 'metadatas': [[...]], 'distances': [[...]]}
        """
        if self.index is None or len(self.documents) == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        # Embed the query
        q_emb = self.model.encode(query_texts, convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(q_emb)

        # Retrieve more candidates so we have room to filter
        k = min(len(self.documents), max(n_results * 10, 50))
        distances, indices = self.index.search(q_emb, k)

        docs, metas, dists = [], [], []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = self.metadatas[idx]
            # Apply optional metadata filter
            if where and not self._matches_filter(meta, where):
                continue
            docs.append(self.documents[idx])
            metas.append(meta)
            dists.append(float(dist))
            if len(docs) >= n_results:
                break

        return {"documents": [docs], "metadatas": [metas], "distances": [dists]}

    def get(self, ids: Optional[List[str]] = None) -> Dict:
        """Return documents/metadata, optionally filtered by ID list."""
        if ids is None:
            return {"ids": self.ids, "documents": self.documents, "metadatas": self.metadatas}

        result_ids, result_docs, result_metas = [], [], []
        id_set = set(ids)
        for id_, doc, meta in zip(self.ids, self.documents, self.metadatas):
            if id_ in id_set:
                result_ids.append(id_)
                result_docs.append(doc)
                result_metas.append(meta)

        return {"ids": result_ids, "documents": result_docs, "metadatas": result_metas}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _matches_filter(self, meta: Dict, where: Dict) -> bool:
        """
        Evaluate a ChromaDB-style 'where' filter dict against a metadata dict.
        Supports: {"field": value}, {"$and": [...]}, {"$or": [...]}
        """
        if "$and" in where:
            return all(self._matches_filter(meta, clause) for clause in where["$and"])
        if "$or" in where:
            return any(self._matches_filter(meta, clause) for clause in where["$or"])

        for key, value in where.items():
            if meta.get(key) != value:
                return False
        return True


class VectorStore:
    """Vector storage using FAISS for course content and metadata.
    Drop-in replacement for the original ChromaDB-based VectorStore.
    """

    def __init__(self, faiss_path: str, embedding_model: str, max_results: int = 5):
        self.max_results = max_results
        self.faiss_path  = faiss_path
        os.makedirs(faiss_path, exist_ok=True)

        # Shared sentence-transformer model
        self.model = SentenceTransformer(embedding_model)

        # Two collections: catalog (titles) and content (chunks)
        self.course_catalog = FAISSCollection("course_catalog", faiss_path, self.model)
        self.course_content = FAISSCollection("course_content", faiss_path, self.model)
        self.brand_content = FAISSCollection("brand_content", faiss_path, self.model)

    # ------------------------------------------------------------------
    # Public API — identical signatures to the ChromaDB version
    # ------------------------------------------------------------------

    def search(self,
               query: str,
               course_name: Optional[str] = None,
               lesson_number: Optional[int] = None,
               limit: Optional[int] = None) -> SearchResults:
        """
        Main search interface – resolves course name then searches content.
        """
        course_title = None
        if course_name:
            course_title = self._resolve_course_name(course_name)
            if not course_title:
                return SearchResults.empty(f"No course found matching '{course_name}'")

        filter_dict   = self._build_filter(course_title, lesson_number)
        search_limit  = limit if limit is not None else self.max_results

        try:
            results = self.course_content.query(
                query_texts=[query],
                n_results=search_limit,
                where=filter_dict
            )
            return self._parse_results(results)
        except Exception as e:
            return SearchResults.empty(f"Search error: {str(e)}")

    def add_course_metadata(self, course: Course):
        """Add course information to the catalog for semantic search."""
        lessons_metadata = [
            {
                "lesson_number": lesson.lesson_number,
                "lesson_title":  lesson.title,
                "lesson_link":   lesson.lesson_link,
            }
            for lesson in course.lessons
        ]

        self.course_catalog.add(
            documents=[course.title],
            metadatas=[{
                "title":       course.title,
                "instructor":  course.instructor,
                "course_link": course.course_link,
                "lessons_json": json.dumps(lessons_metadata),
                "lesson_count": len(course.lessons),
            }],
            ids=[course.title]
        )

    def add_course_content(self, chunks: List[CourseChunk]):
        """Add course content chunks to the vector store."""
        if not chunks:
            return

        documents = [chunk.content for chunk in chunks]
        metadatas = [{
            "course_title":  chunk.course_title,
            "lesson_number": chunk.lesson_number,
            "chunk_index":   chunk.chunk_index,
        } for chunk in chunks]
        ids = [f"{chunk.course_title.replace(' ', '_')}_{chunk.chunk_index}" for chunk in chunks]

        self.course_content.add(documents=documents, metadatas=metadatas, ids=ids)

    def add_brand_chunks(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Add brand document chunks to the brand collection."""
        self.brand_content.add(documents=documents, metadatas=metadatas, ids=ids)

    def search_brand(self, query: str, n_results: int = 5, where: Optional[Dict] = None) -> SearchResults:
        """Search brand knowledge base."""
        raw = self.brand_content.query(query_texts=[query], n_results=n_results, where=where)
        return self._parse_results(raw)

    def clear_brand_data(self):
        """Clear brand data."""
        self.brand_content = FAISSCollection("brand_content", self.faiss_path, self.model)

    def clear_all_data(self):
        """Clear all data from both collections and remove persisted files."""
        import shutil
        try:
            if os.path.exists(self.faiss_path):
                shutil.rmtree(self.faiss_path)
            os.makedirs(self.faiss_path, exist_ok=True)
            self.course_catalog = FAISSCollection("course_catalog", self.faiss_path, self.model)
            self.course_content = FAISSCollection("course_content", self.faiss_path, self.model)
            self.brand_content = FAISSCollection("brand_content", self.faiss_path, self.model)
        except Exception as e:
            print(f"Error clearing data: {e}")

    def get_existing_course_titles(self) -> List[str]:
        """Return all existing course title IDs."""
        try:
            results = self.course_catalog.get()
            return results.get("ids", [])
        except Exception as e:
            print(f"Error getting existing course titles: {e}")
            return []

    def get_course_count(self) -> int:
        """Return the total number of courses."""
        try:
            results = self.course_catalog.get()
            return len(results.get("ids", []))
        except Exception as e:
            print(f"Error getting course count: {e}")
            return 0

    def get_all_courses_metadata(self) -> List[Dict[str, Any]]:
        """Return metadata for all courses, with lessons_json parsed."""
        try:
            results = self.course_catalog.get()
            parsed = []
            for meta in results.get("metadatas", []):
                course_meta = meta.copy()
                if "lessons_json" in course_meta:
                    course_meta["lessons"] = json.loads(course_meta["lessons_json"])
                    del course_meta["lessons_json"]
                parsed.append(course_meta)
            return parsed
        except Exception as e:
            print(f"Error getting courses metadata: {e}")
            return []

    def get_course_link(self, course_title: str) -> Optional[str]:
        """Get the course link for a given course title."""
        try:
            results = self.course_catalog.get(ids=[course_title])
            metas = results.get("metadatas", [])
            if metas:
                return metas[0].get("course_link")
        except Exception as e:
            print(f"Error getting course link: {e}")
        return None

    def get_lesson_link(self, course_title: str, lesson_number: int) -> Optional[str]:
        """Get the lesson link for a course title + lesson number."""
        try:
            results = self.course_catalog.get(ids=[course_title])
            metas = results.get("metadatas", [])
            if metas and "lessons_json" in metas[0]:
                lessons = json.loads(metas[0]["lessons_json"])
                for lesson in lessons:
                    if lesson.get("lesson_number") == lesson_number:
                        return lesson.get("lesson_link")
        except Exception as e:
            print(f"Error getting lesson link: {e}")
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_course_name(self, course_name: str) -> Optional[str]:
        """Use vector search to find the best-matching course title."""
        try:
            results = self.course_catalog.query(query_texts=[course_name], n_results=1)
            metas = results["metadatas"][0]
            if metas:
                return metas[0]["title"]
        except Exception as e:
            print(f"Error resolving course name: {e}")
        return None

    def _build_filter(self, course_title: Optional[str], lesson_number: Optional[int]) -> Optional[Dict]:
        """Build a filter dict from optional course title and lesson number."""
        if not course_title and lesson_number is None:
            return None
        if course_title and lesson_number is not None:
            return {"$and": [
                {"course_title":  course_title},
                {"lesson_number": lesson_number},
            ]}
        if course_title:
            return {"course_title": course_title}
        return {"lesson_number": lesson_number}

    @staticmethod
    def _parse_results(chroma_like: Dict) -> SearchResults:
        """Convert the chroma-style dict returned by FAISSCollection.query into SearchResults."""
        return SearchResults(
            documents=chroma_like["documents"][0] if chroma_like["documents"] else [],
            metadata =chroma_like["metadatas"][0]  if chroma_like["metadatas"]  else [],
            distances=chroma_like["distances"][0]  if chroma_like["distances"]  else [],
        )