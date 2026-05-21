import os
import json
import sqlite3
import numpy as np

# Resolve paths relative to the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "db.sqlite3")
INDEX_PATH = os.path.join(BASE_DIR, "data", "jobs_faiss.index")
MAPPER_PATH = os.path.join(BASE_DIR, "data", "jobs_id_map.json")

class RecommendationEngine:
    def __init__(self):
        self.model = None
        self.index = None
        self.job_ids = []
        self._load_resources()

    def _load_resources(self):
        print("Initializing Recommendation Engine resources...")
        # 1. Load Sentence Transformer
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Warning: Failed to load SentenceTransformer model: {e}")

        # 2. Load FAISS index
        try:
            import faiss
            if os.path.exists(INDEX_PATH):
                self.index = faiss.read_index(INDEX_PATH)
                print(f"Loaded FAISS index from {INDEX_PATH}.")
            else:
                print(f"Warning: FAISS index file not found at {INDEX_PATH}.")
        except Exception as e:
            print(f"Warning: Failed to load FAISS index: {e}")

        # 3. Load job ID mapping list
        if os.path.exists(MAPPER_PATH):
            with open(MAPPER_PATH, 'r', encoding='utf-8') as f:
                self.job_ids = json.load(f)
                print(f"Loaded {len(self.job_ids)} job ID mappings.")
        else:
            print(f"Warning: Job ID mapping file not found at {MAPPER_PATH}.")

    def _get_experience_weight(self, user_exp: str, job_exp: str) -> float:
        """Calculate alignment between user experience level and job requirement.
        Scale: 0 (intern) -> 1 (junior) -> 2 (mid) -> 3 (senior/research)
        """
        if not user_exp or not job_exp:
            return 0.5 # Default middle score if missing

        exp_map = {
            "intern": 0,
            "junior": 1,
            "mid": 2,
            "senior": 3,
            "research": 3
        }

        u_lvl = exp_map.get(user_exp.lower(), 1)
        j_lvl = exp_map.get(job_exp.lower(), 1)

        if u_lvl >= j_lvl:
            return 1.0 # Fully qualified or overqualified
        elif u_lvl == j_lvl - 1:
            return 0.5 # Underqualified by one level
        elif u_lvl == j_lvl - 2:
            return 0.1 # Underqualified by two levels
        else:
            return 0.0 # Extremely underqualified

    def rank_jobs(self, skill_profile: dict, top_n: int = 10) -> list:
        """Rank job postings based on a multi-factor hybrid scoring mechanism.

        Weights:
        - 40% Semantic Similarity
        - 30% Skill Overlap
        - 15% Experience Match
        - 10% Category Match
        - 05% Location Match
        """
        # Parse skill profile
        detected_skills = skill_profile.get("detected_skills") or skill_profile.get("skills") or []
        user_exp = skill_profile.get("experience_level") or skill_profile.get("experience") or "junior"
        top_category = skill_profile.get("top_category") or skill_profile.get("category") or ""
        location_pref = skill_profile.get("location") or "remote"

        # Dedup and clean skills list
        detected_skills = list(dict.fromkeys([s.strip().lower() for s in detected_skills if s]))

        # Handle empty resources fallback
        if not self.model or not self.index or not self.job_ids:
            print("Recommendation Engine not fully initialized. Falling back to DB query...")
            return self._db_fallback_recommendations(detected_skills, user_exp, top_category, top_n)

        # 1. RETRIEVAL PHASE (Vector search via FAISS)
        # Construct query string from skills and category
        query_text = ", ".join(detected_skills)
        if top_category:
            query_text = f"{top_category}. Skills: {query_text}"

        query_vector = self.model.encode([query_text], normalize_embeddings=True)[0]
        query_vector = np.array([query_vector]).astype('float32')

        # Retrieve top K candidates (retrieve K=100 to rerank)
        k_retrieve = min(100, len(self.job_ids))
        if k_retrieve == 0:
            return []

        similarities, indices = self.index.search(query_vector, k_retrieve)

        candidate_indices = indices[0]
        candidate_similarities = similarities[0]

        # 2. SCORING AND RERANKING PHASE
        # Fetch metadata and skills for retrieved candidates from SQLite in one batch
        retrieved_job_ids = [self.job_ids[idx] for idx in candidate_indices if idx < len(self.job_ids)]
        if not retrieved_job_ids:
            return []

        # Connect to SQLite
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Query metadata
        placeholders = ",".join("?" for _ in retrieved_job_ids)
        cur.execute(f"""
            SELECT job_id, job_title, description, category, exp_level, location
            FROM jobs
            WHERE job_id IN ({placeholders})
        """, retrieved_job_ids)
        jobs_metadata = {row["job_id"]: dict(row) for row in cur.fetchall()}

        # Query job required skills
        cur.execute(f"""
            SELECT job_id, skill_id
            FROM job_skills
            WHERE job_id IN ({placeholders}) AND is_required = 1
        """, retrieved_job_ids)
        job_skills_mapping = {}
        for row in cur.fetchall():
            jid = row["job_id"]
            sid = row["skill_id"]
            if jid not in job_skills_mapping:
                job_skills_mapping[jid] = set()
            job_skills_mapping[jid].add(sid.lower())

        conn.close()

        # Create user skills set for quick intersection
        user_skills_set = set(detected_skills)

        ranked_results = []
        for i, idx in enumerate(candidate_indices):
            if idx >= len(self.job_ids):
                continue

            job_id = self.job_ids[idx]
            if job_id not in jobs_metadata:
                continue

            job = jobs_metadata[job_id]
            
            # A. Semantic similarity (scaled to [0, 1])
            sem_score = max(0.0, min(1.0, float(candidate_similarities[i])))

            # B. Skill overlap
            required_skills = job_skills_mapping.get(job_id, set())
            if not required_skills:
                skill_overlap_score = 1.0 # Match if no required skills are defined
            else:
                overlap_count = len(user_skills_set.intersection(required_skills))
                skill_overlap_score = float(overlap_count) / len(required_skills)

            # C. Experience Match
            exp_score = self._get_experience_weight(user_exp, job.get("exp_level"))

            # D. Category Match
            job_cat = job.get("category", "")
            cat_score = 1.0 if top_category.lower() == job_cat.lower() else 0.0

            # E. Location Match
            job_loc = job.get("location", "")
            loc_pref_clean = location_pref.lower()
            if loc_pref_clean == "remote":
                loc_score = 1.0 if "remote" in job_loc.lower() else 0.2
            else:
                # If they prefer on-site / specific, match if it contains their preference
                loc_score = 1.0 if loc_pref_clean in job_loc.lower() or not job_loc else 0.5

            # Calculate Final Hybrid Score
            final_score = (
                0.40 * sem_score +
                0.30 * skill_overlap_score +
                0.15 * exp_score +
                0.10 * cat_score +
                0.05 * loc_score
            )

            # Package result
            ranked_results.append({
                "job_id": job_id,
                "job_title": job["job_title"],
                "description": job["description"],
                "category": job["category"],
                "exp_level": job["exp_level"],
                "location": job["location"],
                "match_score": round(final_score * 100, 1),
                "breakdown": {
                    "semantic_similarity": round(sem_score * 100, 1),
                    "skill_overlap": round(skill_overlap_score * 100, 1),
                    "experience_match": round(exp_score * 100, 1),
                    "category_match": round(cat_score * 100, 1),
                    "location_match": round(loc_score * 100, 1)
                },
                "matched_skills": list(user_skills_set.intersection(required_skills)),
                "missing_skills": list(required_skills.difference(user_skills_set))
            })

        # Sort by final score descending
        ranked_results.sort(key=lambda x: x["match_score"], reverse=True)

        return ranked_results[:top_n]

    def _db_fallback_recommendations(self, detected_skills: list, user_exp: str, top_category: str, top_n: int) -> list:
        """Fallback recommendation builder using simple SQL queries if FAISS/Transformers are not ready."""
        print("Executing fallback DB recommendation query...")
        if not os.path.exists(DB_PATH):
            return []

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Query all jobs of the given category or general
        if top_category:
            cur.execute("""
                SELECT job_id, job_title, description, category, exp_level, location
                FROM jobs
                WHERE category = ?
                LIMIT 50
            """, (top_category,))
        else:
            cur.execute("""
                SELECT job_id, job_title, description, category, exp_level, location
                FROM jobs
                LIMIT 50
            """)
        
        rows = cur.fetchall()
        jobs_metadata = [dict(row) for row in rows]
        job_ids = [j["job_id"] for j in jobs_metadata]

        if not job_ids:
            conn.close()
            return []

        # Fetch required skills
        placeholders = ",".join("?" for _ in job_ids)
        cur.execute(f"""
            SELECT job_id, skill_id
            FROM job_skills
            WHERE job_id IN ({placeholders}) AND is_required = 1
        """, job_ids)
        
        job_skills = {}
        for row in cur.fetchall():
            jid = row["job_id"]
            sid = row["skill_id"]
            if jid not in job_skills:
                job_skills[jid] = set()
            job_skills[jid].add(sid.lower())

        conn.close()

        user_skills_set = set(detected_skills)
        ranked_results = []

        for job in jobs_metadata:
            job_id = job["job_id"]
            required_skills = job_skills.get(job_id, set())

            # Simple keyword matching score
            if not required_skills:
                skill_score = 0.5
            else:
                overlap = len(user_skills_set.intersection(required_skills))
                skill_score = float(overlap) / len(required_skills)

            exp_score = self._get_experience_weight(user_exp, job.get("exp_level"))

            # Simple combined score
            score = 0.6 * skill_score + 0.4 * exp_score

            ranked_results.append({
                "job_id": job_id,
                "job_title": job["job_title"],
                "description": job["description"],
                "category": job["category"],
                "exp_level": job["exp_level"],
                "location": job["location"],
                "match_score": round(score * 100, 1),
                "breakdown": {
                    "semantic_similarity": 0.0,
                    "skill_overlap": round(skill_score * 100, 1),
                    "experience_match": round(exp_score * 100, 1),
                    "category_match": 100.0 if top_category.lower() == job["category"].lower() else 0.0,
                    "location_match": 50.0
                },
                "matched_skills": list(user_skills_set.intersection(required_skills)),
                "missing_skills": list(required_skills.difference(user_skills_set))
            })

        ranked_results.sort(key=lambda x: x["match_score"], reverse=True)
        return ranked_results[:top_n]
