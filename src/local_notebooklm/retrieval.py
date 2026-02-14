from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from .config import Settings
from .ingest import ParsedDocument, chunk_text
from .storage import MetadataStore


class LocalRetriever:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)

        self.metadata = MetadataStore(self.settings.data_dir / "metadata.sqlite3")
        self.embedder = SentenceTransformer(self.settings.embedding_model)

        chroma_path = self.settings.data_dir / "chroma"
        self.chroma_client = chromadb.PersistentClient(path=str(chroma_path))
        self.collection: Collection = self.chroma_client.get_or_create_collection("docs")

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.embedder.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def index_document(self, doc: ParsedDocument) -> int:
        chunks = chunk_text(doc.text, self.settings.chunk_size, self.settings.chunk_overlap)
        if not chunks:
            return 0

        ids = [f"{doc.doc_id}__{i}" for i in range(len(chunks))]
        embeddings = self._embed(chunks)
        metadatas = [
            {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "source_type": doc.source_type,
                "source_ref": doc.source_ref,
                "chunk_idx": i,
            }
            for i in range(len(chunks))
        ]

        existing = self.collection.get(ids=ids)
        if existing["ids"]:
            self.collection.delete(ids=ids)

        self.collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)

        self.metadata.upsert_document(doc.doc_id, doc.source_type, doc.source_ref, doc.title)
        self.metadata.replace_chunks(
            doc.doc_id,
            ((f"{doc.doc_id}__{i}", i, chunks[i]) for i in range(len(chunks))),
        )
        return len(chunks)

    def query(self, question: str, top_k: int | None = None) -> list[dict]:
        limit = top_k or self.settings.top_k
        q_emb = self._embed([question])[0]
        results = self.collection.query(query_embeddings=[q_emb], n_results=limit)

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        out = []
        for i, chunk in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            distance = distances[i] if i < len(distances) else None
            out.append({"chunk": chunk, "meta": meta, "distance": distance})
        return out

    def list_documents(self) -> list[dict]:
        return self.metadata.list_documents()
