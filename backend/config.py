import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from typing import Optional

load_dotenv()


@dataclass
class Config:
    # Ollama settings
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    # Embedding settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # Document processing
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    MAX_RESULTS: int = int(os.getenv("MAX_RESULTS", "5"))

    # Vector store
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./faiss_db")

    # Session / campaign
    MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "10"))
    MAX_CAMPAIGN_REVISIONS: int = int(os.getenv("MAX_CAMPAIGN_REVISIONS", "3"))
    CAMPAIGN_STORE_PATH: str = os.getenv("CAMPAIGN_STORE_PATH", "./campaigns")

    # File uploads
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS: list = field(default_factory=lambda: [".pdf", ".docx", ".txt", ".md", ".csv"])

    # Web search (optional)
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
    SERPER_API_KEY: Optional[str] = os.getenv("SERPER_API_KEY")
    WEB_SEARCH_PROVIDER: str = os.getenv("WEB_SEARCH_PROVIDER", "demo")
    WEB_SEARCH_TIMEOUT: int = int(os.getenv("WEB_SEARCH_TIMEOUT", "30"))

    # Observability
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Security
    API_KEY_HEADER: str = os.getenv("API_KEY_HEADER", "X-API-Key")
    API_KEY: Optional[str] = os.getenv("API_KEY")


config = Config()
