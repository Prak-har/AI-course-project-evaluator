import json
from pathlib import Path

import faiss
import numpy as np

from backend.config import get_settings


settings = get_settings()


class SubmissionVectorStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or settings.faiss_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _submission_dir(self, submission_id: int) -> Path:
        return self.base_dir / str(submission_id)

    def _index_path(self, submission_id: int) -> Path:
        return self._submission_dir(submission_id) / "index.faiss"

    def _metadata_path(self, submission_id: int) -> Path:
        return self._submission_dir(submission_id) / "metadata.json"

    def save_submission(self, submission_id: int, chunks: list[dict], embeddings: list[list[float]]) -> None:
        if not chunks or not embeddings:
            raise ValueError("Cannot create a FAISS index without chunks and embeddings.")

        directory = self._submission_dir(submission_id)
        directory.mkdir(parents=True, exist_ok=True)

        vectors = np.asarray(embeddings, dtype="float32")
        faiss.normalize_L2(vectors)

        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(self._index_path(submission_id)))

        centroid = vectors.mean(axis=0).astype("float32").tolist()
        metadata = {
            "submission_id": submission_id,
            "chunks": chunks,
            "centroid": centroid,
            "dimension": int(vectors.shape[1]),
        }
        self._metadata_path(submission_id).write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    def load_metadata(self, submission_id: int) -> dict:
        path = self._metadata_path(submission_id)
        if not path.exists():
            raise FileNotFoundError(f"No vector metadata found for submission {submission_id}.")
        return json.loads(path.read_text(encoding="utf-8"))

    def retrieve(self, submission_id: int, query_embedding: list[float], top_k: int) -> list[dict]:
        index_path = self._index_path(submission_id)
        if not index_path.exists():
            raise FileNotFoundError(f"No FAISS index found for submission {submission_id}.")

        metadata = self.load_metadata(submission_id)
        chunk_count = len(metadata["chunks"])
        if chunk_count == 0:
            return []

        query = np.asarray([query_embedding], dtype="float32")
        faiss.normalize_L2(query)

        index = faiss.read_index(str(index_path))
        scores, identifiers = index.search(query, min(top_k, chunk_count))

        results: list[dict] = []
        for score, chunk_index in zip(scores[0], identifiers[0], strict=False):
            if chunk_index < 0:
                continue
            chunk = metadata["chunks"][chunk_index]
            results.append({**chunk, "score": round(float(score), 4)})

        return results

    def find_similar_submissions(
        self,
        submission_id: int,
        submission_lookup,
        limit: int = 3,
        threshold: float | None = None,
    ) -> list[dict]:
        threshold = threshold if threshold is not None else settings.plagiarism_threshold
        target_metadata = self.load_metadata(submission_id)
        target_centroid = np.asarray(target_metadata["centroid"], dtype="float32")
        target_norm = float(np.linalg.norm(target_centroid)) or 1.0

        matches: list[dict] = []
        for child in self.base_dir.iterdir():
            if not child.is_dir() or child.name == str(submission_id):
                continue

            metadata_path = child / "metadata.json"
            if not metadata_path.exists():
                continue

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            other_centroid = np.asarray(metadata["centroid"], dtype="float32")
            other_norm = float(np.linalg.norm(other_centroid)) or 1.0
            similarity = float(np.dot(target_centroid, other_centroid) / (target_norm * other_norm))

            if similarity < threshold:
                continue

            other_submission = submission_lookup(int(child.name))
            if not other_submission:
                continue

            matches.append(
                {
                    "submission_id": other_submission.id,
                    "student_id": other_submission.student_id,
                    "student_name": other_submission.student.name,
                    "similarity": round(similarity, 4),
                }
            )

        matches.sort(key=lambda item: item["similarity"], reverse=True)
        return matches[:limit]


submission_vector_store = SubmissionVectorStore()
