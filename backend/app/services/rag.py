import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Literal

from app.models import Citation, RetrievalStrategy


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    source: str
    text: str
    terms: tuple[str, ...]


class LocalTfidfRetriever:
    """本地双路检索：TF-IDF 基线、BM25，以及使用 RRF 的稳定融合排序。"""

    def __init__(self, chunk_size: int = 260, overlap: int = 40):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.chunks: list[Chunk] = []
        self.document_frequency: Counter[str] = Counter()
        self.term_frequencies: dict[str, Counter[str]] = {}
        self.average_chunk_length = 0.0
        self.default_strategy: RetrievalStrategy = "rrf"

    @staticmethod
    def tokenize(text: str) -> list[str]:
        normalized = text.lower()
        ascii_terms = re.findall(r"[a-z0-9_]+", normalized)
        chinese_sequences = re.findall(r"[\u4e00-\u9fff]+", normalized)
        chinese_terms: list[str] = []
        for sequence in chinese_sequences:
            chinese_terms.extend(sequence)
            chinese_terms.extend(
                sequence[index : index + 2] for index in range(len(sequence) - 1)
            )
        return ascii_terms + chinese_terms

    def split_text(self, text: str) -> list[str]:
        paragraphs = [item.strip() for item in re.split(r"\n+", text) if item.strip()]
        units: list[str] = []
        for paragraph in paragraphs:
            units.extend(
                item.strip()
                for item in re.split(r"(?<=[。！？；])", paragraph)
                if item.strip()
            )

        chunks: list[str] = []
        current = ""
        for unit in units:
            if current and len(current) + len(unit) > self.chunk_size:
                chunks.append(current)
                current = current[-self.overlap :] + unit
            else:
                current += unit
        if current:
            chunks.append(current)
        return chunks or ([text.strip()] if text.strip() else [])

    def build(self, documents: Iterable[dict]) -> None:
        chunks: list[Chunk] = []
        document_frequency: Counter[str] = Counter()
        term_frequencies: dict[str, Counter[str]] = {}
        for document in documents:
            for index, text in enumerate(self.split_text(document["text"])):
                terms = tuple(self.tokenize(text))
                chunk = Chunk(
                    id=f'{document["id"]}#{index}',
                    document_id=document["id"],
                    source=document["source"],
                    text=text,
                    terms=terms,
                )
                chunks.append(chunk)
                document_frequency.update(set(terms))
                term_frequencies[chunk.id] = Counter(terms)
        self.chunks = chunks
        self.document_frequency = document_frequency
        self.term_frequencies = term_frequencies
        self.average_chunk_length = (
            sum(len(chunk.terms) for chunk in chunks) / len(chunks) if chunks else 0.0
        )

    def _idf(self, term: str) -> float:
        return math.log((len(self.chunks) + 1) / (self.document_frequency[term] + 1)) + 1

    def _vector(self, terms: Iterable[str]) -> dict[str, float]:
        counts = Counter(terms)
        if not counts:
            return {}
        scale = sum(counts.values())
        return {term: count / scale * self._idf(term) for term, count in counts.items()}

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        if not left or not right:
            return 0.0
        dot = sum(value * right.get(term, 0.0) for term, value in left.items())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0

    def _rank_tfidf(self, query: str) -> list[tuple[float, Chunk]]:
        query_vector = self._vector(self.tokenize(query))
        return sorted(
            (
                (self._cosine(query_vector, self._vector(chunk.terms)), chunk)
                for chunk in self.chunks
            ),
            key=lambda item: (-item[0], item[1].id),
        )

    def _bm25_idf(self, term: str) -> float:
        total = len(self.chunks)
        frequency = self.document_frequency[term]
        return math.log(1 + (total - frequency + 0.5) / (frequency + 0.5)) if total else 0.0

    def _rank_bm25(self, query: str) -> list[tuple[float, Chunk]]:
        query_terms = Counter(self.tokenize(query))
        if not query_terms or not self.chunks:
            return []
        k1, b = 1.5, 0.75
        average_length = self.average_chunk_length or 1.0
        scored: list[tuple[float, Chunk]] = []
        for chunk in self.chunks:
            frequencies = self.term_frequencies[chunk.id]
            length = len(chunk.terms)
            score = 0.0
            for term, query_frequency in query_terms.items():
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + k1 * (1 - b + b * length / average_length)
                score += self._bm25_idf(term) * (frequency * (k1 + 1) / denominator) * query_frequency
            scored.append((score, chunk))
        return sorted(scored, key=lambda item: (-item[0], item[1].id))

    @staticmethod
    def _rrf(
        tfidf_ranked: list[tuple[float, Chunk]], bm25_ranked: list[tuple[float, Chunk]], k: int = 60
    ) -> list[tuple[float, Chunk]]:
        fused: dict[str, tuple[float, Chunk]] = {}
        for ranked in (tfidf_ranked, bm25_ranked):
            for rank, (_, chunk) in enumerate(ranked, start=1):
                if not _:
                    continue
                score, _chunk = fused.get(chunk.id, (0.0, chunk))
                fused[chunk.id] = (score + 1 / (k + rank), _chunk)
        return sorted(fused.values(), key=lambda item: (-item[0], item[1].id))

    def rank(
        self, query: str, strategy: RetrievalStrategy | Literal["tfidf", "bm25", "rrf"] | None = None
    ) -> list[tuple[float, Chunk]]:
        selected = strategy or self.default_strategy
        tfidf_ranked = self._rank_tfidf(query)
        if selected == "tfidf":
            return [(score, chunk) for score, chunk in tfidf_ranked if score > 0]
        bm25_ranked = self._rank_bm25(query)
        if selected == "bm25":
            return [(score, chunk) for score, chunk in bm25_ranked if score > 0]
        return self._rrf(tfidf_ranked, bm25_ranked)

    def search(
        self, query: str, top_k: int = 4, strategy: RetrievalStrategy | None = None
    ) -> list[Citation]:
        selected = strategy or self.default_strategy
        ranked = self.rank(query, selected)
        # RRF 与 BM25 的内部分数只用于排序，不能直接拿来做跨策略证据判断。
        # 所有策略对外统一暴露 TF-IDF 余弦分，让 Top-1 证据门槛和 UI 百分比保持同一语义。
        tfidf_scores = {chunk.id: score for score, chunk in self._rank_tfidf(query)}
        return [
            Citation(
                source=chunk.source,
                chunk=chunk.text,
                score=round(tfidf_scores.get(chunk.id, 0.0), 4),
                chunk_id=chunk.id,
            )
            for score, chunk in ranked[:top_k]
        ]

    def chunk_counts(self) -> Counter[str]:
        return Counter(chunk.document_id for chunk in self.chunks)
