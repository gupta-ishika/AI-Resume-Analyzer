import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import Any

from backend.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService(ABC):
    """Abstract interface for text embedding generation."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single string into a vector."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings into vectors."""

    @abstractmethod
    def similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors (-1.0 to 1.0)."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name/version of the embedding model."""


class DeterministicHashEmbeddingService(EmbeddingService):
    """
    Deterministic embedding generator using hashing and term frequency.
    Ensures 100% reproducible, fast embeddings without external model weights.
    Vector dimension defaults to 128.
    """

    def __init__(self, dimension: int = 128):
        self._dim = dimension
        self._model_name = f"deterministic-hash-v1-{dimension}d"

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        if not text or not text.strip():
            return vec

        # Tokenize words and character 3-grams
        tokens = [t.lower() for t in re.findall(r"\b\w+\b", text)]
        if not tokens:
            return vec

        for token in tokens:
            # Word hash
            h_val = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h_val % self._dim
            sign = 1.0 if (h_val // self._dim) % 2 == 0 else -1.0
            vec[idx] += sign

            # Sub-word 3-grams
            if len(token) >= 3:
                for i in range(len(token) - 2):
                    ngram = token[i : i + 3]
                    h_ng = int(hashlib.sha256(ngram.encode("utf-8")).hexdigest(), 16)
                    idx_ng = h_ng % self._dim
                    sign_ng = 1.0 if (h_ng // self._dim) % 2 == 0 else -1.0
                    vec[idx_ng] += 0.5 * sign_ng

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def similarity(self, vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 <= 0.0 or norm2 <= 0.0:
            return 0.0
        cos = dot / (norm1 * norm2)
        return max(-1.0, min(1.0, cos))


class VectorStore(ABC):
    """Abstract interface for analysis-isolated vector storage."""

    @abstractmethod
    def create_collection(self, analysis_id: str) -> None:
        """Idempotently create an analysis-specific collection."""

    @abstractmethod
    def upsert_document(
        self,
        analysis_id: str,
        doc_id: str,
        text: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Upsert a document into the analysis collection."""

    @abstractmethod
    def query(
        self,
        analysis_id: str,
        query_text: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Query top matching documents within the analysis collection."""

    @abstractmethod
    def delete_collection(self, analysis_id: str) -> None:
        """Idempotently delete an analysis collection."""


class InMemoryVectorStore(VectorStore):
    """
    In-memory vector store guaranteeing complete collection isolation per analysis.
    Used for unit testing and local execution without requiring a running ChromaDB daemon.
    """

    def __init__(self, embedding_service: EmbeddingService | None = None):
        self._embedding_service = embedding_service or DeterministicHashEmbeddingService()
        self._collections: dict[str, dict[str, dict[str, Any]]] = {}

    def _col_name(self, analysis_id: str) -> str:
        return f"analysis_{analysis_id}"

    def create_collection(self, analysis_id: str) -> None:
        col_name = self._col_name(analysis_id)
        if col_name not in self._collections:
            self._collections[col_name] = {}

    def upsert_document(
        self,
        analysis_id: str,
        doc_id: str,
        text: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.create_collection(analysis_id)
        col_name = self._col_name(analysis_id)
        if embedding is None:
            embedding = self._embedding_service.embed(text)
        self._collections[col_name][doc_id] = {
            "id": doc_id,
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {},
        }

    def query(
        self,
        analysis_id: str,
        query_text: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        col_name = self._col_name(analysis_id)
        if col_name not in self._collections:
            return []

        q_vec = self._embedding_service.embed(query_text)
        docs = self._collections[col_name].values()
        scored: list[tuple[float, dict[str, Any]]] = []

        for doc in docs:
            sim = self._embedding_service.similarity(q_vec, doc["embedding"])
            scored.append((sim, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": doc["id"],
                "score": sim,
                "text": doc["text"],
                "metadata": doc["metadata"],
            }
            for sim, doc in scored[:top_k]
        ]

    def delete_collection(self, analysis_id: str) -> None:
        col_name = self._col_name(analysis_id)
        self._collections.pop(col_name, None)


# Default global instances for convenience
default_embedding_service = DeterministicHashEmbeddingService()
default_vector_store = InMemoryVectorStore(default_embedding_service)
