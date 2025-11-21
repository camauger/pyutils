from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable, Protocol, cast

import numpy as np

CosineSimilarity = Callable[[np.ndarray, np.ndarray], np.ndarray]


class _SentenceTransformer(Protocol):
    def encode(
        self, sentences: Any, *args: Any, **kwargs: Any
    ) -> np.ndarray:  # pragma: no cover - typing helper
        ...


_MODEL_NAME = "all-MiniLM-L6-v2"
_MODEL: _SentenceTransformer | None = None
_COSINE_SIMILARITY: CosineSimilarity | None = None


def _get_sentence_transformer() -> _SentenceTransformer:
    global _MODEL
    model = _MODEL
    if model is None:
        try:
            module = importlib.import_module("sentence_transformers")
        except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "search_notes requires the 'sentence-transformers' package. "
                "Install it via 'pip install sentence-transformers>=2.2.2,<3.0.0'."
            ) from exc
        sentence_transformer_cls = module.SentenceTransformer
        model = sentence_transformer_cls(_MODEL_NAME)
        _MODEL = model
    return model


def _get_cosine_similarity() -> CosineSimilarity:
    global _COSINE_SIMILARITY
    cosine = _COSINE_SIMILARITY
    if cosine is None:
        try:
            metrics = importlib.import_module("sklearn.metrics.pairwise")
        except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "search_notes requires scikit-learn. Install it via 'pip install scikit-learn>=1.5.0'."
            ) from exc
        cosine = cast(CosineSimilarity, metrics.cosine_similarity)
        _COSINE_SIMILARITY = cosine
    return cosine


notes_dir = Path("notes")
notes: list[str] = []
contents: list[str] = []

for file_path in notes_dir.iterdir():
    if not file_path.is_file():
        continue
    text = file_path.read_text(encoding="utf-8")
    contents.append(text)
    notes.append(file_path.name)

model = _get_sentence_transformer()
cosine_similarity_fn = _get_cosine_similarity()
embeddings = model.encode(contents)


def search(query):
    query_vec = model.encode([query])
    scores = cosine_similarity_fn(query_vec, embeddings)[0]
    top_idx = np.argmax(scores)
    return notes[top_idx], contents[top_idx]


result = search("how to reverse a linked list")
print(result)
