from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import numpy as np

from app.gap_analyzer import get_session_gaps

try:
	import faiss
	from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - handled at runtime
	faiss = None
	SentenceTransformer = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE_DIR, "data", "index.faiss")
ID_MAP_PATH = os.path.join(BASE_DIR, "data", "id_map.json")
META_PATH = os.path.join(BASE_DIR, "data", "resources_meta.json")


class ResourceRecommender:
	"""Semantic search for learning resources using a FAISS index."""

	def __init__(
		self,
		index_path: str = INDEX_PATH,
		id_map_path: str = ID_MAP_PATH,
		meta_path: str = META_PATH,
		model_name: str = "all-MiniLM-L6-v2",
	):
		self.index_path = index_path
		self.id_map_path = id_map_path
		self.meta_path = meta_path
		self.model_name = model_name
		self._model = None
		self._index = None
		self._id_map: List[str] = []
		self._meta: Dict[str, Dict[str, Any]] = {}
		self._load_error: Optional[str] = None

	def _ensure_loaded(self) -> None:
		if self._index is not None or self._load_error:
			return
		if faiss is None or SentenceTransformer is None:
			self._load_error = "FAISS or sentence-transformers not available"
			return
		if not (os.path.exists(self.index_path) and os.path.exists(self.id_map_path) and os.path.exists(self.meta_path)):
			self._load_error = "Resource index not found"
			return
		try:
			self._model = SentenceTransformer(self.model_name)
			self._index = faiss.read_index(self.index_path)
			with open(self.id_map_path, "r", encoding="utf-8") as handle:
				self._id_map = json.load(handle)
			with open(self.meta_path, "r", encoding="utf-8") as handle:
				self._meta = json.load(handle)
		except Exception as exc:  # pragma: no cover - defensive
			self._load_error = str(exc)

	def is_ready(self) -> bool:
		self._ensure_loaded()
		return self._index is not None

	def search_resources(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
		self._ensure_loaded()
		if not query or self._index is None or self._model is None:
			return []

		vec = self._model.encode([query], normalize_embeddings=True)
		vec = np.array(vec, dtype="float32")
		scores, indices = self._index.search(vec, top_k)

		results: List[Dict[str, Any]] = []
		for score, idx in zip(scores[0], indices[0]):
			if idx == -1 or idx >= len(self._id_map):
				continue
			rid = self._id_map[idx]
			resource = self._meta.get(rid, {}).copy()
			if not resource:
				continue
			resource["_similarity"] = round(float(score), 4)
			results.append(resource)
		return results

	def filter_and_rank(
		self,
		candidates: List[Dict[str, Any]],
		session: Dict[str, Any],
		skill_id: str,
	) -> List[Dict[str, Any]]:
		domain = str(session.get("detected_domain") or "").lower()
		seen = set(session.get("resources_shown") or [])

		def score(resource: Dict[str, Any]) -> float:
			score_value = float(resource.get("_similarity", 0.0))
			if resource.get("job_gap_alignment", {}).get("gap_priority") == "high":
				score_value += 0.10
			best_for = [item.lower() for item in resource.get("best_for", []) if isinstance(item, str)]
			if domain and domain in best_for:
				score_value += 0.08
			if resource.get("is_free"):
				score_value += 0.04
			if resource.get("resource_id") in seen:
				score_value -= 0.50
			return score_value

		ranked = sorted(candidates, key=score, reverse=True)
		return ranked[:2]

	def recommend(self, session: Dict[str, Any]) -> List[Dict[str, Any]]:
		gaps = get_session_gaps(session)
		results: List[Dict[str, Any]] = []
		for gap in gaps:
			candidates = self.search_resources(gap.get("query", ""))
			top = self.filter_and_rank(candidates, session, gap.get("skill_id", ""))
			for resource in top:
				results.append({"gap": gap, "resource": resource})
		return results
