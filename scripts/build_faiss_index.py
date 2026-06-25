from __future__ import annotations

import json
import os

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_PATH = os.path.join(BASE_DIR, "data", "learning_resources.json")
INDEX_PATH = os.path.join(BASE_DIR, "data", "index.faiss")
ID_MAP_PATH = os.path.join(BASE_DIR, "data", "id_map.json")
META_PATH = os.path.join(BASE_DIR, "data", "resources_meta.json")


MODEL_NAME = "all-MiniLM-L6-v2"  # 384-dim, fast, free


def make_text(resource: dict) -> str:
	covers = ", ".join(resource.get("covers", []))
	titles = ", ".join(resource.get("job_gap_alignment", {}).get("target_job_titles", []))
	why = resource.get("job_gap_alignment", {}).get("why_this_resource", "")
	return f"{resource.get('title', '')} {covers} {titles} {why}".strip()


def main() -> None:
	if not os.path.exists(RESOURCES_PATH):
		raise FileNotFoundError(f"Missing resources file: {RESOURCES_PATH}")

	with open(RESOURCES_PATH, "r", encoding="utf-8") as handle:
		resources = json.load(handle).get("resources", [])

	model = SentenceTransformer(MODEL_NAME)
	texts = [make_text(resource) for resource in resources]
	ids = [resource["resource_id"] for resource in resources]
	metadata = {resource["resource_id"]: resource for resource in resources}

	embeddings = model.encode(texts, normalize_embeddings=True)
	embeddings = np.array(embeddings, dtype="float32")

	index = faiss.IndexFlatIP(embeddings.shape[1])
	index.add(embeddings)

	faiss.write_index(index, INDEX_PATH)
	with open(ID_MAP_PATH, "w", encoding="utf-8") as handle:
		json.dump(ids, handle)
	with open(META_PATH, "w", encoding="utf-8") as handle:
		json.dump(metadata, handle)

	print(f"Indexed {len(ids)} resources.")


if __name__ == "__main__":
	main()
