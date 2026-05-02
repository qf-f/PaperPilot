from __future__ import annotations

from collections.abc import Iterable

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings


class EmbeddingServiceError(Exception):
    pass


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.embedding_api_key:
            raise EmbeddingServiceError("EMBEDDING_API_KEY is not configured")

        self.client = OpenAI(
            api_key=self.settings.embedding_api_key,
            base_url=self.settings.embedding_base_url,
            timeout=self.settings.embedding_timeout_seconds,
        )

    def embed_text(self, text: str) -> list[float]:
        embeddings = self.embed_texts([text])
        return embeddings[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        cleaned = self._validate_texts(texts)
        all_embeddings: list[list[float]] = []
        batch_size = self._effective_batch_size()

        for batch in self._batched(cleaned, batch_size):
            embeddings = self._request_embeddings(batch)
            for embedding in embeddings:
                self._validate_dimension(embedding)
            all_embeddings.extend(embeddings)

        return all_embeddings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _request_embeddings(self, texts: list[str]) -> list[list[float]]:
        try:
            kwargs = {
                "model": self.settings.embedding_model,
                "input": texts,
            }
            if self.settings.embedding_model in {"text-embedding-v3", "text-embedding-v4"}:
                kwargs["dimensions"] = self.settings.embedding_dim
                kwargs["encoding_format"] = "float"
            response = self.client.embeddings.create(
                **kwargs,
            )
            return [list(item.embedding) for item in response.data]
        except Exception as exc:
            raise EmbeddingServiceError(f"Embedding API call failed: {exc}") from exc

    def _validate_dimension(self, embedding: list[float]) -> None:
        if len(embedding) != self.settings.embedding_dim:
            raise EmbeddingServiceError(
                "Embedding dimension mismatch: "
                f"expected {self.settings.embedding_dim}, got {len(embedding)}. "
                "Keep EMBEDDING_DIM aligned with document_chunks.embedding vector dimension."
            )

    @staticmethod
    def _validate_texts(texts: list[str]) -> list[str]:
        if not texts:
            raise EmbeddingServiceError("No texts provided for embedding")

        cleaned = [text.strip() if text else "" for text in texts]
        if any(not text for text in cleaned):
            raise EmbeddingServiceError("Embedding text cannot be empty")
        return cleaned

    def _effective_batch_size(self) -> int:
        configured = max(1, self.settings.embedding_batch_size)
        if self.settings.embedding_model in {"text-embedding-v3", "text-embedding-v4"}:
            # DashScope compatible embedding models currently reject batches larger than 10.
            return min(configured, 10)
        return configured

    @staticmethod
    def _batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
        safe_batch_size = max(1, batch_size)
        for index in range(0, len(items), safe_batch_size):
            yield items[index : index + safe_batch_size]
