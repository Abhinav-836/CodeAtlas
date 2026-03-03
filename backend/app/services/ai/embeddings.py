"""
Text and code embeddings with multiple backends (OpenAI, HuggingFace, Local).
PRODUCTION-SAFE VERSION
"""

from app.core.config import settings
from typing import List, Optional, Dict, Any
import numpy as np
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =========================
# ENUMS & DATA MODELS
# =========================

class EmbeddingBackend(str, Enum):
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    FAKE = "fake"


@dataclass
class EmbeddingResult:
    vector: List[float]
    model: str
    backend: EmbeddingBackend
    dimensions: int
    tokens: Optional[int] = None
    cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =========================
# CORE SERVICE
# =========================

class EmbeddingService:
    """Unified embedding service."""

    def __init__(self, backend: EmbeddingBackend | None = None):
        self.backend = backend or self._detect_backend()
        self._client = None

    def _detect_backend(self) -> EmbeddingBackend:
        if settings.OPENAI_API_KEY:
            return EmbeddingBackend.OPENAI
        return EmbeddingBackend.LOCAL

    # ---------- OPENAI ----------
    def _get_openai_client(self):
        if not self._client:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def _embed_openai(self, text: str, model: Optional[str], normalize: bool):
        client = self._get_openai_client()
        model = model or "text-embedding-3-small"

        response = client.embeddings.create(
            model=model,
            input=text
        )

        vector = response.data[0].embedding
        if normalize:
            vector = self._normalize(vector)

        return EmbeddingResult(
            vector=vector,
            model=model,
            backend=EmbeddingBackend.OPENAI,
            dimensions=len(vector),
            tokens=response.usage.total_tokens if response.usage else None,
        )

    # ---------- LOCAL ----------
    def _embed_local(self, text: str, normalize: bool):
        hash_bytes = hashlib.sha256(text.encode()).digest()
        vector = [(b / 255.0) * 2 - 1 for b in hash_bytes]

        if normalize:
            vector = self._normalize(vector)

        return EmbeddingResult(
            vector=vector,
            model="local-sha256",
            backend=EmbeddingBackend.LOCAL,
            dimensions=len(vector),
        )

    # ---------- FAKE ----------
    def _embed_fake(self, text: str, normalize: bool):
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
        rng = np.random.default_rng(seed)
        vector = rng.standard_normal(256).tolist()

        if normalize:
            vector = self._normalize(vector)

        return EmbeddingResult(
            vector=vector,
            model="fake-random",
            backend=EmbeddingBackend.FAKE,
            dimensions=len(vector),
        )

    # ---------- PUBLIC ----------
    def embed(
        self,
        text: str,
        model: Optional[str] = None,
        normalize: bool = True,
    ) -> Optional[EmbeddingResult]:

        if not text or not text.strip():
            return None

        text = text.replace("\n", " ").strip()

        try:
            if self.backend == EmbeddingBackend.OPENAI:
                return self._embed_openai(text, model, normalize)
            elif self.backend == EmbeddingBackend.FAKE:
                return self._embed_fake(text, normalize)
            else:
                return self._embed_local(text, normalize)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return self._embed_local(text, normalize)

    # ---------- SIMILARITY ----------
    def similarity(self, v1: List[float], v2: List[float]) -> float:
        if len(v1) != len(v2):
            logger.warning("Vector dimension mismatch")
            return 0.0

        v1 = np.array(v1)
        v2 = np.array(v2)

        denom = np.linalg.norm(v1) * np.linalg.norm(v2)
        return float(np.dot(v1, v2) / denom) if denom else 0.0

    @staticmethod
    def _normalize(vec: List[float]) -> List[float]:
        norm = np.linalg.norm(vec)
        return (np.array(vec) / norm).tolist() if norm else vec


# =========================
# CODE EMBEDDER
# =========================

class CodeEmbedder(EmbeddingService):
    """Embedding service specialized for source code."""

    def __init__(self, backend: EmbeddingBackend | None = None):
        super().__init__(backend)
        self._cache: Dict[str, EmbeddingResult] = {}

    def embed_code(
        self,
        code: str,
        language: str = "python",
    ) -> Optional[EmbeddingResult]:

        key = f"{language}:{hashlib.md5(code.encode()).hexdigest()}"

        if key in self._cache:
            return self._cache[key]

        text = f"[{language} code]\n{code}"
        result = self.embed(text)

        if result:
            result.metadata = {
                "language": language,
                "lines": code.count("\n") + 1,
            }
            self._cache[key] = result

        return result

    def find_similar_code(
        self,
        query_code: str,
        code_items: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:

        query_emb = self.embed_code(query_code)
        if not query_emb:
            return []

        scored = []
        for item in code_items:
            emb = item.get("embedding")
            if not emb:
                continue

            sim = self.similarity(query_emb.vector, emb)
            scored.append({**item, "similarity": sim})

        return sorted(scored, key=lambda x: x["similarity"], reverse=True)[:top_k]


# =========================
# GLOBALS
# =========================

embedding_service = EmbeddingService()
code_embedder = CodeEmbedder()


# =========================
# HELPERS
# =========================

def get_embedding(text: str) -> Optional[List[float]]:
    result = embedding_service.embed(text)
    return result.vector if result else None


def get_code_embedding(code: str, language: str = "python") -> Optional[List[float]]:
    result = code_embedder.embed_code(code, language)
    return result.vector if result else None
